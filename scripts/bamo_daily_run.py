#!/usr/bin/env python3
"""Daily BAMO English Shorts factory.

1) Brain selects one idea from the bank
2) HyperFrames official kinetic-type renders the video
3) YouTube public upload with title/description/tags/hashtags
4) Reply to a few recent comments (English, safe)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.bamo_brain import append_history, build_youtube_package, mark_used, select_idea
from scripts.bamo_hyperframes_factory import render_short


def _upload(video: Path, pkg: dict, *, privacy: str, dry_run: bool) -> dict:
    if dry_run:
        return {"ok": True, "dry_run": True, "privacy": privacy, "title": pkg["title"]}
    from app.youtube_client import upload_video

    # Prefer English language fields via env for containsSyntheticMedia=false
    return upload_video(
        video_path=video,
        title=pkg["title"],
        description=pkg["description"],
        tags=pkg["tags"],
        privacy=privacy,
        thumbnail_path=None,  # HyperFrames frame can be used later; allow public without custom thumb if client enforces
        category_id=pkg.get("category_id") or "27",
    )


def _reply_comments(max_replies: int, dry_run: bool) -> dict:
    if dry_run or max_replies <= 0:
        return {"ok": True, "skipped": True}
    try:
        from app.channel_ops import reply_to_recent_comments

        return reply_to_recent_comments(max_videos=3, max_comments_per_video=max_replies)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="Upload publicly to YouTube")
    ap.add_argument("--dry-run", action="store_true", help="Select + metadata only, no render")
    ap.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])
    ap.add_argument("--skip-comments", action="store_true")
    args = ap.parse_args()

    idea = select_idea()
    pkg = build_youtube_package(idea)
    print(json.dumps({"selected": idea.get("id"), "title": pkg["title"]}, ensure_ascii=False), flush=True)

    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "package": pkg}, ensure_ascii=False))
        return 0

    out = ROOT / "outputs" / "daily" / f"BAMO_{idea.get('id')}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.mp4"
    video = render_short(pkg["narration"], out)

    upload_result: dict = {"ok": False, "skipped": True}
    if args.publish:
        # youtube_client currently requires thumbnail for public; fall back to unlisted if blocked
        upload_result = _upload(video, pkg, privacy=args.privacy, dry_run=False)
        if not upload_result.get("ok") and "thumbnail" in str(upload_result.get("error") or "").lower():
            print("[warn] public needs thumbnail; retrying as unlisted", flush=True)
            upload_result = _upload(video, pkg, privacy="unlisted", dry_run=False)

    if upload_result.get("ok") and not upload_result.get("dry_run"):
        mark_used(str(idea.get("id")))

    comments = {"ok": True, "skipped": True}
    if args.publish and not args.skip_comments:
        comments = _reply_comments(5, dry_run=False)

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "idea_id": idea.get("id"),
        "title": pkg["title"],
        "video": str(video),
        "upload": upload_result,
        "comments": comments,
    }
    append_history(record)
    print(json.dumps(record, ensure_ascii=False, default=str))
    return 0 if (not args.publish or upload_result.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
