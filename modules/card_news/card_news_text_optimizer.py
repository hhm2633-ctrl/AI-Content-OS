import re
from typing import Any, Dict, List, Optional, Tuple


class CardNewsTextOptimizer:
    """
    Slide Balance Engine v2 (CardNews Layout Intelligence Sprint 2).

    카드뉴스 렌더링 직전에 slide headline/body 텍스트를 규칙 기반으로 다듬는다.

    - headline이 너무 길면 카드뉴스용으로 짧게 정리 (단어 경계에서 자연스럽게 자름)
    - body 문장이 너무 많거나 길면 2~3줄 단위로 정리
    - 빈 문장 제거
    - 슬라이드 내 중복 문장 제거
    - CTA(role="cta") 슬라이드는 더 짧고 명확하게(문장 수를 더 엄격히) 정리
    - (Sprint 2) headline/body 길이 비율이 TITLE_BODY_RATIO_MIN~MAX 범위를 벗어나면
      body를 비율에 맞게 추가로 정리한다 ("제목/본문 비율 최적화").
    - (Sprint 2) 슬라이드별/전체 readability_score(0.0~1.0)를 계산해 반환한다
      ("가독성 점수 추가").

    LLM을 호출하지 않고 정규식/문자열 연산만 사용한다. content_result 원본이나
    입력으로 받은 slides 리스트/딕셔너리를 직접 변형하지 않고, 항상 새 리스트/딕셔너리를
    반환한다. 최적화 자체가 실패해도 예외를 던지지 않고 원본 slides를 그대로 담은
    fallback 결과(fallback_used=True)를 반환한다.
    """

    HEADLINE_MAX_LENGTH = 18
    HEADLINE_MIN_LENGTH = 4
    BODY_LINE_MAX_LENGTH = 24
    BODY_MAX_SENTENCES = 3
    CTA_MAX_SENTENCES = 2
    # Phase M8 (Production Quality) - Cover Optimization: 첫 장(hook)은 본문
    # 요약이 아니라 "제목 1개 + 보조 문장 최대 1개"여야 한다. CTA와 동일한
    # 기존 role 분기 패턴(is_cta)을 그대로 재사용해 hook에도 문장 수 상한을
    # 둔다 - 새 파이프라인을 만들지 않는다.
    COVER_MAX_SENTENCES = 1

    # body 길이는 headline 길이의 이 배수 범위 안에 있는 것을 이상적으로 본다.
    TITLE_BODY_RATIO_MIN = 1.2
    TITLE_BODY_RATIO_MAX = 6.0

    # 문장 종결 부호(.!?。！？) 뒤 공백 또는 줄바꿈 기준으로 문장을 나눈다.
    # 종결 부호 바로 앞이 숫자면(예: "1." "2." 같은 번호 매긴 목록 표시) 문장
    # 경계로 보지 않는다 - 그렇지 않으면 "1. 내용\n2. 내용"이 "1.", "내용",
    # "2." 처럼 쪼개져 뒤 문장 수 제한(BODY_MAX_SENTENCES)에서 "2."만 남고
    # 실제 내용이 잘려나가는 결함이 있었다(Phase M8 실제 렌더 샘플 검증에서
    # 발견).
    SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[^\d][.!?。!?])\s+|\n+")

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
                "cover_optimized": False,
                "readability_warnings": [f"Text Optimizer 실패: {error}"],
                "fallback_used": True,
                "readability_score": 0.0,
                "slide_readability": [],
                "ratio_adjusted_count": 0,
            }

    def _optimize(self, slides: List[Dict[str, Any]]) -> Dict[str, Any]:
        optimized_slides: List[Dict[str, Any]] = []

        headline_trimmed_count = 0
        body_trimmed_count = 0
        duplicate_removed_count = 0
        ratio_adjusted_count = 0
        cta_optimized = False
        cover_optimized = False
        warnings: List[str] = []
        slide_readability: List[Dict[str, Any]] = []

        for slide in slides:
            if not isinstance(slide, dict):
                optimized_slides.append(slide)
                continue

            new_slide = dict(slide)
            page = slide.get("page", "?")
            role = str(slide.get("role", ""))
            is_cta = role == "cta"
            is_cover = role == "hook"

            headline = str(slide.get("headline", ""))
            optimized_headline, headline_trimmed = self._optimize_headline(headline)

            if headline_trimmed:
                headline_trimmed_count += 1
                warnings.append(
                    f"{page}장 headline이 {self.HEADLINE_MAX_LENGTH}자를 초과해 정리함."
                )

            body = str(slide.get("body", ""))
            if is_cta:
                max_sentences = self.CTA_MAX_SENTENCES
            elif is_cover:
                max_sentences = self.COVER_MAX_SENTENCES
            else:
                max_sentences = self.BODY_MAX_SENTENCES

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

            if is_cover:
                cover_optimized = True

                if body_stats["original_sentence_count"] > self.COVER_MAX_SENTENCES:
                    warnings.append(
                        f"{page}장 Cover 보조 문장이 {self.COVER_MAX_SENTENCES}개를 초과해 더 짧게 정리함."
                    )

            optimized_body, ratio_adjusted, ratio_value = self._balance_title_body_ratio(
                optimized_headline, optimized_body
            )

            if ratio_adjusted:
                ratio_adjusted_count += 1
                warnings.append(
                    f"{page}장 제목/본문 비율({ratio_value})이 범위를 벗어나 body를 추가로 정리함."
                )

            new_slide["headline"] = optimized_headline
            new_slide["body"] = optimized_body
            optimized_slides.append(new_slide)

            slide_readability.append(
                self._score_slide_readability(page, optimized_headline, optimized_body)
            )

        readability_score = (
            round(sum(item["score"] for item in slide_readability) / len(slide_readability), 4)
            if slide_readability
            else 0.0
        )

        return {
            "slides": optimized_slides,
            "text_optimized": True,
            "headline_trimmed_count": headline_trimmed_count,
            "body_trimmed_count": body_trimmed_count,
            "duplicate_removed_count": duplicate_removed_count,
            "cta_optimized": cta_optimized,
            "cover_optimized": cover_optimized,
            "readability_warnings": warnings,
            "fallback_used": False,
            "ratio_adjusted_count": ratio_adjusted_count,
            "readability_score": readability_score,
            "slide_readability": slide_readability,
        }

    def _balance_title_body_ratio(self, headline: str, body: str) -> Tuple[str, bool, float]:
        headline_length = len(headline.strip())
        body_length = len(body.strip())

        if headline_length == 0 or body_length == 0:
            return body, False, 0.0

        ratio = round(body_length / headline_length, 2)

        if ratio <= self.TITLE_BODY_RATIO_MAX:
            return body, False, ratio

        max_body_length = int(headline_length * self.TITLE_BODY_RATIO_MAX)
        adjusted_body = self._trim_naturally(body, max_body_length)

        return adjusted_body, True, ratio

    def _score_slide_readability(self, page: Any, headline: str, body: str) -> Dict[str, Any]:
        headline = headline.strip()
        body = body.strip()

        headline_length = len(headline)
        body_length = len(body)

        headline_ok = self.HEADLINE_MIN_LENGTH <= headline_length <= self.HEADLINE_MAX_LENGTH
        body_ok = 0 < body_length <= self.BODY_LINE_MAX_LENGTH * self.BODY_MAX_SENTENCES

        ratio = round(body_length / headline_length, 2) if headline_length else 0.0
        ratio_ok = headline_length > 0 and body_length > 0 and (
            self.TITLE_BODY_RATIO_MIN <= ratio <= self.TITLE_BODY_RATIO_MAX
        )

        score = 0.0
        score += 0.4 if headline_ok else 0.0
        score += 0.4 if body_ok else 0.0
        score += 0.2 if ratio_ok else 0.0

        return {
            "page": page,
            "headline_ok": headline_ok,
            "body_ok": body_ok,
            "ratio_ok": ratio_ok,
            "ratio": ratio,
            "score": round(score, 4),
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

        content_limit = max(1, max_length - 1)
        truncated = text[:content_limit]
        last_space = truncated.rfind(" ")

        # 단어 경계에서 자르되, 너무 많이 잘려나가지 않도록(최소 60% 이상 유지) 보정한다.
        if last_space >= int(content_limit * 0.6):
            truncated = truncated[:last_space]

        return f"{truncated.strip()}…"

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
            # Phase M8 실제 렌더 샘플 검증에서 발견된 결함 수정: 번호 매긴
            # 목록처럼 문장이 여러 개인 경우, 글자 단위(_trim_naturally)로
            # 바로 자르면 "2." 처럼 항목 번호만 남고 내용이 사라져 의미가
            # 달라진다. 문장이 2개 이상 남아 있으면 뒤쪽 문장부터 통째로
            # 제거해 예산에 맞추고, 문장이 1개만 남았을 때만 최후 수단으로
            # 글자 단위 자연스러운 절단을 쓴다(_fit_lines의 원칙과 동일).
            while len(deduped_sentences) > 1 and len(" ".join(deduped_sentences)) > total_budget:
                deduped_sentences = deduped_sentences[:-1]
                trimmed = True

            optimized_body = " ".join(deduped_sentences).strip()

            if len(optimized_body) > total_budget:
                # 문장 단위 제거로도 예산을 못 맞춘 마지막 한 문장은 글자
                # 단위로 자연스럽게 자른다 - 이때도 잘렸다는 사실 자체를
                # 숨기지 않기 위해 말줄임표(…)를 붙인다(Codex 리뷰 지적 반영,
                # "조용히" 잘리지 않게 하는 최소한의 표시).
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
