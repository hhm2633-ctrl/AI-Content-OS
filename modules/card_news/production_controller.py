"""Pure fail-closed state machine for CardNews production.

The controller authorizes work; it never renders, publishes, issues links, or
writes receipts.  Every transition is bound to the exact prior state hash,
package batch hash, and immutable owner hard-rule evidence.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Dict, List, Mapping, Sequence

from modules.agent_console.package_completion_gate import assess_package_completion
from modules.media_intelligence.local_media_pipeline import SCHEMA_VERSION as LOCAL_MEDIA_SCHEMA_VERSION


STATE_SCHEMA_VERSION = "cardnews_production_controller_state_v1"
RECEIPT_SCHEMA_VERSION = "cardnews_production_controller_receipt_v1"
REQUIRED_HARD_RULE_IDS = (
    "OD-CARD-017",
    "OD-CARD-018",
    "OD-CARD-019",
    "OD-CARD-020",
)

AWAITING_HARD_RULES = "awaiting_hard_rules"
REPRESENTATIVE_PENDING = "representative_pending"
REPRESENTATIVE_AUTHORIZED = "representative_authorized"
REPRESENTATIVE_RENDER_RECORDED = "representative_render_recorded"
REPRESENTATIVE_QA_PASSED = "representative_qa_passed"
BATCH_AUTHORIZED = "batch_authorized"
BATCH_RENDER_RECORDED = "batch_render_recorded"
MANUAL_UPLOAD_READY = "manual_upload_ready"
BLOCKED = "blocked"

BIND_HARD_RULES = "bind_hard_rules"
AUTHORIZE_REPRESENTATIVES = "authorize_representatives"
RECORD_REPRESENTATIVE_RENDER = "record_representative_render"
ACCEPT_REPRESENTATIVE_QA = "accept_representative_qa"
AUTHORIZE_BATCH = "authorize_batch"
RECORD_BATCH_RENDER = "record_batch_render"
ACCEPT_BATCH_QA = "accept_batch_qa"

LEGAL_TRANSITIONS = {
    (AWAITING_HARD_RULES, BIND_HARD_RULES): REPRESENTATIVE_PENDING,
    (REPRESENTATIVE_PENDING, AUTHORIZE_REPRESENTATIVES): REPRESENTATIVE_AUTHORIZED,
    (REPRESENTATIVE_AUTHORIZED, RECORD_REPRESENTATIVE_RENDER): REPRESENTATIVE_RENDER_RECORDED,
    (REPRESENTATIVE_RENDER_RECORDED, ACCEPT_REPRESENTATIVE_QA): REPRESENTATIVE_QA_PASSED,
    (REPRESENTATIVE_QA_PASSED, AUTHORIZE_BATCH): BATCH_AUTHORIZED,
    (BATCH_AUTHORIZED, RECORD_BATCH_RENDER): BATCH_RENDER_RECORDED,
    (BATCH_RENDER_RECORDED, ACCEPT_BATCH_QA): MANUAL_UPLOAD_READY,
}
PROHIBITED_ACTIONS = {
    "publish",
    "post",
    "sns_publish",
    "issue_affiliate_link",
    "resume_automation",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_F_DRIVE_PATH = re.compile(r"^[Ff]:[\\/]")


class ProductionControllerError(ValueError):
    """A stable fail-closed controller violation."""

    def __init__(self, reason_code: str, detail: str):
        super().__init__(f"{reason_code}: {detail}")
        self.reason_code = reason_code
        self.detail = detail


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_hash(value: Any) -> str:
    """Return a deterministic SHA-256 digest for a JSON-compatible value."""

    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _state_body(state: Mapping[str, Any]) -> Dict[str, Any]:
    body = copy.deepcopy(dict(state))
    body.pop("state_hash", None)
    return body


def _state_hash(state: Mapping[str, Any]) -> str:
    return canonical_hash(_state_body(state))


def _assert_hash(value: Any, field: str) -> str:
    text = _text(value).lower()
    if not _SHA256.fullmatch(text):
        raise ProductionControllerError("receipt_hash_invalid", f"{field} must be a SHA-256 hex digest")
    return text


def validate_state(state: Mapping[str, Any]) -> None:
    """Reject malformed or tampered controller state."""

    if not isinstance(state, Mapping):
        raise ProductionControllerError("controller_state_missing", "controller state must be an object")
    if state.get("schema_version") != STATE_SCHEMA_VERSION:
        raise ProductionControllerError("controller_schema_unsupported", "controller state schema is unsupported")
    if not _text(state.get("controller_id")):
        raise ProductionControllerError("controller_id_missing", "controller identity is required")
    expected = _state_hash(state)
    if _text(state.get("state_hash")) != expected:
        raise ProductionControllerError("controller_state_tampered", "stored state hash does not match state body")
    hard_rules = state.get("hard_rule_evidence")
    hard_rule_hash = _text(state.get("hard_rule_hash"))
    if hard_rules:
        if hard_rule_hash != canonical_hash(hard_rules):
            raise ProductionControllerError(
                "hard_rule_evidence_tampered", "immutable hard-rule evidence no longer matches its binding"
            )
    elif hard_rule_hash:
        raise ProductionControllerError("hard_rule_evidence_missing", "hard-rule hash has no bound evidence")


def _package_identity(receipt: Mapping[str, Any]) -> tuple[str, str]:
    candidate_id = _text(receipt.get("candidate_id"))
    account = _text(receipt.get("account")).upper()
    if not candidate_id or account not in {"A", "B", "C"}:
        raise ProductionControllerError(
            "package_identity_invalid", "completion receipt needs a candidate id and account A, B, or C"
        )
    return candidate_id, account


def initialize_controller(
    controller_id: str,
    packages: Sequence[Mapping[str, Any]],
    completion_receipts: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Create an un-authorized controller from independently complete packages."""

    controller_id = _text(controller_id)
    if not controller_id:
        raise ProductionControllerError("controller_id_missing", "controller identity is required")
    if not isinstance(packages, Sequence) or isinstance(packages, (str, bytes)) or not packages:
        raise ProductionControllerError("packages_missing", "at least one package is required")
    if len(packages) != len(completion_receipts):
        raise ProductionControllerError(
            "completion_receipt_count_mismatch", "one completion receipt is required per package"
        )

    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for package, supplied in zip(packages, completion_receipts):
        if not isinstance(package, Mapping) or not isinstance(supplied, Mapping):
            raise ProductionControllerError(
                "package_or_receipt_invalid", "packages and completion receipts must be objects"
            )
        fresh = assess_package_completion(package)
        if not fresh.get("package_complete"):
            raise ProductionControllerError(
                "package_completion_failed",
                ", ".join(fresh.get("missing_fields") or ["package requirements missing"]),
            )
        if canonical_hash(supplied) != canonical_hash(fresh):
            raise ProductionControllerError(
                "completion_receipt_stale", "completion receipt does not match the current package"
            )
        candidate_id, account = _package_identity(fresh)
        if candidate_id in seen:
            raise ProductionControllerError("duplicate_package", f"duplicate candidate {candidate_id}")
        seen.add(candidate_id)
        rows.append(
            {
                "candidate_id": candidate_id,
                "account": account,
                "package_hash": canonical_hash(package),
                "completion_receipt_hash": canonical_hash(fresh),
            }
        )

    rows.sort(key=lambda item: item["candidate_id"])
    state: Dict[str, Any] = {
        "schema_version": STATE_SCHEMA_VERSION,
        "controller_id": controller_id,
        "state": AWAITING_HARD_RULES,
        "sequence": 0,
        "batch_hash": canonical_hash(rows),
        "packages": rows,
        "candidate_ids": [item["candidate_id"] for item in rows],
        "accounts": sorted({item["account"] for item in rows}),
        "hard_rule_evidence": [],
        "hard_rule_hash": None,
        "representatives": {},
        "local_media_receipt_hashes": {},
        "local_media_source_bindings": {},
        "representative_render_receipt_hashes": {},
        "representative_output_set_ids": {},
        "representative_qa_receipt_hashes": {},
        "representative_qa_receipt_ids": {},
        "batch_authorization_hash": None,
        "batch_render_receipt_hashes": {},
        "batch_output_set_ids": {},
        "batch_qa_receipt_hashes": {},
        "used_render_authorization_ids": [],
        "manual_upload_ready": False,
        "used_receipt_ids": [],
        "transition_log": [],
        "blocked_reason": None,
        "recovery_count": 0,
    }
    state["state_hash"] = _state_hash(state)
    return state


def build_transition_receipt(
    state: Mapping[str, Any],
    transition: str,
    receipt_id: str,
    payload: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build a deterministic receipt; this does not authorize the transition."""

    validate_state(state)
    transition = _text(transition).lower()
    receipt_id = _text(receipt_id)
    if not transition or not receipt_id:
        raise ProductionControllerError("receipt_identity_missing", "transition and receipt id are required")
    normalized_payload = copy.deepcopy(dict(payload or {}))
    hard_rule_hash = _text(state.get("hard_rule_hash")) or None
    if transition == BIND_HARD_RULES:
        hard_rule_hash = canonical_hash(normalized_payload.get("hard_rules", []))
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "receipt_id": receipt_id,
        "controller_id": state["controller_id"],
        "transition": transition,
        "from_state": state["state"],
        "state_hash_before": state["state_hash"],
        "batch_hash": state["batch_hash"],
        "hard_rule_hash": hard_rule_hash,
        "payload": normalized_payload,
        "payload_hash": canonical_hash(normalized_payload),
    }


def _validate_hard_rules(payload: Mapping[str, Any], receipt: Mapping[str, Any]) -> List[Dict[str, str]]:
    rules = payload.get("hard_rules")
    if not isinstance(rules, list):
        raise ProductionControllerError("hard_rule_receipt_missing", "hard_rules list is required")
    normalized: List[Dict[str, str]] = []
    for item in rules:
        if not isinstance(item, Mapping):
            raise ProductionControllerError("hard_rule_receipt_invalid", "each hard rule must be an object")
        claim_id = _text(item.get("claim_id"))
        rule = _text(item.get("rule"))
        source = _text(item.get("source"))
        if not claim_id or not rule or not source:
            raise ProductionControllerError(
                "hard_rule_receipt_invalid", "claim_id, exact rule text, and source are required"
            )
        normalized.append({"claim_id": claim_id, "rule": rule, "source": source})
    normalized.sort(key=lambda item: item["claim_id"])
    actual = [item["claim_id"] for item in normalized]
    if actual != list(REQUIRED_HARD_RULE_IDS):
        raise ProductionControllerError(
            "hard_rule_receipt_incomplete", "OD-CARD-017 through OD-CARD-020 must be bound exactly once"
        )
    expected_hash = canonical_hash(normalized)
    if _text(receipt.get("hard_rule_hash")) != expected_hash:
        raise ProductionControllerError("hard_rule_hash_mismatch", "receipt does not bind the exact hard rules")
    return normalized


def _candidate_account_map(state: Mapping[str, Any]) -> Dict[str, str]:
    return {item["candidate_id"]: item["account"] for item in state["packages"]}


def _string_map(value: Any, field: str, keys: Sequence[str] | None = None) -> Dict[str, str]:
    if not isinstance(value, Mapping):
        raise ProductionControllerError("transition_payload_invalid", f"{field} must be an object")
    result = {_text(key): _text(item) for key, item in value.items() if _text(key) and _text(item)}
    if keys is not None and set(result) != set(keys):
        raise ProductionControllerError(
            "transition_scope_incomplete", f"{field} must cover exactly {sorted(keys)}"
        )
    return result


def _hash_map(value: Any, field: str, keys: Sequence[str]) -> Dict[str, str]:
    result = _string_map(value, field, keys)
    for key, value_hash in result.items():
        _assert_hash(value_hash, f"{field}.{key}")
    return result


def _object_map(value: Any, field: str, keys: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(value, Mapping) or set(value) != set(keys):
        raise ProductionControllerError(
            "transition_scope_incomplete", f"{field} must cover exactly {sorted(keys)}"
        )
    result: Dict[str, Dict[str, Any]] = {}
    for key in keys:
        item = value.get(key)
        if not isinstance(item, Mapping):
            raise ProductionControllerError(
                "transition_payload_invalid", f"{field}.{key} must be an object"
            )
        result[key] = copy.deepcopy(dict(item))
    return result


def _validated_local_media_receipts(
    value: Any,
    candidate_ids: Sequence[str],
) -> tuple[
    Dict[str, List[Dict[str, Any]]],
    Dict[str, List[str]],
    Dict[str, List[Dict[str, str]]],
]:
    """Validate completed, self-sealed local-media receipts per candidate.

    The candidate-to-receipt mapping is the controller binding because the
    pre-render receipt deliberately describes an asset, not an editorial
    candidate.  A candidate may therefore bind one or more prepared assets.
    """

    if not isinstance(value, Mapping) or set(value) != set(candidate_ids):
        raise ProductionControllerError(
            "local_media_scope_incomplete",
            f"local_media_receipts must cover exactly {sorted(candidate_ids)}",
        )
    normalized: Dict[str, List[Dict[str, Any]]] = {}
    hashes: Dict[str, List[str]] = {}
    source_bindings: Dict[str, List[Dict[str, str]]] = {}
    seen_request_ids: set[str] = set()
    for candidate_id in candidate_ids:
        raw_rows = value.get(candidate_id)
        if isinstance(raw_rows, Mapping):
            rows = [raw_rows]
        elif isinstance(raw_rows, list):
            rows = raw_rows
        else:
            rows = []
        if not rows:
            raise ProductionControllerError(
                "local_media_receipt_missing", f"{candidate_id} needs at least one preparation receipt"
            )
        candidate_rows: List[Dict[str, Any]] = []
        candidate_hashes: List[str] = []
        candidate_sources: List[Dict[str, str]] = []
        for position, raw in enumerate(rows, start=1):
            field = f"local_media_receipts.{candidate_id}[{position}]"
            if not isinstance(raw, Mapping):
                raise ProductionControllerError("local_media_receipt_invalid", f"{field} must be an object")
            receipt = copy.deepcopy(dict(raw))
            supplied_hash = _assert_hash(receipt.get("receipt_hash"), f"{field}.receipt_hash")
            unsealed = copy.deepcopy(receipt)
            unsealed.pop("receipt_hash", None)
            if canonical_hash(unsealed) != supplied_hash:
                raise ProductionControllerError(
                    "local_media_receipt_stale", f"{field} no longer matches its sealed receipt hash"
                )
            if receipt.get("schema_version") != LOCAL_MEDIA_SCHEMA_VERSION:
                raise ProductionControllerError(
                    "local_media_schema_unsupported", f"{field} must use {LOCAL_MEDIA_SCHEMA_VERSION}"
                )
            if _text(receipt.get("status")) != "completed" or receipt.get("pre_render_prepared") is not True:
                raise ProductionControllerError(
                    "local_media_not_prepared", f"{field} is not a completed pre-render preparation"
                )
            if (
                receipt.get("owner_selected") is not True
                or receipt.get("rights_cleared") is not True
                or receipt.get("source_modified") is not False
                or receipt.get("implicit_execution") is not False
            ):
                raise ProductionControllerError(
                    "local_media_safety_gate_failed", f"{field} does not satisfy the explicit preparation gates"
                )
            source = receipt.get("source") if isinstance(receipt.get("source"), Mapping) else {}
            if source.get("preserved") is not True:
                raise ProductionControllerError(
                    "local_media_source_not_preserved", f"{field} must preserve the source asset"
                )
            source_hash = _assert_hash(source.get("sha256"), f"{field}.source.sha256")
            source_path = _text(source.get("path"))
            if not source_path:
                raise ProductionControllerError(
                    "local_media_source_path_missing", f"{field} needs the prepared source path"
                )
            if not _F_DRIVE_PATH.match(_text(receipt.get("output_root"))):
                raise ProductionControllerError(
                    "local_media_output_root_invalid", f"{field} output_root must be an explicit F: path"
                )
            operations = receipt.get("operations")
            if not isinstance(operations, list) or not operations:
                raise ProductionControllerError(
                    "local_media_operations_missing", f"{field} needs at least one completed operation"
                )
            if any(not isinstance(item, Mapping) or _text(item.get("status")) != "completed" for item in operations):
                raise ProductionControllerError(
                    "local_media_operation_failed", f"{field} contains an incomplete operation"
                )
            preserve_original = False
            if len(operations) == 1 and isinstance(operations[0], Mapping):
                operation = operations[0]
                result = operation.get("result") if isinstance(operation.get("result"), Mapping) else {}
                preserve_original = (
                    _text(operation.get("operation")) == "preserve_original"
                    and result.get("status") == "completed"
                    and result.get("source_preserved") is True
                    and result.get("tool_subprocess_executed") is False
                )
            if preserve_original:
                if receipt.get("tools_executed") is not False:
                    raise ProductionControllerError(
                        "local_media_passthrough_invalid",
                        f"{field} preserve_original must attest that no tool subprocess ran",
                    )
            elif receipt.get("tools_executed") is not True:
                raise ProductionControllerError(
                    "local_media_safety_gate_failed",
                    f"{field} non-passthrough preparation must execute its requested tool",
                )
            request_id = _text(receipt.get("request_id"))
            asset_id = _text(receipt.get("asset_id"))
            if not request_id or not asset_id:
                raise ProductionControllerError(
                    "local_media_identity_missing", f"{field} needs request_id and asset_id"
                )
            if request_id in seen_request_ids:
                raise ProductionControllerError(
                    "local_media_receipt_reused", f"request_id {request_id} is bound more than once"
                )
            seen_request_ids.add(request_id)
            candidate_rows.append(receipt)
            candidate_hashes.append(supplied_hash)
            candidate_sources.append(
                {
                    "receipt_hash": supplied_hash,
                    "request_id": request_id,
                    "asset_id": asset_id,
                    "source_path": source_path,
                    "source_sha256": source_hash,
                }
            )
        normalized[candidate_id] = candidate_rows
        hashes[candidate_id] = sorted(candidate_hashes)
        source_bindings[candidate_id] = sorted(
            candidate_sources, key=lambda item: (item["receipt_hash"], item["source_path"])
        )
    return normalized, hashes, source_bindings


def _positive_equal_counts(receipt: Mapping[str, Any], first: str, second: str, field: str) -> int:
    try:
        left = int(receipt.get(first))
        right = int(receipt.get(second))
    except (TypeError, ValueError):
        raise ProductionControllerError(
            "receipt_slide_count_invalid", f"{field} needs integer {first} and {second}"
        ) from None
    if left < 1 or left != right:
        raise ProductionControllerError(
            "receipt_slide_count_mismatch", f"{field} needs equal positive {first} and {second}"
        )
    return left


def _validated_render_receipts(
    value: Any, candidate_ids: Sequence[str], state: Mapping[str, Any]
) -> tuple[Dict[str, Any], Dict[str, str]]:
    receipts = _object_map(value, "render_receipts", candidate_ids)
    hashes: Dict[str, str] = {}
    expected_mode = (
        "representative" if state.get("state") == REPRESENTATIVE_AUTHORIZED else "batch"
    )
    expected_media_binding = canonical_hash(
        {
            candidate_id: list(state.get("local_media_receipt_hashes", {}).get(candidate_id, []))
            for candidate_id in candidate_ids
        }
    )
    authorization_ids: set[str] = set()
    for candidate_id, receipt in receipts.items():
        if _text(receipt.get("candidate_id")) != candidate_id:
            raise ProductionControllerError(
                "render_receipt_identity_mismatch", f"render receipt does not belong to {candidate_id}"
            )
        if _text(receipt.get("status")) != "render_completed_pending_visual_qa":
            raise ProductionControllerError(
                "render_receipt_not_complete", f"{candidate_id} render is not awaiting visual QA"
            )
        for field in (
            "controller_state_hash",
            "batch_hash",
            "hard_rule_hash",
            "output_set_id",
            "authorization_id",
            "render_mode",
            "local_media_binding_hash",
        ):
            if not _text(receipt.get(field)):
                raise ProductionControllerError(
                    "render_receipt_binding_missing", f"{candidate_id} render receipt needs {field}"
                )
        authorization_id = _text(receipt.get("authorization_id"))
        authorization_ids.add(authorization_id)
        if authorization_id in state.get("used_render_authorization_ids", []):
            raise ProductionControllerError(
                "render_authorization_reused", f"{authorization_id} was already consumed"
            )
        if _text(receipt.get("output_set_id")) != authorization_id:
            raise ProductionControllerError(
                "render_authorization_output_set_mismatch",
                f"{candidate_id} output set must be the consumed authorization id",
            )
        if _text(receipt.get("render_mode")) != expected_mode:
            raise ProductionControllerError(
                "render_authorization_mode_mismatch", f"{candidate_id} render mode is not {expected_mode}"
            )
        if _text(receipt.get("local_media_binding_hash")) != expected_media_binding:
            raise ProductionControllerError(
                "render_local_media_binding_mismatch",
                f"{candidate_id} render is not bound to current local-media receipts",
            )
        if _text(receipt.get("controller_state_hash")) != state["state_hash"]:
            raise ProductionControllerError(
                "render_receipt_state_mismatch", f"{candidate_id} render was not authorized by the current state"
            )
        if _text(receipt.get("batch_hash")) != state["batch_hash"]:
            raise ProductionControllerError(
                "render_receipt_batch_mismatch", f"{candidate_id} render belongs to another package batch"
            )
        if _text(receipt.get("hard_rule_hash")) != state["hard_rule_hash"]:
            raise ProductionControllerError(
                "render_receipt_hard_rule_mismatch", f"{candidate_id} render used another hard-rule binding"
            )
        count = _positive_equal_counts(
            receipt, "expected_slide_count", "rendered_slide_count", f"render_receipts.{candidate_id}"
        )
        output_hashes = receipt.get("output_hashes")
        values: List[str]
        if isinstance(output_hashes, Mapping):
            values = [_text(item) for item in output_hashes.values()]
        elif isinstance(output_hashes, list):
            values = [_text(item) for item in output_hashes]
        else:
            values = []
        if len(values) != count or len(set(values)) != count:
            raise ProductionControllerError(
                "render_output_hashes_incomplete",
                f"{candidate_id} needs one distinct output hash per rendered slide",
            )
        for position, output_hash in enumerate(values, start=1):
            _assert_hash(output_hash, f"render_receipts.{candidate_id}.output_hashes[{position}]")
        hashes[candidate_id] = canonical_hash(receipt)
    if len(authorization_ids) != 1:
        raise ProductionControllerError(
            "render_authorization_mixed", "all rendered candidates must share one authorization"
        )
    return receipts, hashes


def _validated_visual_qa_receipts(
    value: Any,
    candidate_ids: Sequence[str],
    expected_output_set_ids: Mapping[str, str],
    *,
    expected_representative_receipt_ids: Mapping[str, str] | None = None,
) -> tuple[Dict[str, Any], Dict[str, str]]:
    receipts = _object_map(value, "visual_qa_receipts", candidate_ids)
    hashes: Dict[str, str] = {}
    for candidate_id, receipt in receipts.items():
        if _text(receipt.get("candidate_id")) != candidate_id:
            raise ProductionControllerError(
                "visual_qa_identity_mismatch", f"visual QA receipt does not belong to {candidate_id}"
            )
        if _text(receipt.get("status")) != "passed" or receipt.get("visual_qa_passed") is not True:
            raise ProductionControllerError(
                "visual_qa_not_passed", f"{candidate_id} does not have a passed visual QA receipt"
            )
        if _text(receipt.get("output_set_id")) != _text(expected_output_set_ids.get(candidate_id)):
            raise ProductionControllerError(
                "visual_qa_output_set_mismatch", f"{candidate_id} QA does not review its rendered output set"
            )
        failure_count = receipt.get("failure_count")
        if isinstance(failure_count, bool) or failure_count != 0:
            raise ProductionControllerError(
                "visual_qa_failures_present", f"{candidate_id} visual QA has failures"
            )
        if receipt.get("reviewer_independent") is not True:
            raise ProductionControllerError(
                "visual_qa_reviewer_not_independent", f"{candidate_id} maker and reviewer must be separate"
            )
        if not _text(receipt.get("receipt_id")):
            raise ProductionControllerError(
                "visual_qa_receipt_id_missing", f"{candidate_id} visual QA needs its source receipt id"
            )
        if expected_representative_receipt_ids is not None:
            actual_ids = receipt.get("representative_receipt_ids")
            if not isinstance(actual_ids, Mapping) or {
                _text(key).upper(): _text(item) for key, item in actual_ids.items()
            } != dict(expected_representative_receipt_ids):
                raise ProductionControllerError(
                    "visual_qa_representative_binding_mismatch",
                    f"{candidate_id} batch QA is not bound to the approved representative QA receipts",
                )
        _positive_equal_counts(
            receipt, "expected_slide_count", "reviewed_slide_count", f"visual_qa_receipts.{candidate_id}"
        )
        hashes[candidate_id] = canonical_hash(receipt)
    return receipts, hashes


def _validate_transition_payload(
    state: Mapping[str, Any], receipt: Mapping[str, Any]
) -> Dict[str, Any]:
    transition = receipt["transition"]
    payload = receipt.get("payload")
    if not isinstance(payload, Mapping):
        raise ProductionControllerError("transition_payload_invalid", "receipt payload must be an object")
    normalized = copy.deepcopy(dict(payload))
    candidates = list(state["candidate_ids"])
    accounts = list(state["accounts"])

    if transition == BIND_HARD_RULES:
        normalized["hard_rules"] = _validate_hard_rules(payload, receipt)
    elif transition == AUTHORIZE_REPRESENTATIVES:
        representatives = _string_map(payload.get("representatives"), "representatives", accounts)
        account_by_candidate = _candidate_account_map(state)
        if len(set(representatives.values())) != len(accounts):
            raise ProductionControllerError(
                "representative_selection_invalid", "one distinct representative is required per account"
            )
        for account, candidate_id in representatives.items():
            if account_by_candidate.get(candidate_id) != account:
                raise ProductionControllerError(
                    "representative_selection_invalid", f"{candidate_id} is not an Account {account} package"
                )
        normalized["representatives"] = representatives
        representative_ids = sorted(representatives.values())
        media_receipts, media_hashes, source_bindings = _validated_local_media_receipts(
            payload.get("local_media_receipts"), representative_ids
        )
        normalized["local_media_receipts"] = media_receipts
        normalized["local_media_receipt_hashes"] = media_hashes
        normalized["local_media_source_bindings"] = source_bindings
    elif transition == RECORD_REPRESENTATIVE_RENDER:
        representative_ids = sorted(state["representatives"].values())
        receipts, hashes = _validated_render_receipts(
            payload.get("render_receipts"), representative_ids, state
        )
        normalized["render_receipts"] = receipts
        normalized["render_receipt_hashes"] = hashes
    elif transition == ACCEPT_REPRESENTATIVE_QA:
        representative_ids = sorted(state["representatives"].values())
        receipts, hashes = _validated_visual_qa_receipts(
            payload.get("visual_qa_receipts"), representative_ids, state["representative_output_set_ids"]
        )
        normalized["visual_qa_receipts"] = receipts
        normalized["visual_qa_receipt_hashes"] = hashes
    elif transition == AUTHORIZE_BATCH:
        requested = payload.get("candidate_ids")
        if not isinstance(requested, list) or sorted({_text(item) for item in requested if _text(item)}) != sorted(candidates):
            raise ProductionControllerError(
                "batch_scope_incomplete", "batch authorization must cover every bound package exactly"
            )
        normalized["candidate_ids"] = sorted(candidates)
        media_receipts, media_hashes, source_bindings = _validated_local_media_receipts(
            payload.get("local_media_receipts"), candidates
        )
        for candidate_id, prior_hashes in state.get("local_media_receipt_hashes", {}).items():
            if candidate_id in media_hashes and list(prior_hashes) != media_hashes[candidate_id]:
                raise ProductionControllerError(
                    "local_media_receipt_changed",
                    f"{candidate_id} media preparation changed after representative authorization",
                )
        normalized["local_media_receipts"] = media_receipts
        normalized["local_media_receipt_hashes"] = media_hashes
        normalized["local_media_source_bindings"] = source_bindings
    elif transition == RECORD_BATCH_RENDER:
        receipts, hashes = _validated_render_receipts(payload.get("render_receipts"), candidates, state)
        normalized["render_receipts"] = receipts
        normalized["render_receipt_hashes"] = hashes
    elif transition == ACCEPT_BATCH_QA:
        receipts, hashes = _validated_visual_qa_receipts(
            payload.get("visual_qa_receipts"), candidates, state["batch_output_set_ids"],
            expected_representative_receipt_ids=state["representative_qa_receipt_ids"],
        )
        normalized["visual_qa_receipts"] = receipts
        normalized["visual_qa_receipt_hashes"] = hashes
    return normalized


def _validate_receipt(state: Mapping[str, Any], receipt: Mapping[str, Any]) -> Dict[str, Any]:
    validate_state(state)
    if not isinstance(receipt, Mapping):
        raise ProductionControllerError("transition_receipt_missing", "transition receipt is required")
    transition = _text(receipt.get("transition")).lower()
    if transition in PROHIBITED_ACTIONS:
        raise ProductionControllerError("publish_prohibited", f"{transition} is outside this controller")
    if receipt.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        raise ProductionControllerError("receipt_schema_unsupported", "transition receipt schema is unsupported")
    receipt_id = _text(receipt.get("receipt_id"))
    if not receipt_id:
        raise ProductionControllerError("receipt_id_missing", "receipt id is required")
    if receipt_id in state.get("used_receipt_ids", []):
        raise ProductionControllerError("duplicate_receipt", f"receipt {receipt_id} was already consumed")
    if _text(receipt.get("controller_id")) != state["controller_id"]:
        raise ProductionControllerError("controller_id_mismatch", "receipt belongs to another controller")
    if _text(receipt.get("from_state")) != state["state"]:
        raise ProductionControllerError("receipt_state_mismatch", "receipt was not issued for the current state")
    if _text(receipt.get("state_hash_before")) != state["state_hash"]:
        raise ProductionControllerError("stale_state_hash", "receipt was issued for a stale controller state")
    if _text(receipt.get("batch_hash")) != state["batch_hash"]:
        raise ProductionControllerError("stale_batch_hash", "receipt was issued for another package batch")
    if (state["state"], transition) not in LEGAL_TRANSITIONS:
        raise ProductionControllerError(
            "illegal_transition", f"{transition or '<missing>'} is not legal from {state['state']}"
        )
    payload = receipt.get("payload")
    if canonical_hash(payload if isinstance(payload, Mapping) else {}) != _text(receipt.get("payload_hash")):
        raise ProductionControllerError("receipt_payload_tampered", "payload hash does not match receipt payload")
    if transition != BIND_HARD_RULES:
        if not state.get("hard_rule_evidence") or not _text(state.get("hard_rule_hash")):
            raise ProductionControllerError("hard_rule_receipt_missing", "hard rules must be bound first")
        if _text(receipt.get("hard_rule_hash")) != state["hard_rule_hash"]:
            raise ProductionControllerError(
                "hard_rule_hash_mismatch", "transition receipt is not bound to current hard rules"
            )
    normalized = _validate_transition_payload(state, receipt)
    copy_receipt = copy.deepcopy(dict(receipt))
    copy_receipt["payload"] = normalized
    copy_receipt["payload_hash"] = canonical_hash(normalized)
    return copy_receipt


def apply_transition(state: Mapping[str, Any], receipt: Mapping[str, Any]) -> Dict[str, Any]:
    """Apply one legal, one-use transition without mutating the input state."""

    valid = _validate_receipt(state, receipt)
    transition = valid["transition"]
    next_state = LEGAL_TRANSITIONS[(state["state"], transition)]
    updated = copy.deepcopy(dict(state))
    payload = valid["payload"]

    if transition == BIND_HARD_RULES:
        updated["hard_rule_evidence"] = copy.deepcopy(payload["hard_rules"])
        updated["hard_rule_hash"] = canonical_hash(updated["hard_rule_evidence"])
    elif transition == AUTHORIZE_REPRESENTATIVES:
        updated["representatives"] = copy.deepcopy(payload["representatives"])
        updated["local_media_receipt_hashes"] = copy.deepcopy(payload["local_media_receipt_hashes"])
        updated["local_media_source_bindings"] = copy.deepcopy(payload["local_media_source_bindings"])
    elif transition == RECORD_REPRESENTATIVE_RENDER:
        updated["representative_render_receipt_hashes"] = copy.deepcopy(payload["render_receipt_hashes"])
        updated["representative_output_set_ids"] = {
            candidate_id: _text(receipt.get("output_set_id"))
            for candidate_id, receipt in payload["render_receipts"].items()
        }
        updated["used_render_authorization_ids"].append(
            _text(next(iter(payload["render_receipts"].values())).get("authorization_id"))
        )
    elif transition == ACCEPT_REPRESENTATIVE_QA:
        account_by_candidate = _candidate_account_map(updated)
        updated["representative_qa_receipt_ids"] = {
            account_by_candidate[candidate_id]: _text(receipt.get("receipt_id"))
            for candidate_id, receipt in payload["visual_qa_receipts"].items()
        }
        updated["representative_qa_receipt_hashes"] = {
            account_by_candidate[candidate_id]: _text(payload["visual_qa_receipt_hashes"].get(candidate_id, ""))
            for candidate_id in payload["visual_qa_receipt_hashes"]
            if account_by_candidate.get(candidate_id)
        }
    elif transition == AUTHORIZE_BATCH:
        updated["batch_authorization_hash"] = canonical_hash(valid)
        updated["local_media_receipt_hashes"] = copy.deepcopy(payload["local_media_receipt_hashes"])
        updated["local_media_source_bindings"] = copy.deepcopy(payload["local_media_source_bindings"])
    elif transition == RECORD_BATCH_RENDER:
        updated["batch_render_receipt_hashes"] = copy.deepcopy(payload["render_receipt_hashes"])
        updated["batch_output_set_ids"] = {
            candidate_id: _text(receipt.get("output_set_id"))
            for candidate_id, receipt in payload["render_receipts"].items()
        }
        updated["used_render_authorization_ids"].append(
            _text(next(iter(payload["render_receipts"].values())).get("authorization_id"))
        )
    elif transition == ACCEPT_BATCH_QA:
        updated["batch_qa_receipt_hashes"] = copy.deepcopy(payload["visual_qa_receipt_hashes"])
        updated["manual_upload_ready"] = True

    updated["state"] = next_state
    updated["sequence"] = int(updated["sequence"]) + 1
    updated["used_receipt_ids"].append(valid["receipt_id"])
    updated["transition_log"].append(
        {
            "receipt_id": valid["receipt_id"],
            "transition": transition,
            "from_state": state["state"],
            "to_state": next_state,
            "receipt_hash": canonical_hash(valid),
        }
    )
    updated["state_hash"] = _state_hash(updated)
    return updated


def _blocked_state(state: Mapping[str, Any], error: ProductionControllerError) -> Dict[str, Any]:
    blocked = copy.deepcopy(dict(state))
    blocked["state"] = BLOCKED
    blocked["manual_upload_ready"] = False
    blocked["representatives"] = {}
    blocked["local_media_receipt_hashes"] = {}
    blocked["local_media_source_bindings"] = {}
    blocked["representative_render_receipt_hashes"] = {}
    blocked["representative_output_set_ids"] = {}
    blocked["representative_qa_receipt_hashes"] = {}
    blocked["representative_qa_receipt_ids"] = {}
    blocked["batch_authorization_hash"] = None
    blocked["batch_render_receipt_hashes"] = {}
    blocked["batch_output_set_ids"] = {}
    blocked["batch_qa_receipt_hashes"] = {}
    blocked["blocked_reason"] = {"reason_code": error.reason_code, "detail": error.detail}
    blocked["state_hash"] = _state_hash(blocked)
    return blocked


def transition_or_block(state: Mapping[str, Any], receipt: Mapping[str, Any]) -> Dict[str, Any]:
    """Preferred integration API: any violation returns a fail-closed blocked state."""

    try:
        updated = apply_transition(state, receipt)
        return {"ok": True, "state": updated, "error": None}
    except ProductionControllerError as error:
        validate_state(state)
        return {
            "ok": False,
            "state": _blocked_state(state, error),
            "error": {"reason_code": error.reason_code, "detail": error.detail},
        }


def recover_fail_closed(
    blocked_state: Mapping[str, Any],
    packages: Sequence[Mapping[str, Any]],
    completion_receipts: Sequence[Mapping[str, Any]],
    recovery_receipt_id: str,
) -> Dict[str, Any]:
    """Restart from package verification and require hard-rule binding again."""

    validate_state(blocked_state)
    if blocked_state.get("state") != BLOCKED:
        raise ProductionControllerError("recovery_not_allowed", "only a blocked controller can recover")
    recovery_receipt_id = _text(recovery_receipt_id)
    if not recovery_receipt_id:
        raise ProductionControllerError("receipt_id_missing", "recovery receipt id is required")
    if recovery_receipt_id in blocked_state.get("used_receipt_ids", []):
        raise ProductionControllerError("duplicate_receipt", "recovery receipt was already consumed")
    recovered = initialize_controller(blocked_state["controller_id"], packages, completion_receipts)
    recovered["used_receipt_ids"] = list(blocked_state.get("used_receipt_ids", [])) + [recovery_receipt_id]
    recovered["transition_log"] = list(blocked_state.get("transition_log", [])) + [
        {
            "receipt_id": recovery_receipt_id,
            "transition": "recover_fail_closed",
            "from_state": BLOCKED,
            "to_state": AWAITING_HARD_RULES,
            "receipt_hash": canonical_hash(
                {
                    "recovery_receipt_id": recovery_receipt_id,
                    "blocked_state_hash": blocked_state["state_hash"],
                    "new_batch_hash": recovered["batch_hash"],
                }
            ),
        }
    ]
    recovered["recovery_count"] = int(blocked_state.get("recovery_count", 0)) + 1
    recovered["state_hash"] = _state_hash(recovered)
    return recovered


__all__ = [
    "STATE_SCHEMA_VERSION",
    "RECEIPT_SCHEMA_VERSION",
    "REQUIRED_HARD_RULE_IDS",
    "LEGAL_TRANSITIONS",
    "AWAITING_HARD_RULES",
    "REPRESENTATIVE_PENDING",
    "REPRESENTATIVE_AUTHORIZED",
    "REPRESENTATIVE_RENDER_RECORDED",
    "REPRESENTATIVE_QA_PASSED",
    "BATCH_AUTHORIZED",
    "BATCH_RENDER_RECORDED",
    "MANUAL_UPLOAD_READY",
    "BLOCKED",
    "BIND_HARD_RULES",
    "AUTHORIZE_REPRESENTATIVES",
    "RECORD_REPRESENTATIVE_RENDER",
    "ACCEPT_REPRESENTATIVE_QA",
    "AUTHORIZE_BATCH",
    "RECORD_BATCH_RENDER",
    "ACCEPT_BATCH_QA",
    "ProductionControllerError",
    "canonical_hash",
    "initialize_controller",
    "build_transition_receipt",
    "validate_state",
    "apply_transition",
    "transition_or_block",
    "recover_fail_closed",
]
