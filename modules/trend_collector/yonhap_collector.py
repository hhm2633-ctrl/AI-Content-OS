import html
import json
import re
import socket
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError

from modules.common.service_diagnostic import ServiceDiagnostic


class YonhapCollector:
    """Yonhap headline/list collector (live fetch is explicit policy-disabled by default)."""

    DEFAULT_CACHE_PATH = Path("storage/cache/yonhap_cache.json")
    DEFAULT_MAX_ITEMS = 30
    LIVE_REJECTION_REASON = "live_activation_not_approved"

    def __init__(
        self,
        timeout: int = 8,
        max_items: int = DEFAULT_MAX_ITEMS,
        config: Optional[Dict[str, Any]] = None,
        fetcher: Optional[Callable[[str], Tuple[str, str]]] = None,
        parser: Optional[Callable[[str], List[Dict[str, Any]]]] = None,
    ):
        self.timeout = timeout
        self.max_items = int(max_items)
        self.config = config or {}
        self.fetcher = fetcher or self._fetch_url
        self.parser = parser or self._parse_live_payload
        self.cache_ttl_seconds = int(self.config.get("cache_ttl_seconds", 24 * 60 * 60))
        self.retry_enabled = bool(self.config.get("retry_enabled", True))
        self.max_retries = max(0, int(self.config.get("max_retries", 2)))
        self.retry_count = 0
        self.service_diagnostic = ServiceDiagnostic()
        self.cache_path = Path(self.config.get("cache_path", self.DEFAULT_CACHE_PATH))
        self.last_status = self._empty_status()

    def _empty_status(self) -> Dict[str, Any]:
        return {
            "source": "yonhap",
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
            "retry_enabled": self.retry_enabled,
            "retry_count": 0,
            "service_diagnostic": {
                "service": "yonhap",
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

        failures: List[Dict[str, str]] = []
        parsed_items: List[Dict[str, Any]] = []
        self.retry_count = 0

        live_url = self._resolve_live_url(source)
        if live_url:
            parsed_items, failures = self._collect_live_items(live_url)
            self.retry_count = self.last_status.get("retry_count", 0)
        else:
            failures.append({"source": "policy", "reason": self.LIVE_REJECTION_REASON})

        if parsed_items:
            items = self._dedupe(self._build_items(parsed_items, source, "yonhap_live_parse", is_fallback=False))
            self._set_success_status(items, "yonhap_live_parse")
            self._save_cache(items)
            self._record_diagnostic()
            return items

        cache_items = self._load_cache(source)
        if cache_items:
            self.last_status["used_cache"] = True
            self.last_status["fallback_reason"] = (
                self._primary_failed_reason(failures) if failures else ""
            )
            self.last_status["collection_method"] = "yonhap_cache"
            self.last_status["success"] = True
            self.last_status["count"] = len(cache_items)
            self.last_status["retry_count"] = self.retry_count
            self.last_status["retry_enabled"] = self.retry_enabled
            self.last_status["failed_reason"] = ""
            self.last_status["final_error_type"] = self.last_status["fallback_reason"] or ""
            self._record_diagnostic()
            return cache_items

        self.last_status["failed_reason"] = self._primary_failed_reason(failures or [])
        self.last_status["final_error_type"] = self.last_status["failed_reason"] or "no_results"
        self.last_status["fallback_reason"] = self.last_status["failed_reason"]
        self.last_status["error_message"] = self.last_status["failed_reason"] or "no results"
        self.last_status["collection_method"] = "yonhap_no_data"
        self.last_status["retry_count"] = self.retry_count
        self.last_status["retry_enabled"] = self.retry_enabled
        self._record_diagnostic()
        return []

    def _collect_live_items(self, live_url: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
        errors: List[Dict[str, str]] = []
        attempts = 1 + (self.max_retries if self.retry_enabled else 0)

        for attempt in range(attempts):
            try:
                _, raw_payload = self.fetcher(live_url)
                rows = self.parser(raw_payload)
                if rows:
                    return rows, []
                errors.append({"source": "live", "reason": "malformed_fixture"})
            except Exception as error:
                errors.append({"source": "live", "reason": self._classify_error(error)})

            if attempt < attempts - 1:
                self.retry_count += 1
                delay = self._retry_delay(attempt)
                if delay > 0:
                    time.sleep(delay)

        return [], errors

    def _resolve_live_url(self, source: Dict[str, Any]) -> str:
        if not bool(self.config.get("allow_live_fetch", False)):
            return ""

        live_url = str(self.config.get("yonhap_live_url", "")).strip()
        if live_url:
            return live_url

        source_url = str(source.get("url", "")).strip()
        if source_url.rstrip("/") == "https://www.yna.co.kr":
            return "https://www.yna.co.kr/"
        return ""

    def _retry_delay(self, retry_index: int) -> float:
        backoff_seconds = [0.2, 0.5, 1.0]
        try:
            return max(0.0, float(backoff_seconds[retry_index]))
        except Exception:
            return 0.0

    def _parse_live_payload(self, raw_payload: str) -> List[Dict[str, Any]]:
        normalized = self._safe_text(raw_payload)
        if not normalized:
            return []

        payload = self._load_json_payload(normalized) or {}

        if not isinstance(payload, dict):
            return []

        candidates: List[Any] = []
        for key in ("items", "articles", "headlines", "data", "results", "rows"):
            value = payload.get(key)
            if isinstance(value, list) and value:
                candidates = value
                break

        if not candidates and "pageProps" in payload:
            page_props = payload.get("pageProps")
            if isinstance(page_props, dict):
                for key in ("items", "articles", "headlines", "data", "results"):
                    value = page_props.get(key)
                    if isinstance(value, list) and value:
                        candidates = value
                        break

        if not candidates and "props" in payload and isinstance(payload["props"], dict):
            page_props = payload["props"].get("pageProps")
            if isinstance(page_props, dict):
                for key in ("items", "articles", "headlines", "data", "results"):
                    value = page_props.get(key)
                    if isinstance(value, list) and value:
                        candidates = value
                        break

        if not candidates:
            return self._parse_public_homepage_links(normalized)

        rows: List[Dict[str, Any]] = []
        for index, item in enumerate(candidates[: self.max_items], start=1):
            if not isinstance(item, dict):
                continue
            row = self._normalize_row(item, index)
            if row.get("title"):
                rows.append(row)
        return rows

    def _parse_public_homepage_links(self, raw_html: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        seen_links = set()

        for article_match in re.finditer(
            r'<article\b[^>]*>(.*?)</article>',
            raw_html,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            article_html = article_match.group(1)
            title_match = re.search(
                r'<a\b[^>]*href=["\'](https://www\.yna\.co\.kr/view/AKR\d+[^"\']*)["\']'
                r'[^>]*class=["\'][^"\']*tit-news[^"\']*["\'][^>]*>(.*?)</a>',
                article_html,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if not title_match:
                continue
            link = html.unescape(title_match.group(1)).strip()
            title = self._normalize_text(title_match.group(2))
            if not title or link in seen_links:
                continue
            lead_match = re.search(
                r'<p\b[^>]*class=["\'][^"\']*lead[^"\']*["\'][^>]*>(.*?)</p>',
                article_html,
                flags=re.IGNORECASE | re.DOTALL,
            )
            section_match = re.search(r"[?&]section=([^&]+)", link)
            seen_links.add(link)
            rows.append(
                {
                    "title": title,
                    "link": link,
                    "summary": self._normalize_text(lead_match.group(1)) if lead_match else "",
                    "published_at": "",
                    "category": section_match.group(1).split("/", 1)[0] if section_match else "",
                    "rank_position": len(rows) + 1,
                }
            )

        for match in re.finditer(
            r'<a\b[^>]*href=["\'](https://www\.yna\.co\.kr/view/AKR\d+[^"\']*)["\'][^>]*>(.*?)</a>',
            raw_html,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            link = html.unescape(match.group(1)).strip()
            title = self._normalize_text(match.group(2))
            if not title or len(title) < 8 or link in seen_links:
                continue
            seen_links.add(link)
            section_match = re.search(r"[?&]section=([^&]+)", link)
            rows.append(
                {
                    "title": title,
                    "link": link,
                    "summary": "",
                    "published_at": "",
                    "category": section_match.group(1).split("/", 1)[0] if section_match else "",
                    "rank_position": len(rows) + 1,
                }
            )
            if len(rows) >= self.max_items:
                break
        return rows

    def _normalize_row(self, item: Dict[str, Any], rank_position: int) -> Dict[str, Any]:
        title = self._first_text(item, ("title", "headline", "headline_title"))
        if not title:
            return {}

        raw_link = self._first_text(item, ("url", "link", "href", "canonical_link"))
        link = self._normalize_link(raw_link)

        published_at = self._first_text(
            item,
            (
                "published_at",
                "published",
                "time",
                "pub_date",
                "publish_time",
                "published_at_text",
            ),
        )
        category = self._first_text(item, ("category", "section", "board"))
        rank_value = self._coerce_int(self._first_text(item, ("rank_position", "rank", "position", "idx", "order")))
        rank_position = rank_value if rank_value is not None else rank_position

        return {
            "title": title,
            "link": link,
            "published_at": published_at,
            "category": category or "",
            "rank_position": int(rank_position),
        }

    def _build_items(
        self,
        rows: List[Dict[str, Any]],
        source: Dict[str, Any],
        collection_method: str,
        is_fallback: bool,
    ) -> List[Dict[str, Any]]:
        built = []
        source_id = str(source.get("source_id", "yonhap"))
        source_name = str(source.get("name") or source.get("source_name") or "연합뉴스")
        source_type = str(source.get("type", "news_wire"))
        tier = int(source.get("tier", 1))
        weight = int(source.get("weight", 20))

        for index, row in enumerate(rows, start=1):
            title = self._normalize_text(row.get("title", ""))
            if not title:
                continue

            link = self._normalize_link(row.get("link", ""))
            rank = self._coerce_int(row.get("rank_position"), default=index) or index
            built.append(
                {
                    "keyword": title,
                    "title": title,
                    "link": link,
                    "url": link,
                    "summary": self._normalize_text(row.get("summary", "")),
                    "publisher": "연합뉴스",
                    "published_at": self._normalize_text(row.get("published_at", "")),
                    "category": self._normalize_text(row.get("category", "")),
                    "rank_position": int(rank),
                    "source_id": source_id,
                    "source_name": source_name,
                    "source_type": source_type,
                    "tier": tier,
                    "weight": weight,
                    "base_score": max(95 - int(rank), 1),
                    "trend_reason": f"연합뉴스 수집({collection_method})",
                    "collection_method": collection_method,
                    "is_fallback": is_fallback,
                    "collected_at": datetime.now().isoformat(),
                }
            )

        return built

    def _dedupe(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_urls = set()
        seen_titles = set()
        deduped: List[Dict[str, Any]] = []

        for item in items:
            link = self._normalize_link(item.get("link", ""))
            title_key = self._normalize_text(item.get("title", "")).casefold()
            if not title_key:
                continue

            # Canonical URL has first priority, then normalized title catches
            # the same headline published under distinct list URLs.
            if (link and link in seen_urls) or title_key in seen_titles:
                continue

            if link:
                seen_urls.add(link)
            seen_titles.add(title_key)
            deduped.append(item)

        ranked = []
        for index, item in enumerate(deduped, start=1):
            item["rank_position"] = index
            item["base_score"] = max(95 - index, 1)
            ranked.append(item)

        return ranked[: self.max_items]

    def _set_success_status(self, items: List[Dict[str, Any]], method: str) -> None:
        self.last_status["success"] = bool(items)
        self.last_status["count"] = len(items)
        self.last_status["collection_method"] = method
        self.last_status["used_cache"] = False
        self.last_status["fallback_reason"] = ""
        self.last_status["final_error_type"] = ""
        self.last_status["failed_reason"] = ""
        self.last_status["retry_count"] = self.retry_count
        self.last_status["retry_enabled"] = self.retry_enabled

    def _load_cache(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.cache_path.exists():
            return []

        try:
            with open(self.cache_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            return []

        if not isinstance(payload, dict):
            return []

        updated_at = self._coerce_time(payload.get("updated_at"))
        if not self._is_cache_valid(updated_at):
            return []

        items = payload.get("items", [])
        if not isinstance(items, list):
            return []

        rows = []
        for item in items:
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "title": self._normalize_text(item.get("title", "")),
                    "link": self._normalize_link(item.get("link", item.get("url", ""))),
                    "summary": self._normalize_text(item.get("summary", "")),
                    "published_at": self._normalize_text(item.get("published_at", "")),
                    "category": self._normalize_text(item.get("category", "")),
                    "rank_position": self._coerce_int(item.get("rank_position"), default=1),
                }
            )

        return self._dedupe(
            self._build_items(rows, source, "yonhap_cache", is_fallback=True)
        )

    def _save_cache(self, items: List[Dict[str, Any]]) -> None:
        if not items:
            return

        payload = {
            "source": "yonhap",
            "updated_at": datetime.now().isoformat(),
            "items": [
                {
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "summary": item.get("summary", ""),
                    "published_at": item.get("published_at", ""),
                    "category": item.get("category", ""),
                    "rank_position": item.get("rank_position", 0),
                    "publisher": item.get("publisher", "연합뉴스"),
                }
                for item in items
            ],
        }

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def _is_cache_valid(self, updated_at: Optional[datetime]) -> bool:
        if self.cache_ttl_seconds <= 0:
            return True
        if not updated_at:
            return False
        age_seconds = (datetime.now() - updated_at).total_seconds()
        if age_seconds < 0:
            return False
        return age_seconds <= self.cache_ttl_seconds

    def _fetch_url(self, url: str) -> Tuple[str, str]:
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

    def _load_json_payload(self, raw_payload: str) -> Optional[Dict[str, Any]]:
        html_candidate = self._safe_text(raw_payload)
        try:
            parsed = json.loads(html_candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        match = re.search(
            r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
            html_candidate,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return None

        candidate = self._safe_text(match.group(1))
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None

        return None

    def _coerce_time(self, value: Any) -> Optional[datetime]:
        if not value:
            return None
        try:
            if isinstance(value, datetime):
                return value
            return datetime.fromisoformat(str(value))
        except Exception:
            return None

    def _record_diagnostic(self) -> None:
        try:
            used_cache = bool(self.last_status.get("used_cache", False))
            has_failure = bool(
                self.last_status.get("failed_reason")
                or self.last_status.get("fallback_reason")
                or self.last_status.get("final_error_type")
            )
            if self.last_status.get("success") and not (has_failure or used_cache):
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="yonhap",
                    reason="",
                    status="ok",
                )
            else:
                reason = self.last_status.get("failed_reason") or self.last_status.get("fallback_reason")
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="yonhap",
                    reason=reason or self.LIVE_REJECTION_REASON,
                    status="fallback_used",
                )
                self.service_diagnostic.record(diagnostic)

            self.last_status["service_diagnostic"] = diagnostic
        except Exception as error:
            print(f"Yonhap Service Diagnostic Failed: {error}")

    def _first_text(self, data: Dict[str, Any], keys: tuple) -> str:
        for key in keys:
            value = data.get(key)
            if value is None:
                continue
            cleaned = self._normalize_text(value)
            if cleaned:
                return cleaned
        return ""

    def _normalize_text(self, value: Any) -> str:
        if value is None:
            return ""
        text = str(value)
        text = re.sub(r"<script.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<.*?>", " ", text)
        text = html.unescape(text)
        text = text.replace("\n", " ").replace("\t", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _safe_text(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value)

    def _normalize_link(self, value: Any) -> str:
        text = self._normalize_text(value)
        if not text:
            return ""
        if text.startswith("//"):
            return f"https:{text}"
        if text.startswith("/"):
            return f"https://www.yna.co.kr{text}"
        if text.startswith("http://") or text.startswith("https://"):
            return text
        return ""

    def _coerce_int(self, value: Any, default: Optional[int] = None) -> Optional[int]:
        try:
            as_text = self._normalize_text(value)
            if as_text.isdigit():
                return int(as_text)
        except Exception:
            return default
        return default

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
            if isinstance(reason, socket.timeout):
                return "timeout"
            if isinstance(reason, ConnectionRefusedError):
                return "connection_refused"
            text = str(reason).lower()
            if "timed out" in text or "timeout" in text:
                return "timeout"
            if "forbidden" in text or "403" in text:
                return "http_403_forbidden"
            if "refused" in text or "10061" in text:
                return "connection_refused"
            return "network_error"
        return "unknown_error"

    def _primary_failed_reason(self, failures: List[Dict[str, str]]) -> str:
        if not failures:
            return "no_results"
        priorities = [
            self.LIVE_REJECTION_REASON,
            "http_403_forbidden",
            "connection_refused",
            "timeout",
            "network_error",
            "malformed_fixture",
            "unknown_error",
            "no_results",
        ]
        reasons = [entry.get("reason", "unknown_error") for entry in failures]
        for reason in priorities:
            if reason in reasons:
                return reason
        return reasons[0] if reasons else "no_results"
