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


