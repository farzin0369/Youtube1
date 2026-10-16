import json
import tempfile
import unittest
from pathlib import Path

from science_engine.cli import dedupe_key, load_records, merge_records, save_records, search_bank
from science_engine.ranking import rank_idea, rank_ideas


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
        existing = [{"title": "Paper A", "sources": [{"doi": "https://doi.org/10.1234/example"}]}]
        incoming = [{"title": "Different title", "doi": "10.1234/example"}]
        merged, added = merge_records(existing, incoming)
        self.assertEqual(added, 0)
        self.assertEqual(len(merged), 1)
        self.assertEqual(dedupe_key(existing[0]), dedupe_key(incoming[0]))

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

    def test_ranking_is_bounded_and_explainable(self):
        record = {
            "id": "x",
            "title": "Why does light bend near a black hole?",
            "hook": "What if the straightest path in space looked curved?",
            "plain_explanation": "A plain explanation.",
            "deeper_angle": "A deeper explanation.",
            "tags": ["physics", "space"],
            "sources": [{"provider": "OpenAlex", "doi": "10.1234/abc"}],
            "evidence_status": "established_science",
            "workflow_status": "seed_reviewed",
            "visual_plan": ["Show a curved grid"],
        }
        result = rank_idea(record)
        self.assertGreaterEqual(result["priority_score"], 0)
        self.assertLessEqual(result["priority_score"], 100)
        self.assertIn("components", result)
        self.assertFalse(result["review_required"])

    def test_ranking_marks_philosophy_for_review(self):
        result = rank_idea({"title": "Does mathematics exist independently?", "evidence_status": "philosophical_debate"})
        self.assertTrue(result["review_required"])

    def test_rank_ideas_sorted_highest_first(self):
        results = rank_ideas([{"title": "Untitled"}, {"title": "Why is space curved?", "hook": "What if space were curved?", "tags": ["space"]}])
        self.assertGreaterEqual(results[0]["priority_score"], results[1]["priority_score"])


if __name__ == "__main__":
    unittest.main()
