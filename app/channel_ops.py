"""Idempotent YouTube comment moderation with a human-review queue for uncertain cases."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.local_ai import local_enabled, ollama_available, ollama_generate
from app.utils import (
    env, has_openai, has_qwen, load_content_policy, load_channel_config,
    qwen_client_kwargs, save_json, utc_now_iso,
)


def _youtube():
    from googleapiclient.discovery import build
    from app.youtube_client import _build_credentials
    return build("youtube", "v3", credentials=_build_credentials())


def _has_our_reply(thread: dict[str, Any], own_channel_id: str) -> bool:
    if not own_channel_id:
        return False
    replies = thread.get("replies", {}).get("comments", []) or []
    return any(
        str(reply.get("snippet", {}).get("authorChannelId", {}).get("value") or "") == own_channel_id
        for reply in replies
    )


def _looks_like_spam(text: str) -> bool:
    lower = text.lower()
    urls = re.findall(r"https?://|www\.", lower)
    words = re.sub(r"\s+", " ", lower).split()
    repeated = len(words) >= 8 and len(set(words)) <= 3
    promotional = any(term in lower for term in ("subscribe my channel", "follow me", "crypto signal", "earn money fast"))
    return len(urls) >= 2 or promotional or repeated


def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else default
    except (OSError, ValueError, TypeError):
        return default


def _generate_reply(prompt: str) -> str:
    if local_enabled() and ollama_available():
        return ollama_generate(
            prompt,
            "تو مدیر محترمانه و دقیق کانال ImamAli110 هستی. اگر نیاز به بررسی انسانی است فقط PENDING بنویس.",
            env("LOCAL_LLM_MODEL") or "qwen2.5:7b",
        )
    if has_qwen():
        from openai import OpenAI
        kwargs = qwen_client_kwargs()
        model = env("QWEN_MODEL") or env("DASHSCOPE_MODEL") or "qwen-plus"
        response = OpenAI(api_key=kwargs["api_key"], base_url=kwargs["base_url"]).chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "پاسخ‌گوی محترمانهٔ فارسی کانال ImamAli110 هستی. در موارد حساس فقط PENDING بنویس."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return str(response.choices[0].message.content or "").strip()
    if has_openai():
        from openai import OpenAI
        response = OpenAI(
            api_key=env("OPENAI_API_KEY"),
            base_url=env("OPENAI_API_BASE") or "https://api.openai.com/v1",
        ).responses.create(model=env("OPENAI_MODEL") or "gpt-4o-mini", input=prompt)
        return str(response.output_text or "").strip()
    raise RuntimeError("No available local Ollama, Qwen, or OpenAI text model")


def reply_to_comments(video_id: str, max_comments: int = 10) -> dict[str, Any]:
    if not video_id:
        return {"ok": False, "error": "Missing video id"}
    if not ((local_enabled() and ollama_available()) or has_qwen() or has_openai()):
        return {"ok": False, "error": "No local AI, Qwen, or OpenAI configured"}

    youtube = _youtube()
    policy = load_content_policy()
    out_dir = Path("output")
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = out_dir / "comment_reply_ledger.json"
    pending_path = out_dir / "pending_replies.json"
    ledger = _load_json(ledger_path, {"replied": {}})
    if not isinstance(ledger.get("replied"), dict):
        ledger["replied"] = {}
    previous_pending = _load_json(pending_path, {"pending": []}).get("pending", [])
    pending_by_id = {
        str(item.get("comment_id")): item
        for item in previous_pending if isinstance(item, dict) and item.get("comment_id")
    }
    replied = 0
    skipped = 0
    items = youtube.commentThreads().list(
        part="snippet,replies", videoId=video_id, maxResults=max(1, min(int(max_comments), 100)),
        textFormat="plainText",
    ).execute().get("items", [])
    channel_response = youtube.channels().list(part="id", mine=True).execute().get("items", [])
    own_channel_id = str(channel_response[0].get("id") or "") if channel_response else ""

    for item in items:
        top = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
        comment_id = str(item.get("id") or "")
        text = str(top.get("textOriginal") or top.get("textDisplay") or "").strip()
        if not comment_id or not text:
            continue
        author_id = str(top.get("authorChannelId", {}).get("value") or "")
        if (author_id and author_id == own_channel_id) or comment_id in ledger["replied"] or _has_our_reply(item, own_channel_id):
            skipped += 1
            continue
        if _looks_like_spam(text):
            pending_by_id[comment_id] = {"comment_id": comment_id, "video_id": video_id, "comment": text, "reason": "possible spam; manual review"}
            continue

        prompt = (
            "یک پاسخ کوتاه، محترمانه، انسانی و مرتبط به فارسی برای این نظر بنویس. "
            "هرگز آیه، حدیث، نقل‌قول یا واقعیت را جعل نکن. "
            "برای تهدید، خودآسیبی، محتوای جنسی، آزار هدفمند، نفرت‌پراکنی، سیاست، درخواست حساس یا هر مورد نامطمئن فقط PENDING بنویس. "
            "از تکرار عبارت‌های تبلیغاتی و دعوت اجباری به دنبال‌کردن پرهیز کن. "
            f"سیاست کانال: {json.dumps(policy, ensure_ascii=False)}\nنظر: {text}"
        )
        try:
            reply = _generate_reply(prompt).strip()
        except Exception as exc:
            pending_by_id[comment_id] = {"comment_id": comment_id, "video_id": video_id, "comment": text, "reason": f"generation failed: {exc}"}
            continue
        if not reply or reply.upper().strip(" .!؟") == "PENDING":
            pending_by_id[comment_id] = {"comment_id": comment_id, "video_id": video_id, "comment": text, "reason": "policy review"}
            continue
        if len(reply) > 1000:
            reply = reply[:997].rstrip() + "..."
        try:
            youtube.comments().insert(
                part="snippet",
                body={"snippet": {"parentId": comment_id, "textOriginal": reply}},
            ).execute()
            ledger["replied"][comment_id] = {"video_id": video_id, "replied_at": utc_now_iso()}
            pending_by_id.pop(comment_id, None)
            save_json(ledger_path, ledger)
            replied += 1
        except Exception as exc:
            pending_by_id[comment_id] = {"comment_id": comment_id, "video_id": video_id, "comment": text, "reason": f"YouTube reply failed: {exc}"}

    save_json(pending_path, {"updated_at": utc_now_iso(), "pending": list(pending_by_id.values())})
    return {"ok": True, "replied": replied, "skipped_duplicate_or_self": skipped, "pending": len(pending_by_id)}



def reply_to_recent_comments(max_videos: int = 5, max_comments_per_video: int = 10) -> dict[str, Any]:
    """Moderate recent non-private uploads; uncertain or spam-like comments remain pending."""
    try:
        youtube = _youtube()
        channels = youtube.channels().list(part="contentDetails", mine=True).execute().get("items", [])
        if not channels:
            return {"ok": False, "error": "No authenticated YouTube channel returned"}
        uploads_playlist = (
            channels[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        )
        if not uploads_playlist:
            return {"ok": False, "error": "Could not resolve the channel uploads playlist"}
        limit = max(1, min(int(max_videos), 20))
        playlist_items = youtube.playlistItems().list(
            part="contentDetails", playlistId=uploads_playlist, maxResults=limit
        ).execute().get("items", [])
        video_ids = [
            str(item.get("contentDetails", {}).get("videoId") or "")
            for item in playlist_items
            if item.get("contentDetails", {}).get("videoId")
        ]
        if not video_ids:
            return {"ok": True, "videos_checked": 0, "videos_skipped_private": 0, "results": []}
        videos = youtube.videos().list(part="status", id=",".join(video_ids)).execute().get("items", [])
        statuses = {str(item.get("id")): item.get("status", {}) for item in videos}
        results = []
        skipped_private = 0
        for video_id in video_ids:
            privacy = str(statuses.get(video_id, {}).get("privacyStatus") or "unknown")
            if privacy not in {"public", "unlisted"}:
                skipped_private += 1
                continue
            try:
                results.append({
                    "video_id": video_id,
                    **reply_to_comments(video_id, max_comments=max_comments_per_video),
                })
            except Exception as exc:
                results.append({"video_id": video_id, "ok": False, "error": str(exc)})
        return {
            "ok": all(item.get("ok", False) for item in results) if results else True,
            "videos_checked": len(results),
            "videos_skipped_private": skipped_private,
            "results": results,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

def channel_health() -> dict[str, Any]:
    cfg = load_channel_config()
    checks: dict[str, Any] = {
        "local_ai": local_enabled() and ollama_available(),
        "qwen_configured": has_qwen(),
        "openai_configured": has_openai(),
        "youtube": False,
        "channel": cfg.get("channel", {}).get("url"),
    }
    try:
        youtube = _youtube()
        response = youtube.channels().list(part="snippet,statistics", mine=True).execute()
        checks["youtube"] = bool(response.get("items"))
        if response.get("items"):
            item = response["items"][0]
            checks["channel_title"] = item.get("snippet", {}).get("title")
            checks["statistics"] = item.get("statistics", {})
    except Exception as exc:
        checks["youtube_error"] = str(exc)
    return checks
