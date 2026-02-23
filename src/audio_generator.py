"""Generate TTS narration via ElevenLabs REST API and measure its duration."""

import json
import os
import subprocess

import requests


ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"


def _get_voice_id(api_key: str) -> str:
    """Return configured voice ID or the first available voice on the account."""
    configured = os.environ.get("ELEVENLABS_VOICE_ID", "")
    if configured:
        return configured

    resp = requests.get(
        f"{ELEVENLABS_BASE}/voices",
        headers={"xi-api-key": api_key},
        timeout=10,
    )
    resp.raise_for_status()
    voices = resp.json().get("voices", [])
    if not voices:
        raise RuntimeError("No voices found on ElevenLabs account")

    voice = voices[0]
    print(f"Using voice: {voice['name']} ({voice['voice_id']})")
    return voice["voice_id"]


def _get_model_id(api_key: str) -> str:
    """Return configured model ID or the first TTS-capable model on the account."""
    configured = os.environ.get("ELEVENLABS_MODEL_ID", "")
    if configured:
        return configured

    resp = requests.get(
        f"{ELEVENLABS_BASE}/models",
        headers={"xi-api-key": api_key},
        timeout=10,
    )
    resp.raise_for_status()
    models = resp.json()

    # Prefer turbo/flash (fast + cheap), fall back to first available TTS model
    preferred = ["eleven_turbo_v2", "eleven_flash_v2_5", "eleven_turbo_v2_5"]
    tts_models = [m for m in models if m.get("can_do_text_to_speech", False)]

    for pref in preferred:
        for m in tts_models:
            if m["model_id"] == pref:
                print(f"Using model: {m['name']} ({m['model_id']})")
                return m["model_id"]

    if tts_models:
        m = tts_models[0]
        print(f"Using model: {m['name']} ({m['model_id']})")
        return m["model_id"]

    raise RuntimeError("No TTS-capable models found on ElevenLabs account")


def generate_audio(quote: dict, output_path: str) -> tuple[str, float]:
    """Synthesise speech for the quote and return (mp3_path, duration_seconds)."""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY environment variable is not set")

    voice_id = _get_voice_id(api_key)
    model_id = _get_model_id(api_key)

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

    url = f"{ELEVENLABS_BASE}/text-to-speech/{voice_id}"
    resp = requests.post(url, headers=headers, json=payload, timeout=60)

    if not resp.ok:
        raise RuntimeError(
            f"ElevenLabs TTS failed {resp.status_code}: {resp.text[:500]}"
        )

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
