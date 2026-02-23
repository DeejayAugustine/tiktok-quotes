"""Send daily videos via SendGrid — one email per video."""

import base64
import os
from pathlib import Path

import requests


SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


def send_daily_videos(video_paths: list[str], quotes: list[dict]) -> bool:
    """Send one email per video as an attachment via SendGrid.

    Returns True on success, False if SendGrid env vars are not configured.
    """
    api_key = os.environ.get("SENDGRID_API_KEY")
    to_email = os.environ.get("TO_EMAIL")
    from_email = os.environ.get("FROM_EMAIL") or to_email

    if not all([api_key, to_email]):
        print(
            "\nSendGrid not configured — skipping email delivery.\n"
            "Add SENDGRID_API_KEY and TO_EMAIL secrets to enable.\n"
        )
        return False

    total = len(video_paths)
    for i, (path, quote) in enumerate(zip(video_paths, quotes), 1):
        _send_one(api_key, from_email, to_email, path, quote, i, total)

    print(f"All {total} emails sent to {to_email}")
    return True


def _send_one(
    api_key: str,
    from_email: str,
    to_email: str,
    video_path: str,
    quote: dict,
    index: int,
    total: int,
) -> None:
    data = Path(video_path).read_bytes()
    size_mb = len(data) / 1024 / 1024
    print(f"  Sending video {index}/{total} ({size_mb:.1f} MB)...")

    body = (
        f"Video {index} of {total} — ready to upload!\n\n"
        f"\"{quote['content']}\" — {quote['author']}\n\n"
        "Add your music in TikTok and post."
    )

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email},
        "subject": f"TikTok video {index}/{total} — {quote['author']}",
        "content": [{"type": "text/plain", "value": body}],
        "attachments": [{
            "content": base64.b64encode(data).decode(),
            "type": "video/mp4",
            "filename": Path(video_path).name,
            "disposition": "attachment",
        }],
    }

    resp = requests.post(
        SENDGRID_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )

    if resp.status_code not in (200, 202):
        raise RuntimeError(
            f"SendGrid error on video {index}: {resp.status_code} {resp.text[:300]}"
        )
