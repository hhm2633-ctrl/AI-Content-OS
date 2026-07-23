"""Compile heterogeneous owner-feedback analysis into auditable learning layers.

The compiler is deliberately conservative:
- source JSON files remain immutable;
- screenshot observations are never performance evidence;
- explicit owner corrections may become active owner rules;
- reusable executable patterns are registered only as CANDIDATE;
- promotion and production approval are never performed here.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from modules.knowledge.pattern_contract import Pattern, PatternStatus
from modules.knowledge.pattern_registry import PatternRegistry, PatternRegistryError


SCHEMA_VERSION = "owner_feedback_corpus_v1"
DEFAULT_FEEDBACK_ROOT = Path("knowledge/owner_feedback")
DEFAULT_OUTPUT_PATH = DEFAULT_FEEDBACK_ROOT / "owner_learning_taxonomy_v1.json"
EXCLUDED_SOURCE_FILES = {
    "cardnews_owner_learning_index.json",
    "owner_learning_taxonomy_v1.json",
}

ACCOUNT_KEYWORDS = {
    "news": ("news", "뉴스", "보도", "사건", "정책", "경제", "knn", "편지"),
    "story": ("story", "썰", "연애", "관계", "도파민", "연예", "커뮤니티", "짤"),
    "fashion": ("fashion", "패션", "브랜드", "착장", "아이템", "런웨이"),
    "beauty": ("beauty", "뷰티", "메이크업", "헤어", "피부", "향수"),
    "magazine": ("magazine", "매거진", "큐레이션", "발견형"),
}
FORMAT_KEYWORDS = {
    "card_news": ("card_news", "cardnews", "카드뉴스", "캐러셀", "carousel", "슬라이드"),
    "reels": ("reels", "릴스", "세로 영상"),
    "shorts": ("shorts", "쇼츠"),
    "blog": ("blog", "블로그", "naver", "네이버"),
    "commerce": ("commerce", "커머스", "상품", "제품", "제휴", "쿠팡"),
    "common": ("common", "공통", "workflow", "운영", "파이프라인"),
}
LAYER_KEYWORDS = {
    "topic": ("topic", "주제", "이슈", "소재", "선정"),
    "hook": ("hook", "훅", "첫 장", "첫화면", "표지", "썸네일"),
    "story_structure": ("story", "서사", "구조", "전개", "반전", "가변"),
    "layout": ("layout", "레이아웃", "구도", "배치", "캐러셀"),
    "color": ("color", "색감", "팔레트", "프리셋", "채도"),
    "typography": ("typography", "타이포", "폰트", "자막", "글씨"),
    "image_media": ("image", "visual", "이미지", "영상", "짤", "gif", "캡처"),
    "caption_cta": ("caption", "cta", "본문", "캡션", "댓글", "저장"),
    "source_evidence": ("source", "evidence", "출처", "근거", "저작권", "보도"),
    "commerce": ("commerce", "상품", "제품", "수익", "제휴"),
    "tool": ("tool", "도구", "설치", "capcut", "lightroom", "rtk"),
    "workflow": ("workflow", "pipeline", "자동화", "루프", "검수"),
    "safety": ("guardrail", "금지", "미검증", "승인", "주의"),
}

ACTIVE_RULE_FILE_ALLOWLIST = {
    "account_ai_presenter_identity_rule_v1.json",
    "account_first_screen_system_rule_v1.json",
    "cardnews_automation_human_editor_rule_v1.json",
    "emotional_reaction_media_rule_v1.json",
    "licensed_media_discovery_scope_v1.json",
    "modern_ai_story_entertainment_visual_rule_v1.json",
    "rough_2d_visual_language_rule_v1.json",
    "seasonal_context_spread_learning_rule_v1.json",
    "topic_series_expansion_rule_v1.json",
}

PATTERN_THEMES = (
    {
        "pattern_id": "pattern.owner_corpus.content_pattern.variable_length_emotional_story",
        "name": "근거량에 따른 가변형 감정 서사",
        "domain": "content_pattern",
        "source_files": (
            "owner_correction_cross_format_learning_and_final_redistribution.json",
            "cross_format_prompt_color_story_learning_batch_050_051.json",
            "owner_correction_fashion_item_visual_introduction_pattern.json",
        ),
        "preconditions": ["story 또는 관계·연예·커뮤니티 소재", "사용 가능한 장면과 근거량 확인"],
        "recommended_action": "고정 장수 대신 사건 도입, 감정 상승, 맥락, 반전 또는 판단 요청에 필요한 장면만 사용한다.",
        "prohibited_actions": ["네 장 또는 한 장으로 고정", "근거가 부족한 장면 추가"],
        "failure_signals": ["반복 슬라이드", "감정 전개 단절", "과도한 텍스트"],
        "confidence": 0.5,
    },
    {
        "pattern_id": "pattern.owner_corpus.content_pattern.source_form_preserving_editorial",
        "name": "원자료 형식 보존형 편집",
        "domain": "content_pattern",
        "source_files": (
            "owner_correction_batch_029_celebrity_clip_opinion.json",
            "owner_correction_batch_031_knn_news_reediting.json",
            "owner_correction_batch_033_prison_letter_news_text_edit.json",
            "owner_correction_batch_034_account_type_celebrity_image_use.json",
            "owner_correction_batch_035_trend_capture_mark.json",
        ),
        "preconditions": ["뉴스·방송·SNS·커뮤니티 원자료가 존재", "계정 유형 확인"],
        "recommended_action": "보도는 사실을 왜곡하지 않고, 짤·썰 계정은 허용된 의견과 캡처 표식을 분리해 원자료의 성격을 보존한다.",
        "prohibited_actions": ["원자료와 무관한 인물 이미지 사용", "주장을 확인 사실로 변경"],
        "failure_signals": ["출처 성격 혼동", "사실과 의견 혼합", "무관 이미지"],
        "confidence": 0.55,
    },
    {
        "pattern_id": "pattern.owner_corpus.content_pattern.emotion_reaction_media_fallback",
        "name": "감정 맞춤형 짤·밈·반응 매체 보완",
        "domain": "content_pattern",
        "source_files": (
            "emotional_reaction_media_rule_v1.json",
            "reaction_media_source_extension_tenor_v1.json",
            "cross_format_prompt_color_story_learning_batch_050_051.json",
        ),
        "preconditions": ["story·relationship·dopamine 소재", "직접 참고 이미지가 부족함"],
        "recommended_action": "감정과 서사 역할에 맞는 짤, 밈, 반응 이미지 또는 GIF를 보조 매체로 선택한다.",
        "prohibited_actions": ["무관한 유명인 사용", "사실 장면처럼 제시", "권리 상태 미기록"],
        "failure_signals": ["감정 불일치", "사실 오인", "낡고 저품질인 시각물"],
        "confidence": 0.45,
    },
    {
        "pattern_id": "pattern.owner_corpus.content_pattern.fashion_item_visual_sequence",
        "name": "패션·뷰티 아이템 가변 시각 소개",
        "domain": "content_pattern",
        "source_files": (
            "owner_correction_fashion_item_visual_introduction_pattern.json",
            "cross_format_design_distribution_learning_batch_048_049.json",
        ),
        "preconditions": ["패션·뷰티 브랜드 또는 아이템 주제", "실제 제품·착장·세부 이미지 확인"],
        "recommended_action": "제품 원형, 착장, 각도, 디테일, 스타일링, 핵심 정보를 가용 자료에 맞춰 가변 순서로 구성한다.",
        "prohibited_actions": ["고정 장수 강제", "실제 제품과 다른 생성 이미지로 대체", "상품 연결 강제"],
        "failure_signals": ["제품 식별 불가", "반복 각도", "정보와 이미지 불일치"],
        "confidence": 0.55,
    },
    {
        "pattern_id": "pattern.owner_corpus.content_pattern.account_specific_first_screen",
        "name": "계정 약속을 드러내는 첫 화면",
        "domain": "content_pattern",
        "source_files": (
            "account_first_screen_system_rule_v1.json",
            "modern_ai_story_entertainment_visual_rule_v1.json",
        ),
        "preconditions": ["대상 계정과 콘텐츠 유형이 확정됨"],
        "recommended_action": "뉴스, 짤·썰, 패션·뷰티, 발견형 매거진의 독자 약속에 맞춰 첫 화면의 이미지·제목·정보 밀도를 다르게 선택한다.",
        "prohibited_actions": ["모든 계정에 같은 표지 문법 사용", "무관한 유명인으로 훅 생성"],
        "failure_signals": ["계정 식별 불가", "첫 화면과 본문 불일치"],
        "confidence": 0.5,
    },
    {
        "pattern_id": "pattern.owner_corpus.content_pattern.discovery_magazine_editorial_filter",
        "name": "호기심 기반 발견형 매거진 큐레이션",
        "domain": "content_pattern",
        "source_files": ("owner_correction_three_account_concept_split_537_540.json",),
        "preconditions": ["새롭고 의외이며 설명 가치가 있는 소재", "실제 첫 시각 근거 존재"],
        "recommended_action": "분야가 넓어도 발견 가치, 시의성, 짧은 설명, 반복되는 표지 문법으로 매거진처럼 재편집한다.",
        "prohibited_actions": ["잡다한 소재 단순 나열", "발견 가치 없는 무작위 혼합"],
        "failure_signals": ["편집 기준 부재", "계정 약속 불명확", "표지 문법 불일치"],
        "confidence": 0.45,
    },
    {
        "pattern_id": "pattern.owner_corpus.content_pattern.topic_series_context_expansion",
        "name": "터진 주제의 맥락형 시리즈 확장",
        "domain": "content_pattern",
        "source_files": (
            "topic_series_expansion_rule_v1.json",
            "seasonal_context_spread_learning_rule_v1.json",
        ),
        "preconditions": ["하나의 주제가 실제로 확장 가치가 있음", "계절·생활·카테고리 연결 근거 존재"],
        "recommended_action": "한 주제가 터지면 동일 내용을 반복하지 말고 계절, 생활 문제, 카테고리, 아이템 관점으로 후속 편을 확장한다.",
        "prohibited_actions": ["항상 정해진 편수 생성", "관련성 없는 상품 끼워 넣기"],
        "failure_signals": ["시리즈 간 중복", "맥락 없는 확장", "고정 편수 강제"],
        "confidence": 0.5,
    },
    {
        "pattern_id": "pattern.owner_corpus.engagement_mechanic.real_question_tutorial_outline",
        "name": "실제 질문 기반 교육 목차",
        "domain": "engagement_mechanic",
        "source_files": ("cross_format_video_search_loop_learning_batch_052_053.json",),
        "preconditions": ["실제 댓글 또는 사용자 질문이 존재", "교육형 콘텐츠"],
        "recommended_action": "반복되는 실제 질문을 사회적 증거와 설명 순서로 사용하고 답변을 가변 목차로 구성한다.",
        "prohibited_actions": ["댓글 조작", "존재하지 않는 반응 생성"],
        "failure_signals": ["질문과 답변 불일치", "가짜 사회적 증거"],
        "confidence": 0.45,
    },
    {
        "pattern_id": "pattern.owner_corpus.content_pattern.narrative_payoff_commerce",
        "name": "서사적 반전과 자연스러운 상품 연결",
        "domain": "content_pattern",
        "source_files": (
            "narrative_payoff_commerce_rule_v1.json",
            "commerce_association_reference_v1.json",
        ),
        "preconditions": ["상품 기능과 장면·인물·계절의 실제 연결이 존재"],
        "recommended_action": "표면적 키워드보다 장면의 반전, 기능, 생활 맥락을 찾아 자연스러운 상품 후보를 제안한다.",
        "prohibited_actions": ["모든 주제에 상품 강제", "실사용 후기 조작", "무관 상품 연결"],
        "failure_signals": ["기능 불일치", "억지 연결", "사용 경험 날조"],
        "confidence": 0.5,
    },
    {
        "pattern_id": "pattern.owner_corpus.content_pattern.generated_presenter_identity_gate",
        "name": "계정별 AI 진행자 일관성 게이트",
        "domain": "content_pattern",
        "source_files": (
            "account_ai_presenter_identity_rule_v1.json",
            "owner_correction_batch_040_041_repeated_ai_account_model.json",
        ),
        "preconditions": ["계정별 생성 진행자 전략", "동일 얼굴·신체 유지 메커니즘의 현재 테스트 통과"],
        "recommended_action": "검증된 동일 인물 메커니즘이 있을 때만 계정별 AI 진행자를 반복 사용하고 계정 자산으로 관리한다.",
        "prohibited_actions": ["미검증 반복 생성으로 동일 인물이라 주장", "실제 인물로 오인시키기"],
        "failure_signals": ["얼굴·신체 불일치", "계정 간 모델 혼용", "생성 표시 누락"],
        "confidence": 0.35,
    },
)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _flatten_strings(value: Any, *, limit: int = 80) -> list[str]:
    output: list[str] = []

    def visit(item: Any) -> None:
        if len(output) >= limit:
            return
        if isinstance(item, str):
            text = item.strip()
            if text and text not in output:
                output.append(text[:1000])
        elif isinstance(item, Mapping):
            for child in item.values():
                visit(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                visit(child)

    visit(value)
    return output


def _tags(text: str, mapping: Mapping[str, Iterable[str]]) -> list[str]:
    lowered = text.casefold()
    return [
        tag
        for tag, keywords in mapping.items()
        if any(keyword.casefold() in lowered for keyword in keywords)
    ]


def _source_kind(path: Path, payload: Mapping[str, Any]) -> str:
    record_type = _text(payload.get("record_type")).lower()
    if path.name.startswith("owner_correction") or record_type == "owner_correction":
        return "owner_correction"
    if "tool_candidates" in payload or "tool_candidates_discovered" in payload:
        return "analysis_with_tool_candidates"
    if "items" in payload or "records" in payload:
        return "analysis_batch"
    if "rule_id" in payload or path.name.endswith("_rule_v1.json"):
        return "owner_rule_reference"
    return "reference"


def _item_id(item: Mapping[str, Any], index: int) -> str:
    for key in ("id", "source_id", "item_id", "record_id", "candidate_id", "rule_id"):
        value = item.get(key)
        if isinstance(value, (str, int)) and str(value).strip():
            return re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", str(value).strip())[:80]
    return f"item_{index:04d}"


def _record(
    path: Path,
    payload: Mapping[str, Any],
    item: Mapping[str, Any],
    item_id: str,
    kind: str,
) -> dict[str, Any]:
    strings = _flatten_strings(item)
    combined = " ".join(strings)
    title = next(
        (
            _text(item.get(key))
            for key in ("title", "pattern", "name", "concept", "learning", "rule", "owner_intent")
            if _text(item.get(key))
        ),
        path.stem,
    )
    return {
        "learning_id": f"owner-feedback:{path.stem}:{item_id}",
        "source_file": path.as_posix(),
        "source_item_id": item_id,
        "source_kind": kind,
        "title": title[:300],
        "summary": " | ".join(strings)[:3000],
        "accounts": _tags(combined, ACCOUNT_KEYWORDS),
        "formats": _tags(combined, FORMAT_KEYWORDS),
        "learning_layers": _tags(combined, LAYER_KEYWORDS),
        "owner_confirmed": kind in {"owner_correction", "owner_rule_reference"},
        "is_performance_evidence": False,
        "runtime_connected": payload.get("runtime_connected") is True,
        "tested": payload.get("tested") is True or payload.get("performance_verified") is True,
    }


def _root_record(path: Path, payload: Mapping[str, Any], kind: str) -> dict[str, Any]:
    selected = {
        key: payload.get(key)
        for key in (
            "owner_correction", "owner_intent", "owner_rule", "rule", "standing_learning",
            "standing_learning_rules", "standing_rules", "project_learning", "cross_item_learning",
            "cross_format_distribution", "cross_format_learning",
        )
        if key in payload
    }
    return _record(path, payload, selected or payload, "root", kind)


def _candidate_patterns(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims_by_file: dict[str, list[str]] = {}
    for record in records:
        name = Path(record["source_file"]).name
        claims_by_file.setdefault(name, []).append(record["learning_id"])
    patterns: list[dict[str, Any]] = []
    for theme in PATTERN_THEMES:
        claims: list[str] = []
        for name in theme["source_files"]:
            claims.extend(claims_by_file.get(name, []))
        claims = sorted(dict.fromkeys(claims))[:30]
        if not claims:
            continue
        pattern = Pattern(
            pattern_id=theme["pattern_id"],
            name=theme["name"],
            domain=theme["domain"],
            source_claim_ids=claims,
            preconditions=list(theme["preconditions"]),
            recommended_action=theme["recommended_action"],
            prohibited_actions=list(theme["prohibited_actions"]),
            success_metrics=[],
            failure_signals=list(theme["failure_signals"]),
            confidence=float(theme["confidence"]),
            status=PatternStatus.CANDIDATE,
            version="1.0",
            reviewed_at=None,
            owner_skill="ai-content-os-knowledge-intelligence",
            supersedes=None,
            expires_at=None,
        )
        patterns.append(pattern.to_dict())
    return patterns


def _owner_rule_payload(
    path: Path,
    payload: Mapping[str, Any],
    kind: str,
) -> dict[str, Any] | None:
    if kind != "owner_correction" and path.name not in ACTIVE_RULE_FILE_ALLOWLIST:
        return None
    selected = {
        key: payload.get(key)
        for key in (
            "owner_correction", "owner_intent", "owner_rule", "rule", "standing_learning",
            "standing_learning_rules", "standing_rules", "project_learning", "production_rules",
            "applicable_categories", "category_directions", "first_screen_rules",
            "per_account_identity_spec", "application_rules", "selection_conditions",
            "rejection_conditions",
        )
        if key in payload
    }
    strings = _flatten_strings(selected or payload, limit=30)
    if not strings:
        return None
    combined = f"{path.stem} {' '.join(strings)}"
    categories = _tags(combined, ACCOUNT_KEYWORDS)
    execution_categories = [item for item in categories if item in {"news", "story", "fashion", "beauty"}]
    category = execution_categories[0] if len(execution_categories) == 1 else "multi_account"
    legacy_digest = hashlib.sha256(path.name.encode("utf-8")).hexdigest()[:20]
    canonical = json.dumps(
        {
            "path": path.name,
            "categories": execution_categories,
            "selected": selected,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
    account_scopes = []
    if "news" in execution_categories:
        account_scopes.append("account_a")
    if "story" in execution_categories:
        account_scopes.append("account_b")
    if {"fashion", "beauty"} & set(execution_categories):
        account_scopes.append("account_c")
    return {
        "event_id": f"owner-corpus-rule-{digest}",
        "review_kind": "correction",
        "category": category,
        "title": path.stem.replace("_", " ")[:300],
        "owner_decision": strings[0][:2000],
        "owner_reason": " | ".join(strings[1:] or strings)[:2000],
        "applies_to": sorted(
            dict.fromkeys(
                execution_categories
                + account_scopes
                + _tags(combined, FORMAT_KEYWORDS)
                + ["owner_corpus"]
            )
        ),
        "supersedes_event_id": f"owner-corpus-rule-{legacy_digest}",
        "source": "human_owner_review_workspace",
    }


def compile_owner_feedback_corpus(
    feedback_root: str | Path = DEFAULT_FEEDBACK_ROOT,
    *,
    output_path: str | Path | None = DEFAULT_OUTPUT_PATH,
) -> dict[str, Any]:
    root = Path(feedback_root)
    records: list[dict[str, Any]] = []
    owner_rule_payloads: list[dict[str, Any]] = []
    errors: list[str] = []
    source_count = 0
    for path in sorted(root.glob("*.json"), key=lambda item: item.name.casefold()):
        if path.name in EXCLUDED_SOURCE_FILES:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"read_failed:{path.name}:{type(error).__name__}")
            continue
        if not isinstance(payload, Mapping):
            errors.append(f"invalid_root:{path.name}")
            continue
        source_count += 1
        relative = path.relative_to(Path.cwd()) if path.is_absolute() and Path.cwd() in path.parents else path
        kind = _source_kind(path, payload)
        records.append(_root_record(relative, payload, kind))
        collection = payload.get("items")
        if not isinstance(collection, list):
            collection = payload.get("records")
        if isinstance(collection, list):
            for index, item in enumerate(collection, start=1):
                if isinstance(item, Mapping):
                    records.append(
                        _record(relative, payload, item, _item_id(item, index), kind)
                    )
        rule_payload = _owner_rule_payload(path, payload, kind)
        if rule_payload is not None:
            owner_rule_payloads.append(rule_payload)

    records.sort(key=lambda item: (item["source_file"], item["source_item_id"]))
    candidate_patterns = _candidate_patterns(records)
    stats = {
        "source_file_count": source_count,
        "normalized_record_count": len(records),
        "owner_confirmed_record_count": sum(1 for item in records if item["owner_confirmed"]),
        "candidate_pattern_count": len(candidate_patterns),
        "owner_rule_payload_count": len(owner_rule_payloads),
        "runtime_connected_source_record_count": sum(1 for item in records if item["runtime_connected"]),
        "tested_source_record_count": sum(1 for item in records if item["tested"]),
    }
    taxonomy = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "learning_boundary": {
            "source_files_modified": False,
            "screenshot_observation_is_performance": False,
            "candidate_patterns_auto_promoted": False,
            "explicit_owner_corrections_may_feed_owner_learning": True,
            "runtime_pattern_tier": "CANDIDATE_REFERENCE_ONLY",
        },
        "stats": stats,
        "taxonomy": {
            "accounts": sorted(ACCOUNT_KEYWORDS),
            "formats": sorted(FORMAT_KEYWORDS),
            "learning_layers": sorted(LAYER_KEYWORDS),
        },
        "records": records,
        "candidate_patterns": candidate_patterns,
        "owner_rule_payloads": owner_rule_payloads,
        "errors": errors,
    }
    if output_path is not None:
        _atomic_json(Path(output_path), taxonomy)
    return taxonomy


def register_candidate_patterns(
    patterns: Iterable[Mapping[str, Any]],
    *,
    registry_path: str | Path = Path("knowledge/patterns/pattern_registry.jsonl"),
) -> dict[str, Any]:
    registry = PatternRegistry(Path(registry_path))
    current = registry.current()
    registered: list[str] = []
    skipped_existing: list[str] = []
    rejected: list[dict[str, str]] = []
    for raw in patterns:
        try:
            pattern = Pattern.from_dict(dict(raw))
            if pattern.status is not PatternStatus.CANDIDATE:
                raise ValueError("compiler may register CANDIDATE only")
            if pattern.pattern_id in current:
                skipped_existing.append(pattern.pattern_id)
                continue
            registry.register(pattern)
            current[pattern.pattern_id] = pattern
            registered.append(pattern.pattern_id)
        except (TypeError, ValueError, PatternRegistryError) as error:
            rejected.append(
                {
                    "pattern_id": _text(raw.get("pattern_id")),
                    "reason": str(error),
                }
            )
    return {
        "registered": registered,
        "registered_count": len(registered),
        "skipped_existing": skipped_existing,
        "skipped_existing_count": len(skipped_existing),
        "rejected": rejected,
        "rejected_count": len(rejected),
    }


__all__ = [
    "DEFAULT_FEEDBACK_ROOT",
    "DEFAULT_OUTPUT_PATH",
    "SCHEMA_VERSION",
    "compile_owner_feedback_corpus",
    "register_candidate_patterns",
]
