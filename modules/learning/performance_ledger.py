"""Local ledger that keeps internal QA proxies separate from measured performance."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


class PerformanceLedgerError(ValueError):
    """Raised when performance evidence violates the local ledger contract."""


class PerformanceLedger:
    SCHEMA_VERSION = 1
    INTERNAL_PROXY = "internal_proxy"
    EXTERNAL_MEASURED = "external_measured"
    INTERNAL_ONLY_METRICS = {
        "audit_score",
        "brand_score",
        "cta_score",
        "hook_score",
        "image_score",
        "internal_learning_score",
        "layout_score",
        "overall_performance_score",
        "quality_score",
    }

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or "storage/learning/performance_ledger.json")

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as error:
            raise PerformanceLedgerError(f"could not read performance ledger: {error}") from error
        if not isinstance(data, dict):
            raise PerformanceLedgerError("performance ledger must be a JSON object")
        internal = data.get("internal_proxy_records", [])
        external = data.get("external_measured_records", [])
        imports = data.get("import_batches", [])
        if not all(isinstance(value, list) for value in (internal, external, imports)):
            raise PerformanceLedgerError("performance ledger record collections must be lists")
        return {
            "schema_version": self.SCHEMA_VERSION,
            "internal_proxy_records": internal,
            "external_measured_records": external,
            "import_batches": imports,
            "updated_at": data.get("updated_at"),
        }

    def record_internal_proxy(self, record: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._normalize_identity(record)
        normalized.update(
            {
                "ledger_entry_id": self._entry_id(self.INTERNAL_PROXY, record),
                "measurement_class": self.INTERNAL_PROXY,
                "metrics": self._numeric_metrics(record.get("metrics")),
                "eligible_for_pattern_promotion": False,
                "recorded_at": self._now(),
            }
        )
        data = self.load()
        fingerprints = {
            item.get("ledger_entry_id") for item in data["internal_proxy_records"] if isinstance(item, dict)
        }
        if normalized["ledger_entry_id"] not in fingerprints:
            data["internal_proxy_records"].append(normalized)
            self._save(data)
        return normalized

    def import_external(
        self,
        records: Iterable[Dict[str, Any]],
        *,
        source_type: str,
        source_name: str,
        source_hash: str,
    ) -> Dict[str, Any]:
        if source_type not in {"manual_csv", "manual_json"}:
            raise PerformanceLedgerError("external import source_type must be manual_csv or manual_json")
        normalized_records = [
            self._normalize_external(
                record,
                source_type=source_type,
                source_name=source_name,
                source_hash=source_hash,
            )
            for record in records
        ]
        data = self.load()
        known = {
            item.get("ledger_entry_id")
            for item in data["external_measured_records"]
            if isinstance(item, dict)
        }
        inserted: List[str] = []
        duplicates: List[str] = []
        for record in normalized_records:
            entry_id = record["ledger_entry_id"]
            if entry_id in known:
                duplicates.append(entry_id)
                continue
            data["external_measured_records"].append(record)
            known.add(entry_id)
            inserted.append(entry_id)

        batch = {
            "import_batch_id": self._hash(
                {
                    "source_type": source_type,
                    "source_hash": source_hash,
                    "entry_ids": [item["ledger_entry_id"] for item in normalized_records],
                }
            ),
            "source_type": source_type,
            "source_name": source_name,
            "source_hash": source_hash,
            "received_count": len(normalized_records),
            "inserted_count": len(inserted),
            "duplicate_count": len(duplicates),
            "inserted_entry_ids": inserted,
            "duplicate_entry_ids": duplicates,
            "imported_at": self._now(),
        }
        if not any(
            item.get("import_batch_id") == batch["import_batch_id"]
            for item in data["import_batches"]
            if isinstance(item, dict)
        ):
            data["import_batches"].append(batch)
        self._save(data)
        return batch

    def external_records(self, *, pattern_id: Optional[str] = None) -> List[Dict[str, Any]]:
        records = list(self.load()["external_measured_records"])
        if pattern_id:
            records = [
                record for record in records if pattern_id in (record.get("pattern_ids") or [])
            ]
        return records

    def _normalize_external(
        self,
        record: Dict[str, Any],
        *,
        source_type: str,
        source_name: str,
        source_hash: str,
    ) -> Dict[str, Any]:
        declared_class = record.get("measurement_class")
        if declared_class not in (None, "", self.EXTERNAL_MEASURED):
            raise PerformanceLedgerError("manual performance import cannot contain internal_proxy records")
        normalized = self._normalize_identity(record)
        if not normalized["media_id"]:
            raise PerformanceLedgerError("external measured performance requires media_id")
        if not normalized["pattern_ids"] and not normalized["reference_ids"]:
            raise PerformanceLedgerError("external measured performance requires pattern_ids or reference_ids")

        start, end = self._evaluation_period(record)
        sample_size = self._positive_integer(record.get("sample_size"), "sample_size")
        metrics = self._numeric_metrics(record.get("metrics") or self._flat_metrics(record))
        forbidden = sorted(set(metrics).intersection(self.INTERNAL_ONLY_METRICS))
        if forbidden:
            raise PerformanceLedgerError(
                "external measured metrics cannot include internal proxy fields: " + ", ".join(forbidden)
            )
        if not metrics:
            raise PerformanceLedgerError("external measured performance requires at least one numeric metric")

        canonical = {
            **normalized,
            "measurement_class": self.EXTERNAL_MEASURED,
            "evaluation_period": {"start": start, "end": end},
            "sample_size": sample_size,
            "metrics": metrics,
        }
        return {
            **canonical,
            "ledger_entry_id": self._entry_id(self.EXTERNAL_MEASURED, canonical),
            "provenance": {
                "source_type": source_type,
                "source_name": source_name,
                "source_hash": source_hash,
                "imported_at": self._now(),
            },
            "eligible_for_pattern_promotion": True,
        }

    def _normalize_identity(self, record: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(record, dict):
            raise PerformanceLedgerError("performance record must be an object")
        output_set_id = self._required_text(record.get("output_set_id"), "output_set_id")
        candidate_id = self._required_text(record.get("candidate_id"), "candidate_id")
        return {
            "output_set_id": output_set_id,
            "candidate_id": candidate_id,
            "pattern_ids": self._id_list(record.get("pattern_ids") or record.get("pattern_id")),
            "reference_ids": self._id_list(record.get("reference_ids") or record.get("reference_id")),
            "media_id": str(record.get("media_id") or "").strip(),
        }

    def _evaluation_period(self, record: Dict[str, Any]) -> Tuple[str, str]:
        period = record.get("evaluation_period") or {}
        if not isinstance(period, dict):
            raise PerformanceLedgerError("evaluation_period must be an object")
        start = period.get("start") or record.get("evaluation_start")
        end = period.get("end") or record.get("evaluation_end")
        start_dt = self._parse_datetime(start, "evaluation_start")
        end_dt = self._parse_datetime(end, "evaluation_end")
        if end_dt < start_dt:
            raise PerformanceLedgerError("evaluation_end must not precede evaluation_start")
        return start_dt.isoformat(), end_dt.isoformat()

    @staticmethod
    def _parse_datetime(value: Any, field: str) -> datetime:
        text = str(value or "").strip()
        if not text:
            raise PerformanceLedgerError(f"{field} is required")
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as error:
            raise PerformanceLedgerError(f"{field} must be ISO-8601") from error
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _positive_integer(value: Any, field: str) -> int:
        if isinstance(value, bool):
            raise PerformanceLedgerError(f"{field} must be a positive integer")
        try:
            parsed = int(value)
        except (TypeError, ValueError) as error:
            raise PerformanceLedgerError(f"{field} must be a positive integer") from error
        if parsed <= 0:
            raise PerformanceLedgerError(f"{field} must be greater than zero")
        return parsed

    @staticmethod
    def _required_text(value: Any, field: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise PerformanceLedgerError(f"{field} is required")
        return text

    @staticmethod
    def _id_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            values = value.replace(";", ",").split(",")
        elif isinstance(value, (list, tuple, set)):
            values = value
        else:
            values = [value]
        result: List[str] = []
        for item in values:
            text = str(item or "").strip()
            if text and text not in result:
                result.append(text)
        return result

    @staticmethod
    def _numeric_metrics(value: Any) -> Dict[str, float]:
        if not isinstance(value, dict):
            return {}
        result: Dict[str, float] = {}
        for key, metric in value.items():
            if isinstance(metric, bool):
                continue
            try:
                result[str(key)] = float(metric)
            except (TypeError, ValueError):
                continue
        return result

    @staticmethod
    def _flat_metrics(record: Dict[str, Any]) -> Dict[str, Any]:
        reserved = {
            "measurement_class",
            "output_set_id",
            "candidate_id",
            "pattern_id",
            "pattern_ids",
            "reference_id",
            "reference_ids",
            "media_id",
            "evaluation_period",
            "evaluation_start",
            "evaluation_end",
            "sample_size",
            "metrics",
        }
        return {key: value for key, value in record.items() if key not in reserved}

    def _save(self, data: Dict[str, Any]) -> None:
        data = dict(data)
        data["schema_version"] = self.SCHEMA_VERSION
        data["updated_at"] = self._now()
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
                json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.path)
        except OSError as error:
            if temporary_name:
                Path(temporary_name).unlink(missing_ok=True)
            raise PerformanceLedgerError(f"could not write performance ledger: {error}") from error

    def _empty(self) -> Dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "internal_proxy_records": [],
            "external_measured_records": [],
            "import_batches": [],
            "updated_at": None,
        }

    @classmethod
    def _entry_id(cls, measurement_class: str, record: Dict[str, Any]) -> str:
        return f"perf-{cls._hash({'measurement_class': measurement_class, 'record': record})[:24]}"

    @staticmethod
    def _hash(value: Any) -> str:
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
