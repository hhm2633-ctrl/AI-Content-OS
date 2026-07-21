"""Shallow, fallback-first collector for ApparelNews public editorial lists."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re
import urllib.parse
import urllib.request

from modules.trend_collector.fashionbiz_collector import FashionBizCollector


class ApparelNewsCollector(FashionBizCollector):
    """Collect ApparelNews list metadata without article-detail requests."""

    DEFAULT_URL = "https://www.apparelnews.co.kr/news/news_list/?cat=CAT100"
    DEFAULT_CACHE_PATH = Path("storage/cache/apparelnews_editorial_cache.json")
    ALLOWED_HOSTS = {"apparelnews.co.kr", "www.apparelnews.co.kr"}

    def _empty_status(self) -> Dict[str, Any]:
        status = super()._empty_status()
        status["source"] = "apparelnews"
        status["service_diagnostic"] = (
            self.service_diagnostic.build_diagnostic_from_reason(
                service="apparelnews", reason="", status="ok"
            )
        )
        return status

    def collect(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return live list rows, a bounded cache fallback, or an honest empty list."""
        self.last_status = self._empty_status()
        self.last_status["attempted"] = True
        failures: List[str] = []
        rows: List[Dict[str, Any]] = []

        if bool(self.config.get("allow_live_fetch", False)):
            try:
                _, raw_html = self.fetcher(self._resolve_url(source))
                rows = self.parser(raw_html)
                if not rows:
                    failures.append("parse_failed")
            except Exception as error:
                failures.append(self._classify_error(error))
        else:
            failures.append(self.LIVE_REJECTION_REASON)

        if rows:
            items = self._build_items(
                rows, source, "apparelnews_public_editorial_list", False
            )
            self._set_status(items, "apparelnews_public_editorial_list")
            return items

        cache_items = self._load_cache(source)
        if cache_items:
            reason = self._primary_reason(failures)
            self.last_status.update(
                {
                    "success": True,
                    "count": len(cache_items),
                    "fallback_reason": reason,
                    "final_error_type": reason,
                    "collection_method": "apparelnews_editorial_cache",
                    "used_cache": True,
                }
            )
            self._set_diagnostic(reason, "fallback_used")
            return cache_items

        reason = self._primary_reason(failures)
        self.last_status.update(
            {
                "failed_reason": reason,
                "fallback_reason": reason,
                "final_error_type": reason,
                "error_message": reason,
                "collection_method": "apparelnews_no_data",
            }
        )
        self._set_diagnostic(reason, "fallback_used")
        return []

    def _visible_row(
        self, block: str, title: str, link: str, position: int
    ) -> Dict[str, Any]:
        row = super()._visible_row(block, title, link, position)
        row["attribution"] = "ApparelNews public editorial list"
        summary = self._extract_visible_field(block, ("txt", "excerpt", "summary"))
        if summary:
            row["summary"] = summary
        info = self._extract_visible_field(block, ("info",))
        if info:
            date_match = re.search(r"20\d{2}[./-]\d{1,2}[./-]\d{1,2}", info)
            if date_match:
                row["visible_date"] = date_match.group(0)
            category = re.split(r"[ㅣ|]", info, maxsplit=1)[0].strip()
            if category and not re.fullmatch(r"20\d{2}[./-].*", category):
                row["section_category"] = category
        return row

    def _is_editorial_link(self, link: str) -> bool:
        parsed = urllib.parse.urlparse(link)
        if parsed.path.rstrip("/") != "/news/news_view":
            return False
        query = urllib.parse.parse_qs(parsed.query)
        return bool(query.get("idx") and str(query["idx"][0]).isdigit())

    def _resolve_url(self, source: Dict[str, Any]) -> str:
        url = str(source.get("url") or "").strip()
        if url.startswith(("http://", "https://")):
            parsed = urllib.parse.urlparse(url)
            if parsed.hostname in self.ALLOWED_HOSTS and parsed.path.rstrip("/") == "/news/news_list":
                return url
        return self.DEFAULT_URL

    def _fetch_url(self, url: str) -> Tuple[str, str]:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return response.geturl(), response.read().decode("utf-8", errors="ignore")

    def _build_items(
        self,
        rows: List[Dict[str, Any]],
        source: Dict[str, Any],
        collection_method: str,
        is_fallback: bool,
    ) -> List[Dict[str, Any]]:
        normalized_source = dict(source)
        normalized_source.setdefault("source_id", "apparelnews")
        normalized_source.setdefault("name", "ApparelNews")
        items = super()._build_items(
            rows, normalized_source, collection_method, is_fallback
        )
        for item in items:
            item["attribution"] = "ApparelNews public editorial list"
        return items

    def _load_cache(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.cache_path.exists():
            return []
        try:
            import json

            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or not self._cache_is_fresh(payload.get("updated_at")):
                return []
            rows = payload.get("items")
            if not isinstance(rows, list):
                return []
        except Exception:
            return []
        return self._build_items(rows, source, "apparelnews_editorial_cache", True)

    def _set_diagnostic(self, reason: str, status: str) -> None:
        self.last_status["service_diagnostic"] = (
            self.service_diagnostic.build_diagnostic_from_reason(
                service="apparelnews", reason=reason, status=status
            )
        )
