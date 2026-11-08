#!/usr/bin/env python3
"""BAMO Shorts factory — render with topic visuals. Publish only if --publish."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.bamo_brain import append_history, build_youtube_package, mark_used, select_idea
from scripts.bamo_hyperframes_factory import render_short


def _make_thumbnail(video: Path) -> Path:
    thumb = video.with_suffix(".jpg")
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        "2.5",
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(thumb),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    if not thumb.exists() or thumb.stat().st_size < 1000:
        raise RuntimeError(f"thumbnail generation failed: {thumb}")
    print(f"thumbnail -> {thumb}", flush=True)
    return thumb


def _upload(video: Path, pkg: dict, thumb: Path | None, *, privacy: str) -> dict:
    from app.youtube_client import upload_video

    return upload_video(
        video_path=video,
        title=pkg["title"],
        description=pkg["description"],
        tags=pkg["tags"],
        privacy=privacy,
        thumbnail_path=thumb,
        category_id=pkg.get("category_id") or "27",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="Upload (default OFF)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--privacy", default="private", choices=["public", "unlisted", "private"])
    ap.add_argument("--skip-comments", action="store_true")
    ap.add_argument("--prefer-category", default="", help="e.g. astronomy, physics")
    args = ap.parse_args()

    prefer = args.prefer_category.strip() or None
    idea = select_idea(prefer_curated=True, prefer_category=prefer)
    pkg = build_youtube_package(idea)
    print(
        json.dumps(
            {
                "selected": idea.get("id"),
                "title": pkg["title"],
                "category": idea.get("category"),
                "publish": bool(args.publish),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "package": pkg}, ensure_ascii=False))
        return 0

    out = ROOT / "outputs" / "daily" / f"BAMO_{idea.get('id')}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.mp4"
    video = render_short(
        pkg["narration"],
        out,
        title=pkg.get("title") or idea.get("title") or "",
        hook=pkg.get("hook") or idea.get("hook") or "",
        category=idea.get("category") or "",
    )
    thumb = _make_thumbnail(video)

    upload_result: dict = {"ok": False, "skipped": True}
    if args.publish:
        upload_result = _upload(video, pkg, thumb, privacy=args.privacy)
        if upload_result.get("ok"):
            mark_used(str(idea.get("id")))

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "idea_id": idea.get("id"),
        "title": pkg["title"],
        "category": idea.get("category"),
        "video": str(video),
        "thumbnail": str(thumb),
        "upload": upload_result,
    }
    append_history(record)
    print(json.dumps(record, ensure_ascii=False, default=str))
    return 0 if (not args.publish or upload_result.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
