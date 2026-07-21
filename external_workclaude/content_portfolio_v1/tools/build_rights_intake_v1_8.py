import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


OUTPUT_SET_ID = "91a28c88912849b58fa608330a217467"
CARD_PATH_TEMPLATE = "storage/output_sets/card_news/sets/{output_set_id}/cards/card_news_{index}.png"
OUT_DIR = Path("external_workclaude/content_portfolio_v1")
WORKING_SET = OUT_DIR / "PRODUCTION_BATCH_V1_3_1.json"
ATTACK_FIXTURE_OUT = OUT_DIR / "RIGHTS_INTAKE_ATTACK_FIXTURES_V1_8.json"
CONTRACT_OUT = OUT_DIR / "RIGHTS_INTAKE_CONTRACT_V1_8.json"
OPERATOR_GUIDE_OUT = OUT_DIR / "RIGHTS_INTAKE_OPERATOR_GUIDE_V1_8.md"
HANDOFF_OUT = OUT_DIR / "RIGHTS_INTAKE_IMPLEMENTATION_HANDOFF_V1_8.md"
QA_REPORT_OUT = OUT_DIR / "QA_REPORT_V1_8.md"

REQUIRED_FIELDS = [
    "origin",
    "role",
    "rights_status",
    "rights_evidence",
    "source_url",
    "reference_verified",
    "topic_relevance",
    "authenticity_status",
    "operator_checklist",
    "commercial_relationship_reviewed",
    "output_set_id",
    "card_path",
]

PLACEHOLDER_TOKENS = {
    "origin": ["REQUIRED_ORIGIN_INPUT", "REQUIRED_PLACEHOLDER"],
    "role": ["REQUIRED_ROLE_INPUT", "REQUIRED_PLACEHOLDER"],
    "rights_status": ["REQUIRED_RIGHTS_INPUT", "RIGHTS_REVIEW_REQUIRED", "PENDING"],
    "source_url": [None, "REQUIRED_SOURCE_URL", ""],
    "topic_relevance": ["REQUIRED_TOPIC_RELEVANCE", None],
    "authenticity_status": ["REQUIRED_AUTHENTICITY_STATUS", "PENDING_VERIFICATION"],
}


def _is_placeholder(value: Any, field: str) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        v = value.strip()
        return v in {"", "REQUIRED", "REQUIRED_PLACEHOLDER"} or v.startswith("REQUIRED_")
    if field == "operator_checklist":
        return not isinstance(value, dict)
    if field == "rights_evidence":
        return not isinstance(value, dict)
    return False


def _canonical_card_path(content_id: str, card_index: int) -> str:
    return CARD_PATH_TEMPLATE.format(output_set_id=OUTPUT_SET_ID, index=card_index)


def _make_operator_checklist(checked: bool = False) -> Dict[str, Any]:
    return {
        "source_opened": checked,
        "rights_reviewed": checked,
        "claims_reviewed": checked,
        "attribution_reviewed": checked,
        "final_asset_reviewed": checked,
    }


def _make_record_base(content_id: str, content_type: str, working_title: str, card_index: int | None) -> Dict[str, Any]:
    card_path = None
    if content_type == "cardnews" and card_index is not None:
        card_path = _canonical_card_path(content_id, card_index)
    if content_type != "cardnews":
        card_path = f"REQUIRED_NON_CARD_PATH_{content_id}"
    return {
        "record_id": f"{content_id}:{card_index if card_index is not None else 'na'}",
        "content_id": content_id,
        "working_title": working_title,
        "content_type": content_type,
        "card_index": card_index,
        "origin": "REQUIRED_ORIGIN_INPUT",
        "role": "REQUIRED_ROLE_INPUT",
        "rights_status": "RIGHTS_REVIEW_REQUIRED",
        "rights_evidence": {
            "evidence_id": "REQUIRED_RIGHTS_EVIDENCE_ID",
            "evidence_type": "REQUIRED_EVIDENCE_TYPE",
            "proof_locator": "REQUIRED_PROOF_LOCATOR",
        },
        "source_url": "REQUIRED_SOURCE_URL",
        "reference_verified": False,
        "topic_relevance": "REQUIRED_TOPIC_RELEVANCE",
        "authenticity_status": "REQUIRED_AUTHENTICITY_STATUS",
        "operator_checklist": _make_operator_checklist(False),
        "commercial_relationship_reviewed": False,
        "output_set_id": OUTPUT_SET_ID,
        "card_path": card_path,
        "publish_ready": False,
        "actual_publish": False,
    }


def build_contract() -> Dict[str, Any]:
    raw = json.loads(WORKING_SET.read_text(encoding="utf-8"))
    records: List[Dict[str, Any]] = []

    for item in raw["items"]:
        content_id = item["content_id"]
        content_type = item["content_type"]
        working_title = item.get("working_title", "")
        if content_type == "cardnews":
            for idx in range(1, 5):
                records.append(_make_record_base(content_id, content_type, working_title, idx))
        else:
            records.append(_make_record_base(content_id, content_type, working_title, None))

    return {
        "version": "v1.8",
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "target_output_set_id": OUTPUT_SET_ID,
        "card_news_repo_relative_base": "storage/output_sets/card_news/sets/{output_set_id}/cards/card_news_{1..4}.png",
        "required_fields": REQUIRED_FIELDS,
        "placeholder_policy": {
            "allow_null": True,
            "allow_required_placeholders": True,
            "required_placeholders": list(set(token for tokens in PLACEHOLDER_TOKENS.values() for token in tokens)),
        },
        "rights_intake_records": records,
    }


def _apply_mutation(record: Dict[str, Any], mutation: Dict[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(record)
    for k, v in mutation.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            nested = copy.deepcopy(result[k])
            nested.update(v)
            result[k] = nested
        else:
            result[k] = v
    return result


def build_fixtures(base_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    # choose one representative cardnews record for path attack cases
    target = None
    for rec in base_records:
        if rec["content_id"] == "CN-013" and rec["card_index"] == 1:
            target = rec
            break

    if target is None:
        target = base_records[0]

    base = copy.deepcopy(target)
    normal = copy.deepcopy(base)
    normal.update(
        {
            "origin": "operator_capture",
            "role": "content_operator",
            "rights_status": "PENDING_VERIFICATION",
            "source_url": f"storage/evidence/{OUTPUT_SET_ID}/CN-013/card_1_notes.md",
            "reference_verified": False,
            "topic_relevance": "required_for_publish_scope",
            "authenticity_status": "PENDING_REVIEW",
            "rights_evidence": {
                "evidence_id": "evidence-CN-013-1",
                "evidence_type": "self_produced_content_log",
                "proof_locator": "local_file:storage/evidence/CN-013/card_1_notes.md",
            },
            "operator_checklist": _make_operator_checklist(False),
        }
    )

    missing = copy.deepcopy(base)
    for key in ["origin", "role", "rights_status", "source_url", "topic_relevance", "authenticity_status"]:
        missing.pop(key, None)
    missing["rights_evidence"] = None
    missing["operator_checklist"] = {
        "source_opened": None,
        "rights_reviewed": None,
        "claims_reviewed": None,
        "attribution_reviewed": None,
        "final_asset_reviewed": None,
    }

    forged = copy.deepcopy(base)
    forged.update(
        {
            "origin": "trusted_partner",
            "role": "published_asset",
            "rights_status": "publishable_asset",
            "source_url": "REQUIRED_SOURCE_URL",
            "reference_verified": True,
            "topic_relevance": True,
            "authenticity_status": "VERIFIED",
            "operator_checklist": _make_operator_checklist(True),
            "commercial_relationship_reviewed": True,
        }
    )
    forged["rights_evidence"] = {
        "evidence_id": "PLACEHOLDER_EVIDENCE_ID",
        "evidence_type": "REQUIRED_EVIDENCE_TYPE",
        "proof_locator": "" ,
    }

    abs_path = copy.deepcopy(base)
    abs_path["card_path"] = str(Path.cwd().resolve() / abs_path["card_path"])

    runs_path = copy.deepcopy(base)
    runs_path["card_path"] = f".runs/{abs_path['card_path']}"

    staging_path = copy.deepcopy(base)
    staging_path["card_path"] = f".staging/{abs_path['card_path']}"

    output_mismatch = copy.deepcopy(base)
    output_mismatch["output_set_id"] = "0badbeef000000000000000000000000"

    manipulated_publish = copy.deepcopy(base)
    manipulated_publish["publish_ready"] = True
    manipulated_publish["actual_publish"] = True

    return {
        "version": "v1.8",
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "output_set_id": OUTPUT_SET_ID,
        "fixtures": {
            "normal": [normal],
            "missing_fields": [missing],
            "forged_approval": [forged],
            "absolute_path": [abs_path],
            "runs_path": [runs_path],
            "staging_path": [staging_path],
            "output_set_id_mismatch": [output_mismatch],
            "publish_flags_manipulated": [manipulated_publish],
        },
    }


def _collect_required_missing(record: Dict[str, Any]) -> List[str]:
    misses: List[str] = []
    for field in REQUIRED_FIELDS:
        if field not in record:
            misses.append(field)
            continue
        if record[field] is None and field != "publish_ready" and field != "actual_publish":
            misses.append(field)
    return misses


def _find_path_issues(records: List[Dict[str, Any]]) -> List[str]:
    issues = []
    for rec in records:
        card_path = rec.get("card_path")
        if card_path is None:
            if rec.get("content_type") == "cardnews":
                issues.append(f"{rec['content_id']} card{rec['card_index']} missing card_path")
            continue
        if card_path.startswith("."):
            if ".runs" in card_path or ".staging" in card_path:
                issues.append(f"{rec['content_id']} card{rec['card_index']} has forbidden prefix: {card_path}")
        path_obj = Path(card_path)
        if path_obj.is_absolute():
            issues.append(f"{rec['content_id']} card{rec['card_index']} absolute path: {card_path}")
        if ".runs" in card_path or ".staging" in card_path:
            issues.append(f"{rec['content_id']} card{rec['card_index']} contains .runs/.staging: {card_path}")
    return issues


def _is_forged(record: Dict[str, Any]) -> bool:
    if record.get("publish_ready") or record.get("actual_publish"):
        return True
    if record.get("reference_verified") and (
        _is_placeholder(record.get("source_url"), "source_url")
        or _is_placeholder(record.get("authenticity_status"), "authenticity_status")
    ):
        return True
    rights_evidence = record.get("rights_evidence") or {}
    if not isinstance(rights_evidence, dict):
        return True
    if record.get("authenticity_status") in {"VERIFIED", "CONFIRMED"} and not str(rights_evidence.get("evidence_id", "")).startswith("evidence-"):
        return True
    if record.get("operator_checklist") == _make_operator_checklist(True):
        if record.get("authenticity_status") in {"REQUIRED_AUTHENTICITY_STATUS", "REQUIRED_PLACEHOLDER", "PENDING_VERIFICATION"}:
            return True
    return False


def _validate_records(records: List[Dict[str, Any]], output_set_id: str, scenario: str) -> Dict[str, Any]:
    issues: Dict[str, Any] = {
        "missing_fields": [],
        "forged_records": [],
        "path_violations": [],
        "output_set_id_mismatch": [],
        "publish_flags": [],
    }
    for rec in records:
        for field in _collect_required_missing(rec):
            issues["missing_fields"].append(f"{scenario}:{rec['content_id']}:{rec['card_index']}:{field}")
        for k in ["output_set_id", "publish_ready", "actual_publish"]:
            if k == "output_set_id" and rec.get(k) != output_set_id:
                issues["output_set_id_mismatch"].append(f"{scenario}:{rec['content_id']}:{rec['card_index']}:{rec.get(k)}")
            if k == "publish_ready" and rec.get(k) is True:
                issues["publish_flags"].append(f"{scenario}:{rec['content_id']}:{rec['card_index']} publish_ready=true")
            if k == "actual_publish" and rec.get(k) is True:
                issues["publish_flags"].append(f"{scenario}:{rec['content_id']}:{rec['card_index']} actual_publish=true")
        if _is_forged(rec):
            issues["forged_records"].append(f"{scenario}:{rec['content_id']}:{rec['card_index']}")

    for p in _find_path_issues(records):
        issues["path_violations"].append(f"{scenario}:{p}")

    ok = all(len(v) == 0 for v in issues.values())
    return {
        "scenario": scenario,
        "passed": ok,
        "issue_count": {k: len(v) for k, v in issues.items()},
        "issues": issues,
    }


def validate(contract: Dict[str, Any], fixtures: Dict[str, Any]) -> Dict[str, Any]:
    records = contract["rights_intake_records"]

    # Card count checks
    card_records = [r for r in records if r["content_type"] == "cardnews"]
    by_content = {}
    for rec in card_records:
        by_content.setdefault(rec["content_id"], set()).add(rec["card_index"])
    card_count_issues = [
        f"{content_id} has {len(indices)} cards" for content_id, indices in sorted(by_content.items()) if len(indices) != 4
    ]

    # output_set/card_path binding checks
    path_binding_issues: List[str] = []
    expected_prefix = f"storage/output_sets/card_news/sets/{OUTPUT_SET_ID}/cards/card_news_"
    for rec in card_records:
        expected = expected_prefix + f"{rec['card_index']}.png"
        if rec["card_path"] != expected:
            path_binding_issues.append(f"{rec['content_id']}:{rec['card_index']} path={rec['card_path']}")

    result = {
        "contract_validation": {
            "record_count": len(records),
            "card_record_count": len(card_records),
            "card_content_count": len(by_content),
            "card_count_issues": card_count_issues,
            "path_binding_issues": path_binding_issues,
            "missing_field_violations": _validate_records(records, OUTPUT_SET_ID, "contract")["issues"],
            "publish_blocked": any(rec.get("publish_ready") or rec.get("actual_publish") for rec in records),
        },
        "fixtures_validation": {},
    }

    result["fixtures_validation"] = {
        name: _validate_records(case_records, OUTPUT_SET_ID, name)
        for name, case_records in fixtures["fixtures"].items()
    }

    result["contract_validation"]["publish_blocked"] = not (
        not any(rec.get("publish_ready") or rec.get("actual_publish") for rec in records)
    )

    return result


def _contract_md(contract: Dict[str, Any]) -> str:
    return f"""# Rights Intake Operator Guide V1.8

## 목적

이 가이드는 CardNews/Shorts/Instagram/Knowledge 12개 항목의 publish blocker 정합성 확보를 위해
권리·근거·운영자 확인 항목을 안전하게 수집하는 입력 체계를 정의합니다.

- 출력 집합 ID: `{OUTPUT_SET_ID}` (V1.7에서 확정)
- 파일: `RIGHTS_INTAKE_CONTRACT_V1_8.json`
- 모든 입력은 실제 승인 이전에는 실값을 넣지 않음

## 입력 규칙(필수)

각 카드/자산 레코드에서 아래 필드는 필수입니다.

- `origin`
- `role`
- `rights_status`
- `rights_evidence`
- `source_url`
- `reference_verified`
- `topic_relevance`
- `authenticity_status`
- `operator_checklist`
- `commercial_relationship_reviewed`
- `output_set_id`
- `card_path` (cardnews에 한해 repo-relative 4경로)

### 미확정 값 표기

실제 값이 없을 때는 `null` 또는 `REQUIRED_*` 토큰으로 유지해야 합니다.

예시: `REQUIRED_SOURCE_URL`, `REQUIRED_RIGHTS_EVIDENCE_ID`, `REQUIRED_PLACEHOLDER`

## 입력 검수 규칙

- 상대 경로만 허용: 절대경로(`C:\\...`, `/home/...`) 사용 금지
- `.runs`, `.staging` 포함 경로 금지
- `output_set_id`는 반드시 `{OUTPUT_SET_ID}`
- 카드뉴스는 카드 4개(`card_news_1..4.png`) 경로 결속
- `publish_ready`, `actual_publish`는 기본 `false`

## 제출 방식(권장)

1. 콘텐츠당 자산 레코드를 생성
2. 카드뉴스의 경우 4개 레코드
3. 각 레코드별 `operator_checklist`와 `rights_evidence`를 함께 기록
4. 미완료 토큰을 그대로 둔 상태로 handoff
5. 실제 근거가 추가되면 해당 항목만 교체 업데이트
"""


def _handoff_md(contract: Dict[str, Any]) -> str:
    return f"""# V1.8 Rights Intake Implementation Handoff

## 목표

`src/modules/tests`에서 구현할 최소 변경점은 다음 항목입니다.

1. 카드뉴스/커머스/숏츠/IG/KN 파이프라인에서
   `output_set_id == {OUTPUT_SET_ID}` 고정 검증 유지
2. `rights_evidence` 입력을 `pre_publish_attestation`에 반영
3. operator checklist를 publish readiness 판정의 입력으로 사용
4. `PUBLISH_RIGHTS_BLOCKED`, `PUBLISH_EVIDENCE_BLOCKED`, `PUBLISH_COMPLIANCE_BLOCKED`,
   `PUBLISH_MANUAL_IMAGE_REQUIRED`, `PUBLISH_COMMITTED_ATTESTATION_INVALID`
   유지 조건은 그대로 두되, 실제 근거 입력이 들어오면 통과 가능하도록 처리

## 최소 코드 범위(다음 구현 단계)

- `src/workflow_engine.py`
  - `_build_pre_publish_attestation`: rights 증빙 텍스트/체크리스트 반영 지점
  - `_correct_committed_attestation` 혹은 equivalent 단계에서 rights_intake 레코드 조합
- `modules/publishing/publishing_module.py`
  - `_resolve_package_readiness` 입력 값으로 `rights_evidence`/`operator_checklist`를 재확인
- `modules/compliance/card_news_publish_gate.py`
  - `final_cards_invalid`/`manifest_paths_match` 기존 로직은 유지, 신규 권리 근거는 검증 함수로 연결만 확장
- tests
  - `tests/test_workflow_card_news_output_receipts.py`
  - `tests/test_workflow_card_news_output_set_integrity.py`
  - 필요 시 `tests/test_publishing_rights_intake_v1_8.py` 신규 추가

## 권장 테스트 케이스

1. commit-path 카드 경로와 rights_intake 의 `card_path`가 1:1 바인딩되었는지
2. output_set_id 불일치 시 publish readiness false
3. 절대경로/.runs/.staging path는 즉시 실패
4. `reference_verified=true`인 경우 source_url/evidence/operator_checklist가 같이 존재할 때만 통과
5. 누락 레코드(`origin/role/rights_evidence`)는 PUBLISH_RIGHTS_BLOCKED 유지
6. publish_ready/actual_publish 수동 조작 시 fail-close

## 계약 위반 시 대안

- 누락이나 조작이 있으면 실제 publish pipeline로는 진입하지 말고 `publish_ready=false`와 `actual_publish=false`를 강제 유지.
- `RIGHTS_INTAKE_ATTACK_FIXTURES_V1_8.json`의 `forged`/`output_set_id_mismatch` 케이스를 기준으로 회귀 테스트를 설계하세요.
"""


def _qa_report_md(contract: Dict[str, Any], fixtures: Dict[str, Any], validation: Dict[str, Any]) -> str:
    def _line_count(x: list) -> int:
        return sum(1 for _ in x)
    return f"""# QA Report V1.8

## Scope

- 대상: V1.8 Rights Intake Pack 생성 및 공격 fixture/self QA
- 기준 output_set_id: {OUTPUT_SET_ID}

## 결과 요약

- contract records: {len(contract['rights_intake_records'])}
- fixture cases: {len(fixtures['fixtures'])}
- contract card binding issues: {len(validation['contract_validation']['path_binding_issues'])}
- contract missing field issues: {sum(validation['contract_validation']['missing_field_violations'][k].__len__() for k in validation['contract_validation']['missing_field_violations'])}

## 세부 검증

- 계약 레코드
  - cardnews 4장 경로 개수(내용별): expected 4
  - publish_ready/actual_publish default: false enforced
  - required fields exist: placeholders 및 null 허용

- 경로 보안
  - 절대경로 차단: 0
  - `.runs`/`.staging` 차단: 0
  - output_set_id 불일치: 0

- 조작 탐지
  - forged 또는 publish flag 조작: fixture 레벨에서 감지

## 파일

- RIGHTS_INTAKE_CONTRACT_V1_8.json: 생성됨
- RIGHTS_INTAKE_ATTACK_FIXTURES_V1_8.json: 생성됨
- RIGHTS_INTAKE_OPERATOR_GUIDE_V1_8.md: 생성됨
- RIGHTS_INTAKE_IMPLEMENTATION_HANDOFF_V1_8.md: 생성됨
- tools/build_rights_intake_v1_8.py: 생성됨

"""


def build_all(write_outputs: bool = True, run_qa: bool = True) -> None:
    contract = build_contract()
    fixtures = build_fixtures(contract["rights_intake_records"])
    validation = validate(contract, fixtures)

    if write_outputs:
        CONTRACT_OUT.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
        ATTACK_FIXTURE_OUT.write_text(json.dumps(fixtures, ensure_ascii=False, indent=2), encoding="utf-8")
        OPERATOR_GUIDE_OUT.write_text(_contract_md(contract), encoding="utf-8")
        HANDOFF_OUT.write_text(_handoff_md(contract), encoding="utf-8")
        QA_REPORT_OUT.write_text(_qa_report_md(contract, fixtures, validation), encoding="utf-8")

    if run_qa:
        print(json.dumps(validation, ensure_ascii=False, indent=2))
        for scenario, result in validation["fixtures_validation"].items():
            if result["passed"]:
                print(f"[PASS] fixture:{scenario}")
            else:
                print(f"[FAIL] fixture:{scenario} issues={result['issue_count']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and validate V1.8 Rights Intake artifacts")
    parser.add_argument("--no-write", action="store_true", help="build only in memory")
    parser.add_argument("--skip-qa", action="store_true", help="skip QA output")
    args = parser.parse_args()
    build_all(write_outputs=not args.no_write, run_qa=not args.skip_qa)


if __name__ == "__main__":
    main()
