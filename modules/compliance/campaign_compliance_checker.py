"""Campaign Compliance Phase 1 -- networkless sponsored-campaign checker.

Compares a sponsor/advertiser-supplied `CampaignRequirement` list against a
`ContentPackage` and reports, per requirement, whether it is satisfied
(`pass`), unmet (`fail`), unverifiable offline (`manual_review`), or irrelevant
(`not_applicable`) -- plus a package-wide `publish_ready` verdict.

No network call, browser automation, image OCR, LLM judgment, or real
publishing action is implemented anywhere in this module. Every check is a
deterministic, structural comparison over the fields already present in the
normalized input dicts (see `campaign_contract.py`).

Fail-closed discipline used throughout:
- An unresolved/ambiguous condition never becomes `pass` -- it becomes
  `manual_review` (structured evidence absent, e.g. `map_required`) or `fail`
  (a hard requirement, e.g. missing disclosure/rights/evidence).
- A campaign contract that is structurally invalid (not a dict/list, a dict
  missing/mistyping `requirements`, or a duplicate `requirement_id`) blocks
  the entire check before any requirement or content-package rule runs --
  see `_check`.
- An internal exception while evaluating one requirement, or an unrecognized
  `verification_mode` on one requirement, always blocks publishing overall --
  regardless of that requirement's own `required` flag -- because a check
  that could not actually run must never be treated as "this condition is
  merely optional and failed harmlessly".
- The outer `check()` call is wrapped again so a genuinely unexpected error
  still returns a valid, blocked compliance result instead of raising.
- Reason/messages are always fixed templates parameterized only by counts,
  thresholds, and field *names* -- raw link/body/caption content is never
  echoed back into the result, so a secret embedded in a URL or an exception
  message can never leak through this checker's output.

IMPORTANT (documented, not enforced by this module): `publish_ready: true`
from this checker is one of two required, AND-combined gates. It reflects
only this checker's own rules -- it is never, by itself, authorization to
actually publish. `modules/publishing/publishing_module.py`'s own gate
(`operations.publishing_blocked`, `manual_image_required`, etc.) is
independent and equally required. See
`docs/CAMPAIGN_COMPLIANCE_PHASE_1_CONTRACT.md` Section 6.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from modules.compliance.campaign_contract import (
    ALLOWED_VERIFICATION_MODES,
    normalize_campaign_contract,
    normalize_content_package,
)
from modules.compliance.compliance_result import (
    ALLOWED_RIGHTS_STATUSES,
    STATUS_FAIL,
    STATUS_MANUAL_REVIEW,
    STATUS_NOT_APPLICABLE,
    STATUS_PASS,
    build_compliance_result,
    build_contract_error_result,
    build_error_result,
)

# Co-occurrence based claim-risk scan (rule 7 + the bait/financial combo
# rule). Deliberately conservative/simple: a single shared keyword hit is
# enough to flag `manual_review`/blocking rather than trying to parse exact
# monetary meaning -- false positives just mean "a human should look", which
# is the safe direction for a networkless, non-LLM checker.
_CLAIM_KEYWORDS = (
    "수익", "매출", "수익률", "판매량", "순위", "효능", "할인", "적립",
    "환급", "배당", "이자", "원금보장", "보장수익", "수수료",
)
# NO-GO fix: spelled-out Korean amount/quantity words carry no ASCII digit at
# all (e.g. "댓글 남기면 수익 십만원"), so a digit-only numeric signal missed
# them entirely. Each of these is now sufficient on its own to satisfy BOTH
# the "claim keyword" and the "numeric signal" arm of `_claim_pattern_detected`
# -- a bare monetary/quantity figure is inherently claim-worthy, independent
# of whether a word like "수익"/"매출" also appears nearby.
_KOREAN_AMOUNT_QUANTITY_WORDS = (
    "십만원", "백만원", "천만원", "억원", "만원", "억", "천만",
    "한 개", "열 개", "백 개",
)
_ENGAGEMENT_BAIT_KEYWORDS = ("댓글", "디엠", "dm", "팔로우", "좋아요", "공유", "저장")
_ENGAGEMENT_BAIT_INDUCEMENTS = ("남기면", "주시면", "달면", "하면", "드립니다", "드려요", "이벤트", "추첨")
_DIGIT_PATTERN = re.compile(r"\d")

# NO-GO fix (rule 7): a conservative heuristic for OCR-misread-shaped numbers
# -- a digit directly adjacent to a commonly-confused letter (0/O, 1/l/I,
# 5/S, 8/B, 2/Z). This module never performs OCR itself; the point is to
# never let a suspicious digit/letter mix be *confidently* confirmed as a
# real number -- it degrades to `manual_review` instead.
_OCR_AMBIGUOUS_PATTERN = re.compile(r"[0-9][OolIiSsBbZz][0-9]|[0-9][OolIiSsBbZz]\b|\b[OolIiSsBbZz][0-9]")


class CampaignComplianceChecker:
    """Offline sponsored-campaign compliance checker (Phase 1)."""

    _CHECK_DISPATCH = {
        "required_keyword": "_check_keyword_presence",
        "brand_name": "_check_keyword_presence",
        "product_name": "_check_keyword_presence",
        "prohibited_keyword": "_check_prohibited_keyword",
        "disclosure_text": "_check_disclosure_text",
        "image_count": "_check_image_count",
        "video_required": "_check_video_required",
        "map_required": "_check_map_required",
        "link_required": "_check_link_required",
        "hashtag": "_check_hashtag",
        "publishing_window": "_check_publishing_window",
        "numeric_claim": "_check_numeric_claim",
        "manual_instruction": "_check_manual_instruction",
    }

    _ALLOWED_VERIFICATION_MODE_VALUES = frozenset({""}) | ALLOWED_VERIFICATION_MODES

    def check(self, campaign: Any, content_package: Any) -> Dict[str, Any]:
        """Main entry point. Never raises -- see module docstring."""
        package_id = content_package.get("package_id") if isinstance(content_package, dict) else None
        campaign_id = campaign.get("campaign_id") if isinstance(campaign, dict) else None

        try:
            return self._check(campaign, content_package)
        except Exception:
            return build_error_result(package_id, campaign_id)

    def _check(self, campaign: Any, content_package: Any) -> Dict[str, Any]:
        contract = normalize_campaign_contract(campaign)
        package = normalize_content_package(content_package)

        if not contract["contract_valid"]:
            # NO-GO fix (rules 1/2/13): a structurally invalid campaign
            # contract (wrong root type, missing/non-list `requirements`, or
            # a duplicate requirement_id) blocks the whole check before any
            # requirement or content-package rule ever runs.
            return build_contract_error_result(
                package["package_id"] or None,
                contract["campaign_id"],
                contract["contract_errors"],
            )

        requirement_results: List[Dict[str, Any]] = []
        blocking_reasons: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []
        manual_checklist: List[Dict[str, Any]] = []
        passed_count = failed_count = manual_review_count = 0

        for requirement in contract["requirements"]:
            status, reason, location, force_blocking = self._evaluate(requirement, package)

            requirement_results.append({
                "requirement_id": requirement["requirement_id"],
                "requirement_type": requirement["requirement_type"],
                "required": requirement["required"],
                "status": status,
                "reason": reason,
                "location": location,
            })

            if status == STATUS_PASS:
                passed_count += 1
            elif status == STATUS_FAIL:
                failed_count += 1
                is_blocking = (
                    requirement["required"]
                    or requirement["requirement_type"] == "disclosure_text"
                    or force_blocking
                )
                target = blocking_reasons if is_blocking else warnings
                target.append({
                    "code": "requirement_failed",
                    "requirement_id": requirement["requirement_id"],
                    "requirement_type": requirement["requirement_type"],
                    "message": reason,
                })
            elif status == STATUS_MANUAL_REVIEW:
                manual_review_count += 1
                manual_checklist.append({
                    "requirement_id": requirement["requirement_id"],
                    "requirement_type": requirement["requirement_type"],
                    "label": f"[{requirement['requirement_type']}] {requirement['requirement_id']} manual review required",
                    "reason": reason,
                })
            # STATUS_NOT_APPLICABLE: recorded in requirement_results only.

        self._apply_global_scans(package, blocking_reasons)

        return build_compliance_result(
            package_id=package["package_id"] or None,
            campaign_id=contract["campaign_id"],
            requirement_results=requirement_results,
            passed_count=passed_count,
            failed_count=failed_count,
            manual_review_count=manual_review_count,
            blocking_reasons=blocking_reasons,
            warnings=warnings,
            manual_checklist=manual_checklist,
        )

    def _evaluate(
        self, requirement: Dict[str, Any], package: Dict[str, Any]
    ) -> Tuple[str, str, Optional[List[str]], bool]:
        verification_mode = requirement["verification_mode"]

        if verification_mode not in self._ALLOWED_VERIFICATION_MODE_VALUES:
            # NO-GO fix (rule 15): an unrecognized verification_mode is a
            # per-requirement contract defect -- block, regardless of
            # `required`, rather than silently dispatching as if unset.
            return (
                STATUS_FAIL,
                f"Unsupported verification_mode '{verification_mode}'; this requirement is blocked.",
                None,
                True,
            )

        method_name = self._CHECK_DISPATCH.get(requirement["requirement_type"])

        if method_name is None:
            return (
                STATUS_MANUAL_REVIEW,
                f"Unsupported requirement_type '{requirement['requirement_type']}'; manual review required.",
                None,
                False,
            )

        try:
            status, reason, location = getattr(self, method_name)(requirement, package)
        except Exception:
            # NO-GO fix (rule 5): an internal error while checking a
            # requirement always blocks publishing overall, regardless of
            # that requirement's own `required` flag -- a check that could
            # not run must never be treated as a harmless optional failure.
            return STATUS_FAIL, "Requirement check failed internally; treated as fail-closed.", None, True

        return self._apply_verification_mode(requirement, status, reason, location, package)

    def _apply_verification_mode(
        self,
        requirement: Dict[str, Any],
        status: str,
        reason: str,
        location: Optional[List[str]],
        package: Dict[str, Any],
    ) -> Tuple[str, str, Optional[List[str]], bool]:
        """Apply `verification_mode`'s defined behavior on top of the
        requirement-type dispatch result (NO-GO fix, rule 14):

        - `""`/`"automatic"`: no change -- the dispatch result stands.
        - `"manual"`: any `pass`/`fail` automatic result is forced to
          `manual_review` -- the campaign explicitly wants a human to decide
          this condition regardless of what the automatic check found.
        - `"evidence_required"`: a `pass` can only survive if `source_reference`
          resolves to a complete structured evidence entry (same completeness
          rule as `numeric_claim`, generalized to any requirement type) -- if
          evidence is present and complete, the result becomes
          `manual_review` (never an unattended `pass`); if evidence is
          missing/incomplete, the result becomes a blocking `fail`.
        """
        mode = requirement["verification_mode"]

        if mode in ("", "automatic"):
            return status, reason, location, False

        if mode == "manual":
            if status in (STATUS_PASS, STATUS_FAIL):
                return (
                    STATUS_MANUAL_REVIEW,
                    f"verification_mode=manual forces human review (automatic result would have been '{status}').",
                    location,
                    False,
                )
            return status, reason, location, False

        if mode == "evidence_required":
            if status == STATUS_PASS:
                evidence = self._find_structured_evidence(requirement["source_reference"], package)
                if evidence is not None and self._evidence_is_complete(evidence):
                    return (
                        STATUS_MANUAL_REVIEW,
                        "verification_mode=evidence_required: a complete evidence reference is present; human confirmation is required before publish.",
                        location,
                        False,
                    )
                return (
                    STATUS_FAIL,
                    "verification_mode=evidence_required: no complete structured evidence reference was found for this requirement.",
                    location,
                    True,
                )
            return status, reason, location, False

        return status, reason, location, False  # unreachable: mode already validated in `_evaluate`

    # ------------------------------------------------------------------
    # Global, requirement-independent safety scans
    # ------------------------------------------------------------------

    def _apply_global_scans(self, package: Dict[str, Any], blocking_reasons: List[Dict[str, Any]]) -> None:
        rights_status = package["rights_status"]
        if rights_status not in ALLOWED_RIGHTS_STATUSES:
            blocking_reasons.append({
                "code": "package_rights_status_invalid",
                "requirement_id": None,
                "requirement_type": None,
                "message": "content_package.rights_status is missing or not in the allowed set; publishing is blocked.",
            })

        # NO-GO fix (rules 11/12): package-level rights_status alone must
        # never be treated as approving every asset. Each asset needs its own
        # rights_status, or a link to an approved upstream rights-manifest
        # entry -- checked independently here, per asset.
        for index, asset in enumerate(package["assets"]):
            if self._asset_rights_approved(asset, package["rights_manifest"]):
                continue
            asset_id = asset.get("asset_id") if isinstance(asset.get("asset_id"), str) and asset.get("asset_id") else f"index_{index}"
            blocking_reasons.append({
                "code": "asset_rights_status_missing",
                "requirement_id": None,
                "requirement_type": None,
                "message": f"asset '{asset_id}' has no valid rights_status and no approved upstream rights-manifest link; publishing is blocked.",
            })

        combined = self._combined_text(package)
        if self._claim_pattern_detected(combined) and self._bait_pattern_detected(combined):
            blocking_reasons.append({
                "code": "engagement_bait_financial_claim_combo",
                "requirement_id": None,
                "requirement_type": None,
                "message": (
                    "Comment/DM/follow-inducing language combined with a financial/numeric "
                    "claim was detected; publishing is blocked regardless of requirement list."
                ),
            })

    @staticmethod
    def _asset_rights_approved(asset: Dict[str, Any], rights_manifest: Dict[str, Dict[str, Any]]) -> bool:
        own_rights = str(asset.get("rights_status", "")).strip().lower()
        if own_rights in ALLOWED_RIGHTS_STATUSES:
            return True

        manifest_id = asset.get("upstream_rights_manifest_id")
        if not manifest_id:
            return False

        manifest_entry = rights_manifest.get(str(manifest_id))
        if not isinstance(manifest_entry, dict):
            return False

        return manifest_entry.get("rights_status") in ALLOWED_RIGHTS_STATUSES

    # ------------------------------------------------------------------
    # Per-requirement-type checks. Each returns (status, reason, location).
    # ------------------------------------------------------------------

    def _check_keyword_presence(
        self, requirement: Dict[str, Any], package: Dict[str, Any]
    ) -> Tuple[str, str, Optional[List[str]]]:
        candidates = self._candidates(requirement)
        if not candidates:
            return STATUS_NOT_APPLICABLE, "No keyword was specified to check.", None

        min_count = int(requirement["minimum_count"]) if requirement["minimum_count"] else 1
        combined_normalized = self._normalize(self._combined_text(package))
        total_matches = sum(combined_normalized.count(self._normalize(str(candidate))) for candidate in candidates)

        if total_matches < min_count:
            return STATUS_FAIL, "Required keyword was not found in title/body/caption/hashtags.", None
        return STATUS_PASS, "Required keyword is present.", None

    def _check_prohibited_keyword(
        self, requirement: Dict[str, Any], package: Dict[str, Any]
    ) -> Tuple[str, str, Optional[List[str]]]:
        candidates = requirement["prohibited_values"] or self._candidates(requirement)
        if not candidates:
            return STATUS_NOT_APPLICABLE, "No prohibited keyword was specified to check.", None

        locations = self._find_locations(candidates, package)
        if locations:
            return STATUS_FAIL, "A prohibited keyword was found.", locations
        return STATUS_PASS, "No prohibited keyword was found.", None

    def _check_disclosure_text(
        self, requirement: Dict[str, Any], package: Dict[str, Any]
    ) -> Tuple[str, str, Optional[List[str]]]:
        candidates = self._candidates(requirement)
        if not candidates:
            return STATUS_FAIL, "No disclosure phrase was specified; treated fail-closed.", None

        combined_normalized = self._normalize(self._combined_text(package))
        present = any(self._normalize(str(candidate)) in combined_normalized for candidate in candidates)
        if not present:
            return STATUS_FAIL, "Required advertising/sponsorship disclosure text is missing.", None
        return STATUS_PASS, "Advertising/sponsorship disclosure text is present.", None

    def _check_image_count(
        self, requirement: Dict[str, Any], package: Dict[str, Any]
    ) -> Tuple[str, str, Optional[List[str]]]:
        min_count = requirement["minimum_count"]
        max_count = requirement["maximum_count"]
        if min_count is None and max_count is None:
            return STATUS_NOT_APPLICABLE, "No image count constraint was specified.", None

        image_count = sum(
            1 for asset in package["assets"]
            if str(asset.get("type", "")).strip().lower() == "image"
        )

        if min_count is not None and image_count < min_count:
            return STATUS_FAIL, f"Image count {image_count} is below the required minimum {int(min_count)}.", None
        if max_count is not None and image_count > max_count:
            return STATUS_FAIL, f"Image count {image_count} exceeds the allowed maximum {int(max_count)}.", None
        return STATUS_PASS, f"Image count {image_count} satisfies the configured range.", None

    def _check_video_required(
        self, requirement: Dict[str, Any], package: Dict[str, Any]
    ) -> Tuple[str, str, Optional[List[str]]]:
        has_video = any(
            str(asset.get("type", "")).strip().lower() == "video" for asset in package["assets"]
        )
        want_video = requirement["expected_value"] is not False

        if want_video and not has_video:
            return STATUS_FAIL, "A required video asset is missing.", None
        if not want_video and has_video:
            return STATUS_FAIL, "A video asset is present but this requirement prohibits video.", None
        return STATUS_PASS, "Video condition is satisfied.", None

    def _check_map_required(
        self, requirement: Dict[str, Any], package: Dict[str, Any]
    ) -> Tuple[str, str, Optional[List[str]]]:
        # No structured "has_map"/place-tag field exists in the ContentPackage
        # input contract -- never guess; always route to a human (rule 5).
        return (
            STATUS_MANUAL_REVIEW,
            "Map/place inclusion cannot be verified offline (no structured evidence field); manual review required.",
            None,
        )

    def _check_link_required(
        self, requirement: Dict[str, Any], package: Dict[str, Any]
    ) -> Tuple[str, str, Optional[List[str]]]:
        candidates = self._candidates(requirement)
        min_count = int(requirement["minimum_count"]) if requirement["minimum_count"] else 1
        links = package["links"]

        if not candidates:
            if len(links) < min_count:
                return STATUS_FAIL, f"Fewer than the required {min_count} link(s) are present.", None
            return STATUS_PASS, "Required link count is satisfied.", None

        normalized_links = [self._normalize(link) for link in links]
        matched = [
            candidate for candidate in candidates
            if any(self._normalize(str(candidate)) in link for link in normalized_links)
        ]
        if len(matched) < min_count:
            return STATUS_FAIL, "A required link was not found.", None
        return STATUS_PASS, "Required link(s) are present.", None

    def _check_hashtag(
        self, requirement: Dict[str, Any], package: Dict[str, Any]
    ) -> Tuple[str, str, Optional[List[str]]]:
        candidates = self._candidates(requirement)
        if not candidates:
            return STATUS_NOT_APPLICABLE, "No required hashtag was specified.", None

        min_count = int(requirement["minimum_count"]) if requirement["minimum_count"] else 1
        normalized_hashtags = [self._normalize(tag) for tag in package["hashtags"]]
        matched = [
            candidate for candidate in candidates
            if any(self._normalize(str(candidate)) in tag for tag in normalized_hashtags)
        ]
        if len(matched) < min_count:
            return STATUS_FAIL, "A required hashtag is missing.", None
        return STATUS_PASS, "Required hashtag(s) are present.", None

    def _check_publishing_window(
        self, requirement: Dict[str, Any], package: Dict[str, Any]
    ) -> Tuple[str, str, Optional[List[str]]]:
        parsed = self._parse_tz_datetime(package["publishing_time"])
        if parsed is None:
            return STATUS_FAIL, "publishing_time must be a timezone-aware date/time value.", None

        expected = requirement["expected_value"]
        window_start = window_end = None

        if isinstance(expected, dict):
            raw_start = expected.get("window_start")
            raw_end = expected.get("window_end")

            if raw_start not in (None, ""):
                window_start = self._parse_tz_datetime(raw_start)
                if window_start is None:
                    # NO-GO fix (rule 3): an unparseable bound must never be
                    # silently ignored (which previously let the check pass).
                    return STATUS_FAIL, "publishing_window.window_start could not be parsed as a timezone-aware date/time value.", None

            if raw_end not in (None, ""):
                window_end = self._parse_tz_datetime(raw_end)
                if window_end is None:
                    return STATUS_FAIL, "publishing_window.window_end could not be parsed as a timezone-aware date/time value.", None

            if window_start is not None and window_end is not None and window_start > window_end:
                # NO-GO fix (rule 4): a campaign window whose own start is
                # after its own end is an invalid window, not a usable one.
                return STATUS_FAIL, "publishing_window.window_start is after window_end; the campaign window is invalid.", None

        if window_start is not None and parsed < window_start:
            return STATUS_FAIL, "publishing_time is before the allowed campaign window.", None
        if window_end is not None and parsed > window_end:
            return STATUS_FAIL, "publishing_time is after the allowed campaign window.", None
        return STATUS_PASS, "publishing_time is within the allowed window.", None

    def _check_numeric_claim(
        self, requirement: Dict[str, Any], package: Dict[str, Any]
    ) -> Tuple[str, str, Optional[List[str]]]:
        combined_text = self._combined_text(package)
        expected = requirement["expected_value"]

        if expected is not None:
            if self._normalize(str(expected)) not in self._normalize(combined_text):
                return STATUS_FAIL, "Expected numeric/financial claim was not found in the content.", None
            claim_source_text = str(expected)
        elif self._claim_pattern_detected(combined_text):
            claim_source_text = combined_text
        else:
            return STATUS_NOT_APPLICABLE, "No numeric/financial claim pattern was detected in the content.", None

        if self._looks_like_ocr_ambiguous_number(claim_source_text):
            # NO-GO fix (rule 7): never confidently confirm an OCR-ambiguous
            # digit pattern one way or the other -- always defer to a human.
            return (
                STATUS_MANUAL_REVIEW,
                "The numeric claim contains an OCR-ambiguous digit pattern; it cannot be confidently confirmed automatically.",
                None,
            )

        evidence = self._find_structured_evidence(requirement["source_reference"], package)

        if evidence is None:
            return STATUS_FAIL, "Numeric/financial/efficacy/sales/ranking/discount claim has no direct evidence reference.", None

        if not self._evidence_is_complete(evidence):
            # NO-GO fix (rules 8/9/10): an arbitrary/incomplete evidence
            # reference (missing source_url/locator, captured_at, verified_at,
            # or an unapproved rights_status) is never sufficient -- block.
            return (
                STATUS_FAIL,
                "The referenced evidence is missing a required field (source_url/locator, captured_at, verified_at, or an approved rights_status); the claim is blocked.",
                None,
            )

        # Rule: even a properly evidenced numeric claim never auto-publishes --
        # it always waits for human confirmation (no OCR/LLM judgment here).
        return (
            STATUS_MANUAL_REVIEW,
            "Numeric/financial claim has a complete evidence reference; human confirmation is required before publish.",
            None,
        )

    def _check_manual_instruction(
        self, requirement: Dict[str, Any], package: Dict[str, Any]
    ) -> Tuple[str, str, Optional[List[str]]]:
        return (
            STATUS_MANUAL_REVIEW,
            "manual_instruction requirements cannot be automatically verified; human review required.",
            None,
        )

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _candidates(requirement: Dict[str, Any]) -> List[str]:
        if requirement["allowed_values"]:
            return list(requirement["allowed_values"])
        if requirement["expected_value"] not in (None, "", [], {}) and isinstance(requirement["expected_value"], (str, int, float)):
            return [str(requirement["expected_value"])]
        return []

    @staticmethod
    def _normalize(text: Any) -> str:
        return re.sub(r"\s+", " ", str(text or "")).strip().lower()

    def _combined_text(self, package: Dict[str, Any]) -> str:
        return " ".join([
            package["title"],
            package["body"],
            package["caption"],
            " ".join(package["hashtags"]),
        ])

    def _find_locations(self, candidates: List[str], package: Dict[str, Any]) -> List[str]:
        normalized_candidates = [self._normalize(str(candidate)) for candidate in candidates if str(candidate).strip()]
        if not normalized_candidates:
            return []

        fields = {
            "title": package["title"],
            "body": package["body"],
            "caption": package["caption"],
            "hashtags": " ".join(package["hashtags"]),
            "links": " ".join(package["links"]),
        }

        found = []
        for field_name, text in fields.items():
            normalized_text = self._normalize(text)
            if any(candidate in normalized_text for candidate in normalized_candidates):
                found.append(field_name)
        return found

    @staticmethod
    def _find_structured_evidence(source_reference: Optional[str], package: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not source_reference:
            return None
        for entry in package["evidence_refs"]:
            if isinstance(entry, dict) and entry.get("evidence_id") == source_reference:
                return entry
        return None

    def _evidence_is_complete(self, evidence: Dict[str, Any]) -> bool:
        has_locator = bool(evidence.get("source_url")) or bool(evidence.get("locator"))
        captured_at = self._parse_tz_datetime(evidence.get("captured_at"))
        verified_at = self._parse_tz_datetime(evidence.get("verified_at"))
        rights_ok = evidence.get("rights_status") in ALLOWED_RIGHTS_STATUSES
        return has_locator and captured_at is not None and verified_at is not None and rights_ok

    @classmethod
    def _claim_pattern_detected(cls, text: str) -> bool:
        normalized = str(text or "").lower()
        has_amount_word = any(word in normalized for word in _KOREAN_AMOUNT_QUANTITY_WORDS)
        has_keyword = has_amount_word or any(keyword in normalized for keyword in _CLAIM_KEYWORDS)
        has_numeric_signal = has_amount_word or bool(_DIGIT_PATTERN.search(normalized))
        return has_keyword and has_numeric_signal

    @classmethod
    def _bait_pattern_detected(cls, text: str) -> bool:
        normalized = str(text or "").lower()
        has_bait_keyword = any(keyword in normalized for keyword in _ENGAGEMENT_BAIT_KEYWORDS)
        has_inducement = any(marker in normalized for marker in _ENGAGEMENT_BAIT_INDUCEMENTS)
        return has_bait_keyword and has_inducement

    @classmethod
    def _looks_like_ocr_ambiguous_number(cls, text: str) -> bool:
        return bool(_OCR_AMBIGUOUS_PATTERN.search(str(text or "")))

    @staticmethod
    def _parse_tz_datetime(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                return None
            return value.astimezone(timezone.utc)

        if isinstance(value, str) and value.strip():
            normalized = value.strip().replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(normalized)
            except ValueError:
                return None
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                return None
            return parsed.astimezone(timezone.utc)

        return None
