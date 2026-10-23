"""Optional free YouTube Analytics API reader for performance-aware topic planning."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any


METRICS = "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,shares,impressions,impressionsClickThroughRate"


def fetch_recent_video_analytics(*, days: int = 28, max_results: int = 50) -> dict[str, Any]:
    """Fetch recent video metrics; return a non-fatal unavailable result on OAuth/API issues."""
    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from app.youtube_client import _build_credentials, has_youtube_creds

        if not has_youtube_creds():
            return {"ok": False, "reason": "youtube_oauth_not_configured", "videos": []}
        credentials = _build_credentials()
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
        videos = []
        for row in response.get("rows") or []:
            record = dict(zip(headers, row))
            video_id = str(record.get("video") or "")
            if not video_id:
                continue
            videos.append({
                "video_id": video_id,
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
        title = str((linked or {}).get("title") or "")
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
