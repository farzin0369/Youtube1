import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from app.spiritual_content import validate_content, word_count
from app.spiritual_pipeline import _should_run_comment_moderation, next_publish_at
from app.spiritual_tts import phrase_cues, TICKS_PER_SECOND
from app.spiritual_comments import _spam, SENSITIVE_TERMS
from app.spiritual_video import _get_with_backoff


def _content(words=720):
    base, remainder = divmod(words, 6)
    chunks = []
    for section in range(6):
        count = base + (1 if section < remainder else 0)
        hook = "آیا امروز می‌توانی یک قدم کوچک برداری؟" if section == 0 else ""
        tokens = [f"واژه{section}نشان{index}" for index in range(max(0, count - len(hook.split())))]
        sentences = [hook] if hook else []
        sentences.extend(" ".join(tokens[i:i + 8]) + "." for i in range(0, len(tokens), 8))
        chunks.append(" ".join(sentence for sentence in sentences if sentence))
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


def test_content_gate_rejects_a_weak_opening_hook():
    item = _content()
    item["sections"][0]["text"] = "در زندگی ما، گاهی انتخاب‌های مهم دیده می‌شوند. " + item["sections"][0]["text"].split("؟", 1)[1]
    with pytest.raises(ValueError, match="opening has no immediate"):
        validate_content(item)


def test_content_gate_rejects_duplicate_spoken_sections():
    item = _content()
    item["sections"][1]["text"] = item["sections"][0]["text"]
    with pytest.raises(ValueError, match="repeated or near-duplicate"):
        validate_content(item)


def test_content_gate_rejects_prompt_directions_in_spoken_text():
    item = _content()
    item["sections"][0]["text"] = "سه پاراگراف کوتاه برای بخش تمرین کوچک 2: " + item["sections"][0]["text"]
    with pytest.raises(ValueError, match="prompt or draft instruction"):
        validate_content(item)


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


def test_daily_channel_defaults_to_retention_gated_shorts():
    config = yaml.safe_load(Path("config/channel.yaml").read_text(encoding="utf-8"))
    content = config["content"]
    assert content["production_format"] == "shorts"
    assert content["target_duration_seconds"] == "18-30"
    assert content["target_word_count"] == "28-44"


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


def test_private_upload_never_enters_comment_moderation():
    assert not _should_run_comment_moderation(
        dry_run=False, upload_private=True, upload={"ok": True, "privacy": "private"}
    )
    assert _should_run_comment_moderation(
        dry_run=False, upload_private=False, upload={"ok": True, "privacy": "scheduled"}
    )


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


def test_local_ollama_uses_constrained_json_mode(monkeypatch):
    from app import local_ai

    captured = {}
    monkeypatch.setattr(local_ai, "ollama_available", lambda: True)

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"response":"{\\"ok\\":true}"}'

    def fake_urlopen(request, timeout):
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return Response()

    monkeypatch.setattr(local_ai.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("OLLAMA_NUM_PREDICT", "4096")
    monkeypatch.setenv("OLLAMA_NUM_CTX", "4096")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "600")
    result = local_ai.ollama_generate("make JSON", system="JSON only", model="llama3.2:1b", format_json=True)

    assert result == '{"ok":true}'
    assert captured["payload"]["format"] == "json"
    assert captured["payload"]["options"]["num_predict"] == 4096
    assert captured["payload"]["options"]["num_ctx"] == 4096
    assert captured["timeout"] == 600

def test_brand_and_niche_seo_tags_are_mandatory():
    value = validate_content(_content())
    assert {
        "ImamAli110", "The110Path", "امام علی", "معنویت اسلامی",
        "توکل", "برکت", "رشد فردی", "سواد مالی", "مدیریت مالی شخصی",
    }.issubset(set(value["tags"]))

def test_title_is_prefixed_with_imam_ali_brand():
    value = validate_content(_content())
    assert value["title"].startswith("Imam Ali ✨ ")
    assert len(value["title"]) <= 90


def test_thumbnail_brand_uses_a_latin_capable_font():
    from app.spiritual_video import _font

    arabic = ("NotoNaskhArabic-Regular.ttf", "NotoSansArabic-Regular.ttf")
    if not any((Path("/usr/share/fonts/truetype/noto") / name).exists() for name in arabic):
        pytest.skip("Noto Arabic fonts are not installed")
    # The Noto Arabic faces carry no Latin glyphs, so the Latin brand name
    # must never be drawn with them.
    assert Path(_font(30, persian=True).path).name in arabic
    assert Path(_font(30, persian=False).path).name not in arabic
