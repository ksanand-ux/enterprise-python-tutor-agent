"""Bound request bodies and emit content-free, correlated access logs."""

import asyncio
import json
import logging
import time
import uuid

from starlette.responses import JSONResponse

logger = logging.getLogger("tutor")


class RequestBoundary:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started = time.perf_counter()
        trace_id = str(uuid.uuid4())
        state = scope.setdefault("state", {})
        state["trace_id"] = trace_id
        status = 500

        async def traced_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = list(message.get("headers", [])) + [
                    (b"x-request-id", trace_id.encode()),
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                ]
            await send(message)

        try:
            if scope.get("path") == "/ask":
                body = bytearray()
                try:
                    async with asyncio.timeout(5):
                        while True:
                            message = await receive()
                            if message["type"] == "http.disconnect":
                                return
                            chunk = message.get("body", b"")
                            if len(body) + len(chunk) > 16384:
                                await JSONResponse({"detail": "Request is too large"}, 413)(
                                    scope, receive, traced_send
                                )
                                return
                            body.extend(chunk)
                            if not message.get("more_body", False):
                                break
                except TimeoutError:
                    await JSONResponse({"detail": "Request body timed out"}, 408)(
                        scope, receive, traced_send
                    )
                    return
                sent = False

                async def replay():
                    nonlocal sent
                    if not sent:
                        sent = True
                        return {"type": "http.request", "body": bytes(body), "more_body": False}
                    return await receive()

                await self.app(scope, replay, traced_send)
            else:
                await self.app(scope, receive, traced_send)
        finally:
            logger.info(json.dumps({
                "event": "request", "trace_id": trace_id,
                "route": scope.get("path") if scope.get("path") in {"/ask", "/health", "/ready"} else "other",
                "status": status, "caller": state.get("caller", "anonymous"),
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            }))
