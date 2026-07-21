"""Affiliate Revenue Router Phase 1 -- networkless product-affiliate router.

Compares a `RoutingRequest`'s candidate `AffiliateProgram`s and
`MerchantOffer`s and returns which (program, offer) pairings are eligible,
need manual review, or are rejected, plus a `TrackingLinkRequest` and
disclosure text for every *eligible* pairing (manual-review pairings get a
`manual_actions` entry instead -- see NO-GO fixes below).

No network call, no login, no credential/key loading, no real affiliate
link/deep-link/sub-id generation anywhere in this module -- every
`TrackingLinkRequest` this router builds carries the input's own
already-supplied `canonical_url` and an explicit
`tracking_link_generated: false`. `lead_cpa` programs are always blocked
(rule 1/8); a network's declared `api_status` is capped by the Phase-1
capability ceiling in `affiliate_policy_gate.py`, never raised above it.

NO-GO fixes in this pass:
- The old full Cartesian program*offer join is removed. An offer is only ever
  evaluated against the *one* `AffiliateProgram` whose `(network_id,
  program_id, merchant_id)` it exactly references -- a missing or
  non-matching back-reference rejects that offer outright instead of pairing
  it with an unrelated program.
- `candidate_id` includes `network_id`, `program_id`, `merchant_id`, and
  `offer_id`.
- Manual-review candidates get a `manual_actions` entry, never a
  `TrackingLinkRequest` or a disclosure text (only `eligible` candidates get
  those).
- A structurally invalid request (duplicate program/offer id, an
  oversized `candidate_programs`/`candidate_offers` list, or too many
  evaluated pairs) is rejected as a whole before any evaluation runs.
- `request_id` is replaced with an irreversible opaque token in the output
  whenever it looks like it might carry a secret/JWT/path (see
  `affiliate_safety_utils.make_id_output_safe`).
- `policy_receipts` never includes an unsafe/credential-bearing URL.

Fail-closed discipline mirrors `modules/compliance/campaign_compliance_checker.py`:
a single (program, offer) pairing's evaluation raising an exception degrades
that one pairing to `rejected`, never crashing the whole run; the outer
`route()` call is wrapped again so a genuinely unexpected error still returns
a valid, blocked routing result instead of raising. Reason messages are fixed
templates parameterized only by codes/field names/durations -- raw URL/offer
content and exception text are never echoed into the result.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from modules.affiliate.affiliate_contract import normalize_routing_request
from modules.affiliate.affiliate_policy_gate import effective_api_status, evaluate_offer, evaluate_pairing, evaluate_program
from modules.affiliate.affiliate_result import (
    STATUS_ELIGIBLE,
    STATUS_MANUAL_REVIEW,
    build_contract_error_result,
    build_error_result,
    build_routing_result,
    combine_status,
)
from modules.affiliate.affiliate_safety_utils import is_safe_public_url, make_id_output_safe, normalize_id_component, parse_tz_datetime

# NO-GO fix (rules 19/20): explicit Phase 1 input-size limits. Exceeding any
# of these blocks the whole request with a structured reason rather than
# evaluating a partial/truncated set silently.
MAX_PROGRAMS = 50
MAX_OFFERS = 200
MAX_EVALUATED_PAIRS = 200


class AffiliateRevenueRouter:
    """Offline Phase 1 affiliate program/offer router. See module docstring."""

    def route(self, request: Any) -> Dict[str, Any]:
        """Main entry point. Never raises -- see module docstring."""
        raw_request_id = request.get("request_id") if isinstance(request, dict) else None

        try:
            return self._route(request, raw_request_id)
        except Exception:
            return build_error_result(self._safe_request_id(raw_request_id))

    def _route(self, request: Any, raw_request_id: Any) -> Dict[str, Any]:
        normalized = normalize_routing_request(request)
        request_id = self._safe_request_id(normalized["request_id"] or None)

        if normalized["contract_errors"]:
            return build_contract_error_result(request_id, normalized["contract_errors"])

        programs = normalized["candidate_programs"]
        offers = normalized["candidate_offers"]

        if len(programs) > MAX_PROGRAMS:
            return build_contract_error_result(request_id, [f"candidate_programs exceeds the maximum of {MAX_PROGRAMS}."])
        if len(offers) > MAX_OFFERS:
            return build_contract_error_result(request_id, [f"candidate_offers exceeds the maximum of {MAX_OFFERS}."])
        if len(offers) > MAX_EVALUATED_PAIRS:
            return build_contract_error_result(request_id, [f"evaluated (program, offer) pairs would exceed the maximum of {MAX_EVALUATED_PAIRS}."])

        current_time = parse_tz_datetime(normalized["current_time"])
        if current_time is None:
            return build_routing_result(
                request_id=request_id,
                status="blocked",
                eligible_candidates=[],
                rejected_candidates=[],
                manual_review_candidates=[],
                tracking_link_requests=[],
                disclosure_texts=[],
                manual_actions=[],
                blocking_reasons=[{
                    "code": "current_time_missing_or_invalid",
                    "message": "RoutingRequest.current_time must be a timezone-aware date/time value.",
                }],
                warnings=[],
                policy_receipts=[],
            )
        normalized["current_time"] = current_time

        program_index: Dict[Tuple[str, str, str], Dict[str, Any]] = {
            (program["network_id"], program["program_id"], program["merchant_id"]): program
            for program in programs
        }

        policy_receipts: List[Dict[str, Any]] = [self._build_policy_receipt(program) for program in programs]
        program_evaluations: Dict[Tuple[str, str, str], Tuple[str, List[Dict[str, str]]]] = {}
        for key, program in program_index.items():
            try:
                program_evaluations[key] = evaluate_program(program, normalized)
            except Exception:
                program_evaluations[key] = ("rejected", [{"scope": "program", "code": "program_evaluation_error", "message": "Program evaluation failed internally; treated as fail-closed."}])

        eligible_candidates: List[Dict[str, Any]] = []
        rejected_candidates: List[Dict[str, Any]] = []
        manual_review_candidates: List[Dict[str, Any]] = []

        for offer in offers:
            ref_key = (offer["network_id"], offer["program_id"], offer["merchant_id"])

            if not all(ref_key):
                rejected_candidates.append(self._build_orphan_candidate(offer, "offer_missing_back_reference", "network_id, program_id, and merchant_id are all required on every MerchantOffer."))
                continue

            program = program_index.get(ref_key)
            if program is None:
                rejected_candidates.append(self._build_orphan_candidate(offer, "no_matching_program_reference", "No candidate_programs entry has this exact (network_id, program_id, merchant_id) triple."))
                continue

            try:
                offer_status, offer_reasons, image_usage_approved = evaluate_offer(offer, normalized)
            except Exception:
                offer_status, offer_reasons, image_usage_approved = ("rejected", [{"scope": "offer", "code": "offer_evaluation_error", "message": "Offer evaluation failed internally; treated as fail-closed."}], False)

            program_status, program_reasons = program_evaluations[ref_key]

            try:
                pairing_status, pairing_reasons = evaluate_pairing(program, offer)
            except Exception:
                pairing_status, pairing_reasons = "rejected", [{"scope": "pairing", "code": "pairing_evaluation_error", "message": "Pairing evaluation failed internally; treated as fail-closed."}]

            combined_status = combine_status(program_status, offer_status, pairing_status)
            combined_reasons = program_reasons + offer_reasons + pairing_reasons

            candidate = {
                "candidate_id": self._candidate_id(program["network_id"], program["program_id"], program["merchant_id"], offer["offer_id"]),
                "network_id": program["network_id"],
                "program_id": program["program_id"],
                "merchant_id": program["merchant_id"],
                "offer_id": offer["offer_id"],
                "status": combined_status,
                "reasons": combined_reasons,
                "commission_value": offer["commission_value"],
                "image_usage_approved": image_usage_approved,
            }

            if combined_status == STATUS_ELIGIBLE:
                eligible_candidates.append(candidate)
            elif combined_status == STATUS_MANUAL_REVIEW:
                manual_review_candidates.append(candidate)
            else:
                rejected_candidates.append(candidate)

        eligible_candidates.sort(key=self._eligible_sort_key)
        manual_review_candidates.sort(key=self._id_sort_key)
        rejected_candidates.sort(key=self._id_sort_key)

        offers_by_id = {offer["offer_id"]: offer for offer in offers}
        tracking_link_requests: List[Dict[str, Any]] = []
        disclosure_texts: List[Dict[str, Any]] = []
        manual_actions: List[Dict[str, Any]] = []

        # NO-GO fix (rules 15/16): only `eligible` candidates get a
        # TrackingLinkRequest/disclosure text. `manual_review` candidates get
        # a `manual_actions` entry instead -- never a tracking artifact.
        for candidate in eligible_candidates:
            program = program_index.get((candidate["network_id"], candidate["program_id"], candidate["merchant_id"]))
            offer = offers_by_id.get(candidate["offer_id"])
            if program is None or offer is None:
                continue
            tracking_link_requests.append(self._build_tracking_link_request(request_id, candidate, program, offer))
            disclosure_texts.append(self._build_disclosure_text(candidate, program))

        for candidate in manual_review_candidates:
            manual_actions.append(self._build_manual_action(candidate))

        return build_routing_result(
            request_id=request_id,
            status="routed",
            eligible_candidates=eligible_candidates,
            rejected_candidates=rejected_candidates,
            manual_review_candidates=manual_review_candidates,
            tracking_link_requests=tracking_link_requests,
            disclosure_texts=disclosure_texts,
            manual_actions=manual_actions,
            blocking_reasons=[],
            warnings=[],
            policy_receipts=policy_receipts,
            disclosure_policy_verified=normalized["disclosure_policy_verified"],
            human_approval=normalized["human_approval"],
        )

    @staticmethod
    def _safe_request_id(value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        return make_id_output_safe(value)

    @staticmethod
    def _candidate_id(network_id: str, program_id: str, merchant_id: str, offer_id: str) -> str:
        return ":".join(
            normalize_id_component(part) for part in (network_id, program_id, merchant_id, offer_id)
        )

    def _build_orphan_candidate(self, offer: Dict[str, Any], code: str, message: str) -> Dict[str, Any]:
        return {
            "candidate_id": self._candidate_id(offer["network_id"], offer["program_id"], offer["merchant_id"], offer["offer_id"]),
            "network_id": offer["network_id"] or None,
            "program_id": offer["program_id"] or None,
            "merchant_id": offer["merchant_id"] or None,
            "offer_id": offer["offer_id"],
            "status": "rejected",
            "reasons": [{"scope": "offer", "code": code, "message": message}],
            "commission_value": offer["commission_value"],
            "image_usage_approved": False,
        }

    @staticmethod
    def _eligible_sort_key(candidate: Dict[str, Any]) -> Tuple[int, float, str, str, str, str]:
        commission = candidate["commission_value"]
        has_commission = commission is not None
        return (
            0 if has_commission else 1,
            -(commission if has_commission else 0.0),
            candidate["network_id"] or "",
            candidate["program_id"] or "",
            candidate["merchant_id"] or "",
            candidate["offer_id"],
        )

    @staticmethod
    def _id_sort_key(candidate: Dict[str, Any]) -> Tuple[str, str, str, str]:
        return candidate["network_id"] or "", candidate["program_id"] or "", candidate["merchant_id"] or "", candidate["offer_id"]

    @staticmethod
    def _safe_url_for_receipt(url: Optional[str]) -> Optional[str]:
        # NO-GO fix (rule 13): never surface an unsafe/credential-bearing URL
        # in an audit artifact, even for a program that ends up rejected.
        if not url:
            return None
        if is_safe_public_url(url):
            return url
        return "***REDACTED_UNSAFE_URL***"

    def _build_policy_receipt(self, program: Dict[str, Any]) -> Dict[str, Any]:
        effective_status, ceiling_applied = effective_api_status(program["network_id"], program["api_status"])
        checked_at = parse_tz_datetime(program["policy_checked_at"])

        return {
            "network_id": program["network_id"],
            "program_id": program["program_id"],
            "merchant_id": program["merchant_id"],
            "declared_api_status": program["api_status"],
            "effective_api_status": effective_status,
            "capability_ceiling_applied": ceiling_applied,
            "policy_version": program["policy_version"],
            "policy_evidence_url": self._safe_url_for_receipt(program["policy_evidence_url"]),
            "policy_checked_at": checked_at.isoformat() if checked_at else None,
        }

    def _build_tracking_link_request(
        self, request_id: Optional[str], candidate: Dict[str, Any], program: Dict[str, Any], offer: Dict[str, Any]
    ) -> Dict[str, Any]:
        safe_request_id = normalize_id_component(request_id or "affiliate_request")
        return {
            "request_id": f"{safe_request_id}:{candidate['candidate_id']}",
            "candidate_id": candidate["candidate_id"],
            "network_id": program["network_id"],
            "program_id": program["program_id"],
            "merchant_id": program["merchant_id"],
            "offer_id": offer["offer_id"],
            "destination_url": offer["canonical_url"],
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "link_generation_method": "official_ui_human_required",
            "tracking_link_generated": False,
            "notes": (
                "Phase 1 does not call any network API and does not generate a real affiliate/"
                "deep link or sub-id. A human must issue the actual tracking link in the "
                "network's official UI/dashboard before publishing."
            ),
        }

    @staticmethod
    def _build_disclosure_text(candidate: Dict[str, Any], program: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "candidate_id": candidate["candidate_id"],
            "network_id": program["network_id"],
            "program_id": program["program_id"],
            "merchant_id": program["merchant_id"],
            "text": (
                f"본 콘텐츠는 제휴 프로그램({program['network_id']}/{program['program_id']})을 통해 "
                "경제적 이해관계(수수료 등)가 발생할 수 있는 콘텐츠입니다. 구매/신청 시 작성자에게 "
                "수수료가 지급될 수 있습니다."
            ),
            "placement": "before_or_near_first_affiliate_link",
        }

    @staticmethod
    def _build_manual_action(candidate: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "candidate_id": candidate["candidate_id"],
            "network_id": candidate["network_id"],
            "program_id": candidate["program_id"],
            "merchant_id": candidate["merchant_id"],
            "offer_id": candidate["offer_id"],
            "action_required": (
                "Resolve every condition listed in `reasons` (e.g. confirm enrollment evidence, "
                "recheck policy freshness) before this candidate can become eligible. No tracking "
                "link or disclosure text is generated for a manual-review candidate."
            ),
            "reasons": candidate["reasons"],
        }
