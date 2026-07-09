import json
from pathlib import Path
from typing import Any, Dict, List


class TopicClassifier:
    """
    키워드/selected_topic을 config/topic_engine.json 기준 카테고리로 분류한다.
    config 파일이 없거나 손상되어도 하드코딩된 기본값으로 동작한다.
    """

    DEFAULT_ALLOWED_CATEGORIES = ["AI", "부업", "경제", "생활", "쇼핑", "트렌드"]
    DEFAULT_BLOCKED_CATEGORIES = ["도박", "성인", "불법", "혐오", "정치선동"]

    CATEGORY_KEYWORDS = {
        "AI": ["ai", "인공지능", "챗gpt", "chatgpt", "자동화", "automation", "이미지 생성", "프롬프트"],
        "부업": ["부업", "side", "income", "수익화", "monetization", "재택", "creator", "hustle"],
        "경제": ["경제", "물가", "생활비", "inflation", "재테크", "투자"],
        "생활": ["생활", "일상", "육아", "건강", "습관"],
        "쇼핑": ["쇼핑", "스마트스토어", "쿠팡", "할인", "구매", "상품"],
        "트렌드": ["트렌드", "trend", "이슈", "화제"],
    }

    BLOCKED_KEYWORDS = {
        "도박": ["도박", "베팅", "토토"],
        "성인": ["성인", "음란"],
        "불법": ["불법", "마약", "사기"],
        "혐오": ["혐오", "차별"],
        "정치선동": ["정치선동", "선동"],
    }

    def __init__(self, config=None):
        self.config = config or {}
        self.topic_engine_config = self._load_topic_engine_config()

        self.allowed_categories = self.topic_engine_config.get(
            "allowed_categories",
            self.DEFAULT_ALLOWED_CATEGORIES,
        )
        self.blocked_categories = self.topic_engine_config.get(
            "blocked_categories",
            self.DEFAULT_BLOCKED_CATEGORIES,
        )

    def classify(self, keywords: List[str], selected_topic: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self._classify(keywords or [], selected_topic or {})
        except Exception:
            return {
                "category": "트렌드",
                "blocked": False,
                "reason": "분류 계산 실패로 기본 카테고리 '트렌드'로 대체함.",
            }

    def _classify(self, keywords: List[str], selected_topic: Dict[str, Any]) -> Dict[str, Any]:
        title = str(selected_topic.get("title") or selected_topic.get("keyword") or "")
        search_text = (title + " " + " ".join(str(keyword) for keyword in keywords)).lower()

        blocked_category = self._match_blocked(search_text)

        if blocked_category:
            return {
                "category": blocked_category,
                "blocked": True,
                "reason": f"차단 카테고리 '{blocked_category}' 관련 키워드가 감지되어 안전 처리함.",
            }

        best_category = ""
        best_score = 0

        for category in self.allowed_categories:
            category_keywords = self.CATEGORY_KEYWORDS.get(category, [])
            score = sum(1 for keyword in category_keywords if keyword in search_text)

            if score > best_score:
                best_score = score
                best_category = category

        if not best_category:
            return {
                "category": "트렌드",
                "blocked": False,
                "reason": "일치하는 카테고리 키워드가 없어 기본 카테고리 '트렌드'로 분류함.",
            }

        return {
            "category": best_category,
            "blocked": False,
            "reason": f"키워드 매칭 {best_score}건으로 카테고리 '{best_category}'로 분류함.",
        }

    def _match_blocked(self, search_text: str) -> str:
        for category, keywords in self.BLOCKED_KEYWORDS.items():
            for keyword in keywords:
                if keyword in search_text:
                    return category

        return ""

    def _load_topic_engine_config(self) -> Dict[str, Any]:
        config_path = Path("config/topic_engine.json")

        if not config_path.exists():
            return {}

        try:
            with open(config_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception:
            pass

        return {}
