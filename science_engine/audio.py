"""Generate a narration track with Edge TTS; run only in the isolated science render workflow."""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import edge_tts


async def synthesize(text_path: Path, output_path: Path, voice: str, rate: str) -> None:
    text = text_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Narration file is empty: {text_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
    await communicate.save(str(output_path))


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthesize narration using Edge TTS.")
    parser.add_argument("--text-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--voice", default="fa-IR-FaridNeural")
    parser.add_argument("--rate", default="-5%")
    args = parser.parse_args()
    asyncio.run(synthesize(args.text_file, args.output, args.voice, args.rate))


if __name__ == "__main__":
    main()
