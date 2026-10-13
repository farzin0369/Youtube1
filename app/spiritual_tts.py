"""Persian TTS with Edge word timings and explicit, quality-gated fallbacks."""
from __future__ import annotations

import asyncio
import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

from app.utils import env, load_channel_config

TICKS_PER_SECOND = 10_000_000
LOGGER = logging.getLogger(__name__)


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


def _approximate_phrase_cues(text: str, duration: float, *, max_words: int = 5) -> list[tuple[float, float, str]]:
    """Estimate readable cue ranges when a fallback provider exposes no alignment."""
    words = text.split()
    if not words or duration <= 0:
        return []
    groups = [words[i:i + max_words] for i in range(0, len(words), max_words)]
    weights = [sum(max(1, len(word)) for word in group) for group in groups]
    total_weight = sum(weights) or 1
    cues: list[tuple[float, float, str]] = []
    cursor = 0.0
    for index, (group, weight) in enumerate(zip(groups, weights)):
        start = cursor
        cursor = duration if index == len(groups) - 1 else cursor + duration * weight / total_weight
        if cursor <= start:
            continue
        cues.append((start, cursor, " ".join(group)))
    return cues


async def _render_edge(text: str, audio_path: Path) -> list[dict[str, Any]]:
    import edge_tts

    communicate = edge_tts.Communicate(
        text,
        voice=_voice(),
        rate="-4%",
        boundary="WordBoundary",
        proxy=(env("EDGE_TTS_PROXY") or "").strip() or None,
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
    if not events:
        raise RuntimeError("Edge TTS returned no word-boundary metadata")
    audio_path.write_bytes(audio)
    return events


def _audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
        capture_output=True, text=True, check=True, timeout=30,
    )
    duration = float(result.stdout.strip())
    if duration <= 0:
        raise RuntimeError("TTS output has an invalid duration")
    return duration


def _save_gtts(text: str, audio_path: Path) -> None:
    from gtts import gTTS
    from gtts.lang import tts_langs

    if "fa" not in tts_langs():
        raise RuntimeError("Installed gTTS release does not advertise Persian")
    gTTS(text=text, lang="fa", slow=False).save(str(audio_path))
    if not audio_path.is_file() or audio_path.stat().st_size < 1024:
        raise RuntimeError("gTTS returned no usable audio")


def _save_elevenlabs(text: str, audio_path: Path) -> None:
    key = (env("ELEVENLABS_API_KEY") or "").strip()
    voice_id = (env("ELEVENLABS_VOICE_ID") or "").strip()
    if not key or not voice_id:
        raise RuntimeError("ElevenLabs fallback is not configured")
    import requests

    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
        json={"text": text, "model_id": "eleven_multilingual_v2"},
        timeout=(15, 120),
    )
    try:
        response.raise_for_status()
        if len(response.content) < 1024:
            raise RuntimeError("ElevenLabs returned no usable audio")
        audio_path.write_bytes(response.content)
    finally:
        response.close()


def _save_pyttsx3(text: str, audio_path: Path) -> None:
    import pyttsx3

    engine = pyttsx3.init()
    voices = engine.getProperty("voices") or []
    persian = []
    for voice in voices:
        name_and_id = " ".join((str(getattr(voice, "name", "")), str(getattr(voice, "id", "")))).lower()
        languages = " ".join(str(item) for item in (getattr(voice, "languages", []) or [])).lower()
        has_fa_locale = bool(re.search(r"(?:^|[^a-z])fa(?:[-_][a-z0-9]+)?(?:$|[^a-z])", languages))
        if has_fa_locale or "persian" in name_and_id or "farsi" in name_and_id:
            persian.append(voice)
    if not persian:
        engine.stop()
        raise RuntimeError("No Persian voice is installed for pyttsx3")
    wav_path = audio_path.with_suffix(".wav")
    try:
        engine.setProperty("voice", persian[0].id)
        engine.save_to_file(text, str(wav_path))
        engine.runAndWait()
        engine.stop()
        if not wav_path.is_file() or wav_path.stat().st_size < 1024:
            raise RuntimeError("pyttsx3 returned no usable audio")
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-q:a", "3", str(audio_path)],
            capture_output=True, text=True, check=True, timeout=180,
        )
    finally:
        wav_path.unlink(missing_ok=True)


def _write_srt(cues: list[tuple[float, float, str]], captions_path: Path) -> None:
    if not cues:
        raise RuntimeError("No subtitle phrases could be built")
    blocks = [
        f"{index}\n{srt_timestamp(start)} --> {srt_timestamp(end)}\n{phrase}\n"
        for index, (start, end, phrase) in enumerate(cues, 1)
    ]
    captions_path.write_text("\n".join(blocks), encoding="utf-8")


def synthesize_with_captions(text: str, audio_path: Path, captions_path: Path) -> dict[str, Any]:
    audio_path, captions_path = Path(audio_path), Path(captions_path)
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    captions_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = " ".join(text.split())

    try:
        events = asyncio.run(_render_edge(normalized, audio_path))
        cues = phrase_cues(events)
        _write_srt(cues, captions_path)
        return {
            "path": str(audio_path), "captions_path": str(captions_path), "provider": "edge-tts",
            "voice": _voice(), "narrator_locked": True, "caption_mode": "word-boundary phrase captions",
            "duration_seconds": _audio_duration(audio_path), "caption_count": len(cues), "ok": True,
        }
    except Exception as edge_error:
        # Never print provider exceptions: aiohttp may put signed WebSocket URLs in them.
        LOGGER.warning("Edge TTS unavailable (%s); trying configured fallback providers", type(edge_error).__name__)

    fallbacks: list[tuple[str, Callable[[str, Path], None]]] = [
        ("gtts", _save_gtts),
        ("elevenlabs", _save_elevenlabs),
        ("pyttsx3", _save_pyttsx3),
    ]
    failures: list[str] = []
    for provider, synthesize in fallbacks:
        try:
            synthesize(normalized, audio_path)
            duration = _audio_duration(audio_path)
            cues = _approximate_phrase_cues(normalized, duration)
            _write_srt(cues, captions_path)
            LOGGER.info("TTS fallback selected provider=%s duration_seconds=%.2f", provider, duration)
            return {
                "path": str(audio_path), "captions_path": str(captions_path), "provider": provider,
                "voice": f"{provider}:fa", "narrator_locked": provider == "elevenlabs",
                "caption_mode": "estimated phrase timing (fallback provider has no word boundaries)",
                "duration_seconds": duration, "caption_count": len(cues), "ok": True,
            }
        except Exception as exc:
            failures.append(f"{provider}:{type(exc).__name__}")
            LOGGER.warning("TTS fallback unavailable provider=%s error_type=%s", provider, type(exc).__name__)
            audio_path.unlink(missing_ok=True)
            captions_path.unlink(missing_ok=True)
    raise RuntimeError("Edge TTS and fallback providers failed (" + ", ".join(failures) + ")") from None
