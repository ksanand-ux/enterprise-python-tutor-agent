"""Atomic Redis admission across workers. No automatic reset on store loss."""

from contextlib import asynccontextmanager
import logging

from fastapi import HTTPException
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import RedisError

logger = logging.getLogger("tutor")

# Hash fields store the Redis-server minute/day, so app clocks cannot reset limits.
# All keys share a Redis hash tag; the script also works in a single cluster slot.
ADMIT = """
if redis.call('GET', KEYS[1]) ~= '1' then return {503, 0} end
if redis.call('SISMEMBER', KEYS[2], ARGV[1]) == 1 then return {403, 0} end
if redis.call('GET', KEYS[3]) ~= 'true' then return {503, 0} end
local now = tonumber(redis.call('TIME')[1])
local minute = math.floor(now / 60)
local day = math.floor(now / 86400)
local function count(key, window, field)
  if redis.call('HGET', key, 'window') ~= tostring(window) then return 0 end
  return tonumber(redis.call('HGET', key, field) or '0')
end
local cm = count(KEYS[4], minute, 'count')
local cd = count(KEYS[5], day, 'count')
local gd = count(KEYS[6], day, 'count')
if cm >= tonumber(ARGV[3]) then return {429, 60 - (now % 60)} end
if cd >= tonumber(ARGV[4]) or gd >= tonumber(ARGV[5]) then
  return {429, 86400 - (now % 86400)}
end
redis.call('ZREMRANGEBYSCORE', KEYS[7], '-inf', now)
if redis.call('ZCARD', KEYS[7]) >= tonumber(ARGV[6]) then return {429, 5} end
redis.call('HSET', KEYS[4], 'window', minute, 'count', cm + 1)
redis.call('HSET', KEYS[5], 'window', day, 'count', cd + 1)
redis.call('HSET', KEYS[6], 'window', day, 'count', gd + 1)
redis.call('EXPIRE', KEYS[4], 120)
redis.call('EXPIRE', KEYS[5], 172800)
redis.call('EXPIRE', KEYS[6], 172800)
redis.call('ZADD', KEYS[7], now + tonumber(ARGV[7]), ARGV[2])
return {200, 0}
"""


def prefix(settings):
    return "tutor:{" + settings.namespace + "}:"


def connect(settings):
    return Redis.from_url(
        settings.redis_url, decode_responses=True,
        socket_connect_timeout=2, socket_timeout=2,
        retry_on_timeout=False,
        retry=Retry(NoBackoff(), 0),
    )


async def check_store(settings):
    async with connect(settings) as store:
        base = prefix(settings)
        ready, enabled = await store.mget(base + "initialized", base + "enabled")
        return ready == "1" and enabled == "true"


@asynccontextmanager
async def admission(settings, caller, trace_id):
    if settings.mode == "demo":
        yield
        return
    base = prefix(settings)
    active_key = base + "active"
    try:
        async with connect(settings) as store:
            status, retry_after = await store.eval(
                ADMIT, 7,
                base + "initialized", base + "revoked", base + "enabled",
                base + caller + ":minute", base + caller + ":day",
                base + "global:day", active_key,
                caller, trace_id, settings.per_minute, settings.per_day,
                settings.global_per_day, settings.concurrency,
                settings.deadline + 30,
            )
            if status == 403:
                raise HTTPException(403, "Missing or invalid tutor access key")
            if status == 429:
                raise HTTPException(429, "Tutor usage limit reached", headers={
                    "Retry-After": str(retry_after),
                })
            if status != 200:
                raise HTTPException(503, "Tutor is temporarily unavailable")
            try:
                yield
            finally:
                # Failed release keeps a lease until expiry: fail closed on capacity.
                try:
                    await store.zrem(active_key, trace_id)
                except RedisError:
                    logger.warning('{"event":"usage_lease_release_failed"}')
    except RedisError as error:
        raise HTTPException(503, "Tutor usage controls are unavailable") from error
