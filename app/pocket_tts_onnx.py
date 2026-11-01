"""Lazy CPU-only adapter for Nimaone's Persian Pocket-TTS ONNX engine.

The upstream model is CC-BY-NC-4.0. This adapter is opt-in and must not be
used for monetized/commercial output unless the model author grants permission.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.utils import env

ROOT = Path(__file__).resolve().parents[1]
CACHE_ROOT = Path(env("POCKET_TTS_CACHE_DIR") or ROOT / ".cache" / "persian_tts")
MODEL_REPO = "Nimaone/pocket-tts-farsi-v2-onnx"
BASE_MODEL_REPO = "mehdi-hf/pocket-tts-farsi-v2"
UPSTREAM_REPO = "https://github.com/nimaone/persian_tts.git"
_REQUIRED_ONNX = (
    "flow_lm_step.onnx", "flow_lm_step.onnx.data",
    "mimi_encoder.onnx", "mimi_encoder.onnx.data",
    "mimi_decoder_step_kv.onnx", "mimi_decoder_step_kv.onnx.data",
    "g2p_encoder.onnx", "g2p_decoder.onnx", "g2p_decoder.onnx.data",
    "weights.npz", "decode_state_init.npz", "manifest.json",
)

_ENGINE = None


def _ensure_runtime() -> tuple[Path, Path]:
    try:
        from huggingface_hub import hf_hub_download, snapshot_download
    except ImportError as exc:
        raise RuntimeError(
            "Pocket TTS dependencies are missing; install onnxruntime, numpy, "
            "scipy, soundfile, sentencepiece and huggingface_hub"
        ) from exc

    scripts_dir = CACHE_ROOT / "scripts"
    repo_root = CACHE_ROOT
    if not (scripts_dir / "tts_onnx.py").is_file():
        CACHE_ROOT.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", UPSTREAM_REPO, str(CACHE_ROOT)],
            check=True, capture_output=True, text=True, timeout=180,
        )

    model_dir = repo_root / "model" / "onnx"
    model_dir.mkdir(parents=True, exist_ok=True)
    if not all((model_dir / name).is_file() for name in _REQUIRED_ONNX):
        snapshot_download(
            repo_id=MODEL_REPO, local_dir=str(model_dir),
            allow_patterns=list(_REQUIRED_ONNX),
        )

    # The upstream ONNX engine reads this phoneme tokenizer from model/v2.
    tokenizer_dir = repo_root / "model" / "v2"
    tokenizer_dir.mkdir(parents=True, exist_ok=True)
    tokenizer = tokenizer_dir / "tokenizer_ph.model"
    if not tokenizer.is_file():
        hf_hub_download(
            repo_id=BASE_MODEL_REPO, filename="tokenizer_ph.model",
            local_dir=str(tokenizer_dir),
        )
    if not tokenizer.is_file():
        raise RuntimeError("Pocket TTS phoneme tokenizer download failed")
    return repo_root, model_dir


def _engine():
    global _ENGINE
    if _ENGINE is None:
        repo_root, model_dir = _ensure_runtime()
        for path in (str(repo_root / "scripts"), str(repo_root / "model" / "v2")):
            if path not in sys.path:
                sys.path.insert(0, path)
        from tts_onnx import OnnxTts
        _ENGINE = OnnxTts(pkg_dir=model_dir)
    return _ENGINE


def reference_voice() -> Path:
    configured = str(env("POCKET_TTS_REFERENCE_VOICE") or "").strip()
    if configured:
        voice = Path(configured).expanduser()
        if not voice.is_absolute():
            voice = ROOT / voice
        if not voice.is_file():
            raise FileNotFoundError(f"POCKET_TTS_REFERENCE_VOICE not found: {voice}")
        return voice
    repo_root, _ = _ensure_runtime()
    voice = repo_root / "voices" / "male_hello.wav"
    if not voice.is_file():
        raise FileNotFoundError(
            "Default Pocket TTS reference voice is missing; set POCKET_TTS_REFERENCE_VOICE"
        )
    return voice


def synthesize_array(text: str, *, mode: str = "pack"):
    """Return (mono float32 samples, sample_rate) from CPUExecutionProvider."""
    import numpy as np

    engine = _engine()
    voice = reference_voice()
    pace = float(env("POCKET_TTS_PACE") or 1.0)
    if not 0.6 <= pace <= 1.5:
        raise ValueError("POCKET_TTS_PACE must be between 0.6 and 1.5")
    audio = engine.synthesize_text(str(text), str(voice), pace=pace, mode=mode)
    audio = np.asarray(audio, dtype=np.float32).reshape(-1)
    if audio.size == 0 or not np.isfinite(audio).all():
        raise RuntimeError("Pocket TTS returned empty or invalid audio")
    return audio, int(engine.sample_rate)


def synthesize_to_file(text: str, out_path: Path, *, mode: str = "pack") -> dict[str, Any]:
    import soundfile as sf

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    audio, sample_rate = synthesize_array(text, mode=mode)
    sf.write(str(out_path), audio, sample_rate, subtype="PCM_16")
    if not out_path.is_file() or out_path.stat().st_size < 1024:
        raise RuntimeError("Pocket TTS WAV output was not created correctly")
    return {
        "path": str(out_path), "provider": "pocket-tts-onnx",
        "voice": str(env("POCKET_TTS_REFERENCE_VOICE") or "male_hello.wav"),
        "model": MODEL_REPO, "sample_rate": sample_rate,
        "duration_seconds": round(len(audio) / sample_rate, 3),
        "runtime": "onnxruntime-cpu", "narrator_locked": True, "ok": True,
    }
