"""Fetch a random inspirational quote from ZenQuotes.io."""

import requests


ZENQUOTES_URL = "https://zenquotes.io/api/random"


def fetch_quote() -> dict:
    """Return a dict with 'content' and 'author' keys.

    Raises:
        RuntimeError: if the request fails.
    """
    try:
        resp = requests.get(ZENQUOTES_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()[0]
        return {"content": data["q"], "author": data["a"]}
    except Exception as e:
        raise RuntimeError(f"Failed to fetch a quote from ZenQuotes: {e}")
