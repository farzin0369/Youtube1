"""CPU smoke test for the opt-in Pocket TTS ONNX Persian voice engine."""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import onnxruntime as ort
import soundfile as sf

from app.pocket_tts_onnx import synthesize_to_file

def main() -> None:
    providers = ort.get_available_providers()
    if "CPUExecutionProvider" not in providers:
        raise RuntimeError(f"ONNX CPU provider missing: {providers}")
    os.environ["TTS_PROVIDER"] = "pocket-tts-onnx"
    out = Path(os.environ.get("POCKET_TTS_TEST_OUTPUT", "output/pocket-tts-test"))
    out.mkdir(parents=True, exist_ok=True)
    text = (
        "فکر می‌کنی آینده با یک اتفاق بزرگ ساخته می‌شود؟ "
        "نه؛ آینده با انتخاب‌های کوچک ساخته می‌شود. "
        "هر قدم، حتی اگر کسی نبیند، مسیرت را عوض می‌کند. شروع کن؛ همین حالا."
    )
    result = synthesize_to_file(text, out / "bamo_pocket_tts_farsi.wav")
    audio, sample_rate = sf.read(result["path"])
    if audio.size < sample_rate or not np.isfinite(audio).all():
        raise RuntimeError("Generated WAV failed audio validation")
    report = {
        **result,
        "text": text,
        "sample_rate": sample_rate,
        "samples": int(audio.size),
        "peak": float(np.max(np.abs(audio))),
        "rms": float(np.sqrt(np.mean(np.square(audio)))),
        "available_providers": providers,
        "used_provider": "CPUExecutionProvider",
        "commercial_license_verified": False,
    }
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
