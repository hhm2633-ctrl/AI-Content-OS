import html
import json
import re
import socket
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin

from modules.common.service_diagnostic import ServiceDiagnostic


class News1Collector:
    """Low-cost News1 collector using `__NEXT_DATA__` first and HTML fallback.

    Scope is strict:
    - collects only fields directly exposed by list payloads or verified fallback selectors
    - parser/network failures are non-fatal
    - fallback chain: live parse -> cache -> settings keyword -> placeholder
    """

    def __init__(self, timeout: int = 8, max_items: int = 30, config: Optional[Dict[str, Any]] = None):
        self.timeout = timeout
        self.max_items = max_items
        self.config = config or {}
        self.cache_path = Path("storage/cache/news1_cache.json")
        self.service_diagnostic = ServiceDiagnostic()
        self.last_status = self._empty_status()

    def _empty_status(self) -> Dict[str, Any]:
        return {
            "source": "news1",
            "attempted": False,
            "success": False,
            "count": 0,
            "error_message": "",
            "failed_reason": "",
            "fallback_reason": "",
            "final_error_type": "",
            "collection_method": "",
            "used_cache": False,
            "cache_path": str(self.cache_path).replace("\\", "/"),
            "service_diagnostic": {
                "service": "news1",
                "status": "ok",
                "error_type": "",
                "safe_message": "",
                "api_key_present": None,
            },
        }

    def collect(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.last_status = self._empty_status()
        self.last_status["attempted"] = True
        self.last_status["cache_path"] = str(self.cache_path).replace("\\", "/")

        collected: List[Dict[str, Any]] = []
        parsed_payload = []
        primary_errors: List[Dict[str, str]] = []
        fallback_source_url = self._normalize_source_url(source.get("url", ""))

        try:
            fetched_url, raw_html = self._fetch_url(fallback_source_url)
            parsed_payload = self._extract_from_html(raw_html, fetched_url)
        except Exception as error:
            primary_errors.append({"reason": self._classify_error(error), "message": str(error)})
            raw_html = ""

        parsed_items = self._build_items_from_payload(parsed_payload, source)
        if parsed_items:
            collected.extend(parsed_items)
            self.last_status["success"] = True
            self.last_status["count"] = len(collected)
            self.last_status["collection_method"] = (
                parsed_payload[0].get("collection_method", "news1_next_data")
                if parsed_items
                else "news1_next_data"
            )
            self._save_cache(parsed_items)
            self._record_diagnostic()
            return collected

        if raw_html:
            html_items = self._extract_from_html_fallback(raw_html)
            if html_items:
                collected.extend(self._build_items_from_payload(html_items, source, "news1_html_fallback"))
                if collected:
                    self.last_status["success"] = True
                    self.last_status["count"] = len(collected)
                    self.last_status["collection_method"] = "news1_html_fallback"
                    self._save_cache(collected)
                    self._record_diagnostic()
                    return collected

        if collected:
            self.last_status["success"] = True
            self.last_status["count"] = len(collected)
            self._record_diagnostic()
            return collected

        cached = self._load_cache(source)
        if cached:
            self.last_status["used_cache"] = True
            self.last_status["collection_method"] = "news1_cache"
            self.last_status["count"] = len(cached)
            self.last_status["failed_reason"] = self._primary_failed_reason(primary_errors)
            self.last_status["final_error_type"] = self.last_status["failed_reason"]
            self.last_status["fallback_reason"] = self._primary_failed_reason(primary_errors)
            self._record_diagnostic()
            return cached

        fallback_reason = self._primary_failed_reason(primary_errors)
        settings_items = self._build_settings_fallback(source, fallback_reason)
        if settings_items:
            self.last_status["collection_method"] = "news1_settings_fallback"
            self.last_status["fallback_reason"] = fallback_reason
            self.last_status["count"] = len(settings_items)
            self.last_status["error_message"] = self.last_status["fallback_reason"]
            self._record_diagnostic()
            return settings_items

        placeholder_items = self._build_placeholder_fallback(source, fallback_reason)
        self.last_status["collection_method"] = "news1_placeholder_fallback"
        self.last_status["fallback_reason"] = fallback_reason
        self.last_status["count"] = len(placeholder_items)
        self._record_diagnostic()
        return placeholder_items

    def _normalize_source_url(self, source_url: str) -> str:
        url = str(source_url or "").strip()
        if not url:
            return "https://www.news1.kr/latest"

        if url.endswith("/latest") or url.endswith("/trend") or url.endswith("/latest/") or url.endswith("/trend/"):
            return url

        if "news1.kr" not in url:
            return "https://www.news1.kr/latest"

        return "https://www.news1.kr/latest"

    def _fetch_url(self, url: str):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return response.geturl(), response.read().decode("utf-8", errors="ignore")

    def _extract_from_html(self, raw_html: str, fetched_url: str) -> List[Dict[str, Any]]:
        payload = self._extract_next_data(raw_html)
        if not isinstance(payload, dict):
            return []

        page_props = payload.get("props", {}).get("pageProps")
        if not isinstance(page_props, dict):
            return []

        items = self._select_item_list(page_props, fetched_url)
        if not isinstance(items, list):
            return []

        results: List[Dict[str, Any]] = []
        for index, item in enumerate(items[: self.max_items], start=1):
            if not isinstance(item, dict):
                continue
            title = self._clean_text(item.get("title", ""))
            if not title:
                continue

            results.append(
                {
                    "title": title,
                    "url": self._normalize_article_url(item.get("url", "")),
                    "category": self._clean_text(item.get("section", "")) or self._derive_category(fetched_url),
                    "rank_position": index,
                    "publisher": "뉴스1",
                    "time": self._clean_text(item.get("pubdate", "")),
                    "summary": self._clean_text(item.get("summary", "")),
                    "collection_method": "news1_next_data",
                }
            )

        return results

    def _select_item_list(self, page_props: Dict[str, Any], fetched_url: str) -> List[Any]:
        path = fetched_url.lower()
        if "/trend" in path:
            value = page_props.get("data")
            if isinstance(value, list):
                return value
        if "/latest" in path:
            value = page_props.get("data")
            if isinstance(value, list):
                return value

        for key in ("subsectionData", "sectionTop", "data"):
            value = page_props.get(key)
            if isinstance(value, list):
                return value

        return []

    def _extract_next_data(self, raw_html: str) -> Dict[str, Any]:
        match = re.search(
            r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            raw_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return {}

        text = match.group(1).strip()
        if not text:
            return {}

        try:
            return json.loads(text)
        except Exception:
            return {}

    def _extract_from_html_fallback(self, raw_html: str) -> List[Dict[str, str]]:
        if not raw_html:
            return []

        entries = []
        container_pattern = re.compile(
            r'<div[^>]*class="[^"]*row-bottom-border-2[^"]*"[^>]*>(.*?)</div>\s*</div>',
            flags=re.IGNORECASE | re.DOTALL,
        )
        for container in container_pattern.findall(raw_html):
            title_match = re.search(
                r'<h2[^>]*class="[^"]*n1-header-title-1-2[^"]*"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>\s*</h2>',
                container,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if not title_match:
                continue
            entry: Dict[str, str] = {
                "title": self._clean_text(title_match.group(2)),
                "url": self._normalize_article_url(title_match.group(1)),
                "summary": "",
                "category": "",
                "publisher": "",
                "time": "",
                "collection_method": "news1_html_fallback",
            }
            if entry["title"]:
                summary_match = re.search(
                    r'<span[^>]*class="[^"]*n1-header-desc-1[^"]*"[^>]*>(.*?)</span>',
                    container,
                    flags=re.IGNORECASE | re.DOTALL,
                )
                if summary_match:
                    entry["summary"] = self._clean_text(summary_match.group(1))

                author_matches = re.findall(
                    r"<span[^>]*>(.*?)</span>",
                    container,
                    flags=re.IGNORECASE | re.DOTALL,
                )
                if author_matches:
                    entry["publisher"] = self._clean_text(author_matches[-1])

                entries.append(entry)

        return entries

    def _build_items_from_payload(
        self,
        payload_items: List[Dict[str, Any]],
        source: Dict[str, Any],
        collection_method: str = "news1_next_data",
    ) -> List[Dict[str, Any]]:
        results = []
        for item in payload_items:
            if not isinstance(item, dict):
                continue
            title = self._clean_text(item.get("title", ""))
            if not title:
                continue

            item_url = self._normalize_article_url(item.get("url", ""))
            if not item_url:
                continue

            rank = item.get("rank_position")
            if not isinstance(rank, int):
                if str(rank).strip().isdigit():
                    rank = int(str(rank).strip())
                else:
                    rank = len(results) + 1

            publisher = item.get("publisher") or "뉴스1"
            item_time = item.get("time") or item.get("published_at") or ""

            item_payload = {
                "keyword": title,
                "title": title,
                "link": item_url,
                "url": item_url,
                "summary": self._clean_text(item.get("summary", "")),
                "category": self._clean_text(item.get("category", "")),
                "rank_position": int(rank),
                "publisher": self._clean_text(str(publisher)),
                "published_at": self._clean_text(item_time),
                "collection_method": item.get("collection_method", collection_method),
                "is_fallback": collection_method.endswith("fallback"),
                "source_id": source.get("source_id", "news1"),
                "source_name": source.get("name", "뉴스1"),
                "source_type": source.get("type", "news_wire"),
                "tier": int(source.get("tier", 1)),
                "weight": int(source.get("weight", 30)),
                "base_score": max(90 - int(rank), 1),
                "trend_reason": f"News1 {_derive_collection_reason(collection_method)}",
                "collected_at": datetime.now().isoformat(),
            }
            results.append(item_payload)

        return results

    def _build_settings_fallback(self, source: Dict[str, Any], fallback_reason: str) -> List[Dict[str, Any]]:
        fallback_sources = self.config.get("trend_sources", [])
        if not fallback_sources:
            fallback_sources = [source.get("name", "뉴스1"), "정치", "경제"]

        items = []
        for index, keyword in enumerate(fallback_sources[:3], start=1):
            items.append(
                {
                    "keyword": str(keyword),
                    "title": str(keyword),
                    "link": "",
                    "url": "",
                    "summary": "",
                    "category": "",
                    "rank_position": index,
                    "publisher": "",
                    "published_at": "",
                    "collection_method": "news1_settings_fallback",
                    "is_fallback": True,
                    "trend_reason": f"News1 settings fallback: {fallback_reason}",
                    "source_id": "news1",
                    "source_name": source.get("name", "뉴스1"),
                    "source_type": source.get("type", "news_wire"),
                    "tier": int(source.get("tier", 1)),
                    "weight": int(source.get("weight", 30)),
                    "base_score": max(85 - index, 1),
                    "collected_at": datetime.now().isoformat(),
                }
            )
        return items

    def _build_placeholder_fallback(self, source: Dict[str, Any], fallback_reason: str) -> List[Dict[str, Any]]:
        placeholders = ["최신 뉴스", "경제 동향", "사회 이슈"]
        items = []
        for index, keyword in enumerate(placeholders, start=1):
            items.append(
                {
                    "keyword": keyword,
                    "title": keyword,
                    "link": "",
                    "url": "",
                    "summary": "",
                    "category": "",
                    "rank_position": index,
                    "publisher": "",
                    "published_at": "",
                    "collection_method": "news1_placeholder_fallback",
                    "is_fallback": True,
                    "trend_reason": f"News1 placeholder fallback: {fallback_reason}",
                    "source_id": "news1",
                    "source_name": source.get("name", "뉴스1"),
                    "source_type": source.get("type", "news_wire"),
                    "tier": int(source.get("tier", 1)),
                    "weight": int(source.get("weight", 30)),
                    "base_score": max(80 - index, 1),
                    "collected_at": datetime.now().isoformat(),
                }
            )
        return items

    def _save_cache(self, items: List[Dict[str, Any]]) -> None:
        try:
            payload = {
                "source": "news1",
                "updated_at": datetime.now().isoformat(),
                "items": [
                    {
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "category": item.get("category"),
                        "rank_position": item.get("rank_position"),
                        "publisher": item.get("publisher"),
                        "published_at": item.get("published_at"),
                    }
                    for item in items
                ],
            }
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_cache(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.cache_path.exists():
            return []

        try:
            with open(self.cache_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            return []

        items = data.get("items", [])
        if not isinstance(items, list):
            return []

        results = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            title = self._clean_text(item.get("title", ""))
            link = self._normalize_article_url(item.get("url", ""))
            if not title or not link:
                continue

            results.append(
                {
                    "keyword": title,
                    "title": title,
                    "link": link,
                    "url": link,
                    "summary": "",
                    "category": self._clean_text(item.get("category", "")),
                    "rank_position": int(item.get("rank_position", index)),
                    "publisher": self._clean_text(item.get("publisher", "뉴스1")),
                    "published_at": self._clean_text(item.get("published_at", "")),
                    "collection_method": "news1_cache",
                    "is_fallback": True,
                    "trend_reason": "News1 cache fallback",
                    "source_id": "news1",
                    "source_name": source.get("name", "뉴스1"),
                    "source_type": source.get("type", "news_wire"),
                    "tier": int(source.get("tier", 1)),
                    "weight": int(source.get("weight", 30)),
                    "base_score": max(80 - index, 1),
                    "collected_at": datetime.now().isoformat(),
                }
            )
        return results

    def _derive_category(self, fetched_url: str) -> str:
        for segment in str(fetched_url).split("/"):
            if segment and segment not in {"", "https:", "www.news1.kr", "latest", "trend"}:
                return segment
        return ""

    def _normalize_article_url(self, value: Any) -> str:
        text = self._clean_text(value)
        if not text:
            return ""

        if text.startswith("//"):
            return f"https:{text}"
        if text.startswith("/"):
            return urljoin("https://www.news1.kr", text)
        if text.startswith("http://") or text.startswith("https://"):
            return text

        return ""

    def _clean_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        text = re.sub(r"<script.*?</script>", "", str(text), flags=re.DOTALL)
        text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<.*?>", " ", text)
        text = html.unescape(text)
        text = text.replace("\n", " ").replace("\t", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _primary_failed_reason(self, errors: List[Dict[str, str]]) -> str:
        if not errors:
            return "unknown_error"
        priorities = [
            "http_403_forbidden",
            "connection_refused",
            "timeout",
            "network_error",
            "parse_failed",
            "empty_result",
            "no_results",
            "unknown_error",
        ]
        reasons = [item.get("reason", "unknown_error") for item in errors]
        for reason in priorities:
            if reason in reasons:
                return reason
        return reasons[0]

    def _classify_error(self, error: Exception) -> str:
        if isinstance(error, HTTPError):
            if error.code == 403:
                return "http_403_forbidden"
            return f"http_{error.code}"

        if isinstance(error, TimeoutError):
            return "timeout"

        if isinstance(error, URLError):
            reason = getattr(error, "reason", "")
            if isinstance(reason, TimeoutError):
                return "timeout"
            if isinstance(reason, ConnectionRefusedError):
                return "connection_refused"
            if isinstance(reason, socket.timeout):
                return "timeout"
            reason_text = str(reason).lower()
            if "timed out" in reason_text or "timeout" in reason_text:
                return "timeout"
            if "forbidden" in reason_text or "403" in reason_text:
                return "http_403_forbidden"
            if "refused" in reason_text or "10061" in reason_text:
                return "connection_refused"
            return "network_error"

        return "unknown_error"

    def _record_diagnostic(self) -> None:
        try:
            if self.last_status.get("success"):
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="news1",
                    reason="",
                    status="ok",
                )
                self.last_status["service_diagnostic"] = diagnostic
                return

            diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                service="news1",
                reason=self.last_status.get("failed_reason", "unknown_error"),
                status="fallback_used",
            )
            self.last_status["service_diagnostic"] = diagnostic
            self.service_diagnostic.record(diagnostic)
        except Exception as error:
            print(f"News1 Service Diagnostic Failed: {error}")


def _derive_collection_reason(collection_method: str) -> str:
    if collection_method.startswith("news1_html"):
        return "html fallback"
    if collection_method.endswith("cache"):
        return "cache fallback"
    if collection_method.endswith("settings_fallback"):
        return "settings fallback"
    if collection_method.endswith("placeholder_fallback"):
        return "placeholder fallback"
    return "live collect"
