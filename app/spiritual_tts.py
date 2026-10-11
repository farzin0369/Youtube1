"""Fixed-voice Persian Edge TTS with phrase captions timed from word boundaries."""
from __future__ import annotations

import asyncio
import re
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


def phrase_cues(events: list[dict[str, Any]], *, max_words: int = 5, max_seconds: float = 3.2) -> list[tuple[float, float, str]]:
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


async def _render(text: str, audio_path: Path) -> list[dict[str, Any]]:
    import edge_tts

    voice = _voice()
    communicate = edge_tts.Communicate(
        text,
        voice=voice,
        rate="-4%",
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


def synthesize_with_captions(text: str, audio_path: Path, captions_path: Path) -> dict[str, Any]:
    audio_path, captions_path = Path(audio_path), Path(captions_path)
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    captions_path.parent.mkdir(parents=True, exist_ok=True)
    events = asyncio.run(_render(" ".join(text.split()), audio_path))
    cues = phrase_cues(events)
    if not cues:
        raise RuntimeError("No subtitle phrases could be built from Edge TTS metadata")
    blocks = [
        f"{index}\n{srt_timestamp(start)} --> {srt_timestamp(end)}\n{text}\n"
        for index, (start, end, text) in enumerate(cues, 1)
    ]
    captions_path.write_text("\n".join(blocks), encoding="utf-8")
    final_end = cues[-1][1]
    return {
        "path": str(audio_path),
        "captions_path": str(captions_path),
        "provider": "edge-tts",
        "voice": _voice(),
        "narrator_locked": True,
        "caption_mode": "word-boundary phrase captions",
        "duration_seconds": final_end,
        "caption_count": len(cues),
        "ok": True,
    }
