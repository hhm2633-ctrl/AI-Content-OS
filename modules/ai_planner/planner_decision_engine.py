from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from modules.ai_planner.planning_context import PlanningContext
from modules.ai_planner.planning_result_schema import PLANNER_VERSION, build_undecided_result
from modules.pattern_engine.cta_selector import CTASelector
from modules.pattern_engine.hook_selector import HookSelector
from modules.pattern_engine.pattern_selector import PatternSelector
from modules.topic_engine.confidence_score import ConfidenceScorer
from modules.topic_engine.keyword_weight import KeywordWeightEngine
from modules.topic_engine.topic_classifier import TopicClassifier
from modules.topic_engine.topic_cluster import TopicCluster

# Brand DNA 이력이 이 정도 이상 관측되어야 pattern 기반 기본값 대신 실제 브랜드
# 선호도를 채택한다 - 소수 관측치의 노이즈로 매번 뒤집히는 것을 방지한다.
MIN_BRAND_DNA_OBSERVATIONS_FOR_OVERRIDE = 5

# Image Strategy Engine의 ContentTypeClassifier와 동일한 값 체계(education/
# tutorial/ai_tools/news/community/shopping/review/promotion)를 쓰지만, 이
# Planner 위치에서는 아직 content_result가 없으므로 keyword/source만으로
# 미리 추정한다 - 최종 판단은 여전히 ImageStrategyModule이 content_result까지
# 갖고 다시 내린다 (이 값은 어디까지나 사전 힌트).
CONTENT_TYPE_KEYWORD_RULES: Dict[str, List[str]] = {
    "shopping": ["쇼핑", "스마트스토어", "쿠팡", "할인", "구매", "특가", "최저가", "상품 추천"],
    "review": ["후기", "리뷰", "사용해보니", "써본", "직접 써", "경험담"],
    "promotion": ["광고", "프로모션", "이벤트", "공동구매", "할인코드", "협찬"],
    "ai_tools": ["chatgpt", "gpt", "claude", "codex", "gemini", "미드저니", "ai 툴", "ai툴", "프롬프트"],
    "tutorial": ["하는 법", "만드는 법", "세팅", "따라하기", "튜토리얼", "가이드"],
}
COMMUNITY_SOURCES = {"nate_pann", "fmkorea", "bobaedream"}
NEWS_SOURCES = {"naver_news"}

# competitor_history.account_profiles의 priority 값 중 참고할 등급과 정렬 우선순위.
COMPETITOR_PRIORITY_ORDER: Dict[str, int] = {"Very High": 0, "High": 1}


class PlannerDecisionEngine(object):
    """
    AI Planner Decision Engine v1 (Sprint 15-1).

    Runtime Input(`trend_result`/`topic_result`)과 Historical Input(`knowledge_history`/
    `trend_memory_history`/`competitor_history`/`brand_dna_history`/`performance_history`)만
    사용해 콘텐츠 전략을 결정한다. LLM 호출도, 외부 API 호출도, 무작위 값도 없다 -
    모든 판단은 이미 Repository에 존재하는 실제 규칙 기반 클래스의 재사용과, 로컬
    storage에 실제로 누적된 데이터에 대한 단순 집계(정렬/필터/카운트)로만 이뤄진다.

    핵심 설계: `pattern_type`/`hook_type`/`cta_type` 판단은 새로운 휴리스틱을
    발명하지 않고, `PatternEngineModule`이 실제로 사용하는 것과 동일한 클래스
    (`KeywordWeightEngine`, `TopicClassifier`, `TopicCluster`, `ConfidenceScorer`,
    `PatternSelector`, `HookSelector`, `CTASelector`)를 그대로 재사용한다. 이
    클래스들은 전부 `selected_topic`/`trends`(Runtime Input에 이미 존재)만 입력으로
    받는 순수 함수형 클래스라서, Pattern Engine이 나중에 독립적으로 실행될 때와
    동일한 값을 얻는다 - Planner가 다른 답을 만들어내는 것이 아니라, Pattern Engine이
    실행되기 전에 "곧 나올 답을 미리 계산"하는 것에 가깝다.

    여기에 두 가지만 Planner 고유의 판단을 더한다:
    - hook/cta는 Brand DNA 이력이 충분히 쌓여 있으면(관측 5회 이상) pattern 기반
      기본값 대신 실제로 가장 많이 써온 hook/cta를 채택한다(브랜드 일관성 우선).
    - knowledge_priority/competitor_reference는 순수하게 Historical Input의
      실제 저장된 통계를 정렬/필터링한 결과다.

    Runtime Input에 실제 topic 신호(title/keyword)가 전혀 없으면(`selected_topic`이
    없거나 비어 있음) `PatternSelector`/`HookSelector`/`CTASelector`를 호출해도 각
    클래스의 하드코딩된 기본값(예: "number_list"/"saveable_tip")만 그대로 반환될 뿐
    실제 신호에 기반한 판단이 아니므로, 이 경우는 그럴듯해 보이는 값을 만들어내지
    않고 정직하게 `build_undecided_result()`(판단 보류)를 반환한다 - Codex 독립 검수
    지적을 반영해 Sprint 15-1 중 추가된 규칙이다.

    모든 계산은 `decide()`에서 try/except로 감싸여 있어 어떤 예외가 나도
    `build_undecided_result()`(정직한 "판단 실패" 상태)로 안전하게 대체되며,
    절대 호출자에게 예외를 전파하지 않는다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        self.keyword_weight_engine = KeywordWeightEngine(self.config)
        self.topic_classifier = TopicClassifier(self.config)
        self.topic_cluster = TopicCluster(self.config)
        self.confidence_scorer = ConfidenceScorer(self.config)
        self.pattern_selector = PatternSelector(self.config)
        self.hook_selector = HookSelector(self.config)
        self.cta_selector = CTASelector(self.config)

    def decide(self, context: Optional[PlanningContext]) -> Dict[str, Any]:
        try:
            return self._decide(context or PlanningContext())
        except Exception as error:
            print(f"AI Planner Decision Engine Failed, returning safe undecided result: {error}")
            return build_undecided_result(reason=f"planner_decision_exception: {error}")

    def _decide(self, context: PlanningContext) -> Dict[str, Any]:
        selected_topic = self._safe_dict(context.topic_result.get("selected_topic"))

        if not self._has_real_topic_signal(selected_topic):
            # Runtime Input에 실제 topic 신호가 전혀 없다(selected_topic 자체가 없거나
            # title/keyword가 모두 비어 있음) - 이 경우 category/pattern/hook/cta를
            # 계산해도 "실제 신호에 기반한 판단"이 아니라 각 Selector의 하드코딩된
            # 기본값을 그대로 흉내내는 것에 불과하므로, 그럴듯해 보이는 값을 만들어내지
            # 않고 정직하게 "판단 보류" 상태를 반환한다(Codex 검수 지적 반영).
            return build_undecided_result(reason="selected_topic_missing_or_invalid")

        trends = context.trend_result.get("trends")
        trends = trends if isinstance(trends, list) else []

        keywords, keyword_weights = self.keyword_weight_engine.compute_weights(selected_topic, trends)

        classification = self.topic_classifier.classify(keywords, selected_topic)
        category = classification.get("category", "트렌드")
        blocked = bool(classification.get("blocked", False))

        cluster_result = self.topic_cluster.assign_cluster(category, keywords, selected_topic)
        cluster = cluster_result.get("cluster", "general_trend_cluster")

        confidence_result = self.confidence_scorer.score(
            selected_topic=selected_topic,
            keyword_weights=keyword_weights,
            category=category,
            cluster=cluster,
            blocked=blocked,
        )
        confidence_score = self._to_float(confidence_result.get("confidence_score"), default=0.0)

        pattern_result = self.pattern_selector.select(category, cluster, confidence_score)
        pattern_type = pattern_result.get("pattern_type", "resource")

        hook_result = self.hook_selector.select(category, pattern_type)
        cta_result = self.cta_selector.select(category, pattern_type)

        hook_type, hook_note, hook_overridden = self._select_hook_with_history(
            baseline_hook_type=hook_result.get("hook_type", "saveable_tip"),
            brand_dna_history=context.brand_dna_history,
        )
        cta_type, cta_note, cta_overridden = self._select_cta_with_history(
            baseline_cta_type=cta_result.get("cta_type", "save"),
            brand_dna_history=context.brand_dna_history,
        )

        content_type_guess, content_type_reason = self._guess_content_type(category, selected_topic)

        knowledge_priority = self._rank_knowledge_priority(context.knowledge_history)
        competitor_reference = self._select_competitor_reference(context.competitor_history)

        content_strategy = self._build_content_strategy(
            category=category,
            pattern_type=pattern_type,
            hook_type=hook_type,
            cta_type=cta_type,
            content_type_guess=content_type_guess,
        )

        planner_confidence = self._compute_confidence(
            confidence_score=confidence_score,
            brand_dna_override_used=hook_overridden or cta_overridden,
            knowledge_priority=knowledge_priority,
            competitor_reference=competitor_reference,
        )

        fallback_used = bool(blocked) or not bool(keywords)

        reason = " ".join(
            filter(
                None,
                [
                    classification.get("reason", ""),
                    cluster_result.get("reason", ""),
                    confidence_result.get("reason", ""),
                    pattern_result.get("reason", ""),
                    hook_note,
                    cta_note,
                    content_type_reason,
                ],
            )
        )

        return {
            "status": "planner_decided",
            "selected_pattern": pattern_type,
            "selected_hook_strategy": hook_type,
            "selected_cta_strategy": cta_type,
            "selected_image_strategy": content_type_guess,
            "knowledge_priority": knowledge_priority,
            "competitor_reference": competitor_reference,
            "content_strategy": content_strategy,
            "planner_confidence": planner_confidence,
            "planner_reason": reason,
            "planner_version": PLANNER_VERSION,
            "fallback_used": fallback_used,
            "decision_basis": {
                "category": category,
                "cluster": cluster,
                "topic_confidence_score": confidence_score,
                "blocked": blocked,
                "brand_dna_hook_override_used": hook_overridden,
                "brand_dna_cta_override_used": cta_overridden,
            },
            "created_at": datetime.now().isoformat(),
        }

    def _select_hook_with_history(
        self,
        baseline_hook_type: str,
        brand_dna_history: Any,
    ) -> Tuple[str, str, bool]:
        brand_dna_history = self._safe_dict(brand_dna_history)
        dominant_hook_type = str(brand_dna_history.get("dominant_hook_type") or "")
        total_observations = self._to_int(brand_dna_history.get("total_observations"), default=0)

        if (
            dominant_hook_type
            and dominant_hook_type in HookSelector.HOOK_TYPES
            and total_observations >= MIN_BRAND_DNA_OBSERVATIONS_FOR_OVERRIDE
        ):
            note = (
                f"Brand DNA 이력(실제 관측 {total_observations}회)에서 가장 많이 쓰인 hook_type "
                f"'{dominant_hook_type}'을 pattern 기반 기본값 '{baseline_hook_type}' 대신 채택함."
            )
            return dominant_hook_type, note, True

        note = (
            f"Brand DNA 이력이 부족(관측 {total_observations}회 < "
            f"{MIN_BRAND_DNA_OBSERVATIONS_FOR_OVERRIDE}회)하여 pattern 기반 기본값 hook_type "
            f"'{baseline_hook_type}'을 그대로 사용함."
        )
        return baseline_hook_type, note, False

    def _select_cta_with_history(
        self,
        baseline_cta_type: str,
        brand_dna_history: Any,
    ) -> Tuple[str, str, bool]:
        brand_dna_history = self._safe_dict(brand_dna_history)
        dominant_cta_type = str(brand_dna_history.get("dominant_cta_type") or "")
        total_observations = self._to_int(brand_dna_history.get("total_observations"), default=0)

        if (
            dominant_cta_type
            and dominant_cta_type in CTASelector.CTA_TYPES
            and total_observations >= MIN_BRAND_DNA_OBSERVATIONS_FOR_OVERRIDE
        ):
            note = (
                f"Brand DNA 이력(실제 관측 {total_observations}회)에서 가장 많이 쓰인 cta_type "
                f"'{dominant_cta_type}'을 pattern 기반 기본값 '{baseline_cta_type}' 대신 채택함."
            )
            return dominant_cta_type, note, True

        note = (
            f"Brand DNA 이력이 부족(관측 {total_observations}회 < "
            f"{MIN_BRAND_DNA_OBSERVATIONS_FOR_OVERRIDE}회)하여 pattern 기반 기본값 cta_type "
            f"'{baseline_cta_type}'을 그대로 사용함."
        )
        return baseline_cta_type, note, False

    def _guess_content_type(self, category: str, selected_topic: Dict[str, Any]) -> Tuple[str, str]:
        text = " ".join(
            [
                str(selected_topic.get("keyword", "")),
                str(selected_topic.get("title", "")),
                str(selected_topic.get("angle", "")),
            ]
        ).lower()

        if category == "쇼핑" or self._match(text, "shopping"):
            return "shopping", "category/keyword가 쇼핑 관련으로 판단되어 image content_type 'shopping'을 제안함."

        if self._match(text, "promotion"):
            return "promotion", "프로모션/광고 키워드가 감지되어 image content_type 'promotion'을 제안함."

        if self._match(text, "review"):
            return "review", "후기/리뷰 키워드가 감지되어 image content_type 'review'을 제안함."

        if category == "AI" or self._match(text, "ai_tools"):
            return "ai_tools", "AI 관련 카테고리/키워드가 감지되어 image content_type 'ai_tools'를 제안함."

        if self._match(text, "tutorial"):
            return "tutorial", "튜토리얼 키워드가 감지되어 image content_type 'tutorial'을 제안함."

        source = str(selected_topic.get("source", "")).lower()
        collection_method = str(selected_topic.get("collection_method", "")).lower()

        if source in NEWS_SOURCES and "fallback" not in collection_method:
            return "news", f"선정 주제가 뉴스 소스({source})에서 수집되어 image content_type 'news'를 제안함."

        if source in COMMUNITY_SOURCES:
            return "community", f"선정 주제가 커뮤니티 소스({source})에서 수집되어 image content_type 'community'를 제안함."

        return "education", "명확히 일치하는 content_type이 없어 기본값 'education'을 제안함."

    def _match(self, text: str, rule_key: str) -> bool:
        return any(keyword in text for keyword in CONTENT_TYPE_KEYWORD_RULES.get(rule_key, []))

    def _rank_knowledge_priority(self, knowledge_history: Any) -> List[str]:
        knowledge_history = self._safe_dict(knowledge_history)
        scores = knowledge_history.get("average_overall_score_by_type")

        if not isinstance(scores, dict) or not scores:
            return []

        valid_scores: Dict[str, float] = {}
        for knowledge_type, score in scores.items():
            if isinstance(score, (int, float)) and not isinstance(score, bool):
                valid_scores[str(knowledge_type)] = float(score)

        if not valid_scores:
            return []

        return sorted(valid_scores.keys(), key=lambda knowledge_type: (-valid_scores[knowledge_type], knowledge_type))

    def _select_competitor_reference(self, competitor_history: Any, limit: int = 5) -> List[str]:
        competitor_history = self._safe_dict(competitor_history)
        profiles = competitor_history.get("account_profiles")

        if not isinstance(profiles, list):
            return []

        eligible = [
            profile
            for profile in profiles
            if isinstance(profile, dict)
            and profile.get("priority") in COMPETITOR_PRIORITY_ORDER
            and profile.get("account")
        ]

        eligible.sort(
            key=lambda profile: (
                COMPETITOR_PRIORITY_ORDER[profile["priority"]],
                str(profile.get("account", "")),
            )
        )

        return [str(profile["account"]) for profile in eligible[:limit]]

    def _build_content_strategy(
        self,
        category: str,
        pattern_type: str,
        hook_type: str,
        cta_type: str,
        content_type_guess: str,
    ) -> str:
        return (
            f"category={category or 'unknown'}, pattern={pattern_type}, hook={hook_type}, "
            f"cta={cta_type}, image_content_type={content_type_guess}"
        )

    def _compute_confidence(
        self,
        confidence_score: float,
        brand_dna_override_used: bool,
        knowledge_priority: List[str],
        competitor_reference: List[str],
    ) -> float:
        confidence = float(confidence_score or 0.0)

        if brand_dna_override_used:
            confidence += 0.05
        if knowledge_priority:
            confidence += 0.05
        if competitor_reference:
            confidence += 0.05

        return round(max(0.0, min(1.0, confidence)), 4)

    def _has_real_topic_signal(self, selected_topic: Dict[str, Any]) -> bool:
        return bool(str(selected_topic.get("title", "")).strip()) or bool(
            str(selected_topic.get("keyword", "")).strip()
        )

    def _safe_dict(self, value: Any) -> Dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _to_float(self, value: Any, default: float) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _to_int(self, value: Any, default: int) -> int:
        try:
            if value is None:
                return default
            return int(value)
        except (TypeError, ValueError):
            return default
