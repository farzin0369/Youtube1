"""YouTube channel inventory and fail-closed duplicate protection for BAMO."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

FINGERPRINT_PREFIX = "bamo_fp_"


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = re.sub(r"[^\w\u0600-\u06FF]+", " ", text)
    return " ".join(text.split())


def content_fingerprint(script: str) -> str:
    normalized = normalize_text(script)
    if not normalized:
        raise ValueError("cannot fingerprint an empty script")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]


def fingerprint_tag(script: str) -> str:
    return FINGERPRINT_PREFIX + content_fingerprint(script)


def add_fingerprint_tag(tags: list[str], script: str) -> list[str]:
    """Reserve one YouTube tag for a durable, API-readable content fingerprint."""
    fingerprint = fingerprint_tag(script)
    clean = [str(tag).strip() for tag in tags if str(tag).strip()
             and not str(tag).strip().startswith(FINGERPRINT_PREFIX)]
    clean = [tag for tag in clean if tag != fingerprint]
    return (clean[:19] + [fingerprint])


def fetch_recent_channel_videos(*, max_results: int = 100) -> list[dict[str, Any]]:
    """Read the authenticated channel's own uploads playlist, including private/scheduled uploads.

    This is intentionally a hard dependency for production publishing: if the channel
    inventory cannot be read, BAMO must not guess that a topic is new.
    """
    if not 1 <= max_results <= 200:
        raise ValueError("max_results must be between 1 and 200")
    from googleapiclient.discovery import build
    from app.youtube_client import _build_credentials

    youtube = build("youtube", "v3", credentials=_build_credentials(), cache_discovery=False)
    channel_response = youtube.channels().list(
        part="contentDetails,snippet", mine=True, maxResults=1
    ).execute()
    channels = channel_response.get("items") or []
    if not channels:
        raise RuntimeError("YouTube channel inventory returned no authenticated channel")
    channel = channels[0]
    uploads_id = (((channel.get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads"))
    if not uploads_id:
        raise RuntimeError("YouTube channel did not expose its uploads playlist")

    ids: list[str] = []
    page_token = None
    while len(ids) < max_results:
        response = youtube.playlistItems().list(
            part="contentDetails", playlistId=uploads_id,
            maxResults=min(50, max_results - len(ids)), pageToken=page_token,
        ).execute()
        for item in response.get("items") or []:
            video_id = ((item.get("contentDetails") or {}).get("videoId"))
            if video_id:
                ids.append(video_id)
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    videos: list[dict[str, Any]] = []
    for offset in range(0, len(ids), 50):
        response = youtube.videos().list(
            part="snippet,status", id=",".join(ids[offset:offset + 50]), maxResults=50
        ).execute()
        videos.extend(response.get("items") or [])
    return [{
        "video_id": item.get("id"),
        "title": str((item.get("snippet") or {}).get("title") or ""),
        "description": str((item.get("snippet") or {}).get("description") or ""),
        "tags": list((item.get("snippet") or {}).get("tags") or []),
        "published_at": (item.get("snippet") or {}).get("publishedAt"),
        "privacy": (item.get("status") or {}).get("privacyStatus"),
        "topic": str((item.get("snippet") or {}).get("title") or ""),
    } for item in videos]


def build_generation_history(local_history: dict[str, Any], channel_videos: list[dict[str, Any]]) -> dict[str, Any]:
    """Make YouTube authoritative; merge local history only as supplementary context."""
    merged: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in channel_videos:
        if not isinstance(row, dict):
            continue
        video_id = str(row.get("video_id") or "")
        if video_id and video_id in seen_ids:
            continue
        if video_id:
            seen_ids.add(video_id)
        merged.append({
            "title": str(row.get("title") or ""),
            "topic": str(row.get("topic") or row.get("title") or ""),
            "video_id": video_id,
            "description": str(row.get("description") or ""),
            "tags": list(row.get("tags") or []),
            "uploaded_at": row.get("published_at"),
            "source": "youtube",
        })
    for row in (local_history.get("recent") or []) if isinstance(local_history, dict) else []:
        if not isinstance(row, dict):
            continue
        video_id = str(row.get("video_id") or "")
        if video_id and video_id in seen_ids:
            continue
        merged.append(row)
        if video_id:
            seen_ids.add(video_id)
    return {"recent": merged[-200:], "source": "youtube+local"}


def find_duplicate(candidate: dict[str, Any], channel_videos: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Detect exact fingerprints and exact/near-identical titles against real channel uploads."""
    title = normalize_text(str(candidate.get("title") or ""))
    fingerprint = fingerprint_tag(str(candidate.get("script") or ""))
    for video in channel_videos:
        if not isinstance(video, dict):
            continue
        tags = {str(tag).strip() for tag in (video.get("tags") or [])}
        if fingerprint in tags:
            return {"reason": "content_fingerprint_match", "video_id": video.get("video_id"),
                    "title": video.get("title")}
        previous = normalize_text(str(video.get("title") or ""))
        if title and previous:
            similarity = SequenceMatcher(None, title, previous).ratio()
            if title == previous or similarity >= 0.90:
                return {"reason": "duplicate_or_near_duplicate_title", "similarity": round(similarity, 3),
                        "video_id": video.get("video_id"), "title": video.get("title")}
    return None


def require_unique(candidate: dict[str, Any], channel_videos: list[dict[str, Any]]) -> None:
    duplicate = find_duplicate(candidate, channel_videos)
    if duplicate:
        raise ValueError(
            "YouTube duplicate gate rejected candidate: "
            + str(duplicate.get("reason")) + " against video "
            + str(duplicate.get("video_id") or duplicate.get("title") or "unknown")
        )
