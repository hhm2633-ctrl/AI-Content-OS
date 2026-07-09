import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from modules.base_module import BaseModule
from modules.pattern_engine.cta_selector import CTASelector
from modules.pattern_engine.hook_selector import HookSelector
from modules.pattern_engine.layout_selector import LayoutSelector
from modules.pattern_engine.pattern_result_writer import PatternResultWriter
from modules.pattern_engine.pattern_selector import PatternSelector
from modules.topic_engine.confidence_score import ConfidenceScorer
from modules.topic_engine.keyword_weight import KeywordWeightEngine
from modules.topic_engine.topic_classifier import TopicClassifier
from modules.topic_engine.topic_cluster import TopicCluster


class PatternEngineModule(BaseModule):
    """
    Sprint 2 Topic Intelligence + Pattern Engine module.

    WorkflowEngine runs this after TopicEngineModule and before ResearchModule.
    Missing inputs or calculation failures are converted into fallback pattern
    results instead of workflow failures.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}

        self.selected_topic_path = Path("storage/trends/selected_topic.json")
        self.trend_result_path = Path("storage/trends/trend_result.json")

        self.keyword_weight_engine = KeywordWeightEngine(self.config)
        self.topic_classifier = TopicClassifier(self.config)
        self.topic_cluster = TopicCluster(self.config)
        self.confidence_scorer = ConfidenceScorer(self.config)

        self.pattern_selector = PatternSelector(self.config)
        self.hook_selector = HookSelector(self.config)
        self.cta_selector = CTASelector(self.config)
        self.layout_selector = LayoutSelector(self.config)

        self.result_writer = PatternResultWriter()

    def run(
        self,
        selected_topic: Optional[Dict[str, Any]] = None,
        trend_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        print("Pattern Engine Module Started")

        result = self._build_result(selected_topic, trend_result)

        try:
            self.result_writer.write(result)
        except Exception as error:
            print(f"Pattern Result Write Failed: {error}")

        print("Pattern Engine Module Finished")
        return result

    def _build_result(
        self,
        selected_topic: Optional[Dict[str, Any]],
        trend_result: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        try:
            selected_topic = selected_topic or self._load_json(self.selected_topic_path)
            trend_result = trend_result or self._load_json(self.trend_result_path)

            if not isinstance(trend_result, dict):
                trend_result = {}

            trends = trend_result.get("trends", [])
            if not isinstance(trends, list):
                trends = []

            if not self._has_title(selected_topic):
                embedded_topic = trend_result.get("selected_topic")

                if self._has_title(embedded_topic):
                    selected_topic = embedded_topic
                else:
                    return self._fallback_result(reason="selected_topic_missing")

            return self._build_pattern_result(selected_topic, trends)

        except Exception as error:
            return self._fallback_result(reason=f"pattern_engine_error: {error}")

    def _build_pattern_result(
        self,
        selected_topic: Dict[str, Any],
        trends: Any,
    ) -> Dict[str, Any]:
        keywords, keyword_weights = self.keyword_weight_engine.compute_weights(
            selected_topic,
            trends,
        )

        classification = self.topic_classifier.classify(keywords, selected_topic)
        category = classification.get("category", "trend")
        blocked = bool(classification.get("blocked", False))

        cluster_result = self.topic_cluster.assign_cluster(category, keywords, selected_topic)
        cluster = cluster_result.get("cluster", "general_trend_cluster")

        confidence_result = self.confidence_scorer.score(
            selected_topic=selected_topic,
            keyword_weights=keyword_weights,
            category=category,
            cluster=cluster,
            blocked=blocked,
        )
        confidence_score = confidence_result.get("confidence_score", 0.0)

        topic_intelligence = {
            "keywords": keywords,
            "keyword_weights": keyword_weights,
            "category": category,
            "cluster": cluster,
            "confidence_score": confidence_score,
            "reason": " ".join(
                filter(
                    None,
                    [
                        classification.get("reason", ""),
                        cluster_result.get("reason", ""),
                        confidence_result.get("reason", ""),
                    ],
                )
            ),
        }

        pattern_type_result = self.pattern_selector.select(category, cluster, confidence_score)
        pattern_type = pattern_type_result.get("pattern_type", "resource")

        hook_result = self.hook_selector.select(category, pattern_type)
        cta_result = self.cta_selector.select(category, pattern_type)
        layout_result = self.layout_selector.select(category, pattern_type)

        pattern_plan = {
            "pattern_type": pattern_type,
            "hook_type": hook_result.get("hook_type", "saveable_tip"),
            "cta_type": cta_result.get("cta_type", "save"),
            "layout_type": layout_result.get("layout_type", "bold_ai"),
            "reason": " ".join(
                filter(
                    None,
                    [
                        pattern_type_result.get("reason", ""),
                        hook_result.get("reason", ""),
                        cta_result.get("reason", ""),
                        layout_result.get("reason", ""),
                    ],
                )
            ),
        }

        collection_method = str(selected_topic.get("collection_method", ""))
        fallback_used = (
            bool(blocked)
            or bool(selected_topic.get("is_fallback", False))
            or "fallback" in collection_method
        )

        return {
            "status": "pattern_selected",
            "selected_topic": selected_topic,
            "topic_intelligence": topic_intelligence,
            "pattern_plan": pattern_plan,
            "fallback_used": fallback_used,
            "created_at": datetime.now().isoformat(),
        }

    def _fallback_result(self, reason: str) -> Dict[str, Any]:
        print(f"Pattern Engine Fallback Used: {reason}")

        return {
            "status": "pattern_selected",
            "selected_topic": {},
            "topic_intelligence": {
                "keywords": [],
                "keyword_weights": {},
                "category": "trend",
                "cluster": "general_trend_cluster",
                "confidence_score": 0.0,
                "reason": f"fallback: {reason}",
            },
            "pattern_plan": {
                "pattern_type": "resource",
                "hook_type": "saveable_tip",
                "cta_type": "save",
                "layout_type": "bold_ai",
                "reason": "Pattern Engine fallback used; safe default pattern selected.",
            },
            "fallback_used": True,
            "created_at": datetime.now().isoformat(),
        }

    def _has_title(self, topic: Any) -> bool:
        return isinstance(topic, dict) and bool(str(topic.get("title", "")).strip())

    def _load_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}

        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception as error:
            print(f"Pattern Engine Input Load Failed ({path}): {error}")

        return {}
