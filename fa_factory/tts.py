#!/usr/bin/env python3
"""Per-sentence Persian TTS with exact timing, plus an ambient music bed.

Each sentence is synthesized separately, so the caption/scene timeline is the
real audio timeline (no estimation drift). Voices are tried in order.
"""
from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass
from pathlib import Path

VOICES = ("fa-IR-FaridNeural", "fa-IR-DilaraNeural")
GAP = 0.28       # pause between sentences (s)
LEAD_IN = 0.45   # silence before first word (s)
TAIL = 1.6       # outro after last word (s)


@dataclass
class Beat:
    text: str
    start: float
    end: float


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def probe(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        text=True,
    )
    return float(out.strip())


async def _edge(text: str, dest: Path, voice: str, rate: str) -> None:
    import edge_tts

    await edge_tts.Communicate(text, voice, rate=rate).save(str(dest))


def synth_sentence(text: str, dest: Path, *, fake: bool = False, rate: str = "-4%") -> float:
    if fake:  # offline test path: silence proportional to text length
        dur = max(1.2, len(text) * 0.065)
        _run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{dur:.2f}", "-q:a", "9", "-acodec", "libmp3lame", str(dest)])
        return dur
    last: Exception | None = None
    for voice in VOICES:
        for attempt in range(2):
            try:
                asyncio.run(_edge(text, dest, voice, rate))
                if dest.exists() and dest.stat().st_size > 1500:
                    return probe(dest)
            except Exception as exc:  # network/voice hiccup -> retry / next voice
                last = exc
    raise RuntimeError(f"TTS failed for sentence: {text!r}: {last}")


def build_audio(sentences: list[str], outdir: Path, *, fake: bool = False) -> tuple[Path, list[Beat], float]:
    """Returns (final_audio_path, beats, total_duration_seconds)."""
    parts = outdir / "parts"
    parts.mkdir(parents=True, exist_ok=True)
    beats: list[Beat] = []
    files: list[Path] = []
    t = LEAD_IN
    for i, s in enumerate(sentences):
        p = parts / f"s{i:02d}.mp3"
        d = synth_sentence(s, p, fake=fake)
        files.append(p)
        beats.append(Beat(s, round(t, 3), round(t + d, 3)))
        t += d + GAP
    total = round(beats[-1].end + TAIL, 3)

    # concat with exact silences (re-encode to a common format for sample-accurate joins)
    inputs: list[str] = []
    filt: list[str] = []
    idx = 0
    inputs += ["-f", "lavfi", "-t", f"{LEAD_IN}", "-i", "anullsrc=r=24000:cl=mono"]
    filt.append(f"[{idx}:a]aformat=sample_rates=24000:channel_layouts=mono[a{idx}]")
    labels = [f"[a{idx}]"]
    idx += 1
    for i, f in enumerate(files):
        inputs += ["-i", str(f)]
        filt.append(f"[{idx}:a]aformat=sample_rates=24000:channel_layouts=mono[a{idx}]")
        labels.append(f"[a{idx}]")
        idx += 1
        gap = GAP if i < len(files) - 1 else TAIL
        inputs += ["-f", "lavfi", "-t", f"{gap}", "-i", "anullsrc=r=24000:cl=mono"]
        filt.append(f"[{idx}:a]aformat=sample_rates=24000:channel_layouts=mono[a{idx}]")
        labels.append(f"[a{idx}]")
        idx += 1
    filt.append("".join(labels) + f"concat=n={len(labels)}:v=0:a=1[vo]")
    vo = outdir / "voice.wav"
    _run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filt), "-map", "[vo]", "-ar", "44100", str(vo)])

    # ambient bed: soft chord + slow tremolo, ducked under the voice
    bed = outdir / "bed.wav"
    _run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=f=110:d={total}",
        "-f", "lavfi", "-i", f"sine=f=164.81:d={total}",
        "-f", "lavfi", "-i", f"sine=f=220:d={total}",
        "-filter_complex",
        "[0][1][2]amix=inputs=3:normalize=0,tremolo=f=0.35:d=0.5,lowpass=f=700,volume=0.35,"
        f"afade=t=in:d=1.5,afade=t=out:st={max(0.1, total - 2.0):.2f}:d=2[b]",
        "-map", "[b]", "-ar", "44100", str(bed),
    ])
    final = outdir / "audio.mp3"
    _run([
        "ffmpeg", "-y", "-i", str(vo), "-i", str(bed),
        "-filter_complex",
        "[0:a]asplit=2[v1][v2];[1:a][v2]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[bd];"
        "[v1]volume=1.0[vv];[vv][bd]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-16:TP=-1.5:LRA=9[o]",
        "-map", "[o]", "-ar", "44100", "-b:a", "192k", str(final),
    ])
    return final, beats, probe(final)
