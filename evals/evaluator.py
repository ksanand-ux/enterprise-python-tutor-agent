from urllib.parse import urlsplit


def is_expected_source(url, expected_domain):
    """Accept only HTTPS URLs on the exact expected host."""
    if not isinstance(url, str) or not url:
        return False
    if any(character.isspace() or ord(character) < 32 for character in url):
        return False

    try:
        parsed = urlsplit(url)
        return (
            parsed.scheme == "https"
            and parsed.hostname == expected_domain.lower()
            and parsed.username is None
            and parsed.password is None
            and parsed.port in (None, 443)
        )
    except ValueError:
        return False


def evaluate_response(scenario, answer, sources):
    answer_lower = answer.lower()

    if "expected_term_groups" in scenario:
        terms_present = all(
            any(
                term.lower() in answer_lower
                for term in group
            )
            for group in scenario["expected_term_groups"]
        )
    else:
        terms_present = all(
            term.lower() in answer_lower
            for term in scenario["expected_terms"]
        )

    forbidden_terms_absent = all(
        term.lower() not in answer_lower
        for term in scenario.get("forbidden_terms", [])
    )

    sources_are_official = bool(sources) and all(
        is_expected_source(
            source.get("url", ""),
            scenario["expected_source_domain"],
        )
        for source in sources
    )

    citation_requirement_met = (
        not scenario["requires_citation"] or bool(sources)
    )

    source_requirement_met = (
        not scenario["requires_citation"] or sources_are_official
    )

    checks = {
        "terms_present": terms_present,
        "forbidden_terms_absent": forbidden_terms_absent,
        "source_requirement_met": source_requirement_met,
        "citation_requirement_met": citation_requirement_met,
    }

    return {
        "scenario_id": scenario["id"],
        "category": scenario["category"],
        "passed": all(checks.values()),
        "checks": checks,
    }
