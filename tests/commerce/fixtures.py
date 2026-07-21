"""Shared test fixtures for tests/commerce/.

Two fixture styles are provided:
- `sample_commerce_result()` -- a hand-built dict matching the CONFIRMED real
  shape of `CommerceModule.run()`'s output (verified by direct code reading,
  see modules/commerce/contract_loader.py's module docstring). Fast, no
  CommerceModule/KnowledgeInterface/BrandDNAInterface dependency.
- `run_commerce_module()` -- an actual `CommerceModule.run()` call (persist=False),
  for true end-to-end integration tests against the real Phase 1 module.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

NOW = datetime.now(timezone.utc)


def iso(delta=timedelta()):
    return (NOW + delta).isoformat()


def sample_commerce_result() -> Dict[str, Any]:
    """A minimal, CONFIRMED-shape stand-in for a `ready_for_manual_upload`
    Phase 1 result. Mirrors exactly the keys `CommerceModule.run()`/`_package()`
    actually produce -- no `verified_product_facts`, no `platform_packages.*.category`,
    `notice_information` (not `required_notices`) as the notice dict key.
    """
    notice_information = {"manufacturer": "TestManufacturer Co.", "country_of_origin": "Korea"}

    smartstore_package = {
        "platform": "smartstore",
        "status": "ready_for_manual_upload",
        "missing_fields": [],
        "blocked_reasons": [],
        "product_name": "TestBrand Electric Kettle TB-100",
        "search_keywords": ["TestBrand", "TB-100", "Electric Kettle TB-100"],
        "options": [],
        "detail_description": "[HEADLINE]\nTestBrand Electric Kettle TB-100 — 확인된 상품 정보를 살펴보세요.",
        "notice_information": dict(notice_information),
        "manual_upload_text_path": "storage/commerce/smoke_test_001/smartstore_package.txt",
    }

    coupang_notice = dict(notice_information)
    coupang_notice["model_name"] = "TB-100"
    coupang_package = {
        "platform": "coupang",
        "status": "ready_for_manual_upload",
        "missing_fields": [],
        "blocked_reasons": [],
        "product_name": "TestBrand Electric Kettle TB-100",
        "search_keywords": "TestBrand,TB-100,Electric Kettle TB-100",
        "options": [],
        "detail_description": "[HEADLINE]\nTestBrand Electric Kettle TB-100 — 확인된 상품 정보를 살펴보세요.",
        "notice_information": coupang_notice,
        "manual_upload_text_path": "storage/commerce/smoke_test_001/coupang_package.txt",
    }

    return {
        "module": "CommerceModule",
        "version": "commerce_phase_1.1",
        "phase": "commerce_phase_1",
        "request_id": "smoke_test_001",
        "generated_at": iso(),
        "status": "ready_for_manual_upload",
        "upload_mode": "manual_only",
        "auto_upload_performed": False,
        "source_summary": {"provided": 1, "valid_source_ids": ["s1"]},
        "freshness_summary": {"generation_time": iso(), "policy": {}},
        "learned_data_metadata": {"application_mode": "read_only", "writes_performed": False},
        "detail_page": {
            "headline": {"status": "ready", "source_ids": ["s1"], "text": "TestBrand Electric Kettle TB-100 — 확인된 상품 정보를 살펴보세요."},
            "benefits": {"status": "partial", "source_ids": [], "items": []},
            "features": {"status": "ready", "source_ids": ["s1"], "items": ["1.7L capacity"]},
            "specifications": {"status": "ready", "source_ids": ["s1"], "items": ["220V, 1500W"]},
            "usage": {"status": "ready", "source_ids": ["s1"], "items": ["Fill with water and press the button."]},
            "cautions": {"status": "ready", "source_ids": ["s1"], "items": ["Do not immerse in water."]},
        },
        "platform_packages": {"smartstore": smartstore_package, "coupang": coupang_package},
        "manual_upload_checklist": [],
        "missing_fields": [],
        "blocked_reasons": [],
        "output_paths": [],
        "phase_2_gate": {"required": True, "status": "not_approved", "owner": "CTO"},
    }


def _fact(value, source_id="s1", verified_at=None, method="document"):
    return {
        "value": value,
        "source_ids": [source_id],
        "verification_method": method,
        "verified_at": verified_at or iso(timedelta(minutes=-5)),
    }


def sample_product_facts_request() -> Dict[str, Any]:
    """A `product_facts` request dict that passes CommerceModule's gates for
    the fields it actually renders (product_name, notice fields, detail
    sections) -- used by `run_commerce_module()` below."""
    return {
        "request_id": "smoke_test_001",
        "sources": [{
            "source_id": "s1",
            "source_type": "document",
            "source_name": "manufacturer spec sheet",
            "source_locator": "https://example.com/spec.pdf",
            "retrieved_at": iso(timedelta(minutes=-5)),
            "rights_or_permission": {"confirmed": True},
        }],
        "product": {
            "brand": _fact("TestBrand"),
            "manufacturer": _fact("TestManufacturer Co."),
            "model_name": _fact("TB-100"),
            "category": _fact("Home Appliances > Kettles"),
            "product_name": _fact("TestBrand Electric Kettle TB-100"),
            "seller": _fact("TestSeller Inc."),
            "country_of_origin": _fact("Korea"),
            "facts": [_fact("1.7L capacity")],
            "specifications": [_fact("220V, 1500W")],
            "usage": [_fact("Fill with water and press the button.")],
            "cautions": [_fact("Do not immerse in water.")],
        },
        "target_platforms": ["smartstore", "coupang"],
        "learned_data": {"knowledge_enabled": False, "brand_dna_enabled": False, "content_patterns_enabled": False},
    }


def run_commerce_module():
    """Actually run Phase 1's real `CommerceModule` (persist=False) against
    `sample_product_facts_request()`. Import is local to avoid pulling
    CommerceModule's KnowledgeInterface/BrandDNAInterface dependencies into
    modules that only need the lightweight `sample_commerce_result()`."""
    from modules.commerce.commerce_module import CommerceModule

    return CommerceModule().run(product_facts=sample_product_facts_request(), persist=False)
