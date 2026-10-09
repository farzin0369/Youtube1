"""Persian narration: neural Edge voice, OpenAI when configured, and local Piper fallback."""
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

    provider = (env("TTS_PROVIDER") or "auto").lower()
    piper_model = env("PIPER_MODEL")

    # Microsoft Edge neural Persian voices are available without a paid API key.
    # Explicit edge mode uses a natural Persian voice first, with local Piper as fallback.
    if provider == "edge":
        voice = env("TTS_VOICE") or "fa-IR-FaridNeural"
        try:
            import asyncio
            import edge_tts
            spoken = " ".join(text.strip().replace("\\n", " ").split())
            mp3_path = out_path.with_suffix(".mp3")
            async def _save_edge():
                await edge_tts.Communicate(spoken[:8000], voice=voice, rate="-5%").save(str(mp3_path))
            asyncio.run(_save_edge())
            if not mp3_path.exists() or mp3_path.stat().st_size < 1024:
                raise RuntimeError("Edge TTS returned an empty audio file")
            return {"path": str(mp3_path), "provider": "edge-tts", "voice": voice,
                    "model": "neural", "narrator_locked": True, "ok": True}
        except Exception as exc:
            print(f"[tts] Edge neural voice unavailable; trying fallback: {exc}")
            if piper_model:
                from app.local_ai import piper_synthesize
                return piper_synthesize(text, out_path)
            raise RuntimeError("Edge TTS failed and no Piper fallback is configured") from exc

    if provider == "piper":
        from app.local_ai import piper_synthesize
        return piper_synthesize(text, out_path)

    voice, model = _voice_settings()
    if has_openai():
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=env("OPENAI_API_KEY"),
                base_url=env("OPENAI_API_BASE") or "https://api.openai.com/v1",
            )
            spoken = text.strip().replace("\\n", " ")
            resp = client.audio.speech.create(
                model=model, voice=voice, input=spoken[:4000],
                response_format="mp3", speed=0.95,
            )
            mp3_path = out_path.with_suffix(".mp3")
            resp.stream_to_file(str(mp3_path))
            return {
                "path": str(mp3_path), "provider": "openai", "voice": voice,
                "model": model, "narrator_locked": True, "ok": True,
            }
        except Exception as exc:
            print(f"[tts] OpenAI unavailable; trying local Piper fallback: {exc}")

    if piper_model:
        from app.local_ai import piper_synthesize
        return piper_synthesize(text, out_path)

    raise RuntimeError(
        "No usable TTS provider. Set TTS_PROVIDER=edge with edge-tts installed, "
        "TTS_PROVIDER=piper with PIPER_MODEL, or configure a working OpenAI API key."
    )
