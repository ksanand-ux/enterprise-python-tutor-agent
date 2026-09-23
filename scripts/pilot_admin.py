"""Run only from a trusted operator machine with its private configuration."""

import argparse
import asyncio
import hashlib
import json
import re
import secrets

from dotenv import load_dotenv
from app.settings import get_settings, ConfigurationError
from app.usage import connect, prefix
from redis.exceptions import RedisError


async def operate(command, caller=None):
    settings = get_settings()
    if settings.mode != "pilot":
        raise ConfigurationError("Set TUTOR_MODE=pilot for store operations")
    base = prefix(settings)
    async with connect(settings) as store:
        if command == "initialize":
            created = await store.eval("""
                if redis.call('EXISTS', KEYS[1]) == 1 then return 0 end
                redis.call('SET', KEYS[2], 'false')
                redis.call('SET', KEYS[1], '1')
                return 1
            """, 2, base + "initialized", base + "enabled")
            return {"initialized": True, "created": bool(created), "note": "New stores start paused"}
        if await store.get(base + "initialized") != "1":
            raise ConfigurationError("Store is not initialized")
        if command in {"pause", "enable"}:
            await store.set(base + "enabled", "true" if command == "enable" else "false")
        elif command == "revoke":
            await store.sadd(base + "revoked", caller)
        elif command == "restore":
            await store.srem(base + "revoked", caller)
        return {
            "enabled": await store.get(base + "enabled") == "true",
            "global_usage": await store.hgetall(base + "global:day"),
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["issue", "initialize", "status", "pause", "enable", "revoke", "restore"])
    parser.add_argument("--caller")
    parser.add_argument("--env-file", default=".env")
    args = parser.parse_args()
    if args.command in {"issue", "revoke", "restore"}:
        if not args.caller or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", args.caller):
            parser.error("Use --caller with an opaque ID such as learner-01")
    if args.command == "issue":
        token = secrets.token_urlsafe(32)
        print("PRIVATE caller key (store and share privately):", token)
        print("Server entry:", json.dumps({args.caller: hashlib.sha256(token.encode()).hexdigest()}))
        return
    load_dotenv(args.env_file)
    try:
        print(json.dumps(asyncio.run(operate(args.command, args.caller))))
    except (ConfigurationError, RedisError):
        parser.exit(1, "Operation failed: check private configuration and store availability.\n")


if __name__ == "__main__":
    main()
