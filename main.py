"""TikTok Daily Quote Automation — pipeline entry point."""

import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

import src.history as history_store
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

    # Load history
    history = history_store.load()
    print(f"History: {len(history['quotes'])} quotes used, {len(history['videos'])} videos used\n")

    # 1. Fetch quote
    print("[1/4] Fetching quote...")
    quote = fetch_quote(history)
    print(f"  \"{quote['content']}\" — {quote['author']}")

    # 2. Download background video
    print("\n[2/4] Fetching background video...")
    video_path, video_id = fetch_video(str(output_dir), history)

    # 3. Compose TikTok video
    print("\n[3/4] Composing video...")
    final_video = compose_video(video_path, quote, str(output_dir))

    # 4. Post to TikTok
    print("\n[4/4] Posting to TikTok...")
    post_video(final_video, quote)

    # Save history only after everything succeeded
    history_store.record(history, quote["content"], video_id)
    history_store.save(history)

    print(f"\nDone! Final video: {final_video}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
