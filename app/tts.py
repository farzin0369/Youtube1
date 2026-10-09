"""Quality narrator: OpenAI HD male voice (onyx) — fixed for all videos."""
from __future__ import annotations

from pathlib import Path

from app.utils import env, has_openai, load_channel_config


def _voice_settings() -> tuple[str, str]:
    try:
        ch = (load_channel_config().get("channel") or {})
        voice = env("TTS_VOICE") or ch.get("tts_voice") or "onyx"
        model = env("TTS_MODEL") or ch.get("tts_model") or "tts-1-hd"
        return str(voice), str(model)
    except Exception:
        return "onyx", "tts-1-hd"


def synthesize(text: str, out_path: Path, kind: str = "short") -> dict:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    voice, model = _voice_settings()

    if not has_openai():
        raise RuntimeError(
            "OPENAI_API_KEY required for quality narrator. "
            "Free Piper path was removed from production quality mode."
        )

    from openai import OpenAI

    client = OpenAI(
        api_key=env("OPENAI_API_KEY"),
        base_url=env("OPENAI_API_BASE") or "https://api.openai.com/v1",
    )
    # Normalize text for more natural speech
    spoken = text.strip().replace("\n", " ")
    resp = client.audio.speech.create(
        model=model,
        voice=voice,
        input=spoken[:4000],
        response_format="mp3",
        speed=0.95,
    )
    out_path = out_path.with_suffix(".mp3")
    resp.stream_to_file(str(out_path))
    return {
        "path": str(out_path),
        "provider": "openai",
        "voice": voice,
        "model": model,
        "narrator_locked": True,
        "ok": True,
    }
