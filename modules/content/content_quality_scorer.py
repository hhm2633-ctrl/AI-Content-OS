from typing import Any, Dict, List, Optional


class ContentQualityScorer:
    """
    생성된 카드뉴스 콘텐츠의 품질을 0.0~1.0 사이 점수로 계산한다.

    hook/CTA 존재 여부, 슬라이드 구조 완성도, selected_topic/pattern_plan 반영 여부,
    caption/hashtag 충실도를 가점하고, 빈약한 문장/중복 문구/fallback 사용을 감점한다.
    계산에 실패해도 예외를 던지지 않고 0.0을 반환한다.
    """

    MAX_POINTS = 100
    MIN_HEADLINE_LENGTH = 4
    MIN_BODY_LENGTH = 8
    REQUIRED_ROLES = {"hook", "problem", "solution", "cta"}

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def score(
        self,
        content_result: Optional[Dict[str, Any]],
        research_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            return self._score(content_result or {}, research_result or {})
        except Exception:
            return {
                "quality_score": 0.0,
                "checks": {},
                "reason": "quality_score 계산 실패로 0.0 처리함.",
            }

    def _score(
        self,
        content_result: Dict[str, Any],
        research_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        points = 0
        reasons: List[str] = []
        checks: Dict[str, Any] = {}

        slides = content_result.get("slides", [])
        if not isinstance(slides, list):
            slides = []

        slides_by_role: Dict[str, Dict[str, Any]] = {}
        for slide in slides:
            if isinstance(slide, dict):
                slides_by_role.setdefault(slide.get("role"), slide)

        hook_ok = self._slide_is_substantial(slides_by_role.get("hook"))
        checks["hook_present"] = hook_ok
        if hook_ok:
            points += 15
            reasons.append("hook 슬라이드 확인됨(+15)")

        cta_ok = self._slide_is_substantial(slides_by_role.get("cta"))
        checks["cta_present"] = cta_ok
        if cta_ok:
            points += 15
            reasons.append("cta 슬라이드 확인됨(+15)")

        structure_ok = self.REQUIRED_ROLES.issubset(set(slides_by_role.keys())) and len(slides) >= 4
        checks["structure_complete"] = structure_ok
        if structure_ok:
            points += 20
            reasons.append("4개 슬라이드 구조 완성(+20)")

        topic_reflected = self._topic_reflected(content_result, research_result)
        checks["topic_reflected"] = topic_reflected
        if topic_reflected:
            points += 15
            reasons.append("selected_topic 키워드 반영됨(+15)")

        pattern_reflected = content_result.get("prompt_source") == "pattern_aware"
        checks["pattern_reflected"] = pattern_reflected
        if pattern_reflected:
            points += 15
            reasons.append("pattern_plan 기반 prompt 사용됨(+15)")

        caption = str(content_result.get("caption", "")).strip()
        caption_ok = len(caption) >= 15
        checks["caption_ok"] = caption_ok
        if caption_ok:
            points += 10
            reasons.append("caption 충분함(+10)")

        hashtags = content_result.get("hashtags", [])
        hashtags_ok = isinstance(hashtags, list) and len(hashtags) >= 3
        checks["hashtags_ok"] = hashtags_ok
        if hashtags_ok:
            points += 10
            reasons.append("hashtags 충분함(+10)")

        thin_slide_count = sum(
            1 for slide in slides if isinstance(slide, dict) and not self._slide_is_substantial(slide)
        )
        checks["thin_slide_count"] = thin_slide_count
        if thin_slide_count:
            penalty = min(20, thin_slide_count * 5)
            points -= penalty
            reasons.append(f"빈약한 슬라이드 {thin_slide_count}개 감점(-{penalty})")

        duplicate_penalty = self._duplicate_slide_penalty(slides)
        checks["duplicate_slide_penalty"] = duplicate_penalty
        if duplicate_penalty:
            points -= duplicate_penalty
            reasons.append(f"슬라이드 문구 중복 감점(-{duplicate_penalty})")

        fallback_used = bool(content_result.get("fallback_used", False))
        checks["fallback_used"] = fallback_used
        if fallback_used:
            points -= 30
            reasons.append("fallback_used=True 감점(-30)")

        points = max(0, min(self.MAX_POINTS, points))
        quality_score = round(points / self.MAX_POINTS, 4)

        return {
            "quality_score": quality_score,
            "checks": checks,
            "reason": ("; ".join(reasons) + ".") if reasons else "평가 항목 없음.",
        }

    def _slide_is_substantial(self, slide: Optional[Dict[str, Any]]) -> bool:
        if not isinstance(slide, dict):
            return False

        headline = str(slide.get("headline", "")).strip()
        body = str(slide.get("body", "")).strip()

        return len(headline) >= self.MIN_HEADLINE_LENGTH and len(body) >= self.MIN_BODY_LENGTH

    def _topic_reflected(self, content_result: Dict[str, Any], research_result: Dict[str, Any]) -> bool:
        keyword = str(research_result.get("keyword") or research_result.get("topic") or "").strip()
        topic_intelligence = research_result.get("topic_intelligence")

        keywords: List[str] = []
        if isinstance(topic_intelligence, dict):
            raw_keywords = topic_intelligence.get("keywords", [])
            if isinstance(raw_keywords, list):
                keywords = [str(item) for item in raw_keywords]

        search_terms = [term for term in [keyword] + keywords if term]

        if not search_terms:
            return False

        haystack = self._collect_text(content_result).lower()

        return any(term.lower() in haystack for term in search_terms)

    def _collect_text(self, content_result: Dict[str, Any]) -> str:
        parts = [str(content_result.get("title", "")), str(content_result.get("caption", ""))]

        slides = content_result.get("slides", [])
        if isinstance(slides, list):
            for slide in slides:
                if isinstance(slide, dict):
                    parts.append(str(slide.get("headline", "")))
                    parts.append(str(slide.get("body", "")))

        return " ".join(parts)

    def _duplicate_slide_penalty(self, slides: List[Dict[str, Any]]) -> int:
        seen = set()
        duplicates = 0

        for slide in slides:
            if not isinstance(slide, dict):
                continue

            signature = (
                str(slide.get("headline", "")).strip().lower(),
                str(slide.get("body", "")).strip().lower(),
            )

            if signature in seen and any(signature):
                duplicates += 1

            seen.add(signature)

        return min(15, duplicates * 7)
