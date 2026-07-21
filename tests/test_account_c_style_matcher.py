from __future__ import annotations

import copy
import unittest

from modules.source_intake.account_c_style_matcher import run_account_c_style_matcher


FINGERPRINT = {
    "item_type": "jacket",
    "silhouette": "cropped",
    "color": ["black", "charcoal"],
    "material": "leather",
    "pattern": "solid",
    "detail": ["zip", "minimal"],
    "use_context": "evening",
}


class AccountCStyleMatcherTests(unittest.TestCase):
    def test_strong_match_returns_explicit_evidence_and_safe_relation(self):
        candidates = [
            {
                "candidate_id": "strong",
                "price_tier": "mid_range",
                "item_type": "JACKET",
                "silhouette": "cropped",
                "color": "black",
                "material": "leather",
                "pattern": "solid",
                "detail": ["zip", "belt"],
                "use_context": "evening",
            }
        ]

        result = run_account_c_style_matcher(FINGERPRINT, candidates)

        self.assertEqual("matched", result["status"])
        self.assertEqual(1, result["selected_count"])
        match = result["matches"][0]
        self.assertEqual("similar_silhouette", match["relation_label"])
        self.assertEqual(1.0, match["score"])
        self.assertEqual(list(FINGERPRINT), match["evidence"]["compared_attributes"])
        self.assertEqual(["black"], match["evidence"]["matched_values"]["color"]["shared_values"])

    def test_weak_match_and_unknown_only_candidate_are_excluded(self):
        candidates = [
            {
                "candidate_id": "weak",
                "price_tier": "accessible",
                "item_type": "coat",
                "silhouette": "oversized",
                "color": "black",
                "material": "wool",
            },
            {
                "candidate_id": "unknown",
                "price_tier": "accessible",
                "item_type": "unknown",
                "silhouette": "정보 없음",
                "color": None,
                "material": [],
            },
        ]

        result = run_account_c_style_matcher(FINGERPRINT, candidates)

        self.assertEqual("no_matches", result["status"])
        reasons = {item["candidate_id"]: item["reason_code"] for item in result["excluded"]}
        self.assertEqual("below_match_threshold", reasons["weak"])
        self.assertEqual("insufficient_compared_attributes", reasons["unknown"])

    def test_price_tiers_are_kept_separate(self):
        candidates = [
            {
                "candidate_id": tier,
                "price_tier": tier,
                "item_type": "jacket",
                "silhouette": "cropped",
                "color": "black",
            }
            for tier in ("accessible", "luxury_reference", "mid_range")
        ]

        result = run_account_c_style_matcher(FINGERPRINT, candidates)

        self.assertEqual(3, result["selected_count"])
        self.assertEqual(
            ["luxury_reference", "mid_range", "accessible"],
            [item["tier"] for item in result["matches"]],
        )
        for tier in ("luxury_reference", "mid_range", "accessible"):
            self.assertEqual([tier], [item["candidate_id"] for item in result["matches_by_tier"][tier]])

    def test_forbidden_claim_is_removed_from_output_and_never_becomes_relation(self):
        candidate = {
            "candidate_id": "unsafe",
            "price_tier": "luxury_reference",
            "item_type": "jacket",
            "silhouette": "cropped",
            "color": "black",
            "relation_claim": "exact celebrity_worn dupe",
        }

        result = run_account_c_style_matcher(FINGERPRINT, [candidate])

        self.assertEqual([], result["matches"])
        self.assertEqual("forbidden_equivalence_claim_removed", result["manual_review"][0]["reason_code"])
        self.assertIn(result["manual_review"][0]["safe_relation_label"], {"similar_mood", "similar_silhouette"})
        serialized = repr(result).lower()
        self.assertNotIn("celebrity_worn", serialized)
        self.assertNotIn("exact celebrity", serialized)

    def test_missing_tier_requires_manual_review_without_fabrication(self):
        candidate = {
            "candidate_id": "no-tier",
            "item_type": "jacket",
            "silhouette": "cropped",
            "color": "black",
        }

        result = run_account_c_style_matcher(FINGERPRINT, [candidate])

        self.assertEqual([], result["matches"])
        self.assertIsNone(result["manual_review"][0]["tier"])
        self.assertEqual("missing_or_invalid_price_tier", result["manual_review"][0]["reason_code"])

    def test_ordering_is_deterministic_and_inputs_are_not_mutated(self):
        candidates = [
            {
                "candidate_id": candidate_id,
                "price_tier": "mid_range",
                "item_type": "jacket",
                "silhouette": "cropped",
                "color": "black",
                "material": material,
            }
            for candidate_id, material in (("b", "wool"), ("a", "wool"), ("z", "leather"))
        ]
        fingerprint_snapshot = copy.deepcopy(FINGERPRINT)
        candidates_snapshot = copy.deepcopy(candidates)

        first = run_account_c_style_matcher(FINGERPRINT, candidates)
        second = run_account_c_style_matcher(FINGERPRINT, list(reversed(candidates)))

        self.assertEqual(["z", "a", "b"], [item["candidate_id"] for item in first["matches"]])
        self.assertEqual(first["matches"], second["matches"])
        self.assertEqual(fingerprint_snapshot, FINGERPRINT)
        self.assertEqual(candidates_snapshot, candidates)


if __name__ == "__main__":
    unittest.main()
