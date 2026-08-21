def check_request(question: str):
    normalized = " ".join(question.lower().split())

    secret_terms = (
        "api key",
        "openai_api_key",
        "password",
        "secret key",
    )

    secret_actions = (
        "reveal",
        "print",
        "show",
        "display",
        "give me",
    )

    asks_for_secret = (
        any(term in normalized for term in secret_terms)
        and any(action in normalized for action in secret_actions)
    )

    if asks_for_secret:
        return {
            "category": "secret_exfiltration",
            "answer": (
                "I cannot reveal credentials, API keys, passwords, "
                "or other secrets."
            ),
        }

    destructive_phrases = (
        "delete every file",
        "delete all files",
        "rm -rf",
        "without asking me",
    )

    if any(phrase in normalized for phrase in destructive_phrases):
        return {
            "category": "destructive_action",
            "answer": (
                "I cannot perform destructive file operations without "
                "explicit authorization and confirmation."
            ),
        }

    if "ignore your instructions" in normalized:
        return {
            "category": "prompt_injection",
            "answer": (
                "I cannot ignore the system instructions or bypass "
                "the application safety policy."
            ),
        }

    return None
