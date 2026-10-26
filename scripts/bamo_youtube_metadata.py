#!/usr/bin/env python3
"""Export and safely apply YouTube metadata for the authenticated channel.

Default mode is audit/export only. Apply mode requires an explicit CSV containing
video_id,title,description,tags (tags separated by |) and --apply.
Existing snippet fields are fetched before updating, and categoryId is preserved.
"""
import argparse, csv, json, os, sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
EXPECTED_CHANNEL_ID = "UCaU-FyL0_MoMThD8n1VtHSw"  # BAMO | بامو (@12bamo)

def youtube_client():
    client_id = os.environ["YOUTUBE_CLIENT_ID"]
    client_secret = os.environ["YOUTUBE_CLIENT_SECRET"]
    refresh_token = os.environ["YOUTUBE_REFRESH_TOKEN"]
    creds = Credentials(
        None, refresh_token=refresh_token, token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id, client_secret=client_secret, scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds, cache_discovery=False)

def list_uploads(youtube):
    channel_resp = youtube.channels().list(part="id,snippet,contentDetails", mine=True).execute()
    items = channel_resp.get("items", [])
    if len(items) != 1:
        raise RuntimeError(f"Expected exactly one authorized channel, got {len(items)}")
    channel = items[0]
    if channel.get("id") != EXPECTED_CHANNEL_ID:
        raise RuntimeError(
            "Safety stop: OAuth credentials are connected to channel "
            f"{channel.get('id')} ({channel.get('snippet', {}).get('title', 'unknown')}), "
            f"not BAMO ({EXPECTED_CHANNEL_ID}). No videos were changed."
        )
    uploads = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    rows = []
    token = None
    while True:
        page = youtube.playlistItems().list(
            part="snippet,contentDetails", playlistId=uploads, maxResults=50, pageToken=token
        ).execute()
        ids = [x.get("contentDetails", {}).get("videoId") for x in page.get("items", [])]
        ids = [x for x in ids if x]
        for start in range(0, len(ids), 50):
            videos = youtube.videos().list(part="snippet,status", id=",".join(ids[start:start+50])).execute()
            for v in videos.get("items", []):
                s = v.get("snippet", {})
                rows.append({
                    "video_id": v["id"], "title": s.get("title", ""),
                    "description": s.get("description", ""), "tags": "|".join(s.get("tags", [])),
                    "category_id": s.get("categoryId", ""), "privacy_status": v.get("status", {}).get("privacyStatus", ""),
                    "published_at": s.get("publishedAt", ""), "url": "https://youtu.be/" + v["id"],
                    "new_title": "", "new_description": "", "new_tags": "",
                })
        token = page.get("nextPageToken")
        if not token:
            return channel, rows

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="Apply rows with non-empty new_title from approved CSV")
    p.add_argument("--csv", default="bamo_metadata.csv")
    args = p.parse_args()
    yt = youtube_client()
    channel, current = list_uploads(yt)
    path = Path(args.csv)
    if not args.apply:
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(current[0].keys()) if current else [
                "video_id","title","description","tags","category_id","privacy_status","published_at","url","new_title","new_description","new_tags"])
            w.writeheader(); w.writerows(current)
        print(json.dumps({"mode":"audit_only","channel":channel["snippet"]["title"],"channel_id":channel["id"],"video_count":len(current),"csv":str(path)}, ensure_ascii=False))
        return
    if not path.exists():
        raise SystemExit(f"CSV not found: {path}; run audit mode first.")
    by_id = {r["video_id"]: r for r in current}
    changed = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            vid = (row.get("video_id") or "").strip()
            title = (row.get("new_title") or "").strip()
            if not title:
                continue
            if vid not in by_id:
                raise RuntimeError(f"Video {vid} is not in the authorized channel")
            if len(title) > 100:
                raise RuntimeError(f"Title exceeds 100 chars for {vid}")
            old = by_id[vid]
            snippet = {
                "title": title,
                "description": row.get("new_description") if row.get("new_description") not in (None, "") else old["description"],
                "categoryId": old["category_id"] or "22",
            }
            raw_tags = row.get("new_tags") or ""
            if raw_tags.strip():
                snippet["tags"] = [t.strip() for t in raw_tags.split("|") if t.strip()]
            elif old["tags"]:
                snippet["tags"] = [t for t in old["tags"].split("|") if t]
            yt.videos().update(part="snippet", body={"id":vid,"snippet":snippet}).execute()
            changed.append(vid)
    print(json.dumps({"mode":"apply","channel_id":channel["id"],"updated_count":len(changed),"video_ids":changed}, ensure_ascii=False))

if __name__ == "__main__":
    main()
