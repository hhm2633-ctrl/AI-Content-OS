import unittest

from modules.content.content_output_validator import ContentOutputValidator


def make_valid_result():
    return {
        "title": "카드뉴스 제목",
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


class TestContentOutputValidator(unittest.TestCase):
    """
    ContentOutputValidator에 대한 순수 로컬 단위 테스트.

    외부 API/LLM/네트워크를 전혀 사용하지 않는다 - 순수하게 dict 입력을 만들어
    validate()의 출력만 검증한다.
    """

    def setUp(self):
        self.validator = ContentOutputValidator()

    # ---- 정상 케이스 ----

    def test_valid_four_slide_result_passes(self):
        result = self.validator.validate(make_valid_result())
        self.assertTrue(result["valid"])
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["slide_issues"], {})

    # ---- slides 누락/타입 오류 ----

    def test_missing_slides_key_detected(self):
        data = make_valid_result()
        del data["slides"]
        result = self.validator.validate(data)
        self.assertFalse(result["valid"])
        self.assertIn("slides_not_list", result["issues"])

    def test_slides_not_a_list_detected(self):
        data = make_valid_result()
        data["slides"] = "not a list"
        result = self.validator.validate(data)
        self.assertFalse(result["valid"])
        self.assertIn("slides_not_list", result["issues"])

    def test_slide_count_mismatch_detected(self):
        data = make_valid_result()
        data["slides"] = data["slides"][:2]
        result = self.validator.validate(data)
        self.assertFalse(result["valid"])
        self.assertIn("slide_count_mismatch:2", result["issues"])

    # ---- page 번호 문제 ----

    def test_wrong_page_order_detected(self):
        data = make_valid_result()
        # 중복은 없지만 위치와 맞지 않는 순서(4,3,2,1)로 뒤집는다.
        for index, slide in enumerate(data["slides"]):
            slide["page"] = 4 - index
        result = self.validator.validate(data)
        self.assertFalse(result["valid"])
        all_issues = [issue for issues in result["slide_issues"].values() for issue in issues]
        self.assertIn("page_out_of_order", all_issues)

    def test_duplicate_page_detected(self):
        data = make_valid_result()
        data["slides"][1]["page"] = 1
        result = self.validator.validate(data)
        self.assertFalse(result["valid"])
        all_issues = [issue for issues in result["slide_issues"].values() for issue in issues]
        self.assertIn("page_duplicate", all_issues)

    def test_missing_page_detected(self):
        data = make_valid_result()
        del data["slides"][0]["page"]
        result = self.validator.validate(data)
        self.assertFalse(result["valid"])
        self.assertIn("page_missing_or_invalid", result["slide_issues"]["0"])

    # ---- role 순서 문제 ----

    def test_wrong_role_order_detected(self):
        data = make_valid_result()
        data["slides"][0]["role"], data["slides"][3]["role"] = "cta", "hook"
        result = self.validator.validate(data)
        self.assertFalse(result["valid"])
        self.assertIn("hook_not_first", result["issues"])
        self.assertIn("cta_not_last", result["issues"])

    def test_role_order_mismatch_when_middle_slides_swapped(self):
        data = make_valid_result()
        # hook/cta 위치는 맞지만 problem/solution이 뒤바뀐 경우.
        data["slides"][1]["role"], data["slides"][2]["role"] = "solution", "problem"
        result = self.validator.validate(data)
        self.assertFalse(result["valid"])
        self.assertIn("role_order_mismatch", result["issues"])

    def test_unrecognized_role_detected(self):
        data = make_valid_result()
        data["slides"][1]["role"] = "intro"
        result = self.validator.validate(data)
        self.assertFalse(result["valid"])
        self.assertIn("role_unrecognized", result["slide_issues"]["1"])

    # ---- headline/body 누락 ----

    def test_missing_headline_detected(self):
        data = make_valid_result()
        data["slides"][0]["headline"] = ""
        result = self.validator.validate(data)
        self.assertFalse(result["valid"])
        self.assertIn("headline_missing", result["slide_issues"]["0"])

    def test_missing_body_detected(self):
        data = make_valid_result()
        data["slides"][2]["body"] = ""
        result = self.validator.validate(data)
        self.assertFalse(result["valid"])
        self.assertIn("body_missing", result["slide_issues"]["2"])

    def test_headline_too_long_detected(self):
        data = make_valid_result()
        data["slides"][0]["headline"] = "가" * 41
        result = self.validator.validate(data)
        self.assertFalse(result["valid"])
        self.assertIn("headline_too_long", result["slide_issues"]["0"])

    # ---- caption/hashtags 타입 오류 ----

    def test_caption_type_error_detected(self):
        data = make_valid_result()
        data["caption"] = 12345
        result = self.validator.validate(data)
        self.assertFalse(result["valid"])
        self.assertIn("caption_invalid", result["issues"])

    def test_hashtags_type_error_detected(self):
        data = make_valid_result()
        data["hashtags"] = "not a list"
        result = self.validator.validate(data)
        self.assertFalse(result["valid"])
        self.assertIn("hashtags_invalid", result["issues"])

    def test_hashtags_empty_list_detected(self):
        data = make_valid_result()
        data["hashtags"] = []
        result = self.validator.validate(data)
        self.assertFalse(result["valid"])
        self.assertIn("hashtags_invalid", result["issues"])

    # ---- 안전성 ----

    def test_result_not_a_dict_detected(self):
        result = self.validator.validate(None)
        self.assertFalse(result["valid"])
        self.assertIn("result_not_dict", result["issues"])

    def test_validator_never_raises_on_garbage_input(self):
        for garbage in [None, 123, ["a", "b"], "just text", {}, object()]:
            try:
                result = self.validator.validate(garbage)
            except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
                self.fail(f"validate() raised an exception for {garbage!r}: {error}")
            self.assertIn("valid", result)
            self.assertIn("issues", result)
            self.assertIn("slide_issues", result)


if __name__ == "__main__":
    unittest.main()
