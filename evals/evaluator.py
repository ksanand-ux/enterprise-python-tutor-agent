def evaluate_response(scenario, answer, sources):
    answer_lower = answer.lower()

    terms_present = all(
        term.lower() in answer_lower
        for term in scenario["expected_terms"]
    )

    source_domain_present = any(
        scenario["expected_source_domain"] in source.get("url", "")
        for source in sources
    )

    citation_requirement_met = (
        not scenario["requires_citation"] or bool(sources)
    )

    source_requirement_met = (
        not scenario["requires_citation"] or source_domain_present
    )

    checks = {
        "terms_present": terms_present,
        "source_requirement_met": source_requirement_met,
        "citation_requirement_met": citation_requirement_met,
    }

    return {
        "scenario_id": scenario["id"],
        "passed": all(checks.values()),
        "checks": checks,
    }
