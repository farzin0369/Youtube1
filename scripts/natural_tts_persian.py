#!/usr/bin/env python3
"""Natural Persian TTS: Open Swara male reference + Coqui XTTS voice clone.

Parler-TTS does NOT support Persian — do not use it for fa narration.
Open Swara provides humanized reference WAVs; XTTS speaks new text in that voice.
"""
from __future__ import annotations

import os
import subprocess
import sys
import urllib.request
from pathlib import Path

# Public Open Swara Persian male sample (CC-BY-SA 4.0 — attribute Open Swara)
# Fallback URLs if github raw path changes
REF_CANDIDATES = [
    "https://raw.githubusercontent.com/jaymunshi/open-swara/main/voices/persian/male/persian_male_open_swara_001.wav",
    "https://huggingface.co/datasets/jaymunshi/open-swara/resolve/main/voices/persian/male/persian_male_open_swara_001.wav",
]

DEFAULT_TEXT = (
    "وقتی همه درها بسته به نظر می‌رسند، "
    "یک نور هنوز راه را نشان می‌دهد. "
    "از نو شروع کن. "
    "تو قوی‌تری از چیزی که فکر می‌کنی."
)


def download_ref(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 1000:
        return dest
    last_err = None
    for url in REF_CANDIDATES:
        try:
            print(f"[tts] download ref {url}", flush=True)
            urllib.request.urlretrieve(url, dest)
            if dest.stat().st_size > 1000:
                return dest
        except Exception as e:
            last_err = e
            print(f"[tts] ref fail: {e}", flush=True)
    raise RuntimeError(f"Could not download Open Swara Persian male ref: {last_err}")


def synth_xtts(text: str, ref_wav: Path, out_wav: Path) -> None:
    """Coqui XTTS-v2 zero-shot clone."""
    try:
        from TTS.api import TTS
    except ImportError:
        print("[tts] installing coqui-tts...", flush=True)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "TTS", "torch"]
        )
        from TTS.api import TTS

    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[tts] XTTS on {device}", flush=True)
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    tts.tts_to_file(
        text=text,
        speaker_wav=str(ref_wav),
        language="fa",
        file_path=str(out_wav),
    )


def synth_piper_fallback(text: str, out_wav: Path) -> None:
    """CPU Piper Persian if XTTS unavailable."""
    print("[tts] Piper fallback", flush=True)
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "piper-tts"])
    # Try common Persian models via edge as last resort
    try:
        import edge_tts
        import asyncio

        async def _run():
            c = edge_tts.Communicate(text, "fa-IR-FaridNeural", rate="-10%", pitch="-3Hz")
            # edge outputs mp3; convert
            mp3 = out_wav.with_suffix(".mp3")
            await c.save(str(mp3))
            subprocess.check_call(
                ["ffmpeg", "-y", "-i", str(mp3), str(out_wav)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        asyncio.run(_run())
    except Exception as e:
        raise RuntimeError(f"All TTS backends failed: {e}") from e


def main() -> int:
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "output/colab_cli")
    text = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_TEXT
    out_dir.mkdir(parents=True, exist_ok=True)

    ref = out_dir / "open_swara_fa_male_ref.wav"
    out_wav = out_dir / "narration.wav"
    out_mp3 = out_dir / "narration.mp3"

    try:
        download_ref(ref)
        synth_xtts(text, ref, out_wav)
    except Exception as e:
        print(f"[tts] XTTS path failed: {e}", flush=True)
        synth_piper_fallback(text, out_wav)

    # Normalize loudness + mp3 for mux
    subprocess.check_call(
        [
            "ffmpeg", "-y", "-i", str(out_wav),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar", "44100",
            str(out_mp3),
        ]
    )
    print("[tts] OK", out_mp3, out_mp3.stat().st_size, flush=True)
    # Attribution note
    (out_dir / "ATTRIBUTION_VOICES.txt").write_text(
        "Voice reference: Open Swara (jaymunshi/open-swara) Persian male sample, CC-BY-SA 4.0.\n"
        "Synthesis: Coqui XTTS v2 multilingual (or Edge/Piper fallback).\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
