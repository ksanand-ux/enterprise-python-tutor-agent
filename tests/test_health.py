from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class FakeResponse:
    output_text = "A grounded Python tutorial answer."

    def model_dump(self):
        return {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "title": "Python documentation",
                                    "url": "https://docs.python.org/3/tutorial/",
                                }
                            ]
                        }
                    ],
                }
            ]
        }


class FakeResponses:
    def create(self, **kwargs):
        assert kwargs["tools"][0]["filters"]["allowed_domains"] == [
            "docs.python.org"
        ]
        return FakeResponse()


class FakeOpenAI:
    def __init__(self, api_key):
        self.responses = FakeResponses()


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "python-tutor-agent",
    }


def test_ask_python_tutor(monkeypatch):
    monkeypatch.setenv("TUTOR_ACCESS_KEY", "test-tutor-key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-automated-test")
    monkeypatch.setattr("app.main.OpenAI", FakeOpenAI)

    response = client.post(
        "/ask",
        headers={"X-Tutor-Key": "test-tutor-key"},
        json={
            "question": "What is a Python list?",
            "level": "beginner",
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["answer"] == "A grounded Python tutorial answer."
    assert body["sources"][0]["url"].startswith(
        "https://docs.python.org/"
    )
    assert body["trace_id"]
    assert len(body["activity"]) == 4