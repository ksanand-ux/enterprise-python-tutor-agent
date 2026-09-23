import pytest


@pytest.fixture(autouse=True)
def isolate_configuration(monkeypatch):
    # Local .env must never change the deterministic test contract or call a model.
    import os
    for name in list(os.environ):
        if name.startswith("TUTOR_") or name in {"REDIS_URL", "OPENAI_API_KEY", "OPENAI_MODEL"}:
            monkeypatch.delenv(name, raising=False)

    def no_real_model(*args, **kwargs):
        raise AssertionError("Tests must explicitly inject a fake model client")

    monkeypatch.setattr("app.main.OpenAI", no_real_model)
