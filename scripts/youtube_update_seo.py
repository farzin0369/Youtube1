#!/usr/bin/env python3
"""List recent channel videos and update title/description/tags for one of them."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.youtube_client import _build_credentials

# Default SEO for Dunning-Kruger short
DEFAULT_TITLE = "هرچه کمتر بدانی بیشتر فکر می‌کنی بلدی 😱 مغز این‌طور فریبت می‌ده"
DEFAULT_DESC = """هرچه کمتر بدانی، بیشتر فکر می‌کنی بلدی.

اسم این پدیده اثر دانینگ–کروگره.
تازه‌کارها معمولاً خودشون رو خیلی قوی می‌بینن…
چون هنوز نمی‌دونن چه چیزهایی رو نمی‌دونن.

با یادگیری واقعی، اول اعتماد پایین میاد.
بعد کم‌کم دوباره بالا می‌ره — این بار واقعی.

اگه همیشه مطمئنی که حقی، شاید هنوز اول راهی.

👉 سابسکرایب کن: بامو | @12bamo

#shorts #روانشناسی #مغز #دانینگ_کروگر #اثر_دانینگ_کروگر #حقیقت #علم #رشد_فردی #خودشناسی #بامو"""
DEFAULT_TAGS = [
    "shorts",
    "شورتس",
    "روانشناسی",
    "مغز",
    "دانینگ کروگر",
    "اثر دانینگ کروگر",
    "dunning kruger",
    "روانشناسی رفتاری",
    "خودشناسی",
    "رشد فردی",
    "حقیقت مغز",
    "باگ مغز",
    "اعتماد به نفس کاذب",
    "یادگیری",
    "علم",
    "دانستنی",
    "بامو",
    "12bamo",
    "حقایق روانشناسی",
    "روانشناسی تاریک",
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
        # privacy from videos.list
        out.append(
            {
                "video_id": vid,
                "title": sn.get("title"),
                "published_at": sn.get("publishedAt"),
                "url": f"https://www.youtube.com/watch?v={vid}",
            }
        )
    # enrich privacy
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
    category_id: str = "27",
    privacy: str | None = None,
) -> dict:
    yt = _yt()
    # must fetch current snippet (categoryId required on update)
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
    # only change privacy if explicitly requested
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
    ap.add_argument("--list", action="store_true", help="List recent videos and exit")
    ap.add_argument("--video-id", default="", help="Specific video id to update")
    ap.add_argument("--latest-private", action="store_true", help="Update newest private video")
    ap.add_argument("--privacy", default="", choices=["", "private", "unlisted", "public"])
    ap.add_argument("--title", default=DEFAULT_TITLE)
    ap.add_argument("--description-file", default="", help="Optional path to description text")
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

    if not video_id:
        print(json.dumps({"ok": False, "error": "Provide --video-id or --latest-private"}, ensure_ascii=False))
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
