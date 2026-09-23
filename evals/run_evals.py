import argparse
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi.testclient import TestClient

from app.main import app
from evals.evaluator import evaluate_response
from evals.scenarios import SCENARIOS


load_dotenv(dotenv_path=".env")
client = TestClient(app)


def run_evaluations(limit):
    tutor_key = os.getenv("TUTOR_ACCESS_KEY")

    if not tutor_key:
        raise RuntimeError(
            "Set TUTOR_ACCESS_KEY before running evaluations"
        )

    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    model = os.getenv("OPENAI_MODEL", "gpt-5.6")
    results = []

    for scenario in SCENARIOS[:limit]:
        request_started = time.perf_counter()

        response = client.post(
            "/ask",
            headers={"X-Tutor-Key": tutor_key},
            json={
                "question": scenario["question"],
                "level": scenario["level"],
            },
        )

        latency_ms = round(
            (time.perf_counter() - request_started) * 1000,
            2,
        )

        if response.status_code == 200:
            body = response.json()

            eval_result = evaluate_response(
                scenario=scenario,
                answer=body["answer"],
                sources=body["sources"],
            )

            result = {
                "scenario_id": scenario["id"],
                "category": scenario["category"],
                "http_status": response.status_code,
                "success": eval_result["passed"],
                "trace_id": body["trace_id"],
                "model": model,
                "latency_ms": latency_ms,
                "tokens": None,
                "estimated_cost_usd": None,
                "final_answer": body["answer"],
                "sources": body["sources"],
                "activity": body["activity"],
                "eval_result": eval_result,
            }
        else:
            result = {
                "scenario_id": scenario["id"],
                "category": scenario["category"],
                "http_status": response.status_code,
                "success": False,
                "trace_id": None,
                "model": model,
                "latency_ms": latency_ms,
                "tokens": None,
                "estimated_cost_usd": None,
                "error": response.json(),
            }

        results.append(result)

        print(
            scenario["id"],
            "PASS" if result["success"] else "FAIL",
            f"{latency_ms} ms",
        )

    passed = sum(result["success"] for result in results)

    report = {
        "run_id": run_id,
        "started_at_utc": started_at,
        "model": model,
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round(passed / len(results), 4),
        "results": results,
    }

    Path("reports").mkdir(exist_ok=True)
    report_path = Path("reports") / f"eval-{run_id}.json"
    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(f"Report saved: {report_path}")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        choices=range(1, 16),
    )
    arguments = parser.parse_args(argv)
    report = run_evaluations(arguments.limit)
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
