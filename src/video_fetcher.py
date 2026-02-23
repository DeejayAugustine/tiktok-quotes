"""Fetch a random portrait background video from Pexels."""

import os
import random
import requests


PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"

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


def fetch_video(output_path: str) -> str:
    """Download a random landscape video to output_path/background.mp4.

    Args:
        output_path: Directory where the video will be saved.

    Returns:
        Absolute path to the downloaded file.

    Raises:
        RuntimeError: if no suitable video is found or download fails.
    """
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        raise RuntimeError("PEXELS_API_KEY environment variable is not set")

    query = random.choice(SEARCH_QUERIES)
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "per_page": 15,
        "orientation": "portrait",
        "size": "medium",
    }

    resp = requests.get(PEXELS_VIDEO_URL, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    videos = data.get("videos", [])
    if not videos:
        raise RuntimeError(f"No videos returned for query: {query!r}")

    video = random.choice(videos)

    # Prefer portrait files (height > width), then pick highest resolution
    all_files = video.get("video_files", [])
    portrait_files = [f for f in all_files if f.get("height", 0) > f.get("width", 0)]
    candidates = portrait_files if portrait_files else all_files
    video_files = sorted(candidates, key=lambda f: f.get("height", 0), reverse=True)
    if not video_files:
        raise RuntimeError("Selected Pexels video has no downloadable files")

    video_url = video_files[0]["link"]
    dest = os.path.join(output_path, "background.mp4")

    print(f"Downloading video: {query!r} → {video_url[:60]}...")
    with requests.get(video_url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                f.write(chunk)

    return dest
