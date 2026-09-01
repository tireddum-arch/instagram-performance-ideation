from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "instagram_ideation.py"
SPEC = importlib.util.spec_from_file_location("instagram_ideation", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def post(self, media_id, days_old, reach, shares, follows=0, caption=""):
        timestamp = (self.now - timedelta(days=days_old)).isoformat()
        return {
            "id": media_id,
            "caption": caption,
            "timestamp": timestamp,
            "permalink": f"https://example.invalid/{media_id}",
            "metrics": {"reach": reach, "shares": shares, "follows": follows},
        }

    def labels(self):
        return {
            "high": {"content_text": "late meeting escape plan", "topic": "work", "exclude": False},
            "mid": {"content_text": "payday budget collapse", "topic": "money", "exclude": False},
            "tiny": {"content_text": "tiny sample miracle", "topic": "sample", "exclude": False},
            "recent": {"content_text": "current voice reference", "topic": "voice", "exclude": False},
            "excluded": {"content_text": "paid campaign", "topic": "ad", "exclude": True},
        }

    def test_rank_filters_low_reach_exclusions_and_recent_sources(self):
        posts = [
            self.post("high", 200, 10000, 500, 30),
            self.post("mid", 180, 8000, 160, 50),
            self.post("tiny", 200, 100, 20, 1),
            self.post("recent", 10, 20000, 700, 80),
            self.post("excluded", 200, 50000, 5000, 500),
        ]
        result = MODULE.rank_posts(
            posts, self.labels(), set(), "shares", "follows", 2, 1,
            min_reach=3000, min_age_days=90, recent_count=6,
            count=8, pool_size=40, dedupe_threshold=0.45, now=self.now,
        )
        self.assertEqual([p["id"] for p in result["candidates"]], ["high", "mid"])
        self.assertEqual([p["id"] for p in result["recent_reference"]], ["recent"])
        self.assertEqual(result["stats"]["excluded"], 1)
        self.assertEqual(result["stats"]["mature_below_min_reach"], 1)

    def test_rotation_resets_when_unused_pool_is_too_small(self):
        posts = [self.post("high", 200, 10000, 500), self.post("mid", 180, 8000, 160)]
        result = MODULE.rank_posts(
            posts, self.labels(), {"high", "mid"}, "shares", "", 2, 0,
            min_reach=3000, min_age_days=90, recent_count=6,
            count=2, pool_size=40, dedupe_threshold=0.45, now=self.now,
        )
        self.assertTrue(result["rotation_reset"])
        self.assertEqual(len(result["candidates"]), 2)

    def test_deduplication_keeps_better_ranked_source(self):
        first = self.post("a", 200, 10000, 500, caption="meeting escape plan now")
        second = self.post("b", 200, 10000, 400, caption="meeting escape plan today")
        labels = {
            "a": {"content_text": "meeting escape plan now"},
            "b": {"content_text": "meeting escape plan today"},
        }
        result = MODULE.rank_posts(
            [first, second], labels, set(), "shares", "", 2, 0,
            min_reach=0, min_age_days=90, recent_count=0,
            count=8, pool_size=40, dedupe_threshold=0.45, now=self.now,
        )
        self.assertEqual([p["id"] for p in result["candidates"]], ["a"])

    def test_percentile_ties_receive_equal_rank(self):
        self.assertEqual(MODULE.percentile_ranks([1, 1, 3]), [0.25, 0.25, 1.0])


class PromptTests(unittest.TestCase):
    def test_prompt_command_writes_mechanism_brief(self):
        payload = {
            "objective": {"primary": "shares", "secondary": "follows"},
            "candidates": [{
                "id": "x", "timestamp": "2025-01-01", "reach": 10000,
                "primary_count": 500, "primary_rate": 0.05,
                "secondary_count": 20, "secondary_rate": 0.002,
                "caption": "", "permalink": "https://example.invalid/x",
                "label": {"content_text": "visible hook", "mechanism": "contrast"},
            }],
            "recent_reference": [],
        }
        text = MODULE.build_prompt(payload, "Audience: creators", 3)
        self.assertIn("visible hook", text)
        self.assertIn("contrast", text)
        self.assertIn("materially different", text)
        self.assertIn("Audience: creators", text)

    def test_atomic_json_write(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "nested" / "value.json"
            MODULE.write_json(target, {"ok": True})
            self.assertEqual(json.loads(target.read_text()), {"ok": True})


if __name__ == "__main__":
    unittest.main()
