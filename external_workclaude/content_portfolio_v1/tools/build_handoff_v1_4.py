"""Content Portfolio V1.4 -- Production Team Handoff Pack.

Stdlib only. Converts the 12 red-teamed V1.3.1 items into a stage-by-stage work-order pipeline
that the existing production organization can pick up immediately. This produces work orders and
sequencing documentation only -- it writes no code, renders nothing, and publishes nothing.

Hard constraint from the CTO: `tests/test_workflow_card_news_output_receipts.py` and
`modules/common/card_news_output_set.py` (read-only checked, not modified) show that the
07/08 workflow_results receipt validation for CardNews (`publishing_ready` /
`legacy_receipt_blocked`) is a live, in-progress fix owned by another lane (Common Engine /
CardNews), not this package. Until that fix lands, every CardNews item's render and packaging
work orders are marked `queued` -- only copy, evidence/rights, and layout-prep work orders for
CardNews are parallel-executable.

Never reads/writes outside external_workclaude/content_portfolio_v1/, no network call, no Git
operation, no real publish/purchase/account action, no code change to modules/tests/docs.
"""

from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
BATCH_JSON = BASE / "PRODUCTION_BATCH_V1_3_1.json"

OUT_WORKORDERS_JSON = BASE / "WORK_ORDERS_V1_4.json"
OUT_SEQUENCE_MD = BASE / "PRODUCTION_SEQUENCE_V1_4.md"
OUT_TEAMHANDOFFS_MD = BASE / "TEAM_HANDOFFS_V1_4.md"
OUT_ACCEPTANCE_JSON = BASE / "ACCEPTANCE_MATRIX_V1_4.json"
OUT_BLOCKER_MD = BASE / "BLOCKER_REGISTER_V1_4.md"
OUT_USERINPUT_MD = BASE / "USER_INPUT_REQUEST_V1_4.md"
OUT_QA_MD = BASE / "QA_REPORT_V1_4.md"

CARDNEWS_RECEIPT_BLOCKER = "CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED"

ROLES = [
    "문안·스토리", "Evidence·Rights", "레이아웃·타이포", "렌더링·산출물",
    "패키징·게시인계", "독립 QA", "Shorts", "Instagram·Intelligence", "Knowledge·Learning",
]

WAVE_1 = ["CN-013", "CN-014", "CN-016", "CN-017"]
WAVE_2 = ["KN-008", "KN-007", "IG-007", "IG-013"]
WAVE_3 = ["SH-017", "SH-006", "SH-018", "IG-009"]

_wo_counter = {}


def next_wo_id(content_id):
    _wo_counter[content_id] = _wo_counter.get(content_id, 0) + 1
    return f"{content_id}-WO-{_wo_counter[content_id]:02d}"


def make_wo(content_id, item, stage_key, stage_label, role, task_goal, upstream_inputs,
            exclusive_output, read_only_refs, forbidden_actions, dor, dod, acceptance_checks,
            blocker_codes, next_handoff, parallel_executable, critical_path):
    # Invariant enforced here, not left to each call site to get right: a work order with any
    # open blocker can never be parallel_executable=True, regardless of what the caller passed.
    # This is exactly the bug the QA script's "blocker 없는 작업만 parallel-ready" check exists to
    # catch -- KN-008's Evidence/Rights stage had EVIDENCE_REVIEW_PENDING but was still flagged
    # parallel by the generic knowledge_stages() template, since that template's parallel=True
    # default didn't account for the per-item exception. Fixing it structurally here means no
    # future stage template can reintroduce the same mistake.
    if blocker_codes:
        parallel_executable = False
    return {
        "work_order_id": next_wo_id(content_id),
        "content_id": content_id,
        "stage": stage_key,
        "working_title": item["working_title"],
        "content_type": item["content_type"],
        "current_readiness": ("queued" if blocker_codes else "ready_to_start"),
        "task_goal": task_goal,
        "upstream_inputs": upstream_inputs,
        "owning_role": role,
        "exclusive_output": exclusive_output,
        "read_only_references": read_only_refs,
        "forbidden_actions": forbidden_actions,
        "definition_of_ready": dor,
        "definition_of_done": dod,
        "acceptance_checks": acceptance_checks,
        "blocker_codes": blocker_codes,
        "next_handoff_target": next_handoff,
        "parallel_executable": parallel_executable,
        "critical_path": critical_path,
        "publish_ready": False,
        "actual_publish": False,
    }


COMMON_FORBIDDEN = [
    "실제 API 호출·웹 스크래핑·게시·구매·계정 자동화",
    "modules/, tests/, docs/, storage/, config/, site/ 등 기존 저장소 파일 수정",
    "Git add/commit/push/reset 등 모든 Git 작업",
    "실제 권리 승인·성과·가격·재고·통계 생성 또는 조작",
    "실제 담당자 이름·채팅 ID·완료일 임의 지정",
]


def cardnews_stages(content_id, item):
    wos = []
    base_inputs = ["PRODUCTION_BATCH_V1_3_1.json", "EVIDENCE_RED_TEAM_V1_3_1.md"]

    wos.append(make_wo(
        content_id, item, "COPY_STORY_FINALIZE", "Copy/Story Finalize", "문안·스토리",
        "V1.3.1 최종 문안(4장)을 프로덕션 확정본으로 재확인하고, 슬라이드별 역할(hook/problem/solution/cta)과 문장 완결성을 최종 서명한다.",
        base_inputs,
        f"{content_id}_copy_signoff.md (문안 최종 확인 서명)",
        ["EVIDENCE_RED_TEAM_V1_3_1.md의 해당 content_id 행"],
        COMMON_FORBIDDEN + ["최종 문안의 의미를 변경하는 재작성 (변경 필요 시 Evidence·Rights 역할과 협의 후 별도 개정 요청)"],
        "PRODUCTION_BATCH_V1_3_1.json에 해당 content_id의 4장 완성 문안이 존재함",
        "4장 문장 완결성(말줄임표 없음), 숫자 약속-실제 항목 수 일치, CTA 단일 여부를 재확인하고 서명 완료",
        ["4장 존재 확인", "ellipsis 없음 확인", "number_consistency_check.match == true 확인", "CTA 1개 확인"],
        [],
        "레이아웃·타이포",
        True, True,
    ))
    wos.append(make_wo(
        content_id, item, "EVIDENCE_RIGHTS_CONFIRM", "Evidence/Rights Confirm", "Evidence·Rights",
        "RIGHTS_INTAKE_TEMPLATE.json 양식을 사용해 이미지 사용 경로(자체 촬영/생성 배경/라이선스)를 확정하고 attribution 필요 여부를 재확인한다.",
        ["RIGHTS_INTAKE_TEMPLATE.json", "TOP20_EVIDENCE_PACK.json", "PRODUCTION_BATCH_V1_3_1.json"],
        f"{content_id}_rights_intake.json (완료된 intake 레코드)",
        ["EVIDENCE_RED_TEAM_V1_3_1.md"],
        COMMON_FORBIDDEN + ["실제 이미지 라이선스를 확보하지 않은 채 '확보됨'으로 표기"],
        "해당 content_id의 evidence_status/rights_status가 V1.3.1에 명시되어 있음",
        "이미지 사용 경로가 자체 촬영/CardNewsModule fallback/라이선스 확보 중 하나로 확정되고, 미확정 항목은 명시적 placeholder로 남음",
        ["rights_intake 레코드의 모든 필드가 null 또는 허용된 placeholder 토큰인지 확인", "attribution_required 판단이 evidence_status와 일치하는지 확인"],
        [],
        "레이아웃·타이포",
        True, True,
    ))
    wos.append(make_wo(
        content_id, item, "LAYOUT_TYPOGRAPHY_PREP", "Layout/Typography Prep", "레이아웃·타이포",
        "4장 슬라이드의 레이아웃 초안(기존 CardNewsModule 10개 레이아웃 중 선택)과 타이포그래피 계획(제목/본문 크기, 안전 여백)을 준비한다.",
        [f"{content_id}_copy_signoff.md", f"{content_id}_rights_intake.json"],
        f"{content_id}_layout_plan.md (레이아웃/타이포 초안)",
        ["templates/card_news_layout_rules.json (읽기 전용, 수정 금지)"],
        COMMON_FORBIDDEN + ["11번째 레이아웃 신규 추가", "CardNewsModule 코드 수정"],
        "문안 서명 및 이미지 경로가 확정됨",
        "각 슬라이드에 대해 레이아웃 유형, 텍스트 위계, 이미지 배치, 안전 여백 계획이 문서화됨 -- 실제 렌더링은 수행하지 않음",
        ["4장 모두 레이아웃 유형이 지정되었는지 확인", "안전 여백 기준 명시 확인"],
        [],
        "렌더링·산출물 (07/08 receipt 이슈 해결 전까지 queued)",
        True, False,
    ))
    wos.append(make_wo(
        content_id, item, "RENDER_OUTPUT", "Render/Output", "렌더링·산출물",
        "레이아웃 계획을 CardNewsModule Pillow 렌더러로 실제 4장 PNG를 생성한다.",
        [f"{content_id}_layout_plan.md", f"{content_id}_rights_intake.json"],
        f"{content_id}_render_output.png x4 (미실행)",
        [],
        COMMON_FORBIDDEN + ["07/08 receipt 이슈를 우회하거나 임시 처리로 강제 실행", "workflow_results/07,08 파일을 직접 수정"],
        f"07/08 workflow_results receipt false-ready 이슈(tests/test_workflow_card_news_output_receipts.py 대상)가 담당 팀에 의해 해결되어 CardNewsModule 렌더 경로가 신뢰 가능한 상태가 됨",
        "N/A -- 이 작업지시는 상위 블로커 해소 전까지 시작하지 않음",
        ["07/08 receipt 이슈 해결 여부를 Common Engine/CardNews 담당 팀에 확인"],
        [CARDNEWS_RECEIPT_BLOCKER],
        "독립 QA (동일하게 queued)",
        False, True,
    ))
    wos.append(make_wo(
        content_id, item, "INDEPENDENT_QA_FINAL", "Independent QA (final render)", "독립 QA",
        "렌더링된 4장 PNG를 대상으로 가독성, 안전 여백, 텍스트 잘림, 문안-이미지 일치를 독립적으로 검수한다.",
        [f"{content_id}_render_output.png x4"],
        f"{content_id}_qa_report.md (독립 QA 결과)",
        [],
        COMMON_FORBIDDEN + ["렌더링되지 않은 자산에 대해 QA 통과 처리"],
        "렌더링된 4장 PNG가 실제로 존재함",
        "N/A -- 렌더링 작업지시가 완료되기 전까지 시작하지 않음",
        ["렌더된 PNG 4장 존재 확인 후 시각 검수"],
        [CARDNEWS_RECEIPT_BLOCKER],
        "패키징·게시인계 (동일하게 queued)",
        False, True,
    ))
    wos.append(make_wo(
        content_id, item, "PACKAGING_PUBLISH_HANDOFF", "Packaging/Publish Handoff", "패키징·게시인계",
        "독립 QA를 통과한 산출물을 게시 준비 패키지(캡션/해시태그/발행 큐 항목)로 포장하되, 실제 게시는 수행하지 않는다.",
        [f"{content_id}_qa_report.md"],
        f"{content_id}_publish_package.json (publish_ready=false 고정)",
        ["config/publishing.json (읽기 전용, 수정 금지)"],
        COMMON_FORBIDDEN + ["publish_ready 또는 actual_publish를 true로 설정", "실제 발행 큐에 등록"],
        "독립 QA가 통과 상태로 완료됨",
        "N/A -- 상위 작업지시가 완료되기 전까지 시작하지 않음",
        ["publish_ready == false 확인", "actual_publish == false 확인"],
        [CARDNEWS_RECEIPT_BLOCKER],
        "(외부) 실제 게시 승인 -- 이 패키지 범위 밖",
        False, True,
    ))
    return wos


def shorts_stages(content_id, item):
    wos = []
    wos.append(make_wo(
        content_id, item, "COPY_STORY_FINALIZE", "Script Finalize", "문안·스토리",
        "V1.3.1 최종 스크립트(4장면, 내레이션/자막)를 프로덕션 확정본으로 재확인하고 서명한다.",
        ["PRODUCTION_BATCH_V1_3_1.json", "EVIDENCE_RED_TEAM_V1_3_1.md"],
        f"{content_id}_script_signoff.md",
        ["EVIDENCE_RED_TEAM_V1_3_1.md의 해당 content_id 행"],
        COMMON_FORBIDDEN,
        "PRODUCTION_BATCH_V1_3_1.json에 해당 content_id의 4장면 스크립트가 존재함",
        "4장면의 내레이션/자막/촬영 구도가 재확인되고 서명 완료",
        ["4장면 존재 확인", "narration/subtitle/shot_composition 필드 존재 확인"],
        [],
        "Evidence·Rights",
        True, True,
    ))
    wos.append(make_wo(
        content_id, item, "EVIDENCE_RIGHTS_CONFIRM", "Footage Rights Confirm", "Evidence·Rights",
        "촬영 예정 소재(반려동물/원두/캐리어 등)의 소유권 및 제3자 동의 필요 여부를 RIGHTS_INTAKE_TEMPLATE.json으로 확인한다.",
        ["RIGHTS_INTAKE_TEMPLATE.json", "TOP20_EVIDENCE_PACK.json"],
        f"{content_id}_rights_intake.json",
        ["EVIDENCE_RED_TEAM_V1_3_1.md"],
        COMMON_FORBIDDEN + ["실제 촬영 없이 소유권을 확보됨으로 표기"],
        "manual_assets_needed 목록이 V1.3.1에 명시되어 있음",
        "촬영 소재 소유권/동의 상태가 확정되거나 명시적 placeholder로 남음",
        ["manual_assets_needed 각 항목에 대한 소유권 확인 상태 기록 여부"],
        [],
        "Shorts",
        True, True,
    ))
    wos.append(make_wo(
        content_id, item, "SHORTS_PRODUCTION", "Filming/Editing", "Shorts",
        "실제 소재를 촬영하고 장면표에 따라 편집한다 (TTS/음악/자동 렌더링 없음, 전부 수동).",
        [f"{content_id}_script_signoff.md", f"{content_id}_rights_intake.json"],
        f"{content_id}_edited_clip.mp4 (미실행)",
        [],
        COMMON_FORBIDDEN + ["TTS 자동 생성", "배경음악 자동 삽입", "자동 렌더링 도구로 대체", "실제 업로드"],
        "촬영 소재 권리 확인이 완료됨",
        "실제 촬영/편집이 완료되고 원본 스크립트와 일치함",
        ["실제 촬영 여부 확인 (스톡 영상 대체 금지)", "제3자 동의 필요 여부 재확인"],
        [],
        "독립 QA",
        True, True,
    ))
    wos.append(make_wo(
        content_id, item, "INDEPENDENT_QA_FINAL", "Independent QA", "독립 QA",
        "편집된 영상이 스크립트와 일치하는지, 미검증 수치/효과 주장이 삽입되지 않았는지 독립 검수한다.",
        [f"{content_id}_edited_clip.mp4"],
        f"{content_id}_qa_report.md",
        [],
        COMMON_FORBIDDEN + ["편집되지 않은 자산에 대해 QA 통과 처리"],
        "편집된 영상이 실제로 존재함",
        "스크립트 일치 및 자막 내 미검증 수치 부재를 확인",
        ["자막에 실제 성과/수치가 삽입되지 않았는지 확인"],
        [],
        "패키징·게시인계",
        False, True,
    ))
    wos.append(make_wo(
        content_id, item, "PACKAGING_PUBLISH_HANDOFF", "Packaging/Publish Handoff", "패키징·게시인계",
        "QA를 통과한 영상을 게시 준비 패키지로 포장하되, 실제 게시는 수행하지 않는다.",
        [f"{content_id}_qa_report.md"],
        f"{content_id}_publish_package.json (publish_ready=false 고정)",
        ["config/publishing.json (읽기 전용, 수정 금지)"],
        COMMON_FORBIDDEN + ["publish_ready 또는 actual_publish를 true로 설정"],
        "독립 QA가 통과 상태로 완료됨",
        "게시 준비 메타데이터가 구성되고 publish_ready/actual_publish가 false로 유지됨",
        ["publish_ready == false 확인", "actual_publish == false 확인"],
        [],
        "(외부) 실제 게시 승인 -- 이 패키지 범위 밖",
        False, False,
    ))
    return wos


def instagram_stages(content_id, item):
    wos = []
    wos.append(make_wo(
        content_id, item, "COPY_STORY_FINALIZE", "Copy Finalize", "문안·스토리",
        "V1.3.1 최종 hook/본문/CTA를 프로덕션 확정본으로 재확인하고 서명한다.",
        ["PRODUCTION_BATCH_V1_3_1.json", "EVIDENCE_RED_TEAM_V1_3_1.md"],
        f"{content_id}_copy_signoff.md",
        ["EVIDENCE_RED_TEAM_V1_3_1.md의 해당 content_id 행"],
        COMMON_FORBIDDEN,
        "PRODUCTION_BATCH_V1_3_1.json에 해당 content_id의 hook/body/cta가 존재함",
        "hook/본문/CTA가 완결된 문장이며 해시태그 정책(무해시태그) 준수를 재확인",
        ["hook/body 존재 확인", "해시태그 미포함 확인", "CTA 1개 확인"],
        [],
        "레이아웃·타이포",
        True, True,
    ))
    wos.append(make_wo(
        content_id, item, "EVIDENCE_RIGHTS_CONFIRM", "Evidence/Rights Confirm", "Evidence·Rights",
        "이미지 사용 경로(자체 제작 카드 배경/자체 촬영)를 확정하고 attribution 필요 여부를 재확인한다.",
        ["RIGHTS_INTAKE_TEMPLATE.json", "TOP20_EVIDENCE_PACK.json"],
        f"{content_id}_rights_intake.json",
        ["EVIDENCE_RED_TEAM_V1_3_1.md"],
        COMMON_FORBIDDEN,
        "evidence_status/rights_status가 V1.3.1에 명시되어 있음",
        "이미지 사용 경로가 확정되거나 명시적 placeholder로 남음",
        ["rights_intake 레코드 필드가 null 또는 허용된 placeholder인지 확인"],
        [],
        "레이아웃·타이포",
        True, True,
    ))
    wos.append(make_wo(
        content_id, item, "LAYOUT_TYPOGRAPHY_PREP", "Layout/Typography Prep", "레이아웃·타이포",
        "정보 요약형 카드 배경 또는 단일 피드 이미지의 레이아웃/타이포 초안을 준비한다.",
        [f"{content_id}_copy_signoff.md", f"{content_id}_rights_intake.json"],
        f"{content_id}_layout_plan.md",
        [],
        COMMON_FORBIDDEN,
        "문안 서명 및 이미지 경로가 확정됨",
        "텍스트 삽입 여백을 포함한 카드 레이아웃 계획이 문서화됨",
        ["텍스트 삽입 여백 명시 확인"],
        [],
        "Instagram·Intelligence",
        True, False,
    ))
    wos.append(make_wo(
        content_id, item, "INSTAGRAM_INTELLIGENCE_PREP", "Instagram Intelligence Prep", "Instagram·Intelligence",
        "게시 포맷/캡션 길이/내부 quality_score proxy 기준 부합 여부를 확인한다 (실제 Graph API 성과 데이터는 사용하지 않음).",
        [f"{content_id}_layout_plan.md"],
        f"{content_id}_ig_prep_note.md",
        ["ROADMAP.md의 Instagram Requires External API 섹션 (읽기 전용)"],
        COMMON_FORBIDDEN + ["실제 Instagram 성과 데이터 존재를 가정한 최적화 주장 생성"],
        "레이아웃 계획이 완료됨",
        "내부 proxy 기준으로만 검토되고 실제 성과 데이터가 없다는 점이 명시됨",
        ["실제 성과 데이터 미사용 확인"],
        [],
        "독립 QA",
        True, False,
    ))
    wos.append(make_wo(
        content_id, item, "INDEPENDENT_QA_FINAL", "Independent QA", "독립 QA",
        "최종 카드/캡션이 근거·권리·해시태그 정책을 준수하는지 독립 검수한다.",
        [f"{content_id}_ig_prep_note.md"],
        f"{content_id}_qa_report.md",
        [],
        COMMON_FORBIDDEN,
        "Instagram Intelligence Prep이 완료됨",
        "근거 없는 해시태그/성과 주장이 없음을 확인",
        ["해시태그 정책 준수 재확인", "hook/body 완결성 재확인"],
        [],
        "패키징·게시인계",
        False, False,
    ))
    wos.append(make_wo(
        content_id, item, "PACKAGING_PUBLISH_HANDOFF", "Packaging/Publish Handoff", "패키징·게시인계",
        "QA를 통과한 카드/캡션을 게시 준비 패키지로 포장하되, 실제 게시는 수행하지 않는다.",
        [f"{content_id}_qa_report.md"],
        f"{content_id}_publish_package.json (publish_ready=false 고정)",
        ["config/publishing.json (읽기 전용, 수정 금지)"],
        COMMON_FORBIDDEN + ["publish_ready 또는 actual_publish를 true로 설정"],
        "독립 QA가 통과 상태로 완료됨",
        "게시 준비 메타데이터가 구성되고 publish_ready/actual_publish가 false로 유지됨",
        ["publish_ready == false 확인", "actual_publish == false 확인"],
        [],
        "(외부) 실제 게시 승인 -- 이 패키지 범위 밖",
        False, False,
    ))
    return wos


def knowledge_stages(content_id, item):
    wos = []
    wos.append(make_wo(
        content_id, item, "COPY_STORY_FINALIZE", "Copy Finalize", "문안·스토리",
        "V1.3.1 최종 4장 설명 문안을 프로덕션 확정본으로 재확인하고 서명한다.",
        ["PRODUCTION_BATCH_V1_3_1.json", "EVIDENCE_RED_TEAM_V1_3_1.md"],
        f"{content_id}_copy_signoff.md",
        ["EVIDENCE_RED_TEAM_V1_3_1.md의 해당 content_id 행"],
        COMMON_FORBIDDEN,
        "PRODUCTION_BATCH_V1_3_1.json에 해당 content_id의 4장 문안이 존재함",
        "4장 문장이 완결되고 특정 인물/연구 귀속 주장이 없음을 재확인",
        ["4장 존재 확인", "역사적 인물 귀속 문구 부재 확인", "CTA 1개 확인"],
        [],
        "레이아웃·타이포",
        True, True,
    ))
    wos.append(make_wo(
        content_id, item, "EVIDENCE_RIGHTS_CONFIRM", "Evidence/Rights Confirm", "Evidence·Rights",
        "이미지 사용 경로(자체 제작 인포그래픽)를 확정한다. evidence_not_required_reason이 null인 항목(KN-008)은 별도 검토 필요로 표시한다.",
        ["RIGHTS_INTAKE_TEMPLATE.json", "TOP20_EVIDENCE_PACK.json"],
        f"{content_id}_rights_intake.json",
        ["EVIDENCE_RED_TEAM_V1_3_1.md"],
        COMMON_FORBIDDEN,
        "evidence_status가 V1.3.1에 명시되어 있음",
        "이미지 사용 경로가 확정되거나 명시적 placeholder로 남음; evidence_not_required_reason이 null인 항목은 CTO/리뷰어 확인 대기로 명시",
        ["rights_intake 레코드 필드 확인", "evidence_not_required_reason null 항목에 대한 추가 검토 플래그 확인"],
        (["EVIDENCE_REVIEW_PENDING"] if item.get("evidence_not_required_reason") is None else []),
        "레이아웃·타이포",
        True, True,
    ))
    wos.append(make_wo(
        content_id, item, "LAYOUT_TYPOGRAPHY_PREP", "Layout/Typography Prep", "레이아웃·타이포",
        "인포그래픽 스타일 카드의 레이아웃/타이포 초안을 준비한다.",
        [f"{content_id}_copy_signoff.md", f"{content_id}_rights_intake.json"],
        f"{content_id}_layout_plan.md",
        [],
        COMMON_FORBIDDEN,
        "문안 서명 및 이미지 경로가 확정됨",
        "인포그래픽 레이아웃 계획이 문서화됨",
        ["텍스트 위계 명시 확인"],
        [],
        "Knowledge·Learning",
        True, False,
    ))
    wos.append(make_wo(
        content_id, item, "KNOWLEDGE_LEARNING_INTEGRATION", "Knowledge/Learning Integration", "Knowledge·Learning",
        "이 콘텐츠를 Knowledge Engine 패턴 후보(CANDIDATE)로 등록할지 검토한다 -- 실제 성과 데이터 없이는 VERIFIED로 승격하지 않는다.",
        [f"{content_id}_layout_plan.md"],
        f"{content_id}_knowledge_note.md",
        [".codex/skills/ai-content-os-knowledge-intelligence/SKILL.md (읽기 전용)"],
        COMMON_FORBIDDEN + ["실제 성과 증거 없이 패턴을 VERIFIED로 승격", "PatternRegistry.promote() 호출"],
        "레이아웃 계획이 완료됨",
        "CANDIDATE 상태 등록 여부만 검토 기록, 승격은 수행하지 않음",
        ["승격(promote) 미수행 확인"],
        [],
        "독립 QA",
        True, False,
    ))
    wos.append(make_wo(
        content_id, item, "INDEPENDENT_QA_FINAL", "Independent QA", "독립 QA",
        "최종 카드 문안이 역사적 귀속/효과 주장 없이 정확한지 독립 검수한다.",
        [f"{content_id}_knowledge_note.md"],
        f"{content_id}_qa_report.md",
        [],
        COMMON_FORBIDDEN,
        "Knowledge/Learning Integration 검토가 완료됨",
        "역사적 인물 귀속·효과 단정 문장이 없음을 확인",
        ["역사적 귀속 문구 부재 재확인", "효과 단정 문구 부재 재확인"],
        [],
        "패키징·게시인계",
        False, False,
    ))
    wos.append(make_wo(
        content_id, item, "PACKAGING_PUBLISH_HANDOFF", "Packaging/Publish Handoff", "패키징·게시인계",
        "QA를 통과한 카드를 게시 준비 패키지로 포장하되, 실제 게시는 수행하지 않는다.",
        [f"{content_id}_qa_report.md"],
        f"{content_id}_publish_package.json (publish_ready=false 고정)",
        ["config/publishing.json (읽기 전용, 수정 금지)"],
        COMMON_FORBIDDEN + ["publish_ready 또는 actual_publish를 true로 설정"],
        "독립 QA가 통과 상태로 완료됨",
        "게시 준비 메타데이터가 구성되고 publish_ready/actual_publish가 false로 유지됨",
        ["publish_ready == false 확인", "actual_publish == false 확인"],
        [],
        "(외부) 실제 게시 승인 -- 이 패키지 범위 밖",
        False, False,
    ))
    return wos


STAGE_BUILDERS = {
    "cardnews": cardnews_stages,
    "shorts": shorts_stages,
    "instagram_feed": instagram_stages,
    "knowledge_evergreen": knowledge_stages,
}


def wave_of(content_id):
    if content_id in WAVE_1:
        return 1
    if content_id in WAVE_2:
        return 2
    if content_id in WAVE_3:
        return 3
    return None


def build_all_work_orders(items):
    all_wos = []
    for it in items:
        builder = STAGE_BUILDERS[it["content_type"]]
        wos = builder(it["content_id"], it)
        w = wave_of(it["content_id"])
        for wo in wos:
            wo["wave"] = w
        all_wos.extend(wos)
    return all_wos


def check_dependency_cycles(work_orders):
    """Build a graph from next_handoff_target where the target names a role that owns a later
    stage of the SAME content_id, and confirm no cycle exists (stage order is strictly linear
    per content_id in this design, so this should always report zero cycles -- verified, not
    assumed)."""
    by_content = {}
    for wo in work_orders:
        by_content.setdefault(wo["content_id"], []).append(wo)

    cycles = []
    for cid, wos in by_content.items():
        # stage order is the list order returned by the builder -- confirm each work order's
        # next_handoff_target role matches a role appearing later in the same list (or is an
        # external/out-of-scope target), never an earlier one.
        roles_seen = []
        for wo in wos:
            target = wo["next_handoff_target"]
            for earlier_role in roles_seen:
                if earlier_role and earlier_role in target and "외부" not in target:
                    cycles.append((cid, wo["work_order_id"], target))
            roles_seen.append(wo["owning_role"])
    return cycles


def run_qa(items, work_orders):
    lines = []
    ok = True

    lines.append(f"[12개 콘텐츠 모두 작업지시 존재] {'PASS' if len(items) == 12 else 'FAIL'} -- count={len(items)}")
    ok &= len(items) == 12

    ids_with_wo = {wo["content_id"] for wo in work_orders}
    missing = [it["content_id"] for it in items if it["content_id"] not in ids_with_wo]
    lines.append(f"[전 content_id에 최소 1개 작업지시] {'PASS' if not missing else 'FAIL'} -- missing={missing}")
    ok &= not missing

    outputs = [wo["exclusive_output"] for wo in work_orders]
    dup_outputs = {o for o in outputs if outputs.count(o) > 1}
    lines.append(f"[한 산출물 한 writer] {'PASS' if not dup_outputs else 'FAIL'} -- duplicates={sorted(dup_outputs)}")
    ok &= not dup_outputs

    missing_fields = []
    required = ["content_id", "task_goal", "owning_role", "exclusive_output", "forbidden_actions",
                "definition_of_ready", "definition_of_done", "acceptance_checks",
                "next_handoff_target", "parallel_executable", "critical_path",
                "publish_ready", "actual_publish"]
    for wo in work_orders:
        for f in required:
            if f not in wo or wo[f] in (None, "", []):
                if f in ("parallel_executable", "critical_path", "publish_ready", "actual_publish"):
                    continue  # booleans, False is a valid non-empty value
                missing_fields.append((wo["work_order_id"], f))
    for wo in work_orders:
        for f in ("parallel_executable", "critical_path", "publish_ready", "actual_publish"):
            if f not in wo or not isinstance(wo[f], bool):
                missing_fields.append((wo["work_order_id"], f, "not boolean"))
    lines.append(f"[모든 작업에 금지 작업·완료 검사·handoff 명시] {'PASS' if not missing_fields else 'FAIL'} -- missing={missing_fields[:20]}")
    ok &= not missing_fields

    cycles = check_dependency_cycles(work_orders)
    lines.append(f"[dependency cycle 0] {'PASS' if not cycles else 'FAIL'} -- cycles={cycles}")
    ok &= not cycles

    bad_parallel = [wo["work_order_id"] for wo in work_orders if wo["blocker_codes"] and wo["parallel_executable"]]
    lines.append(f"[blocker 없는 작업만 parallel-ready] {'PASS' if not bad_parallel else 'FAIL'} -- violations={bad_parallel}")
    ok &= not bad_parallel

    cn_render_stage_ids = {"RENDER_OUTPUT", "PACKAGING_PUBLISH_HANDOFF", "INDEPENDENT_QA_FINAL"}
    cn_bypass = [
        wo["work_order_id"] for wo in work_orders
        if wo["content_type"] == "cardnews" and wo["stage"] in cn_render_stage_ids
        and CARDNEWS_RECEIPT_BLOCKER not in wo["blocker_codes"]
    ]
    lines.append(f"[CardNews receipt blocker 우회 0] {'PASS' if not cn_bypass else 'FAIL'} -- bypassed={cn_bypass}")
    ok &= not cn_bypass

    true_publish = [wo["work_order_id"] for wo in work_orders if wo["publish_ready"] is not False or wo["actual_publish"] is not False]
    lines.append(f"[publish_ready/actual_publish true 0] {'PASS' if not true_publish else 'FAIL'} -- violations={true_publish}")
    ok &= not true_publish

    wave_ids = WAVE_1 + WAVE_2 + WAVE_3
    lines.append(f"[Wave 구성 4/4/4, 12개 정확히 배정] {'PASS' if len(wave_ids) == 12 and len(set(wave_ids)) == 12 else 'FAIL'} -- wave1={len(WAVE_1)}, wave2={len(WAVE_2)}, wave3={len(WAVE_3)}")
    ok &= len(wave_ids) == 12 and len(set(wave_ids)) == 12

    return ok, lines


def render_sequence_md(items_by_id, work_orders):
    lines = ["# Production Sequence V1.4", "", "## Wave assignment rationale", "",
             "Waves are sorted by evidence/rights risk and residual manual-input dependency, not by "
             "expected completion speed (CardNews's Wave 1 items are still gated behind the "
             "external CardNews receipt blocker for their render/packaging stages -- see "
             "`BLOCKER_REGISTER_V1_4.md`).", "",
             "**Wave 1 -- lowest risk (4):** CN-013, CN-014, CN-016, CN-017. All CardNews, all "
             "carry `evidence_not_required_reason: pure_operator_instruction`, all viable on "
             "CardNewsModule fallback backgrounds with zero mandatory real photo, and all cleared "
             "multiple red-team passes in V1.3.1 with no open question.", "",
             "**Wave 2 -- needs additional review (4):** KN-008 (the one item where "
             "`evidence_not_required_reason` was deliberately left null per the classification-"
             "content exception -- needs a reviewer/CTO judgment call, not just file-based "
             "confirmation), KN-007 and IG-007 (both newly substituted into the batch in V1.3.1, "
             "only a single red-team pass so far), IG-013 (rewritten to remove a habit-formation "
             "psychology claim -- recommend a second confirming read before lock).", "",
             "**Wave 3 -- needs manual input (4):** SH-017, SH-006, SH-018 (all three Shorts "
             "require real, self-filmed footage -- the clearest 'someone must physically do "
             "something' case in the batch) and IG-009 (rewritten to remove a mood-change claim -- "
             "grouped here because, like the Shorts items, finalizing it depends on a human "
             "reading the rewritten sentence and confirming it still reads naturally, not just a "
             "file check).", "",
             "## CardNews-specific caution (binding for all 4 Wave-1 CardNews items)", "",
             "Per the CTO's explicit instruction: until the existing global 07/08 workflow_results "
             "receipt false-ready issue is resolved (owned by the Common Engine/CardNews lane -- "
             "see `tests/test_workflow_card_news_output_receipts.py`, read-only reference, not "
             "modified by this package), CardNews's `RENDER_OUTPUT`, `INDEPENDENT_QA_FINAL`, and "
             "`PACKAGING_PUBLISH_HANDOFF` work orders stay `queued` with blocker code "
             f"`{CARDNEWS_RECEIPT_BLOCKER}`. Only `COPY_STORY_FINALIZE`, `EVIDENCE_RIGHTS_CONFIRM`, "
             "and `LAYOUT_TYPOGRAPHY_PREP` are marked parallel-executable for CardNews items. "
             "Common Engine code itself is out of this package's ownership -- no fix is proposed "
             "or attempted here.", "", "## Stage sequence per content type", "",
             "- **CardNews**: 문안·스토리 -> Evidence·Rights -> 레이아웃·타이포 -> [QUEUED] 렌더링·산출물 -> "
             "[QUEUED] 독립 QA -> [QUEUED] 패키징·게시인계",
             "- **Shorts**: 문안·스토리 -> Evidence·Rights -> Shorts(촬영/편집) -> 독립 QA -> 패키징·게시인계",
             "- **Instagram**: 문안·스토리 -> Evidence·Rights -> 레이아웃·타이포 -> Instagram·Intelligence -> "
             "독립 QA -> 패키징·게시인계",
             "- **Knowledge/Evergreen**: 문안·스토리 -> Evidence·Rights -> 레이아웃·타이포 -> "
             "Knowledge·Learning -> 독립 QA -> 패키징·게시인계", "",
             "## Full work order list by wave", ""]
    for wave_num, wave_ids in ((1, WAVE_1), (2, WAVE_2), (3, WAVE_3)):
        lines.append(f"### Wave {wave_num}")
        lines.append("")
        for cid in wave_ids:
            item = items_by_id[cid]
            lines.append(f"**{cid} -- {item['working_title']}** ({item['content_type']})")
            for wo in [w for w in work_orders if w["content_id"] == cid]:
                status = "QUEUED" if wo["blocker_codes"] else ("parallel-ready" if wo["parallel_executable"] else "sequential")
                lines.append(f"  - {wo['work_order_id']} [{wo['stage']}] role={wo['owning_role']} -- {status}")
            lines.append("")
    return "\n".join(lines)


def render_team_handoffs_md(work_orders):
    by_role = {}
    for wo in work_orders:
        by_role.setdefault(wo["owning_role"], []).append(wo)
    lines = ["# Team Handoffs V1.4", "",
             "Per-role view of every work order this role owns, so each team can pick up its "
             "queue without reading the entire pipeline.", ""]
    for role in ROLES:
        wos = by_role.get(role, [])
        lines.append(f"## {role} ({len(wos)} work orders)")
        lines.append("")
        if not wos:
            lines.append("(no work orders assigned)")
            lines.append("")
            continue
        for wo in wos:
            lines.append(f"### {wo['work_order_id']} -- {wo['content_id']} {wo['working_title']}")
            lines.append(f"- task_goal: {wo['task_goal']}")
            lines.append(f"- upstream_inputs: {wo['upstream_inputs']}")
            lines.append(f"- exclusive_output: {wo['exclusive_output']}")
            lines.append(f"- read_only_references: {wo['read_only_references']}")
            lines.append(f"- forbidden_actions: {wo['forbidden_actions']}")
            lines.append(f"- definition_of_ready: {wo['definition_of_ready']}")
            lines.append(f"- definition_of_done: {wo['definition_of_done']}")
            lines.append(f"- acceptance_checks: {wo['acceptance_checks']}")
            lines.append(f"- blocker_codes: {wo['blocker_codes'] or '없음'}")
            lines.append(f"- next_handoff_target: {wo['next_handoff_target']}")
            lines.append(f"- parallel_executable: {wo['parallel_executable']} | critical_path: {wo['critical_path']}")
            lines.append(f"- publish_ready: {wo['publish_ready']} / actual_publish: {wo['actual_publish']}")
            lines.append("")
    return "\n".join(lines)


def render_blocker_register_md(work_orders):
    lines = ["# Blocker Register V1.4", "", "## Active blockers", ""]
    blocked = [wo for wo in work_orders if wo["blocker_codes"]]
    by_code = {}
    for wo in blocked:
        for code in wo["blocker_codes"]:
            by_code.setdefault(code, []).append(wo["work_order_id"])
    for code, wo_ids in by_code.items():
        lines.append(f"### {code}")
        lines.append("")
        if code == CARDNEWS_RECEIPT_BLOCKER:
            lines.append(
                "Owner: Common Engine / CardNews lane (not this package). Reference: "
                "`tests/test_workflow_card_news_output_receipts.py` (read-only, not modified). "
                "The 07/08 `workflow_results` receipt validation for `publishing_ready`/"
                "`legacy_receipt_blocked` is under active correction elsewhere in the repository. "
                "This package cannot resolve it, work around it, or estimate a completion date -- "
                "it can only wait and re-check."
            )
        elif code == "EVIDENCE_REVIEW_PENDING":
            lines.append(
                "Owner: CTO / content reviewer. KN-008's `evidence_not_required_reason` was "
                "deliberately left `null` in V1.3.1 because a classification-scheme description "
                "does not qualify for that field per the CTO's own rule, even fully unattributed "
                "and effect-free. This blocker records that a human judgment call is still open, "
                "not a file-completeness gap."
            )
        else:
            lines.append("Owner: unassigned -- record details before treating as active.")
        lines.append("")
        lines.append(f"Affected work orders: {wo_ids}")
        lines.append("")
    lines.append("## No-blocker work orders (parallel-ready now)")
    lines.append("")
    ready = [wo["work_order_id"] for wo in work_orders if not wo["blocker_codes"] and wo["parallel_executable"]]
    lines.append(f"{len(ready)} work orders: {ready}")
    return "\n".join(lines)


def render_user_input_md(items):
    lines = ["# User Input Request V1.4", "",
             "Plain-language summary of what you (the content owner) actually need to provide -- "
             "no technical jargon, no code, no file paths you need to touch yourself.", "",
             "## Content that needs your own photos or video", "",
             "- **SH-017 (반려동물 산책 준비물 점검)**: a short video of you gathering a leash, "
             "waste bags, water, and an ID tag for your own pet.",
             "- **SH-006 (커피 내리는 법 3단계)**: a short video of you brewing coffee with your "
             "own beans/dripper.",
             "- **SH-018 (캐리어 짐싸기 순서)**: a short video of you packing your own suitcase.",
             "",
             "**Acceptable conditions for any photo/video you provide:**", "",
             "- It must be something you actually own or actually filmed yourself (your own pet, "
             "your own coffee gear, your own suitcase).",
             "- If any other person's face is clearly visible, we need your confirmation that they "
             "are okay with it being used.",
             "- If a brand logo shows up in the shot, let us know so we can blur it or ask you to "
             "reshoot without it.",
             "", "## Content that needs an original source or citation", "",
             "**None.** Every one of the 12 selected pieces was deliberately written to need no "
             "outside source, no statistic, and no named expert -- that was the entire point of "
             "this batch. If you'd like to add a citation to strengthen any piece later, that's "
             "optional, not required.",
             "", "## What we need from you for rights/proof-of-ownership", "",
             "For the 3 Shorts videos above: just your confirmation that you filmed it yourself "
             "(or, if someone else appears in it, that they're fine with it being shown). Nothing "
             "more formal is needed -- there is no license or contract to sign.",
             "", "## What you do NOT need to provide right now", "",
             "- No photos are required for the 4 CardNews items (CN-013, CN-014, CN-016, CN-017), "
             "the 3 Instagram items (IG-007, IG-009, IG-013), or the 2 Knowledge items (KN-007, "
             "KN-008) -- these can all use a plain background graphic instead.",
             "- No price, stock, review, or performance numbers -- none of these 12 pieces use any.",
             "- No brand names, expert names, or citations -- none are needed.",
             "- No approval, signature, or account access is needed to move any of this forward "
             "except the three videos above.",
             "", "## Minimum input package to prepare in one batch (if you want to unblock everything at once)", "",
             "1. Three short phone videos (SH-017 pet-walk gear, SH-006 coffee brewing, SH-018 "
             "suitcase packing) -- no editing needed, just the raw footage.",
             "2. A one-line confirmation for each video: \"this is my own pet/gear/suitcase\" (and, "
             "only if another person appears on camera, \"they're okay with this being used\").",
             "",
             "That's the entire list. Everything else in this batch is already finished text "
             "content that the production team can move forward on without waiting for you.",
             ]
    return "\n".join(lines)


def main():
    batch = json.loads(BATCH_JSON.read_text(encoding="utf-8"))
    items = batch["items"]
    items_by_id = {it["content_id"]: it for it in items}

    work_orders = build_all_work_orders(items)
    ok, qa_lines = run_qa(items, work_orders)

    OUT_WORKORDERS_JSON.write_text(
        json.dumps({"version": "content_portfolio_v1.4", "count": len(work_orders), "work_orders": work_orders}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    acceptance_matrix = {
        "version": "content_portfolio_v1.4",
        "content_ids": sorted(items_by_id),
        "acceptance_by_work_order": {
            wo["work_order_id"]: {
                "content_id": wo["content_id"], "stage": wo["stage"],
                "acceptance_checks": wo["acceptance_checks"],
                "definition_of_done": wo["definition_of_done"],
                "blocker_codes": wo["blocker_codes"],
            }
            for wo in work_orders
        },
    }
    OUT_ACCEPTANCE_JSON.write_text(json.dumps(acceptance_matrix, ensure_ascii=False, indent=2), encoding="utf-8")

    OUT_SEQUENCE_MD.write_text(render_sequence_md(items_by_id, work_orders), encoding="utf-8")
    OUT_TEAMHANDOFFS_MD.write_text(render_team_handoffs_md(work_orders), encoding="utf-8")
    OUT_BLOCKER_MD.write_text(render_blocker_register_md(work_orders), encoding="utf-8")
    OUT_USERINPUT_MD.write_text(render_user_input_md(items), encoding="utf-8")
    OUT_QA_MD.write_text(
        "\n".join(["# QA Report V1.4 -- Production Team Handoff Pack", "", f"Overall: {'PASS' if ok else 'FAIL'}", ""] + [f"- {l}" for l in qa_lines]),
        encoding="utf-8",
    )

    print("QA_V1_4_OK:", ok)
    for l in qa_lines:
        print(l)
    print("total_work_orders:", len(work_orders))


if __name__ == "__main__":
    main()
