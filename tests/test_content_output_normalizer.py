import unittest

from modules.content.content_output_normalizer import ContentOutputNormalizer


def fallback_slides(keyword):
    return [
        {"page": 1, "role": "hook", "headline": "폴백 후킹 문구", "body": "폴백 후킹 본문 충분히 깁니다 정말로"},
        {"page": 2, "role": "problem", "headline": "폴백 문제 문구", "body": "폴백 문제 본문 충분히 깁니다 정말로"},
        {"page": 3, "role": "solution", "headline": "폴백 해결 문구", "body": "폴백 해결 본문 충분히 깁니다 정말로"},
        {"page": 4, "role": "cta", "headline": "폴백 CTA 문구", "body": "폴백 CTA 본문 충분히 깁니다 정말로"},
    ]


def make_valid_result():
    return {
        "title": "정상 카드뉴스 제목",
        "slides": [
            {"page": 1, "role": "hook", "headline": "강한 후킹 문구", "body": "충분히 긴 후킹 본문 내용입니다"},
            {"page": 2, "role": "problem", "headline": "문제 설명 문구", "body": "충분히 긴 문제 설명 본문입니다"},
            {"page": 3, "role": "solution", "headline": "해결책 제시 문구", "body": "충분히 긴 해결책 설명 본문입니다"},
            {"page": 4, "role": "cta", "headline": "저장하고 팔로우", "body": "충분히 긴 CTA 유도 본문입니다"},
        ],
        "caption": "정상적인 인스타그램 캡션 본문입니다",
        "hashtags": ["#AI", "#콘텐츠", "#자동화"],
        "status": "content_created",
    }


class TestContentOutputNormalizer(unittest.TestCase):
    """
    ContentOutputNormalizer에 대한 순수 로컬 단위 테스트.

    외부 API/LLM/네트워크를 전혀 사용하지 않는다 - fallback_slides()는 이 테스트
    파일 안에서만 쓰이는 순수 로컬 함수이며 ContentModule._fallback_slides()와
    동일한 역할(호출 시그니처)을 흉내낸다.
    """

    def setUp(self):
        self.normalizer = ContentOutputNormalizer()

    def _assert_stable_schema(self, result):
        self.assertEqual(len(result["slides"]), 4)
        self.assertEqual(
            [slide["role"] for slide in result["slides"]],
            ["hook", "problem", "solution", "cta"],
        )
        self.assertEqual([slide["page"] for slide in result["slides"]], [1, 2, 3, 4])

        for slide in result["slides"]:
            self.assertTrue(slide["headline"])
            self.assertTrue(slide["body"])
            self.assertLessEqual(len(slide["headline"]), ContentOutputNormalizer.MAX_HEADLINE_LENGTH)
            self.assertLessEqual(len(slide["body"]), ContentOutputNormalizer.MAX_BODY_LENGTH)

        self.assertIsInstance(result["title"], str)
        self.assertTrue(result["title"])
        self.assertIsInstance(result["caption"], str)
        self.assertTrue(result["caption"])
        self.assertIsInstance(result["hashtags"], list)
        self.assertTrue(all(isinstance(tag, str) and tag for tag in result["hashtags"]))
        self.assertEqual(result["status"], "content_created")
        self.assertIn("output_normalization", result)

    # ---- slides 구조 복구 ----

    def test_missing_slides_key_is_recovered(self):
        data = {"title": "t", "caption": "c", "hashtags": ["#a", "#b", "#c"]}
        result = self.normalizer.normalize(data, "테스트키워드", fallback_slides)
        self._assert_stable_schema(result)
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["fallback_reason"], "no_usable_llm_slide_content")

    def test_slides_as_dict_is_recovered(self):
        data = {
            "title": "t",
            "slides": {"page": 1, "role": "hook", "headline": "x", "body": "y"},
            "caption": "c",
            "hashtags": ["#a", "#b", "#c"],
        }
        result = self.normalizer.normalize(data, "테스트키워드", fallback_slides)
        self._assert_stable_schema(result)

    def test_two_slides_recovered_to_four(self):
        data = {
            "title": "t",
            "slides": [
                {"page": 1, "role": "hook", "headline": "진짜 후킹 문구", "body": "진짜 후킹 본문입니다 충분히 길게"},
                {"page": 2, "role": "cta", "headline": "진짜 CTA 문구", "body": "진짜 CTA 본문입니다 충분히 길게"},
            ],
            "caption": "c",
            "hashtags": ["#a", "#b", "#c"],
        }
        result = self.normalizer.normalize(data, "테스트키워드", fallback_slides)
        self._assert_stable_schema(result)
        self.assertEqual(result["slides"][0]["headline"], "진짜 후킹 문구")
        self.assertEqual(result["slides"][3]["headline"], "진짜 CTA 문구")
        self.assertFalse(result["fallback_used"])  # 실제 콘텐츠 2장을 보존했으므로 fallback이 아님

    # ---- page 정규화 ----

    def test_pages_normalized_to_1_through_4(self):
        data = make_valid_result()
        for slide in data["slides"]:
            slide["page"] = 99
        result = self.normalizer.normalize(data, "테스트키워드", fallback_slides)
        self.assertEqual([slide["page"] for slide in result["slides"]], [1, 2, 3, 4])

    # ---- role 정규화 (핵심 시나리오: role 뒤섞임) ----

    def test_roles_normalized_by_role_field_not_position(self):
        data = {
            "title": "t",
            "slides": [
                {"page": 1, "role": "cta", "headline": "CTA 문구입니다", "body": "CTA 본문 충분히 깁니다 정말로"},
                {"page": 2, "role": "solution", "headline": "해결 문구입니다", "body": "해결 본문 충분히 깁니다 정말로"},
                {"page": 3, "role": "problem", "headline": "문제 문구입니다", "body": "문제 본문 충분히 깁니다 정말로"},
                {"page": 4, "role": "hook", "headline": "후킹 문구입니다", "body": "후킹 본문 충분히 깁니다 정말로"},
            ],
            "caption": "c",
            "hashtags": ["#a", "#b", "#c"],
        }
        result = self.normalizer.normalize(data, "테스트키워드", fallback_slides)

        self.assertEqual(
            [slide["role"] for slide in result["slides"]],
            ["hook", "problem", "solution", "cta"],
        )
        # 리스트상의 위치가 아니라 role 필드를 기준으로 재배치되어야 한다.
        self.assertEqual(result["slides"][0]["headline"], "후킹 문구입니다")
        self.assertEqual(result["slides"][1]["headline"], "문제 문구입니다")
        self.assertEqual(result["slides"][2]["headline"], "해결 문구입니다")
        self.assertEqual(result["slides"][3]["headline"], "CTA 문구입니다")
        self.assertFalse(result["fallback_used"])

    # ---- headline/body 복구 ----

    def test_missing_headline_and_body_recovered(self):
        data = make_valid_result()
        data["slides"][1]["headline"] = ""
        data["slides"][1]["body"] = ""
        result = self.normalizer.normalize(data, "테스트키워드", fallback_slides)
        self._assert_stable_schema(result)
        self.assertTrue(result["slides"][1]["headline"])
        self.assertTrue(result["slides"][1]["body"])

    def test_headline_too_long_is_trimmed(self):
        data = make_valid_result()
        data["slides"][0]["headline"] = "가" * 80
        result = self.normalizer.normalize(data, "테스트키워드", fallback_slides)
        self.assertLessEqual(len(result["slides"][0]["headline"]), ContentOutputNormalizer.MAX_HEADLINE_LENGTH)

    # ---- hashtags 정규화 ----

    def test_hashtags_string_normalized_to_list(self):
        data = make_valid_result()
        data["hashtags"] = "#AI #콘텐츠 #자동화"
        result = self.normalizer.normalize(data, "테스트키워드", fallback_slides)
        self.assertIsInstance(result["hashtags"], list)
        self.assertIn("#AI", result["hashtags"])
        self.assertIn("#콘텐츠", result["hashtags"])
        self.assertIn("#자동화", result["hashtags"])

    def test_hashtags_comma_separated_string_normalized_to_list(self):
        data = make_valid_result()
        data["hashtags"] = "#AI,#콘텐츠,#자동화"
        result = self.normalizer.normalize(data, "테스트키워드", fallback_slides)
        self.assertIsInstance(result["hashtags"], list)
        self.assertIn("#AI", result["hashtags"])
        self.assertIn("#콘텐츠", result["hashtags"])
        self.assertIn("#자동화", result["hashtags"])

    def test_too_few_hashtags_padded(self):
        data = make_valid_result()
        data["hashtags"] = ["#one"]
        result = self.normalizer.normalize(data, "테스트키워드", fallback_slides)
        self.assertGreaterEqual(len(result["hashtags"]), ContentOutputNormalizer.MIN_HASHTAG_COUNT)
        self.assertIn("#one", result["hashtags"])

    # ---- 완전 안전성 ----

    def test_completely_invalid_input_returns_safe_result_without_raising(self):
        for garbage in [None, 12345, ["a", "b", "c"], "just a plain string", {}, object()]:
            try:
                result = self.normalizer.normalize(garbage, "테스트키워드", fallback_slides)
            except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
                self.fail(f"normalize() raised an exception for {garbage!r}: {error}")
            self._assert_stable_schema(result)

    # ---- 불필요한 변경 금지 ----

    def test_valid_result_is_not_unnecessarily_modified(self):
        data = make_valid_result()
        result = self.normalizer.normalize(data, "테스트키워드", fallback_slides)

        self.assertFalse(result["output_normalization"]["normalization_applied"])
        self.assertEqual(result["output_normalization"]["notes"], [])
        self.assertEqual(result["title"], data["title"])
        self.assertEqual(result["caption"], data["caption"])
        self.assertFalse(result["fallback_used"])

        for original_slide, normalized_slide in zip(data["slides"], result["slides"]):
            self.assertEqual(original_slide["headline"], normalized_slide["headline"])
            self.assertEqual(original_slide["body"], normalized_slide["body"])
            self.assertEqual(original_slide["role"], normalized_slide["role"])


if __name__ == "__main__":
    unittest.main()
