"""Text-to-speech via OpenAI; silent fallback."""
from __future__ import annotations

import wave
from pathlib import Path

from app.utils import env, has_openai


def _write_silent_wav(path: Path, duration_sec: float = 8.0, rate: int = 24000) -> None:
    n = int(rate * duration_sec)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * n)


def synthesize(text: str, out_path: Path, kind: str = "short") -> dict:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if (env("TTS_PROVIDER") or "openai").lower() == "openai" and has_openai():
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=env("OPENAI_API_KEY"),
                base_url=env("OPENAI_API_BASE") or "https://api.openai.com/v1",
            )
            voice = env("TTS_VOICE") or "onyx"
            resp = client.audio.speech.create(
                model=env("TTS_MODEL") or "tts-1",
                voice=voice,
                input=text[:4000],
                response_format="mp3",
            )
            out_path = out_path.with_suffix(".mp3")
            resp.stream_to_file(str(out_path))
            return {"path": str(out_path), "provider": "openai", "voice": voice, "ok": True}
        except Exception as e:
            print(f"[tts] failed: {e}")

    out_path = out_path.with_suffix(".wav")
    _write_silent_wav(out_path, duration_sec=40.0 if kind == "short" else 180.0)
    return {"path": str(out_path), "provider": "silent_fallback", "ok": False}
