import copy
import unittest

from modules.source_intake.reviewed_evidence_validator import is_verified_reviewed_evidence_bundle


def reviewed_bundle():
    return {
        "status": "verified", "verified": True, "eligible": True,
        "bundle_evidence_needs": [], "warnings": [],
        "verified_evidence_items": [{
            "evidence_id": "evidence-1", "verification_status": "verified",
            "reviewer_type": "human", "reviewed_at": "2026-07-16T10:00:00+09:00",
            "source_url": "https://www.korea.kr/briefing/1", "claim_ids": ["claim-1"],
        }],
        "claims": [{
            "claim_id": "claim-1", "status": "verified", "claim_alignment": True,
            "evidence_needs": [], "verified_evidence_ids": ["evidence-1"],
        }],
    }


class ReviewedEvidenceValidatorTests(unittest.TestCase):
    def test_valid_bound_bundle_passes_without_mutation(self):
        value = reviewed_bundle(); before = copy.deepcopy(value)
        self.assertTrue(is_verified_reviewed_evidence_bundle(value)); self.assertEqual(before, value)

    def test_nonexistent_or_cross_claim_reference_fails(self):
        missing = reviewed_bundle(); missing["claims"][0]["verified_evidence_ids"] = ["not-present"]
        self.assertFalse(is_verified_reviewed_evidence_bundle(missing))
        mismatch = reviewed_bundle(); mismatch["verified_evidence_items"][0]["claim_ids"] = ["other"]
        self.assertFalse(is_verified_reviewed_evidence_bundle(mismatch))

    def test_unreviewed_or_malformed_evidence_item_fails(self):
        for patch in ({"reviewer_type": "model"}, {"reviewed_at": "2026-07-16T10:00:00"},
                      {"source_url": "https://["}, {"source_url": "https://www.korea.kr:bad/x"},
                      {"source_url": "https://www.korea.kr:8443/x"},
                      {"verification_status": "candidate"}):
            value = reviewed_bundle(); value["verified_evidence_items"][0].update(patch)
            self.assertFalse(is_verified_reviewed_evidence_bundle(value))

    def test_duplicate_evidence_or_claim_ids_fail(self):
        value = reviewed_bundle(); value["verified_evidence_items"].append(copy.deepcopy(value["verified_evidence_items"][0]))
        self.assertFalse(is_verified_reviewed_evidence_bundle(value))
        value = reviewed_bundle(); value["claims"].append(copy.deepcopy(value["claims"][0]))
        self.assertFalse(is_verified_reviewed_evidence_bundle(value))


if __name__ == "__main__": unittest.main()
