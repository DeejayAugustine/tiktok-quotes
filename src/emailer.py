"""Send daily videos via SendGrid."""

import base64
import os
from pathlib import Path

import requests


SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


def send_daily_videos(video_paths: list[str], quotes: list[dict]) -> bool:
    """Email up to 3 videos as attachments via SendGrid.

    Returns True on success, False if SendGrid env vars are not configured.
    """
    api_key = os.environ.get("SENDGRID_API_KEY")
    to_email = os.environ.get("TO_EMAIL")
    from_email = os.environ.get("FROM_EMAIL", to_email)  # sender = recipient by default

    if not all([api_key, to_email]):
        print(
            "\nSendGrid not configured — skipping email delivery.\n"
            "Add SENDGRID_API_KEY and TO_EMAIL secrets to enable.\n"
        )
        return False

    attachments = []
    for path in video_paths:
        data = Path(path).read_bytes()
        attachments.append({
            "content": base64.b64encode(data).decode(),
            "type": "video/mp4",
            "filename": Path(path).name,
            "disposition": "attachment",
        })

    total_mb = sum(len(a["content"]) * 3 / 4 / 1024 / 1024 for a in attachments)
    print(f"Sending email with {len(attachments)} attachments ({total_mb:.1f} MB total)...")

    if total_mb > 28:
        print("Warning: attachments exceed 28 MB — splitting into individual emails.")
        return _send_individual_emails(api_key, from_email, to_email, video_paths, quotes)

    body = _build_body(quotes)
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email},
        "subject": f"Your {len(video_paths)} TikTok videos for today",
        "content": [{"type": "text/plain", "value": body}],
        "attachments": attachments,
    }

    resp = requests.post(
        SENDGRID_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )

    if resp.status_code in (200, 202):
        print(f"Email sent to {to_email}")
        return True

    raise RuntimeError(f"SendGrid error {resp.status_code}: {resp.text[:300]}")


def _send_individual_emails(
    api_key: str,
    from_email: str,
    to_email: str,
    video_paths: list[str],
    quotes: list[dict],
) -> bool:
    """Fallback: send one email per video when total size exceeds limit."""
    for i, (path, quote) in enumerate(zip(video_paths, quotes), 1):
        data = Path(path).read_bytes()
        attachment = {
            "content": base64.b64encode(data).decode(),
            "type": "video/mp4",
            "filename": Path(path).name,
            "disposition": "attachment",
        }
        body = f"Video {i} of {len(video_paths)}\n\n\"{quote['content']}\" — {quote['author']}"
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": from_email},
            "subject": f"TikTok video {i}/{len(video_paths)} — {quote['author']}",
            "content": [{"type": "text/plain", "value": body}],
            "attachments": [attachment],
        }
        resp = requests.post(
            SENDGRID_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        if resp.status_code not in (200, 202):
            raise RuntimeError(f"SendGrid error on video {i}: {resp.status_code} {resp.text[:300]}")
        print(f"  Email {i}/{len(video_paths)} sent")

    return True


def _build_body(quotes: list[dict]) -> str:
    lines = ["Here are your TikTok videos for today:\n"]
    for i, q in enumerate(quotes, 1):
        lines.append(f"{i}. \"{q['content']}\" — {q['author']}")
    lines.append("\nUpload, add your music, and post!")
    return "\n".join(lines)
