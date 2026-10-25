"""Persian neural TTS with word-timed captions and per-scene delivery shaping."""
from __future__ import annotations

import asyncio
import base64
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.utils import env, load_channel_config

TICKS_PER_SECOND = 10_000_000


def _provider() -> str:
    configured = env("TTS_PROVIDER")
    if configured:
        provider = str(configured).strip().lower()
    else:
        try:
            provider = str((load_channel_config().get("channel") or {}).get("tts_model") or "edge-tts").strip().lower()
        except Exception:
            provider = "edge-tts"
    aliases = {"edge": "edge-tts", "eleven": "elevenlabs", "eleven-v4": "elevenlabs"}
    provider = aliases.get(provider, provider)
    if provider not in {"edge-tts", "elevenlabs"}:
        raise ValueError(f"unsupported TTS_PROVIDER: {provider}")
    return provider


def _voice(provider: str | None = None) -> str:
    provider = provider or _provider()
    if provider == "elevenlabs":
        value = env("ELEVENLABS_VOICE_ID")
        if not value:
            raise RuntimeError("ELEVENLABS_VOICE_ID is required when TTS_PROVIDER=elevenlabs")
        return str(value).strip()
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
        voice=_voice("edge-tts"),
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


def _elevenlabs_tagged_text(text: str, hint: dict[str, Any] | None) -> tuple[str, str]:
    """Add one v4 audio tag when the detected label is sufficiently confident."""
    hint = hint if isinstance(hint, dict) else {}
    emotion = str(hint.get("emotion") or "neutral").lower()
    try:
        intensity = max(0.0, min(1.0, float(hint.get("intensity") or 0.0)))
        confidence = max(0.0, min(1.0, float(hint.get("confidence") or 0.0)))
    except (TypeError, ValueError):
        intensity, confidence = 0.0, 0.0
    tags = {
        "angry": "[angry]", "motivational": "[encouraging]", "calm": "[calm]",
        "reassuring": "[reassuring]", "sad": "[sad]", "joyful": "[excited]",
    }
    tag = tags.get(emotion, "") if confidence >= 0.55 and intensity >= 0.35 else ""
    return (f"{tag} {text}" if tag else text), tag


def _alignment_word_events(alignment: dict[str, Any], expected_text: str) -> list[dict[str, Any]]:
    """Convert ElevenLabs character-level alignment into this module's word events."""
    chars = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []
    aligned_text = "".join(str(char) for char in chars)
    start_at = aligned_text.find(expected_text)
    if start_at < 0 or len(starts) < start_at + len(expected_text) or len(ends) < start_at + len(expected_text):
        raise RuntimeError("ElevenLabs alignment did not contain the original narration text")
    events: list[dict[str, Any]] = []
    for match in re.finditer(r"\S+", expected_text):
        left, right = start_at + match.start(), start_at + match.end()
        word_start = min(float(value) for value in starts[left:right])
        word_end = max(float(value) for value in ends[left:right])
        events.append({
            "type": "WordBoundary", "text": match.group(),
            "offset": max(0, int(round(word_start * TICKS_PER_SECOND))),
            "duration": max(1, int(round((word_end - word_start) * TICKS_PER_SECOND))),
        })
    if not events:
        raise RuntimeError("ElevenLabs returned no word timings")
    return events


def _render_elevenlabs(
    text: str, audio_path: Path, *, hint: dict[str, Any] | None = None,
    previous_text: str = "", next_text: str = "",
) -> list[dict[str, Any]]:
    """Call ElevenLabs v4 timing endpoint and persist audio for normal FFmpeg flow."""
    import requests

    api_key = str(env("ELEVENLABS_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is required when TTS_PROVIDER=elevenlabs")
    voice_id = _voice("elevenlabs")
    tagged_text, _tag = _elevenlabs_tagged_text(text, hint)
    model_id = str(env("ELEVENLABS_MODEL_ID") or "eleven_v4").strip()
    payload: dict[str, Any] = {
        "text": tagged_text,
        "model_id": model_id,
        "language_code": "fa",
        "voice_settings": {
            "stability": float(env("ELEVENLABS_STABILITY") or 0.5),
            "similarity_boost": float(env("ELEVENLABS_SIMILARITY") or 0.75),
        },
    }
    if previous_text:
        payload["previous_text"] = previous_text[-1000:]
    if next_text:
        payload["next_text"] = next_text[:1000]
    try:
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps",
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            params={"output_format": "mp3_44100_128"}, json=payload, timeout=(15, 120),
        )
        response.raise_for_status()
        result = response.json()
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        suffix = f" status={status}" if status else ""
        raise RuntimeError(f"ElevenLabs TTS request failed{suffix} ({type(exc).__name__})") from None
    try:
        audio = base64.b64decode(result["audio_base64"], validate=True)
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"ElevenLabs returned invalid audio payload ({type(exc).__name__})") from None
    if len(audio) < 1024:
        raise RuntimeError("ElevenLabs returned no usable audio")
    audio_path.write_bytes(audio)
    alignment = result.get("alignment") or result.get("normalized_alignment")
    if not isinstance(alignment, dict):
        raise RuntimeError("ElevenLabs returned no character alignment; timed captions are required")
    return _alignment_word_events(alignment, text)


def _duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, capture_output=True, text=True, timeout=30,
    )
    duration = float(result.stdout.strip())
    if duration <= 0:
        raise RuntimeError("TTS segment has a non-positive duration")
    return duration


def _merge_segments(
    parts: list[Path], output: Path, pause_seconds: float | list[float] = 0.28,
) -> None:
    filters: list[str] = []
    inputs: list[str] = []
    for index in range(len(parts)):
        pause = pause_seconds[index] if isinstance(pause_seconds, list) and index < len(pause_seconds) else pause_seconds
        pad = f",apad=pad_dur={max(0.0, float(pause)):.3f}" if index < len(parts) - 1 else ""
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


def _delivery(mood: str, hint: dict[str, Any] | None = None) -> tuple[str, str]:
    """Map scene mood and auto-tag to Edge TTS rate/pitch (integer-only strings).

    edge-tts ValidateString rejects fractional rates like '+4.5%'; values must
    be whole-number percent and Hz.
    """
    base_rate, base_pitch = {
        "hook": ("+5%", "+3Hz"),
        "calm": ("-8%", "-2Hz"),
        "reassuring": ("-3%", "+0Hz"),
        "motivational": ("+6%", "+2Hz"),
    }.get(str(mood or "").lower(), ("-4%", "+0Hz"))
    hint = hint if isinstance(hint, dict) else {}
    emotion = str(hint.get("emotion") or "neutral").lower()
    intensity = max(0.0, min(1.0, float(hint.get("intensity") or 0.0)))
    rate_delta, pitch_delta = {
        "angry": (3.0, 1.0), "motivational": (4.0, 1.0), "joyful": (3.0, 1.0),
        "calm": (-3.0, -1.0), "reassuring": (-2.0, 0.0), "sad": (-3.0, -1.0),
        "neutral": (0.0, 0.0),
    }.get(emotion, (0.0, 0.0))
    confidence = max(0.0, min(1.0, float(hint.get("confidence") or 0.0)))
    scale = intensity * confidence * 0.5
    base_rate_value = float(base_rate.rstrip("%"))
    base_pitch_value = float(base_pitch.rstrip("Hz"))
    rate = int(round(max(-10.0, min(10.0, base_rate_value + rate_delta * scale))))
    pitch = int(round(max(-3.0, min(3.0, base_pitch_value + pitch_delta * scale))))
    return f"{rate:+d}%", f"{pitch:+d}Hz"


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
    provider = _provider()

    if scenes:
        scene_texts = [re.sub(r"\s+", " ", str(scene.get("spoken_text") or "")).strip() for scene in scenes]
        if " ".join(scene_texts) != normalized_script:
            raise ValueError("TTS scene narration must exactly match the approved script")
        with tempfile.TemporaryDirectory(prefix="persian-tts-", dir=str(audio_path.parent)) as temp_dir:
            temp = Path(temp_dir)
            parts: list[Path] = []
            scene_pauses: list[float] = []
            cursor = 0.0
            for index, (scene, scene_text) in enumerate(zip(scenes, scene_texts)):
                hint = scene.get("delivery_hint") if isinstance(scene.get("delivery_hint"), dict) else {}
                rate, pitch = _delivery(str(scene.get("mood") or ""), hint)
                part = temp / f"scene-{index:02d}.mp3"
                if provider == "elevenlabs":
                    events = _render_elevenlabs(
                        scene_text, part, hint=hint,
                        previous_text=scene_texts[index - 1] if index > 0 else "",
                        next_text=scene_texts[index + 1] if index + 1 < len(scene_texts) else "",
                    )
                else:
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
                pause = max(0.18, min(0.70, float(hint.get("pause_after_ms", 280)) / 1000.0))
                scene_pauses.append(pause)
                delivery_log.append({
                    "mood": str(scene.get("mood") or ""),
                    "emotion": str(hint.get("emotion") or "neutral"),
                    "intensity": str(hint.get("intensity", 0.0)),
                    "confidence": str(hint.get("confidence", 0.0)),
                    "pace": str(hint.get("pace") or "steady"),
                    "pause_after_ms": str(round(pause * 1000)),
                    "rate": rate if provider == "edge-tts" else "provider-managed",
                    "pitch": pitch if provider == "edge-tts" else "provider-managed",
                })
                cursor += duration + (pause if index < len(scenes) - 1 else 0.0)
                parts.append(part)
            _merge_segments(parts, audio_path, pause_seconds=scene_pauses)
    else:
        if provider == "elevenlabs":
            all_events = _render_elevenlabs(normalized_script, audio_path)
        else:
            all_events = asyncio.run(_render(normalized_script, audio_path))

    cues: list[tuple[float, float, str]] = []
    if scenes:
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
        "provider": provider,
        "model": str(env("ELEVENLABS_MODEL_ID") or "eleven_v4") if provider == "elevenlabs" else "edge-tts",
        "voice": _voice(provider),
        "narrator_locked": True,
        "caption_mode": "word-boundary phrase captions",
        "duration_seconds": _duration(audio_path),
        "caption_count": len(cues),
        "scene_timings": scene_timings,
        "delivery_profiles": delivery_log,
        "ok": True,
    }
