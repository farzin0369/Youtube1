"""Natural Persian TTS via Mana-Persian-Piper (Piper ONNX).

Model: https://huggingface.co/MahtaFetrat/Mana-Persian-Piper
Trained on Mana-TTS — far more natural than Edge-TTS / MMS for Farsi.
"""
from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Any

import numpy as np

MODEL_DIR_DEFAULT = Path.home() / ".cache" / "bamo" / "mana_piper"
MODEL_ONNX = "fa_IR-mana-medium.onnx"
MODEL_JSON = "fa_IR-mana-medium.onnx.json"
HF_BASE = "https://huggingface.co/MahtaFetrat/Mana-Persian-Piper/resolve/main"


def ensure_model(model_dir: Path | None = None) -> Path:
    import urllib.request

    model_dir = Path(model_dir or MODEL_DIR_DEFAULT)
    model_dir.mkdir(parents=True, exist_ok=True)
    onnx = model_dir / MODEL_ONNX
    cfg = model_dir / MODEL_JSON
    if not onnx.exists() or onnx.stat().st_size < 1_000_000:
        print(f"downloading Mana Piper -> {onnx}")
        urllib.request.urlretrieve(f"{HF_BASE}/{MODEL_ONNX}", onnx)
    if not cfg.exists():
        urllib.request.urlretrieve(f"{HF_BASE}/{MODEL_JSON}", cfg)
    return onnx


def _read_wav(path: Path) -> tuple[int, np.ndarray]:
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return sr, audio


def synthesize_beats(
    beats: list[str],
    out_dir: Path,
    *,
    model_path: Path | None = None,
    gap_sec: float = 0.12,
    end_gap_sec: float = 0.25,
) -> dict[str, Any]:
    """Synthesize each sentence; return narration path + timeline."""
    from piper import PiperVoice

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    onnx = Path(model_path) if model_path else ensure_model()
    voice = PiperVoice.load(str(onnx))

    parts: list[np.ndarray] = []
    timeline: list[dict[str, Any]] = []
    t = 0.0
    sr = 22050

    for i, text in enumerate(beats):
        p = out_dir / f"p{i:02d}.wav"
        with wave.open(str(p), "wb") as wf:
            voice.synthesize_wav(text, wf)
        srate, audio = _read_wav(p)
        sr = srate
        dur = float(len(audio) / sr)
        gap = end_gap_sec if i == len(beats) - 1 else gap_sec
        timeline.append(
            {
                "i": i,
                "start": round(t, 3),
                "speech_end": round(t + dur, 3),
                "end": round(t + dur + gap, 3),
                "speech": round(dur, 3),
                "spoken": text,
            }
        )
        parts.append(audio)
        parts.append(np.zeros(int(sr * gap), dtype=np.float32))
        t += dur + gap
        print(f"mana[{i}] {dur:.2f}s  {text[:48]}")

    full = np.concatenate(parts)
    peak = float(np.max(np.abs(full)) + 1e-8)
    full_i16 = (full / peak * 0.95 * 32767).astype(np.int16)
    narr = out_dir / "narration.wav"
    with wave.open(str(narr), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(full_i16.tobytes())

    meta = {
        "engine": "mana-persian-piper",
        "model": "fa_IR-mana-medium",
        "path": str(narr),
        "sample_rate": sr,
        "duration": round(t, 3),
        "timeline": timeline,
    }
    (out_dir / "timeline.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


if __name__ == "__main__":
    demo = [
        "صبر کن. این یکی عجیبه.",
        "صفر ممیز نه نه نه، تا بی نهایت.",
        "اما برابر یک است.",
    ]
    print(synthesize_beats(demo, Path("/tmp/mana_demo")))
