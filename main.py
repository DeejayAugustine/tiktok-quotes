"""TikTok Daily Quote Automation — pipeline entry point."""

import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

import src.history as history_store
from src.emailer import send_daily_videos
from src.quote_fetcher import fetch_quote
from src.tiktok_poster import post_video
from src.video_composer import compose_video
from src.video_fetcher import fetch_video

load_dotenv()

VIDEOS_PER_DAY = 3


def main() -> int:
    run_id = str(uuid.uuid4())[:8]
    output_dir = Path("output") / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Run ID: {run_id}  →  output: {output_dir}")

    history = history_store.load()
    print(f"History: {len(history['quotes'])} quotes used, {len(history['videos'])} videos used\n")

    video_paths = []
    quotes = []

    for i in range(1, VIDEOS_PER_DAY + 1):
        print(f"{'=' * 50}")
        print(f"  Generating video {i} of {VIDEOS_PER_DAY}")
        print(f"{'=' * 50}")

        # 1. Fetch quote
        print(f"\n[{i}.1] Fetching quote...")
        quote = fetch_quote(history)
        print(f"  \"{quote['content']}\" — {quote['author']}")

        # 2. Download background video
        print(f"\n[{i}.2] Fetching background video...")
        video_path, video_id = fetch_video(str(output_dir), history)

        # 3. Compose video
        print(f"\n[{i}.3] Composing video...")
        final_video = compose_video(video_path, quote, str(output_dir), index=i)

        # Record immediately so next iteration won't reuse the same quote/video
        history_store.record(history, quote["content"], video_id)

        video_paths.append(final_video)
        quotes.append(quote)
        print()

    # 4. Email all 3 videos
    print(f"{'=' * 50}")
    print("Sending email...")
    send_daily_videos(video_paths, quotes)

    # 5. Post to TikTok (stub mode unless credentials set)
    print("\nTikTok posting...")
    for final_video, quote in zip(video_paths, quotes):
        post_video(final_video, quote)

    # Save history after full success
    history_store.save(history)

    print(f"\nDone! {len(video_paths)} videos in: {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
