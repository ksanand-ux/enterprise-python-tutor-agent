import json
from datetime import datetime, timezone
from pathlib import Path

from evals.evaluator import evaluate_response
from evals.scenarios import SCENARIOS


report_paths = [
    path
    for path in Path("reports").glob("eval-*.json")
    if "rechecked" not in path.stem
]

report_path = max(
    report_paths,
    key=lambda path: path.stat().st_mtime,
)

report = json.loads(report_path.read_text())
scenarios_by_id = {
    scenario["id"]: scenario
    for scenario in SCENARIOS
}

for result in report["results"]:
    if result["http_status"] != 200:
        continue

    scenario = scenarios_by_id[result["scenario_id"]]

    eval_result = evaluate_response(
        scenario=scenario,
        answer=result["final_answer"],
        sources=result["sources"],
    )

    result["eval_result"] = eval_result
    result["success"] = eval_result["passed"]

passed = sum(result["success"] for result in report["results"])

report["passed"] = passed
report["failed"] = len(report["results"]) - passed
report["pass_rate"] = round(
    passed / len(report["results"]),
    4,
)
report["rechecked_at_utc"] = datetime.now(
    timezone.utc
).isoformat()

output_path = report_path.with_name(
    f"{report_path.stem}-rechecked.json"
)

output_path.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

print(
    f"{report['passed']}/{report['total']} passed"
)
print(f"Rechecked report saved: {output_path}")
