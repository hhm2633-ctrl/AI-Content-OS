"""Fallback-first shallow collector for MUSINSA Beauty public lists."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from modules.trend_collector.musinsa_boutique_collector import (
    MusinsaBoutiqueCollector,
)


class MusinsaBeautyCollector(MusinsaBoutiqueCollector):
    """Parse visible Beauty list metadata as a platform beauty-retail signal."""

    DEFAULT_URL = "https://www.musinsa.com/main/beauty"
    DEFAULT_CACHE_PATH = Path("storage/cache/musinsa_beauty_cache.json")
    SOURCE_ROLE = "beauty_retail"
    SIGNAL_SCOPE = "platform_specific"
    VERTICAL = "beauty"

    def __init__(
        self,
        timeout: int = 8,
        max_items: int = 30,
        config: Optional[Dict[str, Any]] = None,
        fetcher: Optional[Callable[[str], Tuple[str, str]]] = None,
        parser: Optional[Callable[[str], List[Dict[str, Any]]]] = None,
    ) -> None:
        super().__init__(
            timeout=timeout,
            max_items=max_items,
            config=config,
            fetcher=fetcher,
            parser=parser or self.parse_public_beauty_list,
        )

    def _empty_status(self) -> Dict[str, Any]:
        status = super()._empty_status()
        status.update(
            {
                "source": "musinsa_beauty",
                "source_role": self.SOURCE_ROLE,
                "vertical": self.VERTICAL,
                "signal_scope": self.SIGNAL_SCOPE,
            }
        )
        return status

    def collect(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.last_status = self._empty_status()
        self.last_status["attempted"] = True
        failures: List[str] = []
        rows: List[Dict[str, Any]] = []
        if bool(self.config.get("allow_live_fetch", False)):
            try:
                _, payload = self.fetcher(self._resolve_url(source))
                rows = self.parser(payload)
                if not rows:
                    failures.append(self.last_parse_reason or "parse_failed")
            except Exception as error:
                failures.append(self._classify_error(error))
        else:
            failures.append(self.LIVE_REJECTION_REASON)

        if rows:
            items = self._build_items(rows, source, "musinsa_beauty_public_list", False)
            self._set_success(items, "musinsa_beauty_public_list")
            return items

        cached = self._load_cache(source)
        if cached:
            reason = self._primary_reason(failures)
            self.last_status.update(
                {
                    "success": True,
                    "count": len(cached),
                    "fallback_reason": reason,
                    "final_error_type": reason,
                    "collection_method": "musinsa_beauty_cache",
                    "used_cache": True,
                }
            )
            self._set_diagnostic(reason, "fallback_used")
            return cached

        reason = self._primary_reason(failures)
        self.last_status.update(
            {
                "failed_reason": reason,
                "fallback_reason": reason,
                "final_error_type": reason,
                "error_message": reason,
                "collection_method": "musinsa_beauty_no_data",
            }
        )
        self._set_diagnostic(reason, "fallback_used")
        return []

    def parse_public_beauty_list(self, raw_payload: str) -> List[Dict[str, Any]]:
        document = str(raw_payload or "")
        self.last_parse_reason = ""
        if not document.strip():
            self.last_parse_reason = "empty_result"
            return []
        payload = self._load_json_payload(document)
        rows = self._parse_json_rows(payload) if payload is not None else []
        if not rows:
            rows = self._parse_html_rows(document)
        if not rows:
            self.last_parse_reason = (
                self.PUBLIC_SHELL_REASON
                if "__NEXT_DATA__" in document
                else "parse_failed"
            )
        return rows[: self.max_items]

    def _build_items(
        self,
        rows: List[Dict[str, Any]],
        source: Dict[str, Any],
        collection_method: str,
        is_fallback: bool,
    ) -> List[Dict[str, Any]]:
        items = super()._build_items(rows, source, collection_method, is_fallback)
        for item in items:
            item["source_id"] = "musinsa_beauty"
            item["source_name"] = str(source.get("name") or "MUSINSA Beauty")
            item["source_type"] = str(source.get("type") or "beauty_retail")
            item["source_role"] = self.SOURCE_ROLE
            item["vertical"] = self.VERTICAL
            item["signal_scope"] = self.SIGNAL_SCOPE
        return items

    def _load_cache(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.cache_path.exists():
            return []
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            rows = payload.get("items") if self._cache_is_fresh(payload.get("updated_at")) else []
            if not isinstance(rows, list):
                return []
        except Exception:
            return []
        return self._build_items(rows, source, "musinsa_beauty_cache", True)

    def _set_diagnostic(self, reason: str, status: str) -> None:
        self.last_status["service_diagnostic"] = (
            self.service_diagnostic.build_diagnostic_from_reason(
                service="musinsa_beauty",
                reason=reason,
                status=status,
            )
        )
