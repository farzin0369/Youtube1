from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from app.spiritual_content import validate_content, word_count
from app.spiritual_pipeline import next_publish_at
from app.spiritual_tts import phrase_cues, TICKS_PER_SECOND
from app.spiritual_comments import _spam, SENSITIVE_TERMS
from app.spiritual_video import _get_with_backoff


def _content(words=720):
    tokens = ["تأمل" for _ in range(words)]
    chunk_size = max(1, (words + 5) // 6)
    chunks = [" ".join(tokens[i:i + chunk_size]) for i in range(0, words, chunk_size)]
    while len(chunks) < 6:
        chunks.append("تأمل")
    chunks = chunks[:6]
    return {
        "title": "چگونه آرام‌تر و آگاهانه‌تر پیش برویم",
        "thumbnail_text": "قدم آرام امروز",
        "description": "یک ویدئوی تأملی و کاربردی.",
        "tags": ["رشد فردی"],
        "visual_keywords": ["sunrise forest"],
        "sections": [{"heading": f"بخش {i + 1}", "text": text} for i, text in enumerate(chunks)],
    }


def test_content_gate_accepts_six_minute_persian_script():
    value = validate_content(_content())
    assert value["word_count"] == 720
    assert len(value["sections"]) == 6


def test_content_gate_rejects_short_or_repeated_content():
    with pytest.raises(ValueError, match="length"):
        validate_content(_content(100))
    with pytest.raises(ValueError, match="duplicates"):
        validate_content(_content(), ["چگونه آرام‌تر و آگاهانه‌تر پیش برویم"])


def test_word_count_treats_persian_zwnj_as_part_of_one_word():
    assert word_count("می‌شود یک تمرین روزانه") == 4


def test_content_gate_rejects_unverified_attributed_quote():
    item = _content()
    item["sections"][0]["text"] += " قرآن می‌فرماید"
    with pytest.raises(ValueError, match="quotation"):
        validate_content(item)


def test_publication_slot_is_18_tehran_and_moves_to_tomorrow_if_too_late():
    before = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
    late = datetime(2026, 10, 11, 14, 15, tzinfo=timezone.utc)
    assert next_publish_at(before) == "2026-10-11T14:30:00Z"
    assert next_publish_at(late) == "2026-10-12T14:30:00Z"


def test_github_schedule_triggers_at_18_tehran():
    workflow = yaml.load(Path(".github/workflows/daily_run.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert workflow["on"]["schedule"][0]["cron"] == "30 14 * * *"


def test_daily_cli_imports_from_outside_repository(tmp_path):
    cli = Path(__file__).resolve().parents[1] / "scripts" / "daily_run.py"
    result = subprocess.run([sys.executable, str(cli), "--help"], cwd=tmp_path, capture_output=True, text=True, check=True)
    assert "Daily Persian spiritual video pipeline" in result.stdout


def test_word_boundaries_are_grouped_into_phrase_captions():
    events = [
        {"type": "WordBoundary", "offset": i * TICKS_PER_SECOND, "duration": TICKS_PER_SECOND // 2, "text": f"واژه{i}"}
        for i in range(7)
    ]
    cues = phrase_cues(events, max_words=3)
    assert len(cues) == 3
    assert cues[0][2] == "واژه0 واژه1 واژه2"
    assert cues[0][0] == 0


def test_sensitive_or_spam_comments_are_never_auto_replied_to():
    assert _spam("سلام https://spam.example")
    assert SENSITIVE_TERMS.search("من به خودکشی فکر می‌کنم")
    assert SENSITIVE_TERMS.search("برای سرمایه‌گذاری شخصی چه کنم؟")


def test_pexels_rate_limit_retries_before_falling_back(monkeypatch):
    import app.spiritual_video as video

    class Response:
        def __init__(self, status):
            self.status_code = status
            self.headers = {"Retry-After": "0"}
            self.closed = False

        def raise_for_status(self):
            if self.status_code >= 400:
                import requests
                raise requests.HTTPError("test error")

        def close(self):
            self.closed = True

    monkeypatch.setattr(video.time, "sleep", lambda _seconds: None)
    statuses = iter([429, 200])
    responses = []

    def request():
        response = Response(next(statuses))
        responses.append(response)
        return response

    result = _get_with_backoff(request)
    assert result.status_code == 200
    assert len(responses) == 2 and responses[0].closed
