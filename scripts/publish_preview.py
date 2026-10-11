#!/usr/bin/env python3
"""Publish one reviewed, quality-gated dry-run artifact without regenerating it."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.media_qa import validate_render_package
from app.spiritual_pipeline import _description
from app.utils import load_channel_config
from app.youtube_client import probe_youtube_auth, upload_video


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path.name}")
    return value


def load_reviewed_package(artifact_dir: Path) -> dict[str, Any]:
    """Find exactly one complete, QA-passed, non-publishing production package."""
    packages: list[dict[str, Any]] = []
    for result_path in artifact_dir.rglob("result.json"):
        try:
            result = _read_json(result_path)
            if result.get("dry_run") is not True:
                continue
            if (result.get("media_qa") or {}).get("ok") is not True:
                continue
            if (result.get("upload") or {}).get("skipped") is not True:
                continue
            run_dir = result_path.parent
            content = _read_json(run_dir / "content.json")
            render = result.get("render") or {}
            tts = result.get("tts") or {}
            video_path = run_dir / Path(str(render.get("video_path") or "video.mp4")).name
            thumbnail_path = run_dir / Path(str(render.get("thumbnail_path") or "thumbnail.jpg")).name
            captions_path = run_dir / Path(str(render.get("captions_path") or "captions.srt")).name
            audio_path = run_dir / "narration.mp3"
            if not all(path.is_file() and path.stat().st_size > 0 for path in (
                video_path, thumbnail_path, captions_path, audio_path,
            )):
                continue
            title = str(content.get("title") or "").strip()
            if not title or title != str(result.get("title") or "").strip():
                continue
            qa = validate_render_package(
                {
                    "ok": render.get("ok"),
                    "video_path": str(video_path),
                    "thumbnail_path": str(thumbnail_path),
                    "captions_path": str(captions_path),
                    "duration": render.get("duration_seconds"),
                    "on_screen_captions": render.get("on_screen_captions"),
                },
                audio_path,
            )
            if not qa.get("ok"):
                continue
            duration = float(tts.get("duration_seconds") or render.get("duration_seconds") or 0)
            description = _description(content, render, duration)
            packages.append({
                "run_dir": run_dir,
                "result": result,
                "content": content,
                "render": render,
                "video_path": video_path,
                "thumbnail_path": thumbnail_path,
                "captions_path": captions_path,
                "audio_path": audio_path,
                "title": title,
                "description": description,
                "tags": list(content.get("tags") or [])[:20],
            })
        except (OSError, ValueError, TypeError, KeyError):
            continue
    if len(packages) != 1:
        raise ValueError(f"Expected exactly one complete reviewed package; found {len(packages)}")
    return packages[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--publish-at", required=True, help="Exact UTC ISO-8601 schedule approved by the owner")
    parser.add_argument("--publish", action="store_true", help="Upload and schedule the already-reviewed package")
    args = parser.parse_args()

    package = load_reviewed_package(args.artifact_dir)
    cfg = load_channel_config()
    category_id = str((cfg.get("publishing") or {}).get("category_id") or "22")
    summary = {
        "title": package["title"],
        "publish_at": args.publish_at,
        "video_file": package["video_path"].name,
        "thumbnail_file": package["thumbnail_path"].name,
        "captions_file": package["captions_path"].name,
        "media_qa": "passed",
        "comment_replies": "disabled",
    }
    if not args.publish:
        print(json.dumps({**summary, "upload": "not performed; pass --publish after owner approval"}, ensure_ascii=False))
        return 0

    auth = probe_youtube_auth()
    if not auth.get("ok"):
        raise RuntimeError("YouTube OAuth preflight failed; no upload was started")

    uploaded = upload_video(
        video_path=package["video_path"],
        title=package["title"],
        description=package["description"],
        tags=package["tags"],
        privacy="public",
        thumbnail_path=package["thumbnail_path"],
        category_id=category_id,
        publish_at=args.publish_at,
    )
    if not uploaded.get("ok"):
        raise RuntimeError(str(uploaded.get("error") or "YouTube upload/scheduling failed"))
    print(json.dumps({**summary, "upload": uploaded}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
