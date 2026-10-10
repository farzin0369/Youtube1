"""YouTube upload — private/unlisted/public."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any

from app.utils import env, has_youtube_creds

# Must match scripts/get_youtube_token.py so refresh_token works.
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube",
]


def _contains_synthetic_media() -> bool:
    setting = env("YOUTUBE_CONTAINS_SYNTHETIC_MEDIA")
    if setting is None:
        return (env("VIDEO_ENGINE") or "cpu").lower() == "cogvideox"
    return setting.strip().lower() in {"1", "true", "yes", "on"}


def _validate_publish_at(publish_at: str, *, now: datetime | None = None) -> str:
    """Validate a requested publish slot and reject slots that are too close/past.

    Do not silently drop scheduling for a late slot: with public privacy that
    could publish immediately instead of at the requested time.
    """
    parsed = datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if parsed <= current + timedelta(minutes=15):
        raise ValueError(
            f"publishAt {publish_at} is too close/past; choose a future slot "
            "at least 15 minutes away"
        )
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_credentials():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    client_id = (env("YOUTUBE_CLIENT_ID") or "").strip()
    client_secret = (env("YOUTUBE_CLIENT_SECRET") or "").strip()
    refresh_token = (env("YOUTUBE_REFRESH_TOKEN") or "").strip()
    if not client_id or not client_secret or not refresh_token:
        raise RuntimeError("Missing YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN")

    # Do not force a narrower scope set on refresh — that triggers invalid_scope
    # when the token was issued with the full set from get_youtube_token.py.
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=YOUTUBE_SCOPES,
    )
    try:
        creds.refresh(Request())
    except Exception as exc:
        msg = str(exc)
        hint = ""
        low = msg.lower()
        if "invalid_grant" in low:
            hint = (
                " | HINT: refresh_token rejected. Re-run scripts/get_youtube_token.py, "
                "put ALL THREE values from the same run into GitHub Secrets, and ensure "
                "the OAuth client is Desktop + YouTube Data API enabled."
            )
        elif "invalid_scope" in low:
            hint = (
                " | HINT: token scopes mismatch. Revoke app access at "
                "https://myaccount.google.com/permissions and re-issue the token."
            )
        raise RuntimeError(f"YouTube OAuth refresh failed: {msg}{hint}") from exc
    if not creds.valid or not creds.token:
        raise RuntimeError("YouTube OAuth refresh produced no access token")
    return creds


def probe_youtube_auth() -> dict[str, Any]:
    """Cheap auth check: refresh + channels.list(mine=True). Call before GPU work."""
    try:
        from googleapiclient.discovery import build

        youtube = build("youtube", "v3", credentials=_build_credentials())
        resp = youtube.channels().list(part="snippet,contentDetails", mine=True).execute()
        items = resp.get("items") or []
        if not items:
            return {
                "ok": False,
                "error": "OAuth ok but no channel returned for this account (wrong Google account?).",
            }
        ch = items[0]
        return {
            "ok": True,
            "channel_id": ch.get("id"),
            "title": (ch.get("snippet") or {}).get("title"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def upload_video(
    video_path: Path | None,
    title: str,
    description: str,
    tags: list[str],
    privacy: str = "private",
    thumbnail_path: Path | None = None,
    category_id: str = "22",
    publish_at: str | None = None,
) -> dict[str, Any]:
    if privacy not in ("private", "unlisted", "public"):
        return {"ok": False, "error": "Unsupported privacy mode."}
    if not has_youtube_creds():
        return {"ok": False, "skipped": True, "error": "Missing YouTube secrets."}
    if not video_path or not Path(video_path).exists():
        return {"ok": False, "error": "No video file."}

    contains_synthetic_media = _contains_synthetic_media()

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        youtube = build("youtube", "v3", credentials=_build_credentials())
        scheduled_at = (publish_at or env("YOUTUBE_PUBLISH_AT") or "").strip() or None
        if scheduled_at:
            scheduled_at = _validate_publish_at(scheduled_at)
        # YouTube requires scheduled videos to be uploaded as private with publishAt set.
        effective_privacy = "private" if scheduled_at and privacy == "public" else privacy
        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:20],
                "categoryId": category_id,
                "defaultLanguage": "fa",
                "defaultAudioLanguage": "fa",
            },
            "status": {
                "privacyStatus": effective_privacy,
                "selfDeclaredMadeForKids": False,
                "containsSyntheticMedia": contains_synthetic_media,
                **({"publishAt": scheduled_at} if scheduled_at and effective_privacy == "private" else {}),
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
            "privacy": "scheduled" if scheduled_at and effective_privacy == "private" else privacy,
            "scheduled_for": scheduled_at if scheduled_at and effective_privacy == "private" else None,
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
