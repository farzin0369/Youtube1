"""Natural male Persian TTS via Coqui VITS (Kamtera/persian-tts-male-vits).

Open-source, no API key. Heavier than Piper/Edge but clearly more natural.
Runs on CPU (GitHub Actions / any machine). Falls back to caller on failure.
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from app.persian_tts_normalize import normalize_for_tts

logger = logging.getLogger(__name__)

# Official male VITS checkpoint (OpenRAIL) — natural single-speaker Persian male
MODEL_PATH = os.getenv(
    "COQUI_MODEL_PATH",
    "https://huggingface.co/Kamtera/persian-tts-male1-vits/resolve/main/checkpoint_88000.pth",
)
CONFIG_PATH = os.getenv(
    "COQUI_CONFIG_PATH",
    "https://huggingface.co/Kamtera/persian-tts-male1-vits/resolve/main/config.json",
)
# Alternate repo if male1 unavailable
ALT_MODEL = "https://huggingface.co/Kamtera/persian-tts-male-vits/resolve/main/best_model_91323.pth"
ALT_CONFIG = "https://huggingface.co/Kamtera/persian-tts-male-vits/resolve/main/config.json"

_tts = None


def _ensure_espeak() -> None:
    """Coqui phonemizer expects espeak-ng on PATH."""
    try:
        subprocess.run(["espeak-ng", "--version"], capture_output=True, check=True, timeout=10)
    except Exception:
        # best-effort install on debian runners
        try:
            subprocess.run(["sudo", "apt-get", "update", "-qq"], check=False, timeout=60)
            subprocess.run(
                ["sudo", "apt-get", "install", "-y", "-qq", "espeak-ng"],
                check=False,
                timeout=120,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("espeak-ng install skipped: %s", type(exc).__name__)


def _load_tts():
    global _tts
    if _tts is not None:
        return _tts
    _ensure_espeak()
    try:
        from TTS.api import TTS  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "coqui backend needs coqui-tts; pip install TTS"
        ) from exc

    last_err: Exception | None = None
    for model_path, config_path, name in (
        (MODEL_PATH, CONFIG_PATH, "male1-vits"),
        (ALT_MODEL, ALT_CONFIG, "male-vits"),
    ):
        try:
            logger.info("loading Coqui Persian male model %s …", name)
            _tts = TTS(model_path=model_path, config_path=config_path, progress_bar=False)
            logger.info("Coqui model ready: %s", name)
            return _tts
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("Coqui model %s failed: %s", name, type(exc).__name__)
            _tts = None
    raise RuntimeError(f"could not load Coqui Persian male TTS: {last_err}")


def synthesize_coqui(
    text: str,
    audio_path: Path,
    *,
    mood: str = "calm",
) -> dict[str, Any]:
    """Synthesize natural male Persian speech; writes wav or mp3."""
    cleaned = normalize_for_tts(" ".join(str(text or "").split()).strip())
    if not cleaned:
        raise ValueError("empty text for coqui tts")

    # Leading dot helps some Coqui Persian checkpoints
    if not cleaned.startswith("."):
        speak = "." + cleaned
    else:
        speak = cleaned

    tts = _load_tts()
    audio_path = Path(audio_path)
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    wav_path = audio_path.with_suffix(".wav")

    tts.tts_to_file(text=speak, file_path=str(wav_path))

    if audio_path.suffix.lower() == ".mp3":
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(wav_path),
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(audio_path),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
    elif wav_path.resolve() != audio_path.resolve():
        audio_path.write_bytes(wav_path.read_bytes())

    return {
        "provider": "coqui",
        "model": "Kamtera/persian-tts-male-vits",
        "voice": "male-vits",
        "gender": "male",
        "mood": mood,
        "path": str(audio_path),
    }
