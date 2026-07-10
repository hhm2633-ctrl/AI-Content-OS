import unittest

from modules.ai_planner.planning_result_schema import (
    PLANNER_VERSION,
    REQUIRED_FIELDS,
    TARGET_ENGINE_BY_FIELD,
    build_undecided_result,
    validate_schema,
)


class TestPlanningResultSchema(unittest.TestCase):
    """
    planning_result_schema에 대한 순수 로컬 단위 테스트. 외부 API/LLM/네트워크를
    전혀 사용하지 않는다.
    """

    # ---- 요구사항 6: build_undecided_result가 가짜 판단값을 생성하지 않음 ----

    def test_build_undecided_result_has_no_fabricated_values(self):
        result = build_undecided_result(reason="test reason")

        self.assertIsNone(result["selected_pattern"])
        self.assertIsNone(result["selected_hook_strategy"])
        self.assertIsNone(result["selected_cta_strategy"])
        self.assertIsNone(result["selected_image_strategy"])
        self.assertIsNone(result["content_strategy"])
        self.assertEqual(result["knowledge_priority"], [])
        self.assertEqual(result["competitor_reference"], [])
        self.assertEqual(result["planner_confidence"], 0.0)
        self.assertEqual(result["planner_reason"], "test reason")
        self.assertEqual(result["planner_version"], PLANNER_VERSION)
        self.assertEqual(result["status"], "planner_not_decided")

    def test_build_undecided_result_contains_every_required_field(self):
        result = build_undecided_result(reason="test reason")

        for field in REQUIRED_FIELDS:
            self.assertIn(field, result)

    def test_build_undecided_result_never_raises(self):
        for reason in ["", None, 12345, {"nested": "reason"}]:
            try:
                result = build_undecided_result(reason=reason)
            except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
                self.fail(f"build_undecided_result() raised for reason={reason!r}: {error}")

            self.assertIsNone(result["selected_pattern"])

    # ---- 요구사항 7: validate_schema가 필수 Output 누락을 감지 ----

    def test_validate_schema_passes_for_complete_result(self):
        result = build_undecided_result(reason="test reason")
        check = validate_schema(result)

        self.assertTrue(check["valid"])
        self.assertEqual(check["missing_fields"], [])

    def test_validate_schema_detects_each_missing_field(self):
        base = build_undecided_result(reason="test reason")

        for field in REQUIRED_FIELDS:
            incomplete = dict(base)
            del incomplete[field]

            check = validate_schema(incomplete)

            self.assertFalse(check["valid"], f"missing {field} should make schema invalid")
            self.assertIn(field, check["missing_fields"])

    def test_validate_schema_never_raises_on_garbage_input(self):
        for garbage in [None, 123, ["a", "b"], "just a string", object(), {}]:
            try:
                check = validate_schema(garbage)
            except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
                self.fail(f"validate_schema() raised for {garbage!r}: {error}")

            self.assertIn("valid", check)
            self.assertIn("missing_fields", check)

    # ---- Output Contract: 하위 Engine 전달 가능성 매핑 ----

    def test_target_engine_mapping_covers_selectable_fields(self):
        selectable_fields = [
            "selected_pattern",
            "selected_hook_strategy",
            "selected_cta_strategy",
            "selected_image_strategy",
            "knowledge_priority",
            "competitor_reference",
            "content_strategy",
        ]

        for field in selectable_fields:
            self.assertIn(field, TARGET_ENGINE_BY_FIELD)
            self.assertTrue(TARGET_ENGINE_BY_FIELD[field])

        # Planner 자신의 메타데이터 필드는 특정 하위 Engine에 매핑되지 않는다.
        for meta_field in ("planner_confidence", "planner_reason", "planner_version"):
            self.assertNotIn(meta_field, TARGET_ENGINE_BY_FIELD)


if __name__ == "__main__":
    unittest.main()
