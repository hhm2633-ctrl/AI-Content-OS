"""Fallback-first shallow collector for the GQ Korea grooming list."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from modules.trend_collector.beautynury_collector import BeautynuryCollector


class GqGroomingCollector(BeautynuryCollector):
    """Collect visible metadata from one bounded GQ Korea grooming list page."""

    DEFAULT_URL = "https://www.gqkorea.co.kr/style/grooming/"
    DEFAULT_CACHE_PATH = BeautynuryCollector.DEFAULT_CACHE_PATH.with_name(
        "gq_grooming_editorial_cache.json"
    )
    SOURCE_ID = "gq_grooming"
    SOURCE_NAME = "GQ Korea"
    ATTRIBUTION = "GQ Korea public grooming list"
    LIVE_METHOD = "gq_grooming_public_editorial_list"
    CACHE_METHOD = "gq_grooming_editorial_cache"
    NO_DATA_METHOD = "gq_grooming_no_data"
    ALLOWED_HOSTS = {"gqkorea.co.kr", "www.gqkorea.co.kr"}
    ARTICLE_PATH_PATTERN = re.compile(
        r"^/20\d{2}/\d{2}/\d{2}/[^/?#]+/?$", re.IGNORECASE
    )
    GROOMING_TOPIC_LABELS = (
        "male_grooming",
        "skincare",
        "hair",
        "scalp",
        "shaving",
        "body",
        "fragrance",
    )
    GROOMING_TITLE_KEYWORDS = (
        ("male_grooming", ("그루밍", "grooming")),
        ("skincare", ("스킨케어", "스킨 케어", "skincare", "skin care")),
        ("skin", ("피부", "스킨", "skin")),
        ("hair", ("헤어", "머리", "모발", "탈모", "장발", "hair")),
        ("scalp", ("두피", "scalp")),
        ("shampoo", ("샴푸", "shampoo")),
        ("shaving", ("면도", "쉐이빙", "shaving")),
        ("body", ("바디", "체취", "body care", "bodycare")),
        ("fragrance", ("향수", "향기", "프래그런스", "fragrance", "perfume")),
        (
            "hand_care",
            (
                "핸드케어",
                "핸드 케어",
                "핸드워시",
                "핸드 워시",
                "예쁜 손",
                "손 관리",
                "hand care",
                "hand wash",
            ),
        ),
        ("hair_removal", ("제모", "hair removal")),
    )
    OUT_OF_SCOPE_REASON = "title_outside_male_grooming_scope"

    def _extract_summary(self, block: str) -> Optional[str]:
        """Keep only an explicitly labelled list summary, never an arbitrary paragraph."""
        visible = self._extract_visible_field(
            block, ("summary", "description", "desc", "excerpt", "lead")
        )
        return visible or None

    def _extract_visible_date(self, block: str) -> Optional[str]:
        """Separate the visible date from the nested ``by`` author text."""
        visible = super()._extract_visible_date(block)
        match = re.search(r"\b20\d{2}[./-]\d{1,2}[./-]\d{1,2}\b", visible or "")
        return match.group(0) if match else None

    def _build_items(
        self,
        rows: List[Dict[str, Any]],
        source: Dict[str, Any],
        collection_method: str,
        is_fallback: bool,
    ) -> List[Dict[str, Any]]:
        items = super()._build_items(
            rows, source, collection_method, is_fallback
        )
        for item in items:
            item["source_type"] = str(
                source.get("type") or "male_grooming_editorial"
            )
            item["grooming_editorial"] = True
            item["grooming_topic_labels"] = list(self.GROOMING_TOPIC_LABELS)
            eligible, reason = self._classify_editorial_topic(item.get("title"))
            item["editorial_topic_eligible"] = eligible
            item["editorial_topic_eligibility_reason"] = reason
        return items

    @classmethod
    def _classify_editorial_topic(cls, title: Any) -> tuple[bool, str]:
        normalized = re.sub(r"\s+", " ", str(title or "")).strip().lower()
        for topic, keywords in cls.GROOMING_TITLE_KEYWORDS:
            if any(keyword in normalized for keyword in keywords):
                return True, f"matched_title_keyword:{topic}"
        return False, cls.OUT_OF_SCOPE_REASON


__all__ = ["GqGroomingCollector"]
