import unittest

from modules.card_news.visual_qa_gate import SCHEMA_VERSION, assess_visual_qa_receipt


HASH_A = "a" * 64
HASH_B = "b" * 64


def expected_slides():
    return [
        {
            "account": "B",
            "candidate_id": "candidate-b",
            "page": 1,
            "image_path": "out/b/01.png",
            "image_sha256": HASH_A,
            "requires_comment_readability": False,
        },
        {
            "account": "B",
            "candidate_id": "candidate-b",
            "page": 2,
            "image_path": "out/b/02.png",
            "image_sha256": HASH_B,
            "requires_comment_readability": True,
        },
    ]


def finding(comment=False):
    return {
        "mobile_readability": "pass",
        "copy_density_ok": "pass",
        "image_is_primary": "pass",
        "feed_caption_present": "pass",
        "copy_readability": "pass",
        "content_not_blank": "pass",
        "subject_focus": "pass",
        "subject_crop_preserved": "pass",
        "comment_readability": "pass" if comment else "not_applicable",
        "story_progression": "pass",
    }


def complete_receipt():
    return {
        "schema_version": SCHEMA_VERSION,
        "receipt_id": "visual-receipt-1",
        "output_set_id": "output-set-1",
        "feed_caption": "별도 피드 본문으로 카드뉴스를 이어읽을 수 있어야 한다.",
        "reviewed_at": "2026-07-19T12:00:00+09:00",
        "maker": {"id": "renderer-worker"},
        "reviewer": {"id": "owner-reviewer", "independent_from_maker": True},
        "scope": {
            "kind": "representative",
            "accounts": ["B"],
            "candidate_ids": ["candidate-b"],
        },
        "decision": "approve",
        "slides": [
            {
                "candidate_id": "candidate-b",
                "page": 1,
                "image_path": "out/b/01.png",
                "image_sha256": HASH_A,
                "width": 1080,
                "height": 1350,
                "findings": finding(),
            },
            {
                "candidate_id": "candidate-b",
                "page": 2,
                "image_path": "out/b/02.png",
                "image_sha256": HASH_B,
                "width": 1080,
                "height": 1350,
                "findings": finding(comment=True),
            },
        ],
    }


class CardnewsVisualQaGateTests(unittest.TestCase):
    def test_dimensions_alone_do_not_count_as_visual_approval(self):
        receipt = complete_receipt()
        for slide in receipt["slides"]:
            slide.pop("image_sha256")
            slide.pop("findings")

        result = assess_visual_qa_receipt(receipt, expected_slides())

        self.assertFalse(result["visual_qa_passed"])
        self.assertFalse(result["dimensions_are_visual_approval"])
        codes = {item["reason_code"] for item in result["failures"]}
        self.assertIn("visual_qa_image_hash_missing", codes)
        self.assertIn("visual_qa_finding_missing", codes)

    def test_maker_cannot_be_reviewer(self):
        receipt = complete_receipt()
        receipt["reviewer"]["id"] = receipt["maker"]["id"]

        result = assess_visual_qa_receipt(receipt, expected_slides())

        self.assertFalse(result["visual_qa_passed"])
        self.assertIn(
            "visual_qa_reviewer_not_independent",
            {item["reason_code"] for item in result["failures"]},
        )

    def test_missing_slide_and_hash_fail_closed(self):
        receipt = complete_receipt()
        receipt["slides"] = receipt["slides"][:1]
        receipt["slides"][0]["image_sha256"] = ""

        result = assess_visual_qa_receipt(receipt, expected_slides())

        self.assertFalse(result["visual_qa_passed"])
        codes = {item["reason_code"] for item in result["failures"]}
        self.assertIn("visual_qa_image_hash_missing", codes)
        self.assertIn("visual_qa_slide_missing", codes)

    def test_rejected_visual_finding_blocks_receipt(self):
        receipt = complete_receipt()
        receipt["slides"][0]["findings"]["subject_focus"] = "rejected"

        result = assess_visual_qa_receipt(receipt, expected_slides())

        self.assertFalse(result["visual_qa_passed"])
        self.assertIn(
            "visual_qa_finding_rejected",
            {item["reason_code"] for item in result["failures"]},
        )

    def test_blank_copy_or_destructive_crop_cannot_pass(self):
        receipt = complete_receipt()
        receipt["slides"][0]["findings"]["content_not_blank"] = "fail"
        receipt["slides"][1]["findings"]["subject_crop_preserved"] = "rejected"

        result = assess_visual_qa_receipt(receipt, expected_slides())

        self.assertFalse(result["visual_qa_passed"])
        rejected_fields = {
            item["field"] for item in result["failures"]
            if item["reason_code"] == "visual_qa_finding_rejected"
        }
        self.assertIn("slides[1].findings.content_not_blank", rejected_fields)
        self.assertIn("slides[2].findings.subject_crop_preserved", rejected_fields)

    def test_comment_slide_requires_readability_judgment(self):
        receipt = complete_receipt()
        receipt["slides"][1]["findings"]["comment_readability"] = "not_applicable"

        result = assess_visual_qa_receipt(receipt, expected_slides())

        self.assertFalse(result["visual_qa_passed"])
        self.assertIn(
            "visual_qa_comment_readability_required",
            {item["reason_code"] for item in result["failures"]},
        )

    def test_batch_requires_representative_receipt_for_each_account(self):
        receipt = complete_receipt()
        receipt["scope"]["kind"] = "batch"

        result = assess_visual_qa_receipt(receipt, expected_slides())

        self.assertFalse(result["visual_qa_passed"])
        self.assertIn(
            "visual_qa_batch_representative_missing",
            {item["reason_code"] for item in result["failures"]},
        )

        receipt["scope"]["representative_receipt_ids"] = {"B": "visual-representative-b"}
        result = assess_visual_qa_receipt(receipt, expected_slides())
        self.assertTrue(result["visual_qa_passed"], result["failures"])

    def test_complete_independent_receipt_passes(self):
        result = assess_visual_qa_receipt(
            complete_receipt(), expected_slides(), expected_output_set_id="output-set-1"
        )

        self.assertTrue(result["visual_qa_passed"], result["failures"])
        self.assertEqual("passed", result["status"])
        self.assertTrue(result["reviewer_independent"])
        self.assertEqual(2, result["reviewed_slide_count"])
        self.assertEqual([], result["failures"])

    def test_batch_must_bind_exact_approved_representative_receipt(self):
        receipt = complete_receipt()
        receipt["scope"]["kind"] = "batch"
        receipt["scope"]["representative_receipt_ids"] = {"B": "made-up-id"}

        result = assess_visual_qa_receipt(
            receipt,
            expected_slides(),
            expected_representative_receipt_ids={"B": "approved-representative-b"},
        )

        self.assertFalse(result["visual_qa_passed"])
        self.assertIn(
            "visual_qa_batch_representative_mismatch",
            {item["reason_code"] for item in result["failures"]},
        )

    def test_feed_caption_present_required(self):
        receipt = complete_receipt()
        pass_result = assess_visual_qa_receipt(receipt, expected_slides())
        self.assertTrue(pass_result["visual_qa_passed"], pass_result["failures"])

        missing = complete_receipt()
        missing["feed_caption"] = ""
        fail_result = assess_visual_qa_receipt(missing, expected_slides())

        self.assertFalse(fail_result["visual_qa_passed"])
        self.assertIn(
            "visual_qa_feed_caption_required",
            {item["reason_code"] for item in fail_result["failures"]},
        )
        self.assertIn(
            "slides[1].findings.feed_caption_present",
            {item["field"] for item in fail_result["failures"] if item["reason_code"] == "visual_qa_feed_caption_required"},
        )


if __name__ == "__main__":
    unittest.main()
