import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@pytest.mark.parametrize(
    "payload",
    [
        {
            "question": "Hi",
            "level": "beginner",
        },
        {
            "question": "Explain Python lists.",
            "level": "unsupported-level",
        },
        {
            "question": "",
            "level": "advanced",
        },
    ],
)
def test_invalid_request_is_rejected(payload):
    response = client.post(
        "/ask",
        json=payload,
    )

    assert response.status_code == 422
