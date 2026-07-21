import unittest

from modules.design_learning.card_news_design_learning import (
    build_design_candidates,
    validate_design_candidates,
)


class TestCardNewsDesignLearning(unittest.TestCase):
    def setUp(self):
        self.payload = build_design_candidates()

    def test_builds_candidates_from_existing_instagram_learning(self):
        self.assertGreaterEqual(self.payload["candidate_count"], 20)
        self.assertEqual(
            self.payload["schema_version"],
            "card_news_design_learning_v1",
        )

    def test_all_candidates_validate(self):
        errors = validate_design_candidates(self.payload)
        self.assertEqual(errors, [])

    def test_does_not_add_eleventh_layout(self):
        self.assertEqual(len(self.payload["existing_layout_ids"]), 10)
        for candidate in self.payload["candidates"]:
            self.assertIn(
                candidate["recommended_existing_layout"],
                self.payload["existing_layout_ids"],
            )

    def test_imported_items_remain_candidates_not_verified(self):
        for candidate in self.payload["candidates"]:
            self.assertEqual(candidate["status"], "CANDIDATE")
            self.assertIn(
                candidate["confidence"],
                {"benchmark_observed", "hypothesis_only"},
            )

    def test_dm_or_comment_style_structures_are_review_flagged(self):
        flagged = [
            candidate
            for candidate in self.payload["candidates"]
            if "의견 유도" in candidate["observed_pattern"]
        ]
        self.assertTrue(flagged)
        self.assertTrue(
            any("comment_cta_review" in item["risk_flags"] for item in flagged)
        )


if __name__ == "__main__":
    unittest.main()
