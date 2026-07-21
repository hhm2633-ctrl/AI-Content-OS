import copy
import unittest

from modules.card_news.package_content_quality_gate import assess_package_content_quality


def package(account="A"):
    slides = [
        {"page": 1, "role": "cover", "headline": "오늘 달라진 한 장면", "body": "공개된 원문에서 핵심 상황을 짚었습니다."},
        {"page": 2, "role": "context", "headline": "무슨 일이 있었나", "body": "확인된 내용을 짧고 자연스럽게 이어갑니다."},
        {"page": 3, "role": "meaning", "headline": "지금 볼 지점", "body": "앞선 장면과 다른 정보를 더해 마무리합니다."},
    ]
    return {
        "candidate": {"candidate_id": f"{account}-1", "account": account},
        "evidence": {"sources": ["https://example.test/source"]},
        "story": {"summary": "확인된 원문을 바탕으로 세 장면이 이어진다."},
        "slide_count": 3,
        "slides": slides,
        "feed_caption": "공개된 원문에서 확인된 내용을 카드 밖에서도 자연스럽게 읽히도록 두 문장으로 정리했습니다. 자세한 맥락은 각 장에서 확인할 수 있습니다.",
        "media_plan": [
            {"page": i, "slide_role": row["role"], "media_type": "editorial", "source_credit": ["https://example.test/source"], "asset_status": "original_editorial_graphic"}
            for i, row in enumerate(slides, start=1)
        ],
    }


class PackageContentQualityGateTests(unittest.TestCase):
    def test_passes_complete_account_specific_package_without_execution(self):
        value = package("A")
        original = copy.deepcopy(value)
        result = assess_package_content_quality(value)
        self.assertTrue(result["quality_passed"])
        self.assertEqual(value, original)
        self.assertTrue(all(flag is False for flag in result["execution"].values()))

    def test_reports_dense_copy_jargon_and_media_provenance(self):
        value = package("C")
        value["slides"][0]["headline"] = "세탁 회전이라는 내부 기획 용어를 그대로 내보낸 아주 긴 제목"
        value["media_plan"][0]["source_credit"] = []
        value["media_plan"][0]["asset_status"] = "unknown"
        result = assess_package_content_quality(value)
        reasons = {item["reason_code"] for item in result["failures"]}
        self.assertIn("internal_jargon_in_public_copy", reasons)
        self.assertIn("media_source_credit_missing", reasons)
        self.assertIn("media_asset_status_unapproved", reasons)
        self.assertFalse(result["quality_passed"])

    def test_account_b_requires_visible_progression(self):
        value = package("B")
        for slide in value["slides"]:
            slide["role"] = "story"
        for media in value["media_plan"]:
            media["slide_role"] = "story"
        result = assess_package_content_quality(value)
        self.assertIn("emotional_progression_not_visible", {item["reason_code"] for item in result["failures"]})

    def test_rejects_unacquired_source_media_dependency(self):
        value = package("A")
        value["media_plan"][0]["asset_status"] = "source_page_observed_not_acquired"

        result = assess_package_content_quality(value)

        self.assertFalse(result["quality_passed"])
        self.assertIn("unresolved_media_dependency", {item["reason_code"] for item in result["failures"]})

    def test_rejects_nested_not_acquired_flag(self):
        value = package("C")
        value["media_plan"][0]["acquisition_status"] = "not_acquired"

        result = assess_package_content_quality(value)

        self.assertFalse(result["quality_passed"])
        self.assertIn("unresolved_media_dependency", {item["reason_code"] for item in result["failures"]})


if __name__ == "__main__":
    unittest.main()
