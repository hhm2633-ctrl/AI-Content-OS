"""Content Portfolio V1.1 -- backlog + learning-seed-pattern generator and QA checker.

Stdlib only. Writes CONTENT_BACKLOG.json, CONTENT_BACKLOG.md, LEARNING_SEED_PATTERNS.json,
TOP20_PRIORITY.md, and QA_REPORT.md into the parent content_portfolio_v1/ folder.

V1.1 change (deterministic, no backup, per CTO instruction): each topic now carries a
`theme_tag` used to (a) compute a genuine per-topic `reuse_score` (how many other content
types share the same theme) and (b) drive `tools/audit_v1_1.py`'s cross-channel cluster
detection. `evidence_sourcing_cost`, `rights_difficulty`, and `freshness_risk` are now assessed
per topic instead of being a single constant per content_type, which is what caused every
non-regulated CardNews brief to tie at the same priority score in V1.

This script and its outputs are the only things it touches. It never reads or writes
anything outside external_workclaude/content_portfolio_v1/, makes no network calls, and
performs no real publishing, purchasing, or account action of any kind.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_BACKLOG_JSON = BASE / "CONTENT_BACKLOG.json"
OUT_BACKLOG_MD = BASE / "CONTENT_BACKLOG.md"
OUT_PATTERNS_JSON = BASE / "LEARNING_SEED_PATTERNS.json"
OUT_TOP20_MD = BASE / "TOP20_PRIORITY.md"
OUT_QA_MD = BASE / "QA_REPORT.md"

REQUIRED_FIELDS = [
    "content_id", "content_type", "channel", "category", "working_title", "audience",
    "problem", "promise", "hook", "core_question", "story_structure", "slide_or_scene_roles",
    "cta", "evidence_needed", "source_type_needed", "image_or_asset_needed",
    "rights_status_required", "volatile_claims", "forbidden_claims", "manual_review",
    "monetization_route", "disclosure_required", "freshness_window", "fallback_behavior",
    "reusable_pattern_tags", "priority", "effort", "expected_learning_value",
    "current_readiness", "blocker_codes",
]

ALLOWED_READINESS = {
    "implemented", "offline_ready", "manual_ready", "planning_only", "blocked_by_data",
    "blocked_by_rights", "blocked_by_api", "blocked_by_policy", "not_approved",
}

ALLOWED_PATTERN_STATUS = {"hypothesis_only", "needs_content_qa", "needs_real_performance_data"}

REAL_TAG_TOKENS = {
    "SOURCE_REQUIRED", "PRICE_VERIFICATION_REQUIRED", "RIGHTS_REVIEW_REQUIRED",
    "CURRENT_DATA_REQUIRED", "OPERATOR_APPROVAL_REQUIRED", "PLATFORM_POLICY_REVIEW_REQUIRED",
}

REGULATED_KEYWORDS = [
    "연말정산", "신용점수", "전세", "이직", "육아휴직", "자동차 정기점검", "세금", "저작권",
    "개인정보보호", "재무제표", "신용카드", "환불", "소비자 권리",
]

HEALTH_KEYWORDS = ["스트레칭", "홈트레이닝", "다이어트", "보습", "피부", "면역", "건강"]

ALLOWED_RISK_TAGS = {
    "LEGAL_REGULATORY_RISK", "FINANCIAL_RISK", "MEDICAL_HEALTH_RISK", "PRODUCT_CLAIM_RISK",
}


def is_regulated(topic: str) -> bool:
    return any(k in topic for k in REGULATED_KEYWORDS)


def is_health(topic: str) -> bool:
    return any(k in topic for k in HEALTH_KEYWORDS)


def is_financial(topic: str) -> bool:
    return any(k in topic for k in ("신용점수", "신용카드", "재무제표", "연말정산", "세금"))


def is_trend_sensitive(topic: str) -> bool:
    return any(k in topic for k in ("트렌드", "화제글", "신조어"))


def is_checklist_shaped(topic: str) -> bool:
    return any(k in topic for k in ("체크리스트", "가지", "단계", "기준", "순서"))


def assess_topic(topic: str, content_type: str) -> dict:
    """Per-topic (not per-category-constant) risk/cost assessment.

    This is the direct fix for the V1 scoring defect: V1 assigned a single
    evidence/rights/freshness constant per content_type, so every non-regulated CardNews
    brief scored identically. Here each topic's own keyword profile shifts the baseline,
    so genuinely different topics get genuinely different scores.
    """
    risk_tags = []
    if is_regulated(topic):
        risk_tags.append("LEGAL_REGULATORY_RISK")
    if is_financial(topic):
        risk_tags.append("FINANCIAL_RISK")
    if is_health(topic):
        risk_tags.append("MEDICAL_HEALTH_RISK")
    if content_type in ("commerce_guide", "brandconnect"):
        risk_tags.append("PRODUCT_CLAIM_RISK")
    # de-dupe, keep order
    risk_tags = list(dict.fromkeys(risk_tags))

    base_evidence = {
        "cardnews": 1.2, "shorts": 1.0, "instagram_feed": 1.3, "brandconnect": 3.0,
        "commerce_guide": 2.5, "knowledge_evergreen": 1.3,
    }[content_type]
    if "LEGAL_REGULATORY_RISK" in risk_tags or "FINANCIAL_RISK" in risk_tags:
        base_evidence += 1.0
    if is_trend_sensitive(topic):
        base_evidence += 1.2
    if is_checklist_shaped(topic):
        base_evidence -= 0.3
    evidence_sourcing_cost = max(1.0, min(3.0, round(base_evidence, 2)))

    base_rights = {
        "cardnews": 1.0, "shorts": 1.6, "instagram_feed": 1.2, "brandconnect": 3.0,
        "commerce_guide": 2.0, "knowledge_evergreen": 1.0,
    }[content_type]
    if "화제글" in topic or "커뮤니티" in topic:
        base_rights += 0.8
    rights_difficulty = max(1.0, min(3.0, round(base_rights, 2)))

    base_freshness = {
        "cardnews": 1.2, "shorts": 1.3, "instagram_feed": 1.3, "brandconnect": 2.0,
        "commerce_guide": 2.8, "knowledge_evergreen": 1.2,
    }[content_type]
    if "LEGAL_REGULATORY_RISK" in risk_tags or "FINANCIAL_RISK" in risk_tags:
        base_freshness += 1.0
    if is_trend_sensitive(topic):
        base_freshness += 1.5
    if any(s in topic for s in ("겨울", "여름", "명절")):
        base_freshness += 0.3
    freshness_risk = max(1.0, min(3.0, round(base_freshness, 2)))

    return {
        "risk_tags": risk_tags,
        "evidence_sourcing_cost": evidence_sourcing_cost,
        "rights_difficulty": rights_difficulty,
        "freshness_risk": freshness_risk,
    }


def cardnews_slides(topic: str, evidence_note: str, risky=None, mobile_risk=None) -> list:
    risky = risky or ["과장된 효과·수치 단정 금지", "미검증 통계 인용 금지", "특정 브랜드 비방 금지"]
    mobile_risk = mobile_risk or "제목 15자 내외, 본문 2문장(약 40자) 이내 유지 시 안전 -- 초과 시 말줄임 위험"
    return [
        {
            "slide": 1, "role": "hook",
            "headline_intent": f"{topic}에 대한 궁금증을 자극하는 한 줄 후킹",
            "body_intent": "공감형 도입 문장 1개, 근거 없이 상황만 제시",
            "evidence_placement": "없음 (후킹 전용 슬라이드)",
            "image_role": "주제를 암시하는 배경 이미지 (fallback 배경 대체 가능)",
            "source_placement": "없음",
            "cta_relation": "다음 슬라이드로 시선 유도, 직접 CTA 없음",
            "risky_claims": risky,
            "mobile_readability_risk": mobile_risk,
        },
        {
            "slide": 2, "role": "problem/context",
            "headline_intent": f"{topic} 관련 구체적 문제 상황 정의",
            "body_intent": "독자가 실제로 겪는 불편을 구체적으로 서술 (추상적 진술 금지)",
            "evidence_placement": "선택 -- 통계를 인용할 경우 출처 표기 필수, 없으면 생략",
            "image_role": "문제 상황을 보여주는 이미지",
            "source_placement": "본문 하단 소형 표기 (근거 인용 시에만)",
            "cta_relation": "해결책에 대한 기대감 조성",
            "risky_claims": risky,
            "mobile_readability_risk": mobile_risk,
        },
        {
            "slide": 3, "role": "evidence-backed solution",
            "headline_intent": f"{topic}의 핵심 해결책 제시",
            "body_intent": evidence_note,
            "evidence_placement": "본문 내 인라인 인용 + 출처 표기 (근거 미확보 시 SOURCE_REQUIRED로 보류)",
            "image_role": "해결책을 시각화하는 이미지",
            "source_placement": "슬라이드 하단 고정 표기",
            "cta_relation": "신뢰 확보 후 다음 CTA 슬라이드로 연결",
            "risky_claims": risky,
            "mobile_readability_risk": mobile_risk,
        },
        {
            "slide": 4, "role": "cta/source",
            "headline_intent": "행동 유도 문구 + 핵심 요약 한 줄",
            "body_intent": "저장/공유/댓글 유도 문구, 새 주장 추가 금지",
            "evidence_placement": "전체 출처 재확인 표기",
            "image_role": "브랜드/CTA 강조 이미지",
            "source_placement": "슬라이드 전체 출처 목록",
            "cta_relation": "직접 CTA (저장 및 공유 유도)",
            "risky_claims": risky,
            "mobile_readability_risk": mobile_risk,
        },
    ]


def classify_readiness(topic: str, base_readiness="offline_ready"):
    if is_regulated(topic):
        return "blocked_by_data", ["SOURCE_REQUIRED", "CURRENT_DATA_REQUIRED"], ["관련 법령/제도의 최신 개정 여부"]
    return base_readiness, [], []


_counter = {}


def next_id(prefix: str) -> str:
    _counter[prefix] = _counter.get(prefix, 0) + 1
    return f"{prefix}-{_counter[prefix]:03d}"


def make_brief(**kwargs) -> dict:
    d = {k: kwargs.get(k) for k in REQUIRED_FIELDS}
    extra = {k: v for k, v in kwargs.items() if k not in REQUIRED_FIELDS}
    d.update(extra)
    return d


def score_priority(evidence_cost, rights_difficulty, freshness_risk, reuse_score, effort,
                    learning_value, monetization_potential, policy_risk_penalty):
    """V1.1 formula: per-topic evidence/rights/freshness + a real reuse_score (computed from
    theme-tag cross-channel membership, see `attach_reuse_scores()`) replace V1's
    category-wide constants, so topics within the same content_type no longer tie."""
    effort_ease = {"low": 2.0, "medium": 1.2, "high": 0.6}[effort]
    score = (
        (4.0 - evidence_cost) * 1.2
        + (4.0 - rights_difficulty) * 1.0
        + (4.0 - freshness_risk) * 1.0
        + reuse_score * 1.5
        + effort_ease
        + learning_value
        + monetization_potential
        - policy_risk_penalty
    )
    score = round(score, 2)
    tier = "P1" if score >= 8 else ("P2" if score >= 5 else "P3")
    return {"tier": tier, "score": score}


# ---------------------------------------------------------------------------
# CardNews (min 25) -- (title, theme_tag)
# ---------------------------------------------------------------------------

CARDNEWS_TOPICS = [
    ("겨울철 난방비 절약 습관 5가지", "ENERGY_SAVING"),
    ("자취생 자산관리 첫걸음", "FRESH_START_FINANCE"),
    ("사무직 목/어깨 통증 스트레칭", "STRETCH_HEALTH"),
    ("연말정산 놓치기 쉬운 공제 항목", "TAX_YEAR_END"),
    ("배달음식 대신 집밥 루틴 만들기", "HOME_COOKING"),
    ("미니멀리즘 시작하는 법", "MINIMALISM"),
    ("신용점수 관리 기본기", "CREDIT_FINANCE"),
    ("여름철 냉방비 절약 습관", "ENERGY_SAVING"),
    ("재택근무 생산성 루틴", "REMOTE_WORK"),
    ("초보자를 위한 홈트레이닝 루틴", "HOME_WORKOUT"),
    ("전세 계약 전 확인할 체크리스트", "HOUSING_CONTRACT"),
    ("이직 준비 서류 체크리스트", "CAREER_MOVE"),
    ("반려동물 첫 입양 준비물", "PET_CARE"),
    ("캠핑 초보 준비물 체크리스트", "CAMPING_TRAVEL_PACK"),
    ("자취방 인테리어 저예산 팁", "BUDGET_INTERIOR"),
    ("여행 전 짐싸기 체크리스트", "CAMPING_TRAVEL_PACK"),
    ("커피 원두 보관법", "COFFEE_RITUAL"),
    ("겨울철 피부 보습 루틴", "SKIN_WINTER_CARE"),
    ("식물 초보 집들이 선물 관리법", "PLANT_CARE"),
    ("명절 선물 예산 관리법", "BUDGET_MANAGEMENT"),
    ("중고거래 사기 예방 체크리스트", "SECONDHAND_SAFETY"),
    ("스마트폰 배터리 수명 관리법", "DEVICE_CARE"),
    ("육아휴직 신청 절차 체크리스트", "PARENTAL_LEAVE"),
    ("자동차 정기점검 체크리스트", "VEHICLE_MAINTENANCE"),
    ("온라인 강의 완주하는 습관", "LEARNING_HABIT"),
]


def build_cardnews_briefs():
    briefs = []
    for topic, theme in CARDNEWS_TOPICS:
        readiness, blockers, volatile = classify_readiness(topic)
        assess = assess_topic(topic, "cardnews")
        forbidden = ["효능·치료 효과 단정", "미검증 통계 인용", "특정 브랜드 비방", "순위/판매량 단정"]
        if is_health(topic):
            forbidden.append("의학적 효과 단정 (일반 정보 수준 유지)")
        evidence_note = f"{topic}에 대한 실행 가능한 단계 2~3개, 각 단계에 근거(전문가 코멘트/공식 자료/통계) 배치"
        source_type = "공식 정부·기관 자료 또는 전문가 검수" if is_regulated(topic) else "일반 공개 자료 또는 사내 작성 상식 (전문가 검수 권장)"
        cid = next_id("CN")
        b = make_brief(
            content_id=cid, content_type="cardnews", channel="instagram_cardnews", category="lifestyle_evergreen",
            working_title=topic, audience="20~30대 자취생·직장인 중심 일반 인스타그램 팔로워",
            problem=f"{topic}에 대해 무엇부터 시작해야 할지 막막한 독자",
            promise=f"{topic}을(를) 오늘 바로 실행 가능한 체크리스트로 정리해준다",
            hook=f"{topic}, 이것부터 확인하세요",
            core_question=f"{topic}, 어디서부터 시작해야 할까?",
            story_structure="hook-problem-solution-cta (canonical 4-slide CardNews contract, CardNewsModule Pillow renderer 재사용)",
            slide_or_scene_roles=cardnews_slides(topic, evidence_note),
            cta="저장 및 공유 유도 (문의/방문 유도 없음, 조직형 CTA 아님)",
            evidence_needed="일반 상식 수준 초과 시 전문가 코멘트 또는 공식 자료 1건 이상" if not is_regulated(topic) else "최신 공식 자료/법령 근거 필수",
            source_type_needed=source_type,
            image_or_asset_needed="CardNewsModule 배경 fallback 또는 라이선스 확인된 사진/일러스트 1종",
            rights_status_required="이미지 사용 시 라이선스 확인 필요 (RIGHTS_REVIEW_REQUIRED), 본문 텍스트는 자체 작성",
            volatile_claims=volatile,
            forbidden_claims=forbidden,
            manual_review=True,
            monetization_route="직접 수익화 없음 (저장/공유 기반 도달 확대, 추후 Commerce 가이드 연계 후보)",
            disclosure_required=False,
            freshness_window="계절 항목은 연 1회 갱신 권장, 그 외 evergreen (낮은 계절성)" if any(s in topic for s in ("겨울", "여름", "명절")) else "evergreen (계절성 낮음)",
            fallback_behavior="실시간 근거 확보 실패 시 일반 상식 수준으로 축소하고 근거 필요 항목은 게시 보류",
            reusable_pattern_tags=["checklist_hook", "lifestyle_evergreen"],
            priority=None,  # finalized in attach_reuse_scores()
            effort="low",
            expected_learning_value="medium",
            current_readiness=readiness,
            blocker_codes=blockers,
            theme_tag=theme,
            risk_tags=assess["risk_tags"],
            evidence_sourcing_cost=assess["evidence_sourcing_cost"],
            rights_difficulty=assess["rights_difficulty"],
            freshness_risk=assess["freshness_risk"],
            _learning_value_num=1.5, _monetization_num=0.8, _policy_penalty=0.3,
        )
        briefs.append(b)
    return briefs


# ---------------------------------------------------------------------------
# Shorts / Reels (min 20)
# ---------------------------------------------------------------------------

SHORTS_TOPICS = [
    ("3초 만에 알아보는 냉장고 정리법", "FRIDGE_ORGANIZE"),
    ("출근길 5분 스트레칭", "STRETCH_HEALTH"),
    ("자취생 냉장고 파먹기 레시피", "HOME_COOKING"),
    ("하루 만보 걷기 루틴 브이로그형", "HOME_WORKOUT"),
    ("방 정리 비포애프터", "MINIMALISM"),
    ("커피 내리는 법 3단계", "COFFEE_RITUAL"),
    ("무지출 챌린지 하루", "NO_SPEND_CHALLENGE"),
    ("겨울 이불 빨래 타이밍", "LAUNDRY_CARE"),
    ("스마트폰 사진 잘 찍는 각도", "PHOTO_SKILL"),
    ("손빨래 필요한 옷 구분법", "LAUNDRY_CARE"),
    ("아침 루틴 5분 요약", "MORNING_ROUTINE"),
    ("자기 전 스트레칭 3동작", "STRETCH_HEALTH"),
    ("택배 상자 재활용 아이디어", "RECYCLE_UPCYCLE"),
    ("편의점 다이어트 조합", "HOME_WORKOUT"),
    ("자취 초보 요리 3분 완성", "HOME_COOKING"),
    ("지갑 정리 미니멀 챌린지", "MINIMALISM"),
    ("반려동물 산책 준비물 점검", "PET_CARE"),
    ("캐리어 짐싸기 순서", "CAMPING_TRAVEL_PACK"),
    ("책상 정리 루틴", "MINIMALISM"),
    ("다이소템으로 수납 정리", "MINIMALISM"),
]


def build_shorts_briefs():
    briefs = []
    for topic, theme in SHORTS_TOPICS:
        readiness, blockers, volatile = classify_readiness(topic, base_readiness="offline_ready")
        assess = assess_topic(topic, "shorts")
        forbidden = ["효능 단정", "미검증 통계", "실제 조회수/참여 데이터 언급"]
        if is_health(topic):
            forbidden.append("의학적 효과 단정")
        cid = next_id("SH")
        b = make_brief(
            content_id=cid, content_type="shorts", channel="instagram_reels_or_youtube_shorts", category="short_form_lifestyle",
            working_title=topic, audience="20~30대, 짧은 영상 소비 위주 팔로워",
            problem=f"{topic}을(를) 빠르게 확인하고 싶지만 긴 설명은 보기 싫은 시청자",
            promise=f"{topic}을(를) 15~45초 안에 핵심만 보여준다",
            hook=f"{topic}, 3초 안에 보여드릴게요",
            core_question=f"{topic}, 제일 빠른 방법은?",
            story_structure="3초 hook - 상황 제시 - 핵심 행동 2~3단계 - 마무리/CTA",
            slide_or_scene_roles=[
                {"scene": 1, "role": "hook", "duration_sec": "0-3", "visual": f"{topic} 결과물 미리보기"},
                {"scene": 2, "role": "context", "duration_sec": "3-10", "visual": "문제 상황 또는 시작 전 상태"},
                {"scene": 3, "role": "core_steps", "duration_sec": "10-35", "visual": "단계별 실행 장면 2~3컷"},
                {"scene": 4, "role": "cta", "duration_sec": "35-45", "visual": "완성 결과 + 저장/팔로우 유도 자막"},
            ],
            cta="저장/팔로우 유도, 실제 게시 여부는 담당 팀 수동 결정",
            evidence_needed="실행 장면 자체가 근거 (실사 촬영 필요, 통계 인용 불필요한 실연형 콘텐츠)",
            source_type_needed="자체 촬영 소재, 통계 인용 시 공식 자료",
            image_or_asset_needed="실사 촬영 또는 라이선스 확인된 B-roll 소재 (현재 자동 촬영/렌더링 없음)",
            rights_status_required="자체 촬영 소재만 사용, 스톡 소재는 라이선스 확인 필요 (RIGHTS_REVIEW_REQUIRED)",
            volatile_claims=volatile,
            forbidden_claims=forbidden,
            manual_review=True,
            monetization_route="직접 수익화 없음 (도달 확대), Commerce 연계는 후속 Sprint 대상",
            disclosure_required=False,
            freshness_window="evergreen (계절 소재는 촬영 시점 재확인)",
            fallback_behavior="촬영 소재 확보 실패 시 스토리보드만 보존하고 실제 촬영/제작은 보류",
            reusable_pattern_tags=["short_hook", "checklist_visual"],
            priority=None,
            effort="medium",
            expected_learning_value="medium",
            current_readiness=readiness,
            blocker_codes=blockers,
            theme_tag=theme,
            risk_tags=assess["risk_tags"],
            evidence_sourcing_cost=assess["evidence_sourcing_cost"],
            rights_difficulty=assess["rights_difficulty"],
            freshness_risk=assess["freshness_risk"],
            _learning_value_num=1.5, _monetization_num=1.0, _policy_penalty=0.3,
            shorts_extra={
                "hook_3sec": f"{topic} 결과물을 첫 장면에 보여주는 3초 훅",
                "expected_length_sec": "15-45",
                "narration_intent": "짧고 명령형 문장, 정보 전달 우선",
                "subtitle_intent": "화면 하단 고정, 핵심 단어 강조",
                "required_visual_assets": "자체 촬영 원본 클립 2~4개",
                "music_or_tts_needed": "선택 (자체 음원 사용 시 라이선스 확인 필수, TTS는 후속 Sprint 대상)",
                "provenance_gate": "촬영자/소유권 확인 없는 소재는 render_allowed=false",
                "render_dependency": "영상 편집/렌더링은 현재 자동화 없음 -- 담당 팀 수동 편집 필요",
                "manual_upload_checklist": ["소재 촬영 완료 확인", "자막/내레이션 스크립트 검수", "음원 라이선스 확인", "플랫폼 정책 검토 후 수동 업로드"],
                "unsupported_automation_boundary": "영상/음성/음악 자동 생성, 자동 게시, 자동 자막 생성은 이번 자산에 포함되지 않음",
            },
        )
        briefs.append(b)
    return briefs


# ---------------------------------------------------------------------------
# Instagram feed / informational (min 20)
# ---------------------------------------------------------------------------

INSTAGRAM_TOPICS = [
    ("이번 주 트렌드 키워드 요약 카드", "TREND_INTERPRETATION"),
    ("자주 틀리는 맞춤법 모음", "LANGUAGE_LITERACY"),
    ("알아두면 좋은 소비자 권리 상식", "CONSUMER_RIGHTS"),
    ("계절 환절기 건강 상식", "SEASONAL_HEALTH"),
    ("생활 속 에너지 절약 팁", "ENERGY_SAVING"),
    ("자취생 필수 앱 모음", "APP_TOOLS"),
    ("문화생활 예산 관리 팁", "BUDGET_MANAGEMENT"),
    ("온라인 쇼핑 환불 규정 상식", "CONSUMER_RIGHTS"),
    ("직장인 점심시간 활용법", "REMOTE_WORK"),
    ("반려동물 상식 퀴즈형 카드", "PET_CARE"),
    ("계절 별미 재료 알아보기", "SEASONAL_FOOD"),
    ("생활 속 안전 상식", "SECONDHAND_SAFETY"),
    ("자기계발 습관 만들기 팁", "LEARNING_HABIT"),
    ("요즘 유행하는 인테리어 스타일", "BUDGET_INTERIOR"),
    ("알아두면 유용한 세금 용어", "TAX_YEAR_END"),
    ("신조어 뜻 알아보기", "TREND_INTERPRETATION"),
    ("자취생 냉장고 관리 상식", "FRIDGE_ORGANIZE"),
    ("계절 옷 정리 상식", "RECYCLE_UPCYCLE"),
    ("생활 속 절약 챌린지 소개", "NO_SPEND_CHALLENGE"),
    ("커뮤니티 화제글 요약 카드 (해석형)", "TREND_INTERPRETATION"),
]


def build_instagram_briefs():
    briefs = []
    for topic, theme in INSTAGRAM_TOPICS:
        readiness, blockers, volatile = classify_readiness(topic)
        assess = assess_topic(topic, "instagram_feed")
        is_trend_summary = is_trend_sensitive(topic)
        if is_trend_summary:
            volatile = volatile + ["원문 인용 시점의 정확성 (최신 트렌드는 시의성 유효기간이 짧음)"]
            blockers = list(dict.fromkeys(blockers + ["SOURCE_REQUIRED"]))
        forbidden = ["미검증 최신 사실 단정", "커뮤니티 의견을 확정 사실로 서술", "실제 성과/순위 언급"]
        cid = next_id("IG")
        b = make_brief(
            content_id=cid, content_type="instagram_feed", channel="instagram_feed", category="informational_feed",
            working_title=topic, audience="일반 인스타그램 팔로워, 정보성 콘텐츠 소비층",
            problem=f"{topic}에 대해 짧고 정확하게 알고 싶은 독자",
            promise=f"{topic}을(를) 카드 3~5장 또는 단일 피드로 요약 전달한다",
            hook=f"{topic}, 알고 계셨나요?",
            core_question=f"{topic}, 핵심만 정리하면?",
            story_structure="정보 요약형 카드 3~5장 또는 단일 피드 이미지+캡션 구조",
            slide_or_scene_roles=[
                {"slide": 1, "role": "hook", "content_intent": f"{topic} 관련 흥미 유발 문장"},
                {"slide": 2, "role": "core_info", "content_intent": "핵심 정보 1~3개, 출처 필요 시 표기"},
                {"slide": 3, "role": "detail_or_example", "content_intent": "구체 예시 또는 추가 설명"},
                {"slide": 4, "role": "cta_or_summary", "content_intent": "요약 + 저장/공유 유도"},
            ],
            cta="저장/공유/댓글 유도",
            evidence_needed="원문 커뮤니티/뉴스 인용 시 원문 링크 및 라벨링 필수" if is_trend_summary else "일반 상식 수준, 필요 시 공식 자료 1건",
            source_type_needed="공식 정부·기관 자료 또는 전문가 검수" if is_regulated(topic) else "공개 커뮤니티/뉴스 출처 (원문 라벨링 필수)" if is_trend_summary else "일반 공개 자료",
            image_or_asset_needed="정보 요약형 카드 배경 또는 라이선스 확인된 이미지",
            rights_status_required="커뮤니티 원문 인용 시 출처 명시 및 PII 마스킹 필수 (RIGHTS_REVIEW_REQUIRED)",
            volatile_claims=volatile,
            forbidden_claims=forbidden,
            manual_review=True,
            monetization_route="직접 수익화 없음 (계정 신뢰도/도달 확대)",
            disclosure_required=False,
            freshness_window="1~2주 이내 시의성 유효" if is_trend_summary else "evergreen (계절성 낮음)",
            fallback_behavior="원문/근거 확보 실패 시 게시 보류, '커뮤니티 의견' 라벨 없이 사실처럼 서술하지 않음",
            reusable_pattern_tags=["info_card", "trend_summary" if is_trend_summary else "evergreen_info"],
            priority=None,
            effort="low",
            expected_learning_value="medium",
            current_readiness=readiness,
            blocker_codes=blockers,
            theme_tag=theme,
            risk_tags=assess["risk_tags"],
            evidence_sourcing_cost=assess["evidence_sourcing_cost"],
            rights_difficulty=assess["rights_difficulty"],
            freshness_risk=assess["freshness_risk"],
            _learning_value_num=1.5, _monetization_num=0.8, _policy_penalty=0.3,
        )
        briefs.append(b)
    return briefs


# ---------------------------------------------------------------------------
# BrandConnect (min 15)
# ---------------------------------------------------------------------------

BRANDCONNECT_TOPICS = [
    ("신제품 언박싱 카드뉴스 패키지", "BRANDCONNECT_PACKAGE"),
    ("브랜드 스토리텔링 카드뉴스", "BRANDCONNECT_PACKAGE"),
    ("사용 후기형 콜라보 콘텐츠", "BRANDCONNECT_PACKAGE"),
    ("비교체험단형 콘텐츠 패키지", "BRANDCONNECT_PACKAGE"),
    ("시즌 프로모션 카드뉴스", "BRANDCONNECT_PACKAGE"),
    ("브랜드 챌린지 참여 유도 콘텐츠", "BRANDCONNECT_PACKAGE"),
    ("제품 사용법 튜토리얼 콘텐츠", "BRANDCONNECT_PACKAGE"),
    ("브랜드 앰버서더 소개 콘텐츠", "BRANDCONNECT_PACKAGE"),
    ("오프라인 매장 방문 후기 콘텐츠", "BRANDCONNECT_PACKAGE"),
    ("브랜드 협찬 이벤트 안내 콘텐츠", "BRANDCONNECT_PACKAGE"),
    ("신제품 출시 카운트다운 콘텐츠", "BRANDCONNECT_PACKAGE"),
    ("브랜드 가치 공감형 콘텐츠", "BRANDCONNECT_PACKAGE"),
    ("고객 후기 큐레이션 콘텐츠", "BRANDCONNECT_PACKAGE"),
    ("브랜드 굿즈 소개 콘텐츠", "BRANDCONNECT_PACKAGE"),
    ("B2B 파트너십 소개 콘텐츠", "BRANDCONNECT_PACKAGE"),
]


def bc_deliverable_profile(topic: str) -> dict:
    """BrandConnect-specific complexity differentiator. V1 scored all 15 BrandConnect
    briefs identically because assess_topic() only varied by content_type, and every
    BrandConnect brief shares content_type='brandconnect'. This adds a deliverable-type
    complexity signal (participant count, rights surface, production overhead) so the
    15 package types are no longer indistinguishable in priority."""
    if "B2B" in topic or "파트너십" in topic:
        return {"rights_delta": 0.4, "evidence_delta": 0.3, "reach_multiplier": 0.6}
    if "체험단" in topic:
        return {"rights_delta": 0.5, "evidence_delta": 0.2, "reach_multiplier": 1.0}
    if "앰버서더" in topic or "매장 방문" in topic:
        return {"rights_delta": 0.4, "evidence_delta": 0.1, "reach_multiplier": 1.0}
    if "카운트다운" in topic or "이벤트 안내" in topic:
        return {"rights_delta": -0.2, "evidence_delta": -0.2, "reach_multiplier": 1.2}
    if "굿즈" in topic or "사용법 튜토리얼" in topic:
        return {"rights_delta": -0.3, "evidence_delta": -0.2, "reach_multiplier": 1.0}
    if "후기" in topic or "큐레이션" in topic:
        return {"rights_delta": 0.1, "evidence_delta": 0.0, "reach_multiplier": 1.1}
    if "챌린지" in topic:
        return {"rights_delta": -0.1, "evidence_delta": 0.1, "reach_multiplier": 1.3}
    if "스토리텔링" in topic or "가치 공감형" in topic:
        return {"rights_delta": 0.0, "evidence_delta": 0.3, "reach_multiplier": 0.9}
    return {"rights_delta": -0.1, "evidence_delta": -0.1, "reach_multiplier": 1.1}


def build_brandconnect_briefs():
    briefs = []
    for topic, theme in BRANDCONNECT_TOPICS:
        assess = assess_topic(topic, "brandconnect")
        profile = bc_deliverable_profile(topic)
        assess["rights_difficulty"] = max(1.0, min(3.0, round(assess["rights_difficulty"] + profile["rights_delta"], 2)))
        assess["evidence_sourcing_cost"] = max(1.0, min(3.0, round(assess["evidence_sourcing_cost"] + profile["evidence_delta"], 2)))
        cid = next_id("BC")
        b = make_brief(
            content_id=cid, content_type="brandconnect", channel="instagram_sponsored", category="brandconnect_campaign",
            working_title=topic, audience="브랜드 타겟 오디언스 (실제 브랜드 계약 성사 후 확정)",
            problem="실제 브랜드 계약 없이는 캠페인 목표/타겟을 확정할 수 없음",
            promise=f"{topic} 형태의 캠페인 패키지 구조를 사전 설계해 계약 성사 시 즉시 착수 가능하게 한다",
            hook="(브랜드 확정 후 작성 -- 가상 브랜드 사실 생성 금지)",
            core_question="이 캠페인이 브랜드와 오디언스 양쪽에 어떤 가치를 주는가?",
            story_structure="brandconnect_package_builder/brandconnect_contract 계약 재사용, 4슬라이드 또는 캠페인 유형별 구조",
            slide_or_scene_roles=[
                {"slide": 1, "role": "brand_intro_or_hook", "content_intent": "브랜드/캠페인 소개 (실제 브랜드 확정 후)"},
                {"slide": 2, "role": "product_or_value_context", "content_intent": "제품/가치 제안 맥락"},
                {"slide": 3, "role": "evidence_or_claim", "content_intent": "브랜드 제공 근거 자료 기반 설명만 (자체 추정 금지)"},
                {"slide": 4, "role": "cta_and_disclosure", "content_intent": "CTA + 협찬 disclosure 동시 표기"},
            ],
            cta="브랜드 계약 조건에 따른 CTA (구매/방문/참여), 실제 실행은 승인 후",
            evidence_needed="브랜드 제공 공식 자료/제품 사실만 사용, 자체 추정 금지",
            source_type_needed="브랜드 공식 제공 자료 또는 브랜드 승인 문서",
            image_or_asset_needed="브랜드 제공 이미지/영상 (자체 촬영 시 브랜드 승인 필요)",
            rights_status_required="브랜드 제공 자산 사용권 및 초상권/상표권 확인 필수 (RIGHTS_REVIEW_REQUIRED)",
            volatile_claims=["제품 가격/혜택/기간 한정 정보"],
            forbidden_claims=["가상 브랜드 사실 생성", "브랜드 미확인 효능 주장", "허위 긴급성/한정 표현"],
            manual_review=True,
            monetization_route="브랜드 계약 성사 시 스폰서십 수익 (현재 가상 브랜드 없음, 실제 계약 전 미실행)",
            disclosure_required=True,
            freshness_window="캠페인 기간 한정 (브랜드 계약에 따름)",
            fallback_behavior="브랜드 계약 부재 시 패키지 구조만 보존하고 실제 콘텐츠 제작 보류",
            reusable_pattern_tags=["brandconnect_package", "sponsored_disclosure"],
            priority=None,
            effort="high",
            expected_learning_value="medium",
            current_readiness="not_approved",
            blocker_codes=["OPERATOR_APPROVAL_REQUIRED", "RIGHTS_REVIEW_REQUIRED", "PLATFORM_POLICY_REVIEW_REQUIRED"],
            theme_tag=theme,
            risk_tags=assess["risk_tags"],
            evidence_sourcing_cost=assess["evidence_sourcing_cost"],
            rights_difficulty=assess["rights_difficulty"],
            freshness_risk=assess["freshness_risk"],
            _learning_value_num=round(1.2 * profile["reach_multiplier"], 2),
            _monetization_num=round(1.8 * profile["reach_multiplier"], 2),
            _policy_penalty=1.5,
            brandconnect_extra={
                "campaign_objective": "브랜드 계약 확정 후 정의 (인지도/전환/참여 중 브랜드와 합의)",
                "brand_fit": "OPERATOR_APPROVAL_REQUIRED",
                "audience_fit": "OPERATOR_APPROVAL_REQUIRED",
                "deliverable_type": topic,
                "mandatory_claim_evidence": "브랜드 제공 공식 자료로만 주장 구성, 자체 추정 금지",
                "prohibited_claims": ["가상 브랜드 사실", "미확인 효능", "허위 긴급성"],
                "sponsorship_disclosure": "모든 슬라이드/캡션에 협찬 표기 (#광고 + 본문 내 문구) 필수",
                "image_video_rights": "브랜드 제공 자산만 사용, 자체 촬영 시 브랜드 서면 승인 필요",
                "approval_chain": ["브랜드 담당자 1차 승인", "운영자 최종 승인", "게시 전 최종 검수"],
                "revision_checkpoints": ["기획안 승인", "초안 승인", "최종본 승인"],
                "measurement_proposal": "실제 계약 후 브랜드와 합의된 지표만 사용 (가상 성과 지표 생성 금지)",
                "actual_campaign_execution_gate": "실제 브랜드 계약 + 운영자 승인 + 플랫폼 정책 검토 전까지 실행 불가",
            },
        )
        briefs.append(b)
    return briefs


# ---------------------------------------------------------------------------
# Commerce guides / comparisons (min 20)
# ---------------------------------------------------------------------------

COMMERCE_TOPICS = [
    ("겨울철 가습기 고르는 기준 가이드", "HOME_APPLIANCE_GUIDE"),
    ("자취생 전자레인지 비교 가이드", "HOME_APPLIANCE_GUIDE"),
    ("홈트레이닝 매트 고르는 법", "HOME_WORKOUT"),
    ("캠핑 초보 텐트 고르는 기준", "CAMPING_TRAVEL_PACK"),
    ("노트북 거치대 비교 가이드", "DEVICE_CARE"),
    ("무선 이어폰 고르는 기준", "AUDIO_GEAR"),
    ("커피머신 종류별 비교", "COFFEE_RITUAL"),
    ("침구 소재별 비교 가이드", "BEDDING"),
    ("공기청정기 고르는 기준", "HOME_APPLIANCE_GUIDE"),
    ("자취생 미니 냉장고 비교", "HOME_APPLIANCE_GUIDE"),
    ("아이 학용품 구매 가이드", "KIDS_SUPPLIES"),
    ("반려동물 사료 고르는 기준", "PET_CARE"),
    ("러닝화 고르는 기준", "HOME_WORKOUT"),
    ("USB 허브 비교 가이드", "DEVICE_CARE"),
    ("텀블러 소재별 비교", "TUMBLER"),
    ("전기포트 고르는 기준", "HOME_APPLIANCE_GUIDE"),
    ("스탠드 조명 비교 가이드", "LIGHTING"),
    ("여행용 캐리어 고르는 기준", "CAMPING_TRAVEL_PACK"),
    ("주방 칼 세트 비교 가이드", "KITCHEN_TOOLS"),
    ("데스크 매트 비교 가이드", "MINIMALISM"),
]


def build_commerce_briefs():
    briefs = []
    for topic, theme in COMMERCE_TOPICS:
        assess = assess_topic(topic, "commerce_guide")
        cid = next_id("CM")
        b = make_brief(
            content_id=cid, content_type="commerce_guide", channel="instagram_cardnews_or_blog", category="purchase_guide_comparison",
            working_title=topic, audience="구매를 고민 중인 일반 소비자",
            problem=f"{topic}이 필요하지만 어떤 기준으로 골라야 할지 모르는 소비자",
            promise=f"{topic}에 대한 비교 기준을 실제 상품 없이도 먼저 이해시킨다",
            hook=f"{topic}, 기준부터 알고 고르세요",
            core_question=f"{topic}, 무엇을 먼저 비교해야 할까?",
            story_structure="hook-비교 기준 제시-기준별 설명-구매 전 체크리스트 CTA",
            slide_or_scene_roles=[
                {"slide": 1, "role": "hook", "content_intent": f"{topic} 구매 전 흔한 실수 제시"},
                {"slide": 2, "role": "comparison_criteria", "content_intent": "소재/사양/용도 등 안정적 기준 나열 (가격·재고 제외)"},
                {"slide": 3, "role": "criteria_detail", "content_intent": "기준별 구체 설명, 실제 상품명/가격 미포함"},
                {"slide": 4, "role": "cta_checklist", "content_intent": "구매 전 확인 체크리스트 + 가격/재고는 확인 필요 표기"},
            ],
            cta="비교 기준 저장 유도, 실제 구매 링크/추천 없음 (제품 확보 전까지)",
            evidence_needed="일반 사양/소재 지식은 공개 자료 기반, 실제 상품 데이터는 SOURCE_REQUIRED",
            source_type_needed="공식 제조사 자료 또는 검증된 리뷰 사이트 (실제 상품 연결 시)",
            image_or_asset_needed="실제 상품 이미지 미사용 (현재), 일반 카테고리 일러스트만 사용",
            rights_status_required="실제 상품 이미지 사용 시 제조사/판매자 권리 확인 필수 (RIGHTS_REVIEW_REQUIRED)",
            volatile_claims=["가격", "재고", "배송 조건", "할인율"],
            forbidden_claims=["실제 가격", "할인율", "재고", "판매량/순위", "리뷰 수/평점", "효능 단정"],
            manual_review=True,
            monetization_route="제품 확보 및 계약 승인 후 affiliate 전환 후보 (현재 링크 없음)",
            disclosure_required=True,
            freshness_window="비교 기준 자체는 evergreen, 실제 상품 데이터는 PRICE_VERIFICATION_REQUIRED 기준 매번 재확인",
            fallback_behavior="실제 상품 데이터 없이는 비교 기준 설명까지만 진행, 특정 상품 추천 및 구매 유도는 보류",
            reusable_pattern_tags=["commerce_comparison_criteria", "cardnews_reusable"],
            priority=None,
            effort="medium",
            expected_learning_value="high",
            current_readiness="planning_only",
            blocker_codes=["SOURCE_REQUIRED", "PRICE_VERIFICATION_REQUIRED", "RIGHTS_REVIEW_REQUIRED"],
            theme_tag=theme,
            risk_tags=assess["risk_tags"],
            evidence_sourcing_cost=assess["evidence_sourcing_cost"],
            rights_difficulty=assess["rights_difficulty"],
            freshness_risk=assess["freshness_risk"],
            _learning_value_num=1.5, _monetization_num=1.8, _policy_penalty=1.2,
            commerce_extra={
                "stable_product_facts": "카테고리 일반 사양/소재/용도 지식 (특정 상품 미지정)",
                "volatile_price_stock_shipping_facts": "PRICE_VERIFICATION_REQUIRED -- 실제 상품 연결 전까지 미포함",
                "comparison_criteria": "소재, 용량/사양, 관리 난이도, 용도 적합성 (가격 제외 4~5개 기준)",
                "required_seller_product_sources": "실제 판매자/제조사 소스 연결 전까지 없음",
                "image_rights": "실제 상품 이미지는 제조사/판매자 권리 확인 후에만 사용",
                "affiliate_disclosure": "실제 링크 연결 시 모든 게시물에 제휴 표기 필수",
                "stale_data_behavior": "가격/재고 정보가 확인 시점보다 오래되면 unavailable 처리",
                "unavailable_behavior": "확인되지 않은 값은 '확인 필요'로 표기, 추정치 금지",
                "purchase_cta_approval_gate": "실제 상품/링크 확보 + 운영자 승인 전까지 구매 유도 CTA 비활성",
            },
        )
        briefs.append(b)
    return briefs


# ---------------------------------------------------------------------------
# Knowledge / Evergreen (min 20)
# ---------------------------------------------------------------------------

KNOWLEDGE_TOPICS = [
    ("신용카드 vs 체크카드 차이", "CREDIT_FINANCE"),
    ("전세 vs 월세 장단점", "HOUSING_CONTRACT"),
    ("파레토 법칙 실생활 적용", "PRODUCTIVITY_CONCEPT"),
    ("습관 형성 21일 법칙 진실", "LEARNING_HABIT"),
    ("SNS 알고리즘 기본 원리", "TREND_INTERPRETATION"),
    ("이메일 작성 기본 매너", "WORKPLACE_COMM"),
    ("회의록 작성 기본기", "WORKPLACE_COMM"),
    ("시간관리 매트릭스 활용법", "REMOTE_WORK"),
    ("재무제표 기초 용어", "CREDIT_FINANCE"),
    ("브랜드와 트렌드의 차이", "MARKETING_LITERACY"),
    ("콘텐츠 마케팅 기본 개념", "MARKETING_LITERACY"),
    ("데이터 문해력 기초", "MARKETING_LITERACY"),
    ("협상의 기본 원칙", "WORKPLACE_COMM"),
    ("프레젠테이션 구성 기본", "WORKPLACE_COMM"),
    ("이력서 작성 기본 원칙", "CAREER_MOVE"),
    ("저작권 기초 상식", "LEGAL_PRIVACY_BASICS"),
    ("개인정보보호 기본 상식", "LEGAL_PRIVACY_BASICS"),
    ("구독경제 이해하기", "SUBSCRIPTION_ECONOMY"),
    ("디지털 디톡스 실천법", "DIGITAL_WELLBEING"),
    ("리더십 기본 원칙", "WORKPLACE_COMM"),
]


def build_knowledge_briefs():
    briefs = []
    for topic, theme in KNOWLEDGE_TOPICS:
        readiness, blockers, volatile = classify_readiness(topic)
        assess = assess_topic(topic, "knowledge_evergreen")
        cid = next_id("KN")
        b = make_brief(
            content_id=cid, content_type="knowledge_evergreen", channel="instagram_feed_or_blog", category="concept_explainer",
            working_title=topic, audience="자기계발/실용지식에 관심 있는 20~40대",
            problem=f"{topic}에 대해 정확히 알지 못한 채 사용하는 독자",
            promise=f"{topic}을(를) 쉬운 언어로 정확하게 설명한다",
            hook=f"{topic}, 정확히 알고 계신가요?",
            core_question=f"{topic}, 핵심 차이/원리는 무엇인가?",
            story_structure="개념 정의-핵심 차이/원리 설명-실생활 적용 예시-요약 CTA",
            slide_or_scene_roles=[
                {"slide": 1, "role": "hook", "content_intent": f"{topic}에 대한 흔한 오해 제시"},
                {"slide": 2, "role": "concept_definition", "content_intent": "정확한 정의, 필요 시 공식 자료 인용"},
                {"slide": 3, "role": "practical_application", "content_intent": "실생활 적용 예시"},
                {"slide": 4, "role": "cta_summary", "content_intent": "핵심 요약 + 저장 유도"},
            ],
            cta="저장/공유 유도",
            evidence_needed="법률/금융/저작권/개인정보 관련은 공식 자료 필수, 일반 개념은 통용 정의 사용" if is_regulated(topic) else "통용되는 개념 정의 수준, 필요 시 출처 1건",
            source_type_needed="공식 정부·기관 자료 또는 전문 서적/자료" if is_regulated(topic) else "일반 공개 자료",
            image_or_asset_needed="개념 설명용 인포그래픽 스타일 이미지",
            rights_status_required="이미지 자체 제작 우선, 참고 자료 인용 시 출처 표기 (RIGHTS_REVIEW_REQUIRED 해당 시)",
            volatile_claims=volatile,
            forbidden_claims=["미검증 통계 인용", "법률/금융 정보를 개정 여부 확인 없이 단정"],
            manual_review=True,
            monetization_route="직접 수익화 없음 (계정 전문성/신뢰도 축적)",
            disclosure_required=False,
            freshness_window="evergreen, 법률/금융 관련은 연 1회 이상 재검수 권장" if is_regulated(topic) else "evergreen (개정 위험 낮음)",
            fallback_behavior="공식 근거 확보 실패 시 게시 보류 또는 '일반적으로 알려진 정의' 수준으로 명시",
            reusable_pattern_tags=["concept_explainer", "evergreen_knowledge"],
            priority=None,
            effort="low",
            expected_learning_value="high",
            current_readiness=readiness,
            blocker_codes=blockers,
            theme_tag=theme,
            risk_tags=assess["risk_tags"],
            evidence_sourcing_cost=assess["evidence_sourcing_cost"],
            rights_difficulty=assess["rights_difficulty"],
            freshness_risk=assess["freshness_risk"],
            _learning_value_num=1.8, _monetization_num=0.8, _policy_penalty=0.3,
        )
        briefs.append(b)
    return briefs


def attach_reuse_scores_and_priority(briefs):
    """Second pass: compute a real per-topic reuse_score from theme_tag membership across
    distinct content_types, then finalize each brief's `priority` using the V1.1 formula.
    This is what actually breaks the V1 tie -- reuse_score varies per topic based on real
    theme-sharing, not a category-wide constant."""
    theme_channels = {}
    for b in briefs:
        theme_channels.setdefault(b["theme_tag"], set()).add(b["content_type"])

    for b in briefs:
        other_channels = theme_channels[b["theme_tag"]] - {b["content_type"]}
        reuse_score = min(3, len(other_channels))
        b["reuse_score"] = reuse_score
        b["priority"] = score_priority(
            b["evidence_sourcing_cost"], b["rights_difficulty"], b["freshness_risk"],
            reuse_score, b["effort"], b.pop("_learning_value_num"), b.pop("_monetization_num"),
            b.pop("_policy_penalty"),
        )
    return briefs


# ---------------------------------------------------------------------------
# Learning seed patterns (min 90: 15/10/10/10/10/10/5/20)
# ---------------------------------------------------------------------------

def pattern(pid_prefix, ptype, channels, hypothesis, expected_effect, required_evidence,
            validation_method, promotion_threshold, rejection_condition, status):
    return {
        "pattern_id": next_id(pid_prefix), "pattern_type": ptype, "applicable_channels": channels,
        "hypothesis": hypothesis, "expected_effect": expected_effect, "required_evidence": required_evidence,
        "validation_method": validation_method, "promotion_threshold": promotion_threshold,
        "rejection_condition": rejection_condition, "status": status,
    }


def build_patterns():
    patterns = []
    hook_hyps = [
        "숫자+기간 조합 후킹(예: '3일 만에 정리 끝내는 법')이 일반 진술형보다 저장 유도에 효과적일 것이다",
        "질문형 후킹이 진술형보다 스크롤 정지율이 높을 것이다",
        "'나만 몰랐던' 류의 결핍 프레이밍이 공감형 후킹보다 클릭 유도에 효과적일 것이다",
        "체크리스트형 후킹('~확인하셨나요?')이 저장 유도에 특히 효과적일 것이다",
        "반전형 후킹('다들 이렇게 하지만 사실은...')이 일반 정보형보다 완독률이 높을 것이다",
        "계절/시의성 키워드가 포함된 후킹이 비계절 후킹보다 초기 도달이 높을 것이다",
        "손실 프레이밍('이거 놓치면 손해')이 이득 프레이밍보다 저장 유도에 강할 것이다",
        "자취생/1인가구처럼 구체적 타겟 명시가 범용 타겟보다 공감 지속시간이 길 것이다",
        "첫 문장에 문제 상황을 구체 묘사하는 후킹이 추상적 진술보다 완독률이 높을 것이다",
        "'3초 안에' 류의 즉시성 강조 후킹이 Shorts 이탈률을 낮출 것이다",
        "비교형 후킹('A vs B')이 단일 정보형보다 댓글 유도에 효과적일 것이다",
        "후킹 문장 길이가 15자 이내일 때 모바일 완독 진입률이 더 높을 것이다",
        "커뮤니티 화제 인용형 후킹(출처 표기 전제)이 자체 제작 후킹보다 초기 반응이 빠를 것이다",
        "자기효능감 자극형 후킹('당신도 할 수 있는')이 정보 나열형보다 저장 유도에 효과적일 것이다",
        "체크리스트 개수를 후킹에 명시('5가지')하는 것이 개수 미표기보다 클릭률이 높을 것이다",
    ]
    for h in hook_hyps:
        patterns.append(pattern(
            "HOOK", "hook", ["cardnews", "instagram_feed", "shorts"], h,
            "저장/클릭/완독 지표 개선 가설 (수치 미확정)",
            "동일 카테고리 내 A/B 콘텐츠의 저장수·완독률 비교 데이터 최소 10건",
            "동일 조건 A/B 콘텐츠 비교, 최소 10건 누적 후 평가",
            "A/B 비교에서 관측 지표가 명확히 개선되고 최소 10건 데이터 확보 시 CANDIDATE 승격 검토",
            "10건 이상 데이터에서 개선이 관측되지 않거나 정책 리스크가 발견되면 REJECTED",
            "needs_real_performance_data",
        ))

    story_hyps = [
        "hook-problem-solution-cta 4단계가 3단계보다 완독 후 CTA 도달률이 높을 것이다",
        "문제를 먼저 제시하고 해결책을 나중에 배치하는 구조가 반대 순서보다 신뢰도가 높을 것이다",
        "체크리스트형 구조가 서술형 구조보다 저장 유도에 효과적일 것이다",
        "반전 포함 구조(문제-일반 해법-진짜 해법)가 단순 나열보다 완독률이 높을 것이다",
        "비교/대조 구조가 단일 추천 구조보다 신뢰 형성에 효과적일 것이다",
        "스토리텔링(사례 기반) 도입이 통계 기반 도입보다 공감 형성에 효과적일 것이다",
        "마지막 슬라이드에 요약을 배치하는 구조가 요약 생략 구조보다 저장률이 높을 것이다",
        "질문-답변 반복 구조가 단방향 설명보다 댓글 유도에 효과적일 것이다",
        "단계별 번호 부여 구조가 비번호 나열보다 실행 가능성 인식이 높을 것이다",
        "짧은 문단(2문장 이내) 반복 구조가 긴 문단보다 모바일 완독률이 높을 것이다",
    ]
    for h in story_hyps:
        patterns.append(pattern(
            "STORY", "story_structure", ["cardnews", "instagram_feed"], h,
            "완독률/저장률 개선 가설 (수치 미확정)",
            "동일 주제, 다른 구조 콘텐츠 쌍의 완독/저장 비교 데이터",
            "동일 주제 A/B 구조 비교, 최소 10건 누적 후 평가",
            "A/B 비교에서 명확한 개선 + 최소 10건 데이터 확보 시 CANDIDATE 승격 검토",
            "개선 없음 또는 가독성 저하가 관측되면 REJECTED",
            "needs_real_performance_data",
        ))

    cta_hyps = [
        "'저장해두고 다시 보기' 문구가 '좋아요 눌러주세요'보다 저장 전환에 효과적일 것이다",
        "질문형 CTA('당신의 방법은?')가 명령형 CTA보다 댓글 유도에 효과적일 것이다",
        "혜택 명시형 CTA('이 방법으로 시간 절약')가 단순 행동 지시보다 전환에 효과적일 것이다",
        "CTA를 마지막 슬라이드 상단에 배치하는 것이 하단 배치보다 인지율이 높을 것이다",
        "구체적 대상 지정 공유 유도('친구에게 보내기')가 일반 공유 유도보다 효과적일 것이다",
        "다음 콘텐츠 예고형 CTA가 단순 마무리보다 팔로우 전환에 효과적일 것이다",
        "이중 CTA(저장+공유)가 단일 CTA보다 전체 액션 수를 늘릴 것이다",
        "긴급성 없는 CTA가 긴급성 강조 CTA보다 장기 신뢰 형성에는 유리할 것이다",
        "커머스 가이드는 '지금 구매'보다 '비교 기준 저장하기' CTA가 신뢰 형성에 더 안전하고 효과적일 것이다",
        "BrandConnect CTA는 브랜드명 노출과 disclosure를 동시 배치해도 전환에 불리하지 않을 것이다",
    ]
    for h in cta_hyps:
        patterns.append(pattern(
            "CTA", "cta", ["cardnews", "instagram_feed", "commerce_guide", "brandconnect"], h,
            "저장/댓글/전환 지표 개선 가설 (수치 미확정)",
            "동일 콘텐츠, 다른 CTA 문구 비교 데이터 최소 10건",
            "동일 콘텐츠 A/B CTA 문구 비교, 최소 10건 누적 후 평가",
            "A/B 비교에서 명확한 개선 + 최소 10건 데이터 확보 시 CANDIDATE 승격 검토",
            "개선 없음 또는 신뢰도 저하가 관측되면 REJECTED",
            "needs_real_performance_data",
        ))

    evid_hyps = [
        "출처를 본문 내 인라인으로 표기하는 것이 하단 각주형보다 신뢰 인지에 효과적일 것이다",
        "통계 수치는 원문 그대로 인용하고 자체 해석을 덧붙이지 않는 것이 오인 유발을 줄일 것이다",
        "전문가 코멘트 인용 시 소속/직함을 함께 표기하는 것이 익명 인용보다 신뢰도가 높을 것이다",
        "근거 1개보다 2개 이상 교차 인용이 반박 가능성을 낮출 것이다",
        "이미지 출처 표기를 이미지 하단에 작게 고정하는 것이 인지 방해 없이 신뢰를 유지할 것이다",
        "최신성이 중요한 주제는 발행일자를 근거와 함께 표기하는 것이 신뢰도에 유리할 것이다",
        "커뮤니티발 정보는 '커뮤니티 의견' 라벨을 붙이는 것이 사실 정보와 혼동을 방지할 것이다",
        "근거 없는 슬라이드는 '확인 필요' 표기를 유지하는 것이 근거 있는 척하는 것보다 장기 신뢰에 유리할 것이다",
        "수치 근거는 반올림 여부를 명시하는 것이 정밀해 보이는 미표기보다 신뢰도에 유리할 것이다",
        "상반된 출처가 존재할 경우 두 관점을 모두 명시하는 것이 하나만 선택하는 것보다 신뢰도에 유리할 것이다",
    ]
    for i, h in enumerate(evid_hyps):
        status = "needs_content_qa" if i % 2 == 0 else "needs_real_performance_data"
        patterns.append(pattern(
            "EVID", "evidence_presentation", ["cardnews", "instagram_feed", "commerce_guide"], h,
            "신뢰 인지/정확성 개선 가설 (수치 미확정)",
            "동일 콘텐츠 근거 표기 방식 A/B 비교 또는 QA 체크리스트 통과 여부 (최소 10건 누적)",
            "QA 리뷰 또는 A/B 비교, 최소 10건 누적 후 평가",
            "QA 통과율 개선 또는 A/B 비교 개선 확인 시 CANDIDATE 승격 검토",
            "QA에서 반복적으로 오인 유발이 확인되면 REJECTED",
            status,
        ))

    visual_hyps = [
        "슬라이드당 한 문단(2문장 이내) 원칙이 여러 문단 배치보다 모바일 완독률이 높을 것이다",
        "헤드라인과 본문의 대비(크기 차이 2단계 이상)가 위계 인지 속도를 높일 것이다",
        "4장 전체에 걸친 색상 톤 통일이 브랜드 인지 지속시간을 늘릴 것이다",
        "이미지와 텍스트 영역을 슬라이드마다 분리 배치하는 것이 가독성에 유리할 것이다",
        "CTA 슬라이드에 여백을 더 확보하는 것이 행동 유도 인지에 유리할 것이다",
        "안전 여백(상하좌우 8% 이상) 유지가 크롭 위험을 줄일 것이다",
        "근거 슬라이드에 출처 표기 영역을 고정 위치에 배치하는 것이 일관된 신뢰 인지에 유리할 것이다",
        "체크리스트형 콘텐츠는 아이콘+짧은 문구 조합이 순수 텍스트보다 스캔 속도가 빠를 것이다",
        "Shorts 자막은 화면 하단 1/3 고정 배치가 상단 배치보다 시선 이동을 줄일 것이다",
        "슬라이드 전환 시 동일 레이아웃 반복이 매 슬라이드 새 레이아웃보다 인지 부하를 줄일 것이다",
    ]
    for i, h in enumerate(visual_hyps):
        status = "needs_content_qa" if i % 2 == 0 else "needs_real_performance_data"
        patterns.append(pattern(
            "VISUAL", "visual_rhythm", ["cardnews", "shorts"], h,
            "가독성/인지 속도 개선 가설 (수치 미확정)",
            "디자인 QA 체크리스트 통과 여부 또는 A/B 가독성 비교 (최소 10건 누적)",
            "QA 리뷰 또는 A/B 비교, 최소 10건 누적 후 평가",
            "QA 통과율 개선 또는 A/B 비교 개선 확인 시 CANDIDATE 승격 검토",
            "QA에서 가독성 저하가 반복 확인되면 REJECTED",
            status,
        ))

    trust_hyps = [
        "가격/재고 미확정 문구를 '확인 필요'로 명시하는 것이 침묵보다 신뢰도에 유리할 것이다",
        "비교 기준을 상품 나열보다 먼저 제시하는 것이 구매 유도 오인을 줄일 것이다",
        "스폰서 여부가 없는 순수 비교 가이드는 이를 명시하는 것이 신뢰도에 유리할 것이다",
        "변동 정보(가격/재고/배송)를 고정 정보(소재/사양)와 시각적으로 분리 표기하는 것이 오인을 줄일 것이다",
        "'구매 전 확인할 것' 체크리스트 포함이 단순 추천보다 클레임 리스크를 낮출 것이다",
        "실사용 후기 없이 일반 사양만 다루는 경우 이를 명시하는 것이 과장 인식을 줄일 것이다",
        "affiliate 링크 존재 여부를 CTA 근처에 명시하는 것이 사후 신뢰 손상을 줄일 것이다",
        "오래된 정보 재게시 시 갱신일자를 표기하는 것이 정보 신뢰도 유지에 유리할 것이다",
        "리뷰/평점 데이터가 없을 때 '검증된 리뷰 데이터 없음'을 명시하는 것이 침묵보다 신뢰도에 유리할 것이다",
        "카테고리별 고정 비교 기준 템플릿 재사용이 매번 새 기준 제시보다 신뢰 축적에 유리할 것이다",
    ]
    for h in trust_hyps:
        patterns.append(pattern(
            "TRUST", "commerce_trust", ["commerce_guide"], h,
            "구매 신뢰/클레임 리스크 감소 가설 (수치 미확정)",
            "QA 체크리스트 통과 여부 및 실제 상품 연결 후 클레임 발생률 비교 (최소 10건 누적)",
            "QA 리뷰, 실제 상품 데이터 연결 후 최소 10건 누적 평가",
            "QA 통과 + 클레임 미발생이 반복 확인되면 CANDIDATE 승격 검토",
            "클레임/오인 사례가 발견되면 REJECTED",
            "needs_content_qa",
        ))

    disc_hyps = [
        "협찬/광고 표기를 콘텐츠 상단 첫 슬라이드에 배치하는 것이 하단 배치보다 정책 준수 인지에 유리할 것이다",
        "'#광고' 해시태그와 본문 내 문구 disclosure를 동시에 사용하는 것이 단일 표기보다 정책 리스크를 낮출 것이다",
        "브랜드 제공 사실과 실사용 경험을 구분해 서술하는 것이 혼합 서술보다 신뢰도에 유리할 것이다",
        "협찬 콘텐츠에서도 근거 없는 효능 주장을 배제하는 것이 장기 계정 신뢰도에 유리할 것이다",
        "브랜드 승인 체크포인트를 제작 전/후로 나누어 명시하는 것이 사후 수정 리스크를 낮출 것이다",
    ]
    for h in disc_hyps:
        patterns.append(pattern(
            "DISC", "brandconnect_disclosure", ["brandconnect"], h,
            "플랫폼 정책 준수/신뢰 유지 가설 (수치 미확정)",
            "정책 준수 QA 체크리스트 통과 여부 (실제 캠페인 최소 3건 누적)",
            "QA 리뷰, 실제 캠페인 집행 후 정책 이슈 발생 여부 확인",
            "QA 통과 + 정책 이슈 미발생이 반복 확인되면 CANDIDATE 승격 검토",
            "정책 위반 또는 disclosure 누락이 발견되면 REJECTED",
            "needs_content_qa",
        ))

    anti_hyps = [
        "미검증 수치를 '약', '대략' 없이 단정적으로 제시하는 패턴은 회피 대상이다",
        "실시간 순위/판매량을 근거 확보 없이 언급하는 패턴은 회피 대상이다",
        "경쟁 계정을 직접 캡처해 비방하는 패턴은 회피 대상이다",
        "허위 긴급성('품절 임박')을 사용하는 패턴은 회피 대상이다",
        "의학적 효능을 단정하는 패턴은 회피 대상이다",
        "리뷰 작성자 동의 없이 리뷰 원문을 인용하는 패턴은 회피 대상이다",
        "PII가 포함된 커뮤니티 댓글을 마스킹 없이 인용하는 패턴은 회피 대상이다",
        "브랜드 협찬임에도 disclosure를 생략하는 패턴은 회피 대상이다",
        "저작권 확인 없는 이미지를 사용하는 패턴은 회피 대상이다",
        "세금/법률 정보를 개정 여부 확인 없이 재게시하는 패턴은 회피 대상이다",
        "근거 없는 '1위', '베스트셀러' 표현을 사용하는 패턴은 회피 대상이다",
        "실제 성과 데이터 없이 '높은 전환율'을 주장하는 패턴은 회피 대상이다",
        "커뮤니티발 미확인 정보를 사실처럼 단정하는 패턴은 회피 대상이다",
        "동일 후킹 문구를 과도하게 반복해 신뢰도를 낮추는 패턴은 회피 대상이다",
        "CTA에 허위 혜택('지금만 무료')을 명시하는 패턴은 회피 대상이다",
        "제조사 동의 없는 상품 이미지 워터마크 제거/합성 패턴은 회피 대상이다",
        "근거 슬라이드 없이 결론만 강하게 제시하는 패턴은 회피 대상이다",
        "다른 브랜드/상품을 사실 확인 없이 열등하다고 서술하는 패턴은 회피 대상이다",
        "실제 방문자/팔로워 수를 추정치로 단정 제시하는 패턴은 회피 대상이다",
        "Shorts 자막에 미검증 실제 성과 수치를 삽입하는 패턴은 회피 대상이다",
    ]
    for h in anti_hyps:
        patterns.append(pattern(
            "ANTI", "rejection_anti_pattern", ["cardnews", "shorts", "instagram_feed", "commerce_guide", "brandconnect"], h,
            "이 패턴 배제 시 정책 리스크/신뢰 손상 감소 가설",
            "QA 체크리스트에서 해당 패턴 발생 0건 유지 여부",
            "매 콘텐츠 QA 리뷰에서 해당 패턴 존재 여부 확인",
            "QA 체크리스트에 정식 회피 규칙으로 반영되면 '적용 확정' (승격 아님, 회피 규칙 자체는 즉시 적용)",
            "실제 사례에서 리스크가 없다고 반복 확인되는 예외가 생기면 재검토",
            "needs_content_qa",
        ))

    return patterns


# ---------------------------------------------------------------------------
# QA checks
# ---------------------------------------------------------------------------

FORBIDDEN_PATTERNS = [
    re.compile(r"\d+(,\d{3})*\s*원"),
    re.compile(r"\d+(\.\d+)?\s*%\s*(할인|off|세일)", re.IGNORECASE),
    re.compile(r"\d+(\.\d+)?\s*점"),
    re.compile(r"\d+\s*위\b"),
    re.compile(r"재고\s*\d+"),
    re.compile(r"판매량\s*\d+"),
    re.compile(r"리뷰\s*\d+\s*개"),
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


def run_qa(briefs, patterns):
    report = []
    ok = True

    ids = [b["content_id"] for b in briefs]
    dupes = {i for i in ids if ids.count(i) > 1}
    report.append(f"[content_id 중복] {'PASS' if not dupes else 'FAIL'} -- duplicates={sorted(dupes)}")
    ok &= not dupes

    missing_fields = []
    for b in briefs:
        for f in REQUIRED_FIELDS:
            if f not in b or b[f] in (None, ""):
                missing_fields.append((b.get("content_id"), f))
    report.append(f"[필수 필드 누락] {'PASS' if not missing_fields else 'FAIL'} -- missing={missing_fields[:20]}")
    ok &= not missing_fields

    bad_readiness = [b["content_id"] for b in briefs if b["current_readiness"] not in ALLOWED_READINESS]
    report.append(f"[current_readiness 어휘 준수] {'PASS' if not bad_readiness else 'FAIL'} -- bad={bad_readiness}")
    ok &= not bad_readiness

    bad_risk_tags = [b["content_id"] for b in briefs if any(t not in ALLOWED_RISK_TAGS for t in b.get("risk_tags", []))]
    report.append(f"[risk_tags 어휘 준수] {'PASS' if not bad_risk_tags else 'FAIL'} -- bad={bad_risk_tags}")
    ok &= not bad_risk_tags

    real_figure_hits = []
    for b in briefs:
        for s in flatten_strings(b):
            for rx in FORBIDDEN_PATTERNS:
                if rx.search(s):
                    real_figure_hits.append((b["content_id"], s[:60]))
    report.append(f"[확인되지 않은 실제 수치(가격/재고/평점/순위/리뷰수)] {'PASS' if not real_figure_hits else 'FAIL'} -- hits={real_figure_hits[:20]}")
    ok &= not real_figure_hits

    rights_missing = [b["content_id"] for b in briefs if not b.get("rights_status_required")]
    report.append(f"[권리 상태 누락] {'PASS' if not rights_missing else 'FAIL'} -- missing={rights_missing}")
    ok &= not rights_missing

    disclosure_missing = [b["content_id"] for b in briefs if b.get("disclosure_required") is None]
    report.append(f"[disclosure 누락] {'PASS' if not disclosure_missing else 'FAIL'} -- missing={disclosure_missing}")
    ok &= not disclosure_missing

    cardnews_briefs = [b for b in briefs if b["content_type"] == "cardnews"]
    bad_slides = []
    for b in cardnews_briefs:
        slides = b.get("slide_or_scene_roles")
        if not isinstance(slides, list) or len(slides) != 4:
            bad_slides.append(b["content_id"])
            continue
        required_slide_keys = {"headline_intent", "body_intent", "evidence_placement", "image_role",
                                "source_placement", "cta_relation", "risky_claims", "mobile_readability_risk"}
        for s in slides:
            if not required_slide_keys.issubset(s.keys()):
                bad_slides.append(b["content_id"])
                break
    report.append(f"[CardNews 4장 역할 누락] {'PASS' if not bad_slides else 'FAIL'} -- bad={bad_slides}")
    ok &= not bad_slides

    cardnews_scores = [b["priority"]["score"] for b in cardnews_briefs]
    tie_groups = {s for s in cardnews_scores if cardnews_scores.count(s) > 1}
    report.append(f"[V1.1: CardNews 우선순위 동점 그룹 수] {len(tie_groups)} (V1에서는 19개 항목이 동일 점수 13.8로 묶였음)")

    pattern_ids = [p["pattern_id"] for p in patterns]
    pdupes = {i for i in pattern_ids if pattern_ids.count(i) > 1}
    report.append(f"[pattern_id 중복] {'PASS' if not pdupes else 'FAIL'} -- duplicates={sorted(pdupes)}")
    ok &= not pdupes

    bad_status = [p["pattern_id"] for p in patterns if p["status"] not in ALLOWED_PATTERN_STATUS]
    report.append(f"[seed pattern status 어휘 준수 (validated/proven 금지)] {'PASS' if not bad_status else 'FAIL'} -- bad={bad_status}")
    ok &= not bad_status

    forbidden_status_words = ["validated", "proven", "high_performing"]
    bad_status_words = []
    for p in patterns:
        for s in flatten_strings(p):
            if any(w in s.lower() for w in forbidden_status_words):
                bad_status_words.append((p["pattern_id"], s[:60]))
    report.append(f"[seed pattern 내 validated/proven/high_performing 문구 금지] {'PASS' if not bad_status_words else 'FAIL'} -- hits={bad_status_words}")
    ok &= not bad_status_words

    report.append(f"[콘텐츠 브리프 총 개수] {len(briefs)} (요구 최소 120)")
    report.append(f"[learning seed pattern 총 개수] {len(patterns)} (요구 최소 90)")
    ok &= len(briefs) >= 120
    ok &= len(patterns) >= 90

    return ok, report


def main():
    briefs = (
        build_cardnews_briefs() + build_shorts_briefs() + build_instagram_briefs()
        + build_brandconnect_briefs() + build_commerce_briefs() + build_knowledge_briefs()
    )
    briefs = attach_reuse_scores_and_priority(briefs)
    patterns = build_patterns()

    ok, report_lines = run_qa(briefs, patterns)

    OUT_BACKLOG_JSON.write_text(
        json.dumps({"version": "content_portfolio_v1.1", "count": len(briefs), "briefs": briefs}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    OUT_PATTERNS_JSON.write_text(
        json.dumps({"version": "content_portfolio_v1.1", "count": len(patterns), "patterns": patterns}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    by_category = {}
    for b in briefs:
        by_category.setdefault(b["content_type"], []).append(b)

    md_lines = ["# Content Backlog -- Content Portfolio V1.1", "", f"Total briefs: {len(briefs)}", ""]
    md_lines.append("## Count by content_type")
    md_lines.append("")
    md_lines.append("| content_type | count |")
    md_lines.append("|---|---|")
    for ct, items in by_category.items():
        md_lines.append(f"| {ct} | {len(items)} |")
    md_lines.append("")

    for ct, items in by_category.items():
        md_lines.append(f"## {ct} ({len(items)})")
        md_lines.append("")
        for b in items:
            md_lines.append(f"### {b['content_id']} -- {b['working_title']}")
            md_lines.append("")
            md_lines.append(f"- channel: {b['channel']} | category: {b['category']} | theme_tag: {b['theme_tag']}")
            md_lines.append(f"- audience: {b['audience']}")
            md_lines.append(f"- problem: {b['problem']}")
            md_lines.append(f"- promise: {b['promise']}")
            md_lines.append(f"- hook: {b['hook']}")
            md_lines.append(f"- core_question: {b['core_question']}")
            md_lines.append(f"- cta: {b['cta']}")
            md_lines.append(f"- evidence_needed: {b['evidence_needed']}")
            md_lines.append(f"- source_type_needed: {b['source_type_needed']}")
            md_lines.append(f"- image_or_asset_needed: {b['image_or_asset_needed']}")
            md_lines.append(f"- rights_status_required: {b['rights_status_required']}")
            md_lines.append(f"- volatile_claims: {b['volatile_claims']}")
            md_lines.append(f"- forbidden_claims: {b['forbidden_claims']}")
            md_lines.append(f"- manual_review: {b['manual_review']}")
            md_lines.append(f"- monetization_route: {b['monetization_route']}")
            md_lines.append(f"- disclosure_required: {b['disclosure_required']}")
            md_lines.append(f"- freshness_window: {b['freshness_window']}")
            md_lines.append(f"- fallback_behavior: {b['fallback_behavior']}")
            md_lines.append(f"- reusable_pattern_tags: {b['reusable_pattern_tags']}")
            md_lines.append(f"- risk_tags: {b['risk_tags']}")
            md_lines.append(f"- evidence_sourcing_cost: {b['evidence_sourcing_cost']} | rights_difficulty: {b['rights_difficulty']} | freshness_risk: {b['freshness_risk']} | reuse_score: {b['reuse_score']}")
            md_lines.append(f"- priority: {b['priority']}")
            md_lines.append(f"- effort: {b['effort']} | expected_learning_value: {b['expected_learning_value']}")
            md_lines.append(f"- current_readiness: {b['current_readiness']} | blocker_codes: {b['blocker_codes']}")
            md_lines.append("")
    OUT_BACKLOG_MD.write_text("\n".join(md_lines), encoding="utf-8")

    ranked = sorted(briefs, key=lambda b: b["priority"]["score"], reverse=True)[:20]
    top_lines = ["# Top 20 Priority Content (V1.1 scoring)", "", "Scored per-topic (evidence_sourcing_cost, rights_difficulty, freshness_risk, reuse_score from real theme-tag cross-channel membership), not a category-wide constant. See tools/build_portfolio.py::score_priority / attach_reuse_scores_and_priority.", "", "| Rank | content_id | working_title | content_type | tier | score | current_readiness |", "|---|---|---|---|---|---|---|"]
    for i, b in enumerate(ranked, 1):
        top_lines.append(f"| {i} | {b['content_id']} | {b['working_title']} | {b['content_type']} | {b['priority']['tier']} | {b['priority']['score']} | {b['current_readiness']} |")
    OUT_TOP20_MD.write_text("\n".join(top_lines), encoding="utf-8")

    qa_lines = ["# QA Report -- Content Portfolio V1.1", "", f"Overall: {'PASS' if ok else 'FAIL'}", ""]
    qa_lines.extend(f"- {line}" for line in report_lines)
    OUT_QA_MD.write_text("\n".join(qa_lines), encoding="utf-8")

    print("OVERALL_QA:", "PASS" if ok else "FAIL")
    for line in report_lines:
        print(line)
    print("briefs_by_type:", {k: len(v) for k, v in by_category.items()})
    print("patterns_total:", len(patterns))


if __name__ == "__main__":
    main()
