import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class ResearchContextBuilder:
    """
    Research Intelligence v1 - Research Context Builder.

    selected_topic + storage/trends/trend_result.json(TrendCollectorModule이 이미
    쓰는 기존 파일, 읽기 전용)을 읽어 카드뉴스용 리서치 근거를 만드는 데 필요한
    맥락(research_context)을 구성한다. naver_news/nate_pann/fmkorea/bobaedream
    4개 소스의 수집 상태(시도 여부/성공 여부/수집 개수/fallback 여부)를 반영해
    "지금 이 주제가 어떤 소스에서 얼마나 신뢰도 있게 확인됐는지"를 요약한다.

    storage 스키마를 새로 만들지 않고 기존 trend_result.json/pattern_result를
    읽기 전용으로만 사용한다. 파일이 없거나 손상돼도 예외를 던지지 않고 안전한
    빈 컨텍스트를 반환한다 (fallback-first 계약 유지).
    """

    TRACKED_SOURCES = ["naver_news", "nate_pann", "fmkorea", "bobaedream"]
    TREND_RESULT_PATH = Path("storage/trends/trend_result.json")

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def build(
        self,
        selected_topic: Optional[Dict[str, Any]],
        pattern_result: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        try:
            return self._build(selected_topic or {}, pattern_result or {})
        except Exception as error:
            return {
                "keyword": "",
                "category": "",
                "cluster": "",
                "confidence_score": None,
                "quality_score": None,
                "selection_reason": "",
                "source_signals": {},
                "fallback_sources": [],
                "trend_engine_status": {},
                "reason": f"Research Context 계산 실패로 빈 컨텍스트를 반환함: {error}",
                "fallback_used": True,
            }

    def _build(
        self,
        selected_topic: Dict[str, Any],
        pattern_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        trend_result = self._load_trend_result()

        collection_summary = trend_result.get("collection_summary", {})
        if not isinstance(collection_summary, dict):
            collection_summary = {}

        trend_engine_status = trend_result.get("trend_engine_status", {})
        if not isinstance(trend_engine_status, dict):
            trend_engine_status = {}

        topic_intelligence = pattern_result.get("topic_intelligence", {})
        if not isinstance(topic_intelligence, dict):
            topic_intelligence = {}

        source_signals, fallback_sources = self._build_source_signals(collection_summary)

        return {
            "keyword": str(selected_topic.get("title") or selected_topic.get("keyword") or ""),
            "category": str(topic_intelligence.get("category", "")),
            "cluster": str(topic_intelligence.get("cluster", "")),
            "confidence_score": topic_intelligence.get("confidence_score"),
            "quality_score": selected_topic.get("quality_score"),
            "selection_reason": str(selected_topic.get("selection_reason", "")),
            "source_signals": source_signals,
            "fallback_sources": fallback_sources,
            "trend_engine_status": trend_engine_status,
            "reason": "trend_result.json + selected_topic + topic_intelligence 기반으로 컨텍스트를 구성함.",
            "fallback_used": False,
        }

    def _build_source_signals(
        self,
        collection_summary: Dict[str, Any],
    ) -> "tuple[Dict[str, Dict[str, Any]], List[str]]":
        source_signals: Dict[str, Dict[str, Any]] = {}
        fallback_sources: List[str] = []

        for source_id in self.TRACKED_SOURCES:
            status = collection_summary.get(source_id, {})

            if not isinstance(status, dict):
                status = {}

            used_cache = bool(status.get("used_cache", False))
            collection_method = str(status.get("collection_method", ""))
            is_fallback = bool(
                used_cache
                or "fallback" in collection_method
                or collection_method.endswith("_cache")
            )

            if is_fallback:
                fallback_sources.append(source_id)

            source_signals[source_id] = {
                "attempted": bool(status.get("attempted", False)),
                "success": bool(status.get("success", False)),
                "count": self._safe_int(status.get("count", 0), default=0),
                "collection_method": collection_method,
                "used_cache": used_cache,
                "is_fallback": is_fallback,
            }

        return source_signals, fallback_sources

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(value or default)
        except Exception:
            return default

    def _load_trend_result(self) -> Dict[str, Any]:
        if not self.TREND_RESULT_PATH.exists():
            return {}

        try:
            with open(self.TREND_RESULT_PATH, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception:
            pass

        return {}
