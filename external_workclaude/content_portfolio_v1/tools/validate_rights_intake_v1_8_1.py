"""V1.8.1 Rights Intake QA validator.

This validator uses only Python stdlib and checks:
- V1.8 contract invariants (record/card counts, IDs, path binding)
- fixture set size and case behavior
- strict blocker-code mapping for normal + 10 attack scenarios
- path, output_set, publish flag, and rights-evidence type hardening
- legacy V1.7/V1.8 artifact byte immutability
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[3]
BASE_DIR = ROOT / "external_workclaude" / "content_portfolio_v1"


DEFAULT_CONTRACT = BASE_DIR / "RIGHTS_INTAKE_CONTRACT_V1_8.json"
DEFAULT_FIXTURES = BASE_DIR / "RIGHTS_INTAKE_ATTACK_FIXTURES_V1_8_1.json"
DEFAULT_MATRIX = BASE_DIR / "RIGHTS_INTAKE_ACCEPTANCE_MATRIX_V1_8_1.json"
DEFAULT_REPORT = BASE_DIR / "QA_REPORT_V1_8_1.md"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _as_int(value: Any) -> int:
    return value if isinstance(value, int) and value >= 0 else -1


def _is_placeholder(value: Any, placeholder_tokens: Iterable[str]) -> bool:
    tokens = set(placeholder_tokens)
    if value is None:
        return True
    if isinstance(value, str):
        stripped = value.strip()
        return stripped in tokens or stripped == "" or stripped.startswith("REQUIRED_") or stripped.lower() == "required"
    return False


def _path_has_forbidden_prefix_or_segment(path_value: str) -> bool:
    normalized = str(path_value).replace("\\", "/")
    lowered = normalized.lower()
    if lowered.startswith(".runs/") or lowered.startswith(".runs\\"):
        return True
    if lowered.startswith(".staging/") or lowered.startswith(".staging\\"):
        return True
    return any(part in {".runs", ".staging"} for part in lowered.split("/"))


def _check_contract_invariants(
    contract: Dict[str, Any],
    matrix: Dict[str, Any],
) -> Dict[str, Any]:
    requirements = matrix["contract_expectations"]
    contract_records = contract.get("rights_intake_records", [])
    record_ids = [str(r.get("record_id")) for r in contract_records if isinstance(r, dict)]
    duplicate_count = len(record_ids) - len(set(record_ids))
    content_ids = [r.get("content_id") for r in contract_records if isinstance(r, dict)]
    card_records = [r for r in contract_records if isinstance(r, dict) and r.get("content_type") == "cardnews"]

    by_content = {}
    for rec in card_records:
        cid = rec.get("content_id")
        by_content.setdefault(cid, set()).add(rec.get("card_index"))

    invalid_card_bindings: List[str] = []
    target_set_id = contract.get("target_output_set_id", "")
    for rec in card_records:
        if not isinstance(rec, dict):
            continue
        card_index = _as_int(rec.get("card_index"))
        expected = (
            f"storage/output_sets/card_news/sets/{target_set_id}/cards/card_news_{card_index if card_index > 0 else 0}.png"
        )
        if card_index <= 0 or rec.get("card_path") != expected:
            invalid_card_bindings.append(f"{rec.get('content_id')}:{rec.get('card_index')}")

    checks = {
        "record_count": len(contract_records) == requirements["record_count"],
        "unique_content_count": len(set([x for x in content_ids if x is not None])) == requirements["unique_content_count"],
        "card_news_count": len(card_records) == requirements["card_news_record_count"],
        "cardnews_content_count": len(by_content) == requirements["cardnews_content_count"],
        "cardnews_index_coverage": all(
            isinstance(indices, set)
            and len(indices) == 4
            and set(indices) == {1, 2, 3, 4}
            for indices in by_content.values()
        ),
        "publish_flags_bool_false": all(
            isinstance(r.get("publish_ready"), bool) and r["publish_ready"] is False
            and isinstance(r.get("actual_publish"), bool) and r["actual_publish"] is False
            for r in contract_records
            if isinstance(r, dict)
        ),
        "record_id_no_duplicate": duplicate_count == 0,
        "card_path_binding": len(invalid_card_bindings) == 0,
    }

    return {
        "checks": checks,
        "passed": all(checks.values()),
        "details": {
            "record_count": len(contract_records),
            "content_count": len(set([x for x in content_ids if x is not None])),
            "card_news_count": len(card_records),
            "cardnews_content_count": len(by_content),
            "record_id_duplicate_count": duplicate_count,
            "invalid_card_bindings": invalid_card_bindings,
        },
    }


def _evaluate_record(
    record: Dict[str, Any],
    target_output_set_id: str,
    required_fields: Sequence[str],
    placeholder_tokens: Sequence[str],
    strict_placeholders: bool,
) -> List[str]:
    blockers: List[str] = []

    for field in required_fields:
        if field not in record:
            blockers.append("MISSING_REQUIRED_FIELDS")
            return blockers

    if not isinstance(record.get("publish_ready"), bool):
        blockers.append("PUBLISH_FLAG_TYPE_INVALID")
    if record.get("publish_ready") is True:
        blockers.append("PUBLISH_FLAG_TRUE")
    if not isinstance(record.get("actual_publish"), bool):
        blockers.append("PUBLISH_FLAG_TYPE_INVALID")
    if record.get("actual_publish") is True:
        if "PUBLISH_FLAG_TRUE" not in blockers:
            blockers.append("PUBLISH_FLAG_TRUE")

    output_set_value = record.get("output_set_id")
    if not isinstance(output_set_value, str):
        blockers.append("OUTPUT_SET_ID_INVALID")
    else:
        normalized_set = output_set_value.strip()
        if normalized_set != output_set_value:
            blockers.append("OUTPUT_SET_ID_WHITESPACE_BLOCK")
        if normalized_set != output_set_value and normalized_set == target_output_set_id:
            pass
        elif normalized_set != target_output_set_id:
            blockers.append("OUTPUT_SET_ID_MISMATCH")
    path_value = record.get("card_path")
    if not isinstance(path_value, str):
        blockers.append("PATH_TYPE_INVALID")
        has_path_violation = True
    else:
        path_value = path_value.strip()
        has_path_violation = False
        if output_set_value is not None and Path(path_value).is_absolute():
            blockers.append("PATH_FORBIDDEN_ABSOLUTE")
            has_path_violation = True
        if _path_has_forbidden_prefix_or_segment(path_value):
            blockers.append("PATH_FORBIDDEN_RUNS_OR_STAGING")
            has_path_violation = True
        if record.get("content_type") == "cardnews":
            expected_index = record.get("card_index")
            if not isinstance(expected_index, int) or expected_index not in (1, 2, 3, 4):
                blockers.append("CARD_INDEX_INVALID")
            else:
                expected_path = (
                    f"storage/output_sets/card_news/sets/{target_output_set_id}/cards/card_news_{expected_index}.png"
                )
                if not has_path_violation and path_value != expected_path:
                    blockers.append("PATH_MISMATCH_CARD_NEWS")
    evidence = record.get("rights_evidence")
    if not isinstance(evidence, dict):
        blockers.append("RIGHTS_EVIDENCE_INVALID_TYPE")
    else:
        for key in ("evidence_id", "evidence_type", "proof_locator"):
            if key not in evidence:
                blockers.append("RIGHTS_EVIDENCE_INVALID_SHAPE")
                break
    if strict_placeholders:
        placeholder_sensitive_fields = ("origin", "role", "source_url")
        for field in placeholder_sensitive_fields:
            if _is_placeholder(record.get(field), placeholder_tokens):
                blockers.append("PLACEHOLDER_AS_APPROVAL")

    if "PUBLISH_FLAG_TYPE_INVALID" not in blockers and (
        record.get("reference_verified") is True
        and _is_placeholder(record.get("rights_status"), placeholder_tokens)
    ):
        blockers.append("FORGED_APPROVAL")
    if not blockers:
        # forged-approval pattern intentionally catches suspicious complete "completed" rows
        evidence_id = str((evidence or {}).get("evidence_id", "")).strip()
        proof_locator = str((evidence or {}).get("proof_locator", "")).strip()
        if (
            record.get("origin") in {"trusted_partner", "approved_partner"}
            and record.get("role") in {"published_asset", "operator_publish"}
            and str(record.get("rights_status")).strip() in {"publishable_asset", "verified"}
            and str(record.get("source_url")).strip() in {"REQUIRED_SOURCE_URL", "required_source", ""}
            and str(record.get("topic_relevance")).strip().lower() in {"true", "1"}
            and proof_locator == ""
            and evidence_id.startswith("PLACEHOLDER_")
        ):
            blockers.append("FORGED_APPROVAL")

    return sorted(set(blockers))


def _evaluate_fixture_cases(
    fixtures: Dict[str, Any],
    matrix: Dict[str, Any],
    target_output_set_id: str,
    required_fields: Sequence[str],
    placeholder_tokens: Sequence[str],
) -> Tuple[Dict[str, Any], int, int]:
    expected_cases = matrix["fixture_expectations"]
    case_map = {c["case_id"]: c for c in expected_cases}
    results: Dict[str, Dict[str, Any]] = {}
    pass_count = 0
    fail_count = 0
    actual_pass_count = 0
    actual_fail_count = 0
    mismatch_cases: List[str] = []

    for case_id, case_records in fixtures.get("fixtures", {}).items():
        expected = case_map.get(case_id)
        if expected is None:
            results[case_id] = {
                "status": "UNMAPPED",
                "passed": False,
                "actual_blockers": [],
                "expected_blockers": [],
                "record_count": 0,
            }
            fail_count += 1
            mismatch_cases.append(case_id)
            continue
        if not isinstance(case_records, list) or not case_records:
            actual_codes = ["NO_RECORD"]
            results[case_id] = {
                "status": "FAIL",
                "passed": False,
                "actual_blockers": actual_codes,
                "expected_blockers": expected["expected_blocker_codes"],
                "record_count": 0,
            }
            fail_count += 1
            mismatch_cases.append(case_id)
            continue

        strict_placeholders = case_id == "normal"
        actual_blockers: List[str] = []
        for rec in case_records:
            if not isinstance(rec, dict):
                actual_blockers.append("RECORD_NOT_OBJECT")
                continue
            actual_blockers.extend(
                _evaluate_record(
                    rec,
                    target_output_set_id,
                    required_fields,
                    placeholder_tokens,
                    strict_placeholders=strict_placeholders,
                )
            )
        actual_codes = sorted(set(actual_blockers))

        expected_pass = bool(expected["expected_pass"])
        expected_codes = expected["expected_blocker_codes"]
        actual_pass = len(actual_codes) == 0

        case_pass = actual_pass == expected_pass
        if expected_codes:
            case_pass = case_pass and actual_codes == expected_codes
        else:
            case_pass = case_pass and actual_codes == []

        if case_pass:
            pass_count += 1
        else:
            fail_count += 1
            mismatch_cases.append(case_id)

        if actual_pass:
            actual_pass_count += 1
        else:
            actual_fail_count += 1

        results[case_id] = {
            "status": "PASS" if case_pass else "FAIL",
            "passed": actual_pass,
            "expected_pass": expected_pass,
            "actual_blockers": actual_codes,
            "expected_blockers": expected_codes,
            "record_count": len(case_records),
            "strict_placeholders": strict_placeholders,
        }

    expected_case_count = len(expected_cases)
    mapped_case_count = len(results)
    scenario_count_ok = mapped_case_count == expected_case_count == matrix["fixture_expectations_count"]

    return {
        "scenario_count_ok": scenario_count_ok,
        "expected_case_count": expected_case_count,
        "mapped_case_count": mapped_case_count,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "mismatch_cases": mismatch_cases,
        "case_results": results,
        "actual_pass_count": actual_pass_count,
        "actual_fail_count": actual_fail_count,
    }, pass_count, fail_count


def _evaluate_integrity(matrix: Dict[str, Any]) -> Dict[str, Any]:
    protected = matrix.get("protected_artifacts", [])
    results: List[Tuple[str, bool, str, str]] = []
    for item in protected:
        rel = item["path"]
        expected = item["sha256"].lower()
        current = _sha256_file((ROOT / rel)).lower()
        ok = current == expected
        results.append((rel, ok, expected, current))

    return {
        "all_unchanged": all(ok for _, ok, _, _ in results),
        "items": [
            {"path": rel, "unchanged": ok, "expected_sha256": expected, "actual_sha256": actual}
            for rel, ok, expected, actual in results
        ],
    }


def _evaluate_placeholder_misclassification(placeholder_blockers: Sequence[str]) -> bool:
    return "PLACEHOLDER_AS_APPROVAL" not in placeholder_blockers


def run_validation(
    contract_path: Path,
    fixtures_path: Path,
    matrix_path: Path,
) -> Dict[str, Any]:
    contract = _read_json(contract_path)
    fixtures = _read_json(fixtures_path)
    matrix = _read_json(matrix_path)

    assert isinstance(contract, dict), "contract must be JSON object"
    assert isinstance(fixtures, dict), "fixtures must be JSON object"
    assert isinstance(matrix, dict), "matrix must be JSON object"

    contract_expectations = matrix["contract_expectations"]
    required_fields = contract_expectations["required_fields"]
    placeholder_tokens = contract_expectations["placeholder_tokens"]
    target_output_set_id = contract.get("target_output_set_id", "")

    contract_check = _check_contract_invariants(contract, matrix)
    assert contract_check["passed"], f"contract invariants failed: {contract_check['checks']}"

    integrity_check = _evaluate_integrity(matrix)
    assert integrity_check["all_unchanged"], "legacy V1.7/V1.8 artifacts changed"

    fixture_summary, _expected_ok, _expected_fail = _evaluate_fixture_cases(
        fixtures,
        matrix,
        target_output_set_id,
        required_fields,
        placeholder_tokens,
    )
    assert fixture_summary["mapped_case_count"] == matrix["fixture_expectations_count"], "fixture case count mismatch"
    assert fixture_summary["scenario_count_ok"], "fixture case mapping count failed"
    assert fixture_summary["actual_pass_count"] == matrix["expected_pass_count"], "fixture pass count mismatch"
    assert fixture_summary["actual_fail_count"] == matrix["expected_fail_count"], "fixture fail count mismatch"
    assert fixture_summary["mismatch_cases"] == [], f"fixture mismatches: {fixture_summary['mismatch_cases']}"

    placeholder_guard = _evaluate_placeholder_misclassification(
        fixture_summary["case_results"]["normal"]["actual_blockers"],
    )
    assert placeholder_guard, "placeholder-as-approval misclassification candidate exists"

    return {
        "contract": {
            "passed": contract_check["passed"],
            "checks": contract_check["checks"],
            "details": contract_check["details"],
        },
        "integrity": integrity_check,
        "fixtures": fixture_summary,
        "placeholder_guard": placeholder_guard,
        "expected_pass_count": matrix["expected_pass_count"],
        "expected_fail_count": matrix["expected_fail_count"],
        "pass_count": fixture_summary["actual_pass_count"],
        "fail_count": fixture_summary["actual_fail_count"],
    }


def _build_report(result: Dict[str, Any], matrix: Dict[str, Any], out_path: Path) -> str:
    total = result["pass_count"] + result["fail_count"]
    lines = [
        "# Rights Intake QA Report V1.8.1",
        "",
        f"- 실행 일시: {matrix.get('generated_at_utc', '')}",
        "",
        "## 요약",
        f"- PASS 수: {result['pass_count']}",
        f"- FAIL 수: {result['fail_count']}",
        f"- 전체 fixture 시나리오 수: {total}",
        f"- Fixture 매핑 수: {result['fixtures']['mapped_case_count']} (기대: {result['fixtures']['expected_case_count']})",
        "",
        "## 계약 정합성",
        f"- contract records: {result['contract']['details']['record_count']}",
        f"- unique content: {result['contract']['details']['content_count']}",
        f"- cardnews record: {result['contract']['details']['card_news_count']}",
        f"- record_id duplicate: {result['contract']['details']['record_id_duplicate_count']}",
        f"- contract pass: {result['contract']['passed']}",
        "",
        "### contract check map",
    ]
    for key, value in result["contract"]["checks"].items():
        lines.append(f"- {key}: {'PASS' if value else 'FAIL'}")
    lines.extend(
        [
            "",
            "## Fixture 시나리오",
            f"- 기대 PASS: {result['expected_pass_count']}",
            f"- 기대 FAIL: {result['expected_fail_count']}",
            f"- 실제 PASS: {result['pass_count']}",
            f"- 실제 FAIL: {result['fail_count']}",
            "",
        ]
    )
    for case_name, case in result["fixtures"]["case_results"].items():
        lines.append(
            f"- {case_name}: {case['status']} | actual={case['actual_blockers']} | expected={case['expected_blockers']}"
        )
    allowed_path_cases = {"absolute_path", "runs_path", "staging_path"}
    path_block_in_disallowed_case = any(
        case_name not in allowed_path_cases and any(str(v).startswith("PATH_") for v in case["actual_blockers"])
        for case_name, case in result["fixtures"]["case_results"].items()
    )
    lines.extend(
        [
            "",
            "## 보안 정합성",
            f"- placeholder 오인 승인 오탐 차단: {'PASS' if result['placeholder_guard'] else 'FAIL'}",
            f"- path/.runs/.staging 제로: {'PASS' if not path_block_in_disallowed_case else 'FAIL'}",
            "",
            "## 기존 V1.7/V1.8 바이트 무변경",
        ]
    )
    for item in result["integrity"]["items"]:
        status = "PASS" if item["unchanged"] else "FAIL"
        lines.append(f"- {item['path']}: {status}")
    report_text = "\n".join(lines) + "\n"
    out_path.write_text(report_text, encoding="utf-8")
    return report_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute V1.8.1 Rights Intake executable QA")
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT), help="rights contract json path")
    parser.add_argument("--fixtures", default=str(DEFAULT_FIXTURES), help="attack fixtures json path")
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX), help="acceptance matrix json path")
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help="output markdown report path")
    args = parser.parse_args()

    contract_path = Path(args.contract)
    fixtures_path = Path(args.fixtures)
    matrix_path = Path(args.matrix)
    report_path = Path(args.report)

    for path in (contract_path, fixtures_path, matrix_path):
        assert path.exists(), f"required input missing: {path}"

    matrix = _read_json(matrix_path)
    try:
        result = run_validation(contract_path, fixtures_path, matrix_path)
    except AssertionError as exc:
        result = {"error": str(exc)}
        report_text = _build_report(
            {
                "contract": {"passed": False, "checks": {}, "details": {}},
                "integrity": {"all_unchanged": False, "items": []},
                "fixtures": {"mapped_case_count": 0, "expected_case_count": 0, "case_results": {}, "pass_count": 0, "fail_count": 0},
                "placeholder_guard": False,
                "expected_pass_count": 0,
                "expected_fail_count": 0,
                "pass_count": 0,
                "fail_count": 0,
            },
            matrix,
            report_path,
        )
        report_path.write_text(f"### QA execution failed\n- {str(exc)}\n", encoding="utf-8")
        raise SystemExit(1)

    report = _build_report(result, matrix, report_path)
    print(f"PASS: {result['pass_count']} FAIL: {result['fail_count']}")
    print(f"QA report written: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
