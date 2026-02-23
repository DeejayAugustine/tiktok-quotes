"""Generate TTS narration via ElevenLabs and measure its duration."""

import json
import os
import subprocess


DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"   # Sarah
DEFAULT_MODEL_ID = "eleven_turbo_v2_5"


def generate_audio(quote: dict, output_path: str) -> tuple[str, float]:
    """Synthesise speech for the quote and return (mp3_path, duration_seconds).

    Args:
        quote: dict with 'content' and 'author'.
        output_path: Directory where narration.mp3 will be saved.

    Returns:
        (absolute path to mp3, duration in seconds)
    """
    from elevenlabs import ElevenLabs

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY environment variable is not set")

    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID)
    model_id = os.environ.get("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID)

    text = f"{quote['content']}  — {quote['author']}"
    print(f"Generating audio ({len(text)} chars): {text[:80]}...")

    client = ElevenLabs(api_key=api_key)
    audio_bytes = client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=model_id,
        text=text,
    )

    # elevenlabs SDK may return a generator of bytes chunks
    if hasattr(audio_bytes, "__iter__") and not isinstance(audio_bytes, (bytes, bytearray)):
        audio_bytes = b"".join(audio_bytes)

    dest = os.path.join(output_path, "narration.mp3")
    with open(dest, "wb") as f:
        f.write(audio_bytes)

    duration = _get_duration(dest)
    print(f"Audio saved: {dest} ({duration:.2f}s)")
    return dest, duration


def _get_duration(path: str) -> float:
    """Use ffprobe to get the duration of a media file in seconds."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    for stream in data.get("streams", []):
        if "duration" in stream:
            return float(stream["duration"])
    raise RuntimeError(f"Could not determine duration of {path}")
