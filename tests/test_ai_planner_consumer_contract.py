import unittest

from modules.ai_planner.consumer_contract import (
    MIN_CONFIDENCE_FOR_HINT_APPLICATION,
    PlannerConsumerContract,
)


def _valid_result(**overrides):
    base = {
        "status": "planner_decided",
        "schema_valid": True,
        "selected_pattern": "tutorial",
        "planner_confidence": MIN_CONFIDENCE_FOR_HINT_APPLICATION,
    }
    base.update(overrides)
    return base


class TestPlannerConsumerContract(unittest.TestCase):
    """
    PlannerConsumerContract에 대한 순수 로컬 단위 테스트. 외부 API/LLM/네트워크를
    전혀 사용하지 않는다 - 전부 dict 입력에 대한 결정론적 규칙 판정만 검증한다.
    """

    # ---- is_result_valid ----

    def test_is_result_valid_true_for_decided_and_schema_valid(self):
        self.assertTrue(PlannerConsumerContract.is_result_valid(_valid_result()))

    def test_is_result_valid_false_when_schema_invalid(self):
        self.assertFalse(PlannerConsumerContract.is_result_valid(_valid_result(schema_valid=False)))

    def test_is_result_valid_false_when_not_decided(self):
        self.assertFalse(PlannerConsumerContract.is_result_valid(_valid_result(status="planner_not_decided")))

    def test_is_result_valid_false_for_non_dict(self):
        for garbage in [None, "not a dict", 123, ["a", "b"]]:
            self.assertFalse(PlannerConsumerContract.is_result_valid(garbage))

    # ---- meets_confidence_threshold ----

    def test_meets_confidence_threshold_true_at_or_above_default(self):
        self.assertTrue(
            PlannerConsumerContract.meets_confidence_threshold(
                _valid_result(planner_confidence=MIN_CONFIDENCE_FOR_HINT_APPLICATION)
            )
        )
        self.assertTrue(
            PlannerConsumerContract.meets_confidence_threshold(_valid_result(planner_confidence=0.9))
        )

    def test_meets_confidence_threshold_false_below_default(self):
        self.assertFalse(
            PlannerConsumerContract.meets_confidence_threshold(_valid_result(planner_confidence=0.1))
        )

    def test_meets_confidence_threshold_respects_custom_threshold(self):
        result = _valid_result(planner_confidence=0.6)
        self.assertTrue(PlannerConsumerContract.meets_confidence_threshold(result, threshold=0.5))
        self.assertFalse(PlannerConsumerContract.meets_confidence_threshold(result, threshold=0.7))

    def test_meets_confidence_threshold_false_for_non_numeric(self):
        self.assertFalse(
            PlannerConsumerContract.meets_confidence_threshold(_valid_result(planner_confidence="not_a_number"))
        )

    def test_meets_confidence_threshold_false_for_non_dict(self):
        self.assertFalse(PlannerConsumerContract.meets_confidence_threshold(None))

    # ---- is_value_supported ----

    def test_is_value_supported_true_for_member(self):
        self.assertTrue(PlannerConsumerContract.is_value_supported("tutorial", ["tutorial", "warning"]))

    def test_is_value_supported_false_for_non_member(self):
        self.assertFalse(PlannerConsumerContract.is_value_supported("not_a_real_pattern", ["tutorial", "warning"]))

    def test_is_value_supported_false_for_empty_or_non_string(self):
        for garbage in [None, "", 123, ["tutorial"]]:
            self.assertFalse(PlannerConsumerContract.is_value_supported(garbage, ["tutorial"]))

    # ---- should_apply_hint (scalar fields) ----

    def test_should_apply_hint_true_when_all_gates_pass(self):
        applied, reason = PlannerConsumerContract.should_apply_hint(
            planner_result=_valid_result(selected_pattern="tutorial", planner_confidence=0.8),
            field="selected_pattern",
            supported_values=["tutorial", "warning", "resource"],
            safety_conflict=False,
        )
        self.assertTrue(applied)
        self.assertIn("tutorial", reason)

    def test_should_apply_hint_false_when_result_invalid(self):
        applied, reason = PlannerConsumerContract.should_apply_hint(
            planner_result=_valid_result(status="planner_not_decided"),
            field="selected_pattern",
            supported_values=["tutorial"],
            safety_conflict=False,
        )
        self.assertFalse(applied)
        self.assertTrue(reason)

    def test_should_apply_hint_false_when_confidence_too_low(self):
        applied, reason = PlannerConsumerContract.should_apply_hint(
            planner_result=_valid_result(planner_confidence=0.1),
            field="selected_pattern",
            supported_values=["tutorial"],
            safety_conflict=False,
        )
        self.assertFalse(applied)

    def test_should_apply_hint_false_when_value_unsupported(self):
        applied, reason = PlannerConsumerContract.should_apply_hint(
            planner_result=_valid_result(selected_pattern="not_a_real_pattern", planner_confidence=0.9),
            field="selected_pattern",
            supported_values=["tutorial", "warning"],
            safety_conflict=False,
        )
        self.assertFalse(applied)

    def test_should_apply_hint_false_when_safety_conflict(self):
        applied, reason = PlannerConsumerContract.should_apply_hint(
            planner_result=_valid_result(selected_pattern="tutorial", planner_confidence=0.9),
            field="selected_pattern",
            supported_values=["tutorial"],
            safety_conflict=True,
        )
        self.assertFalse(applied)
        self.assertIn("안전", reason)

    def test_should_apply_hint_never_raises_on_garbage(self):
        for garbage in [None, "not a dict", 123, {"planner_confidence": object()}]:
            try:
                applied, reason = PlannerConsumerContract.should_apply_hint(
                    planner_result=garbage,
                    field="selected_pattern",
                    supported_values=["tutorial"],
                    safety_conflict=False,
                )
            except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
                self.fail(f"should_apply_hint raised for {garbage!r}: {error}")

            self.assertFalse(applied)
            self.assertIsInstance(reason, str)

    # ---- should_apply_list_hint (list fields) ----

    def test_should_apply_list_hint_true_with_valid_items(self):
        applied, reason, items = PlannerConsumerContract.should_apply_list_hint(
            planner_result=_valid_result(knowledge_priority=["hook", "cta"], planner_confidence=0.8),
            field="knowledge_priority",
            item_validator=lambda item: item in ("hook", "cta", "pattern"),
        )
        self.assertTrue(applied)
        self.assertEqual(items, ["hook", "cta"])

    def test_should_apply_list_hint_false_when_list_empty(self):
        applied, reason, items = PlannerConsumerContract.should_apply_list_hint(
            planner_result=_valid_result(knowledge_priority=[], planner_confidence=0.8),
            field="knowledge_priority",
            item_validator=lambda item: True,
        )
        self.assertFalse(applied)
        self.assertEqual(items, [])

    def test_should_apply_list_hint_filters_invalid_items(self):
        applied, reason, items = PlannerConsumerContract.should_apply_list_hint(
            planner_result=_valid_result(
                knowledge_priority=["hook", "not_a_real_type"], planner_confidence=0.8
            ),
            field="knowledge_priority",
            item_validator=lambda item: item in ("hook", "cta"),
        )
        self.assertTrue(applied)
        self.assertEqual(items, ["hook"])

    def test_should_apply_list_hint_false_when_all_items_invalid(self):
        applied, reason, items = PlannerConsumerContract.should_apply_list_hint(
            planner_result=_valid_result(knowledge_priority=["garbage"], planner_confidence=0.8),
            field="knowledge_priority",
            item_validator=lambda item: item in ("hook", "cta"),
        )
        self.assertFalse(applied)
        self.assertEqual(items, [])

    def test_should_apply_list_hint_never_raises_on_garbage(self):
        for garbage in [None, "not a dict", 123]:
            try:
                applied, reason, items = PlannerConsumerContract.should_apply_list_hint(
                    planner_result=garbage,
                    field="knowledge_priority",
                    item_validator=lambda item: True,
                )
            except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
                self.fail(f"should_apply_list_hint raised for {garbage!r}: {error}")

            self.assertFalse(applied)
            self.assertEqual(items, [])

    # ---- describe ----

    def test_describe_exposes_consumption_gates(self):
        described = PlannerConsumerContract.describe()
        self.assertIn("min_confidence_for_hint_application", described)
        self.assertIn("consumption_gates", described)
        self.assertEqual(len(described["consumption_gates"]), 4)


if __name__ == "__main__":
    unittest.main()
