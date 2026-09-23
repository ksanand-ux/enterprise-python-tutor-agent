import hashlib
import os
import secrets

from fastapi import HTTPException


def authenticate(provided_key, settings):
    if settings.mode == "demo":
        expected = os.getenv("TUTOR_ACCESS_KEY")
        if not expected:
            raise HTTPException(503, "Tutor access is not configured")
        if not provided_key or len(provided_key) > 512 or not secrets.compare_digest(
            provided_key.encode("utf-8"), expected.encode("utf-8")
        ):
            raise HTTPException(403, "Missing or invalid tutor access key")
        return "demo"

    if not provided_key or not 32 <= len(provided_key) <= 512:
        raise HTTPException(403, "Missing or invalid tutor access key")
    digest = hashlib.sha256(provided_key.encode("utf-8")).hexdigest()
    matched = None
    for caller, expected in settings.callers.items():
        if secrets.compare_digest(digest, expected):
            matched = caller
    if matched is None:
        raise HTTPException(403, "Missing or invalid tutor access key")
    return matched
