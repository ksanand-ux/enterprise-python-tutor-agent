import asyncio

from app.boundary import RequestBoundary


def test_chunked_body_cannot_bypass_size_limit():
    messages = []
    chunks = iter([
        {"type": "http.request", "body": b"x" * 10000, "more_body": True},
        {"type": "http.request", "body": b"x" * 10000, "more_body": False},
    ])

    async def receive():
        return next(chunks)

    async def send(message):
        messages.append(message)

    async def unreachable(*args):
        raise AssertionError("Oversized input must not reach the app")

    asyncio.run(RequestBoundary(unreachable)({"type": "http", "path": "/ask"}, receive, send))
    assert messages[0]["status"] == 413


def test_slow_body_is_bounded(monkeypatch):
    real_timeout = asyncio.timeout
    monkeypatch.setattr("app.boundary.asyncio.timeout", lambda seconds: real_timeout(0.01))
    messages = []

    async def receive():
        await asyncio.sleep(1)

    async def send(message):
        messages.append(message)

    async def unreachable(*args):
        raise AssertionError("Timed out input must not reach the app")

    asyncio.run(RequestBoundary(unreachable)({"type": "http", "path": "/ask"}, receive, send))
    assert messages[0]["status"] == 408
