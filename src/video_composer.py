"""Compose the final 1080x1920 TikTok video using FFmpeg + Pillow."""

import os
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# Canvas dimensions
W, H = 1080, 1920
FONT_DIR = Path(__file__).parent.parent / "assets" / "fonts"

# Video duration in seconds (no narration — fixed length)
VIDEO_DURATION = 20


def _make_text_overlay(quote: dict, output_path: str, index: int = 1) -> str:
    """Render a transparent PNG with quote text and semi-transparent backdrop.

    Returns the path to the generated PNG.
    """
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_path = str(FONT_DIR / "Montserrat-Bold.ttf")

    # ── Font sizes ────────────────────────────────────────────────────────────
    quote_font_size = 58
    quote_font = ImageFont.truetype(font_path, quote_font_size)

    author_font_size = 40
    author_font = ImageFont.truetype(font_path, author_font_size)

    # ── Word-wrap to fit safely inside the box ────────────────────────────────
    # Available text width = canvas - box margins (120px each side) - inner padding (80px each side)
    # Box spans x: 120 to 960 = 840px wide; inner text area = 840 - 160 = 680px
    max_text_w = 680
    lines = _wrap_to_width(draw, quote["content"], quote_font, max_text_w)
    author_line = f"— {quote['author']}"

    line_spacing = 16
    line_heights = [draw.textbbox((0, 0), l, font=quote_font)[3] for l in lines]
    total_quote_h = sum(line_heights) + line_spacing * (len(lines) - 1)

    author_bbox = draw.textbbox((0, 0), author_line, font=author_font)
    author_h = author_bbox[3] - author_bbox[1]

    gap = 28
    pad_x, pad_y = 80, 60   # padding between text block and box edges
    block_h = total_quote_h + gap + author_h

    # Center the block at 38% down the frame
    center_y = int(H * 0.38)
    box_top    = center_y - block_h // 2 - pad_y
    box_bottom = center_y + block_h // 2 + pad_y
    box_left   = 120
    box_right  = W - 120

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
    for line, lh in zip(lines, line_heights):
        bbox = draw.textbbox((0, 0), line, font=quote_font)
        line_w = bbox[2] - bbox[0]
        x = (W - line_w) // 2
        draw.text((x + 2, y + 2), line, font=quote_font, fill=(0, 0, 0, 160))
        draw.text((x, y), line, font=quote_font, fill=(255, 255, 255, 255))
        y += lh + line_spacing

    # ── Draw author ───────────────────────────────────────────────────────────
    y += gap
    abbox = draw.textbbox((0, 0), author_line, font=author_font)
    ax = (W - (abbox[2] - abbox[0])) // 2
    draw.text((ax + 2, y + 2), author_line, font=author_font, fill=(0, 0, 0, 140))
    draw.text((ax, y), author_line, font=author_font, fill=(220, 220, 220, 230))

    dest = os.path.join(output_path, f"text_overlay_{index}.png")
    img.save(dest, "PNG")
    return dest


def _wrap_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    """Word-wrap text so no line exceeds max_w pixels."""
    words = text.split()
    lines = []
    current = []

    for word in words:
        test = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_w:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]

    if current:
        lines.append(" ".join(current))

    return lines


def compose_video(
    video_path: str,
    quote: dict,
    output_path: str,
    index: int = 1,
) -> str:
    """Compose the final TikTok-ready MP4 (no audio).

    Steps:
      1. Generate Pillow text overlay PNG.
      2. Run FFmpeg: blurred-bg + centered fg + text layer → output.

    Returns:
        Path to the final tiktok_final.mp4.
    """
    overlay_path = _make_text_overlay(quote, output_path, index)
    dest = os.path.join(output_path, f"tiktok_video_{index}.mp4")

    # Scale portrait video to fill 1080x1920, crop any overflow, then overlay text
    filter_complex = (
        "[0:v] scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920 [bg];"
        "[bg][1:v] overlay=0:0 [video_out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", video_path,       # input 0: background video (looped)
        "-i", overlay_path,     # input 1: text overlay PNG
        "-filter_complex", filter_complex,
        "-map", "[video_out]",
        "-t", str(VIDEO_DURATION),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "26",
        "-maxrate", "2500k",    # hard bitrate cap keeps file under ~8 MB for 20s
        "-bufsize", "5000k",
        "-pix_fmt", "yuv420p",
        "-an",                  # no audio
        "-movflags", "+faststart",
        dest,
    ]

    print("Running FFmpeg composition...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed:\n{result.stderr[-2000:]}")

    size_mb = os.path.getsize(dest) / (1024 * 1024)
    print(f"Video saved: {dest} ({size_mb:.1f} MB, {VIDEO_DURATION}s)")
    return dest
