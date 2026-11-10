#!/usr/bin/env python3
"""One run = one never-used idea -> Persian narrated HTML film -> QC -> (optional) YouTube.

Fail-closed: nothing is uploaded unless every QC check passes.
  python -m fa_factory.run --dry-run
  python -m fa_factory.run                       # render only
  python -m fa_factory.run --publish --privacy private
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fa_factory import bank, compose, tts  # noqa: E402

OUT = ROOT / "outputs" / "fa_daily"
HYPERFRAMES = "hyperframes@0.9.19"  # same pinned version the existing pipeline uses


def package(idea: dict) -> dict:
    title = idea["title"][:90]
    tags = list(dict.fromkeys(idea.get("keywords", []) + ["بامو", "شگفتی", "علم", "shorts", "12bamo"]))[:15]
    tag_list = [f"#{t.replace(' ', '_')}" for t in tags[:5]]
    hashtags = " ".join(dict.fromkeys(tag_list + ["#shorts", "#بامو"]))
    desc = "\n".join([idea["sentences"][0], "", " ".join(idea["sentences"][1:3]), "", "هر روز یک شگفتی با بامو · @12bamo", hashtags])
    return {"title": title, "description": desc[:4900], "tags": tags, "category_id": "27"}


def qc(video: Path, expected_dur: float) -> dict:
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)], text=True))
    v = next((s for s in probe["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in probe["streams"] if s["codec_type"] == "audio"), None)
    dur = float(probe["format"]["duration"])
    vol = subprocess.run(["ffmpeg", "-i", str(video), "-af", "volumedetect", "-vn", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    max_vol = None
    for line in vol.splitlines():
        if "max_volume" in line:
            max_vol = float(line.split("max_volume:")[1].split("dB")[0])
    checks = {
        "has_video": v is not None,
        "is_1080x1920": bool(v) and (v["width"], v["height"]) == (1080, 1920),
        "has_audio": a is not None,
        "audible": max_vol is not None and max_vol > -30.0,
        "duration_ok": 12 <= dur <= 58,
        "duration_matches_audio": abs(dur - expected_dur) < 2.5,
        "size_ok": video.stat().st_size > 300_000,
    }
    return {"ok": all(checks.values()), "checks": checks, "duration": dur, "max_volume_db": max_vol}


def render(workdir: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["npx", "--yes", HYPERFRAMES, "render", "-o", str(out)]
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(workdir), check=True, timeout=3000)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    ap.add_argument("--dry-run", action="store_true", help="pick idea + metadata only")
    ap.add_argument("--build-only", action="store_true", help="audio + HTML only, skip render")
    ap.add_argument("--fake-tts", action="store_true", help="offline test: silent audio")
    ap.add_argument("--prefer-category", default="")
    ap.add_argument("--idea-id", default="", help="force a specific idea (test only; still recorded as used on publish)")
    args = ap.parse_args()

    if args.idea_id:
        idea = next(i for i in bank.load() if i["id"] == args.idea_id)
    else:
        idea = bank.select_idea(prefer_category=args.prefer_category or None)
    errs = bank.validate(idea)
    if errs:
        raise SystemExit(f"idea failed validation: {errs}")
    pkg = package(idea)
    print(json.dumps({"idea": idea["id"], "title": idea["title"], "category": idea["category"], "visual": compose.pick_mode(idea)}, ensure_ascii=False), flush=True)
    if args.dry_run:
        print(json.dumps({"ok": True, "package": pkg}, ensure_ascii=False, indent=2))
        return 0

    work = Path("/tmp/fa_work") / idea["id"]
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    audio, beats, dur = tts.build_audio(idea["sentences"], work, fake=args.fake_tts)
    compose.write_project(idea, beats, dur, audio, work)
    print(f"built html project: {work} duration={dur:.1f}s", flush=True)
    if args.build_only:
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    video = OUT / f"BAMO_FA_{idea['id']}_{stamp}.mp4"
    render(work, video)
    result = qc(video, dur)
    print(json.dumps({"qc": result}, ensure_ascii=False), flush=True)
    if not result["ok"]:
        print("QC FAILED -> not uploading", flush=True)
        return 2

    upload: dict = {"ok": False, "skipped": True}
    if args.publish:
        thumb = video.with_suffix(".jpg")
        subprocess.run(["ffmpeg", "-y", "-ss", "2.5", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(thumb)], check=True, capture_output=True)
        from app.youtube_client import upload_video  # existing, tested uploader

        upload = upload_video(video_path=video, title=pkg["title"], description=pkg["description"],
                              tags=pkg["tags"], privacy=args.privacy, thumbnail_path=thumb, category_id=pkg["category_id"])
        if upload.get("ok"):
            bank.record_use(idea, ok=True, video=str(video), upload=upload)
    print(json.dumps({"upload": upload}, ensure_ascii=False, default=str))
    return 0 if (not args.publish or upload.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
