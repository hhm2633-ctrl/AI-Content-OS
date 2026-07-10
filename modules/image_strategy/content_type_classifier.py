from typing import Any, Dict, Optional


class ContentTypeClassifier:
    """
    Image Strategy v1 - Content Type Classifier.

    research_result(keyword/topic_intelligence/source/pattern_plan)와
    content_result(title/caption)를 바탕으로 콘텐츠를
    news/community/shopping/review/promotion/tutorial/ai_tools/education 중
    하나로 분류한다. 계산 실패 시 예외를 던지지 않고 안전한 기본값
    "education"을 반환한다 (fallback-first 계약 유지).
    """

    COMMUNITY_SOURCES = {"nate_pann", "fmkorea", "bobaedream"}
    NEWS_SOURCES = {"naver_news"}

    KEYWORD_RULES = {
        "shopping": ["쇼핑", "스마트스토어", "쿠팡", "할인", "구매", "특가", "최저가", "상품 추천"],
        "review": ["후기", "리뷰", "사용해보니", "써본", "직접 써", "경험담"],
        "promotion": ["광고", "프로모션", "이벤트", "공동구매", "할인코드", "협찬"],
        "ai_tools": [
            "chatgpt", "gpt", "claude", "codex", "gemini", "미드저니",
            "ai 툴", "ai툴", "프롬프트",
        ],
        "tutorial": ["하는 법", "만드는 법", "세팅", "따라하기", "튜토리얼", "가이드"],
    }

    def classify(
        self,
        research_result: Optional[Dict[str, Any]],
        content_result: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        try:
            return self._classify(research_result or {}, content_result or {})
        except Exception as error:
            return {
                "content_type": "education",
                "reason": f"콘텐츠 타입 분류 실패로 기본값 'education'을 사용함: {error}",
                "fallback_used": True,
            }

    def _classify(
        self,
        research_result: Dict[str, Any],
        content_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        search_text = self._build_search_text(research_result, content_result)

        pattern_plan = research_result.get("pattern_plan")
        if not isinstance(pattern_plan, dict):
            pattern_plan = {}
        pattern_type = str(pattern_plan.get("pattern_type", "")).lower()

        topic_intelligence = research_result.get("topic_intelligence")
        if not isinstance(topic_intelligence, dict):
            topic_intelligence = {}
        category = str(topic_intelligence.get("category", ""))

        source = str(research_result.get("source", "")).lower()
        collection_method = str(research_result.get("collection_method", "")).lower()

        if category == "쇼핑" or self._match(search_text, "shopping"):
            return self._result("shopping", "카테고리/키워드가 쇼핑 관련으로 판단됨.")

        if self._match(search_text, "promotion"):
            return self._result("promotion", "프로모션/광고 관련 키워드가 감지됨.")

        if self._match(search_text, "review"):
            return self._result("review", "후기/리뷰 관련 키워드가 감지됨.")

        if self._match(search_text, "ai_tools") or (
            category == "AI" and pattern_type in {"resource", "comparison"}
        ):
            return self._result("ai_tools", "AI 툴 관련 키워드/카테고리가 감지됨.")

        if pattern_type == "tutorial" or self._match(search_text, "tutorial"):
            return self._result("tutorial", "튜토리얼형 패턴/키워드가 감지됨.")

        if source in self.NEWS_SOURCES and "fallback" not in collection_method:
            return self._result("news", "선정 주제가 네이버 뉴스에서 수집됨.")

        if source in self.COMMUNITY_SOURCES:
            return self._result("community", f"선정 주제가 커뮤니티 소스({source})에서 수집됨.")

        return self._result(
            "education",
            "명확히 일치하는 콘텐츠 타입이 없어 기본값 'education'으로 분류함.",
        )

    def _match(self, text: str, rule_key: str) -> bool:
        return any(keyword in text for keyword in self.KEYWORD_RULES.get(rule_key, []))

    def _build_search_text(
        self,
        research_result: Dict[str, Any],
        content_result: Dict[str, Any],
    ) -> str:
        parts = [
            str(research_result.get("keyword", "")),
            str(research_result.get("title", "")),
            str(research_result.get("topic_angle", "")),
            str(content_result.get("title", "")),
            str(content_result.get("caption", "")),
        ]
        return " ".join(parts).lower()

    def _result(self, content_type: str, reason: str) -> Dict[str, Any]:
        return {
            "content_type": content_type,
            "reason": reason,
            "fallback_used": False,
        }
