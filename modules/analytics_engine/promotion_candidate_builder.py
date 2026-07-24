"""Build review-only pattern promotion candidates from external measurements."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


class PromotionCandidateError(ValueError):
    pass


class PromotionCandidateBuilder:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or "storage/learning/promotion_candidates.json")

    def build(
        self,
        *,
        pattern_id: str,
        records: Iterable[Dict[str, Any]],
        metric_thresholds: Optional[Dict[str, float]] = None,
        minimum_sample_size: int = 1,
    ) -> Dict[str, Any]:
        pattern_id = str(pattern_id or "").strip()
        if not pattern_id:
            raise PromotionCandidateError("pattern_id is required")
        selected = [
            dict(record)
            for record in records
            if pattern_id in (record.get("pattern_ids") or [])
        ]
        if not selected:
            raise PromotionCandidateError("no external measured records are linked to pattern_id")
        if any(record.get("measurement_class") != "external_measured" for record in selected):
            raise PromotionCandidateError("promotion candidates may use external_measured records only")

        sample_size = sum(int(record.get("sample_size", 0)) for record in selected)
        metrics = self._weighted_metrics(selected)
        thresholds = {
            str(key): float(value) for key, value in (metric_thresholds or {}).items()
        }
        threshold_results = {
            key: {
                "actual": metrics.get(key),
                "required": required,
                "met": metrics.get(key) is not None and float(metrics[key]) >= required,
            }
            for key, required in thresholds.items()
        }
        performance_met = (
            sample_size >= int(minimum_sample_size)
            and bool(threshold_results)
            and all(item["met"] for item in threshold_results.values())
        )
        entry_ids = sorted(record["ledger_entry_id"] for record in selected)
        candidate_id = "promotion-" + self._hash(
            {
                "pattern_id": pattern_id,
                "entry_ids": entry_ids,
                "thresholds": thresholds,
                "minimum_sample_size": int(minimum_sample_size),
            }
        )[:24]
        candidate = {
            "promotion_candidate_id": candidate_id,
            "pattern_id": pattern_id,
            "status": "pending_owner_approval",
            "measurement_class": "external_measured",
            "ledger_entry_ids": entry_ids,
            "output_set_ids": self._unique(selected, "output_set_id"),
            "candidate_ids": self._unique(selected, "candidate_id"),
            "reference_ids": sorted(
                {
                    reference_id
                    for record in selected
                    for reference_id in (record.get("reference_ids") or [])
                }
            ),
            "media_ids": self._unique(selected, "media_id"),
            "evaluation_period": {
                "start": min(record["evaluation_period"]["start"] for record in selected),
                "end": max(record["evaluation_period"]["end"] for record in selected),
            },
            "sample_size": sample_size,
            "record_count": len(selected),
            "weighted_metrics": metrics,
            "metric_thresholds": thresholds,
            "threshold_results": threshold_results,
            "minimum_sample_size": int(minimum_sample_size),
            "performance_met": performance_met,
            "owner_approval": None,
            "automatic_apply": False,
            "pattern_registry_called": False,
            "created_at": self._now(),
        }
        self._upsert(candidate)
        return candidate

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": 1, "candidates": [], "updated_at": None}
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as error:
            raise PromotionCandidateError(f"could not read promotion candidates: {error}") from error
        if not isinstance(data, dict) or not isinstance(data.get("candidates", []), list):
            raise PromotionCandidateError("promotion candidate store has an invalid shape")
        return data

    def save(self, data: Dict[str, Any]) -> None:
        payload = dict(data)
        payload["schema_version"] = 1
        payload["updated_at"] = self._now()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_name = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                delete=False,
                dir=self.path.parent,
            ) as handle:
                temporary_name = handle.name
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.path)
        except OSError as error:
            if temporary_name:
                Path(temporary_name).unlink(missing_ok=True)
            raise PromotionCandidateError(f"could not write promotion candidates: {error}") from error

    def _upsert(self, candidate: Dict[str, Any]) -> None:
        data = self.load()
        candidates = [
            item
            for item in data.get("candidates", [])
            if item.get("promotion_candidate_id") != candidate["promotion_candidate_id"]
        ]
        candidates.append(candidate)
        data["candidates"] = candidates
        self.save(data)

    @staticmethod
    def _weighted_metrics(records: List[Dict[str, Any]]) -> Dict[str, float]:
        totals: Dict[str, float] = {}
        weights: Dict[str, int] = {}
        for record in records:
            weight = int(record.get("sample_size", 0))
            for key, value in (record.get("metrics") or {}).items():
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    continue
                totals[key] = totals.get(key, 0.0) + float(value) * weight
                weights[key] = weights.get(key, 0) + weight
        return {
            key: round(total / weights[key], 6)
            for key, total in totals.items()
            if weights.get(key, 0) > 0
        }

    @staticmethod
    def _unique(records: List[Dict[str, Any]], key: str) -> List[str]:
        return sorted(
            {
                str(record.get(key))
                for record in records
                if str(record.get(key) or "").strip()
            }
        )

    @staticmethod
    def _hash(value: Any) -> str:
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
