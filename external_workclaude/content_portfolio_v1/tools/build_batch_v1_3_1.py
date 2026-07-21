"""Content Portfolio V1.3.1 -- Evidence Red-Team correction of the Production Batch.

Stdlib only. This is a semantic re-audit, not a re-run of V1.3's keyword scan. Every sentence in
every V1.3 item was individually read and judged; the findings and the reasoning for each
keep/rewrite/replace decision live in EVIDENCE_RED_TEAM_V1_3_1.md (hand-authored, not generated
from a template) and are summarized in BATCH_HANDOFF_V1_3_1.md. This script assembles the
corrected copy into the final JSON/Markdown deliverables and runs the QA regression checks --
the regex checks here are a shallow safety net for known-removed phrases, not a substitute for
the sentence-level review already performed.

Changes from V1.3:
- KN-004 removed entirely (not just its number) -- replaced with KN-007 (회의록 작성 기본기), a
  pure document-template instruction with no historical/statistical/health claim.
- IG-010 removed entirely -- an OX pet-knowledge quiz cannot be limited to pure prep/record
  content by construction (every question was an implicit health/behavior/hygiene-prevention
  claim) -- replaced with IG-007 (문화생활 예산 관리 팁), rewritten as pure personal-budget
  organization prompting (the reader records their own spending, no claim about the world).
- CN-013 rewritten: removed the "이 다섯 가지만 챙기면 ... 적응을 도울 수 있습니다" behavioral/
  welfare-outcome claim; kept the item, the checklist itself is pure preparation/record content.
- SH-017: reviewed, no risky sentence found, kept unchanged.
- KN-008 rewritten: removed "아이젠하워" historical attribution and the "여유 있게 처리할 수
  있습니다" time-management efficacy claim; now a generic, unattributed classification
  description plus a personal-organization prompt.
- CN-017 and SH-006 rewritten: removed all taste/freshness/extraction-effect assertions
  ("향이 금방 날아가고 신선함이 떨어집니다", "신선함을 더 오래 유지할 수 있습니다", "충분해요",
  "매번 맛이 다르셨다면") -- storage/brewing steps are now presented as selectable options, not
  as causes of a guaranteed outcome.
- IG-009 and IG-013 rewritten: removed the "오후 기분이 달라질 수 있습니다" and "작게 시작해서
  오래 이어가는 것이 핵심입니다" outcome/efficacy assertions (neither the CTO named these two,
  but the instruction requires reviewing every final sentence semantically, not only the named
  items -- these were found during that pass).

Never reads/writes outside external_workclaude/content_portfolio_v1/, no network call, no real
publish/purchase/account action.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

OUT_BATCH_JSON = BASE / "PRODUCTION_BATCH_V1_3_1.json"
OUT_REDTEAM_MD = BASE / "EVIDENCE_RED_TEAM_V1_3_1.md"
OUT_HANDOFF_MD = BASE / "BATCH_HANDOFF_V1_3_1.md"
OUT_QA_MD = BASE / "QA_REPORT_V1_3_1.md"

ALLOWED_EVIDENCE_NOT_REQUIRED_REASONS = {
    "pure_operator_instruction", "personal_organization_prompt", "non-claim_creative_copy",
}

# Phrases specifically removed during this red-team pass -- if any of these reappear, the
# regression guard below fails loudly. This list is a safety net, not the audit itself.
REMOVED_RISK_PHRASES = [
    "적응을 도울", "신선함이 떨어집니다", "신선함을 더 오래 유지", "충분해요", "매번 맛이 다르셨다면",
    "아이젠하워", "여유 있게 처리할 수 있습니다", "오후 기분이 달라질 수 있습니다",
    "지치기 쉽습니다", "핵심입니다", "산책을 시켜주는 것이 좋다", "혼자 있는 시간도 잘 보내는",
    "자주 깨끗한 물로 갈아주는", "21일",
]

GENERAL_RISK_KEYWORDS = [
    "독성", "질병", "치료", "예방접종", "안전을 보장", "건강에 좋", "효과가 있", "효능",
    "임상적으로", "연구에 따르면", "입증", "검증(된|됨)",
]

FORBIDDEN_REAL_VALUE_PATTERNS = [
    re.compile(r"https?://"), re.compile(r"www\."),
    re.compile(r"\d+(,\d{3})*\s*원"), re.compile(r"\d+(\.\d+)?\s*%"),
    re.compile(r"승인(됨|완료)"), re.compile(r"확인(됨|완료)(?!\s*필요)"),
]

BANNED_CONTENT_ID = "KN-004"


def flatten_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from flatten_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from flatten_strings(v)


def split_sentences(text: str):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def cardnews_item(content_id, working_title, theme_tag, slides, cta_text, cross_channel,
                   evidence_not_required_reason, evidence_status):
    promised = slides[2].get("promised_count")
    actual = len(slides[2].get("list_items", []))
    return {
        "content_id": content_id, "content_type": "cardnews", "working_title": working_title,
        "theme_tag": theme_tag,
        "final_copy": {"slides": slides},
        "number_consistency_check": {"promised": promised, "actual_items": actual, "match": promised == actual},
        "cta": cta_text,
        "forbidden_expressions": [
            "효능·치료 효과 단정", "미검증 통계·수치 인용", "특정 브랜드 언급/비방",
            "실제 가격·재고·후기 언급", "허위 긴급성 표현", "맛·신선도·추출 효과 단정",
            "동물 건강·행동·예방·안전 보장 주장",
        ],
        "evidence_status": evidence_status,
        "evidence_not_required_reason": evidence_not_required_reason,
        "image_role": [f"슬라이드 {s['slide']} ({s['role']}): {s['image_role']}" for s in slides],
        "user_shoot_conditions": [
            "촬영자 본인 소유 공간/사물만 촬영",
            "제3자 얼굴이 식별 가능하게 노출된 경우 동의 확보 전까지 미사용",
            "브랜드 로고 노출 시 블러 처리 또는 재촬영",
        ],
        "generated_image_scope": [
            "CardNewsModule 배경 fallback(단색/그라디언트)만 자동 생성 경로로 즉시 사용 가능",
            "실사형 합성 이미지는 이번 배치 범위 밖",
        ],
        "rights_status": "제로-리스크 경로(자체 촬영 또는 CardNewsModule fallback 배경)는 즉시 사용 가능, 그 외 이미지는 라이선스 미확보 상태로 유지",
        "attribution_required": {"required": False, "note": "외부 자료 인용이 없으므로 attribution 불필요"},
        "operator_checklist": [
            "4장 문장이 모두 완결되어 있는지 확인 (말줄임표 없음)",
            "슬라이드3에서 약속한 항목 수와 실제 목록 개수가 일치하는지 확인",
            "CTA가 SAVE 하나뿐인지 확인",
            "효과·신선도·건강·안전 보장 문장이 없는지 재확인",
        ],
        "cross_channel_link": cross_channel,
        "publish_ready": False,
        "actual_publish": False,
    }


def shorts_item(content_id, working_title, theme_tag, scenes, cta_text, manual_assets, cross_channel,
                 evidence_not_required_reason, evidence_status):
    return {
        "content_id": content_id, "content_type": "shorts", "working_title": working_title,
        "theme_tag": theme_tag,
        "final_copy": {"scenes": scenes},
        "cta": cta_text,
        "forbidden_expressions": [
            "효능 단정", "미검증 통계", "실제 조회수·참여 데이터 언급", "실제 브랜드·제품명 노출",
            "맛·신선도·추출 효과 단정", "동물 건강·행동·예방·안전 보장 주장",
        ],
        "evidence_status": evidence_status,
        "evidence_not_required_reason": evidence_not_required_reason,
        "image_role": [f"{s['scene']}({s['role']}, {s['duration_sec']}s): {s['visual']}" for s in scenes],
        "user_shoot_conditions": [
            "촬영자 본인 소유 공간/사물/반려동물만 촬영 (타인 소유물은 동의 확보 전까지 미사용)",
            "제3자가 화면에 노출될 경우 동의 확보 전까지 사용 금지",
            "화면에 보이는 값은 촬영 당시 실제 상태만 사용, 사후 수치 삽입 금지",
        ],
        "generated_image_scope": ["생성 이미지/영상 전면 미사용 -- 이번 배치는 실사 촬영 전제"],
        "rights_status": "촬영 소재 소유권 확인 전까지 미사용 -- 본인 촬영 완료 시 즉시 사용 가능",
        "attribution_required": {"required": False, "note": "외부 자료 인용이 없으므로 attribution 불필요"},
        "operator_checklist": [
            "촬영 소재가 실제로 촬영되었는지 확인 (스톡 영상 대체 금지)",
            "제3자 동의 필요 여부 확인",
            "자막이 내레이션과 일치하는지 확인",
            "CTA가 SAVE 하나뿐인지 확인",
            "맛·신선도·효과·동물 안전 보장 문장이 없는지 재확인",
        ],
        "manual_assets_needed": manual_assets,
        "execution_boundary": "TTS 생성, 배경음악 삽입, 영상 렌더링, 실제 업로드는 이번 배치에서 수행하지 않음",
        "cross_channel_link": cross_channel,
        "publish_ready": False,
        "actual_publish": False,
    }


def instagram_item(content_id, working_title, theme_tag, hook, body, cta_text, cross_channel,
                    evidence_not_required_reason, evidence_status):
    return {
        "content_id": content_id, "content_type": "instagram_feed", "working_title": working_title,
        "theme_tag": theme_tag,
        "final_copy": {"hook": hook, "body": body},
        "cta": cta_text,
        "forbidden_expressions": [
            "근거 없는 해시태그(성과 최적화 주장 포함) 사용", "미검증 사실 단정", "실제 성과/순위 언급",
            "실제 브랜드 언급", "동물 건강·행동·예방·안전 보장 주장", "심리적 효과 단정",
        ],
        "evidence_status": evidence_status,
        "evidence_not_required_reason": evidence_not_required_reason,
        "image_role": "정보 요약형 카드 배경 또는 단일 피드 이미지 -- 텍스트 삽입 여백 확보",
        "user_shoot_conditions": ["촬영자 본인 소유 공간/사물만 촬영"],
        "generated_image_scope": ["정보 카드 배경(단색/그라디언트)만 자동 생성 허용, 실사 합성 이미지 미사용"],
        "rights_status": "제로-리스크 경로(자체 제작 배경/자체 촬영)만 사용 -- 그 외 이미지는 라이선스 확인 전까지 미사용",
        "attribution_required": {"required": False, "note": "외부 자료 인용이 없으므로 attribution 불필요"},
        "operator_checklist": [
            "본문에 근거 없는 해시태그나 성과/심리 효과 주장이 없는지 확인",
            "hook과 본문이 완결된 문장인지 확인",
            "CTA가 SAVE 하나뿐인지 확인",
        ],
        "hashtag_policy": "이번 배치에는 해시태그를 포함하지 않음",
        "cross_channel_link": cross_channel,
        "publish_ready": False,
        "actual_publish": False,
    }


def knowledge_item(content_id, working_title, theme_tag, slides, cta_text, cross_channel,
                    evidence_not_required_reason, evidence_status, number_check=None):
    return {
        "content_id": content_id, "content_type": "knowledge_evergreen", "working_title": working_title,
        "theme_tag": theme_tag,
        "final_copy": {"slides": slides},
        "number_consistency_check": number_check,
        "cta": cta_text,
        "forbidden_expressions": [
            "미검증 통계·연구 인용", "특정 인물/연구에 귀속되는 역사적 주장", "효과·성과 수치 주장",
        ],
        "evidence_status": evidence_status,
        "evidence_not_required_reason": evidence_not_required_reason,
        "image_role": [f"슬라이드 {s['slide']} ({s['role']}): {s['image_role']}" for s in slides],
        "user_shoot_conditions": ["실사 촬영보다 자체 제작 인포그래픽 권장"],
        "generated_image_scope": ["인포그래픽 스타일 배경(자체 제작 우선)만 사용, 실사 합성 이미지 미사용"],
        "rights_status": "제로-리스크 경로(자체 제작 인포그래픽)만 사용 -- 그 외 이미지는 라이선스 확인 전까지 미사용",
        "attribution_required": {"required": False, "note": "특정 연구/인물을 인용하지 않으므로 attribution 불필요"},
        "operator_checklist": [
            "특정 인물/연구에 귀속되는 역사적 주장이 없는지 확인",
            "효과·성과를 단정하는 문장이 없는지 확인",
            "4장 문장이 모두 완결되어 있는지 확인",
            "CTA가 SAVE 하나뿐인지 확인",
        ],
        "cross_channel_link": cross_channel,
        "publish_ready": False,
        "actual_publish": False,
    }


def build_items():
    items = []

    # --- CardNews x4 (CN-013 rewritten, CN-014/016 minor problem-slide review kept, CN-017 rewritten) ---
    items.append(cardnews_item(
        "CN-013", "반려동물 첫 입양 준비물", "PET_CARE",
        [
            {"slide": 1, "role": "hook", "text": "강아지·고양이를 데려오기 전, 준비물부터 확인해보세요.",
             "image_role": "반려동물을 맞이하는 상황을 암시하는 배경 이미지"},
            {"slide": 2, "role": "problem", "text": "입양 당일 준비물을 미리 챙기지 않으면 무엇부터 꺼내야 할지 몰라 당황하는 경우가 많습니다.",
             "image_role": "당황스러운 첫날 상황을 보여주는 이미지"},
            {"slide": 3, "role": "solution", "promised_count": 5,
             "list_items": ["이동장", "급식기와 물그릇", "초기 사료", "배변 용품", "가까운 동물병원 연락처"],
             "text": "입양 전 준비 목록은 다음과 같습니다. 이동장, 급식기와 물그릇, 초기 사료, 배변 용품, 가까운 동물병원 연락처, 이렇게 5가지입니다.",
             "image_role": "다섯 가지 준비물을 나열한 이미지"},
            {"slide": 4, "role": "cta", "text": "지금 저장해두고 입양 전날 목록을 다시 확인하세요.",
             "image_role": "저장 유도용 마무리 이미지"},
        ],
        "지금 저장해두고 입양 전날 목록을 다시 확인하세요.",
        "SH-017(반려동물 산책 준비물 점검, PET_CARE)과 근거·리서치 공유",
        "pure_operator_instruction",
        "순수 준비물 목록으로 재작성 -- '적응을 도울 수 있다'는 행동/복지 효과 주장을 제거함 (V1.3.1에서 삭제)",
    ))
    items.append(cardnews_item(
        "CN-014", "캠핑 초보 준비물 체크리스트", "CAMPING_TRAVEL_PACK",
        [
            {"slide": 1, "role": "hook", "text": "캠핑 초보가 자주 빠뜨리는 준비물, 확인해보세요.",
             "image_role": "캠핑장 배경 이미지"},
            {"slide": 2, "role": "problem", "text": "텐트만 챙기면 준비가 끝났다고 생각했다가, 막상 현장에서 필요한 물건이 없어 당황하는 경우가 많습니다.",
             "image_role": "현장에서 당황하는 상황을 암시하는 이미지"},
            {"slide": 3, "role": "solution", "promised_count": 4,
             "list_items": ["취침용품(텐트, 침낭, 매트)", "취사용품(버너, 코펠, 식수)", "방한·방수용품(여벌 옷, 우비)", "안전용품(손전등, 상비약)"],
             "text": "캠핑 전 준비할 4가지 카테고리는 다음과 같습니다. 취침용품, 취사용품, 방한·방수용품, 안전용품입니다.",
             "image_role": "네 가지 카테고리를 나열한 이미지"},
            {"slide": 4, "role": "cta", "text": "저장해두고 캠핑 전날 하나씩 확인하세요.",
             "image_role": "저장 유도용 마무리 이미지"},
        ],
        "저장해두고 캠핑 전날 하나씩 확인하세요.",
        "CN-016(여행 전 짐싸기 체크리스트) 및 SH-018(캐리어 짐싸기 순서)과 CAMPING_TRAVEL_PACK 클러스터 공유",
        "pure_operator_instruction",
        "슬라이드3의 '빠뜨리는 물건 없이 시작할 수 있다'는 완결성 보장 문구를 제거하고 순수 카테고리 목록으로 재작성",
    ))
    items.append(cardnews_item(
        "CN-016", "여행 전 짐싸기 체크리스트", "CAMPING_TRAVEL_PACK",
        [
            {"slide": 1, "role": "hook", "text": "여행 전날, 짐 쌀 때마다 뭔가 빠뜨리셨나요.",
             "image_role": "짐 싸는 상황을 암시하는 배경 이미지"},
            {"slide": 2, "role": "problem", "text": "짐을 다 쌌다고 생각했는데 공항이나 터미널에서야 충전기나 여권 사본을 빠뜨린 것을 깨닫는 경우가 있습니다.",
             "image_role": "당황스러운 상황을 보여주는 이미지"},
            {"slide": 3, "role": "solution", "promised_count": 5,
             "list_items": ["신분증·서류", "전자기기와 충전기", "세면·위생용품", "상비약", "계절에 맞는 옷"],
             "text": "여행 전 확인할 5가지 카테고리는 다음과 같습니다. 신분증과 서류, 전자기기와 충전기, 세면·위생용품, 상비약, 계절에 맞는 옷입니다.",
             "image_role": "다섯 가지 카테고리를 나열한 이미지"},
            {"slide": 4, "role": "cta", "text": "저장해두고 짐 싸기 전 순서대로 확인하세요.",
             "image_role": "저장 유도용 마무리 이미지"},
        ],
        "저장해두고 짐 싸기 전 순서대로 확인하세요.",
        "CN-014(캠핑 초보 준비물) 및 SH-018(캐리어 짐싸기 순서)과 CAMPING_TRAVEL_PACK 클러스터 공유",
        "pure_operator_instruction",
        "슬라이드3의 '빠짐없이 마칠 수 있다'는 완결성 보장 문구를 제거하고 순수 카테고리 목록으로 재작성",
    ))
    items.append(cardnews_item(
        "CN-017", "커피 원두 보관법", "COFFEE_RITUAL",
        [
            {"slide": 1, "role": "hook", "text": "원두, 어떻게 보관하고 계신가요.",
             "image_role": "원두 봉투/보관 상황을 암시하는 배경 이미지"},
            {"slide": 2, "role": "problem", "text": "원두를 어떻게 보관해야 할지 헷갈릴 때가 있습니다.",
             "image_role": "보관 방법을 고민하는 상황을 암시하는 이미지"},
            {"slide": 3, "role": "solution", "promised_count": 3,
             "list_items": ["밀폐 용기에 담아 보관하기", "서늘하고 어두운 곳에 두기", "필요한 만큼만 소분해서 꺼내 쓰기"],
             "text": "원두를 보관할 때 선택할 수 있는 3가지 방법이 있습니다. 밀폐 용기에 담아 보관하기, 서늘하고 어두운 곳에 두기, 필요한 만큼만 소분해서 꺼내 쓰기입니다.",
             "image_role": "밀폐 용기에 소분 보관된 원두 이미지"},
            {"slide": 4, "role": "cta", "text": "저장해두고 오늘 원두 보관 방법을 확인해보세요.",
             "image_role": "저장 유도용 마무리 이미지"},
        ],
        "저장해두고 오늘 원두 보관 방법을 확인해보세요.",
        "SH-006(커피 내리는 법 3단계)과 COFFEE_RITUAL 클러스터 공유",
        "pure_operator_instruction",
        "'향이 금방 날아가고 신선함이 떨어집니다'(화학적 효과 단정) 및 '신선함을 더 오래 유지할 수 있습니다'(효과 보장)를 전면 삭제 -- 보관 방법을 결과 주장 없는 '선택 가능한 옵션'으로만 재작성 (V1.3.1)",
    ))

    # --- Shorts x3 (SH-017 kept unchanged, SH-006 rewritten, SH-018 kept unchanged) ---
    items.append(shorts_item(
        "SH-017", "반려동물 산책 준비물 점검", "PET_CARE",
        [
            {"scene": 1, "duration_sec": "0-3", "role": "hook", "visual": "목줄을 집어드는 손 클로즈업",
             "narration": "산책 나가기 전, 이거 챙기셨나요?", "subtitle": "산책 준비물 점검", "shot_composition": "손과 목줄 클로즈업, 자연광"},
            {"scene": 2, "duration_sec": "3-10", "role": "context", "visual": "현관에서 준비 없이 나가려다 멈추는 연출",
             "narration": "이것 없이 나가면 아쉬워요.", "subtitle": "이거 없으면 곤란해요", "shot_composition": "현관 전신 샷"},
            {"scene": 3, "duration_sec": "10-35", "role": "core_steps", "visual": "목줄 -> 배변봉투 -> 물병 -> 인식표 순서로 챙기는 장면 4컷",
             "narration": "목줄, 배변봉투, 물, 인식표 순서로 챙겨보세요.", "subtitle": "목줄 -> 배변봉투 -> 물 -> 인식표", "shot_composition": "각 아이템 클로즈업, 컷 전환"},
            {"scene": 4, "duration_sec": "35-45", "role": "cta", "visual": "완비된 가방을 들고 나가는 장면",
             "narration": "저장해두고 산책 전마다 확인해보세요.", "subtitle": "저장하고 매번 확인하기", "shot_composition": "가방과 현관문 전신 샷"},
        ],
        "저장해두고 산책 전마다 확인해보세요.",
        ["실제 목줄/배변봉투/물병/인식표 (촬영자 본인 소유)", "촬영자 본인 소유 반려동물 또는 동의 확보된 반려동물"],
        "CN-013(반려동물 첫 입양 준비물)과 PET_CARE 클러스터 공유",
        "pure_operator_instruction",
        "재검토 결과 건강/행동/예방/안전 보장 문장 없음 -- 순수 준비물 목록이므로 변경 없이 유지 (V1.3.1)",
    ))
    items.append(shorts_item(
        "SH-006", "커피 내리는 법 3단계", "COFFEE_RITUAL",
        [
            {"scene": 1, "duration_sec": "0-3", "role": "hook", "visual": "필터에 원두 붓는 장면 클로즈업",
             "narration": "커피, 3단계로 내려볼까요?", "subtitle": "커피 내리는 법 3단계", "shot_composition": "드리퍼와 원두 클로즈업"},
            {"scene": 2, "duration_sec": "3-10", "role": "context", "visual": "드리퍼를 준비하는 장면",
             "narration": "커피 내리는 방법이 궁금하셨다면.", "subtitle": "이 3단계를 참고해보세요", "shot_composition": "드리퍼 준비 장면 클로즈업"},
            {"scene": 3, "duration_sec": "10-35", "role": "core_steps", "visual": "원두 계량 -> 물 온도 확인 -> 천천히 붓기 3컷",
             "narration": "원두 계량, 물 온도, 천천히 붓기 순서예요.", "subtitle": "계량 -> 온도 -> 붓기", "shot_composition": "저울/온도계/드리퍼 각각 클로즈업"},
            {"scene": 4, "duration_sec": "35-45", "role": "cta", "visual": "완성된 커피 잔",
             "narration": "저장해두고 다음에 따라해보세요.", "subtitle": "저장하고 따라하기", "shot_composition": "완성된 커피 잔 탑샷"},
        ],
        "저장해두고 다음에 따라해보세요.",
        ["실제 원두, 드리퍼, 필터 (촬영자 본인 소유)", "저울/온도계(있는 경우)"],
        "CN-017(커피 원두 보관법)과 COFFEE_RITUAL 클러스터 공유",
        "pure_operator_instruction",
        "'충분해요'(효과/충족성 단정)와 '매번 맛이 다르셨다면'(맛 결과에 대한 암묵적 인과 주장)을 삭제하고 순수 절차 안내로 재작성 (V1.3.1)",
    ))
    items.append(shorts_item(
        "SH-018", "캐리어 짐싸기 순서", "CAMPING_TRAVEL_PACK",
        [
            {"scene": 1, "duration_sec": "0-3", "role": "hook", "visual": "빈 캐리어가 열려 있는 장면",
             "narration": "짐 쌀 때 이 순서로 해보세요.", "subtitle": "캐리어 짐싸기 순서", "shot_composition": "열린 캐리어 탑샷"},
            {"scene": 2, "duration_sec": "3-10", "role": "context", "visual": "뒤죽박죽 짐이 쌓인 캐리어(연출)",
             "narration": "순서 없이 싸면 이렇게 되죠.", "subtitle": "순서가 중요해요", "shot_composition": "어수선한 캐리어 클로즈업"},
            {"scene": 3, "duration_sec": "10-35", "role": "core_steps", "visual": "무거운 옷 바닥 -> 신발 옆면 -> 작은 소품 파우치 정리 3컷",
             "narration": "무거운 것은 바닥, 신발은 옆면, 작은 물건은 파우치에 넣어보세요.", "subtitle": "바닥 -> 옆면 -> 파우치", "shot_composition": "캐리어 내부 탑샷, 단계별 컷 전환"},
            {"scene": 4, "duration_sec": "35-45", "role": "cta", "visual": "깔끔하게 정리된 캐리어를 닫는 장면",
             "narration": "저장해두고 다음 여행에 따라해보세요.", "subtitle": "저장하고 짐싸기 순서 기억하기", "shot_composition": "캐리어 닫는 손 클로즈업"},
        ],
        "저장해두고 다음 여행에 따라해보세요.",
        ["실제 캐리어와 여행용 소품 (촬영자 본인 소유)"],
        "CN-014/CN-016(캠핑·여행 짐싸기 체크리스트)과 CAMPING_TRAVEL_PACK 클러스터 공유",
        "pure_operator_instruction",
        "재검토 결과 효과/건강/안전 보장 문장 없음 -- '순서 없이 싸면 이렇게 되죠'는 동어반복적 서술(정리 없이 쌓으면 어수선해진다)로 외부 근거가 필요한 경험적 주장이 아니라고 판단, 변경 없이 유지 (V1.3.1)",
    ))

    # --- Instagram x3 (IG-010 REPLACED by IG-007; IG-009, IG-013 rewritten) ---
    items.append(instagram_item(
        "IG-007", "문화생활 예산 관리 팁", "BUDGET_MANAGEMENT",
        "이번 달 문화생활, 얼마나 쓰셨는지 알고 계신가요?",
        (
            "영화, 전시, 공연처럼 즐거움을 위한 지출은 계획 없이 하다 보면 예산을 넘기기 쉽습니다. "
            "이번 달 문화생활에 쓸 금액을 먼저 정해보세요. 그리고 다녀온 뒤에는 실제로 얼마를 썼는지 적어보세요. "
            "다음 달에는 이번 기록을 참고해서 예산을 다시 정해볼 수 있습니다."
        ),
        "저장해두고 이번 달 문화생활 예산을 적어보세요.",
        "IG-010을 대체 -- CN-020(명절 선물 예산 관리법)과 BUDGET_MANAGEMENT 클러스터 공유",
        "personal_organization_prompt",
        "독자 본인의 지출을 계획·기록하도록 유도하는 순수 개인 정리 프롬프트 -- 외부 세계에 대한 사실 주장이 없음 (V1.3.1 신규 채택, IG-010 대체)",
    ))
    items.append(instagram_item(
        "IG-009", "직장인 점심시간 활용법", "REMOTE_WORK",
        "점심시간 1시간, 어떻게 보내고 계신가요?",
        (
            "회의와 업무 사이, 짧은 점심시간을 그냥 흘려보내는 경우가 많습니다. 오늘은 이렇게 써보는 건 어떨까요. "
            "첫째, 식사 후 10분이라도 걸어보기. 둘째, 스마트폰 대신 잠깐 눈을 감고 쉬어보기. "
            "셋째, 내일 할 일을 미리 가볍게 메모해두기. "
            "거창하지 않아도, 점심시간을 조금 다르게 써보는 것도 하나의 선택지가 될 수 있습니다."
        ),
        "저장해두고 오늘 점심시간에 하나만 시도해보세요.",
        "CN-009(재택근무 생산성 루틴), KN-008(시간관리 매트릭스 활용법)과 REMOTE_WORK 클러스터 공유",
        "personal_organization_prompt",
        "'오후 기분이 달라질 수 있습니다'(심리적 효과 주장)를 삭제하고 '하나의 선택지'로 재작성 -- 독자가 스스로 선택하는 순수 프롬프트로 전환 (V1.3.1)",
    ))
    items.append(instagram_item(
        "IG-013", "자기계발 습관 만들기 팁", "LEARNING_HABIT",
        "작심삼일, 어떻게 이어가면 좋을까요?",
        (
            "습관을 만들 때 시도해볼 수 있는 방법들이 있습니다. "
            "하나, 목표를 아주 작게 쪼개보기. 둘, 이미 하고 있는 행동 뒤에 새 습관을 붙여보기. "
            "예를 들어 양치 후 스트레칭 한 번처럼요. 셋, 완벽하게 하려 하지 말고 이어가는 것 자체에 집중해보기. "
            "오늘 하나만 골라 시작해볼 수 있습니다."
        ),
        "저장해두고 오늘 작은 습관 하나부터 시작해보세요.",
        "CN-025(온라인 강의 완주하는 습관), KN-007(회의록 작성 기본기 -- LEARNING_HABIT 아님, REMOTE_WORK 계열)과 별개, LEARNING_HABIT 클러스터 내 CN-025와 공유",
        "personal_organization_prompt",
        "'큰 목표부터 세우면 오히려 지치기 쉽습니다'(행동심리학적 인과 주장)와 '작게 오래 이어가는 것이 핵심입니다'(효과 단정)를 삭제 -- 전부 '시도해볼 수 있는 방법' 프롬프트로 재작성, 어떤 심리 기제도 주장하지 않음 (V1.3.1)",
    ))

    # --- Knowledge/Evergreen x2 (KN-004 REMOVED, replaced by KN-007; KN-008 rewritten) ---
    items.append(knowledge_item(
        "KN-008", "시간관리 매트릭스 활용법", "REMOTE_WORK",
        [
            {"slide": 1, "role": "hook", "text": "급한 일만 처리하다 하루가 끝나버린 적 있으신가요.",
             "image_role": "바쁜 하루를 암시하는 인포그래픽 배경"},
            {"slide": 2, "role": "concept_definition",
             "text": "긴급함과 중요함이라는 두 기준으로 할 일을 나누는 분류법이 있습니다. 긴급하고 중요한 일, 중요하지만 급하지 않은 일, 급하지만 중요하지 않은 일, 둘 다 아닌 일로 나눠보는 방식입니다.",
             "image_role": "네 칸으로 나뉜 분류 도식 이미지"},
            {"slide": 3, "role": "practical_application",
             "text": "오늘 할 일을 이 네 칸에 나눠 적어보세요. 중요하지만 급하지 않은 일부터 먼저 살펴보는 방법도 시도해볼 수 있습니다.",
             "image_role": "실제 할 일이 채워진 분류 예시 이미지"},
            {"slide": 4, "role": "cta_summary", "text": "저장해두고 오늘 할 일을 네 칸에 나눠 적어보세요.",
             "image_role": "저장 유도용 마무리 이미지"},
        ],
        "저장해두고 오늘 할 일을 네 칸에 나눠 적어보세요.",
        "CN-009(재택근무 생산성 루틴), IG-009(직장인 점심시간 활용법)와 REMOTE_WORK 클러스터 공유",
        None,
        (
            "'아이젠하워'라는 인물 귀속 및 '여유 있게 처리할 수 있다'는 효과 단정을 모두 삭제. 슬라이드2는 "
            "무귀속·무효과 주장의 분류법 설명만 남았으나, 이는 여전히 '분류' 범주에 해당하므로 CTO 지침 5항에 따라 "
            "evidence_not_required_reason을 이 항목 전체에는 부여하지 않음 (null로 유지). 슬라이드3/4는 독자가 "
            "스스로 할 일을 정리하도록 요청하는 personal_organization_prompt 성격이지만, 항목 단위 필드는 슬라이드2의 "
            "분류 설명이 섞여 있어 보수적으로 미부여 처리 -- 상세 근거는 EVIDENCE_RED_TEAM_V1_3_1.md 참조 (V1.3.1)"
        ),
    ))
    items.append(knowledge_item(
        "KN-007", "회의록 작성 기본기", "WORKPLACE_COMM",
        [
            {"slide": 1, "role": "hook", "text": "회의는 했는데, 뭘 했는지 기억이 안 나시나요.",
             "image_role": "회의실/메모를 암시하는 인포그래픽 배경"},
            {"slide": 2, "role": "concept_definition", "promised_count": 5,
             "list_items": ["회의 날짜와 시간", "참석자 명단", "논의한 안건", "결정된 사항", "담당자와 기한이 있는 실행 항목"],
             "text": "회의록에는 보통 다음 5가지 항목을 적습니다. 회의 날짜와 시간, 참석자 명단, 논의한 안건, 결정된 사항, 담당자와 기한이 있는 실행 항목입니다.",
             "image_role": "다섯 항목이 표시된 회의록 양식 이미지"},
            {"slide": 3, "role": "practical_application",
             "text": "다음 회의부터는 이 다섯 항목을 빈 표로 만들어두고, 회의가 끝나자마자 바로 채워보세요.",
             "image_role": "빈 표 양식 이미지"},
            {"slide": 4, "role": "cta_summary", "text": "저장해두고 다음 회의에 이 양식을 활용해보세요.",
             "image_role": "저장 유도용 마무리 이미지"},
        ],
        "저장해두고 다음 회의에 이 양식을 활용해보세요.",
        "IG-013/CN-025와 다른 LEARNING_HABIT 계열이 아닌 별도 문서-템플릿 콘텐츠 -- 현재 확인된 cross-channel cluster 없음, 향후 '업무 문서 템플릿' 클러스터 후보",
        "pure_operator_instruction",
        (
            "회의록에 통상 포함되는 항목(날짜, 참석자, 안건, 결정사항, 실행항목)을 나열하는 문서 양식 안내 -- "
            "특정 이론/연구/인물에 귀속되지 않고, 효과·성과를 주장하지 않는 순수 문서 템플릿 지침. "
            "이전 배치의 습관-형성 관련 Knowledge 항목을 대체 (V1.3.1 신규 채택; 대체 사유는 BATCH_HANDOFF_V1_3_1.md 참조)"
        ),
        number_check={"promised": 5, "actual_items": 5, "match": True},
    ))

    return items


def run_qa(items):
    lines = []
    ok = True

    lines.append(f"[생성 개수 정확히 12개] {'PASS' if len(items) == 12 else 'FAIL'} -- count={len(items)}")
    ok &= len(items) == 12

    by_type_expected = {"cardnews": 4, "shorts": 3, "instagram_feed": 3, "knowledge_evergreen": 2}
    by_type_actual = {}
    for it in items:
        by_type_actual[it["content_type"]] = by_type_actual.get(it["content_type"], 0) + 1
    lines.append(f"[채널별 구성 4/3/3/2] {'PASS' if by_type_actual == by_type_expected else 'FAIL'} -- actual={by_type_actual}")
    ok &= by_type_actual == by_type_expected

    all_ids = [it["content_id"] for it in items]
    kn004_present = BANNED_CONTENT_ID in all_ids
    kn004_anywhere = any(BANNED_CONTENT_ID in s for it in items for s in flatten_strings(it) if isinstance(s, str))
    lines.append(f"[KN-004 완전 제외] {'PASS' if not kn004_present and not kn004_anywhere else 'FAIL'} -- present_as_id={kn004_present}, mentioned_anywhere={kn004_anywhere}")
    ok &= not kn004_present and not kn004_anywhere

    dupes = {i for i in all_ids if all_ids.count(i) > 1}
    lines.append(f"[content_id 중복] {'PASS' if not dupes else 'FAIL'} -- duplicates={sorted(dupes)}")
    ok &= not dupes

    def prose_strings(it):
        ct = it["content_type"]
        out = []
        if ct in ("cardnews", "knowledge_evergreen"):
            out.extend(s["text"] for s in it["final_copy"]["slides"])
        elif ct == "shorts":
            for s in it["final_copy"]["scenes"]:
                out.append(s["narration"]); out.append(s["subtitle"])
        elif ct == "instagram_feed":
            out.append(it["final_copy"]["hook"]); out.append(it["final_copy"]["body"])
        return out

    all_sentences = []
    for it in items:
        for s in prose_strings(it):
            all_sentences.extend(split_sentences(s))
    dup_sentences = {s for s in all_sentences if all_sentences.count(s) > 1}
    lines.append(f"[중복/복제 문장 탐지] {'PASS' if not dup_sentences else 'FAIL'} -- duplicates={list(dup_sentences)[:10]}")
    ok &= not dup_sentences

    removed_phrase_hits = []
    general_risk_hits = []
    for it in items:
        for s in prose_strings(it):
            for p in REMOVED_RISK_PHRASES:
                if p in s:
                    removed_phrase_hits.append((it["content_id"], p, s[:60]))
            for kw in GENERAL_RISK_KEYWORDS:
                if re.search(kw, s):
                    general_risk_hits.append((it["content_id"], kw, s[:60]))
    lines.append(f"[제거 대상 문구 재출현 여부 (regression guard)] {'PASS' if not removed_phrase_hits else 'FAIL'} -- hits={removed_phrase_hits}")
    ok &= not removed_phrase_hits
    lines.append(f"[건강·동물안전·효과 일반 위험 키워드 (regression guard)] {'PASS' if not general_risk_hits else 'FAIL'} -- hits={general_risk_hits}")
    ok &= not general_risk_hits
    lines.append(
        "[주의] 위 두 항목은 정규식 기반 회귀 방지 안전망이며, 실제 의미론적 판단은 "
        "EVIDENCE_RED_TEAM_V1_3_1.md의 문장 단위 수기 검토가 근거임 (형식 검사만으로 충분하다고 주장하지 않음)."
    )

    bad_reason_items = []
    for it in items:
        r = it.get("evidence_not_required_reason")
        if r is not None and r not in ALLOWED_EVIDENCE_NOT_REQUIRED_REASONS:
            bad_reason_items.append((it["content_id"], r))
    lines.append(f"[evidence_not_required_reason 어휘 오용] {'PASS' if not bad_reason_items else 'FAIL'} -- bad={bad_reason_items}")
    ok &= not bad_reason_items

    # KN-008 must NOT carry the tag (explicit exclusion, per instruction item 5 on "분류")
    kn008 = next(it for it in items if it["content_id"] == "KN-008")
    kn008_ok = kn008.get("evidence_not_required_reason") is None
    lines.append(f"[KN-008에 evidence_not_required_reason 미부여 확인 (분류 콘텐츠 제외 규칙)] {'PASS' if kn008_ok else 'FAIL'}")
    ok &= kn008_ok

    real_value_hits = []
    for it in items:
        for s in flatten_strings(it):
            for rx in FORBIDDEN_REAL_VALUE_PATTERNS:
                if rx.search(s):
                    real_value_hits.append(s[:80])
    lines.append(f"[실제 URL/승인/수치 조작] {'PASS' if not real_value_hits else 'FAIL'} -- hits={real_value_hits[:10]}")
    ok &= not real_value_hits

    not_false = [it["content_id"] for it in items if it["publish_ready"] is not False or it["actual_publish"] is not False]
    lines.append(f"[publish_ready/actual_publish 전부 false] {'PASS' if not not_false else 'FAIL'} -- violations={not_false}")
    ok &= not not_false

    # number consistency for any item making a numeric promise (CardNews + KN-007)
    bad_numbers = []
    for it in items:
        nc = it.get("number_consistency_check")
        if nc and nc.get("promised") is not None and not nc.get("match"):
            bad_numbers.append((it["content_id"], nc))
    lines.append(f"[숫자 약속-실제 항목 수 일치] {'PASS' if not bad_numbers else 'FAIL'} -- mismatches={bad_numbers}")
    ok &= not bad_numbers

    cn_items = [it for it in items if it["content_type"] == "cardnews"]
    bad_cn = []
    for it in cn_items:
        slides = it["final_copy"]["slides"]
        if len(slides) != 4:
            bad_cn.append((it["content_id"], "slide count != 4"))
        for s in slides:
            if "..." in s["text"] or "…" in s["text"]:
                bad_cn.append((it["content_id"], "ellipsis found"))
            if not s["text"].strip().endswith((".", "?", "!")):
                bad_cn.append((it["content_id"], f"incomplete sentence: {s['text'][-20:]}"))
        if len(split_sentences(slides[3]["text"])) != 1:
            bad_cn.append((it["content_id"], "CTA slide not exactly one sentence"))
    lines.append(f"[CardNews: 4장/문장완결/ellipsis 없음/단일 CTA] {'PASS' if not bad_cn else 'FAIL'} -- issues={bad_cn}")
    ok &= not bad_cn

    return ok, lines


def render_handoff(items, qa_ok, qa_lines):
    lines = [
        "# Batch Handoff V1.3.1 -- Evidence Red-Team Correction", "",
        f"## Final verdict: {'GO for manual production' if qa_ok else 'NO-GO'}", "",
        "This is a correction pass triggered by the CTO's explicit distrust of V1.3's "
        "'SOURCE_REQUIRED == 0' check -- that check was a string-match, not a semantic audit. "
        "Every sentence in every V1.3 item was re-read individually; the full sentence-level "
        "reasoning is in `EVIDENCE_RED_TEAM_V1_3_1.md`. This document summarizes the outcome.", "",
        "## What changed and why", "",
        "**KN-004 (습관 형성 21일 법칙 진실) -- REMOVED, not just its number.** The V1.2 top-20 "
        "Knowledge pool contains exactly 2 items (KN-004, KN-008); removing KN-004 without a "
        "same-pool substitute would have left only 1 Knowledge item. Per the CTO's explicit "
        "authorization to lift the top-20 restriction for this replacement, KN-007 (회의록 작성 "
        "기본기) was selected from the full 120-item backlog -- a pure document-template "
        "instruction (what fields a meeting-minutes doc contains) with zero historical, "
        "statistical, or efficacy content.", "",
        "**IG-010 (반려동물 상식 퀴즈형 카드) -- REMOVED, replaced rather than rewritten.** An "
        "OX-quiz-about-pet-facts format cannot be limited to pure prep/record content by "
        "construction: all three questions actually used in V1.3 were implicit health/behavior/"
        "hygiene-prevention claims (daily walking is beneficial, cats tolerate solitude well by "
        "nature, water bowls must be changed to prevent something unstated). None of the three "
        "allowed evidence_not_required_reason values legitimately cover a quiz whose entire "
        "premise is asserting facts about animal care. Same pool-size problem as Knowledge -- the "
        "top-20 has exactly 3 Instagram items -- so IG-007 (문화생활 예산 관리 팁) was pulled from "
        "the full backlog instead: rewritten as a pure personal-budget-tracking prompt (the reader "
        "records and plans their own spending, asserting nothing about the external world).", "",
        "**CN-013 (반려동물 첫 입양 준비물) -- kept, rewritten.** The checklist itself (이동장, "
        "급식기, 사료, 배변용품, 병원 연락처) is pure preparation/record content and stays. Removed: "
        "'이 다섯 가지만 챙기면 ... 적응을 도울 수 있습니다' -- an implicit behavioral/welfare-outcome "
        "claim about the animal's adjustment, unsupported by any citation.", "",
        "**SH-017 (반려동물 산책 준비물 점검) -- kept, unchanged.** Reviewed sentence by sentence; "
        "found no health/behavior/prevention/safety-guarantee claim. It is already a pure gear "
        "checklist.", "",
        "**KN-008 (시간관리 매트릭스 활용법) -- kept, rewritten.** Removed the 'Eisenhower' "
        "attribution entirely (a specific-person historical claim this batch cannot verify) and "
        "the 'you'll have time to spare' efficacy claim. It is now an unattributed description of "
        "a generic urgent/important classification tool plus a personal to-do-sorting prompt. Per "
        "instruction item 5, a classification-scheme description does not qualify for "
        "`evidence_not_required_reason` even once fully unattributed and effect-free -- so this "
        "item's field is deliberately left `null`, not defaulted to any of the three tokens. See "
        "the red-team table for the sentence-level split.", "",
        "**CN-017 (커피 원두 보관법) and SH-006 (커피 내리는 법 3단계) -- kept, rewritten.** Removed "
        "every taste/freshness/extraction-effect assertion: '향이 금방 날아가고 신선함이 떨어집니다' "
        "(a chemistry/degradation claim), '신선함을 더 오래 유지할 수 있습니다' (an outcome guarantee), "
        "'충분해요' (a sufficiency/efficacy claim), '매번 맛이 다르셨다면' (an implicit taste-outcome "
        "causal claim). Storage/brewing steps are now presented as selectable options, never as "
        "causes of a promised result.", "",
        "**IG-009 and IG-013 -- kept, rewritten (not named by the CTO, found during the mandated "
        "full re-read of every final sentence).** IG-009's '점심시간을 조금 다르게 써보는 것만으로 "
        "오후 기분이 달라질 수 있습니다' was an unsupported psychological-effect claim -- rewritten "
        "as 'a possible option,' not a promised mood change. IG-013's '큰 목표부터 세우면 오히려 "
        "지치기 쉽습니다' and '작게 오래 이어가는 것이 핵심입니다' were an unsupported behavioral-"
        "psychology causal claim and an assertive efficacy claim -- both rewritten into 'methods you "
        "can try,' asserting no mechanism.", "",
        "## The new field: evidence_not_required_reason", "",
        "Applied only where a sentence set is genuinely non-claim: `pure_operator_instruction` "
        "(CardNews/Shorts checklists, KN-007's document template), `personal_organization_prompt` "
        "(IG-007/IG-009/IG-013's self-tracking prompts), or `non-claim_creative_copy` (hooks/CTAs, "
        "noted at the sentence level in the red-team table, not separately tagged in the JSON's "
        "per-item summary field to avoid schema bloat). Per instruction item 5, this field is "
        "**never** applied to general facts, common knowledge, classification schemes, historical "
        "claims, health claims, or safety claims -- KN-008 is the one item where this restriction "
        "bites even after full rewriting, and it is left `null` rather than mislabeled.", "",
        "## Selected 12 (final)", "",
    ]
    by_type = {}
    for it in items:
        by_type.setdefault(it["content_type"], []).append(it["content_id"])
    for ct, ids in by_type.items():
        lines.append(f"- **{ct}** ({len(ids)}): {', '.join(ids)}")
    lines.append("")
    lines.append("## QA summary")
    lines.append("")
    lines.append(f"Overall: {'PASS' if qa_ok else 'FAIL'} (full detail in `QA_REPORT_V1_3_1.md`)")
    lines.append("")
    for l in qa_lines:
        lines.append(f"- {l}")
    lines.append("")
    lines.append("## No changes outside the owned folder")
    lines.append("")
    lines.append("This correction only reads from and writes to `external_workclaude/content_portfolio_v1/`. "
                 "No file in `modules/`, `tests/`, `docs/`, `storage/`, `config/`, `site/`, or any shared "
                 "status document was touched, and no Git operation was performed.")
    return "\n".join(lines)


def main():
    items = build_items()
    ok, qa_lines = run_qa(items)

    OUT_BATCH_JSON.write_text(
        json.dumps({"version": "content_portfolio_v1.3.1", "count": len(items), "items": items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    OUT_HANDOFF_MD.write_text(render_handoff(items, ok, qa_lines), encoding="utf-8")
    OUT_QA_MD.write_text(
        "\n".join(["# QA Report V1.3.1 -- Evidence Red-Team Correction", "", f"Overall: {'PASS' if ok else 'FAIL'}", ""] + [f"- {l}" for l in qa_lines]),
        encoding="utf-8",
    )

    print("QA_V1_3_1_OK:", ok)
    for l in qa_lines:
        print(l)


if __name__ == "__main__":
    main()
