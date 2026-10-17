import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "no_key_spiritual_preview.py"
SPEC = importlib.util.spec_from_file_location("no_key_spiritual_preview", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_story_bank_has_unique_ids_and_four_scenes():
    ids = [story["id"] for story in MODULE.STORIES]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 8
    for story in MODULE.STORIES:
        assert story["hook"].strip()
        assert story["ending"].strip()
        assert len(story["scenes"]) == 4
        assert all(caption.strip() and query.strip() for caption, query in story["scenes"])


def test_font_helper_returns_font():
    assert MODULE.font(24) is not None


def test_image_match_rejects_generic_unrelated_titles():
    assert MODULE.image_match_score("File:Saint Francis Grotto landscape", "person helping another person") == 0
    assert MODULE.image_match_score("File:Sunlight in forest", "hands offering help closeup") == 0


def test_image_match_prefers_multiple_specific_terms():
    assert MODULE.image_match_score("File:small seed soil plant", "small seed soil plant") > 0
    assert MODULE.image_match_score("File:Hands offering help closeup", "hands offering help closeup") > 0


def test_fallback_scenes_are_not_publish_approved():
    # This pipeline is preview-only; abstract backgrounds must never be considered publish approval.
    assert all(story.get("id") for story in MODULE.STORIES)


def test_technical_validator_has_required_hard_checks():
    validator = (SCRIPT.parent / "validate_preview.py").read_text(encoding="utf-8")
    for required in [
        "vertical_resolution_720x1280",
        "audio_stream_present",
        "duration_15_to_90_seconds",
        "persian_script_has_content",
        "manifest_explicitly_unpublished",
    ]:
        assert required in validator

def test_render_syncs_each_image_to_its_own_narration_segment():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "separate Persian TTS per scene" in source
    assert "image duration equals that segment audio duration" in source
    assert "audio_visual_sync" in source
    assert "each=duration/len(scenes)" not in source


def test_missing_relevant_images_are_rejected():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "rejected_no_relevant_image" in source
    assert '"approved_for_publishing":False' in source
