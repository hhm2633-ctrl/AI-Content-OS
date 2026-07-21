"""Content Portfolio V1.2 -- Evidence & Rights Acquisition Pack for the Top 20.

Stdlib only. Reads CONTENT_BACKLOG.json, CROSS_CHANNEL_CLUSTERS.json, and
PRODUCTION_BRIEFS_V1_1.json (already produced in this folder) and writes exactly:

- TOP20_EVIDENCE_PACK.json
- TOP20_IMAGE_BRIEFS.md
- RIGHTS_INTAKE_TEMPLATE.json
- OPERATOR_REVIEW_CHECKLIST.md
- SOURCE_ACQUISITION_QUEUE.md
- QA_REPORT_V1_2.md

Hard rule: this script never invents a real URL, image, price, performance figure, or rights
approval. Every unconfirmed value is an explicit placeholder token
(SOURCE_REQUIRED / RIGHTS_REVIEW_REQUIRED / CURRENT_DATA_REQUIRED / OPERATOR_APPROVAL_REQUIRED /
PRICE_VERIFICATION_REQUIRED / PLATFORM_POLICY_REVIEW_REQUIRED) or an explicit null, never a
plausible-looking fabricated value. It never reads or writes anything outside
external_workclaude/content_portfolio_v1/, makes no network call, and performs no real
publishing, purchasing, or account action.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))

from build_portfolio import is_regulated, is_health, is_trend_sensitive  # noqa: E402

BACKLOG_JSON = BASE / "CONTENT_BACKLOG.json"
CLUSTERS_JSON = BASE / "CROSS_CHANNEL_CLUSTERS.json"
PRODBRIEFS_JSON = BASE / "PRODUCTION_BRIEFS_V1_1.json"

OUT_EVIDENCE_JSON = BASE / "TOP20_EVIDENCE_PACK.json"
OUT_IMAGE_MD = BASE / "TOP20_IMAGE_BRIEFS.md"
OUT_RIGHTS_TEMPLATE_JSON = BASE / "RIGHTS_INTAKE_TEMPLATE.json"
OUT_OPERATOR_MD = BASE / "OPERATOR_REVIEW_CHECKLIST.md"
OUT_QUEUE_MD = BASE / "SOURCE_ACQUISITION_QUEUE.md"
OUT_QA_MD = BASE / "QA_REPORT_V1_2.md"

REQUIRED_ITEM_FIELDS = [
    "content_id", "working_title", "content_type", "theme_tag",
    "evidence_types_needed", "allowed_primary_source_types", "freshness_check_interval",
    "forbidden_sources_and_claims", "image_role_and_shooting_brief", "user_shot_image_conditions",
    "generated_image_usage_scope", "attribution_requirements", "operator_confirmation_items",
    "publish_rights_evidence_fields", "source_required_placeholders",
    "incomplete_input_blocker_codes", "cross_channel_reuse_conditions",
]

FORBIDDEN_REAL_VALUE_PATTERNS = [
    re.compile(r"https?://"),
    re.compile(r"www\."),
    re.compile(r"\d+(,\d{3})*\s*원"),
    re.compile(r"\d+(\.\d+)?\s*%\s*(할인|off|세일)", re.IGNORECASE),
    re.compile(r"승인(됨|완료)"),
    re.compile(r"확인(됨|완료)(?!\s*필요)"),
]


def flatten_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from flatten_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from flatten_strings(v)


# ---------------------------------------------------------------------------
# Per-content-type templates, parameterized by topic / theme / risk flags
# ---------------------------------------------------------------------------

def cluster_reuse_note(theme_tag, clusters_by_theme, own_content_type):
    cluster = clusters_by_theme.get(theme_tag)
    if not cluster:
        return (
            "이 콘텐츠는 현재 확인된 cross-channel cluster가 없음 -- 동일 리서치를 다른 채널로 "
            "재사용하려면 새 cluster 후보로 CTO 검토 요청."
        )
    other_channels = sorted(set(cluster["channels"]) - {own_content_type})
    members = ", ".join(f"{m['content_id']}({m['content_type']})" for m in cluster["members"] if m["content_type"] != own_content_type)
    return (
        f"cluster `{cluster['cluster_id']}` 소속 (다른 채널: {', '.join(other_channels) if other_channels else '없음'}). "
        f"재사용 조건: 동일 근거/출처 세트를 그대로 재사용하되 포맷만 전환 -- 관련 브리프: {members or '없음'}. "
        "근거가 CardNews 슬라이드3에서 이미 검증되었다면 Shorts/Instagram 재사용 시 별도 재소싱 불필요, "
        "단 이미지/영상 자산은 채널별로 별도 확보(CardNews=정적 이미지, Shorts=실사 촬영, Instagram=카드형 이미지)."
    )


def build_cardnews_item(brief, theme_tag_note):
    topic = brief["working_title"]
    regulated = is_regulated(topic)
    health = is_health(topic)
    evidence_types = ["실행 단계에 대한 근거 (전문가 코멘트, 공식 가이드, 또는 통계 -- 슬라이드3 한정)"]
    if regulated:
        evidence_types.append("최신 법령/제도 공식 원문 (CURRENT_DATA_REQUIRED)")
    if health:
        evidence_types.append("의학적 효능을 주장하지 않는 일반 정보 수준 근거만 (효능 단정 불가)")
    allowed_sources = ["정부/공공기관 공식 발표", "제조사/공식 브랜드 자료", "학술/연구기관 공개 자료", "전문가 공개 코멘트 또는 인터뷰"]
    if regulated:
        allowed_sources.insert(0, "소관 부처/기관 공식 웹사이트 원문 (최우선)")
    freshness = (
        "게시 직전 재확인 + 연 1회 정기 재검수 (법령/제도 변경 여부)" if regulated
        else "게시 직전 1회 확인, 이후 12개월마다 재검수"
    )
    forbidden = [
        "미확인 커뮤니티 게시물을 그대로 사실 근거로 사용",
        "2차 출처의 2차 출처(재인용의 재인용) 사용",
        "특정 브랜드 비방 또는 근거 없는 우열 비교",
    ]
    if health:
        forbidden.append("의학적 효능·치료 효과 단정")
    slides_note = [
        {"slide": 1, "role": "hook", "shooting_brief": f"{topic} 주제를 암시하는 배경 이미지 1장 -- 인물 얼굴 클로즈업 지양, 상황/사물 위주"},
        {"slide": 2, "role": "problem/context", "shooting_brief": "문제 상황을 보여주는 이미지 -- 특정 브랜드 로고 노출 시 모자이크 또는 재촬영"},
        {"slide": 3, "role": "evidence-backed solution", "shooting_brief": "해결책 실행 장면 이미지 -- 근거 문구가 들어갈 여백 확보"},
        {"slide": 4, "role": "cta/source", "shooting_brief": "저장/공유 유도용 마무리 이미지 -- CTA 텍스트 삽입 공간 확보"},
    ]
    return {
        "evidence_types_needed": evidence_types,
        "allowed_primary_source_types": allowed_sources,
        "freshness_check_interval": freshness,
        "forbidden_sources_and_claims": forbidden,
        "image_role_and_shooting_brief": slides_note,
        "user_shot_image_conditions": [
            "촬영자 본인 소유 공간/사물만 촬영 (타인 소유 공간은 이용 동의 확보)",
            "제3자 얼굴이 식별 가능하게 노출된 경우 동의서 확보 전까지 사용 금지",
            "제품/브랜드 로고가 노출된 경우 저작권/상표권 확인 전까지 블러 처리",
        ],
        "generated_image_usage_scope": [
            "CardNewsModule 배경 fallback(단색/그라디언트, 저작권 이슈 없음)만 자동 생성 경로로 즉시 사용 가능",
            "실사형 합성 이미지는 이번 Sprint 범위 밖 -- 외부 이미지 생성 API 승인 전까지 미사용",
        ],
        "attribution_requirements": (
            "공식 자료 인용 시 슬라이드3 하단에 기관/자료명 표기, 이미지는 자체 촬영 또는 라이선스 확인된 소재만 사용하며 "
            "라이선스 조건에 attribution이 명시된 경우 그대로 표기"
        ),
        "operator_confirmation_items": [
            "근거 원문이 실제로 존재하고 슬라이드3 문구와 일치하는지 확인",
            "이미지 라이선스 또는 자체 촬영 동의 확인",
            "게시 전 민감 표현/오탈자 검수",
        ] + (["규제/법령 최신 개정 여부 재확인 (CURRENT_DATA_REQUIRED 해소 여부)"] if regulated else []),
        "publish_rights_evidence_fields": {
            "image_rights_proof": None,
            "source_citation_proof": None,
            "reviewer_name": None,
            "reviewed_at": None,
        },
        "source_required_placeholders": (
            ["SOURCE_REQUIRED: 슬라이드3 근거 원문(문서/링크 아님, 출처명과 확보 경로만 기록)"]
            + (["CURRENT_DATA_REQUIRED: 최신 법령/제도 공식 원문"] if regulated else [])
            + ["RIGHTS_REVIEW_REQUIRED: 비-fallback 이미지 라이선스 문서"]
        ),
        "incomplete_input_blocker_codes": (
            ["SOURCE_REQUIRED", "RIGHTS_REVIEW_REQUIRED"] + (["CURRENT_DATA_REQUIRED"] if regulated else [])
        ),
        "cross_channel_reuse_conditions": theme_tag_note,
    }


def build_shorts_item(brief, theme_tag_note):
    topic = brief["working_title"]
    health = is_health(topic)
    evidence_types = ["실연 장면 자체가 근거 (통계 인용 불필요)", "통계/수치를 자막으로 삽입할 경우에만 공식 자료 필요"]
    if health:
        evidence_types.append("건강/다이어트 관련 언급은 일반 정보 수준 유지, 효능 단정 근거 없이 사용 금지")
    return {
        "evidence_types_needed": evidence_types,
        "allowed_primary_source_types": ["자체 실연/촬영 자체", "통계 인용 시 정부/공공기관 또는 학술 자료"],
        "freshness_check_interval": "촬영 시점 값만 사용 -- 사후 재확인 불필요(실연 자체가 증거), 통계 자막 삽입 시에만 게시 직전 재확인",
        "forbidden_sources_and_claims": [
            "실제 조회수/참여 데이터를 자막으로 삽입",
            "미검증 수치를 실연 결과처럼 표시",
        ] + (["의학적 효능 단정"] if health else []),
        "image_role_and_shooting_brief": [
            {"scene": 1, "role": "hook", "shooting_brief": "결과물/시작 장면 3초 -- 손/사물 클로즈업, 얼굴 노출은 촬영자 본인 동의 범위 내"},
            {"scene": 2, "role": "context", "shooting_brief": "문제 상황 또는 시작 전 상태, 실제 촬영"},
            {"scene": 3, "role": "core_steps", "shooting_brief": "단계별 실행 장면 2~3컷, 각 컷 5~10초"},
            {"scene": 4, "role": "cta", "shooting_brief": "완성 결과 + 자막 삽입 공간 확보"},
        ],
        "user_shot_image_conditions": [
            "촬영자 본인 소유 공간/사물/반려동물만 촬영 (타인 소유물/반려동물은 소유자 동의 확보)",
            "제3자가 화면에 노출될 경우 동의 확보 전까지 사용 금지",
            "실제 걸음 수/시간 등 화면에 보이는 값은 촬영 당시 실제 값만 사용, 사후 수치 삽입 금지",
        ],
        "generated_image_usage_scope": [
            "생성 이미지/영상 전면 미사용 -- 이번 자산은 실사 촬영 전제, 자동 렌더링/합성 없음",
        ],
        "attribution_requirements": "통계 자막 삽입 시 화면 하단에 출처명 표기, 실연 장면은 자체 콘텐츠이므로 attribution 불필요",
        "operator_confirmation_items": [
            "촬영 소재가 실제로 촬영되었는지 확인 (스톡 영상 대체 금지)",
            "제3자 동의 필요 여부 확인",
            "음원/배경음악 라이선스 확인",
            "자막 삽입 수치가 실제 촬영 값과 일치하는지 확인",
        ],
        "publish_rights_evidence_fields": {
            "footage_ownership_proof": None,
            "third_party_consent_proof": None,
            "music_license_proof": None,
            "reviewer_name": None,
            "reviewed_at": None,
        },
        "source_required_placeholders": [
            "RIGHTS_REVIEW_REQUIRED: 촬영 소재 소유권/동의 증빙",
            "RIGHTS_REVIEW_REQUIRED: 음원 라이선스 증빙 (사용 시)",
        ],
        "incomplete_input_blocker_codes": ["RIGHTS_REVIEW_REQUIRED"],
        "cross_channel_reuse_conditions": theme_tag_note,
    }


def build_instagram_item(brief, theme_tag_note):
    topic = brief["working_title"]
    trend = is_trend_sensitive(topic)
    evidence_types = ["핵심 정보 1~3개에 대한 근거, 필요 시 출처 1건"]
    if trend:
        evidence_types.append("실제 원문 커뮤니티/뉴스 게시물 (SOURCE_REQUIRED, 반드시 실시간 확인)")
    return {
        "evidence_types_needed": evidence_types,
        "allowed_primary_source_types": (
            ["공개 커뮤니티/뉴스 원문 (원문 라벨링 필수)"] if trend
            else ["정부/공공기관 공식 자료", "일반 공개 자료 (통용 지식 수준)"]
        ),
        "freshness_check_interval": "게시 시점 기준 1~2주 이내 시의성 유효 (원문 재확인 필수)" if trend else "게시 직전 1회 확인, 이후 12개월마다 재검수",
        "forbidden_sources_and_claims": [
            "미검증 최신 사실을 확정 사실처럼 서술",
            "커뮤니티 의견을 사실 정보로 라벨링",
            "실제 성과/순위/조회수 언급",
        ],
        "image_role_and_shooting_brief": [
            {"slide": 1, "role": "hook", "shooting_brief": "흥미 유발용 배경 이미지"},
            {"slide": 2, "role": "core_info", "shooting_brief": "핵심 정보 강조 이미지"},
            {"slide": 3, "role": "detail_or_example", "shooting_brief": "구체 예시 이미지"},
            {"slide": 4, "role": "cta_or_summary", "shooting_brief": "요약/CTA 이미지"},
        ],
        "user_shot_image_conditions": [
            "촬영자 본인 소유 공간/사물만 촬영",
            "커뮤니티 원문 스크린샷은 작성자 식별정보(닉네임/프로필) 마스킹 후에만 사용",
        ],
        "generated_image_usage_scope": ["정보 요약형 카드 배경(단색/그라디언트)만 자동 생성 허용, 실사 합성 이미지 미사용"],
        "attribution_requirements": (
            "커뮤니티/뉴스 원문 인용 시 출처명 및 게시 시점 표기, PII(닉네임/프로필 사진 등) 마스킹 필수" if trend
            else "공식 자료 인용 시 출처명 표기"
        ),
        "operator_confirmation_items": [
            "원문이 실제로 존재하고 인용이 정확한지 확인" if trend else "정보 정확성 확인",
            "PII 마스킹 여부 확인",
            "게시 전 오탈자/민감 표현 검수",
        ],
        "publish_rights_evidence_fields": {
            "source_citation_proof": None,
            "pii_masking_confirmed": None,
            "reviewer_name": None,
            "reviewed_at": None,
        },
        "source_required_placeholders": [
            "SOURCE_REQUIRED: 원문 게시물/자료명 및 확보 경로" if trend else "SOURCE_REQUIRED: 참고 자료명 (필요 시)",
        ],
        "incomplete_input_blocker_codes": ["SOURCE_REQUIRED"] if trend else [],
        "cross_channel_reuse_conditions": theme_tag_note,
    }


def build_knowledge_item(brief, theme_tag_note):
    topic = brief["working_title"]
    regulated = is_regulated(topic)
    return {
        "evidence_types_needed": (
            ["법률/금융/저작권/개인정보 관련 공식 자료 (CURRENT_DATA_REQUIRED)"] if regulated
            else ["통용되는 개념 정의, 필요 시 출처 1건"]
        ),
        "allowed_primary_source_types": (
            ["소관 부처/기관 공식 자료", "전문 서적/학술 자료"] if regulated
            else ["일반 공개 자료", "통용 개념 정의 (사전/교과서 수준)"]
        ),
        "freshness_check_interval": "연 1회 이상 재검수 (개정 여부)" if regulated else "게시 직전 1회 확인, 이후 12개월마다 재검수",
        "forbidden_sources_and_claims": [
            "미검증 통계 인용",
            "법률/금융 정보를 개정 여부 확인 없이 단정",
        ],
        "image_role_and_shooting_brief": [
            {"slide": 1, "role": "hook", "shooting_brief": "흔한 오해를 암시하는 인포그래픽 스타일 배경"},
            {"slide": 2, "role": "concept_definition", "shooting_brief": "개념 정의 강조 이미지"},
            {"slide": 3, "role": "practical_application", "shooting_brief": "실생활 적용 예시 이미지"},
            {"slide": 4, "role": "cta_summary", "shooting_brief": "요약/CTA 이미지"},
        ],
        "user_shot_image_conditions": ["실사 촬영보다 자체 제작 인포그래픽 권장, 실사 사용 시 본인 소유 사물/공간만"],
        "generated_image_usage_scope": ["인포그래픽 스타일 배경(자체 제작 우선)만 사용, 실사 합성 이미지 미사용"],
        "attribution_requirements": "공식 자료 인용 시 출처명 표기, 통용 개념은 attribution 불필요",
        "operator_confirmation_items": [
            "개념 정의가 정확한지 확인",
            "규제 관련 항목은 최신 개정 여부 재확인" if regulated else "일반 통용 정의와 일치하는지 확인",
            "게시 전 오탈자/민감 표현 검수",
        ],
        "publish_rights_evidence_fields": {
            "source_citation_proof": None,
            "reviewer_name": None,
            "reviewed_at": None,
        },
        "source_required_placeholders": (
            ["CURRENT_DATA_REQUIRED: 최신 법령/제도 공식 원문"] if regulated
            else ["SOURCE_REQUIRED: 참고 자료명 (필요 시)"]
        ),
        "incomplete_input_blocker_codes": ["CURRENT_DATA_REQUIRED"] if regulated else [],
        "cross_channel_reuse_conditions": theme_tag_note,
    }


BUILDERS = {
    "cardnews": build_cardnews_item,
    "shorts": build_shorts_item,
    "instagram_feed": build_instagram_item,
    "knowledge_evergreen": build_knowledge_item,
}


def main():
    backlog = json.loads(BACKLOG_JSON.read_text(encoding="utf-8"))
    briefs = backlog["briefs"]
    briefs_by_id = {b["content_id"]: b for b in briefs}

    clusters_doc = json.loads(CLUSTERS_JSON.read_text(encoding="utf-8"))
    clusters_by_theme = {c["theme_tag"]: c for c in clusters_doc["clusters"]}

    prodbriefs_doc = json.loads(PRODBRIEFS_JSON.read_text(encoding="utf-8"))
    prodbriefs_by_id = {pb["content_id"]: pb for pb in prodbriefs_doc["production_briefs"]}

    top20 = sorted(briefs, key=lambda b: b["priority"]["score"], reverse=True)[:20]

    items = []
    for rank, b in enumerate(top20, 1):
        theme_note = cluster_reuse_note(b["theme_tag"], clusters_by_theme, b["content_type"])
        builder = BUILDERS[b["content_type"]]
        fields = builder(b, theme_note)
        item = {
            "rank": rank,
            "content_id": b["content_id"],
            "working_title": b["working_title"],
            "content_type": b["content_type"],
            "theme_tag": b["theme_tag"],
            "priority_score": b["priority"]["score"],
            "current_readiness": b["current_readiness"],
            **fields,
        }
        if b["content_id"] in prodbriefs_by_id:
            item["linked_production_brief"] = "PRODUCTION_BRIEFS_V1_1.json -- 동일 content_id로 hook/slide 문안 방향 이미 작성됨, 이 파일은 그 위에 근거/이미지/권리 확보 계층만 추가"
        items.append(item)

    OUT_EVIDENCE_JSON.write_text(
        json.dumps({"version": "content_portfolio_v1.2", "count": len(items), "items": items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # ---- TOP20_IMAGE_BRIEFS.md ----
    img_lines = ["# Top 20 Image Briefs -- V1.2", "",
                 "Per-item image role, shooting brief, user-shot conditions, and generated-image scope. "
                 "No real image exists yet for any item; every image path below is prospective.", ""]
    for item in items:
        img_lines.append(f"## #{item['rank']} {item['content_id']} -- {item['working_title']} ({item['content_type']})")
        img_lines.append("")
        img_lines.append("**Image role / shooting brief:**")
        for shot in item["image_role_and_shooting_brief"]:
            key = "slide" if "slide" in shot else "scene"
            img_lines.append(f"- {key} {shot[key]} ({shot['role']}): {shot['shooting_brief']}")
        img_lines.append("")
        img_lines.append("**User-shot image conditions:**")
        for c in item["user_shot_image_conditions"]:
            img_lines.append(f"- {c}")
        img_lines.append("")
        img_lines.append("**Generated-image usage scope:**")
        for c in item["generated_image_usage_scope"]:
            img_lines.append(f"- {c}")
        img_lines.append("")
        img_lines.append(f"**Attribution requirements:** {item['attribution_requirements']}")
        img_lines.append("")
    OUT_IMAGE_MD.write_text("\n".join(img_lines), encoding="utf-8")

    # ---- RIGHTS_INTAKE_TEMPLATE.json (blank reusable schema, no real values) ----
    rights_template = {
        "version": "content_portfolio_v1.2",
        "description": (
            "Reusable intake form schema for the rights/operator team to fill per content item before "
            "publish. Every value below is null or an explicit placeholder token -- this file is a form, "
            "not a filled record. Copy one 'intake_record' block per content_id and complete it with real, "
            "verified values before the corresponding blocker_code is considered resolved."
        ),
        "intake_record_schema": {
            "content_id": "REQUIRED -- must match a real CONTENT_BACKLOG.json content_id",
            "sources": [
                {
                    "source_id": None,
                    "source_type": "PLACEHOLDER -- one of: document, merchant_input, manufacturer_source, "
                                    "marketplace_export, official_document, regulator_document, community_post",
                    "source_name": None,
                    "source_locator": "SOURCE_REQUIRED -- document title/location description, never a live URL fabricated by this template",
                    "retrieved_at": None,
                    "rights_or_permission": "RIGHTS_REVIEW_REQUIRED -- one of: merchant_authorized, merchant_owned, owned, licensed, permitted, granted, permission_confirmed, or NOT_YET_CONFIRMED",
                }
            ],
            "images": [
                {
                    "image_id": None,
                    "capture_type": "PLACEHOLDER -- one of: self_shot, cardnews_fallback_generated, licensed_stock",
                    "photographer_or_source": None,
                    "consent_or_license_proof": "RIGHTS_REVIEW_REQUIRED -- description of the proof document, not the document itself",
                    "third_party_visible": "PLACEHOLDER -- true/false; if true, consent_or_license_proof must cover third-party consent",
                }
            ],
            "operator_signoff": {
                "reviewer_name": None,
                "reviewed_at": None,
                "decision": "PLACEHOLDER -- one of: approved_for_manual_upload, blocked, needs_more_evidence",
                "blocker_codes_open": [],
                "notes": None,
            },
        },
        "allowed_placeholder_tokens": [
            "SOURCE_REQUIRED", "PRICE_VERIFICATION_REQUIRED", "RIGHTS_REVIEW_REQUIRED",
            "CURRENT_DATA_REQUIRED", "OPERATOR_APPROVAL_REQUIRED", "PLATFORM_POLICY_REVIEW_REQUIRED",
            "NOT_YET_CONFIRMED",
        ],
        "hard_rule": (
            "No field in a completed intake_record may contain a fabricated URL, image file, price, "
            "performance figure, or rights approval. A field that cannot yet be verified stays as one of "
            "the allowed_placeholder_tokens or null -- it is never filled with a plausible-looking guess."
        ),
    }
    OUT_RIGHTS_TEMPLATE_JSON.write_text(json.dumps(rights_template, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- OPERATOR_REVIEW_CHECKLIST.md ----
    op_lines = ["# Operator Review Checklist -- Top 20", "",
                "One checklist instance per content_id, to be completed by the operator/rights reviewer "
                "before any item moves from brief to publish-ready. No item in this portfolio may be marked "
                "publish-ready by this checklist alone -- it only records what has been confirmed.", ""]
    for item in items:
        op_lines.append(f"## #{item['rank']} {item['content_id']} -- {item['working_title']}")
        op_lines.append("")
        for c in item["operator_confirmation_items"]:
            op_lines.append(f"- [ ] {c}")
        op_lines.append(f"- [ ] publish_rights_evidence_fields 전체 확보 (현재: {list(item['publish_rights_evidence_fields'].keys())}, 전부 null -- 실제 값 입력 전까지 미완료)")
        op_lines.append(f"- [ ] 남은 blocker_codes 해소: {item['incomplete_input_blocker_codes'] or '없음 (근거/권리 확보 완료 후 자동 소거)'}")
        op_lines.append("- [ ] 최종 서명: reviewer_name / reviewed_at (RIGHTS_INTAKE_TEMPLATE.json 참조)")
        op_lines.append("")
    OUT_OPERATOR_MD.write_text("\n".join(op_lines), encoding="utf-8")

    # ---- SOURCE_ACQUISITION_QUEUE.md ----
    queue_lines = ["# Source Acquisition Queue -- Top 20", "",
                   "Prioritized worklist for whoever sources real evidence/rights next. Ordered by priority_score "
                   "(same order as TOP20_PRIORITY_V1_1.md) so the highest-value, easiest-to-clear items are "
                   "acquired first.", "",
                   "| Rank | content_id | working_title | outstanding blockers | primary source type to pursue | freshness check interval |",
                   "|---|---|---|---|---|---|"]
    for item in items:
        blockers = ", ".join(item["incomplete_input_blocker_codes"]) or "없음"
        primary = item["allowed_primary_source_types"][0] if item["allowed_primary_source_types"] else "N/A"
        queue_lines.append(
            f"| {item['rank']} | {item['content_id']} | {item['working_title']} | {blockers} | {primary} | {item['freshness_check_interval']} |"
        )
    queue_lines.append("")
    queue_lines.append("## Notes")
    queue_lines.append("")
    queue_lines.append(
        "No real source has been acquired for any item yet -- every row's blocker list is the actual, unresolved "
        "state. This queue is a worklist, not a status report of completed sourcing."
    )
    OUT_QUEUE_MD.write_text("\n".join(queue_lines), encoding="utf-8")

    # ---- QA_REPORT_V1_2.md ----
    qa_ok = True
    qa_lines = []

    # JSON validity (re-parse what was just written)
    json_files = [OUT_EVIDENCE_JSON, OUT_RIGHTS_TEMPLATE_JSON]
    invalid_json = []
    for f in json_files:
        try:
            json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            invalid_json.append((f.name, str(e)))
    qa_lines.append(f"[JSON 유효성] {'PASS' if not invalid_json else 'FAIL'} -- invalid={invalid_json}")
    qa_ok &= not invalid_json

    # content_id binding
    unbound = [it["content_id"] for it in items if it["content_id"] not in briefs_by_id]
    qa_lines.append(f"[content_id 결속 (CONTENT_BACKLOG.json 실재 확인)] {'PASS' if not unbound else 'FAIL'} -- unbound={unbound}")
    qa_ok &= not unbound

    not_in_top20 = [it["content_id"] for it in items if it["content_id"] not in {b["content_id"] for b in top20}]
    qa_lines.append(f"[상위 20개 범위 준수] {'PASS' if not not_in_top20 else 'FAIL'} -- out_of_scope={not_in_top20}")
    qa_ok &= not not_in_top20

    dup_ids = {it["content_id"] for it in items if [x["content_id"] for x in items].count(it["content_id"]) > 1}
    qa_lines.append(f"[content_id 중복] {'PASS' if not dup_ids else 'FAIL'} -- duplicates={sorted(dup_ids)}")
    qa_ok &= not dup_ids

    # incomplete_input_blocker_codes legitimately may be an empty list (no outstanding blocker for
    # that item, e.g. a non-regulated Knowledge topic or a non-trend Instagram post) -- only its
    # presence as a list is required, not non-emptiness. Every other required field must be
    # non-empty.
    missing = []
    for it in items:
        for f in REQUIRED_ITEM_FIELDS:
            if f not in it:
                missing.append((it["content_id"], f, "field absent"))
                continue
            if f == "incomplete_input_blocker_codes":
                if not isinstance(it[f], list):
                    missing.append((it["content_id"], f, "must be a list (possibly empty)"))
                continue
            if it[f] in (None, "", []):
                missing.append((it["content_id"], f, "empty"))
    qa_lines.append(f"[필수 필드 누락] {'PASS' if not missing else 'FAIL'} -- missing={missing}")
    qa_ok &= not missing

    rights_missing = [it["content_id"] for it in items if not it.get("attribution_requirements") or not it.get("publish_rights_evidence_fields")]
    qa_lines.append(f"[권리/attribution 필드 누락] {'PASS' if not rights_missing else 'FAIL'} -- missing={rights_missing}")
    qa_ok &= not rights_missing

    freshness_missing = [it["content_id"] for it in items if not it.get("freshness_check_interval")]
    qa_lines.append(f"[freshness 확인 주기 누락] {'PASS' if not freshness_missing else 'FAIL'} -- missing={freshness_missing}")
    qa_ok &= not freshness_missing

    real_value_hits = []
    for obj in (items, rights_template):
        for s in flatten_strings(obj):
            for rx in FORBIDDEN_REAL_VALUE_PATTERNS:
                if rx.search(s):
                    real_value_hits.append(s[:80])
    qa_lines.append(f"[실제 URL/이미지/가격/승인 완료 문구 생성 여부] {'PASS' if not real_value_hits else 'FAIL'} -- hits={real_value_hits[:10]}")
    qa_ok &= not real_value_hits

    # every publish_rights_evidence_fields value must be null (no fabricated approval)
    non_null_rights_values = []
    for it in items:
        for k, v in it["publish_rights_evidence_fields"].items():
            if v is not None:
                non_null_rights_values.append((it["content_id"], k, v))
    qa_lines.append(f"[publish_rights_evidence_fields가 모두 null(미확정)인지] {'PASS' if not non_null_rights_values else 'FAIL'} -- non_null={non_null_rights_values}")
    qa_ok &= not non_null_rights_values

    qa_lines.append(f"[생성 파일 수] 6개 (TOP20_EVIDENCE_PACK.json, TOP20_IMAGE_BRIEFS.md, RIGHTS_INTAKE_TEMPLATE.json, OPERATOR_REVIEW_CHECKLIST.md, SOURCE_ACQUISITION_QUEUE.md, QA_REPORT_V1_2.md)")
    qa_lines.append(f"[대상 콘텐츠 수] {len(items)} (요구: 상위 20개)")
    qa_ok &= len(items) == 20

    OUT_QA_MD.write_text(
        "\n".join(["# QA Report V1.2 -- Evidence & Rights Acquisition Pack", "", f"Overall: {'PASS' if qa_ok else 'FAIL'}", ""] + [f"- {l}" for l in qa_lines]),
        encoding="utf-8",
    )

    print("QA_V1_2_OK:", qa_ok)
    for line in qa_lines:
        print(line)


if __name__ == "__main__":
    main()
