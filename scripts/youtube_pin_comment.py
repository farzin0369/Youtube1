#!/usr/bin/env python3
"""Post a top-level channel comment on a video (latest private by default).

YouTube Data API v3 cannot pin comments programmatically.
This script posts the comment as the channel; pin in Studio (⋯ → Pin).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.youtube_client import _build_credentials

DEFAULT_COMMENT = """هرچه کمتر بدانی، بیشتر فکر می‌کنی بلدی 🧠

اثر دانینگ–کروگر همینه: تازه‌کارها معمولاً بیش از حد به خودشون مطمئنن.
با یادگیری واقعی، اول شک می‌آد… بعد اعتماد واقعی ساخته می‌شه.

اگر برات مفید بود:
✅ لایک کن
✅ سابسکرایب بامو | @12bamo
✅ تو کامنت بنویس: تا حالا کجا بیش از حد مطمئن بودی؟

#روانشناسی #مغز #دانینگ_کروگر"""


def _yt():
    from googleapiclient.discovery import build

    return build("youtube", "v3", credentials=_build_credentials())


def list_recent(max_results: int = 15) -> list[dict]:
    yt = _yt()
    ch = yt.channels().list(part="contentDetails", mine=True).execute()
    items = ch.get("items") or []
    if not items:
        raise SystemExit("No channel for this OAuth account")
    uploads = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    pl = yt.playlistItems().list(
        part="contentDetails,snippet",
        playlistId=uploads,
        maxResults=max_results,
    ).execute()
    out = []
    for it in pl.get("items") or []:
        vid = it["contentDetails"]["videoId"]
        out.append({"video_id": vid, "title": (it.get("snippet") or {}).get("title")})
    if out:
        ids = ",".join(x["video_id"] for x in out)
        vr = yt.videos().list(part="status,snippet", id=ids).execute()
        by_id = {v["id"]: v for v in vr.get("items") or []}
        for x in out:
            v = by_id.get(x["video_id"]) or {}
            x["privacy"] = (v.get("status") or {}).get("privacyStatus")
            x["title"] = (v.get("snippet") or {}).get("title") or x.get("title")
    return out


def post_comment(video_id: str, text: str) -> dict:
    yt = _yt()
    body = {
        "snippet": {
            "videoId": video_id,
            "topLevelComment": {
                "snippet": {
                    "textOriginal": text[:9000],
                }
            },
        }
    }
    resp = yt.commentThreads().insert(part="snippet", body=body).execute()
    sn = resp.get("snippet") or {}
    top = (sn.get("topLevelComment") or {}).get("snippet") or {}
    return {
        "ok": True,
        "video_id": video_id,
        "comment_id": resp.get("id"),
        "text": top.get("textDisplay") or top.get("textOriginal"),
        "url": f"https://www.youtube.com/watch?v={video_id}&lc={resp.get('id')}",
        "pin_note": "API cannot pin — open Studio → Comments → ⋯ on this comment → Pin",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video-id", default="")
    ap.add_argument("--latest-private", action="store_true")
    ap.add_argument("--text-file", default="")
    args = ap.parse_args()

    videos = list_recent(20)
    print(json.dumps({"recent": [{"id": v["video_id"], "privacy": v.get("privacy"), "title": v.get("title")} for v in videos]}, ensure_ascii=False))

    video_id = (args.video_id or "").strip()
    if args.latest_private and not video_id:
        priv = [v for v in videos if v.get("privacy") == "private"]
        if not priv:
            print(json.dumps({"ok": False, "error": "No private video found"}, ensure_ascii=False))
            return 1
        video_id = priv[0]["video_id"]
        print(json.dumps({"selected": priv[0]}, ensure_ascii=False))

    if not video_id:
        print(json.dumps({"ok": False, "error": "Need --video-id or --latest-private"}, ensure_ascii=False))
        return 1

    text = DEFAULT_COMMENT
    if args.text_file:
        text = Path(args.text_file).read_text(encoding="utf-8")

    try:
        result = post_comment(video_id, text)
    except Exception as e:
        result = {"ok": False, "error": str(e), "video_id": video_id}
        print(json.dumps(result, ensure_ascii=False))
        return 1

    print(json.dumps({"comment": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
