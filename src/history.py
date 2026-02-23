"""Track used quotes and video IDs to avoid repeats for 365 days."""

import json
from pathlib import Path


HISTORY_FILE = Path(__file__).parent.parent / "history.json"
MAX_ENTRIES = 365


def load() -> dict:
    """Load history from disk. Returns {'quotes': [...], 'videos': [...]}."""
    if not HISTORY_FILE.exists():
        return {"quotes": [], "videos": []}
    with open(HISTORY_FILE) as f:
        data = json.load(f)
    return {
        "quotes": data.get("quotes", []),
        "videos": data.get("videos", []),
    }


def save(history: dict) -> None:
    """Write history back to disk, trimming each list to MAX_ENTRIES."""
    trimmed = {
        "quotes": history["quotes"][-MAX_ENTRIES:],
        "videos": history["videos"][-MAX_ENTRIES:],
    }
    with open(HISTORY_FILE, "w") as f:
        json.dump(trimmed, f, indent=2)
    print(f"History saved: {len(trimmed['quotes'])} quotes, {len(trimmed['videos'])} videos tracked")


def quote_seen(history: dict, content: str) -> bool:
    return content in history["quotes"]


def video_seen(history: dict, video_id: int) -> bool:
    return video_id in history["videos"]


def record(history: dict, quote_content: str, video_id: int) -> None:
    """Append the used quote and video ID to history (in place)."""
    history["quotes"].append(quote_content)
    history["videos"].append(video_id)
