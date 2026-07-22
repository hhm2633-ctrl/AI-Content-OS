from __future__ import annotations

import copy
import unittest

from modules.agent_console.package_completion_gate import assess_package_completion
from modules.card_news.production_controller import (
    ACCEPT_BATCH_QA,
    ACCEPT_REPRESENTATIVE_QA,
    AUTHORIZE_BATCH,
    AUTHORIZE_REPRESENTATIVES,
    AWAITING_HARD_RULES,
    BATCH_AUTHORIZED,
    BATCH_RENDER_RECORDED,
    BIND_HARD_RULES,
    BLOCKED,
    MANUAL_UPLOAD_READY,
    RECORD_BATCH_RENDER,
    RECORD_REPRESENTATIVE_RENDER,
    REPRESENTATIVE_PENDING,
    REPRESENTATIVE_QA_PASSED,
    REQUIRED_HARD_RULE_IDS,
    ProductionControllerError,
    apply_transition,
    build_transition_receipt,
    canonical_hash,
    initialize_controller,
    recover_fail_closed,
    transition_or_block,
    validate_state,
)


def _package(account: str) -> dict:
    candidate_id = f"candidate-{account.lower()}"
    return {
        "status": "production_package_ready",
        "candidate": {"candidate_id": candidate_id, "account": account},
        "slide_count": 1,
        "story": {"summary": f"source-backed story for {account}"},
        "evidence": {"sources": [{"url": f"https://example.com/{account.lower()}"}]},
        "slides": [
            {"page": 1, "role": "hook", "headline": f"Headline {account}", "body": "Short body"}
        ],
        "feed_caption": f"Separate feed caption for {account}",
        "media_plan": [
            {"page": 1, "slide_role": "hook", "media_type": "editorial"}
        ],
        "gates": {"package_approval": {
            "status": "approved",
            "approved": True,
            "scope": "production_package",
            "approved_by": "owner",
            "receipt_id": f"package-approval-{candidate_id}",
        }},
    }


def _rules() -> list[dict]:
    return [
        {
            "claim_id": claim_id,
            "rule": f"Exact owner hard rule text for {claim_id}",
            "source": "knowledge/owner_directives/cardnews_owner_directives.json",
        }
        for claim_id in REQUIRED_HARD_RULE_IDS
    ]


def _render_receipts(candidate_ids: list[str], state: dict) -> dict[str, dict]:
    authorization_id = f"authorization-{state['sequence']}"
    mode = "representative" if state["state"] == "representative_authorized" else "batch"
    media_binding_hash = canonical_hash({
        candidate_id: state["local_media_receipt_hashes"][candidate_id]
        for candidate_id in candidate_ids
    })
    return {
        candidate_id: {
            "candidate_id": candidate_id,
            "status": "render_completed_pending_visual_qa",
            "expected_slide_count": 1,
            "rendered_slide_count": 1,
            "output_hashes": [canonical_hash({"candidate_id": candidate_id, "slide": 1})],
            "controller_state_hash": state["state_hash"],
            "batch_hash": state["batch_hash"],
            "hard_rule_hash": state["hard_rule_hash"],
            "authorization_id": authorization_id,
            "output_set_id": authorization_id,
            "render_mode": mode,
            "local_media_binding_hash": media_binding_hash,
        }
        for candidate_id in candidate_ids
    }


def _local_media_receipts(candidate_ids: list[str]) -> dict[str, list[dict]]:
    receipts: dict[str, list[dict]] = {}
    for candidate_id in candidate_ids:
        body = {
            "schema_version": "local_media_pre_render_receipt.v1",
            "status": "completed",
            "request_id": f"prepare-{candidate_id}",
            "asset_id": f"asset-{candidate_id}",
            "owner_selected": True,
            "rights_cleared": True,
            "source": {
                "path": f"F:/fixture-assets/{candidate_id}.png",
                "sha256": canonical_hash({"source": candidate_id}),
                "preserved": True,
            },
            "output_root": "F:/AI-Content-OS-Data/external_tools/outputs/local_media_pipeline",
            "operations": [{"operation": "paddleocr", "status": "completed"}],
            "source_modified": False,
            "tools_executed": True,
            "pre_render_prepared": True,
            "implicit_execution": False,
        }
        body["receipt_hash"] = canonical_hash(body)
        receipts[candidate_id] = [body]
    return receipts


def _preserve_original_receipts(candidate_ids: list[str]) -> dict[str, list[dict]]:
    receipts = _local_media_receipts(candidate_ids)
    for rows in receipts.values():
        body = rows[0]
        body["operations"] = [{
            "operation": "preserve_original",
            "status": "completed",
            "result": {
                "status": "completed",
                "source_preserved": True,
                "tool_subprocess_executed": False,
            },
        }]
        body["tools_executed"] = False
        body.pop("receipt_hash")
        body["receipt_hash"] = canonical_hash(body)
    return receipts


def _qa_receipts(
    candidate_ids: list[str],
    output_set_ids: dict[str, str],
    representative_receipt_ids: dict[str, str] | None = None,
) -> dict[str, dict]:
    return {
        candidate_id: {
            "candidate_id": candidate_id,
            "receipt_id": f"visual-{candidate_id}",
            "status": "passed",
            "visual_qa_passed": True,
            "failure_count": 0,
            "reviewer_independent": True,
            "approval_kind": "owner_visual_approval",
            "owner_visual_approval": True,
            "owner_approved_by": "owner",
            "evidence_only": False,
            "expected_slide_count": 1,
            "reviewed_slide_count": 1,
            "output_set_id": output_set_ids[candidate_id],
            "representative_receipt_ids": representative_receipt_ids or {},
        }
        for candidate_id in candidate_ids
    }


class ProductionControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packages = [_package(account) for account in ("A", "B", "C")]
        self.completion = [assess_package_completion(package) for package in self.packages]
        self.state = initialize_controller("daily-2026-07-19", self.packages, self.completion)

    def _bind_rules(self, state: dict | None = None, receipt_id: str = "rules-1") -> dict:
        current = state or self.state
        receipt = build_transition_receipt(
            current,
            BIND_HARD_RULES,
            receipt_id,
            {"hard_rules": _rules()},
        )
        return apply_transition(current, receipt)

    def _authorize_representatives(self, state: dict) -> dict:
        receipt = build_transition_receipt(
            state,
            AUTHORIZE_REPRESENTATIVES,
            "representatives-1",
            {
                "representatives": {
                    "A": "candidate-a",
                    "B": "candidate-b",
                    "C": "candidate-c",
                },
                "local_media_receipts": _local_media_receipts(
                    ["candidate-a", "candidate-b", "candidate-c"]
                ),
            },
        )
        return apply_transition(state, receipt)

    def _representative_qa_passed(self) -> dict:
        state = self._authorize_representatives(self._bind_rules())
        representative_ids = sorted(state["representatives"].values())
        render = build_transition_receipt(
            state,
            RECORD_REPRESENTATIVE_RENDER,
            "representative-render-1",
            {"render_receipts": _render_receipts(representative_ids, state)},
        )
        state = apply_transition(state, render)
        qa = build_transition_receipt(
            state,
            ACCEPT_REPRESENTATIVE_QA,
            "representative-qa-1",
            {"visual_qa_receipts": _qa_receipts(representative_ids, state["representative_output_set_ids"])},
        )
        return apply_transition(state, qa)

    def test_initialization_requires_current_completion_receipts(self) -> None:
        stale = copy.deepcopy(self.completion)
        stale[0]["candidate_id"] = "different"
        with self.assertRaises(ProductionControllerError) as caught:
            initialize_controller("daily", self.packages, stale)
        self.assertEqual(caught.exception.reason_code, "completion_receipt_stale")

    def test_initialization_rejects_unapproved_package(self) -> None:
        pending = copy.deepcopy(self.packages)
        pending[0]["status"] = "production_package_pending_approval"
        completion = [assess_package_completion(package) for package in pending]
        with self.assertRaises(ProductionControllerError) as caught:
            initialize_controller("daily", pending, completion)
        self.assertEqual(caught.exception.reason_code, "production_package_not_ready")

    def test_illegal_transition_is_rejected(self) -> None:
        receipt = build_transition_receipt(
            self.state,
            AUTHORIZE_REPRESENTATIVES,
            "illegal-1",
            {"representatives": {"A": "candidate-a", "B": "candidate-b", "C": "candidate-c"}},
        )
        with self.assertRaises(ProductionControllerError) as caught:
            apply_transition(self.state, receipt)
        self.assertEqual(caught.exception.reason_code, "illegal_transition")

    def test_missing_hard_rule_receipt_is_rejected(self) -> None:
        receipt = build_transition_receipt(self.state, BIND_HARD_RULES, "rules-missing", {})
        with self.assertRaises(ProductionControllerError) as caught:
            apply_transition(self.state, receipt)
        self.assertEqual(caught.exception.reason_code, "hard_rule_receipt_missing")

    def test_hard_rule_evidence_is_tamper_evident(self) -> None:
        state = self._bind_rules()
        tampered = copy.deepcopy(state)
        tampered["hard_rule_evidence"][0]["rule"] = "changed later"
        with self.assertRaises(ProductionControllerError) as caught:
            validate_state(tampered)
        self.assertEqual(caught.exception.reason_code, "controller_state_tampered")

    def test_batch_cannot_be_authorized_before_representative_qa(self) -> None:
        state = self._bind_rules()
        self.assertEqual(state["state"], REPRESENTATIVE_PENDING)
        receipt = build_transition_receipt(
            state,
            AUTHORIZE_BATCH,
            "batch-too-early",
            {"candidate_ids": state["candidate_ids"]},
        )
        with self.assertRaises(ProductionControllerError) as caught:
            apply_transition(state, receipt)
        self.assertEqual(caught.exception.reason_code, "illegal_transition")

    def test_representative_authorization_requires_local_media_receipts(self) -> None:
        state = self._bind_rules()
        receipt = build_transition_receipt(
            state,
            AUTHORIZE_REPRESENTATIVES,
            "representatives-without-media",
            {"representatives": {"A": "candidate-a", "B": "candidate-b", "C": "candidate-c"}},
        )
        with self.assertRaises(ProductionControllerError) as caught:
            apply_transition(state, receipt)
        self.assertEqual(caught.exception.reason_code, "local_media_scope_incomplete")

    def test_stale_local_media_receipt_blocks_representative_authorization(self) -> None:
        state = self._bind_rules()
        local_media = _local_media_receipts(["candidate-a", "candidate-b", "candidate-c"])
        local_media["candidate-a"][0]["output_root"] += "/changed-after-sealing"
        receipt = build_transition_receipt(
            state,
            AUTHORIZE_REPRESENTATIVES,
            "representatives-stale-media",
            {
                "representatives": {"A": "candidate-a", "B": "candidate-b", "C": "candidate-c"},
                "local_media_receipts": local_media,
            },
        )
        with self.assertRaises(ProductionControllerError) as caught:
            apply_transition(state, receipt)
        self.assertEqual(caught.exception.reason_code, "local_media_receipt_stale")

    def test_explicit_preserve_original_receipt_authorizes_without_tool_execution(self) -> None:
        state = self._bind_rules()
        receipt = build_transition_receipt(
            state,
            AUTHORIZE_REPRESENTATIVES,
            "representatives-preserved-originals",
            {
                "representatives": {"A": "candidate-a", "B": "candidate-b", "C": "candidate-c"},
                "local_media_receipts": _preserve_original_receipts(
                    ["candidate-a", "candidate-b", "candidate-c"]
                ),
            },
        )

        authorized = apply_transition(state, receipt)

        self.assertEqual(authorized["state"], "representative_authorized")
        self.assertEqual(set(authorized["local_media_receipt_hashes"]), set(authorized["candidate_ids"]))

    def test_tools_executed_false_is_blocked_outside_narrow_passthrough(self) -> None:
        state = self._bind_rules()
        media = _local_media_receipts(["candidate-a", "candidate-b", "candidate-c"])
        media["candidate-a"][0]["tools_executed"] = False
        media["candidate-a"][0].pop("receipt_hash")
        media["candidate-a"][0]["receipt_hash"] = canonical_hash(media["candidate-a"][0])
        receipt = build_transition_receipt(
            state,
            AUTHORIZE_REPRESENTATIVES,
            "representatives-fake-passthrough",
            {
                "representatives": {"A": "candidate-a", "B": "candidate-b", "C": "candidate-c"},
                "local_media_receipts": media,
            },
        )
        with self.assertRaises(ProductionControllerError) as caught:
            apply_transition(state, receipt)
        self.assertEqual(caught.exception.reason_code, "local_media_safety_gate_failed")

    def test_stale_state_hash_is_rejected(self) -> None:
        state = self._bind_rules()
        receipt = build_transition_receipt(
            state,
            AUTHORIZE_REPRESENTATIVES,
            "stale-1",
            {"representatives": {"A": "candidate-a", "B": "candidate-b", "C": "candidate-c"}},
        )
        receipt["state_hash_before"] = "0" * 64
        with self.assertRaises(ProductionControllerError) as caught:
            apply_transition(state, receipt)
        self.assertEqual(caught.exception.reason_code, "stale_state_hash")

    def test_duplicate_transition_receipt_is_rejected(self) -> None:
        receipt = build_transition_receipt(
            self.state,
            BIND_HARD_RULES,
            "one-use-rules",
            {"hard_rules": _rules()},
        )
        state = apply_transition(self.state, receipt)
        with self.assertRaises(ProductionControllerError) as caught:
            apply_transition(state, receipt)
        self.assertEqual(caught.exception.reason_code, "duplicate_receipt")

    def test_publish_is_always_prohibited(self) -> None:
        receipt = build_transition_receipt(self.state, "publish", "publish-1", {})
        with self.assertRaises(ProductionControllerError) as caught:
            apply_transition(self.state, receipt)
        self.assertEqual(caught.exception.reason_code, "publish_prohibited")

    def test_full_legal_flow_reaches_manual_upload_ready(self) -> None:
        state = self._representative_qa_passed()
        self.assertEqual(state["state"], REPRESENTATIVE_QA_PASSED)
        authorize = build_transition_receipt(
            state,
            AUTHORIZE_BATCH,
            "batch-authorize-1",
            {
                "candidate_ids": state["candidate_ids"],
                "local_media_receipts": _local_media_receipts(state["candidate_ids"]),
            },
        )
        state = apply_transition(state, authorize)
        self.assertEqual(state["state"], BATCH_AUTHORIZED)

        render = build_transition_receipt(
            state,
            RECORD_BATCH_RENDER,
            "batch-render-1",
            {"render_receipts": _render_receipts(state["candidate_ids"], state)},
        )
        state = apply_transition(state, render)
        self.assertEqual(state["state"], BATCH_RENDER_RECORDED)

        qa = build_transition_receipt(
            state,
            ACCEPT_BATCH_QA,
            "batch-qa-1",
            {"visual_qa_receipts": _qa_receipts(
                state["candidate_ids"],
                state["batch_output_set_ids"],
                state["representative_qa_receipt_ids"],
            )},
        )
        state = apply_transition(state, qa)
        self.assertEqual(state["state"], MANUAL_UPLOAD_READY)
        self.assertTrue(state["manual_upload_ready"])
        self.assertEqual(state["sequence"], 7)

    def test_batch_cannot_replace_representative_media_binding(self) -> None:
        state = self._representative_qa_passed()
        changed = _local_media_receipts(state["candidate_ids"])
        changed["candidate-a"][0]["request_id"] = "different-request"
        changed["candidate-a"][0].pop("receipt_hash")
        changed["candidate-a"][0]["receipt_hash"] = canonical_hash(changed["candidate-a"][0])
        receipt = build_transition_receipt(
            state,
            AUTHORIZE_BATCH,
            "batch-rebind-media",
            {"candidate_ids": state["candidate_ids"], "local_media_receipts": changed},
        )
        with self.assertRaises(ProductionControllerError) as caught:
            apply_transition(state, receipt)
        self.assertEqual(caught.exception.reason_code, "local_media_receipt_changed")

    def test_fake_visual_qa_hash_cannot_authorize_batch(self) -> None:
        state = self._authorize_representatives(self._bind_rules())
        representative_ids = sorted(state["representatives"].values())
        render = build_transition_receipt(
            state,
            RECORD_REPRESENTATIVE_RENDER,
            "representative-render-for-fake-qa",
            {"render_receipts": _render_receipts(representative_ids, state)},
        )
        state = apply_transition(state, render)
        qa = _qa_receipts(representative_ids, state["representative_output_set_ids"])
        qa[representative_ids[0]]["reviewer_independent"] = False
        receipt = build_transition_receipt(
            state,
            ACCEPT_REPRESENTATIVE_QA,
            "fake-qa",
            {"visual_qa_receipts": qa},
        )
        with self.assertRaises(ProductionControllerError) as caught:
            apply_transition(state, receipt)
        self.assertEqual(caught.exception.reason_code, "visual_qa_reviewer_not_independent")

    def test_render_receipt_must_bind_current_controller_state(self) -> None:
        state = self._authorize_representatives(self._bind_rules())
        representative_ids = sorted(state["representatives"].values())
        receipts = _render_receipts(representative_ids, state)
        receipts[representative_ids[0]]["controller_state_hash"] = "0" * 64
        receipt = build_transition_receipt(
            state,
            RECORD_REPRESENTATIVE_RENDER,
            "wrong-render-state",
            {"render_receipts": receipts},
        )
        with self.assertRaises(ProductionControllerError) as caught:
            apply_transition(state, receipt)
        self.assertEqual(caught.exception.reason_code, "render_receipt_state_mismatch")

    def test_visual_qa_must_bind_rendered_output_set(self) -> None:
        state = self._authorize_representatives(self._bind_rules())
        representative_ids = sorted(state["representatives"].values())
        render = build_transition_receipt(
            state,
            RECORD_REPRESENTATIVE_RENDER,
            "render-for-output-binding",
            {"render_receipts": _render_receipts(representative_ids, state)},
        )
        state = apply_transition(state, render)
        qa = _qa_receipts(representative_ids, state["representative_output_set_ids"])
        qa[representative_ids[0]]["output_set_id"] = "another-output-set"
        receipt = build_transition_receipt(
            state,
            ACCEPT_REPRESENTATIVE_QA,
            "wrong-output-qa",
            {"visual_qa_receipts": qa},
        )
        with self.assertRaises(ProductionControllerError) as caught:
            apply_transition(state, receipt)
        self.assertEqual(caught.exception.reason_code, "visual_qa_output_set_mismatch")

    def test_invalid_attempt_blocks_and_recovery_starts_from_zero_authority(self) -> None:
        state = self._bind_rules()
        too_early = build_transition_receipt(
            state,
            AUTHORIZE_BATCH,
            "batch-too-early-block",
            {"candidate_ids": state["candidate_ids"]},
        )
        result = transition_or_block(state, too_early)
        self.assertFalse(result["ok"])
        self.assertEqual(result["state"]["state"], BLOCKED)
        self.assertFalse(result["state"]["manual_upload_ready"])

        recovered = recover_fail_closed(
            result["state"], self.packages, self.completion, "recovery-1"
        )
        self.assertEqual(recovered["state"], AWAITING_HARD_RULES)
        self.assertEqual(recovered["hard_rule_evidence"], [])
        self.assertEqual(recovered["representatives"], {})
        self.assertEqual(recovered["local_media_receipt_hashes"], {})
        self.assertFalse(recovered["manual_upload_ready"])
        self.assertEqual(recovered["recovery_count"], 1)


if __name__ == "__main__":
    unittest.main()
