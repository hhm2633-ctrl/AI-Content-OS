import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from modules.common.external_storage import resolve_external_path


class LayoutSelector:
    """
    Layout Engine v2 (CardNews Layout Intelligence Sprint 2).

    Pattern(pattern_prompt_meta), Topic(topic_intelligence), Brand Profile,
    Content Intelligence를 종합해 카드뉴스에 가장 적합한 layout_type을 선택한다.

    지원 layout_type은 LayoutRuleEngine과 동일한 10종
    (notebook, dark_editorial, bold_ai, character_diary, comparison, tutorial,
    checklist, timeline, warning, number_list)이다.

    Sprint 2 개선 (가중치 기반 스코어링으로 재설계):
    - pattern_type 매칭이 여전히 가장 강한 신호(+0.5)다 (Pattern별 최적 Layout 선택).
    - category 매칭에 topic_intelligence.confidence_score를 곱해 신뢰도가 높을수록
      더 크게 반영한다(Topic별 Layout 가중치). 추가로 topic_intelligence.keywords에
      포함된 단어(비교/순위/주의/방법/후기 등)로 세부 layout에 소폭 가점한다.
    - brand_profile에 명시적 preferred_layout 필드가 있으면 우선 반영하고
      (Brand별 Layout 선호도), 없으면 기존 voice 기반 휴리스틱(친근한 말투 ->
      character_diary)을 더 작은 가중치로 사용한다.
    - 모든 layout_type에 대해 가중치를 합산해 가장 높은 점수의 layout을 선택하고,
      그 점수를 0.0~1.0으로 정규화한 layout_score/layout_score_reason을 결과에
      추가한다 (Layout Score).
    - 기존 안전장치(quality_score 낮음/브랜드 위반/중복 위험 높음 -> SAFE_LAYOUT
      강제 대체)는 그대로 유지한다.

    계산에 실패해도 예외를 던지지 않고 안전한 기본 레이아웃(bold_ai)을 반환한다.
    """

    ALL_LAYOUTS: List[str] = [
        "notebook",
        "dark_editorial",
        "bold_ai",
        "character_diary",
        "comparison",
        "tutorial",
        "checklist",
        "timeline",
        "warning",
        "number_list",
    ]

    PATTERN_TYPE_LAYOUT_MAP = {
        "warning": "warning",
        "tutorial": "tutorial",
        "comparison": "comparison",
        "number_list": "number_list",
        "story": "character_diary",
        "resource": "checklist",
    }

    CATEGORY_LAYOUT_MAP = {
        "AI": "bold_ai",
        "부업": "dark_editorial",
        "경제": "notebook",
        "생활": "notebook",
        "쇼핑": "bold_ai",
        "트렌드": "dark_editorial",
    }

    # topic_intelligence.keywords에 특정 단어가 포함되면 세부적으로 어울리는
    # layout_type에 소폭 가점한다 (category보다 더 세밀한 topic 신호).
    KEYWORD_LAYOUT_HINTS = {
        "비교": "comparison",
        "대신": "comparison",
        "vs": "comparison",
        "순위": "number_list",
        "랭킹": "number_list",
        "베스트": "number_list",
        "주의": "warning",
        "경고": "warning",
        "위험": "warning",
        "방법": "tutorial",
        "단계": "tutorial",
        "가이드": "tutorial",
        "후기": "character_diary",
        "일기": "character_diary",
        "경험담": "character_diary",
        "체크리스트": "checklist",
        "준비물": "checklist",
        "타임라인": "timeline",
        "일정": "timeline",
    }

    PATTERN_MATCH_WEIGHT = 0.5
    CATEGORY_BASE_WEIGHT = 0.2
    CATEGORY_CONFIDENCE_WEIGHT = 0.15
    KEYWORD_HINT_WEIGHT = 0.08
    KEYWORD_HINT_MAX_TOTAL_WEIGHT = 0.24
    BRAND_PREFERENCE_WEIGHT = 0.3
    BRAND_VOICE_HEURISTIC_WEIGHT = 0.12
    SAFETY_OVERRIDE_LAYOUT_SCORE = 0.3
    LEARNED_PROFILE_WEIGHT = 0.45
    LEARNED_PROFILE_MIN_SCORE = 0.2

    DEFAULT_LAYOUT = "bold_ai"
    SAFE_LAYOUT = "notebook"
    LOW_QUALITY_THRESHOLD = 0.4

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        configured_path = self.config.get("approved_layout_registry_path")
        self.approved_layout_registry_path = (
            Path(configured_path)
            if configured_path
            else resolve_external_path("artifacts", "design_learning", "owner_source")
            / "approved_layout_registry.json"
        )

    def select(
        self,
        pattern_meta: Optional[Dict[str, Any]] = None,
        topic_intelligence: Optional[Dict[str, Any]] = None,
        brand_profile: Optional[Dict[str, Any]] = None,
        content_intelligence: Optional[Dict[str, Any]] = None,
        design_learning_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            return self._select(
                pattern_meta or {},
                topic_intelligence or {},
                brand_profile or {},
                content_intelligence or {},
                design_learning_context or {},
            )
        except Exception:
            return {
                "layout_type": self.DEFAULT_LAYOUT,
                "reason": "레이아웃 선택 계산 실패로 기본 레이아웃을 사용함.",
                "source": "error_fallback",
                "fallback_used": True,
                "layout_score": 0.0,
                "layout_score_reason": "레이아웃 선택 실패로 0.0 처리함.",
                "design_learning_used": False,
                "selected_layout_profile_id": None,
            }

    def _select(
        self,
        pattern_meta: Dict[str, Any],
        topic_intelligence: Dict[str, Any],
        brand_profile: Dict[str, Any],
        content_intelligence: Dict[str, Any],
        design_learning_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        pattern_type = str(pattern_meta.get("pattern_type", ""))

        scores, reasons = self._score_layouts(pattern_type, topic_intelligence, brand_profile)

        learned_profile, learned_score, learned_reasons = self._select_learned_profile(
            design_learning_context,
            topic_intelligence,
        )
        if learned_profile is not None and learned_score >= self.LEARNED_PROFILE_MIN_SCORE:
            learned_layout = str(learned_profile.get("base_layout_id", ""))
            if learned_layout in scores:
                weight = round(min(self.LEARNED_PROFILE_WEIGHT, learned_score), 4)
                scores[learned_layout] += weight
                reasons.append(
                    f"owner-approved profile '{learned_profile.get('profile_id')}'(+{weight:.4f}: "
                    + ", ".join(learned_reasons)
                    + ")"
                )

        layout_type = max(scores, key=scores.get)
        top_score = scores[layout_type]

        if top_score <= 0.0:
            layout_type = self.DEFAULT_LAYOUT
            source = "default_fallback"
            reason = "pattern_type/topic/brand 신호가 없어 기본 레이아웃을 사용함."
            layout_score = 0.0
        else:
            source = "weighted_selection"
            reason = "; ".join(reasons) + "."
            layout_score = round(min(1.0, top_score), 4)

        risk_reason = self._risk_reason(content_intelligence)

        if risk_reason:
            layout_type = self.SAFE_LAYOUT
            source = "safety_override"
            reason = f"{risk_reason} 안전한 '{self.SAFE_LAYOUT}' 레이아웃으로 대체함."
            layout_score = self.SAFETY_OVERRIDE_LAYOUT_SCORE

        profile_applied = bool(
            learned_profile
            and learned_score >= self.LEARNED_PROFILE_MIN_SCORE
            and learned_profile.get("base_layout_id") == layout_type
            and source != "safety_override"
        )

        return {
            "layout_type": layout_type,
            "reason": reason,
            "source": source,
            "fallback_used": source in ("default_fallback", "safety_override", "error_fallback"),
            "layout_score": layout_score,
            "layout_score_reason": reason,
            "design_learning_used": profile_applied,
            "selected_layout_profile_id": learned_profile.get("profile_id") if profile_applied else None,
            "design_learning_match_score": round(learned_score, 4) if profile_applied else 0.0,
            "style_overrides": dict(learned_profile.get("style_overrides") or {}) if profile_applied else {},
            "design_learning_boundary": "owner_approved_reference_not_performance",
        }

    def _load_approved_profiles(self) -> List[Dict[str, Any]]:
        try:
            payload = json.loads(self.approved_layout_registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return []
        boundary = payload.get("learning_boundary") if isinstance(payload, dict) else None
        if not isinstance(boundary, Mapping) or boundary.get("owner_approval_required") is not True:
            return []
        profiles = payload.get("profiles")
        if not isinstance(profiles, list):
            return []
        return [
            dict(profile)
            for profile in profiles
            if isinstance(profile, Mapping)
            and profile.get("base_layout_id") in self.ALL_LAYOUTS
            and (profile.get("owner_approval") or {}).get("approved_by") == "owner"
            and profile.get("is_performance_evidence") is False
        ]

    @staticmethod
    def _tokens(value: Any) -> set[str]:
        if isinstance(value, (list, tuple, set)):
            return {str(item).strip().casefold() for item in value if str(item).strip()}
        text = str(value or "").strip()
        return {text.casefold()} if text else set()

    def _select_learned_profile(
        self,
        context: Mapping[str, Any],
        topic_intelligence: Mapping[str, Any],
    ) -> Tuple[Optional[Dict[str, Any]], float, List[str]]:
        account_id = str(context.get("account_id") or "").strip().casefold()
        categories = self._tokens(context.get("content_categories"))
        categories |= self._tokens(context.get("category"))
        categories |= self._tokens(topic_intelligence.get("category"))
        moods = self._tokens(context.get("moods"))
        issue_types = self._tokens(context.get("issue_types"))
        media_conditions = self._tokens(context.get("media_conditions"))
        best: Optional[Dict[str, Any]] = None
        best_score = 0.0
        best_reasons: List[str] = []
        for profile in self._load_approved_profiles():
            score = 0.0
            reasons: List[str] = []
            if account_id and account_id in self._tokens(profile.get("account_targets")):
                score += 0.35
                reasons.append("account")
            elif "shared" in self._tokens(profile.get("account_targets")) or profile.get("reference_scope") == "shared":
                score += 0.12
                reasons.append("shared_a_b_c_pool")
            for label, current, weight in (
                ("category", categories, 0.2),
                ("mood", moods, 0.15),
                ("issue", issue_types, 0.15),
                ("media", media_conditions, 0.1),
            ):
                profile_field = {
                    "category": "content_categories",
                    "mood": "moods",
                    "issue": "issue_types",
                    "media": "media_conditions",
                }[label]
                if current & self._tokens(profile.get(profile_field)):
                    score += weight
                    reasons.append(label)
            if score > best_score or (
                score == best_score
                and best is not None
                and str(profile.get("profile_id")) < str(best.get("profile_id"))
            ):
                best, best_score, best_reasons = profile, score, reasons
        return best, min(1.0, best_score), best_reasons

    def _score_layouts(
        self,
        pattern_type: str,
        topic_intelligence: Dict[str, Any],
        brand_profile: Dict[str, Any],
    ) -> Tuple[Dict[str, float], List[str]]:
        scores: Dict[str, float] = {layout: 0.0 for layout in self.ALL_LAYOUTS}
        reasons: List[str] = []

        # --- Pattern별 최적 Layout 선택 (가장 강한 신호) ---
        if pattern_type in self.PATTERN_TYPE_LAYOUT_MAP:
            layout = self.PATTERN_TYPE_LAYOUT_MAP[pattern_type]
            scores[layout] += self.PATTERN_MATCH_WEIGHT
            reasons.append(
                f"pattern_type '{pattern_type}' -> '{layout}'(+{self.PATTERN_MATCH_WEIGHT:.2f})"
            )

        # --- Topic별 Layout 가중치: category를 confidence_score로 가중 ---
        category = str(topic_intelligence.get("category", ""))
        confidence_score = topic_intelligence.get("confidence_score")
        confidence = float(confidence_score) if isinstance(confidence_score, (int, float)) else 0.5
        confidence = max(0.0, min(1.0, confidence))

        if category in self.CATEGORY_LAYOUT_MAP:
            layout = self.CATEGORY_LAYOUT_MAP[category]
            weight = round(self.CATEGORY_BASE_WEIGHT + self.CATEGORY_CONFIDENCE_WEIGHT * confidence, 4)
            scores[layout] += weight
            reasons.append(
                f"category '{category}'(confidence={confidence}) -> '{layout}'(+{weight:.4f})"
            )

        # --- Topic별 Layout 가중치: keyword 세부 신호 ---
        keywords = topic_intelligence.get("keywords", [])
        keyword_weight_used = 0.0

        if isinstance(keywords, list):
            matched_layouts: List[str] = []

            for keyword in keywords:
                keyword_text = str(keyword or "")

                for trigger, layout in self.KEYWORD_LAYOUT_HINTS.items():
                    if trigger in keyword_text and keyword_weight_used < self.KEYWORD_HINT_MAX_TOTAL_WEIGHT:
                        scores[layout] += self.KEYWORD_HINT_WEIGHT
                        keyword_weight_used += self.KEYWORD_HINT_WEIGHT
                        matched_layouts.append(layout)
                        break

            if matched_layouts:
                reasons.append(
                    f"topic keyword 세부 신호로 {matched_layouts} 레이아웃에 가점(+{self.KEYWORD_HINT_WEIGHT:.2f}/건)"
                )

        # --- Brand별 Layout 선호도 반영 ---
        preferred_layout = str(brand_profile.get("preferred_layout", "")).strip()

        if preferred_layout in self.ALL_LAYOUTS:
            scores[preferred_layout] += self.BRAND_PREFERENCE_WEIGHT
            reasons.append(
                f"brand_profile.preferred_layout '{preferred_layout}'(+{self.BRAND_PREFERENCE_WEIGHT:.2f})"
            )
        else:
            voice = str(brand_profile.get("voice", ""))

            if any(word in voice for word in ("친근", "편안", "다정")):
                scores["character_diary"] += self.BRAND_VOICE_HEURISTIC_WEIGHT
                reasons.append(
                    f"brand voice('{voice}') 친근한 말투 -> 'character_diary'"
                    f"(+{self.BRAND_VOICE_HEURISTIC_WEIGHT:.2f})"
                )

        return scores, reasons

    def _risk_reason(self, content_intelligence: Dict[str, Any]) -> str:
        quality_score = content_intelligence.get("quality_score")

        if isinstance(quality_score, (int, float)) and quality_score < self.LOW_QUALITY_THRESHOLD:
            return f"quality_score({quality_score})가 낮아"

        if content_intelligence.get("brand_rule_passed") is False:
            return "브랜드 규칙 위반이 감지되어"

        if content_intelligence.get("duplicate_risk") == "high":
            return "중복 위험이 높아"

        return ""
