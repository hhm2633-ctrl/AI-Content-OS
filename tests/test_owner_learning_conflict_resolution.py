import unittest

from modules.agent_console.owner_feedback_learning import (
    build_owner_learning_index,
    classify_feedback_event,
)


def event(event_id, reason, *, category="multi_account", applies_to=None, sequence=0):
    return classify_feedback_event(
        {
            "event_id": event_id,
            "recorded_at": f"2026-07-23T00:00:{sequence:02d}+09:00",
            "source": "human_owner_chat",
            "feedback_type": "owner_review_correction",
            "category": category,
            "title": reason,
            "owner_decision": reason,
            "owner_reason": reason,
            "applies_to": applies_to or ["fashion", "beauty", "account_c"],
            "is_performance_evidence": False,
            "consumption_status": "ACTIVE",
            "owner_rule_activation": "EXPLICIT",
        },
        sequence=sequence,
    )


class OwnerLearningConflictResolutionTest(unittest.TestCase):
    def test_multi_account_explicit_categories_do_not_expand_to_every_account(self):
        record = event(
            "beauty-rule",
            "패션과 뷰티 아이템 소개 규칙",
            applies_to=["fashion", "beauty", "account_c"],
        )

        self.assertEqual(record["categories"], ["fashion", "beauty"])

    def test_newer_variable_slide_rule_supersedes_fixed_count_rule(self):
        fixed = {
            "event_id": "fixed",
            "recorded_at": "2026-07-23T00:00:01+09:00",
            "source": "human_owner_chat",
            "feedback_type": "owner_review_correction",
            "category": "story",
            "title": "고정 장수",
            "owner_decision": "항상 4장으로 고정한다",
            "owner_reason": "항상 4장으로 고정한다",
            "applies_to": ["story"],
            "is_performance_evidence": False,
            "consumption_status": "ACTIVE",
            "owner_rule_activation": "EXPLICIT",
        }
        variable = {
            **fixed,
            "event_id": "variable",
            "recorded_at": "2026-07-23T00:00:02+09:00",
            "title": "가변 장수",
            "owner_decision": "근거량에 따라 가변으로 한다",
            "owner_reason": "근거량에 따라 가변으로 하고 고정하지 않는다",
        }

        result = build_owner_learning_index([fixed, variable])
        by_id = {item["learning_id"]: item for item in result["records"]}

        self.assertFalse(by_id["fixed"]["active"])
        self.assertEqual(by_id["fixed"]["stage"], "SUPERSEDED_CONFLICT")
        self.assertTrue(by_id["variable"]["active"])
        self.assertEqual(result["stats"]["conflict_resolved_count"], 1)


if __name__ == "__main__":
    unittest.main()
