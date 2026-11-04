import json
from pathlib import Path

import pytest

from scripts import render_ai_domain_proof as proof


def test_single_scene_duration_rejects_invalid_or_misaligned_timing():
    assert proof._single_scene_duration(
        [{"start_seconds": 0.0, "end_seconds": 8.0}], 8.1,
    ) == 8.1
    with pytest.raises(ValueError, match="exactly one timing"):
        proof._single_scene_duration([], 8.0)
    with pytest.raises(ValueError, match="does not match"):
        proof._single_scene_duration(
            [{"start_seconds": 0.0, "end_seconds": 6.0}], 8.0,
        )


def test_proof_emits_three_distinct_narrated_mp4s_and_frame_samples(tmp_path: Path, monkeypatch):
    out = tmp_path / "proof"
    monkeypatch.setattr(proof, "OUT", out)
    synth_calls = []
    render_calls = []
    camera_moves = iter(("orbit", "tracking", "sweep"))

    def fake_synthesize(text, audio_path, captions_path, *, scenes):
        synth_calls.append(text)
        audio_path.write_bytes(b"a" * 9_000)
        captions_path.write_text("1\n00:00:00,000 --> 00:00:08,000\ncaption\n", encoding="utf-8")
        return {
            "ok": True,
            "provider": "edge-tts",
            "voice": "fa-IR-test",
            "scene_timings": [{"start_seconds": 0.0, "end_seconds": 8.0}],
        }

    def fake_direct_scene(*, narration, visual_brief, **kwargs):
        index = len(synth_calls) - 1
        return {
            "domain": proof.SCENES[index]["domain"],
            "matched_by": "semantic_ai_director",
            "provider": "test-local-model",
            "critic_provider": "test-critic",
            "semantic_review_score": 90,
            "visual_thesis": f"Thesis {index}",
            "camera": {"move": next(camera_moves), "angle": "eye", "focus": "subject"},
            "palette": {"background": "#101010", "key": "#ffffff", "accent": "#ffcc00"},
            "objects": [
                {"id": f"object_{index}_{part}", "kind": "sphere"}
                for part in ("a", "b", "c")
            ],
            "relationships": [],
        }

    def fake_render(project, output, *, audio):
        scene = project["scenes"][0]
        assert len(project["scenes"]) == 1
        assert scene["scene_graph"]["objects"]
        assert Path(audio).is_file()
        render_calls.append(scene["narration"])
        output = Path(output)
        output.write_bytes((output.name.encode() + b"x" * 100_000))
        return output

    def fake_burn(source_video, captions_srt, output_video, *, hook, duration):
        assert Path(source_video).is_file() and Path(captions_srt).is_file()
        assert hook and duration == 8.0
        output_video = Path(output_video)
        output_video.write_bytes(output_video.name.encode() + b"c" * 100_000)
        ass = output_video.with_suffix(".ass")
        ass.write_text("timed Persian captions", encoding="utf-8")
        return ass

    def fake_sample(video, duration, destination):
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        paths = []
        for label in ("start", "middle", "end"):
            path = destination / f"{label}.jpg"
            path.write_bytes(b"f" * 1_200)
            paths.append(str(path))
        return paths

    monkeypatch.setattr(proof, "synthesize_with_captions", fake_synthesize)
    monkeypatch.setattr(proof, "direct_scene", fake_direct_scene)
    monkeypatch.setattr(proof, "render_project", fake_render)
    monkeypatch.setattr(proof, "_burn_word_timed_captions", fake_burn)
    monkeypatch.setattr(proof, "probe_duration", lambda _path: 8.0)
    monkeypatch.setattr(proof, "probe_stream_duration", lambda _path, _selector: 8.0)
    monkeypatch.setattr(proof, "_sample_frames", fake_sample)

    proof.main()

    evidence = json.loads((out / "ai-domain-evidence.json").read_text(encoding="utf-8"))
    videos = evidence["videos"]
    assert len(videos) == 3
    assert {row["domain"] for row in videos} == {scene["domain"] for scene in proof.SCENES}
    assert len({row["video_path"] for row in videos}) == 3
    assert len({row["video_sha256"] for row in videos}) == 3
    assert len(synth_calls) == len(render_calls) == 3
    assert all(len(row["inspection_frames"]) == 3 for row in videos)
    assert all(Path(row["video_path"]).is_file() for row in videos)
    assert all(Path(row["burned_caption_path"]).is_file() for row in videos)
    assert evidence["public_upload"] is False
    assert evidence["production_visuals_approved"] is False
