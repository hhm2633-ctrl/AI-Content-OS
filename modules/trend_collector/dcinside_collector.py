import html
import json
import re
import socket
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError

from modules.common.service_diagnostic import ServiceDiagnostic
from modules.trend_collector.dcinside_parser import DcinsideParser


class DcinsideCollector:
    """Dcinside collector for synthetic fixtures with optional bounded live fallback."""

    LIVE_REJECTION_REASON = "live_activation_not_approved"
    MALFORMED_FIXTURE_REASON = "malformed_fixture"
    DEFAULT_CACHE_PATH = Path("storage/cache/dcinside_cache.json")
    DEFAULT_MAX_ITEMS = 30
    DEFAULT_CACHE_TTL_SECONDS = 24 * 60 * 60
    DEFAULT_MAX_RETRIES = 2

    def __init__(
        self,
        timeout: int = 8,
        max_items: int = DEFAULT_MAX_ITEMS,
        config: Optional[Dict[str, Any]] = None,
        fetcher: Optional[Callable[[str], Tuple[str, str]]] = None,
        parser: Optional[Callable[[str, str], List[Dict[str, Any]]]] = None,
    ):
        self.timeout = timeout
        self.max_items = int(max_items)
        self.config = config or {}
        self.fetcher = fetcher or self._fetch_url
        self.parser = parser or DcinsideParser().parse_board_list_payload
        self.cache_ttl_seconds = int(self.config.get("cache_ttl_seconds", self.DEFAULT_CACHE_TTL_SECONDS))
        self.retry_enabled = bool(self.config.get("retry_enabled", True))
        self.max_retries = max(
            0, min(int(self.config.get("max_retries", self.DEFAULT_MAX_RETRIES)), 3)
        )
        self.retry_count = 0
        self.service_diagnostic = ServiceDiagnostic()
        self.cache_path = Path(self.config.get("cache_path", self.DEFAULT_CACHE_PATH))
        self.last_status = self._empty_status()

    def _empty_status(self) -> Dict[str, Any]:
        return {
            "source": "dcinside",
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
            "service_diagnostic": {
                "service": "dcinside",
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
        self.last_status["retry_enabled"] = self.retry_enabled
        self.last_status["retry_count"] = 0

        board_id = self._resolve_board_id(source)
        live_url = self._resolve_live_url(source)

        failures: List[Dict[str, str]] = []
        parsed_rows: List[Dict[str, Any]] = []

        if live_url:
            parsed_rows, failures = self._collect_live(board_id, live_url)
            self.retry_count = self.last_status.get("retry_count", 0)
        else:
            failures.append({"reason": self.LIVE_REJECTION_REASON})

        if parsed_rows:
            items = self._build_items(parsed_rows, source, "dcinside_board_parse", is_fallback=False)
            items = self._dedupe(items)
            if items:
                self.last_status["success"] = True
                self.last_status["count"] = len(items)
                self.last_status["collection_method"] = "dcinside_board_parse"
                self.last_status["used_cache"] = False
                self.last_status["failed_reason"] = ""
                self.last_status["fallback_reason"] = ""
                self.last_status["final_error_type"] = ""
                self.last_status["retry_count"] = self.retry_count
                self._save_cache(items)
                self._record_diagnostic()
                return items

        cache_items = self._load_cache(source)
        if cache_items:
            self.last_status["used_cache"] = True
            self.last_status["collection_method"] = "dcinside_cache"
            self.last_status["count"] = len(cache_items)
            self.last_status["success"] = True
            self.last_status["retry_count"] = self.retry_count
            self.last_status["failed_reason"] = self._primary_failed_reason(failures)
            self.last_status["fallback_reason"] = self._primary_failed_reason(failures)
            self.last_status["final_error_type"] = self.last_status["failed_reason"] or "no_results"
            self._record_diagnostic()
            return cache_items

        self.last_status["failed_reason"] = self._primary_failed_reason(failures)
        self.last_status["final_error_type"] = self.last_status["failed_reason"] or "no_results"
        self.last_status["fallback_reason"] = self.last_status["final_error_type"]
        self.last_status["collection_method"] = "dcinside_no_data"
        self.last_status["retry_count"] = self.retry_count
        self.last_status["count"] = 0
        self._record_diagnostic()
        return []

    def _resolve_board_id(self, source: Dict[str, Any]) -> str:
        board_id = str(source.get("board_id", "")).strip()
        if board_id:
            return board_id
        if str(source.get("url", "")).strip().rstrip("/") == "https://www.dcinside.com":
            return "dcbest"
        return ""

    def _resolve_live_url(self, source: Dict[str, Any]) -> str:
        if not self.config.get("allow_live_fetch"):
            return ""

        live_url = str(self.config.get("dcinside_live_url", "")).strip()
        if live_url:
            return live_url

        source_url = str(source.get("url", "")).strip()
        if source_url.rstrip("/") == "https://www.dcinside.com":
            return "https://www.dcinside.com/"

        # Do not infer arbitrary gallery URLs from unapproved source data.
        return ""

    def _collect_live(self, board_id: str, live_url: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
        errors: List[Dict[str, str]] = []
        rows: List[Dict[str, Any]] = []
        attempts = 1 + (self.max_retries if self.retry_enabled else 0)

        for attempt in range(attempts):
            try:
                _, raw_html = self.fetcher(live_url)
                parsed = self._safe_parse_board_payload(board_id, raw_html)
                if parsed:
                    return parsed, []
                errors.append({"reason": self.MALFORMED_FIXTURE_REASON})
            except Exception as error:
                errors.append({"reason": self._classify_error(error), "message": str(error)})

            if attempt < attempts - 1:
                self.retry_count += 1
                delay = self._retry_delay(attempt)
                if delay > 0:
                    time.sleep(delay)

        return [], errors

    def _safe_parse_board_payload(self, board_id: str, raw_payload: str) -> List[Dict[str, Any]]:
        if not raw_payload or not board_id:
            return []

        parsed_rows = self.parser(board_id=board_id, raw_html=raw_payload)
        if not isinstance(parsed_rows, list):
            return []

        rows: List[Dict[str, Any]] = []
        for index, item in enumerate(parsed_rows[: self.max_items], start=1):
            if not isinstance(item, dict):
                continue

            title = self._clean_text(item.get("title", ""))
            if not title:
                continue

            link = self._normalize_link(item.get("url", ""))
            published_at = self._clean_text(item.get("posted_at", item.get("published_at", "")))

            rows.append(
                {
                    "title": title,
                    "link": link,
                    "published_at": published_at,
                    "rank_position": int(item.get("rank", index)) if isinstance(item.get("rank", index), int) else index,
                    "category": self._clean_text(item.get("board_id", board_id)),
                    "source_id": "dcinside",
                    "source_name": "dcinside",
                    "source_type": "community",
                    "views": self._coerce_optional_int(item.get("views")),
                    "comments": self._coerce_optional_int(item.get("comments")),
                    "likes": self._coerce_optional_int(item.get("recommends")),
                }
            )

        return rows

    def _build_items(
        self,
        rows: List[Dict[str, Any]],
        source: Dict[str, Any],
        collection_method: str,
        is_fallback: bool,
    ) -> List[Dict[str, Any]]:
        source_id = str(source.get("source_id", "dcinside"))
        source_name = str(source.get("name", source.get("source_name", "디씨인사이드")))
        source_type = str(source.get("type", "community"))
        tier = int(source.get("tier", 1))
        weight = int(source.get("weight", 20))
        base_rank = 0

        items: List[Dict[str, Any]] = []
        for row in rows:
            base_rank += 1
            title = self._clean_text(row.get("title", ""))
            if not title:
                continue

            link = self._normalize_link(row.get("link", ""))
            rank = self._coerce_int(row.get("rank_position"), default=base_rank)
            if rank < 1:
                rank = base_rank

            items.append(
                {
                    "title": title,
                    "keyword": title,
                    "link": link,
                    "url": link,
                    "summary": "",
                    "publisher": "디씨인사이드",
                    "published_at": self._clean_text(row.get("published_at", "")),
                    "category": self._clean_text(row.get("category", "")) or self._clean_text(source.get("name", "")),
                    "rank_position": int(rank),
                    "views": self._coerce_optional_int(row.get("views")),
                    "comments": self._coerce_optional_int(row.get("comments")),
                    "likes": self._coerce_optional_int(row.get("likes")),
                    "source_id": source_id,
                    "source_name": source_name,
                    "source_type": source_type,
                    "tier": tier,
                    "weight": weight,
                    "base_score": max(95 - int(rank), 1),
                    "trend_reason": "Dcinside us-post list",
                    "collection_method": collection_method,
                    "is_fallback": is_fallback,
                    "collected_at": datetime.now().isoformat(),
                }
            )

        return items[: self.max_items]

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
            deduped.append(item)

        ranked = []
        for index, item in enumerate(deduped, start=1):
            item["rank_position"] = index
            item["base_score"] = max(95 - index, 1)
            ranked.append(item)

        return ranked[: self.max_items]

    def _save_cache(self, items: List[Dict[str, Any]]) -> None:
        if not items:
            return

        payload = {
            "source": "dcinside",
            "updated_at": datetime.now().isoformat(),
            "items": [
                {
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "published_at": item.get("published_at", ""),
                    "category": item.get("category", ""),
                    "rank_position": item.get("rank_position", index + 1),
                    "views": item.get("views"),
                    "comments": item.get("comments"),
                    "likes": item.get("likes"),
                }
                for index, item in enumerate(items)
            ],
        }

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def _load_cache(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.cache_path.exists():
            return []

        try:
            with open(self.cache_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            return []

        if not isinstance(data, dict):
            return []

        if not self._is_cache_fresh(data.get("updated_at")):
            return []

        items = data.get("items", [])
        if not isinstance(items, list):
            return []

        rows = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = self._clean_text(item.get("title", ""))
            link = self._normalize_link(item.get("link", ""))
            if not title or not link:
                continue
            rows.append(
                {
                    "title": title,
                    "link": link,
                    "published_at": self._clean_text(item.get("published_at", "")),
                    "category": self._clean_text(item.get("category", "")),
                    "rank_position": item.get("rank_position", 1),
                    "views": self._coerce_optional_int(item.get("views")),
                    "comments": self._coerce_optional_int(item.get("comments")),
                    "likes": self._coerce_optional_int(item.get("likes")),
                }
            )

        return self._build_items(rows, source, "dcinside_cache", is_fallback=True)

    def _is_cache_fresh(self, updated_at: Any) -> bool:
        if self.cache_ttl_seconds <= 0:
            return True

        if not updated_at:
            return False

        try:
            parsed = datetime.fromisoformat(str(updated_at))
        except Exception:
            return False

        age = datetime.now() - parsed
        return timedelta(0) <= age <= timedelta(seconds=self.cache_ttl_seconds)

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

    def _record_diagnostic(self) -> None:
        try:
            if self.last_status.get("success") and not self.last_status.get("used_cache"):
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="dcinside",
                    reason="",
                    status="ok",
                )
            else:
                reason = self.last_status.get("failed_reason") or self.LIVE_REJECTION_REASON
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="dcinside",
                    reason=reason,
                    status="fallback_used",
                )
                self.service_diagnostic.record(diagnostic)

            self.last_status["service_diagnostic"] = diagnostic
        except Exception as error:
            print(f"Dcinside Service Diagnostic Failed: {error}")

    def _primary_failed_reason(self, failures: List[Dict[str, str]]) -> str:
        if not failures:
            return "no_results"

        priorities = [
            self.LIVE_REJECTION_REASON,
            "http_403_forbidden",
            "http_403",
            "timeout",
            "connection_refused",
            "network_error",
            self.MALFORMED_FIXTURE_REASON,
            "empty_result",
            "unknown_error",
        ]

        reasons = [entry.get("reason", "unknown_error") for entry in failures]
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
            if isinstance(reason, socket.timeout):
                return "timeout"
            text = str(reason).lower()
            if "timed out" in text or "timeout" in text:
                return "timeout"
            if "refused" in text or "10061" in text:
                return "connection_refused"
            if "forbidden" in text or "403" in text:
                return "http_403_forbidden"
            return "network_error"
        return "unknown_error"

    def _coerce_int(self, value: Any, default: int) -> int:
        try:
            if isinstance(value, int):
                return value
            text = self._clean_text(value)
            if text.isdigit():
                return int(text)
        except Exception:
            return default
        return default

    def _coerce_optional_int(self, value: Any) -> Optional[int]:
        try:
            if value is None or value == "":
                return None
            if isinstance(value, int):
                return max(0, value)
            numeric = re.sub(r"[^\d]", "", self._clean_text(value))
            return int(numeric) if numeric else None
        except Exception:
            return None

    def _normalize_link(self, value: Any) -> str:
        text = self._clean_text(value)
        if not text:
            return ""
        if text.startswith("//"):
            return f"https:{text}"
        if text.startswith("/"):
            return f"https://gall.dcinside.com{text}"
        if text.startswith("http://") or text.startswith("https://"):
            return text
        return ""

    def _clean_text(self, text: Any) -> str:
        if text is None:
            return ""
        text = html.unescape(str(text))
        text = re.sub(r"<script.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<style.*?</style>", "", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = text.replace("\n", " ").replace("\t", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _retry_delay(self, retry_index: int) -> float:
        backoff = [0.3, 0.6, 1.0]
        try:
            return max(0.0, float(backoff[retry_index]))
        except Exception:
            return 0.0
