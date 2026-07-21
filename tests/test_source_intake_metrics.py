import unittest
import json
from pathlib import Path

from modules.source_intake.source_intake_metrics import (
    DEFAULT_DEEP_DIVE_THRESHOLD,
    NEUTRAL_VELOCITY_SCORE,
    compute_deep_dive_priority,
    compute_derived_metrics,
    select_deep_dive_candidates,
)


class TestDerivedMetrics(unittest.TestCase):
    def test_basic_ratios(self):
        derived = compute_derived_metrics(
            {"views": 1000, "comments": 50, "likes": 20},
            published_at="2026-07-14T09:00:00",
            collected_at="2026-07-14T12:00:00",
        )
        self.assertAlmostEqual(derived["comment_density"], 0.05)
        self.assertAlmostEqual(derived["like_rate"], 0.02)
        # controversy = comments / max(likes, 1) = 50 / 20
        self.assertAlmostEqual(derived["controversy_score"], 2.5)
        # velocity = (50 + 20) reactions / 3 hours
        self.assertAlmostEqual(derived["velocity_score"], round(70 / 3, 6))
        self.assertFalse(derived["velocity_fallback"])

    def test_null_and_zero_denominators_are_safe(self):
        for metrics in (
            None,
            {},
            {"views": 0, "comments": 10},
            {"views": None, "comments": None, "likes": None},
        ):
            derived = compute_derived_metrics(metrics)
            self.assertIsNone(derived["comment_density"])
            self.assertIsNone(derived["like_rate"])

    def test_controversy_zero_likes_uses_max_one(self):
        derived = compute_derived_metrics({"views": 100, "comments": 30, "likes": 0})
        self.assertAlmostEqual(derived["controversy_score"], 30.0)

    def test_controversy_dislike_correction(self):
        base = compute_derived_metrics({"comments": 20, "likes": 10})
        corrected = compute_derived_metrics({"comments": 20, "likes": 10, "dislikes": 10})
        self.assertGreater(corrected["controversy_score"], base["controversy_score"])

    def test_velocity_fallback_without_published_at(self):
        derived = compute_derived_metrics(
            {"views": 1000, "comments": 50, "likes": 20},
            published_at=None,
            collected_at="2026-07-14T12:00:00",
        )
        self.assertEqual(derived["velocity_score"], NEUTRAL_VELOCITY_SCORE)
        self.assertTrue(derived["velocity_fallback"])
        self.assertEqual(derived["velocity_reason"], "missing_published_at")

    def test_velocity_fallback_with_garbage_published_at(self):
        derived = compute_derived_metrics(
            {"comments": 5},
            published_at="어제쯤",
            collected_at="2026-07-14T12:00:00",
        )
        self.assertEqual(derived["velocity_score"], NEUTRAL_VELOCITY_SCORE)
        self.assertTrue(derived["velocity_fallback"])

    def test_velocity_clamps_tiny_elapsed_time(self):
        derived = compute_derived_metrics(
            {"comments": 10, "likes": 0},
            published_at="2026-07-14T12:00:00",
            collected_at="2026-07-14T12:00:01",
        )
        # elapsed clamps to 0.1h -> 10 / 0.1 = 100, never division blowup
        self.assertAlmostEqual(derived["velocity_score"], 100.0)

    def test_deterministic(self):
        args = (
            {"views": 500, "comments": 25, "likes": 5, "dislikes": 2},
            "2026-07-14T08:00:00",
            "2026-07-14T12:00:00",
        )
        self.assertEqual(compute_derived_metrics(*args), compute_derived_metrics(*args))


class TestDeepDivePriority(unittest.TestCase):
    def test_priority_respects_channel_candidates(self):
        derived = compute_derived_metrics(
            {"views": 1000, "comments": 60, "likes": 5},
            published_at="2026-07-14T10:00:00",
            collected_at="2026-07-14T12:00:00",
        )
        result = compute_deep_dive_priority(derived, ["issue_daily", "dopamine_issue"])
        self.assertIn(result["best_channel"], ["issue_daily", "dopamine_issue"])
        self.assertEqual(
            sorted(result["channel_scores"].keys()),
            sorted(["issue_daily", "dopamine_issue"]),
        )
        self.assertGreaterEqual(result["deep_dive_priority"], 0.0)
        self.assertLessEqual(result["deep_dive_priority"], 1.0)

    def test_no_metrics_gives_low_priority(self):
        derived = compute_derived_metrics(None)
        result = compute_deep_dive_priority(derived)
        # only neutral velocity contributes; must stay under the deep-dive gate
        self.assertLess(result["deep_dive_priority"], DEFAULT_DEEP_DIVE_THRESHOLD)

    def test_threshold_gate_selects_only_hot_items(self):
        items = [
            {"item_id": "cold", "deep_dive_priority": 0.10},
            {"item_id": "warm", "deep_dive_priority": DEFAULT_DEEP_DIVE_THRESHOLD},
            {"item_id": "hot", "deep_dive_priority": 0.90},
            {"item_id": "broken", "deep_dive_priority": None},
        ]
        selected = select_deep_dive_candidates(items)
        self.assertEqual([item["item_id"] for item in selected], ["hot", "warm"])

    def test_threshold_gate_caps_count(self):
        items = [
            {"item_id": f"i{i}", "deep_dive_priority": 0.5 + i * 0.01}
            for i in range(10)
        ]
        selected = select_deep_dive_candidates(items, max_count=3)
        self.assertEqual(len(selected), 3)
        self.assertEqual(selected[0]["item_id"], "i9")


class TestSourceIntakeConfigContract(unittest.TestCase):
    def test_fmkorea_expected_metrics_are_visible_only(self):
        config_path = Path("config/source_intake_sources.json")
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        sources = payload.get("sources", [])
        fmkorea = next(
            (item for item in sources if item.get("source_id") == "fmkorea"),
            None,
        )

        self.assertIsNotNone(fmkorea)
        self.assertEqual(
            fmkorea.get("expected_metrics"),
            ["rank_position", "comments", "likes"],
        )


if __name__ == "__main__":
    unittest.main()
