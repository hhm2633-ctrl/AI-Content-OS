"""Lightweight validator for BrandConnect relation/story shard outputs.

The validator is intentionally fail-closed:
- file read/parse issues never raise
- return payload always contains deterministic fields
- report-count agreement is checked explicitly
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, Dict, List, Tuple

SCHEMA_VERSION = "brandconnect_relation_story_shard_validation.v1"

REQUIRED_FIELDS = (
    "product_id",
    "product_name",
    "derived_terms",
    "season_context",
    "practical_topic",
    "short_story",
    "product_role",
    "blog_seed",
    "confidence",
    "fallback_used",
)


def _as_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _is_nonempty_text_or_mapping(value: Any) -> bool:
    if isinstance(value, str):
        return _as_text(value) != ""
    if isinstance(value, dict):
        return any(_as_text(item) for item in value.values())
    return False


def _append_error(
    errors: List[Dict[str, Any]],
    *,
    code: str,
    message: str,
    row_no: int | None = None,
    product_id: str = "",
) -> None:
    payload: Dict[str, Any] = {"code": code, "message": message}
    if row_no is not None:
        payload["row_no"] = row_no
    if product_id:
        payload["product_id"] = product_id
    errors.append(payload)


def _load_report(path: str) -> Tuple[Dict[str, Any] | None, List[Dict[str, Any]]]:
    errors: List[Dict[str, Any]] = []
    if not path:
        _append_error(errors, code="missing_report_path", message="report_path was not provided")
        return None, errors

    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        _append_error(errors, code="missing_report", message=str(exc))
        return None, errors
    except json.JSONDecodeError as exc:
        _append_error(errors, code="malformed_report", message=str(exc))
        return None, errors
    except OSError as exc:
        _append_error(errors, code="report_read_error", message=str(exc))
        return None, errors

    if not isinstance(payload, dict):
        _append_error(errors, code="malformed_report", message="report payload must be an object")
        return None, errors
    return payload, errors


def _load_rows(path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for row_no, raw_line in enumerate(handle, start=1):
                text = raw_line.strip()
                if not text:
                    continue
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError as exc:
                    _append_error(errors, code="jsonl_parse_error", message=str(exc), row_no=row_no)
                    continue
                if not isinstance(parsed, dict):
                    _append_error(errors, code="malformed_row", message="row is not a JSON object", row_no=row_no)
                    continue
                normalized = dict(parsed)
                normalized["_row_no"] = row_no
                rows.append(normalized)
    except FileNotFoundError as exc:
        _append_error(errors, code="missing_shard", message=str(exc))
    except OSError as exc:
        _append_error(errors, code="shard_read_error", message=str(exc))
    return rows, errors


def _validate_rows(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, int], int]:
    errors: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {
        "missing_required_field_count": 0,
        "under_30_violation_count": 0,
        "empty_practical_topic_count": 0,
        "story_count": 0,
        "practical_topic_count": 0,
        "duplicate_story_count": 0,
        "product_count": len(rows),
        "invalid_row_count": 0,
    }

    seen_product_ids: set[str] = set()
    seen_stories: Counter[str] = Counter()

    for row in rows:
        row_no = int(row.get("_row_no", 0))
        product_id = _as_text(row.get("product_id"))
        row_invalid = False

        missing_fields = [field for field in REQUIRED_FIELDS if field not in row]
        if missing_fields:
            counts["missing_required_field_count"] += 1
            row_invalid = True
            for field in missing_fields:
                _append_error(
                    errors,
                    code="missing_required_field",
                    message=f"missing required field: {field}",
                    row_no=row_no,
                    product_id=product_id,
                )

        if not product_id:
            _append_error(
                errors,
                code="invalid_product_id",
                message="product_id must be a non-empty string",
                row_no=row_no,
            )
            row_invalid = True
        elif product_id in seen_product_ids:
            _append_error(
                errors,
                code="duplicate_product_id",
                message="product_id must be unique",
                row_no=row_no,
                product_id=product_id,
            )
            row_invalid = True
        else:
            seen_product_ids.add(product_id)

        derived_terms = row.get("derived_terms")
        if not isinstance(derived_terms, list) or not derived_terms or any(
            not _as_text(item) for item in derived_terms
        ):
            _append_error(
                errors,
                code="invalid_derived_terms",
                message="derived_terms must be a non-empty list of strings",
                row_no=row_no,
                product_id=product_id,
            )
            row_invalid = True

        for field in ("product_name", "product_role"):
            if not _as_text(row.get(field)):
                _append_error(
                    errors,
                    code="invalid_required_string",
                    message=f"{field} must be a non-empty string",
                    row_no=row_no,
                    product_id=product_id,
                )
                row_invalid = True

        for field in ("season_context", "blog_seed"):
            if not _is_nonempty_text_or_mapping(row.get(field)):
                _append_error(
                    errors,
                    code="invalid_required_value",
                    message=f"{field} must be a non-empty string or non-empty object",
                    row_no=row_no,
                    product_id=product_id,
                )
                row_invalid = True

        practical_topic = _as_text(row.get("practical_topic"))
        if practical_topic:
            counts["practical_topic_count"] += 1
        else:
            counts["empty_practical_topic_count"] += 1
            row_invalid = True
            _append_error(
                errors,
                code="empty_practical_topic",
                message="practical_topic must be a non-empty string",
                row_no=row_no,
                product_id=product_id,
            )

        short_story = _as_text(row.get("short_story"))
        if short_story:
            counts["story_count"] += 1
            seen_stories[short_story] += 1
            if len(short_story) >= 30:
                counts["under_30_violation_count"] += 1
                row_invalid = True
                _append_error(
                    errors,
                    code="short_story_too_long",
                    message="short_story must be shorter than 30 characters",
                    row_no=row_no,
                    product_id=product_id,
                )
        else:
            row_invalid = True
            _append_error(
                errors,
                code="invalid_short_story",
                message="short_story must be a non-empty string",
                row_no=row_no,
                product_id=product_id,
            )

        confidence = _as_float(row.get("confidence"))
        if confidence is None or confidence < 0 or confidence > 1:
            _append_error(
                errors,
                code="invalid_confidence",
                message="confidence must be a number in [0, 1]",
                row_no=row_no,
                product_id=product_id,
            )
            row_invalid = True

        fallback_used = _as_bool(row.get("fallback_used"))
        if fallback_used is None:
            _append_error(
                errors,
                code="invalid_fallback_used",
                message="fallback_used must be boolean",
                row_no=row_no,
                product_id=product_id,
            )
            row_invalid = True

        if row_invalid:
            counts["invalid_row_count"] += 1

    counts["duplicate_story_count"] = sum(v - 1 for v in seen_stories.values() if v > 1)
    return errors, counts, len(rows) - counts["invalid_row_count"]


def _validate_report_counts(report: Dict[str, Any], metrics: Dict[str, int]) -> Tuple[bool, List[Dict[str, Any]]]:
    errors: List[Dict[str, Any]] = []
    checks = {
        "product_count": metrics["product_count"],
        "story_count": metrics["story_count"],
        "practical_topic_count": metrics["practical_topic_count"],
        "under_30_violation_count": metrics["under_30_violation_count"],
        "duplicate_story_count": metrics["duplicate_story_count"],
        "empty_practical_topic_count": metrics["empty_practical_topic_count"],
        "missing_required_field_count": metrics["missing_required_field_count"],
    }

    report_field_aliases = {
        "product_count": ("product_count", "source_product_count"),
        "under_30_violation_count": ("under_30_violation_count", "under_30_violations"),
        "duplicate_story_count": ("duplicate_story_count", "duplicate_short_story_count"),
        "missing_required_field_count": ("missing_required_field_count", "missing_required_field_rows"),
    }

    for field, actual in checks.items():
        candidates = report_field_aliases.get(field, (field,))
        expected = next((report.get(candidate) for candidate in candidates if candidate in report), None)
        if expected is None:
            continue
        try:
            expected_value = int(expected)
        except (TypeError, ValueError):
            _append_error(
                errors,
                code="invalid_report_field",
                message=f"{field} in report must be numeric",
            )
            return False, errors
        if expected_value != actual:
            _append_error(
                errors,
                code="report_count_mismatch",
                message=f"report {field}={expected_value} != computed {actual}",
            )

    coverage_valid = report.get("product_id_coverage_valid")
    if coverage_valid is None:
        validation_block = report.get("validation", {}) if isinstance(report.get("validation"), dict) else {}
        coverage_valid = (
            validation_block.get("source_id_coverage", validation_block.get("product_id_coverage_valid"))
        )
    if not bool(coverage_valid):
        _append_error(errors, code="report_product_id_coverage_invalid", message="product_id_coverage_valid is false")

    validation_result = None
    if isinstance(report.get("validation"), dict):
        validation_result = report["validation"].get("result")
    elif "validation_result" in report:
        validation_result = report.get("validation_result")

    if validation_result is not None and str(validation_result).upper() != "PASS":
        _append_error(errors, code="report_marked_invalid", message="report validation result is not PASS")

    product_count_mismatch = bool(
        any(item["code"] == "report_count_mismatch" for item in errors)
    )
    coverage_invalid = bool(
        any(item["code"] == "report_product_id_coverage_invalid" for item in errors)
    )

    if report.get("valid") is False:
        _append_error(
            errors,
            code="report_marked_invalid",
            message="report valid is false",
        )

    valid = not errors or not (product_count_mismatch or coverage_invalid or any(item["code"] == "report_marked_invalid" for item in errors))
    return valid, errors


def validate_relation_story_shard(*, shard_path: str, report_path: str | None = None) -> Dict[str, Any]:
    """Validate one shard + paired report. Return a deterministic fail-closed payload."""

    result: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "shard_path": shard_path,
        "report_path": report_path,
        "status": "closed",
        "valid": False,
        "errors": [],
        "warnings": [],
        "metrics": {
            "product_count": 0,
            "story_count": 0,
            "practical_topic_count": 0,
            "under_30_violation_count": 0,
            "duplicate_story_count": 0,
            "empty_practical_topic_count": 0,
            "missing_required_field_count": 0,
            "invalid_row_count": 0,
            "valid_row_count": 0,
            "report_count_agreement": False,
        },
    }

    rows, row_load_errors = _load_rows(shard_path)
    result["errors"].extend(row_load_errors)

    if any(error.get("code") in {"missing_shard", "shard_read_error"} for error in row_load_errors):
        return result

    row_errors, metrics, valid_row_count = _validate_rows(rows)
    result["errors"].extend(row_errors)

    report_payload, report_errors = _load_report(report_path)
    result["errors"].extend(report_errors)
    result["metrics"].update(metrics)
    result["metrics"]["valid_row_count"] = valid_row_count
    result["row_count"] = metrics["product_count"]

    if report_payload is not None and not report_errors:
        count_agreement, report_count_errors = _validate_report_counts(report_payload, metrics)
        result["errors"].extend(report_count_errors)
        result["metrics"]["report_count_agreement"] = bool(count_agreement)
    else:
        result["metrics"]["report_count_agreement"] = False

    # Fail on any structural/validation error.
    if result["errors"]:
        if all(item.get("code") in {"jsonl_parse_error", "malformed_row"} for item in result["errors"]) and len(rows) == 0:
            result["status"] = "closed"
        else:
            result["status"] = "invalid"
        result["valid"] = False
        return result

    result["status"] = "ok"
    result["valid"] = metrics["product_count"] > 0 and result["metrics"]["report_count_agreement"]
    result["report"] = report_payload
    return result


run_relation_story_shard_validation = validate_relation_story_shard
run_relation_story_shard_validator = validate_relation_story_shard

__all__ = [
    "SCHEMA_VERSION",
    "REQUIRED_FIELDS",
    "validate_relation_story_shard",
    "run_relation_story_shard_validation",
    "run_relation_story_shard_validator",
]
