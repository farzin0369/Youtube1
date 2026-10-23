"""Persian narration: Persian Piper -> ElevenLabs -> Azure Speech -> Edge TTS -> local Piper."""
from __future__ import annotations

import html
import json
import urllib.error
import urllib.request
from pathlib import Path

from app.utils import env, load_channel_config


def _voice_settings() -> tuple[str, str]:
    try:
        ch = (load_channel_config().get("channel") or {})
        voice = env("TTS_VOICE") or ch.get("tts_voice") or "fa-IR-FaridNeural"
        model = env("TTS_MODEL") or ch.get("tts_model") or "neural"
        return str(voice), str(model)
    except Exception:
        return "fa-IR-FaridNeural", "neural"


def _write_elevenlabs(text: str, out_path: Path) -> dict | None:
    api_key = (env("ELEVENLABS_API_KEY") or "").strip()
    voice_id = (env("ELEVENLABS_VOICE_ID") or "").strip()
    if not api_key or not voice_id:
        return None
    payload = json.dumps({
        "text": " ".join(text.strip().split())[:8000],
        "model_id": env("ELEVENLABS_MODEL_ID") or "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.75},
    }).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128",
        data=payload,
        headers={"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            audio = response.read()
        if len(audio) < 1024:
            raise RuntimeError("ElevenLabs returned an empty audio file")
        path = out_path.with_suffix(".mp3")
        path.write_bytes(audio)
        return {"path": str(path), "provider": "elevenlabs", "voice": voice_id,
                "model": env("ELEVENLABS_MODEL_ID") or "eleven_multilingual_v2",
                "narrator_locked": True, "ok": True}
    except Exception as exc:
        print(f"[tts] ElevenLabs unavailable ({type(exc).__name__}: {exc}); trying fallback.")
        return None


def _write_azure(text: str, out_path: Path) -> dict | None:
    key = (env("AZURE_SPEECH_KEY") or "").strip()
    region = (env("AZURE_SPEECH_REGION") or "").strip()
    if not key or not region:
        return None
    voice = env("AZURE_SPEECH_VOICE") or "fa-IR-FaridNeural"
    safe_text = html.escape(" ".join(text.strip().split())[:8000])
    ssml = (
        '<speak version="1.0" xml:lang="fa-IR">'
        f'<voice name="{html.escape(voice, quote=True)}">{safe_text}</voice>'
        '</speak>'
    ).encode("utf-8")
    request = urllib.request.Request(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
        data=ssml,
        headers={
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
            "User-Agent": "TTKhabarNewsAgent/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            audio = response.read()
        if len(audio) < 1024:
            raise RuntimeError("Azure Speech returned an empty audio file")
        path = out_path.with_suffix(".mp3")
        path.write_bytes(audio)
        return {"path": str(path), "provider": "azure-speech", "voice": voice,
                "model": "neural", "narrator_locked": True, "ok": True}
    except Exception as exc:
        print(f"[tts] Azure Speech unavailable ({type(exc).__name__}: {exc}); trying fallback.")
        return None


def _write_persian_speech(text: str, out_path: Path) -> dict | None:
    """Offline Persian Piper/ONNX voice (Mana); CPU inference, no API key."""
    try:
        from persian_speech_runtime import talk

        wav_path = out_path.with_suffix(".wav")
        spoken = " ".join(text.strip().split())[:8000]
        talk(spoken, str(wav_path))
        if not wav_path.exists() or wav_path.stat().st_size < 1024:
            raise RuntimeError("Persian Speech returned an empty audio file")
        return {
            "path": str(wav_path),
            "provider": "persian-speech-piper",
            "voice": "fa-IR-Mana",
            "model": "Mana-Persian-Piper",
            "narrator_locked": True,
            "ok": True,
        }
    except Exception as exc:
        print(
            f"[tts] Persian Piper unavailable ({type(exc).__name__}: {exc}); "
            "trying next provider."
        )
        return None


def _write_edge(text: str, out_path: Path) -> dict | None:
    voice = env("TTS_VOICE") or "fa-IR-FaridNeural"
    try:
        import asyncio

        import edge_tts

        spoken = " ".join(text.strip().split())
        mp3_path = out_path.with_suffix(".mp3")

        async def _save_edge():
            await edge_tts.Communicate(spoken[:8000], voice=voice, rate="-5%").save(str(mp3_path))

        asyncio.run(_save_edge())
        if not mp3_path.exists() or mp3_path.stat().st_size < 1024:
            raise RuntimeError("Edge TTS returned an empty audio file")
        return {
            "path": str(mp3_path),
            "provider": "edge-tts",
            "voice": voice,
            "model": "neural",
            "narrator_locked": True,
            "ok": True,
        }
    except Exception as exc:
        print(f"[tts] Edge TTS unavailable ({type(exc).__name__}: {exc}); trying local fallback.")
        return None


def synthesize(text: str, out_path: Path, kind: str = "long") -> dict:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    provider = (env("TTS_PROVIDER") or "auto").lower()
    piper_model = env("PIPER_MODEL")
    allow_fallback = env("TTS_ALLOW_FALLBACK", "1").strip().lower() not in {"0", "false", "no"}

    if provider in {"persian-piper", "persian_speech", "mana"}:
        result = _write_persian_speech(text, out_path)
        if result:
            return result
        if allow_fallback:
            print("[tts] Explicit Persian Piper failed; falling back to Edge TTS (free Persian).")
            result = _write_edge(text, out_path)
            if result:
                return result
        raise RuntimeError(
            "Persian Piper was selected but failed and no free fallback succeeded; "
            "check persian-speech install and model download from Hugging Face."
        )

    if provider == "piper":
        from app.local_ai import piper_synthesize

        return piper_synthesize(text, out_path)

    # Priority chain for auto / named providers
    if provider in {"auto", "persian-piper", "persian_speech", "mana"}:
        result = _write_persian_speech(text, out_path)
        if result:
            return result
    if provider in {"auto", "elevenlabs"}:
        result = _write_elevenlabs(text, out_path)
        if result:
            return result
    if provider in {"auto", "elevenlabs", "azure", "azure-speech"}:
        result = _write_azure(text, out_path)
        if result:
            return result
    if provider in {"auto", "edge", "elevenlabs", "azure", "azure-speech", "persian-piper", "persian_speech", "mana"}:
        result = _write_edge(text, out_path)
        if result:
            return result

    if piper_model:
        from app.local_ai import piper_synthesize

        return piper_synthesize(text, out_path)

    if provider == "openai":
        from app.utils import has_openai

        if has_openai():
            try:
                from openai import OpenAI

                client = OpenAI(
                    api_key=env("OPENAI_API_KEY"),
                    base_url=env("OPENAI_API_BASE") or "https://api.openai.com/v1",
                )
                voice, model = _voice_settings()
                path = out_path.with_suffix(".mp3")
                response = client.audio.speech.create(
                    model=model,
                    voice=voice,
                    input=" ".join(text.strip().split())[:4000],
                    response_format="mp3",
                    speed=0.95,
                )
                response.stream_to_file(str(path))
                return {
                    "path": str(path),
                    "provider": "openai",
                    "voice": voice,
                    "model": model,
                    "narrator_locked": True,
                    "ok": True,
                }
            except Exception as exc:
                print(f"[tts] Optional OpenAI TTS unavailable ({type(exc).__name__}: {exc}).")

    raise RuntimeError(
        "No usable TTS provider. Configure Persian Piper (persian-speech), "
        "ElevenLabs, Azure Speech, Edge TTS, or PIPER_MODEL."
    )
