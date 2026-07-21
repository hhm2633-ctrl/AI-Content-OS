"""Commerce Phase 2A — Product Contract Loader.

Loads the per-platform field contract (required / optional / conditional fields,
blocking-reason codes, and Phase1-field -> platform-field mapping hints) that
`payload_builder.py` and `schema_validator.py` use to build and validate a
dry-run payload.

Design basis: `docs/RESEARCH/COMMERCE/SMARTSTORE_PRODUCT_CONTRACT.md` and
`docs/RESEARCH/COMMERCE/COUPANG_PRODUCT_CONTRACT.md` (research pass, 2026-07-11).
Every field below traces to a specific evidence tier recorded in those documents
-- CONFIRMED (official channel, search-synthesis only), INFERRED, or UNKNOWN.
Nothing here is invented; fields whose exact platform key name is UNKNOWN keep an
explicit `platform_field: null` and a `TODO` marker rather than a guessed name.

This module performs no I/O beyond an optional read of
`config/commerce/marketplaces.json` (falls back to the built-in contract below if
that file is missing/invalid -- never raises).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Field classification: "required" | "optional" | "conditional".
# `platform_field` is the best-evidenced platform payload key name, or None when
# the exact key name is UNKNOWN per the research docs (never guessed).
# `evidence_tier` mirrors the research docs' own tagging so a human reviewer can
# see at a glance which fields are safe to trust and which need re-verification.
#
# `phase1_source` is a dotted path resolved against the actual CommerceModule
# (Phase 1) result dict by `payload_builder.py`. CONFIRMED by direct reading of
# `modules/commerce/commerce_module.py::run()`/`_package()`/`_detail()` (2026-07-11)
# -- NOT from docs/COMMERCE_PHASE_1_CONTRACT.md's *request*-schema description,
# which documents Phase 1's *input* shape, not its *output* shape. The real
# output has exactly two useful roots:
#   - "platform_packages.{platform}.<field>" -- product_name / search_keywords /
#     options / detail_description / notice_information (a dict keyed by
#     manufacturer/country_of_origin/model_name) / manual_upload_text_path.
#     `{platform}` is substituted with the actual platform name at build time.
#   - "detail_page.<section>.items" / "detail_page.<section>.text" -- a
#     platform-agnostic (shared across smartstore/coupang) rendered-content
#     dict (headline/problem/benefits/features/specifications/usage/cautions/faq/cta).
# CONFIRMED CONTRACT GAP: Phase 1's output has NO discrete category / price /
# stock / shipping / seller(vendor) / brand field anywhere in the result dict.
# These are validated internally (gated into `accepted`) but only ever get
# woven into rendered text (`product_name`, `detail_description`) or dropped
# entirely (price/stock are validated but never rendered anywhere) -- they are
# structurally unavailable to a payload builder today. A `None` phase1_source
# below records exactly this, not a guess or an oversight. Closing this gap
# requires extending Phase 1's own result shape (Phase 2B, CTO GATE), which is
# out of scope for this Sprint (WorkflowEngine/module-structure changes are
# explicitly disallowed for the Phase 2A skeleton).
SMARTSTORE_CONTRACT: Dict[str, Dict[str, Any]] = {
    "product_name": {
        "classification": "required",
        "phase1_source": "platform_packages.{platform}.product_name",
        "platform_field": "originProduct.name",
        "evidence_tier": "CONFIRMED (official channel, search-synthesis only)",
        "blocked_reason_code": "missing_required_field",
    },
    "category": {
        "classification": "required",
        "phase1_source": None,
        "platform_field": "originProduct.leafCategoryId",
        "evidence_tier": "CONFIRMED (official channel, search-synthesis only)",
        "blocked_reason_code": "platform_category_metadata_unresolved",
        # TODO(Phase 1 contract gap): CommerceModule's result has no discrete
        # category field -- category only ever appears folded into the
        # rendered `product_name` string. TODO(Phase 2B): leafCategoryId must
        # also be resolved live via the category lookup API before every
        # submission -- never cached across runs, even once Phase 1 exposes it.
        "condition": "resolved leaf category id required, not a category label",
    },
    "price": {
        "classification": "required",
        "phase1_source": None,
        "platform_field": "originProduct.salePrice",
        "evidence_tier": "CONFIRMED (official channel, search-synthesis only)",
        "blocked_reason_code": "stale_volatile_fact",
        # TODO(Phase 1 contract gap): price facts can be submitted to Phase 1
        # (as a commercial_facts["price"] entry) and pass validation, but
        # CommerceModule never renders/exposes an accepted price anywhere in
        # its result dict -- there is no output path to read it from today.
        "condition": "must be re-checked for freshness at build time, not just Phase 1 generation time",
    },
    "stock": {
        "classification": "required",
        "phase1_source": None,
        "platform_field": "originProduct.stockQuantity",
        "evidence_tier": "INFERRED (market_naver.md, third-party reverse-engineered)",
        "blocked_reason_code": "stale_volatile_fact",
        # TODO(Phase 1 contract gap): same gap as price -- validated but never exposed.
        "condition": "same freshness condition as price",
    },
    "detail_description": {
        "classification": "required",
        "phase1_source": "platform_packages.{platform}.detail_description",
        "platform_field": "originProduct.detailContent",
        "evidence_tier": "CONFIRMED (official channel, search-synthesis only)",
        "blocked_reason_code": "missing_required_field",
        "condition": "non-empty HTML string, JSON-significant characters escaped",
    },
    "notice_information": {
        "classification": "conditional",
        "phase1_source": "platform_packages.{platform}.notice_information",
        "platform_field": "detailAttribute.productInfoProvidedNotice",
        "evidence_tier": "INFERRED (market_naver.md); major-category id requirement CONFIRMED (official channel) per PLATFORM_API_EVIDENCE_MATRIX.md",
        "blocked_reason_code": "notice_information_incomplete",
        "condition": "required whenever the resolved MAJOR (top-level) category id has a defined notice template -- NOT the leaf category id used for registration itself",
    },
    "country_of_origin": {
        "classification": "required",
        "phase1_source": "platform_packages.{platform}.notice_information.country_of_origin",
        "platform_field": "detailAttribute.originAreaInfo",
        "evidence_tier": "INFERRED (market_naver.md)",
        "blocked_reason_code": "notice_information_incomplete",
    },
    "shipping": {
        "classification": "required",
        "phase1_source": None,
        "platform_field": "originProduct.deliveryInfo",
        "evidence_tier": "INFERRED (market_naver.md); exact sub-schema UNKNOWN",
        "blocked_reason_code": "missing_required_field",
        # TODO(Phase 1 contract gap): no shipping concept exists anywhere in
        # CommerceModule's result today.
    },
    "return_address": {
        "classification": "required",
        "phase1_source": None,
        "platform_field": None,
        "evidence_tier": "UNKNOWN -- likely a seller-account-level profile setting, not a per-product Phase 1 fact",
        "blocked_reason_code": "platform_field_mapping_unknown",
        # TODO(Phase 2B): confirm whether this is per-product or seller-profile.
    },
    "search_keywords": {
        "classification": "optional",
        "phase1_source": "platform_packages.{platform}.search_keywords",
        "platform_field": "detailAttribute.seoInfo",
        "evidence_tier": "INFERRED (market_naver.md, no exact sub-field name)",
        "blocked_reason_code": None,
    },
    "brand_manufacturer": {
        "classification": "required",
        # Only the "manufacturer" half is exposed by Phase 1 today (inside the
        # notice_information dict); "brand" has no output path at all -- see
        # TODO below. This is a partial, not a true composite, mapping.
        "phase1_source": "platform_packages.{platform}.notice_information.manufacturer",
        "platform_field": "detailAttribute.naverShoppingSearchInfo",
        "evidence_tier": "INFERRED (market_naver.md, no exact sub-field names)",
        "blocked_reason_code": "missing_required_field",
        # TODO(Phase 1 contract gap): "brand" is validated by CommerceModule
        # (product.brand fact) but never rendered/exposed in the result dict --
        # only "manufacturer" survives into platform_packages.notice_information.
        "condition": "manufacturer only; brand has no Phase 1 output path today",
    },
    "benefits": {
        "classification": "optional",
        "phase1_source": "detail_page.benefits.items",
        "platform_field": "customerBenefit",
        "evidence_tier": "INFERRED (market_naver.md)",
        "blocked_reason_code": "stale_volatile_fact",
        "condition": "only included when a currently-fresh, source-backed benefit exists",
    },
    "options": {
        "classification": "conditional",
        "phase1_source": "platform_packages.{platform}.options",
        "platform_field": "detailAttribute.optionInfo",
        "evidence_tier": "INFERRED (market_naver.md); simple-vs-combination schema UNKNOWN",
        "blocked_reason_code": "missing_required_field",
        "condition": "required when the product has more than one purchasable variant",
    },
    "images": {
        "classification": "required",
        "phase1_source": None,
        "platform_field": "images.representativeImage",
        "evidence_tier": "INFERRED (market_naver.md); CONFIRMED (official channel) endpoint exists per PLATFORM_API_EVIDENCE_MATRIX.md (POST .../product-images/upload, JPEG/GIF/PNG/BMP only)",
        "blocked_reason_code": "image_hosting_not_implemented",
        # TODO(Phase 1 contract gap): Phase 1's input contract has NO image fact
        # type today (no product.images[], no source_ids/rights metadata for
        # images). A SmartStore payload cannot honestly populate this field
        # until that Phase 1 gap is closed. See SMARTSTORE_PRODUCT_CONTRACT.md
        # §4.2. This adapter must never fetch or reference an image URL that did
        # not already pass Phase 1's rights_or_permission gate.
    },
}

COUPANG_CONTRACT: Dict[str, Dict[str, Any]] = {
    "product_name": {
        "classification": "required",
        "phase1_source": "platform_packages.{platform}.product_name",
        "platform_field": "sellerProductName",
        "evidence_tier": "CONFIRMED (official channel, search-synthesis only)",
        "blocked_reason_code": "missing_required_field",
    },
    "item_name": {
        "classification": "required",
        "phase1_source": "platform_packages.{platform}.product_name",
        "platform_field": None,  # itemName vs vendorItemName split UNKNOWN
        "evidence_tier": "UNKNOWN exact key split (itemName vs vendorItemName)",
        "blocked_reason_code": "missing_required_field",
        "condition": "required per purchasable item, even for a single-option product -- Coupang is item-centric, not product-centric",
    },
    "category": {
        "classification": "required",
        "phase1_source": None,  # TODO(Phase 1 contract gap): see SMARTSTORE_CONTRACT["category"] note.
        "platform_field": "displayCategoryCode",
        "evidence_tier": "CONFIRMED (official channel, search-synthesis only)",
        "blocked_reason_code": "platform_category_metadata_unresolved",
        "condition": "resolved via the Category Metadata Query API, never guessed from a category label",
    },
    "price": {
        "classification": "required",
        "phase1_source": None,  # TODO(Phase 1 contract gap): validated but never exposed -- see SMARTSTORE_CONTRACT["price"].
        "platform_field": None,  # originalPrice / salePrice exact split UNKNOWN
        "evidence_tier": "CONFIRMED (existence only, official channel search-synthesis)",
        "blocked_reason_code": "stale_volatile_fact",
        "condition": "creation-time only -- after approval, price changes MUST use the dedicated item-level price endpoint, never this field (CONFIRMED, PLATFORM_API_EVIDENCE_MATRIX.md: PUT .../vendor-items/{vendorItemId}/prices/{price})",
    },
    "stock": {
        "classification": "required",
        "phase1_source": None,  # TODO(Phase 1 contract gap): validated but never exposed -- see SMARTSTORE_CONTRACT["stock"].
        "platform_field": None,  # maximumBuyCount + a separate quantity field, exact key UNKNOWN
        "evidence_tier": "CONFIRMED (existence only, official channel search-synthesis)",
        "blocked_reason_code": "stale_volatile_fact",
        "condition": "creation-time only -- after approval, stock changes MUST use the dedicated item-level quantity endpoint, never this field",
    },
    "detail_description": {
        "classification": "required",
        "phase1_source": "platform_packages.{platform}.detail_description",
        "platform_field": None,  # contents[] vs top-level detail field UNKNOWN
        "evidence_tier": "UNKNOWN exact mechanism",
        "blocked_reason_code": "missing_required_field",
    },
    "notice_information": {
        "classification": "conditional",
        "phase1_source": "platform_packages.{platform}.notice_information",
        "platform_field": "items[].notices",
        "evidence_tier": "CONFIRMED (official channel, search-synthesis only) -- noticeCategoryName/noticeCategoryDetailName/content sub-fields",
        "blocked_reason_code": "notice_information_incomplete",
        "condition": "resolved dynamically via the Category Metadata Query API per submission, never cached",
    },
    "required_purchase_options": {
        "classification": "conditional",
        "phase1_source": "platform_packages.{platform}.options",
        "platform_field": None,
        "evidence_tier": "CONFIRMED (existence only) -- live policy effective 2026-02-02, escalating enforcement",
        "blocked_reason_code": "required_purchase_option_missing",
        "condition": "category-dependent; a LIVE/MOVING policy -- re-verify close to implementation time, not a one-time-confirmed static fact",
    },
    "shipping": {
        "classification": "required",
        "phase1_source": None,  # TODO(Phase 1 contract gap): see SMARTSTORE_CONTRACT["shipping"].
        "platform_field": "deliveryMethod",
        "evidence_tier": "INFERRED",
        "blocked_reason_code": "missing_required_field",
    },
    "return_address": {
        "classification": "required",
        "phase1_source": None,
        "platform_field": "returnCenterCode",
        "evidence_tier": "INFERRED -- likely a registered return-center code referencing a seller-level profile, not raw inline address text",
        "blocked_reason_code": "platform_field_mapping_unknown",
    },
    "search_keywords": {
        "classification": "optional",
        "phase1_source": "platform_packages.{platform}.search_keywords",
        "platform_field": None,  # searchTags exact key UNKNOWN
        "evidence_tier": "INFERRED",
        "blocked_reason_code": None,
    },
    "vendor_id": {
        "classification": "required",
        "phase1_source": None,
        "platform_field": "vendorId",
        "evidence_tier": "CONFIRMED (official channel, search-synthesis only)",
        "blocked_reason_code": "missing_required_field",
        # TODO(Phase 1 contract gap): CommerceModule requires and validates a
        # "seller" fact (blocks the whole run if absent) but never exposes the
        # accepted value anywhere in its result dict -- validated-but-invisible,
        # same class of gap as price/stock.
    },
    "fulfillment_model": {
        "classification": "conditional",
        "phase1_source": None,
        "platform_field": None,
        "evidence_tier": "CONFIRMED (existence only) -- Marketplace vs. Rocket Growth hybrid changes modify-flow behavior",
        "blocked_reason_code": "rocket_fulfillment_model_undetermined",
        # TODO(Phase 1 contract gap): Phase 1 has no fulfillment-model concept
        # at all today. See COUPANG_PRODUCT_CONTRACT.md §1 / architecture doc §3.16.
    },
    "images": {
        "classification": "required",
        "phase1_source": None,
        "platform_field": "items[].images",
        "evidence_tier": "UNKNOWN exact schema; >=1 REPRESENTATION-type image confirmed required",
        "blocked_reason_code": "image_hosting_not_implemented",
        # TODO(Phase 1 contract gap): same gap as SmartStore -- Phase 1 has no
        # image fact type today.
    },
    "options": {
        "classification": "conditional",
        "phase1_source": "platform_packages.{platform}.options",
        "platform_field": "items",
        "evidence_tier": "CONFIRMED (existence only) -- item-centric array, one entry per purchasable variant",
        "blocked_reason_code": "missing_required_field",
        "condition": "at least one items[] entry required even for a single-SKU product",
    },
}

# `requested` (Coupang) / listing-status (SmartStore) are workflow-control values,
# never sourced from Phase 1 product facts. An adapter must always force these to
# their safest ("do not go live") value in Phase 2A -- see smartstore_adapter.py /
# coupang_adapter.py.
WORKFLOW_CONTROL_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "smartstore": {"statusType": "SUSPENDED"},  # TODO(Phase 2B): confirm actual safe/inactive status value
    "coupang": {"requested": False},  # CONFIRMED: false = temp-save only, never auto-submit for approval
}

_CONTRACTS = {
    "smartstore": SMARTSTORE_CONTRACT,
    "coupang": COUPANG_CONTRACT,
}


class ContractLoadError(Exception):
    """Raised only for a genuinely unsupported platform name -- never for a
    missing/malformed config file, which falls back silently instead."""


def load_contract(platform: str, config_path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Return the field contract for `platform`.

    Reads an optional `config/commerce/marketplaces.json` override; falls back
    to the built-in, research-derived contract above on any read/parse failure
    (fail-safe, never fail-open to a permissive default).
    """
    platform = str(platform or "").strip().lower()

    if platform not in _CONTRACTS:
        raise ContractLoadError(f"Unsupported platform: {platform!r}. Supported: {sorted(_CONTRACTS)}")

    base_contract = _CONTRACTS[platform]

    config_path = config_path or Path("config/commerce/marketplaces.json")

    try:
        with open(config_path, "r", encoding="utf-8") as file:
            config = json.load(file)
    except Exception:
        return base_contract

    override = config.get("contract_overrides", {}).get(platform) if isinstance(config, dict) else None

    if not isinstance(override, dict):
        return base_contract

    # Overrides are additive/replacing per-field only -- never silently drop a
    # field the built-in contract already defines.
    merged = {key: dict(value) for key, value in base_contract.items()}
    for field_name, field_override in override.items():
        if isinstance(field_override, dict):
            merged.setdefault(field_name, {}).update(field_override)

    return merged


def required_fields(platform: str) -> List[str]:
    contract = load_contract(platform)
    return [name for name, spec in contract.items() if spec.get("classification") == "required"]


def conditional_fields(platform: str) -> List[str]:
    contract = load_contract(platform)
    return [name for name, spec in contract.items() if spec.get("classification") == "conditional"]


def workflow_control_defaults(platform: str) -> Dict[str, Any]:
    """Always-safe workflow-control values (never go-live) for `platform`."""
    return dict(WORKFLOW_CONTROL_DEFAULTS.get(str(platform or "").strip().lower(), {}))
