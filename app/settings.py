"""Explicit limits for the invite-only pilot; demo mode preserves local setup."""

import json
import os
import re
from dataclasses import dataclass


class ConfigurationError(ValueError):
    pass


def integer(name, default, minimum, maximum):
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as error:
        raise ConfigurationError("Invalid limit configuration") from error
    if not minimum <= value <= maximum:
        raise ConfigurationError("Invalid limit configuration")
    return value


@dataclass(frozen=True)
class Settings:
    mode: str
    callers: dict[str, str]
    redis_url: str
    namespace: str
    per_minute: int
    per_day: int
    global_per_day: int
    concurrency: int
    deadline: int
    output_tokens: int
    model_enabled: bool


def get_settings():
    mode = os.getenv("TUTOR_MODE", "demo")
    if mode not in {"demo", "pilot"}:
        raise ConfigurationError("Invalid mode")
    namespace = os.getenv("TUTOR_NAMESPACE", "pilot")
    if not re.fullmatch(r"[a-z0-9_-]{1,32}", namespace):
        raise ConfigurationError("Invalid namespace")
    enabled = os.getenv("TUTOR_MODEL_ENABLED", "true")
    if enabled not in {"true", "false"}:
        raise ConfigurationError("Invalid model switch")
    callers = {}
    redis_url = os.getenv("REDIS_URL", "")
    if mode == "pilot":
        try:
            callers = json.loads(os.getenv("TUTOR_CALLERS_JSON", "{}"))
        except (ValueError, TypeError) as error:
            raise ConfigurationError("Invalid caller configuration") from error
        if not isinstance(callers, dict) or not 1 <= len(callers) <= 100:
            raise ConfigurationError("Invalid caller configuration")
        for caller, digest in callers.items():
            if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", caller):
                raise ConfigurationError("Invalid caller configuration")
            if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
                raise ConfigurationError("Invalid caller configuration")
        if len(set(callers.values())) != len(callers):
            raise ConfigurationError("Caller keys must be unique")
        if not redis_url.startswith(("redis://", "rediss://")):
            raise ConfigurationError("Usage store is not configured")
    return Settings(
        mode=mode,
        callers=callers,
        redis_url=redis_url,
        namespace=namespace,
        per_minute=integer("TUTOR_REQUESTS_PER_MINUTE", 5, 1, 60),
        per_day=integer("TUTOR_REQUESTS_PER_DAY", 20, 1, 1000),
        global_per_day=integer("TUTOR_GLOBAL_REQUESTS_PER_DAY", 50, 1, 10000),
        concurrency=integer("TUTOR_MAX_CONCURRENT", 2, 1, 10),
        deadline=integer("TUTOR_MODEL_TIMEOUT_SECONDS", 45, 1, 120),
        output_tokens=integer("TUTOR_MAX_OUTPUT_TOKENS", 1200, 128, 4096),
        model_enabled=enabled == "true",
    )
