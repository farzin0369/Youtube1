from app.youtube_analytics import performance_notes


def test_analytics_feedback_uses_real_metrics_and_never_predicts_views():
    analytics = {
        "ok": True,
        "period": {"start": "2026-09-01", "end": "2026-09-28"},
        "videos": [
            {"video_id": "a", "views": 10, "average_view_percentage": 12},
            {"video_id": "b", "views": 100, "average_view_percentage": 70},
            {"video_id": "c", "views": 20, "average_view_percentage": 15},
            {"video_id": "d", "views": 200, "average_view_percentage": 80},
        ],
    }
    history = {
        "recent": [
            {"video_id": "a", "title": "عنوان کم‌عملکرد"},
            {"video_id": "b", "title": "عنوان بهتر"},
            {"video_id": "c", "title": "عنوان دوم کم‌عملکرد"},
            {"video_id": "d", "title": "عنوان دوم بهتر"},
        ]
    }
    notes = performance_notes(analytics, history)
    assert any("میانهٔ بازدید" in note for note in notes)
    assert any("عنوان کم‌عملکرد" in note for note in notes)
    assert all("تضمین" not in note for note in notes)


def test_analytics_feedback_fails_closed_without_real_data():
    notes = performance_notes({"ok": False, "videos": []}, {"recent": []})
    assert len(notes) == 1
    assert "حدس نزن" in notes[0]


def test_small_analytics_sample_does_not_claim_a_performance_trend():
    notes = performance_notes({"ok": True, "videos": [{"video_id": "x", "views": 0}]}, {"recent": []})
    assert any("نمونهٔ کافی" in note for note in notes)


def test_competitor_notes_use_only_retrieved_public_facts_and_warn_against_copying():
    from app.youtube_analytics import competitor_notes

    signals = {
        "ok": True,
        "query": "حکمت امام علی فارسی",
        "videos": [{
            "title": "یک عنوان عمومی",
            "channel_title": "یک کانال",
            "view_count": 1234,
            "published_at": "2026-10-01T00:00:00Z",
            "url": "https://www.youtube.com/watch?v=abc",
        }],
    }
    notes = competitor_notes(signals)
    assert any("1234" in note for note in notes)
    assert any("کپی نکن" in note for note in notes)
    assert any("یک عنوان عمومی" in note for note in notes)


def test_competitor_notes_do_not_invent_results_when_search_is_unavailable():
    from app.youtube_analytics import competitor_notes

    notes = competitor_notes({"ok": False, "query": "query", "videos": []})
    assert len(notes) == 1
    assert "نساز" in notes[0]
