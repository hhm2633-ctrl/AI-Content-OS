from typing import Any, Dict, List, Optional


class LearningSelector(object):
    """
    Learning Engine - 고성과 후보 선택 (Sprint 13: internal_learning_score).

    실제 SNS 성과 데이터(조회수/저장수 등)는 없으므로 가짜 성과를 만들지 않는다.
    대신 이미 로컬에서 실제로 계산된 3개 내부 품질 신호를 합쳐
    `internal_learning_score`를 만든다:
    - audit_score (Content Audit Engine, 9개 검사 종합)
    - performance_score (Performance Score Engine, hook/cta/layout/brand/image 종합)
    - knowledge_score (이번 실행에서 Knowledge Engine이 추출한 top_knowledge의
      overall_score 평균 - Knowledge DB를 실제로 읽어 반영)

    internal_learning_score가 기준(0.65) 이상인 "좋은 실행"에서 나온 Hook/CTA/
    Pattern/Layout/Brand Knowledge만 학습(승격) 후보로 선택한다.
    """

    LEARNABLE_TYPES = {"hook", "cta", "pattern", "layout", "brand"}
    LEARNING_THRESHOLD = 0.65
    KNOWLEDGE_SCORE_THRESHOLD = 0.7

    AUDIT_WEIGHT = 0.4
    PERFORMANCE_WEIGHT = 0.35
    KNOWLEDGE_WEIGHT = 0.25

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def select(
        self,
        top_knowledge: List[Dict[str, Any]],
        performance_score_result: Dict[str, Any],
        audit_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            return self._select(top_knowledge or [], performance_score_result or {}, audit_result or {})
        except Exception as error:
            return {
                "internal_learning_score": 0.0,
                "audit_score": 0.0,
                "performance_score": 0.0,
                "knowledge_score": 0.0,
                "is_good_run": False,
                "candidates": [],
                "knowledge_used": False,
                "reason": f"learning_selector 실패: {error}",
            }

    def _select(
        self,
        top_knowledge: List[Dict[str, Any]],
        performance_score_result: Dict[str, Any],
        audit_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        performance_score = float(performance_score_result.get("overall_performance_score", 0.5))
        audit_score = float(audit_result.get("audit_score", 0.5))
        knowledge_score = self._compute_knowledge_score(top_knowledge)

        internal_learning_score = round(
            (audit_score * self.AUDIT_WEIGHT)
            + (performance_score * self.PERFORMANCE_WEIGHT)
            + (knowledge_score * self.KNOWLEDGE_WEIGHT),
            4,
        )
        is_good_run = internal_learning_score >= self.LEARNING_THRESHOLD

        candidates = []

        if is_good_run:
            for item in top_knowledge:
                if item.get("type") not in self.LEARNABLE_TYPES:
                    continue

                if float(item.get("overall_score", 0.0)) < self.KNOWLEDGE_SCORE_THRESHOLD:
                    continue

                candidates.append(item)

        return {
            "internal_learning_score": internal_learning_score,
            "audit_score": round(audit_score, 4),
            "performance_score": round(performance_score, 4),
            "knowledge_score": round(knowledge_score, 4),
            "is_good_run": is_good_run,
            "candidates": candidates,
            "knowledge_used": bool(top_knowledge),
            "reason": (
                f"internal_learning_score={internal_learning_score} "
                f"(audit={round(audit_score, 4)}*{self.AUDIT_WEIGHT} + "
                f"performance={round(performance_score, 4)}*{self.PERFORMANCE_WEIGHT} + "
                f"knowledge={round(knowledge_score, 4)}*{self.KNOWLEDGE_WEIGHT}) "
                f"({'good run' if is_good_run else 'below threshold'}), "
                f"{len(candidates)}건 학습 후보 선정."
            ),
        }

    def _compute_knowledge_score(self, top_knowledge: List[Dict[str, Any]]) -> float:
        scores = [
            float(item.get("overall_score", 0.0))
            for item in top_knowledge
            if isinstance(item.get("overall_score"), (int, float))
        ]

        if not scores:
            return 0.5

        return sum(scores) / len(scores)
