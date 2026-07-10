from typing import Any, Dict, Optional


class LearningScorer(object):
    """
    Learning Engine - Score.

    Memory에 이미 있던 항목이 다시 좋은 실행에서 선택되면(reinforcement),
    memory_score를 조금씩 끌어올린다 (반복적으로 검증된 패턴일수록 신뢰도를 높임).
    """

    REINFORCEMENT_STEP = 0.05
    MAX_SCORE = 1.0

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def compute(self, existing_entry: Optional[Dict[str, Any]], knowledge_overall_score: float) -> Dict[str, Any]:
        try:
            return self._compute(existing_entry, knowledge_overall_score)
        except Exception:
            return {"memory_score": knowledge_overall_score, "reinforced_count": 1}

    def _compute(self, existing_entry: Optional[Dict[str, Any]], knowledge_overall_score: float) -> Dict[str, Any]:
        if not existing_entry:
            return {
                "memory_score": round(float(knowledge_overall_score), 4),
                "reinforced_count": 1,
            }

        reinforced_count = int(existing_entry.get("reinforced_count", 1)) + 1
        previous_score = float(existing_entry.get("memory_score", knowledge_overall_score))

        memory_score = min(
            self.MAX_SCORE,
            round(previous_score + self.REINFORCEMENT_STEP, 4),
        )

        return {
            "memory_score": memory_score,
            "reinforced_count": reinforced_count,
        }
