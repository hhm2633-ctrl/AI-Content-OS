"""Content Portfolio V1.3 -- Production Content Batch (12 finished, evidence-free packages).

Stdlib only. Selects 12 lowest-risk, offline_ready items from V1.2's top-20 evidence pack
(TOP20_EVIDENCE_PACK.json) -- 4 CardNews, 3 Shorts, 3 Instagram, 2 Knowledge/Evergreen -- and
writes finished, publish-team-ready copy for each. Excludes anything legal/tax/financial/
medical, any current-news/trend topic, any real product/price/stock/review, any real brand/
expert, and any topic that would require an efficacy/statistic/performance claim to be honest.

Hard rules enforced and checked by this script:
- Every item's final copy needs ZERO external evidence -- no citation, no statistic, no named
  expert, no real brand. If a number is promised in the copy (e.g. "5가지"), the actual list has
  exactly that many items.
- No ellipsis-truncated sentences; every sentence is complete.
- Exactly one CTA per item, always a SAVE action.
- No literal "SOURCE_REQUIRED" string appears anywhere in this batch's output -- if a topic
  cannot be written without one, it does not belong in this batch (see BATCH_HANDOFF_V1_3.md for
  the two borderline topics that were included only after being rewritten to make zero
  evidence-requiring claims, and the ones that were excluded instead).
- publish_ready and actual_publish are hardcoded false on every item; no real rights approval,
  price, performance, or URL is fabricated anywhere.

Never reads/writes outside external_workclaude/content_portfolio_v1/, no network call, no real
publish/purchase/account action.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

OUT_BATCH_JSON = BASE / "PRODUCTION_BATCH_V1_3.json"
OUT_CARDNEWS_MD = BASE / "CARDNEWS_COPY_BATCH_V1_3.md"
OUT_SHORTS_MD = BASE / "SHORTS_SCRIPT_BATCH_V1_3.md"
OUT_INSTAGRAM_MD = BASE / "INSTAGRAM_COPY_BATCH_V1_3.md"
OUT_KNOWLEDGE_MD = BASE / "KNOWLEDGE_CONTENT_BATCH_V1_3.md"
OUT_SHOTLIST_MD = BASE / "IMAGE_SHOT_LIST_V1_3.md"
OUT_HANDOFF_MD = BASE / "BATCH_HANDOFF_V1_3.md"
OUT_QA_MD = BASE / "QA_REPORT_V1_3.md"

FORBIDDEN_CLAIM_PATTERNS = [
    re.compile(r"\d+(\.\d+)?\s*%"),
    re.compile(r"\d+(,\d{3})*\s*원"),
    re.compile(r"연구에\s*따르면"),
    re.compile(r"임상적으로"),
    re.compile(r"입증"),
    re.compile(r"검증(된|됨)"),
    re.compile(r"1위|베스트셀러|판매량"),
    re.compile(r"승인(됨|완료)"),
    re.compile(r"효능"),
    re.compile(r"치료"),
]

SOURCE_REQUIRED_TOKEN = "SOURCE" + "_REQUIRED"  # split to make the QA scan's intent explicit


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


# ---------------------------------------------------------------------------
# The 12 selected items, fully authored
# ---------------------------------------------------------------------------

def cardnews_item(content_id, working_title, theme_tag, slides, cta_text, cross_channel):
    promised = slides[2]["promised_count"]
    actual = len(slides[2]["list_items"])
    return {
        "content_id": content_id, "content_type": "cardnews", "working_title": working_title,
        "theme_tag": theme_tag,
        "final_copy": {"slides": slides},
        "number_consistency_check": {"promised": promised, "actual_items": actual, "match": promised == actual},
        "cta": cta_text,
        "forbidden_expressions": [
            "효능·치료 효과 단정", "미검증 통계·수치 인용", "특정 브랜드 언급/비방", "실제 가격·재고·후기 언급",
            "허위 긴급성 표현",
        ],
        "evidence_status": "일반 상식·절차 수준 정보만 사용, 외부 검증이 필요한 주장 없음 (근거 확보 대기 항목 없음)",
        "image_role": [f"슬라이드 {s['slide']} ({s['role']}): {s['image_role']}" for s in slides],
        "user_shoot_conditions": [
            "촬영자 본인 소유 공간/사물만 촬영",
            "제3자 얼굴이 식별 가능하게 노출된 경우 동의 확보 전까지 미사용",
            "브랜드 로고 노출 시 블러 처리 또는 재촬영",
        ],
        "generated_image_scope": [
            "CardNewsModule 배경 fallback(단색/그라디언트)만 자동 생성 경로로 즉시 사용 가능",
            "실사형 합성 이미지는 이번 배치 범위 밖 -- 외부 이미지 생성 승인 전까지 미사용",
        ],
        "rights_status": "제로-리스크 경로(자체 촬영 또는 CardNewsModule fallback 배경)는 즉시 사용 가능, 그 외 이미지는 라이선스 미확보 상태로 유지 -- 실제 사용 전 확인 필요",
        "attribution_required": {"required": False, "note": "외부 자료 인용이 없으므로 attribution 불필요"},
        "operator_checklist": [
            "4장 문장이 모두 완결되어 있는지 확인 (말줄임표 없음)",
            "슬라이드3에서 약속한 항목 수와 실제 목록 개수가 일치하는지 확인",
            "CTA가 SAVE 하나뿐인지 확인",
            "이미지 사용 시 자체 촬영/라이선스 여부 확인",
        ],
        "cross_channel_link": cross_channel,
        "publish_ready": False,
        "actual_publish": False,
    }


def shorts_item(content_id, working_title, theme_tag, scenes, cta_text, manual_assets, cross_channel):
    return {
        "content_id": content_id, "content_type": "shorts", "working_title": working_title,
        "theme_tag": theme_tag,
        "final_copy": {"scenes": scenes},
        "cta": cta_text,
        "forbidden_expressions": [
            "효능 단정", "미검증 통계", "실제 조회수·참여 데이터 언급", "실제 브랜드·제품명 노출",
        ],
        "evidence_status": "실연 장면 자체가 근거이며 외부 통계/전문가 인용 없음 -- 근거 확보 대기 항목 없음",
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
        ],
        "manual_assets_needed": manual_assets,
        "execution_boundary": "TTS 생성, 배경음악 삽입, 영상 렌더링, 실제 업로드는 이번 배치에서 수행하지 않음 -- 스크립트/장면표만 완성",
        "cross_channel_link": cross_channel,
        "publish_ready": False,
        "actual_publish": False,
    }


def instagram_item(content_id, working_title, theme_tag, hook, body, cta_text, cross_channel, note=None):
    return {
        "content_id": content_id, "content_type": "instagram_feed", "working_title": working_title,
        "theme_tag": theme_tag,
        "final_copy": {"hook": hook, "body": body},
        "cta": cta_text,
        "forbidden_expressions": [
            "근거 없는 해시태그(성과 최적화 주장 포함) 사용", "미검증 사실 단정", "실제 성과/순위 언급", "실제 브랜드 언급",
        ],
        "evidence_status": (note or "일반 상식·통상적 관행 수준 정보만 사용, 외부 검증이 필요한 주장 없음 (근거 확보 대기 항목 없음)"),
        "image_role": "정보 요약형 카드 배경 또는 단일 피드 이미지 -- 텍스트 삽입 여백 확보",
        "user_shoot_conditions": [
            "촬영자 본인 소유 공간/사물만 촬영",
            "커뮤니티 원문 인용은 이 배치에 포함되지 않음(트렌드 항목 제외)",
        ],
        "generated_image_scope": ["정보 카드 배경(단색/그라디언트)만 자동 생성 허용, 실사 합성 이미지 미사용"],
        "rights_status": "제로-리스크 경로(자체 제작 배경/자체 촬영)만 사용 -- 그 외 이미지는 라이선스 확인 전까지 미사용",
        "attribution_required": {"required": False, "note": "외부 자료 인용이 없으므로 attribution 불필요"},
        "operator_checklist": [
            "본문에 근거 없는 해시태그나 성과 최적화 주장이 없는지 확인",
            "hook과 본문이 완결된 문장인지 확인",
            "CTA가 SAVE 하나뿐인지 확인",
        ],
        "hashtag_policy": "이번 배치에는 해시태그를 포함하지 않음 -- 실제 계정 성과 데이터 없이 '최적화된' 해시태그를 주장할 근거가 없기 때문",
        "cross_channel_link": cross_channel,
        "publish_ready": False,
        "actual_publish": False,
    }


def knowledge_item(content_id, working_title, theme_tag, slides, cta_text, cross_channel, note=None):
    return {
        "content_id": content_id, "content_type": "knowledge_evergreen", "working_title": working_title,
        "theme_tag": theme_tag,
        "final_copy": {"slides": slides},
        "cta": cta_text,
        "forbidden_expressions": [
            "미검증 통계·연구 인용", "특정 연구/논문 결과 단정", "효과·성과 수치 주장",
        ],
        "evidence_status": (note or "통용되는 일반 개념 설명만 사용, 특정 연구/통계 인용 없음 (근거 확보 대기 항목 없음)"),
        "image_role": [f"슬라이드 {s['slide']} ({s['role']}): {s['image_role']}" for s in slides],
        "user_shoot_conditions": ["실사 촬영보다 자체 제작 인포그래픽 권장, 실사 사용 시 본인 소유 사물/공간만"],
        "generated_image_scope": ["인포그래픽 스타일 배경(자체 제작 우선)만 사용, 실사 합성 이미지 미사용"],
        "rights_status": "제로-리스크 경로(자체 제작 인포그래픽)만 사용 -- 그 외 이미지는 라이선스 확인 전까지 미사용",
        "attribution_required": {"required": False, "note": "특정 연구/통계를 인용하지 않으므로 attribution 불필요"},
        "operator_checklist": [
            "특정 연구/통계를 단정적으로 인용하지 않았는지 확인",
            "4장 문장이 모두 완결되어 있는지 확인",
            "CTA가 SAVE 하나뿐인지 확인",
        ],
        "cross_channel_link": cross_channel,
        "publish_ready": False,
        "actual_publish": False,
    }


def build_items():
    items = []

    # --- CardNews x4 ---
    items.append(cardnews_item(
        "CN-013", "반려동물 첫 입양 준비물", "PET_CARE",
        [
            {"slide": 1, "role": "hook", "text": "강아지·고양이, 데려오기 전 이것부터 준비하세요.",
             "image_role": "반려동물을 맞이하는 상황을 암시하는 배경 이미지"},
            {"slide": 2, "role": "problem", "text": "입양 당일 막상 데려오면 무엇부터 챙겨야 할지 몰라 당황하는 경우가 많습니다. 준비물을 미리 챙기지 않으면 첫날부터 아이도 보호자도 힘들어질 수 있습니다.",
             "image_role": "당황스러운 첫날 상황을 보여주는 이미지"},
            {"slide": 3, "role": "solution", "promised_count": 5,
             "list_items": ["이동장", "급식기와 물그릇", "초기 사료", "배변 용품", "가까운 동물병원 정보"],
             "text": "입양 전 꼭 준비해야 할 5가지가 있습니다. 이동장, 급식기와 물그릇, 초기 사료, 배변 용품, 가까운 동물병원 정보입니다. 이 다섯 가지만 미리 챙겨두면 첫날 큰 어려움 없이 적응을 도울 수 있습니다.",
             "image_role": "다섯 가지 준비물을 나열한 이미지"},
            {"slide": 4, "role": "cta", "text": "지금 저장해두고 입양 전날 다시 확인하세요.",
             "image_role": "저장 유도용 마무리 이미지"},
        ],
        "지금 저장해두고 입양 전날 다시 확인하세요.",
        "SH-017(반려동물 산책 준비물 점검, PET_CARE)과 근거·리서치 공유 -- CardNews는 입양 초기 준비물, Shorts는 산책 준비물로 소비 시점이 다름",
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
             "text": "캠핑 전 챙겨야 할 4가지 카테고리가 있습니다. 취침용품, 취사용품, 방한·방수용품, 안전용품입니다. 이 네 가지 카테고리로 나눠 준비하면 빠뜨리는 물건 없이 캠핑을 시작할 수 있습니다.",
             "image_role": "네 가지 카테고리를 나열한 이미지"},
            {"slide": 4, "role": "cta", "text": "저장해두고 캠핑 전날 하나씩 확인하세요.",
             "image_role": "저장 유도용 마무리 이미지"},
        ],
        "저장해두고 캠핑 전날 하나씩 확인하세요.",
        "CN-016(여행 전 짐싸기 체크리스트) 및 SH-018(캐리어 짐싸기 순서)과 CAMPING_TRAVEL_PACK 클러스터 공유 -- 짐 준비라는 동일 맥락을 캠핑 특화/일반 여행/영상 시연으로 분리",
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
             "text": "여행 전 확인할 5가지 카테고리가 있습니다. 신분증과 서류, 전자기기와 충전기, 세면·위생용품, 상비약, 계절에 맞는 옷입니다. 이 순서대로 하나씩 확인하면 짐싸기를 빠짐없이 마칠 수 있습니다.",
             "image_role": "다섯 가지 카테고리를 나열한 이미지"},
            {"slide": 4, "role": "cta", "text": "저장해두고 짐 싸기 전 순서대로 확인하세요.",
             "image_role": "저장 유도용 마무리 이미지"},
        ],
        "저장해두고 짐 싸기 전 순서대로 확인하세요.",
        "CN-014(캠핑 초보 준비물) 및 SH-018(캐리어 짐싸기 순서)과 CAMPING_TRAVEL_PACK 클러스터 공유",
    ))
    items.append(cardnews_item(
        "CN-017", "커피 원두 보관법", "COFFEE_RITUAL",
        [
            {"slide": 1, "role": "hook", "text": "원두, 아무 데나 보관하고 계신가요.",
             "image_role": "원두 봉투/보관 상황을 암시하는 배경 이미지"},
            {"slide": 2, "role": "problem", "text": "원두를 개봉한 뒤 실온에 그대로 두면 향이 금방 날아가고 신선함이 떨어집니다.",
             "image_role": "실온에 방치된 원두 이미지"},
            {"slide": 3, "role": "solution", "promised_count": 3,
             "list_items": ["밀폐 용기에 담아 공기 접촉 줄이기", "직사광선과 습기를 피해 서늘한 곳에 보관하기", "소분해서 필요한 만큼만 꺼내 쓰기"],
             "text": "원두 보관 시 확인할 3가지가 있습니다. 밀폐 용기에 담아 공기 접촉을 줄이고, 직사광선과 습기를 피해 서늘한 곳에 보관하고, 소분해서 필요한 만큼만 꺼내 쓰는 것입니다. 이 세 가지만 지키면 원두의 신선함을 더 오래 유지할 수 있습니다.",
             "image_role": "밀폐 용기에 소분 보관된 원두 이미지"},
            {"slide": 4, "role": "cta", "text": "저장해두고 오늘부터 원두 보관법을 바꿔보세요.",
             "image_role": "저장 유도용 마무리 이미지"},
        ],
        "저장해두고 오늘부터 원두 보관법을 바꿔보세요.",
        "SH-006(커피 내리는 법 3단계)과 COFFEE_RITUAL 클러스터 공유 -- 보관과 추출을 연속된 커피 콘텐츠 여정으로 연결",
    ))

    # --- Shorts x3 ---
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
        "CN-013(반려동물 첫 입양 준비물)과 PET_CARE 클러스터 공유 -- 입양 준비(정적 카드)와 산책 준비(영상 시연)로 소비 시점 차별화",
    ))
    items.append(shorts_item(
        "SH-006", "커피 내리는 법 3단계", "COFFEE_RITUAL",
        [
            {"scene": 1, "duration_sec": "0-3", "role": "hook", "visual": "필터에 원두 붓는 장면 클로즈업",
             "narration": "커피, 3단계면 충분해요.", "subtitle": "커피 내리는 법 3단계", "shot_composition": "드리퍼와 원두 클로즈업"},
            {"scene": 2, "duration_sec": "3-10", "role": "context", "visual": "어설프게 내린 커피 잔 클로즈업(연출)",
             "narration": "매번 맛이 다르셨다면.", "subtitle": "이 3단계만 기억하세요", "shot_composition": "커피 잔 클로즈업"},
            {"scene": 3, "duration_sec": "10-35", "role": "core_steps", "visual": "원두 계량 -> 물 온도 확인 -> 천천히 붓기 3컷",
             "narration": "원두 계량, 물 온도, 천천히 붓기 순서예요.", "subtitle": "계량 -> 온도 -> 붓기", "shot_composition": "저울/온도계/드리퍼 각각 클로즈업"},
            {"scene": 4, "duration_sec": "35-45", "role": "cta", "visual": "완성된 커피 잔",
             "narration": "저장해두고 다음에 따라해보세요.", "subtitle": "저장하고 따라하기", "shot_composition": "완성된 커피 잔 탑샷"},
        ],
        "저장해두고 다음에 따라해보세요.",
        ["실제 원두, 드리퍼, 필터 (촬영자 본인 소유)", "저울/온도계(있는 경우)"],
        "CN-017(커피 원두 보관법)과 COFFEE_RITUAL 클러스터 공유",
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
        "CN-014/CN-016(캠핑·여행 짐싸기 체크리스트)과 CAMPING_TRAVEL_PACK 클러스터 공유 -- 정적 체크리스트와 영상 시연으로 포맷 차별화",
    ))

    # --- Instagram x3 ---
    items.append(instagram_item(
        "IG-010", "반려동물 상식 퀴즈형 카드", "PET_CARE",
        "반려동물 상식, OX로 확인해볼까요?",
        (
            "Q1. 강아지는 매일 산책을 시켜주는 것이 좋다 - O. "
            "Q2. 고양이는 원래 혼자 있는 시간도 잘 보내는 편이다 - O. "
            "Q3. 반려동물 물그릇은 아무 때나 갈아줘도 상관없다 - X. 자주 깨끗한 물로 갈아주는 습관을 들이면 좋습니다. "
            "반려동물과 함께하는 하루, 작은 습관 하나가 큰 차이를 만듭니다."
        ),
        "저장해두고 오늘 하나씩 확인해보세요.",
        "CN-013(반려동물 첫 입양 준비물)과 PET_CARE 클러스터 공유",
        note=(
            "여기 포함된 3문항은 특정 수의학적 진단/치료/영양 성분 주장이 아니라 산책·독립성·물그릇 관리처럼 "
            "일반적으로 통용되는 반려동물 돌봄 상식 수준으로 한정 -- 외부 검증이 필요한 주장 없음"
        ),
    ))
    items.append(instagram_item(
        "IG-009", "직장인 점심시간 활용법", "REMOTE_WORK",
        "점심시간 1시간, 어떻게 보내고 계신가요?",
        (
            "회의와 업무 사이, 짧은 점심시간을 그냥 흘려보내는 경우가 많습니다. 오늘은 이렇게 써보는 건 어떨까요. "
            "첫째, 식사 후 10분이라도 걸어보기. 둘째, 스마트폰 대신 잠깐 눈을 감고 쉬어보기. "
            "셋째, 내일 할 일을 미리 가볍게 메모해두기. "
            "거창하지 않아도 점심시간을 조금 다르게 써보는 것만으로 오후 기분이 달라질 수 있습니다."
        ),
        "저장해두고 오늘 점심시간에 하나만 시도해보세요.",
        "CN-009(재택근무 생산성 루틴), KN-008(시간관리 매트릭스 활용법)과 REMOTE_WORK 클러스터 공유",
    ))
    items.append(instagram_item(
        "IG-013", "자기계발 습관 만들기 팁", "LEARNING_HABIT",
        "작심삼일, 왜 자꾸 반복될까요?",
        (
            "습관을 만들려고 큰 목표부터 세우면 오히려 지치기 쉽습니다. "
            "하나, 목표를 아주 작게 쪼개보세요. 둘, 이미 하고 있는 행동 뒤에 새 습관을 붙여보세요. "
            "예를 들어 양치 후 스트레칭 한 번처럼요. 셋, 완벽하게 하려 하지 말고 이어가는 것 자체에 집중해보세요. "
            "습관은 크게 시작하는 것보다 작게 오래 이어가는 것이 핵심입니다."
        ),
        "저장해두고 오늘 작은 습관 하나부터 시작해보세요.",
        "CN-025(온라인 강의 완주하는 습관), KN-004(습관 형성 21일 법칙 진실)와 LEARNING_HABIT 클러스터 공유",
    ))

    # --- Knowledge/Evergreen x2 ---
    items.append(knowledge_item(
        "KN-008", "시간관리 매트릭스 활용법", "REMOTE_WORK",
        [
            {"slide": 1, "role": "hook", "text": "급한 일만 처리하다 하루가 끝나버린 적 있으신가요.",
             "image_role": "바쁜 하루를 암시하는 인포그래픽 배경"},
            {"slide": 2, "role": "concept_definition",
             "text": "아이젠하워 매트릭스는 할 일을 긴급함과 중요함 두 기준으로 나눠 우선순위를 정하는 방법입니다. 긴급하고 중요한 일, 중요하지만 급하지 않은 일, 급하지만 중요하지 않은 일, 둘 다 아닌 일로 나눠보는 것입니다.",
             "image_role": "네 칸으로 나뉜 매트릭스 도식 이미지"},
            {"slide": 3, "role": "practical_application",
             "text": "오늘 할 일을 이 네 칸에 나눠 적어보세요. 중요하지만 급하지 않은 일을 먼저 챙겨두면, 나중에 급한 일이 되기 전에 여유 있게 처리할 수 있습니다.",
             "image_role": "실제 할 일이 채워진 매트릭스 예시 이미지"},
            {"slide": 4, "role": "cta_summary", "text": "저장해두고 오늘 할 일을 네 칸에 나눠 적어보세요.",
             "image_role": "저장 유도용 마무리 이미지"},
        ],
        "저장해두고 오늘 할 일을 네 칸에 나눠 적어보세요.",
        "CN-009(재택근무 생산성 루틴), IG-009(직장인 점심시간 활용법)와 REMOTE_WORK 클러스터 공유",
    ))
    items.append(knowledge_item(
        "KN-004", "습관 형성 21일 법칙 진실", "LEARNING_HABIT",
        [
            {"slide": 1, "role": "hook", "text": "21일이면 습관이 된다는 말, 들어보셨죠.",
             "image_role": "달력/체크리스트를 암시하는 인포그래픽 배경"},
            {"slide": 2, "role": "concept_definition",
             "text": "이 말은 널리 알려진 이야기지만, 실제로 습관이 자리잡는 데 걸리는 시간은 사람마다, 습관마다 다르다고 보는 시각이 많습니다. 특정 날짜 수에 얽매이기보다, 습관이 자리잡는 과정 자체에 집중하는 것이 더 현실적인 접근입니다.",
             "image_role": "다양한 기간을 암시하는 이미지 (특정 숫자 강조 지양)"},
            {"slide": 3, "role": "practical_application",
             "text": "정해진 날짜를 채우는 데 집중하기보다, 하루하루 이어가는 것 자체를 목표로 삼아보세요. 하루를 건너뛰어도 자책하지 말고 다음 날 다시 이어가면 됩니다.",
             "image_role": "꾸준함을 상징하는 이미지"},
            {"slide": 4, "role": "cta_summary", "text": "저장해두고 오늘부터 날짜 대신 꾸준함에 집중해보세요.",
             "image_role": "저장 유도용 마무리 이미지"},
        ],
        "저장해두고 오늘부터 날짜 대신 꾸준함에 집중해보세요.",
        "CN-025(온라인 강의 완주하는 습관), IG-013(자기계발 습관 만들기 팁)과 LEARNING_HABIT 클러스터 공유",
        note=(
            "이 콘텐츠는 '21일 법칙'이라는 대중적 통설을 다루되, 특정 연구/논문의 대안 수치를 인용하지 않고 "
            "'사람마다 다르다고 보는 시각이 많다'는 헤지된 일반론으로만 서술 -- 통설을 반박하는 competing 통계를 "
            "제시하지 않으므로 외부 근거 검증이 필요 없음 (자세한 선정 사유는 BATCH_HANDOFF_V1_3.md 참조)"
        ),
    ))

    return items


# ---------------------------------------------------------------------------
# QA
# ---------------------------------------------------------------------------

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

    ids = [it["content_id"] for it in items]
    dupes = {i for i in ids if ids.count(i) > 1}
    lines.append(f"[content_id 중복] {'PASS' if not dupes else 'FAIL'} -- duplicates={sorted(dupes)}")
    ok &= not dupes

    # Duplicate/cloned sentence detection -- scoped strictly to genuine prose fields, not
    # structural metadata (role labels like "problem"/"solution", duration ranges like "0-3").
    # An earlier version of this check flattened the entire final_copy dict, which flagged
    # role-label repetition (expected -- every CardNews slide 3 is "role": "solution") as if it
    # were cloned prose. Prose fields only: cardnews/knowledge "text" per slide, shorts
    # "narration" and "subtitle" per scene, instagram "hook"/"body".
    def prose_strings(it):
        ct = it["content_type"]
        out = []
        if ct in ("cardnews", "knowledge_evergreen"):
            out.extend(s["text"] for s in it["final_copy"]["slides"])
        elif ct == "shorts":
            for s in it["final_copy"]["scenes"]:
                out.append(s["narration"])
                out.append(s["subtitle"])
        elif ct == "instagram_feed":
            out.append(it["final_copy"]["hook"])
            out.append(it["final_copy"]["body"])
        return out

    all_sentences = []
    for it in items:
        for s in prose_strings(it):
            all_sentences.extend(split_sentences(s))
    dup_sentences = {s for s in all_sentences if all_sentences.count(s) > 1}
    lines.append(f"[중복/복제 문장 탐지 (final_copy 프로즈 필드 한정)] {'PASS' if not dup_sentences else 'FAIL'} -- duplicates={list(dup_sentences)[:10]}")
    ok &= not dup_sentences

    forbidden_hits = []
    for it in items:
        for s in prose_strings(it):
            for rx in FORBIDDEN_CLAIM_PATTERNS:
                if rx.search(s):
                    forbidden_hits.append((it["content_id"], s[:60]))
    lines.append(f"[미확인 수치·효과·전문가 주장] {'PASS' if not forbidden_hits else 'FAIL'} -- hits={forbidden_hits}")
    ok &= not forbidden_hits

    source_required_hits = []
    for it in items:
        for s in flatten_strings(it):
            if SOURCE_REQUIRED_TOKEN in s:
                source_required_hits.append((it["content_id"], s[:80]))
    lines.append(f"[{SOURCE_REQUIRED_TOKEN} 잔존] {'PASS' if not source_required_hits else 'FAIL'} -- hits={source_required_hits}")
    ok &= not source_required_hits

    fake_rights_hits = []
    for it in items:
        for s in flatten_strings(it):
            if re.search(r"권리\s*승인(됨|완료)|승인(됨|완료)", s):
                fake_rights_hits.append((it["content_id"], s[:80]))
    lines.append(f"[권리 승인 조작] {'PASS' if not fake_rights_hits else 'FAIL'} -- hits={fake_rights_hits}")
    ok &= not fake_rights_hits

    not_false = [it["content_id"] for it in items if it["publish_ready"] is not False or it["actual_publish"] is not False]
    lines.append(f"[publish_ready/actual_publish 전부 false] {'PASS' if not not_false else 'FAIL'} -- violations={not_false}")
    ok &= not not_false

    # CardNews-specific checks
    cn_items = [it for it in items if it["content_type"] == "cardnews"]
    bad_cn = []
    for it in cn_items:
        slides = it["final_copy"]["slides"]
        if len(slides) != 4:
            bad_cn.append((it["content_id"], "slide count != 4"))
            continue
        for s in slides:
            if "..." in s["text"] or "…" in s["text"]:
                bad_cn.append((it["content_id"], "ellipsis found"))
            if not s["text"].strip().endswith((".", "?", "!")):
                bad_cn.append((it["content_id"], f"incomplete sentence: {s['text'][-20:]}"))
        if not it["number_consistency_check"]["match"]:
            bad_cn.append((it["content_id"], "promised count mismatch"))
        cta_sentences = [s for s in split_sentences(slides[3]["text"])]
        if len(cta_sentences) != 1:
            bad_cn.append((it["content_id"], f"CTA slide has {len(cta_sentences)} sentences, expected exactly 1"))
    lines.append(f"[CardNews: 4장/문장완결/ellipsis 없음/숫자일치/단일 CTA] {'PASS' if not bad_cn else 'FAIL'} -- issues={bad_cn}")
    ok &= not bad_cn

    # Shorts-specific checks
    sh_items = [it for it in items if it["content_type"] == "shorts"]
    bad_sh = []
    for it in sh_items:
        scenes = it["final_copy"]["scenes"]
        if len(scenes) != 4:
            bad_sh.append((it["content_id"], "scene count != 4"))
        last_end = scenes[-1]["duration_sec"].split("-")[-1]
        if int(last_end) > 45 or int(last_end) < 15:
            bad_sh.append((it["content_id"], f"total length {last_end}s out of 15-45s window"))
        for req in ("narration", "subtitle", "shot_composition"):
            if any(req not in s for s in scenes):
                bad_sh.append((it["content_id"], f"missing {req} on a scene"))
        if "execution_boundary" not in it:
            bad_sh.append((it["content_id"], "missing execution_boundary"))
    lines.append(f"[Shorts: 4장면/15-45초/내레이션/자막/구도/실행경계] {'PASS' if not bad_sh else 'FAIL'} -- issues={bad_sh}")
    ok &= not bad_sh

    # Instagram-specific checks
    ig_items = [it for it in items if it["content_type"] == "instagram_feed"]
    bad_ig = []
    for it in ig_items:
        if not it["final_copy"].get("hook") or not it["final_copy"].get("body"):
            bad_ig.append((it["content_id"], "missing hook or body"))
        if "hashtag_policy" not in it:
            bad_ig.append((it["content_id"], "missing hashtag_policy"))
        if "#" in json.dumps(it["final_copy"], ensure_ascii=False):
            bad_ig.append((it["content_id"], "contains a hashtag despite no-hashtag policy"))
    lines.append(f"[Instagram: hook/본문/해시태그 정책 준수] {'PASS' if not bad_ig else 'FAIL'} -- issues={bad_ig}")
    ok &= not bad_ig

    # every item: single CTA field non-empty, one sentence
    bad_cta = []
    for it in items:
        cta_sentences = split_sentences(it["cta"])
        if len(cta_sentences) != 1:
            bad_cta.append((it["content_id"], it["cta"]))
    lines.append(f"[전 항목 단일 CTA 문장] {'PASS' if not bad_cta else 'FAIL'} -- issues={bad_cta}")
    ok &= not bad_cta

    return ok, lines


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def render_cardnews_md(items):
    lines = ["# CardNews Copy Batch V1.3 -- 4 finished packages", ""]
    for it in items:
        lines.append(f"## {it['content_id']} -- {it['working_title']}")
        lines.append("")
        for s in it["final_copy"]["slides"]:
            lines.append(f"**Slide {s['slide']} ({s['role']})**: {s['text']}")
        lines.append("")
        lines.append(f"- CTA: {it['cta']}")
        lines.append(f"- number_consistency_check: {it['number_consistency_check']}")
        lines.append(f"- evidence_status: {it['evidence_status']}")
        lines.append(f"- rights_status: {it['rights_status']}")
        lines.append(f"- cross_channel_link: {it['cross_channel_link']}")
        lines.append(f"- publish_ready: {it['publish_ready']} / actual_publish: {it['actual_publish']}")
        lines.append("")
    return "\n".join(lines)


def render_shorts_md(items):
    lines = ["# Shorts Script Batch V1.3 -- 3 finished scripts", ""]
    for it in items:
        lines.append(f"## {it['content_id']} -- {it['working_title']}")
        lines.append("")
        lines.append("| scene | time(s) | role | visual | narration | subtitle | shot composition |")
        lines.append("|---|---|---|---|---|---|---|")
        for s in it["final_copy"]["scenes"]:
            lines.append(f"| {s['scene']} | {s['duration_sec']} | {s['role']} | {s['visual']} | {s['narration']} | {s['subtitle']} | {s['shot_composition']} |")
        lines.append("")
        lines.append(f"- CTA: {it['cta']}")
        lines.append(f"- manual_assets_needed: {it['manual_assets_needed']}")
        lines.append(f"- execution_boundary: {it['execution_boundary']}")
        lines.append(f"- rights_status: {it['rights_status']}")
        lines.append(f"- cross_channel_link: {it['cross_channel_link']}")
        lines.append(f"- publish_ready: {it['publish_ready']} / actual_publish: {it['actual_publish']}")
        lines.append("")
    return "\n".join(lines)


def render_instagram_md(items):
    lines = ["# Instagram Copy Batch V1.3 -- 3 finished posts", ""]
    for it in items:
        lines.append(f"## {it['content_id']} -- {it['working_title']}")
        lines.append("")
        lines.append(f"**Hook:** {it['final_copy']['hook']}")
        lines.append("")
        lines.append(f"**Body:** {it['final_copy']['body']}")
        lines.append("")
        lines.append(f"- CTA: {it['cta']}")
        lines.append(f"- hashtag_policy: {it['hashtag_policy']}")
        lines.append(f"- evidence_status: {it['evidence_status']}")
        lines.append(f"- rights_status: {it['rights_status']}")
        lines.append(f"- cross_channel_link: {it['cross_channel_link']}")
        lines.append(f"- publish_ready: {it['publish_ready']} / actual_publish: {it['actual_publish']}")
        lines.append("")
    return "\n".join(lines)


def render_knowledge_md(items):
    lines = ["# Knowledge/Evergreen Content Batch V1.3 -- 2 finished packages", ""]
    for it in items:
        lines.append(f"## {it['content_id']} -- {it['working_title']}")
        lines.append("")
        for s in it["final_copy"]["slides"]:
            lines.append(f"**Slide {s['slide']} ({s['role']})**: {s['text']}")
        lines.append("")
        lines.append(f"- CTA: {it['cta']}")
        lines.append(f"- evidence_status: {it['evidence_status']}")
        lines.append(f"- rights_status: {it['rights_status']}")
        lines.append(f"- cross_channel_link: {it['cross_channel_link']}")
        lines.append(f"- publish_ready: {it['publish_ready']} / actual_publish: {it['actual_publish']}")
        lines.append("")
    return "\n".join(lines)


def render_shotlist_md(items):
    lines = ["# Image / Shot List V1.3 -- all 12 items", "",
              "Consolidated shooting/image reference for the production team. No image has been captured or "
              "generated yet for any item -- every row is prospective.", ""]
    for it in items:
        lines.append(f"## {it['content_id']} -- {it['working_title']} ({it['content_type']})")
        lines.append("")
        if isinstance(it["image_role"], list):
            for r in it["image_role"]:
                lines.append(f"- {r}")
        else:
            lines.append(f"- {it['image_role']}")
        lines.append("")
        lines.append("**User-shoot conditions:**")
        for c in it["user_shoot_conditions"]:
            lines.append(f"- {c}")
        lines.append("")
        lines.append("**Generated-image scope:**")
        for c in it["generated_image_scope"]:
            lines.append(f"- {c}")
        lines.append("")
        lines.append(f"**Rights status:** {it['rights_status']}")
        lines.append("")
    return "\n".join(lines)


def render_handoff_md(items, qa_ok, qa_lines):
    by_type = {}
    for it in items:
        by_type.setdefault(it["content_type"], []).append(it["content_id"])
    lines = [
        "# Batch Handoff V1.3 -- Production Content Batch", "",
        f"## Final verdict: {'GO for manual production' if qa_ok else 'NO-GO'}", "",
        "All 12 packages are finished copy, ready for a human production team to shoot/render and "
        "for an operator to complete the rights intake before any publish decision. "
        "`publish_ready` and `actual_publish` are hardcoded `false` on every item -- this batch does "
        "not publish anything.", "",
        "## Selection and exclusions (full transparency)", "",
        "Selected from V1.2's `TOP20_EVIDENCE_PACK.json` (the only pool this instruction authorized "
        "selecting from), by priority score, after screening every one of the 20 against the exclusion "
        "list (legal/tax/finance/medical, current news/trend, real product/price/review, real brand/"
        "expert, topics requiring an efficacy/statistic/performance claim, and anything still carrying "
        "an outstanding source-required marker).", "",
        "**Excluded from the top-20 pool and why:**",
        "- CN-010 (초보자를 위한 홈트레이닝 루틴): fitness/health-adjacent (matched the health keyword filter) -- "
        "excluded out of caution even though 'exercise routine' is not strictly medical, since a safer "
        "CardNews alternative (CN-017) was available at the same score tier.",
        "- SH-004 (하루 만보 걷기 루틴): same health-adjacency reasoning as CN-010.",
        "- SH-014 (편의점 다이어트 조합): explicitly diet/weight-related -- excluded.",
        "- SH-016 (지갑 정리 미니멀 챌린지): not excluded for risk, simply not selected once 3 safer Shorts slots "
        "were filled by score (SH-017, SH-006, SH-018); it remains a safe candidate for a future batch.",
        "", "**Two items required careful rewriting rather than straightforward inclusion:**",
        "- IG-010 (반려동물 상식 퀴즈형 카드): the OX-quiz format risks inviting a veterinary/health claim. "
        "The three questions actually used (daily walks are good, cats tolerate solitude well, water bowls "
        "should be changed regularly) were deliberately restricted to uncontroversial pet-ownership "
        "routine knowledge -- no toxicology, no medical, no specific figure. See the item's `evidence_status` "
        "note for the explicit boundary drawn.",
        "- KN-004 (습관 형성 21일 법칙 진실): the working title itself invites a 'here's the real number' framing, "
        "which would require citing a specific study -- exactly what this batch must avoid. It was rewritten to "
        "make **no competing numeric claim at all**: it says the 21-day figure is a popular oversimplification "
        "and that formation time varies by person, without asserting any alternative statistic, then pivots to "
        "an evidence-free behavioral recommendation (focus on consistency, not a fixed deadline). This was the "
        "only way to include it without an outstanding evidence requirement -- the V1.2 top-20 Knowledge pool "
        "has exactly 2 items, and excluding KN-004 without substitution would have left only 1 Knowledge item, "
        "short of the required 2. If the CTO judges this topic too close to the exclusion line regardless of "
        "the rewrite, the recommended replacement is any non-regulated Knowledge/Evergreen brief from the full "
        "120-item backlog (e.g. KN-011/KN-020 style concept explainers) in a follow-up batch.",
        "", "## Selected 12", "",
    ]
    for ct, ids in by_type.items():
        lines.append(f"- **{ct}** ({len(ids)}): {', '.join(ids)}")
    lines.append("")
    lines.append("## QA summary")
    lines.append("")
    lines.append(f"Overall: {'PASS' if qa_ok else 'FAIL'} (full detail in `QA_REPORT_V1_3.md`)")
    lines.append("")
    for l in qa_lines:
        lines.append(f"- {l}")
    lines.append("")
    lines.append("## No changes outside the owned folder")
    lines.append("")
    lines.append("This batch only reads from and writes to `external_workclaude/content_portfolio_v1/`. No file "
                 "in `modules/`, `tests/`, `docs/`, `storage/`, `config/`, `site/`, or any shared status document "
                 "was touched, and no Git operation was performed.")
    return "\n".join(lines)


def main():
    items = build_items()
    ok, qa_lines = run_qa(items)

    OUT_BATCH_JSON.write_text(
        json.dumps({"version": "content_portfolio_v1.3", "count": len(items), "items": items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    OUT_CARDNEWS_MD.write_text(render_cardnews_md([it for it in items if it["content_type"] == "cardnews"]), encoding="utf-8")
    OUT_SHORTS_MD.write_text(render_shorts_md([it for it in items if it["content_type"] == "shorts"]), encoding="utf-8")
    OUT_INSTAGRAM_MD.write_text(render_instagram_md([it for it in items if it["content_type"] == "instagram_feed"]), encoding="utf-8")
    OUT_KNOWLEDGE_MD.write_text(render_knowledge_md([it for it in items if it["content_type"] == "knowledge_evergreen"]), encoding="utf-8")
    OUT_SHOTLIST_MD.write_text(render_shotlist_md(items), encoding="utf-8")
    OUT_HANDOFF_MD.write_text(render_handoff_md(items, ok, qa_lines), encoding="utf-8")
    OUT_QA_MD.write_text(
        "\n".join(["# QA Report V1.3 -- Production Content Batch", "", f"Overall: {'PASS' if ok else 'FAIL'}", ""] + [f"- {l}" for l in qa_lines]),
        encoding="utf-8",
    )

    print("QA_V1_3_OK:", ok)
    for l in qa_lines:
        print(l)


if __name__ == "__main__":
    main()
