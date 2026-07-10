from typing import Any, Dict, List, Optional


class KnowledgeScorer(object):
    """
    Knowledge Engine - Score.

    Knowledge 항목별로 Reusability(재사용성), Importance(중요도), Confidence(신뢰도),
    Duplicate Risk(중복 위험), ROI를 계산해 item["score"]에 담는다.

    필요한 컨텍스트(topic 신뢰도/content 품질 점수 등)가 없거나 계산 중 예외가
    발생해도 안전한 기본 점수를 채워 반환한다 (workflow를 절대 깨지 않음).
    """

    REUSABILITY_BY_TYPE = {
        "hook": 0.9,
        "cta": 0.9,
        "pattern": 0.85,
        "layout": 0.85,
        "prompt_pattern": 0.8,
        "image_strategy": 0.75,
        "tool": 0.7,
        "brand": 0.6,
        "funnel": 0.55,
        "workflow": 0.5,
    }

    DUPLICATE_RISK_VALUE = {
        "low": 0.0,
        "medium": 0.5,
        "high": 1.0,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def score(
        self,
        items: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        context = context if isinstance(context, dict) else {}
        pattern_result = context.get("pattern_result") or {}
        content_result = context.get("content_result") or {}

        topic_confidence = (pattern_result.get("topic_intelligence") or {}).get("confidence_score", 0.0)
        content_quality = (content_result.get("content_intelligence") or {}).get("quality_score", 0.0)

        scored = []

        for item in items or []:
            try:
                scored.append(self._score_item(item, topic_confidence, content_quality))
            except Exception as error:
                print(f"Knowledge Score Failed: {error}")
                safe_item = dict(item) if isinstance(item, dict) else {}
                safe_item["score"] = self._default_score()
                scored.append(safe_item)

        return scored

    def _score_item(
        self,
        item: Dict[str, Any],
        topic_confidence: Any,
        content_quality: Any,
    ) -> Dict[str, Any]:
        item = dict(item)

        knowledge_type = str(item.get("type", ""))
        reusability = self.REUSABILITY_BY_TYPE.get(knowledge_type, 0.5)

        fallback_used = bool(item.get("fallback_used", False))
        importance = 0.4 if fallback_used else 0.8

        try:
            confidence = max(float(topic_confidence or 0.0), float(content_quality or 0.0))
        except Exception:
            confidence = 0.0

        confidence = min(max(confidence, 0.0), 1.0)
        if confidence == 0.0:
            confidence = 0.5

        duplicate_risk_label = str(item.get("duplicate_risk", "low"))
        duplicate_risk_value = self.DUPLICATE_RISK_VALUE.get(duplicate_risk_label, 0.0)

        roi = round(
            (reusability * 0.4) + (importance * 0.3) + (confidence * 0.2) - (duplicate_risk_value * 0.3),
            4,
        )
        roi = max(0.0, min(1.0, roi))

        overall_score = round(
            (reusability * 0.3)
            + (importance * 0.25)
            + (confidence * 0.25)
            + ((1 - duplicate_risk_value) * 0.2),
            4,
        )

        item["score"] = {
            "reusability": round(reusability, 4),
            "importance": round(importance, 4),
            "confidence": round(confidence, 4),
            "duplicate_risk_score": round(duplicate_risk_value, 4),
            "roi": roi,
            "overall_score": overall_score,
        }

        return item

    def _default_score(self) -> Dict[str, Any]:
        return {
            "reusability": 0.5,
            "importance": 0.4,
            "confidence": 0.5,
            "duplicate_risk_score": 0.0,
            "roi": 0.4,
            "overall_score": 0.4,
        }
