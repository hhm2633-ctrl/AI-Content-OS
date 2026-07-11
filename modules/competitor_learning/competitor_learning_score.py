from datetime import datetime
from typing import Any, Dict, List


class CompetitorLearningScorer:
    """
    Competitor Learning Engine - Score (Sprint 18).

    Turns CompetitorLearningStatistics output into ranked Knowledge Database
    entries. Deterministic, no LLM/randomness:

        overall_score = share * 0.6 + confidence * 0.3 + engagement_factor * 0.1

    - share: this value's frequency within its own type's sample.
    - confidence: instagram_research classifier's average confidence for this
      value (0.0 for layout, which has no classifier confidence - post_type is
      directly observed, not inferred).
    - engagement_factor: avg_likes normalized against the highest avg_likes
      seen this run (0.0 when no like counts were observed - never fabricated).

    build_entries() never raises: malformed/missing statistics degrade to an
    empty entry list.
    """

    def build_entries(self, statistics: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            return self._build_entries(statistics or {})
        except Exception as error:
            print(f"Competitor Learning Scorer Failed: {error}")
            return []

    def _build_entries(self, statistics: Dict[str, Any]) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        max_likes = self._max_avg_likes(statistics)
        generated_at = datetime.now().isoformat()

        type_configs = (
            ("hook", "hook_statistics", "top", True),
            ("cta", "cta_statistics", "top", True),
            ("pattern", "pattern_statistics", "top", True),
            ("layout", "layout_statistics", "top_layouts", False),
        )

        for entry_type, stats_key, top_key, has_confidence in type_configs:
            stats = statistics.get(stats_key) or {}
            sample_size = stats.get("sample_size", 0) or 0
            items = stats.get(top_key, []) or []

            for item in items:
                if not isinstance(item, dict):
                    continue

                value = item.get("value")
                if not value or value == "unknown":
                    continue

                entries.append(
                    self._build_entry(entry_type, item, sample_size, max_likes, has_confidence, generated_at)
                )

        entries.sort(key=lambda entry: entry.get("score", {}).get("overall_score", 0.0), reverse=True)

        for rank, entry in enumerate(entries, start=1):
            entry["rank"] = rank

        return entries

    def _build_entry(
        self,
        entry_type: str,
        item: Dict[str, Any],
        sample_size: int,
        max_likes: float,
        has_confidence: bool,
        generated_at: str,
    ) -> Dict[str, Any]:
        count = item.get("count", 0) or 0
        share = round(count / sample_size, 4) if sample_size else 0.0

        avg_confidence = item.get("avg_confidence") if has_confidence else None
        confidence = float(avg_confidence) if isinstance(avg_confidence, (int, float)) else 0.0

        avg_likes = item.get("avg_likes")
        engagement_factor = (
            round(float(avg_likes) / max_likes, 4)
            if isinstance(avg_likes, (int, float)) and max_likes
            else 0.0
        )

        overall_score = round(min(1.0, share * 0.6 + confidence * 0.3 + engagement_factor * 0.1), 4)

        return {
            "knowledge_id": f"competitor_learning_{entry_type}_{item.get('value')}",
            "type": entry_type,
            "value": item.get("value"),
            "frequency": count,
            "sample_size": sample_size,
            "avg_likes": avg_likes,
            "avg_comments": item.get("avg_comments"),
            "score": {
                "share": share,
                "confidence": confidence,
                "engagement_factor": engagement_factor,
                "overall_score": overall_score,
            },
            "source": "instagram_research",
            "generated_at": generated_at,
        }

    def _max_avg_likes(self, statistics: Dict[str, Any]) -> float:
        candidates = []

        for stats_key, top_key in (
            ("hook_statistics", "top"),
            ("cta_statistics", "top"),
            ("pattern_statistics", "top"),
            ("layout_statistics", "top_layouts"),
        ):
            for item in (statistics.get(stats_key) or {}).get(top_key, []) or []:
                if not isinstance(item, dict):
                    continue
                avg_likes = item.get("avg_likes")
                if isinstance(avg_likes, (int, float)):
                    candidates.append(float(avg_likes))

        return max(candidates) if candidates else 0.0
