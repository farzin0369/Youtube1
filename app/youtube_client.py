"""YouTube upload — private/unlisted/public."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.utils import env, has_youtube_creds


def _build_credentials():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    creds = Credentials(
        token=None,
        refresh_token=(env("YOUTUBE_REFRESH_TOKEN") or "").strip(),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=(env("YOUTUBE_CLIENT_ID") or "").strip(),
        client_secret=(env("YOUTUBE_CLIENT_SECRET") or "").strip(),
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.force-ssl",
        ],
    )
    creds.refresh(Request())
    return creds


def upload_video(
    video_path: Path | None,
    title: str,
    description: str,
    tags: list[str],
    privacy: str = "private",
    thumbnail_path: Path | None = None,
    category_id: str = "22",
) -> dict[str, Any]:
    if privacy not in ("private", "unlisted", "public"):
        return {"ok": False, "error": "Unsupported privacy mode."}
    if not has_youtube_creds():
        return {"ok": False, "skipped": True, "error": "Missing YouTube secrets."}
    if not video_path or not Path(video_path).exists():
        return {"ok": False, "error": "No video file."}

    synthetic_setting = env("YOUTUBE_CONTAINS_SYNTHETIC_MEDIA")
    if synthetic_setting is None:
        contains_synthetic_media = (env("VIDEO_ENGINE") or "cpu").lower() == "cogvideox"
    else:
        contains_synthetic_media = synthetic_setting.strip().lower() in {"1", "true", "yes", "on"}

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        youtube = build("youtube", "v3", credentials=_build_credentials())
        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:20],
                "categoryId": category_id,
                "defaultLanguage": "fa",
                "defaultAudioLanguage": "fa",
            },
            # Disclose realistic generated scenes; allow an explicit override for other video engines.
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
                "containsSyntheticMedia": contains_synthetic_media,
            },
        }
        media = MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024, resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"[youtube] {int(status.progress() * 100)}%")
        video_id = response.get("id")
        result: dict[str, Any] = {
            "ok": True,
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "privacy": privacy,
        }
        captions_path = Path(video_path).with_name("captions.srt") if video_path else None
        if captions_path and captions_path.exists() and video_id:
            try:
                youtube.captions().insert(
                    part="snippet",
                    body={"snippet": {"videoId": video_id, "language": "fa", "name": "فارسی", "isDraft": False}},
                    media_body=MediaFileUpload(str(captions_path), mimetype="application/x-subrip", resumable=False),
                ).execute()
                result["captions_set"] = True
            except Exception as ce:
                result["captions_error"] = str(ce)
        if thumbnail_path and Path(thumbnail_path).exists() and video_id:
            try:
                youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(thumbnail_path))).execute()
                result["thumbnail_set"] = True
            except Exception as te:
                result["thumbnail_error"] = str(te)
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}
