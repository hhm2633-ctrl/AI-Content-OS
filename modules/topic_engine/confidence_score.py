from typing import Any, Dict


class ConfidenceScorer:
    """
    selected_topic의 quality_score, fallback 여부, 분류 결과를 종합해
    0.0~1.0 사이의 confidence_score를 계산한다. 계산에 실패하면
    안전하게 0.0을 반환한다.
    """

    def __init__(self, config=None):
        self.config = config or {}

    def score(
        self,
        selected_topic: Dict[str, Any],
        keyword_weights: Dict[str, float],
        category: str,
        cluster: str,
        blocked: bool = False,
    ) -> Dict[str, Any]:
        try:
            return self._score(
                selected_topic or {},
                keyword_weights or {},
                str(category or ""),
                str(cluster or ""),
                bool(blocked),
            )
        except Exception:
            return {
                "confidence_score": 0.0,
                "reason": "confidence_score 계산 실패로 0.0으로 대체함.",
            }

    def _score(
        self,
        selected_topic: Dict[str, Any],
        keyword_weights: Dict[str, float],
        category: str,
        cluster: str,
        blocked: bool,
    ) -> Dict[str, Any]:
        reasons = []

        quality_score = selected_topic.get("quality_score")

        if isinstance(quality_score, (int, float)):
            base = float(quality_score) / 100.0
            reasons.append(f"quality_score 기반 base={round(base, 2)}")
        else:
            base = 0.5
            reasons.append("quality_score 없음으로 base=0.5 사용")

        if selected_topic.get("is_fallback"):
            base -= 0.15
            reasons.append("is_fallback로 감점")

        collection_method = str(selected_topic.get("collection_method", ""))

        if collection_method == "placeholder_fallback":
            base -= 0.2
            reasons.append("placeholder_fallback로 추가 감점")
        elif collection_method.endswith("_cache"):
            base -= 0.05
            reasons.append("cache 기반으로 소폭 감점")

        if not keyword_weights:
            base -= 0.1
            reasons.append("keyword_weights 없음으로 감점")

        if category == "트렌드":
            base -= 0.05
            reasons.append("기본 카테고리라 소폭 감점")

        if blocked:
            base = min(base, 0.1)
            reasons.append("차단 카테고리 감지로 confidence 상한 제한")

        confidence_score = round(max(0.0, min(1.0, base)), 4)

        return {
            "confidence_score": confidence_score,
            "reason": "; ".join(reasons) + ".",
        }
