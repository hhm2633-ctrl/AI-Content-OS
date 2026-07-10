import re
from typing import Any, Callable, Dict, List, Optional, Tuple


class ContentOutputNormalizer(object):
    """
    Content Output Contract - Normalization.

    `ContentOutputValidator`가 어떤 문제를 발견했는지와 무관하게, 항상 4장 구조 /
    hook-first-cta-last role 순서 / headline·body 길이 제한 / caption·hashtags 타입을
    보장하는 안정적인 content_result 스키마를 만든다.

    핵심 원칙: LLM이 실제로 만든 문구는 최대한 보존한다. role이 잘못 붙어 있거나
    순서가 뒤섞여 있어도(예: hook이 3번째 슬라이드에 있음) 내용 자체를 버리지 않고
    올바른 위치로 재배치한다 - 완전히 못 쓸 슬라이드만 fallback 문구로 채운다.

    이 클래스 자체는 예외를 던지지 않는다: 정규화 도중 예외가 발생하면 항상
    완전한 fallback 콘텐츠(`fallback_used: true`)로 대체한다.
    """

    CANONICAL_ROLE_ORDER = ["hook", "problem", "solution", "cta"]

    MIN_HEADLINE_LENGTH = 2
    MAX_HEADLINE_LENGTH = 40
    MIN_BODY_LENGTH = 4
    MAX_BODY_LENGTH = 160

    MIN_HASHTAG_COUNT = 3
    FALLBACK_HASHTAGS = ["#AI콘텐츠", "#콘텐츠자동화", "#카드뉴스", "#부업준비"]

    def normalize(
        self,
        parsed_result: Any,
        keyword: str,
        fallback_slides_fn: Callable[[str], List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        try:
            return self._normalize(parsed_result, keyword, fallback_slides_fn)
        except Exception as error:
            print(f"Content Output Normalizer Failed, using full fallback: {error}")
            return self._build_full_fallback(keyword, fallback_slides_fn, reason=f"normalizer_exception: {error}")

    def _normalize(
        self,
        parsed_result: Any,
        keyword: str,
        fallback_slides_fn: Callable[[str], List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        notes: List[str] = []
        parsed_result = parsed_result if isinstance(parsed_result, dict) else {}
        fallback_slides = fallback_slides_fn(keyword)

        if not isinstance(parsed_result.get("slides"), list):
            notes.append("slides was not a list; rebuilt from fallback")
            raw_slides: List[Any] = []
        else:
            raw_slides = parsed_result["slides"]

        candidates_by_role: Dict[str, Dict[str, str]] = {}
        unmatched: List[Dict[str, str]] = []

        for item in raw_slides:
            if not isinstance(item, dict):
                continue

            role = str(item.get("role", "")).strip().lower()
            headline = str(item.get("headline", "")).strip()
            body = str(item.get("body", "")).strip()

            if not headline and not body:
                continue

            if role in self.CANONICAL_ROLE_ORDER and role not in candidates_by_role:
                candidates_by_role[role] = {"headline": headline, "body": body}
            else:
                unmatched.append({"headline": headline, "body": body})

        normalized_slides = []
        real_content_used_count = 0

        for index, role in enumerate(self.CANONICAL_ROLE_ORDER):
            fallback_slide = fallback_slides[index]
            source: Optional[Dict[str, str]] = None
            has_candidate = False

            if role in candidates_by_role:
                source = candidates_by_role[role]
                has_candidate = True
            elif unmatched:
                source = unmatched.pop(0)
                has_candidate = True
                notes.append(f"page {index + 1} ({role}) filled from a mistagged/unlabeled slide")
            else:
                source = {"headline": fallback_slide["headline"], "body": fallback_slide["body"]}
                notes.append(f"page {index + 1} ({role}) had no usable content; used fallback")

            headline, headline_is_real = self._clean_text(
                source.get("headline") if has_candidate else None, fallback_slide["headline"],
                self.MIN_HEADLINE_LENGTH, self.MAX_HEADLINE_LENGTH,
                notes, index + 1, "headline",
            )
            body, body_is_real = self._clean_text(
                source.get("body") if has_candidate else None, fallback_slide["body"],
                self.MIN_BODY_LENGTH, self.MAX_BODY_LENGTH,
                notes, index + 1, "body",
            )

            # 후보가 있었더라도 headline/body 둘 다 너무 짧아 결국 fallback으로
            # 대체됐다면 이 슬라이드는 실질적으로 "실제 콘텐츠 사용"이 아니다
            # (Codex 독립 검수에서 발견: 후보 존재 여부만으로 카운트하면
            # 부실한 텍스트도 real_content로 잘못 집계될 수 있었음).
            if has_candidate and (headline_is_real or body_is_real):
                real_content_used_count += 1

            normalized_slides.append({
                "page": index + 1,
                "role": role,
                "headline": headline,
                "body": body,
            })

        title = parsed_result.get("title")
        if not isinstance(title, str) or not title.strip():
            title = f"{keyword} 카드뉴스"
            notes.append("title missing/invalid; used fallback title")

        caption = parsed_result.get("caption")
        if not isinstance(caption, str) or not caption.strip():
            caption = f"{keyword}는 작게 시작해서 자동화 구조로 키우는 것이 중요합니다."
            notes.append("caption missing/invalid; used fallback caption")

        hashtags = parsed_result.get("hashtags")
        if isinstance(hashtags, str):
            notes.append("hashtags was a string; split into a list")
            hashtags = [token for token in re.split(r"[,\s]+", hashtags) if token]
        elif not isinstance(hashtags, list):
            notes.append("hashtags was not a list; rebuilt")
            hashtags = []

        clean_hashtags = [str(tag).strip() for tag in hashtags if isinstance(tag, str) and str(tag).strip()]

        if len(clean_hashtags) < self.MIN_HASHTAG_COUNT:
            notes.append("hashtags too few/invalid; padded with fallback hashtags")
            for tag in self.FALLBACK_HASHTAGS:
                if tag not in clean_hashtags:
                    clean_hashtags.append(tag)
                if len(clean_hashtags) >= self.MIN_HASHTAG_COUNT + 1:
                    break

        no_real_content = real_content_used_count == 0
        if no_real_content:
            notes.append("no usable slide content came from the LLM result at all")

        return {
            "title": title,
            "slides": normalized_slides,
            "caption": caption,
            "hashtags": clean_hashtags,
            "status": "content_created",
            "fallback_used": no_real_content,
            "fallback_reason": "no_usable_llm_slide_content" if no_real_content else "",
            "output_normalization": {
                "normalization_applied": bool(notes),
                "notes": notes,
            },
        }

    def _clean_text(
        self,
        value: Optional[str],
        fallback_value: str,
        min_len: int,
        max_len: int,
        notes: List[str],
        page: int,
        field_name: str,
    ) -> Tuple[str, bool]:
        """
        Returns (text, is_real): `is_real` is False exactly when `value` was
        missing/too-short and had to be replaced by `fallback_value` - i.e. when
        none of the caller's real candidate text actually survived. Trimming for
        being too long still counts as real (it's genuine content, just cut).
        """
        text = str(value or "").strip()
        is_real = True

        if not text or len(text) < min_len:
            notes.append(f"page {page} {field_name} missing/too short; used fallback")
            text = fallback_value
            is_real = False

        if len(text) > max_len:
            notes.append(f"page {page} {field_name} too long; trimmed to {max_len} chars")
            text = text[: max_len - 1].rstrip() + "…"

        return text, is_real

    def _build_full_fallback(
        self,
        keyword: str,
        fallback_slides_fn: Callable[[str], List[Dict[str, Any]]],
        reason: str,
    ) -> Dict[str, Any]:
        fallback_slides = fallback_slides_fn(keyword)

        return {
            "title": f"{keyword} 지금 시작해야 하는 이유",
            "slides": [
                {
                    "page": index + 1,
                    "role": slide["role"],
                    "headline": slide["headline"],
                    "body": slide["body"],
                }
                for index, slide in enumerate(fallback_slides)
            ],
            "caption": (
                f"{keyword}는 처음부터 완벽하게 만들기보다, 작은 구조부터 자동화하는 것이 "
                "중요합니다. 저장해두고 하나씩 따라가세요."
            ),
            "hashtags": ["#AI콘텐츠", "#콘텐츠자동화", "#카드뉴스", "#부업준비", "#인스타콘텐츠"],
            "status": "content_created",
            "fallback_used": True,
            "fallback_reason": reason,
            "output_normalization": {
                "normalization_applied": True,
                "notes": [f"normalizer failed internally ({reason}); used full fallback content"],
            },
        }
