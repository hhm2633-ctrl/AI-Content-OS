from typing import Any, Dict, List, Optional


class AuditScorer(object):
    """
    Content Audit Engine - Score (Sprint 13 강화).

    hook/cta/pattern/layout/brand/image_strategy/duplicate/save_inducement/
    comment_inducement 9개 검사 결과를 하나의 audit_score로 합산하고, 실패한
    항목에 대한 recommendations을 반드시 생성한다.
    """

    WEIGHTS = {
        "hook_check": 0.16,
        "cta_check": 0.16,
        "pattern_check": 0.12,
        "layout_check": 0.12,
        "brand_check": 0.12,
        "image_strategy_check": 0.1,
        "duplicate_check": 0.12,
        "save_inducement_check": 0.05,
        "comment_inducement_check": 0.05,
    }

    RECOMMENDATION_BY_CHECK = {
        "hook_check": "hook 슬라이드 문구를 더 구체적이고 강하게 다시 작성하세요.",
        "cta_check": "CTA 슬라이드의 행동 유도 문구를 보강하세요.",
        "pattern_check": "Content가 Pattern Engine이 선택한 pattern_type을 실제로 반영하도록 프롬프트를 다시 확인하세요.",
        "layout_check": "레이아웃 fallback이 사용되었습니다. layout_result를 확인하세요.",
        "brand_check": "브랜드 금지 표현 또는 톤 불일치를 수정하세요.",
        "image_strategy_check": "Image Strategy가 권장한 실제 이미지를 아직 소싱하지 못했습니다. manual_image_required 체크리스트를 확인하세요.",
        "duplicate_check": "최근 콘텐츠/주제와 유사도가 높습니다. 주제/문구를 차별화하세요.",
        "save_inducement_check": "CTA에 '저장' 유도 문구를 추가하면 저장 지표에 도움이 될 수 있습니다.",
        "comment_inducement_check": "CTA에 댓글을 유도하는 질문형 문구를 추가하면 참여율에 도움이 될 수 있습니다.",
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def score(self, checks: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        try:
            return self._score(checks or {})
        except Exception as error:
            return {
                "audit_score": 0.0,
                "passed": False,
                "recommendations": [f"audit_score 계산 실패: {error}"],
            }

    def _score(self, checks: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        total = 0.0

        for check_name, weight in self.WEIGHTS.items():
            check_result = checks.get(check_name) or {}
            check_score = float(check_result.get("score", 0.0))
            total += check_score * weight

        audit_score = round(max(0.0, min(1.0, total)), 4)

        recommendations: List[str] = []
        strengths: List[str] = []
        weaknesses: List[str] = []

        for check_name in self.WEIGHTS:
            check_result = checks.get(check_name) or {}

            if check_result.get("passed"):
                strengths.append(check_name)
            else:
                weaknesses.append(check_name)
                recommendations.append(
                    self.RECOMMENDATION_BY_CHECK.get(check_name, f"{check_name} 재검토 필요.")
                )

        if not recommendations:
            recommendations.append("특별한 개선 필요 사항이 없습니다.")

        return {
            "audit_score": audit_score,
            "passed": audit_score >= 0.6,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": recommendations,
        }
