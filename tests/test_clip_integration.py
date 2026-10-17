import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.clip_integration import build_clip_derivatives_if_enabled


class ClipIntegrationTests(unittest.TestCase):
    def test_disabled_is_skipped(self):
        result = build_clip_derivatives_if_enabled(
            "video.mp4", "out", video_format="long",
            config={"clip_derivatives": {"enabled": False}},
        )
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "disabled")

    def test_shorts_are_never_recut(self):
        with patch("app.clip_automation.build_clips") as build:
            result = build_clip_derivatives_if_enabled(
                "video.mp4", "out", video_format="shorts",
                config={"clip_derivatives": {"enabled": True}},
            )
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "source_is_not_long_form")
        build.assert_not_called()

    def test_long_form_creates_local_derivatives_without_publishing(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "clips"
            with patch("app.clip_automation.build_clips", return_value={"candidates": [{}, {}, {}]}) as build:
                result = build_clip_derivatives_if_enabled(
                    Path(temp) / "source.mp4", output, video_format="long",
                    config={"clip_derivatives": {"enabled": True, "clip_seconds": 30, "count": 3}},
                )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["candidate_count"], 3)
        self.assertFalse(result["auto_publish"])
        build.assert_called_once()
        self.assertTrue(build.call_args.kwargs["rights_confirmed"])


if __name__ == "__main__":
    unittest.main()
