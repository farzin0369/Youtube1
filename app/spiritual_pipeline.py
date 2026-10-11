"""Daily Persian spiritual/personal-growth production and YouTube publishing."""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any

from app.spiritual_content import generate_content
from app.media_qa import validate_render_package
from app.spiritual_tts import synthesize_with_captions
from app.spiritual_video import render_video
from app.utils import OUTPUT_DIR, load_channel_config, save_json, utc_now_iso
from app.youtube_client import upload_video

TEHRAN = ZoneInfo("Asia/Tehran")


def next_publish_at(now: datetime | None = None, *, lead_minutes: int = 30) -> str:
    """Return the next safe 18:00 Tehran slot, at least lead_minutes ahead."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    local = current.astimezone(TEHRAN)
    candidate = local.replace(hour=18, minute=0, second=0, microsecond=0)
    if candidate <= local + timedelta(minutes=lead_minutes):
        candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_state(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {"recent": []}
    except (OSError, ValueError, TypeError):
        return {"recent": []}


def _chapter_timestamp(seconds: float) -> str:
    value = max(0, int(seconds))
    return f"{value // 3600:02d}:{(value % 3600) // 60:02d}:{value % 60:02d}" if value >= 3600 else f"{value // 60:02d}:{value % 60:02d}"


def _description(content: dict[str, Any], render: dict[str, Any], audio_duration: float) -> str:
    section_words = [max(1, len(section["text"].split())) for section in content["sections"]]
    total = sum(section_words) or 1
    cursor = 0.0
    chapters = []
    for section, weight in zip(content["sections"], section_words):
        chapters.append(f"{_chapter_timestamp(cursor)} {section['heading'][:65]}")
        cursor += audio_duration * weight / total
    parts = [content.get("description", "").strip(), "", "فصل‌های ویدئو:", *chapters, "",
             "این ویدئو برای تأمل و آموزش عمومی ساخته شده و توصیهٔ مالی، پزشکی یا درمانی شخصی نیست.",
             "گویندگی فارسی با صدای ثابت هوش مصنوعی تولید شده است."]
    credits = render.get("pexels_credits") or []
    if credits:
        parts += ["", "تصاویر:", *credits]
    parts += ["", "#ImamAli110 #The110Path #امام_علی #رشد_فردی #معنویت #توکل #برکت #سواد_مالی"]
    return "\n".join(x for x in parts if x is not None).strip()[:4900]


def _configure_logging(run_id: str) -> logging.Logger:
    log_dir = Path(os.getenv("LOGS_DIR") or "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    handlers = [
        logging.FileHandler(log_dir / f"daily-{run_id}.log", encoding="utf-8"),
        logging.StreamHandler(),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        handlers=handlers,
        force=True,
    )
    return logging.getLogger("tt_growth")


def _safe_error(message: str) -> str:
    for name in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN", "GROQ_API_KEY", "PEXELS_API_KEY"):
        secret = (os.getenv(name) or "").strip()
        if secret:
            message = message.replace(secret, "[REDACTED]")
    return message[:400]


def run(*, dry_run: bool = False, upload_private: bool = False) -> dict[str, Any]:
    started_at = utc_now_iso()
    run_id = re.sub(r"[^A-Za-z0-9_-]", "_", os.getenv("GITHUB_RUN_ID") or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
    logger = _configure_logging(run_id)
    logger.info("pipeline started run_id=%s dry_run=%s", run_id, dry_run)
    out_dir = OUTPUT_DIR / "spiritual" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path = Path(os.getenv("CHANNEL_HISTORY_PATH") or "state/history.json")
    stage = "history and script generation"
    try:
        history = _load_state(state_path)
        content = generate_content(history)
        save_json(out_dir / "content.json", content)
        (out_dir / "script.txt").write_text(content["script"], encoding="utf-8")
        logger.info("script passed quality gates title=%r words=%s sections=%s", content["title"], content["word_count"], len(content["sections"]))

        stage = "fixed-voice TTS and captions"
        audio_path = out_dir / "narration.mp3"
        captions_path = out_dir / "captions.srt"
        tts = synthesize_with_captions(content["script"], audio_path, captions_path)
        logger.info("TTS ready voice=%s duration_seconds=%.2f caption_count=%s", tts["voice"], tts["duration_seconds"], tts["caption_count"])

        stage = "video render and QA"
        render = render_video(
            title=content["title"], thumbnail_text=content["thumbnail_text"],
            keywords=content["visual_keywords"], audio_path=audio_path,
            captions_path=captions_path, out_dir=out_dir, run_id=run_id,
        )
        logger.info("render passed source=%s scenes=%s duration_seconds=%.2f bytes=%s", render["visual_source"], render["visual_scene_count"], render["duration_seconds"], Path(render["video_path"]).stat().st_size)
        media_quality = validate_render_package(
            {
                "ok": render.get("ok"),
                "video_path": render.get("video_path"),
                "thumbnail_path": render.get("thumbnail_path"),
                "captions_path": render.get("captions_path"),
                "duration": render.get("duration_seconds"),
                "on_screen_captions": render.get("on_screen_captions"),
            },
            audio_path,
        )
        if not media_quality.get("ok"):
            raise RuntimeError("media QA failed: " + ", ".join(media_quality.get("errors") or []))
        logger.info("media QA passed thumbnail=%s cues=%s", media_quality["checks"].get("thumbnail_dimensions"), media_quality["checks"].get("caption_cues"))
        description = _description(content, render, float(tts["duration_seconds"]))
        upload: dict[str, Any] = {"skipped": True, "reason": "dry-run"}
        if not dry_run:
            stage = "YouTube upload and scheduling"
            scheduled_at = None if upload_private else next_publish_at()
            cfg = load_channel_config()
            category_id = str((cfg.get("publishing") or {}).get("category_id") or "22")
            logger.info("uploading video mode=%s slot=%s", "private-draft" if upload_private else "scheduled-public", scheduled_at)
            upload = upload_video(
                video_path=Path(render["video_path"]), title=content["title"],
                description=description, tags=content["tags"], privacy="private" if upload_private else "public",
                thumbnail_path=Path(render["thumbnail_path"]), category_id=category_id,
                publish_at=scheduled_at,
            )
            if not upload.get("ok"):
                raise RuntimeError(str(upload.get("error") or "YouTube upload/scheduling failed"))
            logger.info("YouTube upload complete mode=%s video_id=%s slot=%s", "private-draft" if upload_private else "scheduled-public", upload.get("video_id"), upload.get("scheduled_for"))
            recent = history.get("recent") if isinstance(history.get("recent"), list) else []
            recent.append({
                "title": content["title"], "topic": content["sections"][1]["heading"],
                "video_id": upload.get("video_id"), "url": upload.get("url"),
                "scheduled_for": upload.get("scheduled_for"), "uploaded_at": utc_now_iso(),
            })
            history["recent"] = recent[-90:]
            history["updated_at"] = utc_now_iso()
            state_path.parent.mkdir(parents=True, exist_ok=True)
            save_json(state_path, history)

        comments: dict[str, Any] = {"skipped": True, "reason": "dry-run"}
        if not dry_run and upload.get("ok"):
            stage = "bounded comment moderation"
            try:
                from app.spiritual_comments import reply_to_recent_comments
                comments = reply_to_recent_comments(state_path=Path("state/comment_replies.json"), max_replies=3)
                logger.info("comment pass checked=%s replied=%s skipped=%s", comments.get("checked"), comments.get("replied"), comments.get("skipped"))
            except Exception as exc:
                comments = {"ok": False, "error_type": type(exc).__name__}
                logger.warning("comment moderation pass skipped (%s).", type(exc).__name__)

        result = {
            "run_id": run_id, "started_at": started_at, "finished_at": utc_now_iso(), "dry_run": dry_run,
            "title": content["title"], "word_count": content["word_count"],
            "tts": {key: value for key, value in tts.items() if key != "path"}, "media_qa": media_quality,
            "render": render, "upload": upload, "comments": comments,
        }
        save_json(out_dir / "result.json", result)
        logger.info("pipeline completed upload_ok=%s comment_replies=%s", upload.get("ok", False), comments.get("replied", 0))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    except Exception as exc:
        logger.error("pipeline failed stage=%s error_type=%s detail=%s", stage, type(exc).__name__, _safe_error(str(exc)))
        raise RuntimeError(f"pipeline failed during {stage} ({type(exc).__name__})") from None
