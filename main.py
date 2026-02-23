"""TikTok Daily Quote Automation — pipeline entry point."""

import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

from src.audio_generator import generate_audio
from src.quote_fetcher import fetch_quote
from src.tiktok_poster import post_video
from src.video_composer import compose_video
from src.video_fetcher import fetch_video

load_dotenv()


def main() -> int:
    run_id = str(uuid.uuid4())[:8]
    output_dir = Path("output") / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Run ID: {run_id}  →  output: {output_dir}")

    # 1. Fetch quote
    print("\n[1/5] Fetching quote...")
    quote = fetch_quote()
    print(f"  \"{quote['content']}\" — {quote['author']}")

    # 2. Download background video
    print("\n[2/5] Fetching background video...")
    video_path = fetch_video(str(output_dir))

    # 3. Generate narration
    print("\n[3/5] Generating narration audio...")
    audio_path, duration = generate_audio(quote, str(output_dir))

    # 4. Compose TikTok video
    print("\n[4/5] Composing video...")
    final_video = compose_video(video_path, audio_path, duration, quote, str(output_dir))

    # 5. Post to TikTok
    print("\n[5/5] Posting to TikTok...")
    posted = post_video(final_video, quote)

    print(f"\nDone! Final video: {final_video}")
    if not posted:
        print("(Stub mode — inspect the video locally)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
