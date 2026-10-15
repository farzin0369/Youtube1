"""Offline free Persian TTS via Piper + Mana-Persian-Piper (MIT, no API key)."""
from __future__ import annotations

import logging
import os
import wave
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MODEL_REPO = "MahtaFetrat/Mana-Persian-Piper"
MODEL_ONNX = "fa_IR-mana-medium.onnx"
MODEL_JSON = "fa_IR-mana-medium.onnx.json"


def _model_dir() -> Path:
    root = Path(os.getenv("PIPER_MODEL_DIR") or "models/piper").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_mana_model() -> Path:
    """Download Mana Persian Piper weights once (Hugging Face, free, no key)."""
    out = _model_dir()
    onnx = out / MODEL_ONNX
    cfg = out / MODEL_JSON
    if onnx.is_file() and cfg.is_file() and onnx.stat().st_size > 1_000_000:
        return onnx
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as exc:
        raise RuntimeError(
            "piper backend needs huggingface_hub; pip install huggingface_hub piper-tts"
        ) from exc
    logger.info("downloading free Piper Persian model %s …", MODEL_REPO)
    path = hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_ONNX, local_dir=str(out))
    hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_JSON, local_dir=str(out))
    return Path(path)


def _length_scale_for_mood(mood: str, hint: dict[str, Any] | None = None) -> float:
    """Map scene mood to Piper speaking-rate (lower = slower / calmer)."""
    base = {
        "hook": 0.95,
        "calm": 0.82,
        "reassuring": 0.86,
        "motivational": 1.05,
        "sad": 0.80,
        "joyful": 1.08,
    }.get(str(mood or "").lower(), 0.92)
    hint = hint if isinstance(hint, dict) else {}
    emotion = str(hint.get("emotion") or "").lower()
    if emotion in {"calm", "reassuring", "sad"}:
        base = min(base, 0.85)
    if emotion in {"motivational", "joyful", "angry"}:
        base = max(base, 1.02)
    return max(0.75, min(1.20, float(base)))


def synthesize_piper(
    text: str,
    audio_path: Path,
    *,
    mood: str = "calm",
    hint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Synthesize one utterance with offline Piper; writes 16-bit mono WAV/MP3 path."""
    from piper import PiperVoice  # type: ignore

    cleaned = " ".join(str(text or "").split()).strip()
    if not cleaned:
        raise ValueError("empty text for Piper TTS")

    model_path = ensure_mana_model()
    voice = PiperVoice.load(str(model_path))
    length_scale = _length_scale_for_mood(mood, hint)

    audio_path = Path(audio_path)
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    wav_path = audio_path.with_suffix(".wav")

    with wave.open(str(wav_path), "wb") as wav_file:
        # piper-tts API: synthesize to wav file object
        try:
            voice.synthesize_wav(cleaned, wav_file, length_scale=length_scale)
        except TypeError:
            # older piper API without length_scale kw
            voice.synthesize_wav(cleaned, wav_file)

    if wav_path.stat().st_size < 2000:
        raise RuntimeError("Piper returned empty audio")

    # Convert to mp3 if caller asked for .mp3 (FFmpeg available in production).
    if audio_path.suffix.lower() == ".mp3":
        import subprocess

        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(wav_path), "-codec:a", "libmp3lame", "-b:a", "192k",
                str(audio_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        try:
            wav_path.unlink(missing_ok=True)
        except Exception:
            pass
    else:
        if audio_path.resolve() != wav_path.resolve():
            wav_path.replace(audio_path)

    return {
        "path": str(audio_path),
        "provider": "piper",
        "model": MODEL_REPO,
        "voice": MODEL_ONNX,
        "length_scale": length_scale,
        "mood": mood,
        "ok": True,
    }
