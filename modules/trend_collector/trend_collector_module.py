import json
from datetime import datetime
from pathlib import Path

from modules.trend_collector.source_health_tracker import SourceHealthTracker
from modules.trend_collector.top_topic_picker import TopTopicPicker
from modules.trend_collector.trend_engine_guard import TrendEngineGuard
from modules.trend_collector.trend_quality_scorer import TrendQualityScorer
from modules.trend_collector.trend_run_recorder import TrendRunRecorder
from modules.trend_collector.trend_source_manager import TrendSourceManager


class TrendCollectorModule:
    def __init__(self, config=None):
        self.config = config or {}
        self.output_dir = Path("storage/trends")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.source_manager = TrendSourceManager(self.config)
        self.quality_scorer = TrendQualityScorer()
        self.topic_picker = TopTopicPicker(self.output_dir)
        self.source_health_tracker = SourceHealthTracker(self.output_dir)
        self.engine_guard = TrendEngineGuard(self.output_dir)
        self.run_recorder = TrendRunRecorder(self.output_dir)

    def run(self):
        print("Trend Collector Module Started")

        raw_trends = self.source_manager.collect_from_enabled_sources()
        trends = self._rank_trends(raw_trends)

        max_trends = self.config.get("topic", {}).get("max_trends", 10)
        selected_trends = trends[:max_trends]
        selected_topic = self.topic_picker.pick(selected_trends)
        source_health_summary = self.source_health_tracker.update(
            self.source_manager.last_collection_summary
        )
        trend_engine_status = self._build_trend_engine_status(
            source_health_summary=source_health_summary,
            selected_topic=selected_topic,
        )

        result = {
            "status": "success",
            "message": "trend_collection_completed",
            "collector_version": "trend_source_manager_v1",
            "count": len(selected_trends),
            "total_collected": len(raw_trends),
            "fallback_used": self.source_manager.last_collection_summary.get(
                "fallback_used",
                False
            ),
            "collection_summary": self.source_manager.last_collection_summary,
            "source_health_summary": source_health_summary,
            "trend_engine_status": trend_engine_status,
            "selected_topic": selected_topic,
            "trends": selected_trends,
            "collected_at": datetime.now().isoformat()
        }
        result = self.engine_guard.normalize_result(result)
        result["trend_run_artifacts"] = self.run_recorder.finalize_run(result)

        self._save_result(result)

        print("Trend Collector Module Finished")
        return result

    def _rank_trends(self, raw_trends):
        ranked = []

        for index, item in enumerate(raw_trends, start=1):
            keyword = str(item.get("keyword", "")).strip()

            if not keyword:
                continue

            base_score = int(item.get("base_score", 50))
            weight = int(item.get("weight", 0))
            tier = int(item.get("tier", 99))

            keyword_bonus = self._keyword_bonus(keyword)
            tier_bonus = max(0, 100 - (tier * 10))

            final_score = base_score + weight + keyword_bonus + tier_bonus

            ranked.append({
                "rank": index,
                "keyword": keyword,
                "score": final_score,
                "base_score": base_score,
                "weight": weight,
                "tier": tier,
                "keyword_bonus": keyword_bonus,
                "source": item.get("source_id", "unknown"),
                "source_name": item.get("source_name", "unknown"),
                "source_type": item.get("source_type", "unknown"),
                "link": item.get("link", ""),
                "summary": item.get("summary", ""),
                "publisher": item.get("publisher", ""),
                "published_at": item.get("published_at", ""),
                "query": item.get("query", ""),
                "collection_method": item.get("collection_method", "unknown"),
                "is_fallback": bool(item.get("is_fallback", False)),
                "trend_reason": item.get("trend_reason", ""),
                "collected_at": item.get("collected_at", datetime.now().isoformat())
            })

        ranked = self.quality_scorer.score_items(ranked)
        ranked.sort(
            key=lambda item: (
                item.get("quality_score", 0),
                item.get("score", 0)
            ),
            reverse=True
        )

        for index, item in enumerate(ranked, start=1):
            item["rank"] = index

        return ranked

    def _keyword_bonus(self, keyword):
        score = 0

        bonus_keywords = [
            "AI",
            "자동화",
            "부업",
            "인스타",
            "카드뉴스",
            "콘텐츠",
            "쇼츠",
            "스마트스토어",
            "수익화",
            "퇴사",
            "자영업",
            "생활비",
            "물가"
        ]

        for bonus in bonus_keywords:
            if bonus in keyword:
                score += 10

        return score

    def _save_result(self, result):
        file_path = self.output_dir / "trend_result.json"

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)

        print(f"Trend Result Saved: {file_path}")

    def _build_trend_engine_status(self, source_health_summary, selected_topic):
        latest = source_health_summary.get("latest", {})
        source_records = [
            record
            for record in latest.values()
            if isinstance(record, dict)
        ]
        success_sources = [
            record.get("source")
            for record in source_records
            if record.get("success")
        ]
        failed_sources = [
            record.get("source")
            for record in source_records
            if record.get("attempted") and not record.get("success")
        ]
        fallback_sources = [
            record.get("source")
            for record in source_records
            if (
                record.get("fallback_reason")
                or record.get("used_cache")
                or "fallback" in str(record.get("collection_method", ""))
                or str(record.get("collection_method", "")).endswith("_cache")
            )
        ]

        return {
            "total_sources": len(source_records),
            "success_sources": success_sources,
            "failed_sources": failed_sources,
            "fallback_sources": fallback_sources,
            "selected_topic_available": bool(selected_topic and selected_topic.get("title")),
            "workflow_safe": True,
        }
