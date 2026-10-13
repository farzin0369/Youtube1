"""Persian neural TTS with word-timed captions and per-scene delivery shaping."""
from __future__ import annotations

import asyncio
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.utils import env, load_channel_config

TICKS_PER_SECOND = 10_000_000


def _voice() -> str:
    if env("TTS_VOICE"):
        return str(env("TTS_VOICE"))
    try:
        return str((load_channel_config().get("channel") or {}).get("tts_voice") or "fa-IR-FaridNeural")
    except Exception:
        return "fa-IR-FaridNeural"


def srt_timestamp(seconds: float) -> str:
    millis = max(0, int(round(seconds * 1000)))
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    whole, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole:02d},{ms:03d}"


def phrase_cues(
    events: list[dict[str, Any]], *, max_words: int = 5, max_seconds: float = 3.2,
) -> list[tuple[float, float, str]]:
    """Group Edge word events into readable phrase-by-phrase SRT captions."""
    cues: list[tuple[float, float, str]] = []
    group: list[dict[str, Any]] = []

    def flush() -> None:
        if not group:
            return
        start = int(group[0]["offset"]) / TICKS_PER_SECOND
        end = max(start + 0.18, (int(group[-1]["offset"]) + int(group[-1]["duration"])) / TICKS_PER_SECOND)
        text = " ".join(str(event.get("text") or "").strip() for event in group).strip()
        text = re.sub(r"\s+", " ", text)
        if text:
            cues.append((start, end, text))
        group.clear()

    for event in events:
        if event.get("type") != "WordBoundary" or not str(event.get("text") or "").strip():
            continue
        if group:
            group_start = int(group[0]["offset"]) / TICKS_PER_SECOND
            next_end = (int(event["offset"]) + int(event["duration"])) / TICKS_PER_SECOND
            if len(group) >= max_words or next_end - group_start > max_seconds:
                flush()
        group.append(event)
    flush()
    return cues


async def _render(
    text: str, audio_path: Path, *, rate: str = "-4%", pitch: str = "+0Hz",
) -> list[dict[str, Any]]:
    import edge_tts

    communicate = edge_tts.Communicate(
        text,
        voice=_voice(),
        rate=rate,
        pitch=pitch,
        boundary="WordBoundary",
    )
    audio = bytearray()
    events: list[dict[str, Any]] = []
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            audio.extend(chunk.get("data") or b"")
        elif chunk.get("type") == "WordBoundary":
            events.append(chunk)
    if len(audio) < 1024:
        raise RuntimeError("Edge TTS returned no usable audio")
    audio_path.write_bytes(audio)
    if not events:
        raise RuntimeError("Edge TTS returned no word-boundary metadata; timed captions are required")
    return events


def _duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, capture_output=True, text=True, timeout=30,
    )
    duration = float(result.stdout.strip())
    if duration <= 0:
        raise RuntimeError("TTS segment has a non-positive duration")
    return duration


def _merge_segments(parts: list[Path], output: Path, pause_seconds: float = 0.28) -> None:
    filters: list[str] = []
    inputs: list[str] = []
    for index in range(len(parts)):
        pad = f",apad=pad_dur={pause_seconds:.3f}" if index < len(parts) - 1 else ""
        filters.append(f"[{index}:a]asetpts=PTS-STARTPTS{pad}[a{index}]")
        inputs.append(f"[a{index}]")
    filters.append("".join(inputs) + f"concat=n={len(parts)}:v=0:a=1[aout]")
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for path in parts:
        command += ["-i", str(path)]
    command += [
        "-filter_complex", ";".join(filters), "-map", "[aout]", "-codec:a", "libmp3lame",
        "-b:a", "192k", "-ar", "48000", str(output),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=max(120, 30 * len(parts)))


def _delivery(mood: str) -> tuple[str, str]:
    """Small prosody differences retain one narrator while marking the emotional arc."""
    return {
        "hook": ("+5%", "+3Hz"),
        "calm": ("-8%", "-2Hz"),
        "reassuring": ("-3%", "+0Hz"),
        "motivational": ("+6%", "+2Hz"),
    }.get(str(mood or "").lower(), ("-4%", "+0Hz"))


def synthesize_with_captions(
    text: str,
    audio_path: Path,
    captions_path: Path,
    *,
    scenes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    audio_path, captions_path = Path(audio_path), Path(captions_path)
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    captions_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_script = re.sub(r"\s+", " ", str(text or "")).strip()
    all_events: list[dict[str, Any]] = []
    scene_timings: list[dict[str, float]] = []
    delivery_log: list[dict[str, str]] = []

    if scenes:
        scene_texts = [re.sub(r"\s+", " ", str(scene.get("spoken_text") or "")).strip() for scene in scenes]
        if " ".join(scene_texts) != normalized_script:
            raise ValueError("TTS scene narration must exactly match the approved script")
        with tempfile.TemporaryDirectory(prefix="persian-tts-", dir=str(audio_path.parent)) as temp_dir:
            temp = Path(temp_dir)
            parts: list[Path] = []
            cursor = 0.0
            for index, (scene, scene_text) in enumerate(zip(scenes, scene_texts)):
                rate, pitch = _delivery(str(scene.get("mood") or ""))
                part = temp / f"scene-{index:02d}.mp3"
                events = asyncio.run(_render(scene_text, part, rate=rate, pitch=pitch))
                duration = _duration(part)
                start = cursor
                shifted_events = []
                offset_ticks = int(round(start * TICKS_PER_SECOND))
                for event in events:
                    shifted = dict(event)
                    shifted["offset"] = int(event["offset"]) + offset_ticks
                    shifted_events.append(shifted)
                all_events.extend(shifted_events)
                scene_timings.append({"start_seconds": start, "end_seconds": start + duration})
                delivery_log.append({"mood": str(scene.get("mood") or ""), "rate": rate, "pitch": pitch})
                cursor += duration + (0.28 if index < len(scenes) - 1 else 0.0)
                parts.append(part)
            _merge_segments(parts, audio_path)
    else:
        all_events = asyncio.run(_render(normalized_script, audio_path))

    cues: list[tuple[float, float, str]] = []
    if scenes:
        # Reset caption grouping at scene boundaries so words from separate beats do not merge.
        for timing, scene in zip(scene_timings, scenes):
            start_tick = int(round(timing["start_seconds"] * TICKS_PER_SECOND))
            end_tick = int(round(timing["end_seconds"] * TICKS_PER_SECOND))
            local = [
                {**event, "offset": int(event["offset"]) - start_tick}
                for event in all_events
                if start_tick <= int(event.get("offset") or 0) < end_tick
            ]
            for start, end, phrase in phrase_cues(local, max_words=4, max_seconds=1.8):
                cues.append((start + timing["start_seconds"], end + timing["start_seconds"], phrase))
    else:
        cues = phrase_cues(all_events)
    if not cues:
        raise RuntimeError("No subtitle phrases could be built from Edge TTS metadata")
    blocks = [
        f"{index}\n{srt_timestamp(start)} --> {srt_timestamp(end)}\n{phrase}\n"
        for index, (start, end, phrase) in enumerate(cues, 1)
    ]
    captions_path.write_text("\n".join(blocks), encoding="utf-8")
    return {
        "path": str(audio_path),
        "captions_path": str(captions_path),
        "provider": "edge-tts",
        "voice": _voice(),
        "narrator_locked": True,
        "caption_mode": "word-boundary phrase captions",
        "duration_seconds": _duration(audio_path),
        "caption_count": len(cues),
        "scene_timings": scene_timings,
        "delivery_profiles": delivery_log,
        "ok": True,
    }
