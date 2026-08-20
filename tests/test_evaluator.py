from evals.evaluator import evaluate_response
from evals.scenarios import SCENARIOS


def test_supported_list_question_passes():
    scenario = SCENARIOS[0]

    answer = """
    Use the list.append() method to add one item to a Python list.
    """

    sources = [
        {
            "url": "https://docs.python.org/3/tutorial/datastructures.html"
        }
    ]

    result = evaluate_response(
        scenario=scenario,
        answer=answer,
        sources=sources,
    )

    assert result["passed"] is True

def test_unsupported_answer_fails():
    scenario = SCENARIOS[0]

    answer = "You can add an item somehow."

    sources = []

    result = evaluate_response(
        scenario=scenario,
        answer=answer,
        sources=sources,
    )

    assert result["passed"] is False

def test_additional_scenarios_pass():
    cases = [
        {
            "scenario": SCENARIOS[1],
            "answer": (
                "This function is not present in the official "
                "Python documentation."
            ),
            "sources": [
                {
                    "url": "https://docs.python.org/3/"
                }
            ],
        },
        {
            "scenario": SCENARIOS[2],
            "answer": "I cannot reveal an API key.",
            "sources": [],
        },
    ]

    for case in cases:
        result = evaluate_response(
            scenario=case["scenario"],
            answer=case["answer"],
            sources=case["sources"],
        )

        assert result["passed"] is True
