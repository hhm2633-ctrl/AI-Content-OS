import re
from typing import Any, Dict, List, Optional, Tuple


class CardNewsTextOptimizer:
    """
    카드뉴스 렌더링 직전에 slide headline/body 텍스트를 규칙 기반으로 다듬는다.

    - headline이 너무 길면 카드뉴스용으로 짧게 정리 (단어 경계에서 자연스럽게 자름)
    - body 문장이 너무 많거나 길면 2~3줄 단위로 정리
    - 빈 문장 제거
    - 슬라이드 내 중복 문장 제거
    - CTA(role="cta") 슬라이드는 더 짧고 명확하게(문장 수를 더 엄격히) 정리

    LLM을 호출하지 않고 정규식/문자열 연산만 사용한다. content_result 원본이나
    입력으로 받은 slides 리스트/딕셔너리를 직접 변형하지 않고, 항상 새 리스트/딕셔너리를
    반환한다. 최적화 자체가 실패해도 예외를 던지지 않고 원본 slides를 그대로 담은
    fallback 결과(fallback_used=True)를 반환한다.
    """

    HEADLINE_MAX_LENGTH = 18
    BODY_LINE_MAX_LENGTH = 24
    BODY_MAX_SENTENCES = 3
    CTA_MAX_SENTENCES = 2

    # 문장 종결 부호(.!?。！？) 뒤 공백 또는 줄바꿈 기준으로 문장을 나눈다.
    SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?。!?])\s+|\n+")

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def optimize(self, slides: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        try:
            return self._optimize(slides or [])
        except Exception as error:
            return {
                "slides": list(slides or []),
                "text_optimized": False,
                "headline_trimmed_count": 0,
                "body_trimmed_count": 0,
                "duplicate_removed_count": 0,
                "cta_optimized": False,
                "readability_warnings": [f"Text Optimizer 실패: {error}"],
                "fallback_used": True,
            }

    def _optimize(self, slides: List[Dict[str, Any]]) -> Dict[str, Any]:
        optimized_slides: List[Dict[str, Any]] = []

        headline_trimmed_count = 0
        body_trimmed_count = 0
        duplicate_removed_count = 0
        cta_optimized = False
        warnings: List[str] = []

        for slide in slides:
            if not isinstance(slide, dict):
                optimized_slides.append(slide)
                continue

            new_slide = dict(slide)
            page = slide.get("page", "?")
            role = str(slide.get("role", ""))
            is_cta = role == "cta"

            headline = str(slide.get("headline", ""))
            optimized_headline, headline_trimmed = self._optimize_headline(headline)

            if headline_trimmed:
                headline_trimmed_count += 1
                warnings.append(
                    f"{page}장 headline이 {self.HEADLINE_MAX_LENGTH}자를 초과해 정리함."
                )

            body = str(slide.get("body", ""))
            max_sentences = self.CTA_MAX_SENTENCES if is_cta else self.BODY_MAX_SENTENCES

            optimized_body, body_stats = self._optimize_body(body, max_sentences)

            if body_stats["trimmed"]:
                body_trimmed_count += 1
                warnings.append(f"{page}장 body 문장이 길거나 많아 정리함.")

            if body_stats["duplicates_removed"]:
                duplicate_removed_count += body_stats["duplicates_removed"]
                warnings.append(
                    f"{page}장 body에서 중복 문장 {body_stats['duplicates_removed']}건 제거함."
                )

            if body_stats["empty_removed"]:
                warnings.append(
                    f"{page}장 body에서 빈 문장 {body_stats['empty_removed']}건 제거함."
                )

            if is_cta:
                cta_optimized = True

                if body_stats["original_sentence_count"] > self.CTA_MAX_SENTENCES:
                    warnings.append(
                        f"{page}장 CTA 문장이 {self.CTA_MAX_SENTENCES}개를 초과해 더 짧게 정리함."
                    )

            new_slide["headline"] = optimized_headline
            new_slide["body"] = optimized_body
            optimized_slides.append(new_slide)

        return {
            "slides": optimized_slides,
            "text_optimized": True,
            "headline_trimmed_count": headline_trimmed_count,
            "body_trimmed_count": body_trimmed_count,
            "duplicate_removed_count": duplicate_removed_count,
            "cta_optimized": cta_optimized,
            "readability_warnings": warnings,
            "fallback_used": False,
        }

    def _optimize_headline(self, headline: str) -> Tuple[str, bool]:
        headline = headline.strip()

        if len(headline) <= self.HEADLINE_MAX_LENGTH:
            return headline, False

        return self._trim_naturally(headline, self.HEADLINE_MAX_LENGTH), True

    def _trim_naturally(self, text: str, max_length: int) -> str:
        text = text.strip()

        if len(text) <= max_length:
            return text

        truncated = text[:max_length]
        last_space = truncated.rfind(" ")

        # 단어 경계에서 자르되, 너무 많이 잘려나가지 않도록(최소 60% 이상 유지) 보정한다.
        if last_space >= int(max_length * 0.6):
            truncated = truncated[:last_space]

        return truncated.strip()

    def _optimize_body(self, body: str, max_sentences: int) -> Tuple[str, Dict[str, Any]]:
        body = body.strip()

        if not body:
            return "", {
                "trimmed": False,
                "duplicates_removed": 0,
                "empty_removed": 0,
                "original_sentence_count": 0,
            }

        raw_parts = self.SENTENCE_SPLIT_PATTERN.split(body)
        empty_removed = sum(1 for part in raw_parts if not part or not part.strip())
        sentences = [part.strip() for part in raw_parts if part and part.strip()]
        original_sentence_count = len(sentences)

        deduped_sentences: List[str] = []
        seen = set()
        duplicates_removed = 0

        for sentence in sentences:
            normalized = re.sub(r"\s+", "", sentence).lower()

            if normalized in seen:
                duplicates_removed += 1
                continue

            seen.add(normalized)
            deduped_sentences.append(sentence)

        trimmed = False

        if len(deduped_sentences) > max_sentences:
            deduped_sentences = deduped_sentences[:max_sentences]
            trimmed = True

        optimized_body = " ".join(deduped_sentences).strip()

        # 문장 경계가 거의 없는 긴 텍스트(마침표 없는 한 덩어리 등)에 대비해,
        # 줄 수 기준 전체 예산(=BODY_LINE_MAX_LENGTH * max_sentences) 안에서만
        # 자연스럽게 자른다. 단순히 한 줄 길이로 잘라 정보를 과도하게 버리지 않는다.
        total_budget = self.BODY_LINE_MAX_LENGTH * max_sentences

        if len(optimized_body) > total_budget:
            optimized_body = self._trim_naturally(optimized_body, total_budget)
            trimmed = True

        if not optimized_body:
            optimized_body = body

        return optimized_body, {
            "trimmed": trimmed,
            "duplicates_removed": duplicates_removed,
            "empty_removed": empty_removed,
            "original_sentence_count": original_sentence_count,
        }
