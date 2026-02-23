"""Compose the final 1080x1920 TikTok video using FFmpeg + Pillow."""

import os
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# Canvas dimensions
W, H = 1080, 1920
FONT_DIR = Path(__file__).parent.parent / "assets" / "fonts"


def _make_text_overlay(quote: dict, output_path: str) -> str:
    """Render a transparent PNG with quote text and semi-transparent backdrop.

    Returns the path to the generated PNG.
    """
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_path = str(FONT_DIR / "Montserrat-Bold.ttf")

    # ── Quote text ────────────────────────────────────────────────────────────
    quote_font_size = 68
    quote_font = ImageFont.truetype(font_path, quote_font_size)

    # Author text (smaller + slightly dimmer)
    author_font_size = 46
    author_font = ImageFont.truetype(font_path, author_font_size)

    # Word-wrap
    lines = textwrap.wrap(quote["content"], width=28)
    author_line = f"— {quote['author']}"

    line_spacing = 14
    total_quote_h = sum(
        draw.textbbox((0, 0), line, font=quote_font)[3] for line in lines
    ) + line_spacing * (len(lines) - 1)
    author_bbox = draw.textbbox((0, 0), author_line, font=author_font)
    author_h = author_bbox[3] - author_bbox[1]

    gap = 24  # gap between quote and author
    padding_x, padding_y = 60, 50
    block_h = total_quote_h + gap + author_h

    # Center the block at 38% down the frame
    center_y = int(H * 0.38)
    box_top = center_y - block_h // 2 - padding_y
    box_bottom = center_y + block_h // 2 + padding_y
    box_left = 60
    box_right = W - 60

    # ── Semi-transparent rounded rectangle ───────────────────────────────────
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.rounded_rectangle(
        [(box_left, box_top), (box_right, box_bottom)],
        radius=32,
        fill=(0, 0, 0, int(255 * 0.65)),
    )
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # ── Draw quote lines ──────────────────────────────────────────────────────
    y = center_y - block_h // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=quote_font)
        line_w = bbox[2] - bbox[0]
        x = (W - line_w) // 2
        # Shadow
        draw.text((x + 2, y + 2), line, font=quote_font, fill=(0, 0, 0, 160))
        draw.text((x, y), line, font=quote_font, fill=(255, 255, 255, 255))
        y += (bbox[3] - bbox[1]) + line_spacing

    # ── Draw author ───────────────────────────────────────────────────────────
    y += gap
    abbox = draw.textbbox((0, 0), author_line, font=author_font)
    ax = (W - (abbox[2] - abbox[0])) // 2
    draw.text((ax + 2, y + 2), author_line, font=author_font, fill=(0, 0, 0, 140))
    draw.text((ax, y), author_line, font=author_font, fill=(220, 220, 220, 230))

    dest = os.path.join(output_path, "text_overlay.png")
    img.save(dest, "PNG")
    return dest


def compose_video(
    video_path: str,
    audio_path: str,
    duration: float,
    quote: dict,
    output_path: str,
) -> str:
    """Compose the final TikTok-ready MP4.

    Steps:
      1. Generate Pillow text overlay PNG.
      2. Run FFmpeg: blurred-bg + centered fg + text layer + audio → output.

    Returns:
        Path to the final tiktok_final.mp4.
    """
    overlay_path = _make_text_overlay(quote, output_path)
    dest = os.path.join(output_path, "tiktok_final.mp4")

    # Add 1-second buffer so audio doesn't cut off abruptly
    total_duration = duration + 1.0

    filter_complex = (
        "[0:v] split=2 [bg_in][fg_in];"
        "[bg_in] scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,gblur=sigma=30 [bg];"
        "[fg_in] scale=1080:-2 [fg];"
        "[bg][fg] overlay=0:(H-h)/2 [composed];"
        "[composed][1:v] overlay=0:0 [video_out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", video_path,            # input 0: background video (looped)
        "-i", overlay_path,           # input 1: text overlay PNG
        "-i", audio_path,             # input 2: narration audio
        "-filter_complex", filter_complex,
        "-map", "[video_out]",
        "-map", "2:a",
        "-t", str(total_duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        dest,
    ]

    print("Running FFmpeg composition...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed:\n{result.stderr[-2000:]}")

    size_mb = os.path.getsize(dest) / (1024 * 1024)
    print(f"Video saved: {dest} ({size_mb:.1f} MB, {total_duration:.1f}s)")
    return dest
