"""Fail-closed contract for independent, per-slide CardNews visual review.

This module validates a human visual-QA receipt.  It intentionally does not
open or render images: file existence, dimensions, and renderer success are
not visual approval.  The caller supplies the immutable slide manifest that
was rendered, including its SHA-256 values, and this gate binds the review to
that exact output set.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Sequence, Tuple


SCHEMA_VERSION = "cardnews_visual_qa_receipt_v1"
SCOPE_KINDS = {"representative", "batch"}
REQUIRED_FINDINGS = (
    "mobile_readability",
    "copy_readability",
    "copy_density_ok",
    "feed_caption_present",
    "content_not_blank",
    "image_is_primary",
    "subject_focus",
    "subject_crop_preserved",
    "comment_readability",
    "story_progression",
)
HARD_REQUIRED_FINDING_REASON_CODES = {
    "subject_crop_preserved": "visual_qa_subject_aware_layout",
    "feed_caption_present": "visual_qa_feed_caption_required",
    "comment_readability": "visual_qa_comment_readability_hard",
    "story_progression": "visual_qa_story_progression_order",
    "copy_density_ok": "visual_qa_copy_density_hard_limit",
    "image_is_primary": "visual_qa_image_is_primary",
}
PASS = "pass"
NOT_APPLICABLE = "not_applicable"
ALLOWED_FINDING_STATUSES = {PASS, NOT_APPLICABLE, "fail", "rejected", "blocked"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _objects(value: Any) -> List[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _strings(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [_text(item) for item in value if _text(item)]


def _failure(field: str, reason_code: str, detail: str) -> Dict[str, str]:
    return {"field": field, "reason_code": reason_code, "detail": detail}


def _slide_key(value: Mapping[str, Any]) -> Tuple[str, int] | None:
    candidate_id = _text(value.get("candidate_id"))
    page = value.get("page")
    if not candidate_id or isinstance(page, bool) or not isinstance(page, int) or page < 1:
        return None
    return candidate_id, page


def _normalized_hash(value: Any) -> str:
    result = _text(value).lower()
    return result if SHA256_RE.fullmatch(result) else ""


def assess_visual_qa_receipt(
    receipt: Any,
    expected_slides: Sequence[Mapping[str, Any]],
    *,
    expected_output_set_id: str | None = None,
    expected_representative_receipt_ids: Mapping[str, str] | None = None,
) -> Dict[str, Any]:
    """Validate independent visual approval for an exact rendered slide set.

    ``expected_slides`` is the controller-owned immutable manifest.  Each item
    must include ``account``, ``candidate_id``, ``page``, ``image_path`` and
    ``image_sha256``.  ``requires_comment_readability`` may be true for slides
    containing real-comment evidence.
    """

    value = receipt if isinstance(receipt, Mapping) else {}
    failures: List[Dict[str, str]] = []

    if _text(value.get("schema_version")) != SCHEMA_VERSION:
        failures.append(_failure("schema_version", "visual_qa_schema_invalid", SCHEMA_VERSION))

    for field in ("receipt_id", "output_set_id", "reviewed_at"):
        if not _text(value.get(field)):
            failures.append(_failure(field, f"visual_qa_{field}_missing", f"{field} is required"))
    if expected_output_set_id and _text(value.get("output_set_id")) != expected_output_set_id:
        failures.append(
            _failure(
                "output_set_id",
                "visual_qa_output_set_mismatch",
                "receipt must review the controller-authorized output set",
            )
        )

    maker = value.get("maker") if isinstance(value.get("maker"), Mapping) else {}
    reviewer = value.get("reviewer") if isinstance(value.get("reviewer"), Mapping) else {}
    maker_id = _text(maker.get("id"))
    reviewer_id = _text(reviewer.get("id"))
    if not maker_id:
        failures.append(_failure("maker.id", "visual_qa_maker_missing", "maker identity is required"))
    if not reviewer_id:
        failures.append(_failure("reviewer.id", "visual_qa_reviewer_missing", "reviewer identity is required"))
    if maker_id and reviewer_id and maker_id == reviewer_id:
        failures.append(
            _failure(
                "reviewer.id",
                "visual_qa_reviewer_not_independent",
                "the maker cannot approve the maker's own visual output",
            )
        )
    if reviewer.get("independent_from_maker") is not True:
        failures.append(
            _failure(
                "reviewer.independent_from_maker",
                "visual_qa_independence_not_attested",
                "independent reviewer attestation must be explicit",
            )
        )

    expected_by_key: Dict[Tuple[str, int], Mapping[str, Any]] = {}
    expected_accounts: set[str] = set()
    expected_candidates: set[str] = set()
    for position, slide in enumerate(expected_slides, start=1):
        if not isinstance(slide, Mapping):
            failures.append(
                _failure(
                    f"expected_slides[{position}]",
                    "visual_qa_expected_slide_invalid",
                    "expected slide manifest item must be an object",
                )
            )
            continue
        key = _slide_key(slide)
        account = _text(slide.get("account")).upper()
        path = _text(slide.get("image_path"))
        image_hash = _normalized_hash(slide.get("image_sha256"))
        if key is None or not account or not path or not image_hash:
            failures.append(
                _failure(
                    f"expected_slides[{position}]",
                    "visual_qa_expected_slide_incomplete",
                    "account, candidate_id, page, image_path and SHA-256 are required",
                )
            )
            continue
        if key in expected_by_key:
            failures.append(
                _failure(
                    f"expected_slides[{position}]",
                    "visual_qa_expected_slide_duplicate",
                    "candidate/page keys must be unique",
                )
            )
            continue
        expected_by_key[key] = slide
        expected_accounts.add(account)
        expected_candidates.add(key[0])

    scope = value.get("scope") if isinstance(value.get("scope"), Mapping) else {}
    scope_kind = _text(scope.get("kind"))
    scope_accounts = {item.upper() for item in _strings(scope.get("accounts"))}
    scope_candidates = set(_strings(scope.get("candidate_ids")))
    if scope_kind not in SCOPE_KINDS:
        failures.append(_failure("scope.kind", "visual_qa_scope_invalid", "use representative or batch"))
    if scope_accounts != expected_accounts:
        failures.append(
            _failure("scope.accounts", "visual_qa_scope_accounts_mismatch", "scope must match the reviewed slides")
        )
    if scope_candidates != expected_candidates:
        failures.append(
            _failure(
                "scope.candidate_ids",
                "visual_qa_scope_candidates_mismatch",
                "scope must match the reviewed slides",
            )
        )
    if scope_kind == "representative" and (
        len(expected_accounts) != 1 or len(expected_candidates) != 1
    ):
        failures.append(
            _failure(
                "scope",
                "visual_qa_representative_scope_not_single",
                "a representative receipt must cover exactly one account and one candidate",
            )
        )
    normalized_representative_receipts: Dict[str, str] = {}
    if scope_kind == "batch":
        representative_receipts = scope.get("representative_receipt_ids")
        representative_receipts = (
            representative_receipts if isinstance(representative_receipts, Mapping) else {}
        )
        missing_accounts = [
            account for account in sorted(expected_accounts) if not _text(representative_receipts.get(account))
        ]
        if missing_accounts:
            failures.append(
                _failure(
                    "scope.representative_receipt_ids",
                    "visual_qa_batch_representative_missing",
                    "approved representative receipt required for: " + ",".join(missing_accounts),
                )
            )
        normalized_representative_receipts = {
            account: _text(representative_receipts.get(account))
            for account in sorted(expected_accounts)
            if _text(representative_receipts.get(account))
        }
        if expected_representative_receipt_ids is not None:
            expected_ids = {
                _text(account).upper(): _text(receipt_id)
                for account, receipt_id in expected_representative_receipt_ids.items()
                if _text(account) and _text(receipt_id)
            }
            if normalized_representative_receipts != expected_ids:
                failures.append(
                    _failure(
                        "scope.representative_receipt_ids",
                        "visual_qa_batch_representative_mismatch",
                        "batch QA must bind the exact independently approved representative receipts",
                    )
                )

    reviewed_by_key: Dict[Tuple[str, int], Mapping[str, Any]] = {}
    for position, slide in enumerate(_objects(value.get("slides")), start=1):
        key = _slide_key(slide)
        field = f"slides[{position}]"
        if key is None:
            failures.append(_failure(field, "visual_qa_slide_identity_missing", "candidate_id and page are required"))
            continue
        if key in reviewed_by_key:
            failures.append(_failure(field, "visual_qa_slide_duplicate", "each slide may be reviewed only once"))
            continue
        reviewed_by_key[key] = slide
        expected = expected_by_key.get(key)
        if expected is None:
            failures.append(_failure(field, "visual_qa_unexpected_slide", "slide is not in the authorized manifest"))
            continue

        reviewed_path = _text(slide.get("image_path"))
        if not reviewed_path or reviewed_path != _text(expected.get("image_path")):
            failures.append(
                _failure(f"{field}.image_path", "visual_qa_image_path_mismatch", "review must bind to the rendered path")
            )
        reviewed_hash = _normalized_hash(slide.get("image_sha256"))
        if not reviewed_hash:
            failures.append(
                _failure(f"{field}.image_sha256", "visual_qa_image_hash_missing", "valid SHA-256 is required")
            )
        elif reviewed_hash != _normalized_hash(expected.get("image_sha256")):
            failures.append(
                _failure(
                    f"{field}.image_sha256",
                    "visual_qa_image_hash_mismatch",
                    "reviewed bytes differ from the authorized manifest",
                )
            )

        findings = slide.get("findings") if isinstance(slide.get("findings"), Mapping) else {}
        for finding_name in REQUIRED_FINDINGS:
            if finding_name == "feed_caption_present":
                status = "pass" if _text(value.get("feed_caption")) else "fail"
            else:
                status = _text(findings.get(finding_name))
            finding_field = f"{field}.findings.{finding_name}"
            if status not in ALLOWED_FINDING_STATUSES:
                failures.append(
                    _failure(finding_field, "visual_qa_finding_missing", "explicit visual finding is required")
                )
                continue
            if finding_name == "comment_readability" and expected.get("requires_comment_readability") is True:
                if status == NOT_APPLICABLE:
                    failures.append(
                        _failure(
                            finding_field,
                            "visual_qa_comment_readability_required",
                            "a comment slide cannot mark comment readability not applicable",
                        )
                    )
                    continue
            if finding_name != "comment_readability" and status == NOT_APPLICABLE:
                failures.append(
                    _failure(
                        finding_field,
                        "visual_qa_core_finding_not_applicable",
                        "copy, content, subject crop, mobile readability and story progression must be judged",
                    )
                )
                continue
            if status in {"fail", "rejected", "blocked"}:
                reason_code = HARD_REQUIRED_FINDING_REASON_CODES.get(
                    finding_name, "visual_qa_finding_rejected"
                )
                failures.append(
                    _failure(
                        finding_field,
                        reason_code,
                        f"{finding_name} was {status}",
                    )
                )
                if reason_code != "visual_qa_finding_rejected":
                    failures.append(
                        _failure(
                            finding_field,
                            "visual_qa_finding_rejected",
                            f"{finding_name} was {status}",
                        )
                    )

    for key in sorted(set(expected_by_key) - set(reviewed_by_key)):
        failures.append(
            _failure(
                f"slides[{key[0]}:{key[1]}]",
                "visual_qa_slide_missing",
                "every authorized slide needs an independent visual finding",
            )
        )

    decision = _text(value.get("decision"))
    if decision != "approve":
        failures.append(
            _failure("decision", "visual_qa_not_approved", "only an explicit approve decision can pass")
        )

    unique: List[Dict[str, str]] = []
    seen: set[Tuple[str, str]] = set()
    for failure in failures:
        key = (failure["field"], failure["reason_code"])
        if key not in seen:
            seen.add(key)
            unique.append(failure)

    passed = not unique
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed" if passed else "blocked",
        "visual_qa_passed": passed,
        "scope_kind": scope_kind or None,
        "receipt_id": _text(value.get("receipt_id")) or None,
        "output_set_id": _text(value.get("output_set_id")) or None,
        "representative_receipt_ids": normalized_representative_receipts,
        "expected_slide_count": len(expected_by_key),
        "reviewed_slide_count": len(reviewed_by_key),
        "reviewer_independent": bool(
            reviewer_id and maker_id and reviewer_id != maker_id and reviewer.get("independent_from_maker") is True
        ),
        "failure_count": len(unique),
        "failures": unique,
        "dimensions_are_visual_approval": False,
        "execution": {
            "render": False,
            "publish": False,
            "link_issuance": False,
            "external_calls": False,
        },
    }


validate_visual_qa_receipt = assess_visual_qa_receipt


__all__ = [
    "SCHEMA_VERSION",
    "REQUIRED_FINDINGS",
    "assess_visual_qa_receipt",
    "validate_visual_qa_receipt",
]
