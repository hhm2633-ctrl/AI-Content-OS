"""Capture real comments for final-selected Account B community candidates.

The command is intentionally explicit and bounded.  It accepts only recognized
final-selection shapes, filters to supported public community URLs, delegates
all network work to ``CommunityCommentCaptureProvider``, and writes a small
receipt.  Heavy HTML, screenshots, and comment artifacts remain owned by the
provider and its configured external deep-dive store.
"""

from __future__ import annotations

import argparse
from datetime import date as date_type
import json
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, Mapping
from urllib.parse import urlparse


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from modules.source_intake.account_deep_discovery_runner import (  # noqa: E402
    MAX_REQUESTS_PER_ACCOUNT,
    run_account_deep_discovery,
)


FINAL_SELECTION_SCHEMA = "cardnews_final_selection_v1"
INDEPENDENT_SELECTION_SCHEMA = "1.0"
RECEIPT_SCHEMA = "selected_community_comment_capture_receipt_v1"
SUPPORTED_HOSTS = {
    "pann.nate.com",
    "bobaedream.co.kr",
    "www.bobaedream.co.kr",
    "fmkorea.com",
    "www.fmkorea.com",
}


class SelectionError(ValueError):
    """Raised when the supplied selection is not a recognized final shape."""


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SelectionError("selection_file_not_found") from error
    except json.JSONDecodeError as error:
        raise SelectionError("selection_json_invalid") from error


def _validate_date(value: str) -> str:
    try:
        return date_type.fromisoformat(value).isoformat()
    except ValueError as error:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD") from error


def _bounded_positive(value: str, *, upper: int, label: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"{label} must be an integer") from error
    if number < 1 or number > upper:
        raise argparse.ArgumentTypeError(f"{label} must be between 1 and {upper}")
    return number


def _supported_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.hostname in SUPPORTED_HOSTS


def _candidate(
    raw: Mapping[str, Any],
    *,
    account: str,
    independent_shape: bool,
) -> Dict[str, Any]:
    candidate_id = _text(raw.get("id" if independent_shape else "candidate_id"))
    title = _text(raw.get("title"))
    category = _text(raw.get("category")) or _text(raw.get("category_id"))
    url_field = raw.get("urls" if independent_shape else "source_urls")
    source_urls = [
        _text(url)
        for url in (url_field if isinstance(url_field, list) else [])
        if _text(url)
    ]
    if not candidate_id or not title or not category:
        raise SelectionError("selected_candidate_missing_required_fields")
    return {
        "candidate_id": candidate_id,
        "account": account,
        "title": title,
        "category": category,
        "grade": _text(raw.get("grade")),
        "source_urls": source_urls,
    }


def _normalize_account_b_selection(
    payload: Any,
    *,
    date_str: str,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    if not isinstance(payload, Mapping):
        raise SelectionError("unrecognized_selection_shape")

    rows: Iterable[Any]
    shape: str
    independent_shape = False

    if payload.get("schema_version") == FINAL_SELECTION_SCHEMA:
        if payload.get("status") != "selected":
            raise SelectionError("final_selection_not_selected")
        accounts = payload.get("accounts")
        bucket = accounts.get("B") if isinstance(accounts, Mapping) else None
        rows = bucket.get("selected") if isinstance(bucket, Mapping) else None
        if not isinstance(rows, list):
            raise SelectionError("final_selection_missing_account_b_selected")
        shape = FINAL_SELECTION_SCHEMA
    elif (
        payload.get("schema_version") == INDEPENDENT_SELECTION_SCHEMA
        and _text(payload.get("account")).upper() == "B"
        and isinstance(payload.get("selected"), list)
    ):
        payload_date = _text(payload.get("date"))
        if payload_date and payload_date != date_str:
            raise SelectionError("independent_selection_date_mismatch")
        rows = payload["selected"]
        shape = "independent_selection_B_v1"
        independent_shape = True
    else:
        raise SelectionError("unrecognized_selection_shape")

    normalized = []
    seen = set()
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise SelectionError("selected_candidate_not_object")
        if not independent_shape:
            row_account = _text(raw.get("account")).upper()
            if row_account and row_account != "B":
                continue
            if raw.get("selection_status") == "not_selected":
                continue
        item = _candidate(raw, account="B", independent_shape=independent_shape)
        if item["candidate_id"] in seen:
            continue
        seen.add(item["candidate_id"])
        normalized.append(item)

    if not normalized:
        raise SelectionError("no_account_b_selected_candidates")

    eligible = []
    unsupported = []
    for item in normalized:
        supported = [url for url in item["source_urls"] if _supported_url(url)]
        rejected = [url for url in item["source_urls"] if url not in supported]
        if supported:
            eligible.append({**item, "source_urls": supported})
        else:
            unsupported.append(
                {
                    "candidate_id": item["candidate_id"],
                    "title": item["title"],
                    "reason_code": "no_supported_public_community_url",
                    "rejected_url_count": len(rejected),
                }
            )

    selection = {"accounts": {"B": {"selected": eligible}}}
    metadata = {
        "selection_shape": shape,
        "selected_account_b_count": len(normalized),
        "eligible_count": len(eligible),
        "unsupported_selected": unsupported,
        "eligible_candidates": [
            {
                "candidate_id": item["candidate_id"],
                "title": item["title"],
                "category": item["category"],
                "source_urls": list(item["source_urls"]),
            }
            for item in eligible
        ],
    }
    return selection, metadata


def _provider(*, max_comments: int, headed: bool) -> Any:
    try:
        from modules.source_intake.community_comment_capture_provider import (
            CommunityCommentCaptureProvider,
        )
    except ImportError as error:
        raise RuntimeError("community_comment_capture_provider_unavailable") from error
    return CommunityCommentCaptureProvider(
        max_comments=max_comments,
        headless=not headed,
    )


def _asset_references(assets: Any) -> list[Dict[str, Any]]:
    """Keep receipt references small; never duplicate HTML or comment text."""

    references = []
    for raw in assets if isinstance(assets, list) else []:
        if not isinstance(raw, Mapping):
            continue
        reference = {
            key: raw.get(key)
            for key in (
                "artifact_role",
                "artifact_path",
                "path",
                "screenshot_path",
                "source_url",
                "source_id",
                "is_real_comment",
                "identity_masked",
            )
            if raw.get(key) not in (None, "")
        }
        if reference:
            references.append(reference)
    return references


def _lightweight_execution(result: Mapping[str, Any]) -> Dict[str, Any]:
    account_b = result.get("accounts", {}).get("B", {})
    candidate_results = []
    for candidate in account_b.get("results", []):
        operations = []
        for operation in candidate.get("operations", []):
            assets = operation.get("assets")
            rejected = operation.get("rejected")
            operations.append(
                {
                    "operation": operation.get("operation"),
                    "artifact_role": operation.get("artifact_role"),
                    "status": operation.get("status"),
                    "network_used": bool(operation.get("network_used", False)),
                    "asset_count": len(assets) if isinstance(assets, list) else 0,
                    "rejected_count": len(rejected) if isinstance(rejected, list) else 0,
                    "asset_references": _asset_references(assets),
                }
            )
        candidate_results.append(
            {
                "candidate_id": candidate.get("candidate_id"),
                "title": candidate.get("title"),
                "category": candidate.get("category"),
                "operations": operations,
            }
        )
    return {
        "runner_schema_version": result.get("schema_version"),
        "runner_status": result.get("status"),
        "reason_code": result.get("reason_code"),
        "provider": result.get("provider"),
        "network_executed": bool(result.get("network_executed", False)),
        "requested": account_b.get("requested", 0),
        "unique_requested": account_b.get("unique_requested", 0),
        "executed": account_b.get("executed", 0),
        "skipped_over_limit": account_b.get("skipped_over_limit", []),
        "failure_count": len(result.get("failures", [])),
        "candidate_results": candidate_results,
    }


def _resolve_input(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (REPOSITORY_ROOT / path).resolve()


def _resolve_output(value: str | None, *, date_str: str) -> Path:
    if value:
        return _resolve_input(value)
    return (
        REPOSITORY_ROOT
        / "storage"
        / "source_intake"
        / date_str
        / "community_comment_capture_receipt.json"
    ).resolve()


def execute(args: argparse.Namespace) -> Dict[str, Any]:
    selection_path = _resolve_input(args.selection)
    selection, metadata = _normalize_account_b_selection(
        _read_json(selection_path),
        date_str=args.date,
    )
    list_only = bool(args.list_only)
    receipt: Dict[str, Any] = {
        "schema_version": RECEIPT_SCHEMA,
        "status": "listed" if list_only else "pending",
        "date": args.date,
        "account": "B",
        "selection_file": str(selection_path),
        **metadata,
        "limits": {
            "max_comments": args.max_comments,
            "max_per_account": args.max_per_account,
            "headed": bool(args.headed),
        },
        "external_heavy_store": "provider_configured_F_deep_dive_store",
        "execution_enabled": False,
        "network_executed": False,
        "login_automation": False,
        "posting": False,
        "link_issuance": False,
        "publishing": False,
    }

    if not list_only:
        if not metadata["eligible_count"]:
            receipt["status"] = "closed"
            receipt["reason_code"] = "no_supported_selected_account_b_urls"
        else:
            provider = _provider(max_comments=args.max_comments, headed=args.headed)
            result = run_account_deep_discovery(
                selection,
                provider,
                max_per_account=args.max_per_account,
            )
            lightweight = _lightweight_execution(result)
            receipt["status"] = lightweight["runner_status"] or "completed"
            receipt["execution_enabled"] = True
            receipt["network_executed"] = lightweight["network_executed"]
            receipt["execution"] = lightweight

    output_path = _resolve_output(args.output, date_str=args.date)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "status": receipt["status"],
        "account": "B",
        "selected": metadata["selected_account_b_count"],
        "eligible": metadata["eligible_count"],
        "unsupported": len(metadata["unsupported_selected"]),
        "network_executed": receipt["network_executed"],
        "output": str(output_path),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture real comments for final-selected Account B community URLs."
    )
    parser.add_argument("--selection", required=True)
    parser.add_argument("--date", required=True, type=_validate_date)
    parser.add_argument(
        "--max-comments",
        default=40,
        type=lambda value: _bounded_positive(value, upper=100, label="max-comments"),
    )
    parser.add_argument(
        "--max-per-account",
        default=MAX_REQUESTS_PER_ACCOUNT,
        type=lambda value: _bounded_positive(
            value,
            upper=MAX_REQUESTS_PER_ACCOUNT,
            label="max-per-account",
        ),
    )
    parser.add_argument("--output")
    parser.add_argument(
        "--dry-run",
        "--list-only",
        dest="list_only",
        action="store_true",
        help="List eligible selected candidates and write a no-network receipt.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the provider browser window; default capture is headless.",
    )
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    try:
        summary = execute(args)
    except (SelectionError, RuntimeError) as error:
        parser.exit(2, f"capture closed: {error}\n")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
