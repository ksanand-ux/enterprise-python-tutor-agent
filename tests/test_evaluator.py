import pytest

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


@pytest.mark.parametrize(
    "url",
    [
        "https://docs.python.org/3/tutorial/",
        "https://DOCS.PYTHON.ORG/3/?utm_source=openai",
        "https://docs.python.org:443/3/#lists",
    ],
)
def test_official_https_sources_pass(url):
    result = evaluate_response(
        SCENARIOS[0], "Use append.", [{"url": url}]
    )
    assert result["passed"] is True


@pytest.mark.parametrize(
    "url",
    [
        "https://docs.python.org.evil.example/3/",
        "https://notdocs.python.org/3/",
        "https://evil.example/docs.python.org",
        "https://evil.example/?source=docs.python.org",
        "https://docs.python.org@evil.example/3/",
        "https://user:password@docs.python.org/3/",
        "http://docs.python.org/3/",
        "//docs.python.org/3/",
        "https://docs.python.org:8443/3/",
        "https://docs.python.org:invalid/3/",
        "https://[docs.python.org/3/",
        "https://docs.py\nthon.org/3/",
        "",
        None,
    ],
)
def test_misleading_or_invalid_sources_fail(url):
    result = evaluate_response(
        SCENARIOS[0], "Use append.", [{"url": url}]
    )
    assert result["checks"]["source_requirement_met"] is False
    assert result["passed"] is False


def test_one_official_source_does_not_hide_an_untrusted_source():
    result = evaluate_response(
        SCENARIOS[0],
        "Use append.",
        [
            {"url": "https://docs.python.org/3/"},
            {"url": "https://evil.example/?source=docs.python.org"},
        ],
    )
    assert result["checks"]["source_requirement_met"] is False
    assert result["passed"] is False
