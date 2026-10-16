import json
import tempfile
import unittest
from pathlib import Path

from science_engine.cli import load_records, merge_records, save_records, search_bank


class ScienceIdeaBankTests(unittest.TestCase):
    def test_deduplicates_by_normalized_title(self):
        existing = [{"title": "What is Space?", "tags": ["physics"]}]
        incoming = [
            {"title": "what is space", "tags": ["cosmology"]},
            {"title": "Why is the sky blue?", "tags": ["physics"]},
        ]
        merged, added = merge_records(existing, incoming)
        self.assertEqual(added, 1)
        self.assertEqual(len(merged), 2)

    def test_deduplicates_by_doi(self):
        existing = [{"title": "Paper A", "doi": "https://doi.org/10.1234/example"}]
        incoming = [{"title": "Different title", "doi": "https://doi.org/10.1234/example"}]
        merged, added = merge_records(existing, incoming)
        self.assertEqual(added, 0)
        self.assertEqual(len(merged), 1)

    def test_search_matches_tags_and_title(self):
        records = [
            {"title": "Quantum entanglement", "tags": ["physics"]},
            {"title": "Catalysts and reaction rates", "tags": ["chemistry"]},
        ]
        self.assertEqual(search_bank("quantum", records)[0]["title"], "Quantum entanglement")
        self.assertEqual(search_bank("chemistry", records)[0]["title"], "Catalysts and reaction rates")

    def test_jsonl_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ideas.jsonl"
            expected = [{"title": "A question", "hook": "Why?"}, {"title": "Second question"}]
            save_records(expected, path)
            self.assertEqual(load_records(path), expected)
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            self.assertTrue(all(isinstance(json.loads(line), dict) for line in lines))


if __name__ == "__main__":
    unittest.main()
