"""Generate TTS narration via ElevenLabs REST API and measure its duration."""

import json
import os
import subprocess

import requests


ELEVENLABS_VOICES_URL = "https://api.elevenlabs.io/v1/voices"
ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"


def _get_voice_id(api_key: str) -> str:
    """Return configured voice ID or the first available voice on the account."""
    configured = os.environ.get("ELEVENLABS_VOICE_ID", "")
    if configured:
        return configured

    headers = {"xi-api-key": api_key}
    resp = requests.get(ELEVENLABS_VOICES_URL, headers=headers, timeout=10)
    resp.raise_for_status()
    voices = resp.json().get("voices", [])
    if not voices:
        raise RuntimeError("No voices found on ElevenLabs account")

    voice = voices[0]
    print(f"Using voice: {voice['name']} ({voice['voice_id']})")
    return voice["voice_id"]


def generate_audio(quote: dict, output_path: str) -> tuple[str, float]:
    """Synthesise speech for the quote and return (mp3_path, duration_seconds).

    Uses the ElevenLabs REST API directly to avoid SDK version issues.
    """
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY environment variable is not set")

    model_id = os.environ.get("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID)
    voice_id = _get_voice_id(api_key)

    text = f"{quote['content']}  — {quote['author']}"
    print(f"Generating audio ({len(text)} chars): {text[:80]}...")

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }

    url = ELEVENLABS_TTS_URL.format(voice_id=voice_id)
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()

    dest = os.path.join(output_path, "narration.mp3")
    with open(dest, "wb") as f:
        f.write(resp.content)

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
