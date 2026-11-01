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
from app.spiritual_shorts import generate_shorts_content
from app.media_qa import validate_render_package
from app.spiritual_tts import synthesize_with_captions
from app.bamo_production_renderer import render_bamo_shorts
from app.utils import OUTPUT_DIR, load_channel_config, save_json, utc_now_iso
from app.youtube_client import upload_video
from app.youtube_history import (
    add_fingerprint_tag, build_generation_history, fetch_recent_channel_videos, require_unique,
)
from app.bamo_editorial_review import review_package
from app.bamo_agent_council import review_with_council

TEHRAN = ZoneInfo("Asia/Tehran")


def next_publish_at(now: datetime | None = None, *, lead_minutes: int = 30) -> str:
    """Choose the next configured Tehran publication slot after the safety lead time."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    local = current.astimezone(TEHRAN)
    cfg = load_channel_config()
    schedule = cfg.get("schedule") or {}
    raw_slots = schedule.get("publication_times_local") or ["07:00", "10:00", "12:00", "15:00", "18:00", "21:00"]
    candidates = []
    for raw in raw_slots:
        try:
            hour, minute = (int(part) for part in str(raw).split(":", 1))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                continue
            slot = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if slot > local + timedelta(minutes=lead_minutes):
                candidates.append(slot)
        except (TypeError, ValueError):
            continue
    if not candidates:
        next_day = local + timedelta(days=1)
        for raw in raw_slots:
            try:
                hour, minute = (int(part) for part in str(raw).split(":", 1))
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    candidates.append(next_day.replace(hour=hour, minute=minute, second=0, microsecond=0))
            except (TypeError, ValueError):
                continue
    if not candidates:
        raise ValueError("No valid schedule.publication_times_local slots configured")
    return min(candidates).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_state(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {"recent": []}
    except (OSError, ValueError, TypeError):
        return {"recent": []}


def _chapter_timestamp(seconds: float) -> str:
    value = max(0, int(seconds))
    return f"{value // 3600:02d}:{(value % 3600) // 60:02d}:{value % 60:02d}" if value >= 3600 else f"{value // 60:02d}:{value % 60:02d}"


def _hashtags(content: dict[str, Any]) -> str:
    values = ["#12bamo", "#BAMO", "#بامو"]
    for raw in content.get("tags") or []:
        tag = str(raw).strip()
        if tag.casefold() in {"bamo", "12bamo", "بامو"}:
            continue
        slug = re.sub(r"[^\w\u0600-\u06FF]+", "_", tag, flags=re.UNICODE).strip("_")
        if slug and slug.casefold() not in {item.casefold().lstrip("#") for item in values}:
            values.append("#" + slug)
        if len(values) >= 7:
            break
    return " ".join(values)


def _description(content: dict[str, Any], render: dict[str, Any], audio_duration: float) -> str:
    if content.get("format") == "shorts":
        parts = [
            content.get("description", "").strip(),
            "گویندگی فارسی با صدای هوش مصنوعی تولید شده است.",
        ]
        if render.get("visual_source") == "scene-matched-stills":
            if render.get("contains_synthetic_visuals"):
                parts.append("بخشی از تصویر صحنه‌ها به‌صورت مصنوعی و هماهنگ با گفتار ساخته شده است.")
            else:
                parts.append("تصویر صحنه‌ها از عکس‌های آزاد ویکی‌مدیا کامنز و هماهنگ با موضوع هر بخش انتخاب شده است.")
        credits = render.get("pexels_credits") or []
        if credits:
            parts += ["", "تصاویر:", *credits]
        parts += ["", _hashtags(content)]
        return "\n".join(x for x in parts if x is not None).strip()[:4900]
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
    parts += ["", _hashtags(content)]
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
        channel_videos: list[dict[str, Any]] = []
        if not dry_run:
            stage = "YouTube channel history and duplicate preflight"
            channel_videos = fetch_recent_channel_videos(max_results=200)
            logger.info("YouTube channel inventory loaded videos=%s; remote channel is the source of truth", len(channel_videos))
            generation_history = build_generation_history(history, channel_videos)
        else:
            generation_history = history
        channel_config = load_channel_config()
        content_format = str((channel_config.get("content") or {}).get("production_format") or "long").lower()
        if content_format not in {"shorts", "long"}:
            raise ValueError("config content.production_format must be 'shorts' or 'long'")
        content = generate_shorts_content(generation_history) if content_format == "shorts" else generate_content(generation_history)
        if not dry_run:
            require_unique(content, generation_history.get("recent", channel_videos))
            logger.info("YouTube duplicate gate passed title=%r", content.get("title"))
        save_json(out_dir / "content.json", content)
        (out_dir / "script.txt").write_text(content["script"], encoding="utf-8")
        logger.info("script passed quality gates title=%r words=%s sections=%s", content["title"], content["word_count"], len(content["sections"]))

        stage = "fixed-voice TTS and captions"
        audio_path = out_dir / "narration.mp3"
        captions_path = out_dir / "captions.srt"
        tts = synthesize_with_captions(
            content["script"], audio_path, captions_path,
            scenes=content.get("scenes") if content_format == "shorts" else None,
        )
        logger.info("TTS ready voice=%s duration_seconds=%.2f caption_count=%s", tts["voice"], tts["duration_seconds"], tts["caption_count"])

        stage = "video render and QA"
        if content_format != "shorts":
            raise RuntimeError(
                "BAMO production is locked to the approved CPU 3D motion-graphics renderer; "
                "legacy stock/abstract render modes are disabled."
            )
        render = render_bamo_shorts(
            title=content["title"], thumbnail_text=content["thumbnail_text"],
            audio_path=audio_path, captions_path=captions_path,
            out_dir=out_dir, run_id=run_id, scenes=content.get("scenes", []),
            scene_timings=tts.get("scene_timings") or [],
            hook_overlay=content["scenes"][0]["on_screen_text"],
        )
        logger.info("render passed source=%s scenes=%s duration_seconds=%.2f bytes=%s", render["visual_source"], render["visual_scene_count"], render["duration_seconds"], Path(render["video_path"]).stat().st_size)
        media_quality = validate_render_package(render, audio_path, video_format=content_format, tts_meta=tts)
        if not media_quality.get("ok"):
            raise RuntimeError("media QA failed: " + ", ".join(media_quality.get("errors") or []))
        logger.info("media QA passed thumbnail=%s cues=%s", media_quality["checks"].get("thumbnail_dimensions"), media_quality["checks"].get("caption_cues"))
        stage = "BAMO 11-role editorial review"
        editorial_review = review_package(
            content, channel_videos=channel_videos, captions_path=captions_path,
            policy=channel_config.get("content") or {},
        )
        save_json(out_dir / "editorial_review.json", editorial_review)
        logger.info("BAMO deterministic role gates passed roles=%s", len(editorial_review["roles"]))

        stage = "BAMO independent 11-agent council"
        agent_council = review_with_council(
            content, render=render, media_qa=media_quality,
            memory_dir=Path(os.getenv("BAMO_AGENT_MEMORY_DIR") or "state/agent_memory"),
        )
        save_json(out_dir / "agent_council.json", agent_council)
        logger.info(
            "BAMO independent council passed agents=%s distinct_provider_models=%s approvals=%s average_score=%s",
            agent_council["agents_completed"], agent_council["distinct_provider_models_observed"],
            agent_council["approvals"], agent_council["average_score"],
        )
        description = _description(content, render, float(tts["duration_seconds"]))
        upload: dict[str, Any] = {"skipped": True, "reason": "dry-run"}
        if not dry_run:
            stage = "YouTube upload and scheduling"
            scheduled_at = None if upload_private else next_publish_at()
            cfg = load_channel_config()
            category_id = str((cfg.get("publishing") or {}).get("category_id") or "22")
            logger.info("uploading video mode=%s slot=%s", "private-draft" if upload_private else "scheduled-public", scheduled_at)
            if render.get("contains_synthetic_visuals"):
                os.environ["YOUTUBE_CONTAINS_SYNTHETIC_MEDIA"] = "true"
            if not dry_run:
                require_unique(content, channel_videos)
            upload_tags = add_fingerprint_tag(content["tags"], content["script"])
            upload = upload_video(
                video_path=Path(render["video_path"]), title=content["title"],
                description=description, tags=upload_tags, privacy="private" if upload_private else "public",
                thumbnail_path=Path(render["thumbnail_path"]), category_id=category_id,
                publish_at=scheduled_at,
            )
            if not upload.get("ok"):
                raise RuntimeError(str(upload.get("error") or "YouTube upload/scheduling failed"))
            logger.info("YouTube upload complete mode=%s video_id=%s slot=%s", "private-draft" if upload_private else "scheduled-public", upload.get("video_id"), upload.get("scheduled_for"))
            recent = history.get("recent") if isinstance(history.get("recent"), list) else []
            recent.append({
                "title": content["title"],
                "topic": content.get("topic") or (content["sections"][1]["heading"] if len(content.get("sections") or []) > 1 else content["title"]),
                "video_id": upload.get("video_id"), "url": upload.get("url"),
                "scheduled_for": upload.get("scheduled_for"), "uploaded_at": utc_now_iso(),
                "script_fingerprint": __import__("app.youtube_history", fromlist=["content_fingerprint"]).content_fingerprint(content["script"]),
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
            "editorial_review": editorial_review, "agent_council": agent_council,
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
