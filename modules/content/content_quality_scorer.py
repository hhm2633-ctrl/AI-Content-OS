from typing import Any, Dict, List, Optional


class ContentQualityScorer:
    """
    생성된 카드뉴스 콘텐츠의 최종 Content Score를 0.0~1.0 사이 점수로 계산한다.

    hook/CTA 존재 여부 + Hook Engine v2/CTA Engine v2의 hook_score/cta_score, 슬라이드
    구조 완성도, selected_topic/pattern_plan 반영 여부(및 Pattern Engine fallback 여부),
    caption/hashtag 충실도, BrandRuleEvaluator의 brand_rule_passed를 가점하고, 빈약한
    문장/중복 문구/fallback 사용을 감점한다.

    prompt_meta(ContentPromptBuilder.build()가 만든 meta, hook_score/cta_score/
    pattern_fallback_used 포함)가 있으면 그 값을 반영해 더 정교하게 점수를 매기고,
    없으면(legacy 프롬프트 경로) 기존 동작과 동일하게 hook/cta 존재 여부만으로
    만점을 준다 — 레거시 경로에 점수 회귀가 생기지 않도록 하기 위함이다. brand_result가
    없으면(호출부가 아직 넘기지 않는 경우) brand_ok를 기본 True로 간주해 만점을 주므로,
    기존 score() 호출부도 시그니처 변경 없이 그대로 동작한다(하위 호환).

    계산에 실패해도 예외를 던지지 않고 0.0을 반환한다.
    """

    MAX_POINTS = 100
    MIN_HEADLINE_LENGTH = 4
    MIN_BODY_LENGTH = 8
    REQUIRED_ROLES = {"hook", "problem", "solution", "cta"}

    # hook/cta 각각의 배점(15점)을 "존재 여부 기본점 + Hook/CTA Score 가중치"로 나눈다.
    # 기존과 총점(15)은 동일하게 유지해 하위 호환을 지킨다.
    HOOK_BASE_POINTS = 5
    HOOK_SCORE_MAX_POINTS = 10
    CTA_BASE_POINTS = 5
    CTA_SCORE_MAX_POINTS = 10

    # Pattern Engine이 fallback을 썼다면 "pattern 반영" 가점(15)을 절반만 인정한다.
    PATTERN_REFLECTED_FULL_POINTS = 15
    PATTERN_REFLECTED_FALLBACK_POINTS = 7

    # caption/hashtags 배점을 10 -> 5로 줄이고, 확보한 10점을 brand_ok 배점으로 돌린다.
    # 총점(100)은 그대로 유지된다: hook(15)+cta(15)+structure(20)+topic(15)+pattern(15)
    # +caption(5)+hashtags(5)+brand(10) = 100.
    CAPTION_OK_POINTS = 5
    HASHTAGS_OK_POINTS = 5
    BRAND_OK_POINTS = 10

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def score(
        self,
        content_result: Optional[Dict[str, Any]],
        research_result: Optional[Dict[str, Any]] = None,
        prompt_meta: Optional[Dict[str, Any]] = None,
        brand_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            return self._score(
                content_result or {},
                research_result or {},
                prompt_meta or {},
                brand_result,
            )
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
        prompt_meta: Dict[str, Any],
        brand_result: Optional[Dict[str, Any]],
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

        # --- Hook (존재 여부 + Hook Engine v1 hook_score) ---
        hook_ok = self._slide_is_substantial(slides_by_role.get("hook"))
        checks["hook_present"] = hook_ok

        hook_score = prompt_meta.get("hook_score")
        has_hook_score = isinstance(hook_score, (int, float))
        checks["hook_score"] = hook_score if has_hook_score else None

        if hook_ok:
            effective_hook_score = float(hook_score) if has_hook_score else 1.0
            hook_points = self.HOOK_BASE_POINTS + round(self.HOOK_SCORE_MAX_POINTS * max(0.0, min(1.0, effective_hook_score)))
            points += hook_points
            if has_hook_score:
                reasons.append(f"hook 슬라이드 확인됨, hook_score={hook_score}(+{hook_points})")
            else:
                reasons.append(f"hook 슬라이드 확인됨(+{hook_points})")

        # --- CTA (존재 여부 + CTA Engine v1 cta_score) ---
        cta_ok = self._slide_is_substantial(slides_by_role.get("cta"))
        checks["cta_present"] = cta_ok

        cta_score = prompt_meta.get("cta_score")
        has_cta_score = isinstance(cta_score, (int, float))
        checks["cta_score"] = cta_score if has_cta_score else None

        if cta_ok:
            effective_cta_score = float(cta_score) if has_cta_score else 1.0
            cta_points = self.CTA_BASE_POINTS + round(self.CTA_SCORE_MAX_POINTS * max(0.0, min(1.0, effective_cta_score)))
            points += cta_points
            if has_cta_score:
                reasons.append(f"cta 슬라이드 확인됨, cta_score={cta_score}(+{cta_points})")
            else:
                reasons.append(f"cta 슬라이드 확인됨(+{cta_points})")

        # --- 슬라이드 구조 완성도 ---
        structure_ok = self.REQUIRED_ROLES.issubset(set(slides_by_role.keys())) and len(slides) >= 4
        checks["structure_complete"] = structure_ok
        if structure_ok:
            points += 20
            reasons.append("4개 슬라이드 구조 완성(+20)")

        # --- Topic 반영 ---
        topic_reflected = self._topic_reflected(content_result, research_result)
        checks["topic_reflected"] = topic_reflected
        if topic_reflected:
            points += 15
            reasons.append("selected_topic 키워드 반영됨(+15)")

        # --- Pattern 반영 (Pattern Engine fallback 여부까지 반영) ---
        pattern_reflected = content_result.get("prompt_source") == "pattern_aware"
        checks["pattern_reflected"] = pattern_reflected

        pattern_fallback_used = bool(prompt_meta.get("pattern_fallback_used", False))
        checks["pattern_fallback_used"] = pattern_fallback_used

        if pattern_reflected:
            if pattern_fallback_used:
                points += self.PATTERN_REFLECTED_FALLBACK_POINTS
                reasons.append(
                    f"pattern_plan 기반 prompt 사용되었으나 Pattern Engine fallback 발생"
                    f"(+{self.PATTERN_REFLECTED_FALLBACK_POINTS})"
                )
            else:
                points += self.PATTERN_REFLECTED_FULL_POINTS
                reasons.append(f"pattern_plan 기반 prompt 정상 반영됨(+{self.PATTERN_REFLECTED_FULL_POINTS})")

        # --- caption / hashtags ---
        caption = str(content_result.get("caption", "")).strip()
        caption_ok = len(caption) >= 15
        checks["caption_ok"] = caption_ok
        if caption_ok:
            points += self.CAPTION_OK_POINTS
            reasons.append(f"caption 충분함(+{self.CAPTION_OK_POINTS})")

        hashtags = content_result.get("hashtags", [])
        hashtags_ok = isinstance(hashtags, list) and len(hashtags) >= 3
        checks["hashtags_ok"] = hashtags_ok
        if hashtags_ok:
            points += self.HASHTAGS_OK_POINTS
            reasons.append(f"hashtags 충분함(+{self.HASHTAGS_OK_POINTS})")

        # --- brand (BrandRuleEvaluator 결과 반영) ---
        # brand_result가 없으면(레거시 호출부) 기본 True로 간주해 만점을 준다.
        if brand_result is None:
            brand_ok = True
            checks["brand_ok"] = None
        else:
            brand_ok = bool(brand_result.get("brand_rule_passed", False))
            checks["brand_ok"] = brand_ok

        if brand_ok:
            points += self.BRAND_OK_POINTS
            reasons.append(f"브랜드 규칙 통과(+{self.BRAND_OK_POINTS})")

        # --- 감점 ---
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
