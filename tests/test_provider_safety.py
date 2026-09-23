import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import RateLimitError, AuthenticationError, APIConnectionError

from app.main import app
from app.telemetry import record_usage

client = TestClient(app)


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("TUTOR_ACCESS_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "private-provider-key")
    seen = []
    result = SimpleNamespace(
        status="completed", output_text="Use append to add an item.", usage=None,
    )
    result.model_dump = lambda: {"output": [{"type": "message", "content": [{
        "annotations": [{"type": "url_citation", "url": "https://docs.python.org/3/"}],
    }]}]}

    async def create(**kwargs):
        seen.append(kwargs)
        return result

    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["max_retries"] == 0
            assert kwargs["timeout"] <= 120
            self.responses = SimpleNamespace(create=create)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr("app.main.OpenAI", FakeClient)
    return result, seen, FakeClient


def ask(question="How do I add an item to a list?"):
    return client.post("/ask", headers={"X-Tutor-Key": "test-key"}, json={"question": question})


def test_request_bounds_and_secret_separation(provider):
    _, seen, _ = provider
    assert ask().status_code == 200
    sent = seen[0]
    assert sent["max_output_tokens"] == 1200
    assert sent["max_tool_calls"] == 2
    assert sent["store"] is False
    assert "untrusted data" in sent["instructions"]
    assert "private-provider-key" not in json.dumps(sent)


def test_missing_citations_fail(provider):
    result, _, _ = provider
    result.model_dump = lambda: {"output": []}
    assert ask().status_code == 502


def test_misleading_runtime_citation_fails(provider):
    result, _, _ = provider
    result.model_dump = lambda: {"output": [{"type": "message", "content": [{
        "annotations": [{"type": "url_citation", "url": "https://evil.example/docs.python.org"}],
    }]}]}
    assert ask().status_code == 502


@pytest.mark.parametrize("status", ["incomplete", "failed", "in_progress"])
def test_incomplete_answer_fails(provider, status):
    result, _, _ = provider
    result.status = status
    assert ask().status_code == 502


def test_deadline_stops_waiting(provider, monkeypatch):
    _, _, fake_client = provider
    monkeypatch.setenv("TUTOR_MODEL_TIMEOUT_SECONDS", "1")

    async def enter(self):
        async def slow(**kwargs):
            await asyncio.sleep(10)
        self.responses.create = slow
        return self

    monkeypatch.setattr(fake_client, "__aenter__", enter)
    assert ask().status_code == 504


@pytest.mark.parametrize("error_type,expected", [
    (RateLimitError, 503), (AuthenticationError, 502), (APIConnectionError, 503),
])
def test_provider_failures_are_safe(provider, monkeypatch, error_type, expected):
    _, _, fake_client = provider
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")

    async def enter(self):
        async def fail(**kwargs):
            if error_type is APIConnectionError:
                raise error_type(message="private-provider-key", request=request)
            raise error_type("private-provider-key", response=httpx.Response(429, request=request), body={})
        self.responses.create = fail
        return self

    monkeypatch.setattr(fake_client, "__aenter__", enter)
    response = ask()
    assert response.status_code == expected
    assert "private-provider-key" not in response.text


def test_local_model_switch_prevents_paid_call(provider, monkeypatch):
    _, seen, _ = provider
    monkeypatch.setenv("TUTOR_MODEL_ENABLED", "false")
    assert ask().status_code == 503
    assert seen == []
    assert client.get("/health").status_code == 200


def test_logs_and_errors_do_not_echo_content(provider, monkeypatch):
    entries = []
    monkeypatch.setattr("app.boundary.logger.info", entries.append)
    response = ask("Explain a list using PRIVATE-LEARNER-CONTENT as an example")
    assert response.status_code == 200
    assert response.json()["trace_id"] == response.headers["x-request-id"]
    text = "\n".join(entries)
    for secret in ["test-key", "private-provider-key", "PRIVATE-LEARNER-CONTENT"]:
        assert secret not in text
    invalid = client.post("/ask", json={"question": "short", "level": "private-invalid-value"})
    assert invalid.status_code == 422
    assert "private-invalid-value" not in invalid.text


def test_large_body_is_rejected_before_provider(provider):
    _, seen, _ = provider
    assert ask("x" * 17000).status_code == 413
    assert seen == []


def test_usage_logs_unknown_cost_without_rates(provider, monkeypatch):
    entries = []
    monkeypatch.setattr("app.telemetry.logger.info", entries.append)
    response = SimpleNamespace(usage=SimpleNamespace(input_tokens=100, output_tokens=20))
    record_usage(response, "test-model", "test-trace")
    entry = json.loads(entries[0])
    assert entry["input_tokens"] == 100
    assert entry["estimated_token_cost_usd"] is None


def test_usage_estimate_is_explicitly_partial(provider, monkeypatch):
    for name, value in {
        "TUTOR_PRICE_BASIS": "synthetic test rates, not provider pricing",
        "TUTOR_INPUT_USD_PER_MILLION": "1", "TUTOR_CACHED_INPUT_USD_PER_MILLION": "0.5",
        "TUTOR_OUTPUT_USD_PER_MILLION": "2",
    }.items():
        monkeypatch.setenv(name, value)
    entries = []
    monkeypatch.setattr("app.telemetry.logger.info", entries.append)
    response = SimpleNamespace(usage=SimpleNamespace(input_tokens=100, output_tokens=20))
    record_usage(response, "test-model", "test-trace")
    entry = json.loads(entries[0])
    assert entry["estimated_token_cost_usd"] == "0.00014"
    assert entry["tool_fees_included"] is False
