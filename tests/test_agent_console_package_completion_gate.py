import copy
import unittest

from modules.agent_console.package_completion_gate import assess_package_completion


def complete_package(slide_count=5):
    return {
        "candidate": {"candidate_id": "C-1", "account": "C"},
        "evidence": {"sources": ["https://example.test/source"]},
        "story": {"summary": "확인된 자료를 바탕으로 이어지는 이야기"},
        "slide_count": slide_count,
        "slides": [
            {"page": page, "headline": f"제목 {page}", "body": f"본문 {page}"}
            for page in range(1, slide_count + 1)
        ],
        "feed_caption": "슬라이드 밖에서 읽는 별도 피드 본문",
        "media_plan": [
            {
                "page": page,
                "slide_role": "cover" if page == 1 else "story",
                "media_type": "video" if page == 3 else "image",
            }
            for page in range(1, slide_count + 1)
        ],
    }


class AgentConsolePackageCompletionGateTests(unittest.TestCase):
    def test_accepts_complete_variable_hybrid_package_without_execution(self):
        package = complete_package(6)
        original = copy.deepcopy(package)

        receipt = assess_package_completion(package)

        self.assertEqual(package, original)
        self.assertTrue(receipt["package_complete"])
        self.assertEqual(receipt["status"], "complete")
        self.assertEqual(receipt["missing_field_receipts"], [])
        self.assertTrue(all(value is False for value in receipt["execution"].values()))

    def test_reports_all_missing_requirements_in_one_receipt(self):
        package = complete_package(3)
        package["candidate"] = {"candidate_id": "", "account": "X"}
        package["story"] = {}
        package["evidence"] = {"sources": []}
        package["slides"][1]["body"] = ""
        package["feed_caption"] = ""
        package["media_plan"] = package["media_plan"][:1]

        receipt = assess_package_completion(package)
        reasons = {item["reason_code"] for item in receipt["missing_field_receipts"]}

        self.assertFalse(receipt["package_complete"])
        self.assertEqual(receipt["status"], "blocked")
        self.assertTrue(all(value is False for value in receipt["checks"].values()))
        self.assertTrue(
            {
                "candidate_id_missing",
                "account_missing_or_unsupported",
                "source_backed_story_missing",
                "story_sources_missing",
                "slide_body_missing",
                "feed_caption_missing",
                "media_plan_incomplete",
            }.issubset(reasons)
        )
        self.assertTrue(all(value is False for value in receipt["execution"].values()))

    def test_rejects_duplicate_pages_and_declared_count_mismatch(self):
        package = complete_package(4)
        package["slides"][3]["page"] = 3
        package["media_plan"][3]["page"] = 3

        receipt = assess_package_completion(package)
        reasons = {item["reason_code"] for item in receipt["missing_field_receipts"]}

        self.assertIn("slide_pages_invalid", reasons)
        self.assertIn("slide_count_mismatch", reasons)
        self.assertIn("media_pages_invalid", reasons)
        self.assertFalse(receipt["package_complete"])

    def test_unwraps_explicit_agent_console_handoff_package_only(self):
        receipt = assess_package_completion(
            {"handoff": {"outputs": {"production_package": complete_package(2)}}}
        )
        self.assertTrue(receipt["package_complete"])
        self.assertEqual(receipt["candidate_id"], "C-1")

    def test_non_object_result_fails_closed(self):
        receipt = assess_package_completion(None)
        self.assertEqual(receipt["missing_fields"], ["package"])
        self.assertFalse(receipt["package_complete"])

    def test_accepts_structured_source_receipt_with_url(self):
        package = complete_package(3)
        package["evidence"]["sources"] = [
            {"url": "https://example.test/source", "publisher": "공식 원문"}
        ]
        receipt = assess_package_completion(package)
        self.assertTrue(receipt["package_complete"])


if __name__ == "__main__":
    unittest.main()
