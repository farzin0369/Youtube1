#!/usr/bin/env python3
"""Isolated Persian CPU-only OmniVoice evaluation; does not touch production audio."""
from pathlib import Path
import argparse, json, time
import numpy as np
import soundfile as sf
import torch
from omnivoice import OmniVoice

TEXT = ("فکر می‌کنی آینده با یک اتفاق بزرگ ساخته می‌شود؟ "
        "نه؛ آینده با انتخاب‌های کوچک ساخته می‌شود. "
        "هر قدم، حتی اگر کسی نبیند، مسیرت را عوض می‌کند. "
        "شروع کن؛ همین حالا.")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="output/voice-test/omnivoice-fa-cpu.wav")
    args = p.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if torch.cuda.is_available():
        raise RuntimeError("CPU-only evaluation: CUDA unexpectedly available.")
    started = time.time()
    model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cpu", dtype=torch.float32)
    loaded = time.time()
    with torch.inference_mode():
        audio = model.generate(text=TEXT, language="fa", num_step=16, speed=1.0)
    generated = time.time()
    samples = np.asarray(audio[0], dtype=np.float32)
    if samples.size < 24000 or not np.isfinite(samples).all():
        raise RuntimeError("Generated audio is empty, too short, or invalid.")
    sf.write(out, samples, model.sampling_rate, subtype="PCM_16")
    report = {
        "model": "k2-fsa/OmniVoice", "language": "fa", "device": "cpu",
        "dtype": "float32", "sample_rate": int(model.sampling_rate),
        "duration_seconds": round(samples.size / model.sampling_rate, 2),
        "model_load_seconds": round(loaded - started, 2),
        "generation_seconds": round(generated - loaded, 2),
        "text": TEXT, "audio_file": str(out),
        "commercial_use": "Not cleared: upstream model terms require review; evaluation only."
    }
    out.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
