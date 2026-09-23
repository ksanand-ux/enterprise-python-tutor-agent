import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def fail_if_called(*args, **kwargs):
    raise AssertionError("Rejected requests must stop before tutor logic")


@pytest.mark.parametrize(
    "expected_key, headers, expected_status",
    [
        (None, {}, 503),
        ("test-tutor-key", {}, 403),
        ("test-tutor-key", {"X-Tutor-Key": "wrong-key"}, 403),
    ],
)
def test_access_is_rejected(
    monkeypatch, expected_key, headers, expected_status
):
    if expected_key is None:
        monkeypatch.delenv("TUTOR_ACCESS_KEY", raising=False)
    else:
        monkeypatch.setenv("TUTOR_ACCESS_KEY", expected_key)

    monkeypatch.setattr("app.main.check_request", fail_if_called)
    monkeypatch.setattr("app.main.OpenAI", fail_if_called)

    response = client.post(
        "/ask",
        headers=headers,
        json={
            "question": "What is a Python list?",
            "level": "beginner",
        },
    )

    assert response.status_code == expected_status
