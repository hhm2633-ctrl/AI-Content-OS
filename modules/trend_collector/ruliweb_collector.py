import html
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urljoin

from modules.common.service_diagnostic import ServiceDiagnostic


class RuliwebCollector:
    """Fixture/cache-ready Ruliweb best-list collector with live access disabled."""

    BASE_URL = "https://bbs.ruliweb.com"
    DEFAULT_CACHE_PATH = Path("storage/cache/ruliweb_cache.json")
    LIVE_REJECTION_REASON = "live_activation_not_approved"

    def __init__(
        self,
        max_items: int = 20,
        config: Optional[Dict[str, Any]] = None,
        fetcher: Optional[Callable[[str], Tuple[str, str]]] = None,
        parser: Optional[Callable[[str], List[Dict[str, Any]]]] = None,
    ):
        self.max_items = max(1, int(max_items))
        self.config = config or {}
        self.fetcher = fetcher
        self.parser = parser or self._parse_fixture_html
        self.cache_path = Path(self.config.get("cache_path", self.DEFAULT_CACHE_PATH))
        self.cache_ttl_seconds = int(self.config.get("cache_ttl_seconds", 24 * 60 * 60))
        self.retry_enabled = bool(self.config.get("retry_enabled", True))
        self.max_retries = max(0, min(int(self.config.get("max_retries", 2)), 3))
        self.service_diagnostic = ServiceDiagnostic()
        self.last_status = self._empty_status()

    def _empty_status(self) -> Dict[str, Any]:
        return {
            "source": "ruliweb",
            "attempted": False,
            "success": False,
            "count": 0,
            "failed_reason": "",
            "fallback_reason": "",
            "final_error_type": "",
            "collection_method": "",
            "used_cache": False,
            "cache_path": str(self.cache_path).replace("\\", "/"),
            "retry_enabled": self.retry_enabled,
            "retry_count": 0,
            "service_diagnostic": self._diagnostic("", "ok"),
        }

    def collect(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.last_status = self._empty_status()
        self.last_status["attempted"] = True
        failures: List[str] = []
        rows: List[Dict[str, Any]] = []

        fixture_enabled = bool(self.config.get("fixture_collection_enabled", False))
        live_enabled = bool(self.config.get("allow_live_fetch", False))
        if live_enabled and self.fetcher is None:
            self.fetcher = self._fetch_url
        if (fixture_enabled or live_enabled) and callable(self.fetcher):
            rows, failures = self._collect_fixture(source)
        else:
            failures.append(self.LIVE_REJECTION_REASON)

        if rows:
            method = "ruliweb_live_html" if live_enabled else "ruliweb_fixture_html"
            items = self._dedupe(self._build_items(rows, source))[: self.max_items]
            if items:
                for item in items:
                    item["collection_method"] = method
                    item["trend_reason"] = f"Ruliweb {'live' if live_enabled else 'fixture'} best-list collection"
                self._save_cache(items)
                self._set_success(items, method)
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
                    "collection_method": "ruliweb_cache",
                    "used_cache": True,
                    "service_diagnostic": self._diagnostic(reason, "fallback_used"),
                }
            )
            return cache_items

        reason = self._primary_reason(failures)
        self.last_status.update(
            {
                "failed_reason": reason,
                "fallback_reason": reason,
                "final_error_type": reason,
                "collection_method": "ruliweb_no_data",
                "service_diagnostic": self._diagnostic(reason, "fallback_used"),
            }
        )
        return []

    def _collect_fixture(
        self, source: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        failures: List[str] = []
        attempts = 1 + (self.max_retries if self.retry_enabled else 0)
        fixture_url = str(
            self.config.get("fixture_url") or source.get("url") or self.BASE_URL
        )

        for attempt in range(attempts):
            try:
                _, raw_html = self.fetcher(fixture_url)  # type: ignore[misc]
                rows = self.parser(raw_html)
                if rows:
                    return rows, failures
                failures.append("parse_failed")
            except Exception as error:
                failures.append(self._classify_error(error))

            if attempt < attempts - 1:
                self.last_status["retry_count"] += 1

        return [], failures

    def _parse_fixture_html(self, raw_html: str) -> List[Dict[str, Any]]:
        if not raw_html:
            return []

        rows: List[Dict[str, Any]] = []
        for row_html in re.findall(
            r"<tr\b[^>]*>.*?</tr>", raw_html, flags=re.IGNORECASE | re.DOTALL
        ):
            open_tag = row_html.split(">", 1)[0] + ">"
            row_class = self._attr(open_tag, "class").lower()
            if "notice" in row_class or "공지" in self._clean_text(row_html):
                continue

            anchor = self._title_anchor(row_html)
            if not anchor:
                continue
            href, title = anchor
            if not title:
                continue

            rows.append(
                {
                    "title": title,
                    "link": self._normalize_link(href),
                    "published_at": self._attr(open_tag, "data-published-at")
                    or self._cell_text(row_html, ("time", "date", "regdate")),
                    "category": self._attr(open_tag, "data-category")
                    or self._cell_text(row_html, ("divsn", "category", "board_name")),
                    "views": self._metric(
                        open_tag, row_html, "data-views", ("hit", "views", "readnum")
                    ),
                    "comments": self._metric(
                        open_tag,
                        row_html,
                        "data-comments",
                        ("comments", "comment", "num_reply", "reply"),
                    ),
                    "likes": self._metric(
                        open_tag,
                        row_html,
                        "data-likes",
                        ("recomd", "recommend", "likes"),
                    ),
                    "rank_position": len(rows) + 1,
                }
            )

        return rows[: self.max_items]

    def _build_items(
        self, rows: List[Dict[str, Any]], source: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for index, row in enumerate(rows, start=1):
            title = self._clean_text(row.get("title", ""))
            if not title:
                continue
            rank = self._int_or_none(row.get("rank_position")) or index
            link = self._normalize_link(row.get("link", ""))
            items.append(
                {
                    "keyword": title,
                    "title": title,
                    "link": link,
                    "url": link,
                    "summary": "",
                    "publisher": "루리웹",
                    "published_at": self._clean_text(row.get("published_at", "")),
                    "category": self._clean_text(row.get("category", "")),
                    "rank_position": rank,
                    "views": self._int_or_none(row.get("views")),
                    "comments": self._int_or_none(row.get("comments")),
                    "likes": self._int_or_none(row.get("likes")),
                    "source_id": "ruliweb",
                    "source_name": source.get("name", "Ruliweb"),
                    "source_type": source.get("type", "community"),
                    "tier": int(source.get("tier", 50) or 50),
                    "weight": int(source.get("weight", 0) or 0),
                    "base_score": max(95 - rank, 1),
                    "trend_reason": "Ruliweb fixture list collection",
                    "collection_method": "ruliweb_fixture_html",
                    "is_fallback": False,
                    "collected_at": datetime.now().isoformat(),
                }
            )
        return items

    def _dedupe(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_urls = set()
        seen_titles = set()
        deduped: List[Dict[str, Any]] = []
        for item in items:
            link = self._normalize_link(item.get("link", ""))
            title_key = self._clean_text(item.get("title", "")).casefold()
            if not title_key:
                continue
            if (link and link in seen_urls) or title_key in seen_titles:
                continue
            if link:
                seen_urls.add(link)
            seen_titles.add(title_key)
            item["rank_position"] = len(deduped) + 1
            item["base_score"] = max(95 - item["rank_position"], 1)
            deduped.append(item)
        return deduped

    def _save_cache(self, items: List[Dict[str, Any]]) -> None:
        if not items:
            return
        payload = {
            "source": "ruliweb",
            "updated_at": datetime.now().isoformat(),
            "items": items,
        }
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def _load_cache(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.cache_path.exists():
            return []
        try:
            with open(self.cache_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            updated_at = datetime.fromisoformat(str(payload.get("updated_at", "")))
            age = (datetime.now() - updated_at).total_seconds()
            if age < 0 or (
                self.cache_ttl_seconds > 0 and age > self.cache_ttl_seconds
            ):
                return []
            cached = payload.get("items", [])
            if not isinstance(cached, list):
                return []
        except Exception:
            return []

        items: List[Dict[str, Any]] = []
        for index, cached_item in enumerate(cached, start=1):
            if not isinstance(cached_item, dict):
                continue
            item = dict(cached_item)
            title = self._clean_text(item.get("title", item.get("keyword", "")))
            if not title:
                continue
            link = self._normalize_link(item.get("link", item.get("url", "")))
            rank = self._int_or_none(item.get("rank_position")) or index
            item.update(
                {
                    "keyword": title,
                    "title": title,
                    "link": link,
                    "url": link,
                    "summary": self._clean_text(item.get("summary", "")),
                    "publisher": "루리웹",
                    "published_at": self._clean_text(item.get("published_at", "")),
                    "category": self._clean_text(item.get("category", "")),
                    "rank_position": rank,
                    "views": self._int_or_none(item.get("views")),
                    "comments": self._int_or_none(item.get("comments")),
                    "likes": self._int_or_none(item.get("likes")),
                    "source_id": "ruliweb",
                    "source_name": source.get("name", "Ruliweb"),
                    "source_type": source.get("type", "community"),
                    "tier": int(source.get("tier", 50) or 50),
                    "weight": int(source.get("weight", 0) or 0),
                    "base_score": max(95 - rank, 1),
                    "trend_reason": "Ruliweb cache fallback",
                    "collection_method": "ruliweb_cache",
                    "is_fallback": True,
                    "collected_at": self._clean_text(
                        item.get("collected_at", datetime.now().isoformat())
                    ),
                }
            )
            items.append(item)
        return self._dedupe(items)[: self.max_items]

    def _set_success(self, items: List[Dict[str, Any]], method: str) -> None:
        self.last_status.update(
            {
                "success": True,
                "count": len(items),
                "collection_method": method,
                "service_diagnostic": self._diagnostic("", "ok"),
            }
        )

    def _title_anchor(self, row_html: str) -> Optional[Tuple[str, str]]:
        anchors = re.findall(
            r"<a\b([^>]*)>(.*?)</a>", row_html, flags=re.IGNORECASE | re.DOTALL
        )
        for attrs, content in anchors:
            href = self._attr(f"<a {attrs}>", "href")
            css_class = self._attr(f"<a {attrs}>", "class").lower()
            if (
                "subject" in css_class
                or "deco" in css_class
                or "title" in css_class
                or "/read/" in href
                or "/best/" in href
            ):
                title_match = re.search(
                    r"<(?:strong|span)[^>]*class=[\"'][^\"']*\btext_over\b[^\"']*[\"'][^>]*>(.*?)</(?:strong|span)>",
                    content,
                    flags=re.IGNORECASE | re.DOTALL,
                )
                title = self._clean_text(title_match.group(1) if title_match else content)
                if title:
                    return href, title
        return None

    def _cell_text(self, row_html: str, class_names: Tuple[str, ...]) -> str:
        for class_name in class_names:
            match = re.search(
                rf"<t[dh][^>]*class=[\"'][^\"']*\b{re.escape(class_name)}\b[^\"']*[\"'][^>]*>(.*?)</t[dh]>",
                row_html,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if match:
                return self._clean_text(match.group(1))
        return ""

    def _metric(
        self,
        open_tag: str,
        row_html: str,
        data_attr: str,
        class_names: Tuple[str, ...],
    ) -> Optional[int]:
        raw = self._attr(open_tag, data_attr) or self._cell_text(row_html, class_names)
        if not raw:
            for class_name in class_names:
                match = re.search(
                    rf"<span[^>]*class=[\"'][^\"']*\b{re.escape(class_name)}\b[^\"']*[\"'][^>]*>(.*?)</span>",
                    row_html,
                    flags=re.IGNORECASE | re.DOTALL,
                )
                if match:
                    raw = self._clean_text(match.group(1))
                    break
        return self._int_or_none(raw)

    def _fetch_url(self, url: str) -> Tuple[str, str]:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html,*/*;q=0.8"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            encoding = response.headers.get_content_charset() or "utf-8"
            return response.geturl(), response.read().decode(encoding, errors="ignore")

    def _attr(self, tag: str, name: str) -> str:
        match = re.search(
            rf"\b{re.escape(name)}\s*=\s*[\"']([^\"']*)[\"']",
            tag,
            flags=re.IGNORECASE,
        )
        return html.unescape(match.group(1).strip()) if match else ""

    def _clean_text(self, value: Any) -> str:
        text = html.unescape(str(value or ""))
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _normalize_link(self, value: Any) -> str:
        link = self._clean_text(value)
        if not link:
            return ""
        absolute = urljoin(f"{self.BASE_URL}/", link)
        return absolute if absolute.startswith(f"{self.BASE_URL}/") else ""

    def _int_or_none(self, value: Any) -> Optional[int]:
        text = self._clean_text(value).replace(",", "")
        match = re.search(r"-?\d+", text)
        if not match:
            return None
        try:
            return max(0, int(match.group(0)))
        except ValueError:
            return None

    def _classify_error(self, error: Exception) -> str:
        text = str(error).lower()
        if "timeout" in text or "timed out" in text:
            return "timeout"
        if "refused" in text:
            return "connection_refused"
        return "fixture_fetch_failed"

    def _primary_reason(self, failures: List[str]) -> str:
        for reason in (
            self.LIVE_REJECTION_REASON,
            "connection_refused",
            "timeout",
            "fixture_fetch_failed",
            "parse_failed",
        ):
            if reason in failures:
                return reason
        return failures[0] if failures else "no_results"

    def _diagnostic(self, reason: str, status: str) -> Dict[str, Any]:
        return self.service_diagnostic.build_diagnostic_from_reason(
            service="ruliweb", reason=reason, status=status
        )
