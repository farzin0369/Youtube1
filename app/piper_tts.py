"""Offline free Persian TTS via Piper male voices (rhasspy gyro/ganji)."""
from __future__ import annotations

from app.persian_tts_normalize import normalize_for_tts

import logging
import os
import wave
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Male Persian Piper voices (MIT/CC0 family via rhasspy/piper-voices) — no API key.
# Prefer gyro (male, high naturalness score), fallback ganji.
VOICE_CANDIDATES = [
    {
        "repo": "rhasspy/piper-voices",
        "onnx": "fa/fa_IR/gyro/medium/fa_IR-gyro-medium.onnx",
        "json": "fa/fa_IR/gyro/medium/fa_IR-gyro-medium.onnx.json",
        "local_onnx": "fa_IR-gyro-medium.onnx",
        "local_json": "fa_IR-gyro-medium.onnx.json",
        "name": "gyro-male",
    },
    {
        "repo": "rhasspy/piper-voices",
        "onnx": "fa/fa_IR/ganji/medium/fa_IR-ganji-medium.onnx",
        "json": "fa/fa_IR/ganji/medium/fa_IR-ganji-medium.onnx.json",
        "local_onnx": "fa_IR-ganji-medium.onnx",
        "local_json": "fa_IR-ganji-medium.onnx.json",
        "name": "ganji-male",
    },
    {
        "repo": "rhasspy/piper-voices",
        "onnx": "fa/fa_IR/amir/medium/fa_IR-amir-medium.onnx",
        "json": "fa/fa_IR/amir/medium/fa_IR-amir-medium.onnx.json",
        "local_onnx": "fa_IR-amir-medium.onnx",
        "local_json": "fa_IR-amir-medium.onnx.json",
        "name": "amir-male",
    },
]


def _model_dir() -> Path:
    root = Path(os.getenv("PIPER_MODEL_DIR") or "models/piper").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_male_piper_model() -> tuple[Path, str]:
    """Download first available male Piper Persian voice (HF, free, no key)."""
    out = _model_dir()
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as exc:
        raise RuntimeError(
            "piper backend needs huggingface_hub; pip install huggingface_hub piper-tts"
        ) from exc

    last_err: Exception | None = None
    for cand in VOICE_CANDIDATES:
        onnx = out / cand["local_onnx"]
        cfg = out / cand["local_json"]
        if onnx.is_file() and cfg.is_file() and onnx.stat().st_size > 1_000_000:
            return onnx, cand["name"]
        try:
            logger.info("downloading free male Piper voice %s …", cand["name"])
            hf_hub_download(
                repo_id=cand["repo"],
                filename=cand["onnx"],
                local_dir=str(out),
                local_dir_use_symlinks=False,
            )
            hf_hub_download(
                repo_id=cand["repo"],
                filename=cand["json"],
                local_dir=str(out),
                local_dir_use_symlinks=False,
            )
            # Flatten nested HF path into local flat names
            nested_onnx = out / cand["onnx"]
            nested_json = out / cand["json"]
            if nested_onnx.is_file() and nested_onnx.resolve() != onnx.resolve():
                onnx.write_bytes(nested_onnx.read_bytes())
            if nested_json.is_file() and nested_json.resolve() != cfg.resolve():
                cfg.write_bytes(nested_json.read_bytes())
            if onnx.is_file() and cfg.is_file():
                return onnx, cand["name"]
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("piper voice %s failed: %s", cand["name"], type(exc).__name__)
            continue
    raise RuntimeError(f"no male Piper Persian voice available: {last_err}")


def _length_scale_for_mood(mood: str, hint: dict[str, Any] | None = None) -> float:
    """Map scene mood to Piper speaking-rate (lower = slower / calmer)."""
    base = {
        "hook": 0.95,
        "calm": 0.82,
        "reassuring": 0.86,
        "motivational": 1.05,
        "sad": 0.80,
        "joyful": 1.08,
    }.get(str(mood or "").lower(), 0.90)
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
    """Synthesize one utterance with offline male Piper; writes WAV/MP3 path."""
    from piper import PiperVoice  # type: ignore

    cleaned = normalize_for_tts(" ".join(str(text or "").split()).strip())
    if not cleaned:
        raise ValueError("empty text for piper tts")

    model_path, voice_name = ensure_male_piper_model()
    voice = PiperVoice.load(str(model_path))
    length_scale = _length_scale_for_mood(mood, hint)

    audio_path = Path(audio_path)
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    wav_path = audio_path.with_suffix(".wav")

    with wave.open(str(wav_path), "wb") as wav_file:
        try:
            voice.synthesize_wav(cleaned, wav_file, length_scale=length_scale)
        except TypeError:
            voice.synthesize_wav(cleaned, wav_file)

    # Optional mp3 target
    if audio_path.suffix.lower() == ".mp3":
        import subprocess

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(wav_path),
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "3",
                str(audio_path),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
    else:
        if wav_path.resolve() != audio_path.resolve():
            audio_path.write_bytes(wav_path.read_bytes())

    return {
        "provider": "piper",
        "model": "rhasspy/piper-voices",
        "voice": voice_name,
        "gender": "male",
        "length_scale": length_scale,
        "path": str(audio_path),
    }
