#!/usr/bin/env python3
"""Generate a small Kitten-TTS 2 CPU sample in a documented supported language.

This demo defaults to English. Kitten-TTS 2 currently does not list Persian/Farsi
as a supported language; do not use its output for the Persian narration pipeline.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


DEFAULT_TEXT = (
    "Take a slow breath. You do not have to solve your whole life today. "
    "Take one honest step, and let tomorrow meet you there."
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="output/kitten_tts2_sample.wav")
    parser.add_argument("--text", default=DEFAULT_TEXT)
    parser.add_argument("--voice", default="Bruno")
    parser.add_argument("--preset", default="expressive")
    parser.add_argument("--weights", default="emb4", choices=("emb4", "default"))
    args = parser.parse_args()

    text = " ".join(args.text.strip().split())
    if not text:
        parser.error("--text cannot be empty")
    if re.search(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]", text):
        parser.error(
            "Kitten-TTS 2 currently does not list Persian/Farsi as supported. "
            "Use a supported language for this demo."
        )

    try:
        import numpy as np
        import soundfile as sf
        from kittenml import KittenTTS
    except ImportError as exc:
        raise SystemExit(
            "Missing optional dependencies. Run: pip install -r requirements-kitten.txt"
        ) from exc

    model_name = "KittenML/kitten-tts-2"
    if args.weights == "default":
        model = KittenTTS(model_name)
    else:
        model = KittenTTS(model_name, weights="emb4")

    audio = np.asarray(
        model.generate(text, voice=args.voice, preset=args.preset), dtype=np.float32
    ).squeeze()
    if audio.ndim != 1 or audio.size < 1024 or not np.isfinite(audio).all():
        raise RuntimeError("Kitten-TTS returned invalid or empty audio.")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = int(getattr(model, "sample_rate", 24000))
    sf.write(str(output), audio, sample_rate, subtype="PCM_16")
    if not output.is_file() or output.stat().st_size < 1024:
        raise RuntimeError("Sample audio was not written correctly.")

    print(f"Audio: {output}")
    print(f"Voice: {args.voice}; preset: {args.preset}; sample rate: {sample_rate} Hz")
    print(f"Duration: {audio.size / sample_rate:.2f} seconds")
    print(f"Size: {output.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
