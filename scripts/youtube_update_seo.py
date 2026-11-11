#!/usr/bin/env python3
"""List recent channel videos and update title/description/tags."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.youtube_client import _build_credentials

# Max search + Shorts retention — قالی/دریا/AI
DEFAULT_TITLE = "این قالی نیست… دریاست! 🌊😱 هوش مصنوعی ساختش"
DEFAULT_DESC = """فکر می‌کنی این یه قالیه؟
دوباره نگاه کن… زیرش دریاست 🌊

ساخته‌شده با هوش مصنوعی — فقط برای چند ثانیه نگات می‌کنه و رها نمی‌کنه.

اگه تا آخر دیدی، تو کامنت بنویس: قالی یا دریا؟

✅ لایک کن تا بیشتر از اینا بسازم
✅ سابسکرایب بامو | @12bamo

#shorts #شورتس #هوش_مصنوعی #AI #ویدیوی_هوش_مصنوعی #قالی #دریا #AIVideo #ویدیوی_وایرال #فیلم_کوتاه #هنر_دیجیتال #بامو #12bamo #BAMO #YouTubeShorts #ترند #وایرال"""
DEFAULT_TAGS = [
    "shorts",
    "شورتس",
    "هوش مصنوعی",
    "AI",
    "ویدیوی هوش مصنوعی",
    "قالی",
    "دریا",
    "AIVideo",
    "ویدیوی وایرال",
    "فیلم کوتاه",
    "هنر دیجیتال",
    "بامو",
    "12bamo",
    "BAMO",
    "YouTubeShorts",
    "ترند",
    "وایرال",
    "قالی دریایی",
    "AI art",
    "ocean carpet",
    "ویدیو عجیب",
    "چیزهایی که باور نمی‌کنی",
    "artificial intelligence",
    "digital art",
    "اسمر بصری",
    "ویدیو خفن",
    "شورتس فارسی",
    "یوتیوب شورتس",
    "AI generated",
    "فرش",
]


def _yt():
    from googleapiclient.discovery import build

    return build("youtube", "v3", credentials=_build_credentials())


def list_recent(max_results: int = 15) -> list[dict]:
    yt = _yt()
    ch = yt.channels().list(part="contentDetails", mine=True).execute()
    items = ch.get("items") or []
    if not items:
        raise SystemExit("No channel found for this OAuth account")
    uploads = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    pl = yt.playlistItems().list(
        part="snippet,contentDetails,status",
        playlistId=uploads,
        maxResults=max_results,
    ).execute()
    out = []
    for it in pl.get("items") or []:
        vid = it["contentDetails"]["videoId"]
        sn = it.get("snippet") or {}
        out.append(
            {
                "video_id": vid,
                "title": sn.get("title"),
                "published_at": sn.get("publishedAt"),
                "url": f"https://www.youtube.com/watch?v={vid}",
            }
        )
    if out:
        ids = ",".join(x["video_id"] for x in out)
        vr = yt.videos().list(part="status,snippet", id=ids).execute()
        by_id = {v["id"]: v for v in vr.get("items") or []}
        for x in out:
            v = by_id.get(x["video_id"]) or {}
            st = v.get("status") or {}
            sn = v.get("snippet") or {}
            x["privacy"] = st.get("privacyStatus")
            x["description"] = (sn.get("description") or "")[:120]
            x["tags"] = sn.get("tags") or []
    return out


def update_video(
    video_id: str,
    *,
    title: str,
    description: str,
    tags: list[str],
    category_id: str = "22",
    privacy: str | None = None,
) -> dict:
    yt = _yt()
    cur = yt.videos().list(part="snippet,status", id=video_id).execute()
    items = cur.get("items") or []
    if not items:
        return {"ok": False, "error": f"video not found: {video_id}"}
    sn = items[0]["snippet"]
    st = items[0]["status"]
    body = {
        "id": video_id,
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:30],
            "categoryId": sn.get("categoryId") or category_id,
            "defaultLanguage": "fa",
            "defaultAudioLanguage": "fa",
        },
    }
    if privacy:
        body["status"] = {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": st.get("selfDeclaredMadeForKids", False),
        }
        part = "snippet,status"
    else:
        part = "snippet"
    resp = yt.videos().update(part=part, body=body).execute()
    return {
        "ok": True,
        "video_id": resp.get("id"),
        "title": (resp.get("snippet") or {}).get("title"),
        "privacy": (resp.get("status") or {}).get("privacyStatus") or st.get("privacyStatus"),
        "url": f"https://www.youtube.com/watch?v={resp.get('id')}",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--video-id", default="")
    ap.add_argument("--latest-private", action="store_true")
    ap.add_argument("--latest", action="store_true")
    ap.add_argument("--privacy", default="", choices=["", "private", "unlisted", "public"])
    ap.add_argument("--title", default=DEFAULT_TITLE)
    ap.add_argument("--description-file", default="")
    args = ap.parse_args()

    videos = list_recent(20)
    print(json.dumps({"recent": videos}, ensure_ascii=False, indent=2))

    if args.list:
        return 0

    video_id = (args.video_id or "").strip()
    if args.latest_private and not video_id:
        priv = [v for v in videos if v.get("privacy") == "private"]
        if not priv:
            print(json.dumps({"ok": False, "error": "No private videos found"}, ensure_ascii=False))
            return 1
        video_id = priv[0]["video_id"]
        print(json.dumps({"selected_private": priv[0]}, ensure_ascii=False))
    elif args.latest and not video_id:
        if not videos:
            print(json.dumps({"ok": False, "error": "No videos found"}, ensure_ascii=False))
            return 1
        video_id = videos[0]["video_id"]
        print(json.dumps({"selected_latest": videos[0]}, ensure_ascii=False))

    if not video_id:
        print(json.dumps({"ok": False, "error": "Provide --video-id or --latest-private or --latest"}, ensure_ascii=False))
        return 1

    desc = DEFAULT_DESC
    if args.description_file:
        desc = Path(args.description_file).read_text(encoding="utf-8")

    result = update_video(
        video_id,
        title=args.title,
        description=desc,
        tags=DEFAULT_TAGS,
        privacy=args.privacy or None,
    )
    print(json.dumps({"update": result}, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
