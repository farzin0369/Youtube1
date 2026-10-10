"""Pre-upload validation for generated media; deliberately independent of model providers."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _srt_timestamp(value: str) -> float:
    match = re.fullmatch(r"(\d{2,}):(\d{2}):(\d{2}),(\d{3})", value.strip())
    if not match:
        raise ValueError("invalid SRT timestamp: " + value)
    hours, minutes, seconds, millis = (int(part) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def validate_render_package(render_meta: dict[str, Any], audio_path: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    checks: dict[str, Any] = {}
    if not render_meta.get("ok"):
        errors.append("renderer_reported_failure")
    if render_meta.get("on_screen_captions") is not True:
        errors.append("visible_captions_missing")
    for field, error_name in (
        ("video_path", "missing_or_empty_video"),
        ("thumbnail_path", "missing_or_empty_thumbnail"),
        ("captions_path", "missing_or_empty_captions"),
    ):
        raw = render_meta.get(field)
        path = Path(str(raw)) if raw else None
        valid = bool(path and path.is_file() and path.stat().st_size > 0)
        checks[field] = {"path": str(path) if path else None, "ok": valid, "bytes": path.stat().st_size if valid else 0}
        if not valid:
            errors.append(error_name)
    if audio_path is not None:
        valid_audio = Path(audio_path).is_file() and Path(audio_path).stat().st_size > 0
        checks["audio_path"] = {"path": str(audio_path), "ok": valid_audio}
        if not valid_audio:
            errors.append("missing_or_empty_audio")
    try:
        duration = float(render_meta.get("duration") or 0)
        if duration <= 0:
            errors.append("invalid_video_duration")
        checks["duration_seconds"] = duration
    except (TypeError, ValueError):
        errors.append("invalid_video_duration")
        duration = 0.0

    captions_path = Path(str(render_meta.get("captions_path") or ""))
    if captions_path.is_file() and captions_path.stat().st_size > 0:
        try:
            text = captions_path.read_text(encoding="utf-8-sig").strip()
            blocks = [block for block in re.split(r"\n\s*\n", text) if block.strip()]
            if not blocks:
                errors.append("empty_srt")
            last_end = 0.0
            for block in blocks:
                lines = [line.strip() for line in block.splitlines() if line.strip()]
                timing = next((line for line in lines if "-->" in line), None)
                if timing is None:
                    raise ValueError("caption block has no timing line")
                start_text, end_text = [part.strip() for part in timing.split("-->", 1)]
                start, end = _srt_timestamp(start_text), _srt_timestamp(end_text)
                if end <= start or start < last_end - 0.05:
                    raise ValueError("caption timing is non-positive or overlaps out of order")
                last_end = end
            checks["caption_cues"] = len(blocks)
            checks["caption_end_seconds"] = last_end
            if duration and last_end > duration + 1.5:
                errors.append("captions_exceed_video_duration")
        except (OSError, ValueError) as exc:
            errors.append("invalid_srt: " + str(exc))
    return {"ok": not errors, "errors": errors, "checks": checks}
