import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from app.spiritual_content import validate_content, word_count
from app.spiritual_pipeline import QUALITY_WEIGHTS, _public_mode_enabled, _publication_quality_gate, next_publish_at
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


def test_publication_slot_uses_next_configured_tehran_time():
    before = datetime(2026, 10, 11, 2, 0, tzinfo=timezone.utc)
    after_morning = datetime(2026, 10, 11, 4, 0, tzinfo=timezone.utc)
    assert next_publish_at(before) == "2026-10-11T03:30:00Z"
    assert next_publish_at(after_morning) == "2026-10-11T06:30:00Z"


def _perfect_release_inputs(tmp_path):
    video = tmp_path / "render.mp4"
    video.write_bytes(b"validated test render")
    video_sha256 = __import__("hashlib").sha256(video.read_bytes()).hexdigest()
    reviews = [
        {
            "agent_id": f"agent_{index}", "score": 100, "verdict": "approve",
            "critical_issues": [], "major_issues": [], "confidence": 0.95,
        }
        for index in range(11)
    ]
    rubric_components = {}
    for category in QUALITY_WEIGHTS:
        evidence = tmp_path / f"{category}.json"
        evidence.write_text(json.dumps({"category": category, "reviewed": True}), encoding="utf-8")
        rubric_components[category] = {
            "score": 100, "review_method": "independent-review-of-output-evidence",
            "evidence_path": str(evidence),
        }
    return {
        "render": {
            "video_path": str(video),
            "visual_source": "bamo-cpu-3d-motion",
            "production_visuals_approved": True,
            "scene_visual_alignment_verified": True,
            "visual_review_evidence": {"ok": True},
        },
        "media_quality": {"ok": True, "errors": [], "checks": {"audio": {"ok": True}}},
        "editorial_review": {"ok": True, "roles": [{"ok": True} for _ in range(11)]},
        "agent_council": {
            "ok": True, "gate": "PASS", "agents_expected": 11,
            "agents_completed": 11, "approvals": 11,
            "distinct_agent_roles_observed": 11,
            "distinct_model_ids_observed": 11,
            "distinct_provider_models_observed": 11,
            "average_score": 100, "independent_reviews": reviews,
            "agent_errors": {}, "critical_issues": [],
        },
        "weighted_quality_assessment": {
            "run_id": "test-run", "video_sha256": video_sha256,
            "weighted_score": 100, "components": rubric_components,
        },
        "run_id": "test-run",
        "evidence_root": tmp_path,
    }


def test_public_release_requires_weighted_evidence_and_all_eleven_models(tmp_path):
    inputs = _perfect_release_inputs(tmp_path)
    report = _publication_quality_gate(**inputs)
    assert report["weighted_quality_score"] == 100
    assert report["model_consensus_and_gate_score"] == 100
    assert report["publish_allowed"] is True
    assert report["independent_reviewers"] == 11


def test_public_release_blocks_if_weighted_component_or_agent_is_below_100(tmp_path):
    inputs = _perfect_release_inputs(tmp_path)
    inputs["agent_council"]["independent_reviews"][0]["score"] = 99
    inputs["agent_council"]["average_score"] = 99.9
    report = _publication_quality_gate(**inputs)
    assert report["weighted_quality_score"] == 100
    assert report["model_consensus_and_gate_score"] == 99
    assert report["publish_allowed"] is False
    assert "all_eleven_reviewers_must_score_exactly_100" in report["blockers"]


def test_public_release_blocks_missing_3d_frame_approval_even_with_perfect_council(tmp_path):
    inputs = _perfect_release_inputs(tmp_path)
    inputs["render"]["visual_review_evidence"]["ok"] = False
    report = _publication_quality_gate(**inputs)
    assert report["publish_allowed"] is False
    assert "production_visual_review_not_approved" in report["blockers"]


def test_public_release_blocks_until_evidence_backed_weighted_rubric_is_available(tmp_path):
    inputs = _perfect_release_inputs(tmp_path)
    inputs.pop("weighted_quality_assessment")
    report = _publication_quality_gate(**inputs)
    assert report["weighted_quality_score"] is None
    assert report["publish_allowed"] is False
    assert "weighted_quality_assessment_missing" in report["blockers"]


def test_public_release_blocks_a_nonperfect_weighted_category(tmp_path):
    inputs = _perfect_release_inputs(tmp_path)
    inputs["weighted_quality_assessment"]["components"]["3d_motion_graphics"]["score"] = 99
    inputs["weighted_quality_assessment"]["weighted_score"] = 99.8
    report = _publication_quality_gate(**inputs)
    assert report["weighted_quality_score"] == 99.8
    assert report["publish_allowed"] is False
    assert "weighted_quality_score_not_100" in report["blockers"]


def test_github_schedule_has_six_tehran_publication_runs():
    workflow = yaml.load(Path(".github/workflows/daily_run.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert [row["cron"] for row in workflow["on"]["schedule"]] == ["30 3 * * *", "30 6 * * *", "30 8 * * *", "30 11 * * *", "30 14 * * *", "30 17 * * *"]


def test_daily_workflow_is_local_first_key_optional_and_upload_paused():
    workflow = yaml.safe_load(Path(".github/workflows/daily_run.yml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["produce"]
    env = job["env"]
    steps = job["steps"]
    assert env["USE_LOCAL_LLM"] == "1"
    assert env["BAMO_PREFER_LOCAL_LLM"] == "1"
    assert env["LOCAL_LLM_MODEL"] == "qwen2.5:3b"
    assert env["BAMO_USE_PINNED_AGENT_MODELS"] == "false"
    assert "GROQ_API_KEY" in env  # optional fallback; no credential-verification step
    assert "OPENROUTER_API_KEY" not in env
    assert not any("Verify all 11-agent provider credentials" in step.get("name", "") for step in steps)
    assert any("ollama pull qwen2.5:3b" in step.get("run", "") for step in steps)
    assert next(step for step in steps if step.get("name") == "Verify YouTube credentials before any production work")["if"] is False
    safe_step = next(step for step in steps if step.get("name") == "Safe preview only — public publishing paused")
    assert "scripts/daily_run.py --dry-run" in safe_step["run"]
    assert workflow["permissions"]["contents"] == "read"


def test_daily_channel_defaults_to_retention_gated_shorts():
    config = yaml.safe_load(Path("config/channel.yaml").read_text(encoding="utf-8"))
    content = config["content"]
    assert content["production_format"] == "shorts"
    assert content["target_duration_seconds"] == "18-30"
    assert content["target_word_count"] == "28-44"
    assert config["publishing"]["mode"] == "private"
    assert config["publishing"]["public_publish_enabled"] is False
    assert _public_mode_enabled(config) is False


def test_public_mode_requires_explicit_true_and_public_configuration():
    assert _public_mode_enabled({"publishing": {"mode": "public", "public_publish_enabled": True}})
    assert not _public_mode_enabled({"publishing": {"mode": "public", "public_publish_enabled": "true"}})
    assert not _public_mode_enabled({"publishing": {"mode": "private", "public_publish_enabled": True}})


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
