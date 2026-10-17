"""Optional, non-blocking short derivatives for long-form channel videos."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def build_clip_derivatives_if_enabled(
    video_path: str | Path,
    output_dir: str | Path,
    *,
    video_format: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Create local clip derivatives only for long-form output; never publish them."""
    settings = config.get("clip_derivatives") or {}
    if not settings.get("enabled", False):
        return {"status": "skipped", "reason": "disabled"}
    if str(video_format).lower() != "long":
        return {"status": "skipped", "reason": "source_is_not_long_form"}
    try:
        from app.clip_automation import build_clips

        manifest = build_clips(
            Path(video_path),
            Path(output_dir),
            clip_seconds=float(settings.get("clip_seconds", 30)),
            count=int(settings.get("count", 3)),
            rights_confirmed=True,
        )
        return {
            "status": "ok",
            "manifest_path": str(Path(output_dir) / "manifest.json"),
            "candidate_count": len(manifest.get("candidates") or []),
            "auto_publish": False,
        }
    except Exception as exc:
        logger.warning("clip derivatives failed non-fatally (%s)", type(exc).__name__)
        return {"status": "failed_non_fatal", "error_type": type(exc).__name__}
