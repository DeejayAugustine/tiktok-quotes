"""Fetch a fresh (unused) inspirational quote from ZenQuotes.io."""

import requests


ZENQUOTES_URL = "https://zenquotes.io/api/random"
MAX_ATTEMPTS = 10


def fetch_quote(history: dict) -> dict:
    """Return a dict with 'content' and 'author' that hasn't been used before.

    Retries up to MAX_ATTEMPTS times to find an unused quote.

    Raises:
        RuntimeError: if all attempts return already-used quotes.
    """
    from src.history import quote_seen

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.get(ZENQUOTES_URL, timeout=10)
            resp.raise_for_status()
            data = resp.json()[0]
            quote = {"content": data["q"], "author": data["a"]}

            if not quote_seen(history, quote["content"]):
                return quote

            print(f"  Quote already used, retrying ({attempt}/{MAX_ATTEMPTS})...")
        except Exception as e:
            raise RuntimeError(f"Failed to fetch quote from ZenQuotes: {e}")

    raise RuntimeError(f"Could not find an unused quote after {MAX_ATTEMPTS} attempts")
