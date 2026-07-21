"""Pure batch bridge from approved finalists to production-package inputs.

This module does not execute discovery, package generation, rendering, or
publishing.  It only joins already-completed Agent Console handoffs with
already-completed deep evidence bundles and reports every missing join.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, Iterable, List, Mapping, Tuple

from modules.agent_console.contracts import sanitize_json


SCHEMA_VERSION = "production_package_batch_inputs_v1"
FINAL_SELECTION_SCHEMA = "cardnews_final_selection_v1"
ACCOUNTS = ("A", "B", "C")
COMPLETED = {"complete", "completed"}
DEFAULT_MAX_PER_ACCOUNT = 4
DEEP_BUNDLE_KEYS = (
    "deep_bundle",
    "selected_candidate_deep_bundle",
    "candidate_deep_bundle",
)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _account(value: Any) -> str:
    account = _text(value).upper()
    return account if account in ACCOUNTS else ""


def _safe_copy(value: Any) -> Any:
    return sanitize_json(copy.deepcopy(value))


def _rows(value: Any, collection_key: str) -> List[Mapping[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, Mapping)]
    if not isinstance(value, Mapping):
        return []
    collection = value.get(collection_key)
    if isinstance(collection, list):
        return [item for item in collection if isinstance(item, Mapping)]
    return []


def _handoff_rows(value: Any) -> List[Mapping[str, Any]]:
    rows = _rows(value, "jobs") or _rows(value, "handoffs")
    if rows:
        return rows
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _bundle_rows(value: Any) -> List[Mapping[str, Any]]:
    rows = _rows(value, "bundles")
    if rows:
        return rows
    if isinstance(value, list):
        return [item for item in value if isinstance(item, Mapping)]
    if not isinstance(value, Mapping):
        return []

    rows = []
    for key, item in value.items():
        if key in {"schema_version", "status", "reason_code"} or not isinstance(item, Mapping):
            continue
        bundle = copy.deepcopy(dict(item))
        bundle.setdefault("candidate_id", str(key))
        rows.append(bundle)
    return rows


def _index(
    rows: Iterable[Mapping[str, Any]],
) -> Tuple[Dict[Tuple[str, str], List[Mapping[str, Any]]], Dict[str, List[Mapping[str, Any]]]]:
    exact: Dict[Tuple[str, str], List[Mapping[str, Any]]] = {}
    by_candidate: Dict[str, List[Mapping[str, Any]]] = {}
    for row in rows:
        candidate_id = _text(row.get("candidate_id"))
        if not candidate_id:
            handoff = row.get("handoff")
            if isinstance(handoff, Mapping):
                candidate_id = _text(handoff.get("candidate_id"))
        if not candidate_id:
            continue
        account = _account(row.get("account"))
        if not account:
            handoff = row.get("handoff")
            if isinstance(handoff, Mapping):
                account = _account(handoff.get("account"))
        by_candidate.setdefault(candidate_id, []).append(row)
        if account:
            exact.setdefault((account, candidate_id), []).append(row)
    return exact, by_candidate


def _match(
    index: Tuple[Dict[Tuple[str, str], List[Mapping[str, Any]]], Dict[str, List[Mapping[str, Any]]]],
    account: str,
    candidate_id: str,
) -> Tuple[Mapping[str, Any] | None, bool]:
    exact, by_candidate = index
    matches = exact.get((account, candidate_id), [])
    if not matches:
        matches = by_candidate.get(candidate_id, [])
        # Candidate-only matching is safe only when there is exactly one row
        # and it does not explicitly claim another account.
        if len(matches) == 1 and _account(matches[0].get("account")) not in {"", account}:
            matches = []
    return (matches[0], False) if len(matches) == 1 else (None, len(matches) > 1)


def _completed_handoff(row: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if _text(row.get("status")).lower() != "completed":
        return None
    handoff = row.get("handoff")
    return handoff if isinstance(handoff, Mapping) else None


def _bundle_from_handoff(handoff: Mapping[str, Any]) -> Mapping[str, Any] | None:
    outputs = handoff.get("outputs")
    if not isinstance(outputs, Mapping):
        return None
    for key in DEEP_BUNDLE_KEYS:
        bundle = outputs.get(key)
        if isinstance(bundle, Mapping):
            return bundle
    spark = outputs.get("spark_receipt")
    if isinstance(spark, Mapping) and _text(spark.get("status")).lower() == "completed":
        spark_outputs = spark.get("outputs")
        if isinstance(spark_outputs, Mapping):
            for key in DEEP_BUNDLE_KEYS:
                bundle = spark_outputs.get(key)
                if isinstance(bundle, Mapping):
                    return bundle
    return None


def _blocked_record(
    account: str,
    candidate: Mapping[str, Any],
    reason_code: str,
    *,
    missing: List[str],
) -> Dict[str, Any]:
    candidate_id = _text(candidate.get("candidate_id"))
    return {
        "record_id": f"production-package-input:{account}:{candidate_id}" if candidate_id else None,
        "account": account,
        "candidate_id": candidate_id or None,
        "status": "blocked",
        "reason_code": reason_code,
        "missing_requirements": missing,
        "package_input": None,
    }


def build_production_package_batch_inputs(
    final_selection: Any,
    agent_console_results: Any,
    deep_bundles: Any = None,
    *,
    max_per_account: int = DEFAULT_MAX_PER_ACCOUNT,
) -> Dict[str, Any]:
    """Join selected candidates to completed local results without side effects."""

    empty_accounts = {
        account: {"selected_count": 0, "ready_count": 0, "blocked_count": 0, "records": []}
        for account in ACCOUNTS
    }
    if not isinstance(final_selection, Mapping) or final_selection.get("schema_version") != FINAL_SELECTION_SCHEMA:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "closed",
            "reason_code": "invalid_final_selection",
            "accounts": empty_accounts,
            "package_inputs": [],
            "missing_result_receipts": [],
            "package_executed": False,
            "render_executed": False,
            "publish_executed": False,
            "external_calls_executed": False,
        }
    if final_selection.get("status") not in {None, "selected"}:
        result = build_production_package_batch_inputs(
            {"schema_version": "invalid"}, agent_console_results, deep_bundles
        )
        result["reason_code"] = "final_selection_not_selected"
        return result

    try:
        bound = int(max_per_account)
    except (TypeError, ValueError):
        bound = 0
    if bound < 1:
        result = build_production_package_batch_inputs(
            {"schema_version": "invalid"}, agent_console_results, deep_bundles
        )
        result["reason_code"] = "invalid_account_limit"
        return result

    handoff_index = _index(_handoff_rows(agent_console_results))
    bundle_index = _index(_bundle_rows(deep_bundles))
    accounts = final_selection.get("accounts")
    accounts = accounts if isinstance(accounts, Mapping) else {}
    output_accounts: Dict[str, Any] = {}
    package_inputs: List[Dict[str, Any]] = []
    missing_receipts: List[Dict[str, Any]] = []

    for account in ACCOUNTS:
        bucket = accounts.get(account)
        selected = bucket.get("selected") if isinstance(bucket, Mapping) else []
        selected = selected if isinstance(selected, list) else []
        records: List[Dict[str, Any]] = []
        seen: set[str] = set()
        accepted_position = 0
        for raw_candidate in selected:
            if not isinstance(raw_candidate, Mapping):
                record = _blocked_record(account, {}, "invalid_selected_candidate", missing=["candidate"])
                records.append(record)
                missing_receipts.append(copy.deepcopy(record))
                continue
            candidate = dict(raw_candidate)
            candidate_id = _text(candidate.get("candidate_id"))
            candidate_account = _account(candidate.get("account")) or account
            if not candidate_id or candidate_account != account or candidate.get("selection_status") == "not_selected":
                record = _blocked_record(account, candidate, "invalid_selected_candidate", missing=["candidate_id_or_account"])
                records.append(record)
                missing_receipts.append(copy.deepcopy(record))
                continue
            if candidate_id in seen:
                record = _blocked_record(account, candidate, "duplicate_selected_candidate", missing=["unique_candidate_id"])
                records.append(record)
                missing_receipts.append(copy.deepcopy(record))
                continue
            seen.add(candidate_id)
            accepted_position += 1
            if accepted_position > bound:
                record = _blocked_record(account, candidate, "per_account_limit_exceeded", missing=["bounded_batch_slot"])
                records.append(record)
                missing_receipts.append(copy.deepcopy(record))
                continue

            handoff_row, ambiguous_handoff = _match(handoff_index, account, candidate_id)
            if ambiguous_handoff:
                record = _blocked_record(account, candidate, "ambiguous_agent_console_result", missing=["unique_completed_handoff"])
            elif handoff_row is None:
                record = _blocked_record(account, candidate, "missing_agent_console_result", missing=["completed_handoff"])
            else:
                handoff = _completed_handoff(handoff_row)
                if handoff is None:
                    record = _blocked_record(account, candidate, "agent_console_result_not_completed", missing=["completed_handoff"])
                else:
                    bundle_row, ambiguous_bundle = _match(bundle_index, account, candidate_id)
                    bundle = bundle_row if bundle_row is not None else _bundle_from_handoff(handoff)
                    if ambiguous_bundle:
                        record = _blocked_record(account, candidate, "ambiguous_deep_bundle", missing=["unique_completed_deep_bundle"])
                    elif not isinstance(bundle, Mapping):
                        record = _blocked_record(account, candidate, "missing_deep_bundle", missing=["completed_deep_bundle"])
                    elif _text(bundle.get("status")).lower() not in COMPLETED:
                        record = _blocked_record(account, candidate, "deep_bundle_not_completed", missing=["completed_deep_bundle"])
                    elif _text(bundle.get("candidate_id")) not in {"", candidate_id} or _account(bundle.get("account")) not in {"", account}:
                        record = _blocked_record(account, candidate, "deep_bundle_identity_mismatch", missing=["matching_candidate_account"])
                    else:
                        package_input = {
                            "schema_version": "production_package_input_v1",
                            "record_id": f"production-package-input:{account}:{candidate_id}",
                            "account": account,
                            "candidate_id": candidate_id,
                            "final_candidate": _safe_copy(candidate),
                            "completed_handoff": _safe_copy(handoff),
                            "deep_bundle": _safe_copy(bundle),
                            "package_executed": False,
                            "render_executed": False,
                            "publish_executed": False,
                            "external_calls_executed": False,
                        }
                        record = {
                            "record_id": package_input["record_id"],
                            "account": account,
                            "candidate_id": candidate_id,
                            "status": "ready",
                            "reason_code": "completed_inputs_joined",
                            "missing_requirements": [],
                            "package_input": package_input,
                        }
                        package_inputs.append(copy.deepcopy(package_input))
            records.append(record)
            if record["status"] != "ready":
                missing_receipts.append(copy.deepcopy(record))

        ready_count = sum(record["status"] == "ready" for record in records)
        output_accounts[account] = {
            "selected_count": len(selected),
            "ready_count": ready_count,
            "blocked_count": len(records) - ready_count,
            "records": records,
        }

    selected_count = sum(bucket["selected_count"] for bucket in output_accounts.values())
    ready_count = len(package_inputs)
    status = "ready" if selected_count and ready_count == selected_count else ("partial" if ready_count else "blocked")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "reason_code": "all_inputs_ready" if status == "ready" else ("some_inputs_missing" if status == "partial" else "no_inputs_ready"),
        "max_per_account": bound,
        "selected_count": selected_count,
        "ready_count": ready_count,
        "blocked_count": len(missing_receipts),
        "accounts": output_accounts,
        "package_inputs": package_inputs,
        "missing_result_receipts": missing_receipts,
        "package_executed": False,
        "render_executed": False,
        "publish_executed": False,
        "external_calls_executed": False,
    }


__all__ = ["build_production_package_batch_inputs", "SCHEMA_VERSION"]
