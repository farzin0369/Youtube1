from app.youtube_history import (
    add_fingerprint_tag, build_generation_history, content_fingerprint,
    find_duplicate, fingerprint_tag, require_unique,
)


def test_fingerprint_is_stable_and_normalizes_punctuation():
    assert content_fingerprint("سلام، دنیا!") == content_fingerprint("سلام دنیا")
    assert len(content_fingerprint("متن آزمایشی")) == 20


def test_fingerprint_tag_is_reserved_and_added_once():
    tags = add_fingerprint_tag(["BAMO", "science", "BAMO"], "یک متن")
    assert len(tags) == 3
    assert tags.count(fingerprint_tag("یک متن")) == 1
    assert tags[-1].startswith("bamo_fp_")


def test_youtube_inventory_becomes_generation_history_and_wins_over_local():
    result = build_generation_history(
        {"recent": [{"title": "local", "video_id": "local-id"}]},
        [{"title": "YouTube video", "video_id": "yt-id", "topic": "science"}],
    )
    assert result["recent"][0]["title"] == "local"
    assert result["recent"][-1]["title"] == "YouTube video"


def test_exact_title_duplicate_is_rejected():
    candidate = {"title": "BAMO | فیزیک کوانتوم", "script": "متن تازه"}
    videos = [{"title": "BAMO | فیزیک کوانتوم", "video_id": "abc", "tags": []}]
    duplicate = find_duplicate(candidate, videos)
    assert duplicate["video_id"] == "abc"


def test_fingerprint_duplicate_is_rejected_even_if_title_changes():
    script = "این یک متن نمونه برای بررسی تکراری بودن ویدئو است"
    candidate = {"title": "عنوان جدید", "script": script}
    videos = [{"title": "عنوان قدیمی", "video_id": "abc", "tags": [fingerprint_tag(script)]}]
    duplicate = find_duplicate(candidate, videos)
    assert duplicate["reason"] == "content_fingerprint_match"


def test_unique_candidate_passes():
    require_unique(
        {"title": "BAMO | یک کشف تازه در فیزیک", "script": "متن متفاوت"},
        [{"title": "BAMO | تاریخ معماری ایران", "video_id": "old", "tags": []}],
    )
