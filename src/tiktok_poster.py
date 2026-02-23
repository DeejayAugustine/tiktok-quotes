"""Post the finished video to TikTok via the Content Posting API.

Dual-mode:
  • All 3 env vars set  → full chunked upload flow
  • Any var missing    → print setup instructions and return False
                         (pipeline is still considered successful)
"""

import math
import os
import time

import requests


CHUNK_SIZE = 10 * 1024 * 1024   # 10 MB per chunk (TikTok minimum is 5 MB)
TIKTOK_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
TIKTOK_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"


def post_video(video_path: str, quote: dict) -> bool:
    """Upload video to TikTok.  Returns True on success, False in stub mode."""
    access_token = os.environ.get("TIKTOK_ACCESS_TOKEN")
    open_id = os.environ.get("TIKTOK_OPEN_ID")
    client_key = os.environ.get("TIKTOK_CLIENT_KEY")   # kept for future use

    if not all([access_token, open_id]):
        _print_stub_instructions()
        return False

    file_size = os.path.getsize(video_path)
    chunk_count = math.ceil(file_size / CHUNK_SIZE)

    caption = (
        f'"{quote["content"]}" — {quote["author"]}\n\n'
        "#motivation #quotes #dailyquote #inspirational #fyp"
    )

    # ── 1. Initialise upload ──────────────────────────────────────────────────
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    init_body = {
        "post_info": {
            "title": caption[:150],
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": file_size,
            "chunk_size": CHUNK_SIZE,
            "total_chunk_count": chunk_count,
        },
    }

    resp = requests.post(TIKTOK_INIT_URL, headers=headers, json=init_body, timeout=15)
    resp.raise_for_status()
    init_data = resp.json().get("data", {})
    publish_id = init_data.get("publish_id")
    upload_url = init_data.get("upload_url")

    if not publish_id or not upload_url:
        raise RuntimeError(f"TikTok init response missing fields: {resp.text}")

    print(f"TikTok upload initialised. publish_id={publish_id}")

    # ── 2. Upload chunks ──────────────────────────────────────────────────────
    with open(video_path, "rb") as f:
        for chunk_idx in range(chunk_count):
            chunk_data = f.read(CHUNK_SIZE)
            start = chunk_idx * CHUNK_SIZE
            end = start + len(chunk_data) - 1
            content_range = f"bytes {start}-{end}/{file_size}"

            put_headers = {
                "Content-Range": content_range,
                "Content-Length": str(len(chunk_data)),
                "Content-Type": "video/mp4",
            }
            put_resp = requests.put(
                upload_url,
                headers=put_headers,
                data=chunk_data,
                timeout=120,
            )
            put_resp.raise_for_status()
            print(f"  Chunk {chunk_idx + 1}/{chunk_count} uploaded ({content_range})")

    # ── 3. Poll publish status ────────────────────────────────────────────────
    status_body = {"publish_id": publish_id}
    for attempt in range(10):
        time.sleep(5)
        s_resp = requests.post(
            TIKTOK_STATUS_URL, headers=headers, json=status_body, timeout=15
        )
        s_resp.raise_for_status()
        status_data = s_resp.json().get("data", {})
        status = status_data.get("status", "UNKNOWN")
        print(f"  Status poll {attempt + 1}/10: {status}")
        if status == "PUBLISH_COMPLETE":
            print("TikTok post published successfully!")
            return True
        if status in ("FAILED", "SPAM_RISK_TOO_MANY_POSTS"):
            raise RuntimeError(f"TikTok publish failed: {status_data}")

    raise RuntimeError("TikTok publish timed out after polling")


def _print_stub_instructions():
    print(
        "\n"
        "╔══════════════════════════════════════════════════════════════════╗\n"
        "║  TikTok posting is in STUB MODE — video saved locally only.     ║\n"
        "║                                                                  ║\n"
        "║  To enable live posting, add these GitHub Secrets:              ║\n"
        "║    TIKTOK_ACCESS_TOKEN  — from your OAuth 2.0 flow              ║\n"
        "║    TIKTOK_OPEN_ID       — returned alongside access_token       ║\n"
        "║    TIKTOK_CLIENT_KEY    — from TikTok Developer Portal          ║\n"
        "║                                                                  ║\n"
        "║  See: https://developers.tiktok.com/doc/content-posting-api     ║\n"
        "╚══════════════════════════════════════════════════════════════════╝\n"
    )
