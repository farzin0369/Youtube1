from pathlib import Path
import unittest
from unittest.mock import patch

from app.clip_automation import rank_candidates, build_clips


class ClipAutomationTests(unittest.TestCase):
    def test_rank_candidates_prefers_windows_with_more_scene_changes(self):
        result = rank_candidates(120, 20, [10, 15, 18, 70, 95], 2)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(0 <= item['start'] <= 100 for item in result))
        self.assertTrue(all(item['duration'] == 20 for item in result))

    def test_rejects_too_short_source(self):
        with self.assertRaisesRegex(ValueError, 'at least'):
            rank_candidates(10, 20, [], 1)

    def test_rights_confirmation_required_before_processing(self):
        with self.assertRaises(PermissionError):
            build_clips(Path('not-a-real-file.mp4'), Path('output'), rights_confirmed=False)

    def test_rejects_invalid_count(self):
        with self.assertRaises(ValueError):
            rank_candidates(120, 20, [], 11)


if __name__ == '__main__':
    unittest.main()
