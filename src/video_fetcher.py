"""Fetch a random portrait background video from Pexels."""

import os
import random
import requests


PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"
MAX_ATTEMPTS = 5

SEARCH_QUERIES = [
    "mountains",
    "ocean waves",
    "forest",
    "waterfall",
    "meadow sunrise",
    "desert dunes",
    "river",
    "night sky stars",
    "city",
    "snow nature",
]


def fetch_video(output_path: str, history: dict) -> tuple[str, int]:
    """Download a random unused portrait video to output_path/background.mp4.

    Args:
        output_path: Directory where the video will be saved.
        history: History dict used to skip already-used video IDs.

    Returns:
        (absolute path to downloaded file, pexels video id)

    Raises:
        RuntimeError: if no suitable unused video is found or download fails.
    """
    from src.history import video_seen

    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        raise RuntimeError("PEXELS_API_KEY environment variable is not set")

    headers = {"Authorization": api_key}

    for attempt in range(1, MAX_ATTEMPTS + 1):
        query = random.choice(SEARCH_QUERIES)
        params = {
            "query": query,
            "per_page": 15,
            "orientation": "portrait",
            "size": "medium",
        }

        resp = requests.get(PEXELS_VIDEO_URL, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        videos = resp.json().get("videos", [])

        if not videos:
            continue

        # Filter out already-used video IDs
        fresh = [v for v in videos if not video_seen(history, v["id"])]
        if not fresh:
            print(f"  All videos for {query!r} already used, retrying ({attempt}/{MAX_ATTEMPTS})...")
            continue

        video = random.choice(fresh)

        # Prefer portrait files (height > width), then pick highest resolution
        all_files = video.get("video_files", [])
        portrait_files = [f for f in all_files if f.get("height", 0) > f.get("width", 0)]
        candidates = portrait_files if portrait_files else all_files
        video_files = sorted(candidates, key=lambda f: f.get("height", 0), reverse=True)
        if not video_files:
            continue

        video_url = video_files[0]["link"]
        dest = os.path.join(output_path, "background.mp4")

        print(f"Downloading video #{video['id']}: {query!r} → {video_url[:60]}...")
        with requests.get(video_url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 16):
                    f.write(chunk)

        return dest, video["id"]

    raise RuntimeError(f"Could not find an unused video after {MAX_ATTEMPTS} attempts")
