"""ElevenLabs TTS — natural multilingual male voice for Persian shorts."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

# Energetic male multilingual voices (public library)
# Adam is clear; Brian / Charlie also work well on Multilingual v2
DEFAULT_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")  # Adam
DEFAULT_MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")


def _api_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY missing — set GitHub Secret")
    return key


def _probe(path: Path) -> float:
    try:
        return float(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=nw=1:nk=1",
                    str(path),
                ],
                text=True,
            ).strip()
        )
    except Exception:
        return 2.0


def synthesize_text(text: str, dest: Path, *,
                    voice_id: str | None = None,
                    model_id: str | None = None,
                    stability: float = 0.35,
                    similarity_boost: float = 0.85,
                    style: float = 0.45) -> float:
    """Synthesize one utterance to mp3/wav via ElevenLabs REST."""
    import urllib.request

    dest.parent.mkdir(parents=True, exist_ok=True)
    voice = voice_id or DEFAULT_VOICE_ID
    model = model_id or DEFAULT_MODEL
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
    payload = json.dumps(
        {
            "text": text,
            "model_id": model,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": style,
                "use_speaker_boost": True,
            },
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": _api_key(),
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    dest.write_bytes(data)
    if dest.stat().st_size < 500:
        raise RuntimeError(f"ElevenLabs empty audio for: {text[:40]}")
    return max(0.6, _probe(dest))


def synthesize_beats(
    beats: list[str],
    out_dir: Path,
    *,
    gap_sec: float = 0.10,
    end_gap_sec: float = 0.22,
    voice_id: str | None = None,
) -> dict[str, Any]:
    """Per-sentence TTS + full narration concat. Returns timeline meta."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    timeline: list[dict[str, Any]] = []
    t = 0.0

    for i, text in enumerate(beats):
        p = out_dir / f"p{i:02d}.mp3"
        # light retry on transient errors
        for attempt in range(3):
            try:
                dur = synthesize_text(text, p, voice_id=voice_id)
                break
            except Exception as exc:
                if attempt == 2:
                    raise
                print(f"elevenlabs retry {attempt+1}: {exc}", flush=True)
                time.sleep(1.2 * (attempt + 1))
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
        parts.append(p)
        t += dur + gap
        print(f"11labs[{i}] {dur:.2f}s  {text[:48]}", flush=True)

    # silence pad between parts
    silence = out_dir / "sil.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-t",
            f"{gap_sec}",
            "-q:a",
            "9",
            "-acodec",
            "libmp3lame",
            str(silence),
        ],
        check=True,
        capture_output=True,
    )
    lst = out_dir / "list.txt"
    lines: list[str] = []
    for i, f in enumerate(parts):
        lines.append(f"file '{f.resolve()}'")
        if i < len(parts) - 1:
            lines.append(f"file '{silence.resolve()}'")
    lst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    narr = out_dir / "narration.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(narr)],
        check=True,
        capture_output=True,
    )
    duration = max(_probe(narr), timeline[-1]["end"] if timeline else 1.0)
    meta = {
        "engine": "elevenlabs",
        "voice_id": voice_id or DEFAULT_VOICE_ID,
        "model": DEFAULT_MODEL,
        "path": str(narr),
        "duration": round(duration, 3),
        "timeline": timeline,
    }
    (out_dir / "timeline.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta
