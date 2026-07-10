from typing import Any, Dict, List


class ContentOutputValidator(object):
    """
    Content Output Contract - Validation.

    LLM이 반환(및 json.loads로 파싱)한 content 결과 dict에 어떤 구조적 문제가 있는지
    진단만 한다 (수정은 `ContentOutputNormalizer`가 담당). `ContentModule`은 이 클래스를
    두 번 사용한다: 정규화 전(원본 진단용)과 정규화 후(계약 재확인용, Quality Recheck).

    검사 자체가 실패해도 예외를 던지지 않고 "검증 실패" 이슈만 담은 안전한 결과를
    반환한다 - Validator의 내부 오류가 ContentModule 전체를 죽이면 안 된다.
    """

    EXPECTED_SLIDE_COUNT = 4
    CANONICAL_ROLE_ORDER = ["hook", "problem", "solution", "cta"]

    MIN_HEADLINE_LENGTH = 2
    MAX_HEADLINE_LENGTH = 40
    MIN_BODY_LENGTH = 4
    MAX_BODY_LENGTH = 160

    def validate(self, parsed_result: Any) -> Dict[str, Any]:
        try:
            return self._validate(parsed_result)
        except Exception as error:
            return {
                "valid": False,
                "issues": [f"validator_exception: {error}"],
                "slide_issues": {},
            }

    def _validate(self, parsed_result: Any) -> Dict[str, Any]:
        if not isinstance(parsed_result, dict):
            return {"valid": False, "issues": ["result_not_dict"], "slide_issues": {}}

        issues: List[str] = []
        slide_issues: Dict[str, List[str]] = {}

        slides = parsed_result.get("slides")

        if not isinstance(slides, list):
            issues.append("slides_not_list")
            slides = []
        elif len(slides) != self.EXPECTED_SLIDE_COUNT:
            issues.append(f"slide_count_mismatch:{len(slides)}")

        seen_pages = set()
        roles_in_order: List[str] = []

        for index, slide in enumerate(slides):
            per_slide_issues: List[str] = []

            if not isinstance(slide, dict):
                per_slide_issues.append("slide_not_dict")
                slide_issues[str(index)] = per_slide_issues
                roles_in_order.append("")
                continue

            page = slide.get("page")
            if not isinstance(page, int) or isinstance(page, bool):
                per_slide_issues.append("page_missing_or_invalid")
            else:
                if page in seen_pages:
                    per_slide_issues.append("page_duplicate")
                else:
                    seen_pages.add(page)

                if page != index + 1:
                    per_slide_issues.append("page_out_of_order")

            role = str(slide.get("role", "")).strip().lower()
            roles_in_order.append(role)

            if role not in self.CANONICAL_ROLE_ORDER:
                per_slide_issues.append("role_unrecognized")

            headline = str(slide.get("headline", "")).strip()
            body = str(slide.get("body", "")).strip()

            if not headline:
                per_slide_issues.append("headline_missing")
            elif len(headline) > self.MAX_HEADLINE_LENGTH:
                per_slide_issues.append("headline_too_long")
            elif len(headline) < self.MIN_HEADLINE_LENGTH:
                per_slide_issues.append("headline_too_short")

            if not body:
                per_slide_issues.append("body_missing")
            elif len(body) > self.MAX_BODY_LENGTH:
                per_slide_issues.append("body_too_long")
            elif len(body) < self.MIN_BODY_LENGTH:
                per_slide_issues.append("body_too_short")

            if per_slide_issues:
                slide_issues[str(index)] = per_slide_issues

        if roles_in_order:
            if roles_in_order[0] != "hook":
                issues.append("hook_not_first")

            if roles_in_order[-1] != "cta":
                issues.append("cta_not_last")

            if (
                len(roles_in_order) == self.EXPECTED_SLIDE_COUNT
                and roles_in_order != self.CANONICAL_ROLE_ORDER
                and "hook_not_first" not in issues
                and "cta_not_last" not in issues
            ):
                issues.append("role_order_mismatch")

        title = parsed_result.get("title")
        if not isinstance(title, str) or not title.strip():
            issues.append("title_invalid")

        caption = parsed_result.get("caption")
        if not isinstance(caption, str) or not caption.strip():
            issues.append("caption_invalid")

        hashtags = parsed_result.get("hashtags")
        if (
            not isinstance(hashtags, list)
            or not hashtags
            or not all(isinstance(tag, str) and tag.strip() for tag in hashtags)
        ):
            issues.append("hashtags_invalid")

        valid = not issues and not slide_issues

        return {
            "valid": valid,
            "issues": issues,
            "slide_issues": slide_issues,
        }
