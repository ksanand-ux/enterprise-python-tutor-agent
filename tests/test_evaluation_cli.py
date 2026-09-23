import json

import pytest

from evals import run_evals


@pytest.mark.parametrize(
    "report, expected_exit",
    [
        ({"total": 1, "passed": 1, "failed": 0}, 0),
        ({"total": 2, "passed": 1, "failed": 1}, 1),
        ({"total": 1, "passed": 0, "failed": 1}, 1),
    ],
)
def test_cli_exit_status_matches_evaluation_outcome(
    monkeypatch, report, expected_exit
):
    limits = []

    def evaluate(limit):
        limits.append(limit)
        return report

    monkeypatch.setattr(run_evals, "run_evaluations", evaluate)

    assert run_evals.main(["--limit", "1"]) == expected_exit
    assert limits == [1]


@pytest.mark.parametrize("status_code", [200, 502])
def test_cli_preserves_failure_report_before_returning_nonzero(
    monkeypatch, tmp_path, status_code
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TUTOR_ACCESS_KEY", "local-test-key")

    class FakeResponse:
        def __init__(self):
            self.status_code = status_code

        def json(self):
            if status_code != 200:
                return {"detail": "Model request failed"}
            return {
                "answer": "An unsupported answer without sources.",
                "sources": [],
                "trace_id": "test-trace",
                "activity": [],
            }

    def post(path, headers, json):
        assert path == "/ask"
        assert headers == {"X-Tutor-Key": "local-test-key"}
        assert json["question"] == run_evals.SCENARIOS[0]["question"]
        return FakeResponse()

    monkeypatch.setattr(run_evals.client, "post", post)

    assert run_evals.main(["--limit", "1"]) == 1

    reports = list((tmp_path / "reports").glob("eval-*.json"))
    assert len(reports) == 1
    saved = json.loads(reports[0].read_text(encoding="utf-8"))
    assert saved["total"] == 1
    assert saved["failed"] == 1
    assert saved["results"][0]["http_status"] == status_code
    assert "local-test-key" not in reports[0].read_text(encoding="utf-8")
