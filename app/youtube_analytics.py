"""Optional free YouTube Analytics API reader for performance-aware topic planning."""
from __future__ import annotations

from datetime import date, timedelta
import os
from typing import Any


METRICS = "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,shares,impressions,impressionsClickThroughRate"


def fetch_recent_video_analytics(*, days: int = 28, max_results: int = 50) -> dict[str, Any]:
    """Fetch recent video metrics; return a non-fatal unavailable result on OAuth/API issues."""
    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from app.youtube_client import _build_credentials

        client_id = (os.getenv("YOUTUBE_CLIENT_ID") or "").strip()
        client_secret = (os.getenv("YOUTUBE_CLIENT_SECRET") or "").strip()
        analytics_refresh = (os.getenv("YOUTUBE_ANALYTICS_REFRESH_TOKEN") or "").strip()
        if not client_id or not client_secret or not analytics_refresh:
            return {"ok": False, "reason": "analytics_refresh_token_not_configured", "videos": []}
        credentials = Credentials(
            token=None, refresh_token=analytics_refresh,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id, client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/yt-analytics.readonly"],
        )
        credentials.refresh(Request())
        service = build("youtubeAnalytics", "v2", credentials=credentials, cache_discovery=False)
        end_date = date.today() - timedelta(days=2)  # Analytics data can lag by 1–2 days.
        start_date = end_date - timedelta(days=max(7, min(int(days), 90)))
        try:
            response = service.reports().query(
                ids="channel==MINE",
                startDate=start_date.isoformat(),
                endDate=end_date.isoformat(),
                metrics=METRICS,
                dimensions="video",
                sort="-views",
                maxResults=max(1, min(int(max_results), 200)),
            ).execute()
        except HttpError:
            # Some channels/tokens cannot access impression metrics; retry with basic watch metrics.
            response = service.reports().query(
                ids="channel==MINE",
                startDate=start_date.isoformat(),
                endDate=end_date.isoformat(),
                metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,shares",
                dimensions="video",
                sort="-views",
                maxResults=max(1, min(int(max_results), 200)),
            ).execute()
        headers = [str(item.get("name") or "") for item in response.get("columnHeaders") or []]
        raw_rows = [dict(zip(headers, row)) for row in response.get("rows") or []]
        video_ids = [str(row.get("video") or "") for row in raw_rows if row.get("video")]
        metadata = {}
        if video_ids:
            try:
                data_api = build("youtube", "v3", credentials=_build_credentials(), cache_discovery=False)
                details = data_api.videos().list(part="snippet", id=",".join(video_ids[:50])).execute()
                metadata = {str(item.get("id")): item.get("snippet") or {} for item in details.get("items") or []}
            except Exception:
                metadata = {}
        videos = []
        for record in raw_rows:
            video_id = str(record.get("video") or "")
            snippet = metadata.get(video_id) or ""
            if not video_id:
                continue
            videos.append({
                "video_id": video_id,
                "title": str(snippet.get("title") or "")[:180] if isinstance(snippet, dict) else "",
                "published_at": str(snippet.get("publishedAt") or "") if isinstance(snippet, dict) else "",
                "views": int(record.get("views") or 0),
                "estimated_minutes_watched": float(record.get("estimatedMinutesWatched") or 0),
                "average_view_duration_seconds": float(record.get("averageViewDuration") or 0),
                "average_view_percentage": float(record.get("averageViewPercentage") or 0),
                "likes": int(record.get("likes") or 0),
                "comments": int(record.get("comments") or 0),
                "shares": int(record.get("shares") or 0),
                "impressions": int(record.get("impressions") or 0) if record.get("impressions") is not None else None,
                "impressions_click_through_rate": float(record.get("impressionsClickThroughRate") or 0) if record.get("impressionsClickThroughRate") is not None else None,
            })
        return {
            "ok": True,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "videos": videos,
            "source": "YouTube Analytics API",
        }
    except Exception as exc:
        return {
            "ok": False,
            "reason": "analytics_unavailable",
            "error_type": type(exc).__name__,
            "videos": [],
        }


def performance_notes(
    analytics: dict[str, Any],
    history: dict[str, Any],
) -> list[str]:
    """Create grounded, conservative notes from real metrics only."""
    if not analytics.get("ok"):
        return ["تحلیل عملکرد واقعی در این اجرا در دسترس نبود؛ هیچ عدد یا نتیجه‌ای را حدس نزن."]
    rows = analytics.get("videos") or []
    if len(rows) < 3:
        return ["نمونهٔ کافی از ویدئوهای اخیر برای مقایسه وجود ندارد؛ از ادعای روند قطعی خودداری کن."]
    view_values = sorted(int(row.get("views") or 0) for row in rows)
    retention_values = sorted(float(row.get("average_view_percentage") or 0) for row in rows)
    median_views = view_values[len(view_values) // 2]
    median_retention = retention_values[len(retention_values) // 2]
    recent = history.get("recent") or []
    by_id = {str(row.get("video_id")): row for row in recent if isinstance(row, dict) and row.get("video_id")}
    underperformers = []
    winners = []
    for row in rows:
        linked = by_id.get(str(row.get("video_id")))
        title = str((linked or {}).get("title") or row.get("title") or "")
        if int(row.get("views") or 0) < median_views and float(row.get("average_view_percentage") or 0) < median_retention:
            underperformers.append(title or str(row.get("video_id")))
        elif int(row.get("views") or 0) >= median_views and float(row.get("average_view_percentage") or 0) >= median_retention:
            winners.append(title or str(row.get("video_id")))
    notes = [
        f"مقایسهٔ {len(rows)} ویدئو در بازهٔ {analytics.get('period', {}).get('start')} تا {analytics.get('period', {}).get('end')} انجام شد.",
        f"میانهٔ بازدید {median_views} و میانهٔ درصد مشاهده {median_retention:.1f}% است؛ این‌ها معیار مقایسهٔ داخلی‌اند، نه پیش‌بینی.",
    ]
    if underperformers:
        notes.append("برای ویدئوهای زیر میانهٔ بازدید و نگهداشت، در نسخهٔ بعدی زاویهٔ روایت و قلاب نخست را عوض کن و از تکرار عنوان/صحنه بپرهیز: " + "؛ ".join(underperformers[:5]))
    if winners:
        notes.append("از موضوع/زاویهٔ این ویدئوهای نسبتاً بهتر فقط به‌عنوان سرنخ استفاده کن؛ متن و هوک را کپی نکن: " + "؛ ".join(winners[:5]))
    return notes


def fetch_competitor_signals(query: str, *, max_results: int = 5, days: int = 90) -> dict[str, Any]:
    """Use the free YouTube Data API to find recent public videos; never copy their scripts."""
    try:
        from datetime import datetime, timezone
        from googleapiclient.discovery import build
        from app.youtube_client import _build_credentials

        if not all((os.getenv(key) or "").strip() for key in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")):
            return {"ok": False, "reason": "youtube_oauth_not_configured", "query": query, "videos": []}
        service = build("youtube", "v3", credentials=_build_credentials(), cache_discovery=False)
        published_after = (datetime.now(timezone.utc) - timedelta(days=max(7, min(int(days), 180)))).isoformat().replace("+00:00", "Z")
        search = service.search().list(
            part="snippet", q=str(query)[:100], type="video", order="viewCount",
            publishedAfter=published_after, relevanceLanguage="fa", regionCode="IR",
            maxResults=max(1, min(int(max_results), 10)),
        ).execute()
        items = search.get("items") or []
        ids = [str(item.get("id", {}).get("videoId") or "") for item in items]
        ids = [video_id for video_id in ids if video_id]
        stats = {}
        if ids:
            response = service.videos().list(part="statistics", id=",".join(ids[:50])).execute()
            stats = {str(item.get("id")): item.get("statistics") or {} for item in response.get("items") or []}
        videos = []
        for item in items:
            snippet = item.get("snippet") or {}
            video_id = str(item.get("id", {}).get("videoId") or "")
            if not video_id:
                continue
            metrics = stats.get(video_id) or {}
            videos.append({
                "video_id": video_id,
                "title": str(snippet.get("title") or "")[:180],
                "channel_title": str(snippet.get("channelTitle") or "")[:100],
                "published_at": str(snippet.get("publishedAt") or ""),
                "view_count": int(metrics.get("viewCount") or 0),
                "like_count": int(metrics.get("likeCount") or 0),
                "comment_count": int(metrics.get("commentCount") or 0),
                "url": "https://www.youtube.com/watch?v=" + video_id,
            })
        return {
            "ok": True, "query": str(query), "published_after": published_after,
            "videos": videos, "source": "YouTube Data API public search",
        }
    except Exception as exc:
        return {
            "ok": False, "reason": "competitor_search_unavailable",
            "error_type": type(exc).__name__, "query": str(query), "videos": [],
        }


def competitor_notes(signals: dict[str, Any]) -> list[str]:
    """Summarize only retrieved competitor facts and forbid copying."""
    if not signals.get("ok"):
        return ["جست‌وجوی عمومی رقبا در این اجرا در دسترس نبود؛ عنوان یا آمار رقیب را نساز."]
    videos = signals.get("videos") or []
    if not videos:
        return ["برای عبارت جست‌وجوی انتخاب‌شده نتیجهٔ قابل‌استفاده‌ای برنگشت؛ دربارهٔ رقبا نتیجه‌گیری نکن."]
    notes = [f"جست‌وجوی عمومی YouTube برای «{signals.get('query', '')}» نمونه‌های زیر را برگرداند؛ فقط برای کشف زاویهٔ تازه استفاده کن و متن/عنوان را کپی نکن."]
    for video in videos[:5]:
        notes.append(
            f"عنوان عمومی: «{video.get('title', '')}»؛ کانال: {video.get('channel_title', '')}؛ "
            f"بازدید ثبت‌شده: {int(video.get('view_count') or 0)}؛ تاریخ انتشار: {video.get('published_at') or 'نامشخص'}؛ "
            f"پیوند: {video.get('url', '')}"
        )
    return notes
