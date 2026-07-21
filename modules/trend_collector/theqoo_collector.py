import html
import re
import socket
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError

from modules.common.service_diagnostic import ServiceDiagnostic


class TheQooCollector:
    """Low-cost HOT-board collector for theqoo.net.

    Behavior is intentionally shallow and parse-first:
    - parse only non-notice list rows from /hot
    - parse visible list fields only
    - no deep page fetches
    - failures are non-fatal and reported through status/diagnostics
    - live traffic is optional via live_collection_enabled config gate
    """

    def __init__(
        self,
        timeout: int = 8,
        max_items: int = 20,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.timeout = timeout
        self.max_items = max_items
        self.config = config or {}
        self.service_diagnostic = ServiceDiagnostic()
        self.cache_path = Path("storage/cache/theqoo_cache.json")
        self.last_status = self._empty_status()
        self.source_name = "theQoo"

    def _empty_status(self) -> Dict[str, Any]:
        return {
            "source": "theqoo",
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
                "service": "theqoo",
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

        errors: List[Dict[str, str]] = []
        requested_url = self._normalize_source_url(source.get("url", ""))
        parsed_items: List[Dict[str, Any]] = []

        if self._live_collection_allowed():
            try:
                fetched_url, raw_html = self._fetch_url(requested_url)
                page_index = self._parse_page_index(fetched_url)
                parsed_items, notices_skipped = self._parse_hot_list_page(raw_html, page_index)
                parsed_items = self._dedupe(parsed_items)[: self.max_items]
                self.last_status["fallback_reason"] = f"notices_skipped:{notices_skipped}"
            except Exception as error:
                errors.append({"reason": self._classify_error(error), "message": str(error)})
                self.last_status["fallback_reason"] = errors[0].get("reason", "unknown_error")
        else:
            errors.append(
                {
                    "reason": "blocked_by_contract",
                    "message": "live_collection_disabled_by_config",
                }
            )

        if parsed_items:
            self.last_status["success"] = True
            self.last_status["count"] = len(parsed_items)
            self.last_status["collection_method"] = "theqoo_hot_html"
            self._save_cache(parsed_items)
            self._record_diagnostic()
            return [
                {
                    **item,
                    "source_id": "theqoo",
                    "source_name": source.get("name", self.source_name),
                    "source_type": source.get("type", "community"),
                    "tier": int(source.get("tier", 1)),
                    "weight": int(source.get("weight", 20)),
                    "base_score": 100 - item["rank"],
                    "collection_method": self.last_status["collection_method"],
                    "is_fallback": False,
                }
                for item in parsed_items
            ]

        cache_items = self._load_cache(source)
        if cache_items:
            self.last_status["used_cache"] = True
            self.last_status["collection_method"] = "theqoo_hot_cache"
            self.last_status["count"] = len(cache_items)
            self.last_status["failed_reason"] = self._primary_failed_reason(errors)
            self.last_status["final_error_type"] = self.last_status["failed_reason"]
            self._record_diagnostic()
            return cache_items

        self.last_status["failed_reason"] = self._primary_failed_reason(errors)
        self.last_status["final_error_type"] = self.last_status["failed_reason"]
        self.last_status["error_message"] = self.last_status["failed_reason"]
        self.last_status["collection_method"] = "theqoo_hot_html"
        self._record_diagnostic()
        return []

    def _live_collection_allowed(self) -> bool:
        return bool(self.config.get("live_collection_enabled", False))

    def _normalize_source_url(self, source_url: str) -> str:
        url = str(source_url or "").strip()
        if not url:
            return "https://theqoo.net/hot"
        if url.startswith("/"):
            return f"https://theqoo.net{url}"
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return "https://theqoo.net/hot"

    def _parse_page_index(self, url: str) -> int:
        parsed = urllib.parse.urlparse(url or "")
        query = urllib.parse.parse_qs(parsed.query or "")
        page_value = str(query.get("page", ["1"])[0] or "1").strip()
        if page_value.isdigit():
            return max(1, int(page_value))
        return 1

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

    def _parse_hot_list_page(self, raw_html: str, page_index: int) -> tuple[list[dict[str, Any]], int]:
        table_match = re.search(
            r'<table[^>]*class="[^"]*\btheqoo_board_table\b[^"]*"(.*?)</table>',
            raw_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not table_match:
            return [], 0

        table_html = table_match.group(1)
        tbody_match = re.search(
            r'<tbody[^>]*class="[^"]*hide_notice[^"]*"[^>]*>(.*?)</tbody>',
            table_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not tbody_match:
            return [], 0

        tbody_html = tbody_match.group(1)
        row_matches = re.finditer(
            r'(<tr[^>]*>)(.*?)</tr>',
            tbody_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        items: List[Dict[str, Any]] = []
        notices_skipped = 0

        for row in row_matches:
            row_html = row.group(0)
            if self._is_notice_row(row_html):
                notices_skipped += 1
                continue

            item = self._parse_row(row_html)
            if item is None:
                continue
            item["rank"] = len(items) + 1 + (20 * (page_index - 1))
            items.append(item)

        return items, notices_skipped

    def _is_notice_row(self, row_html: str) -> bool:
        open_tag_match = row_html[:256]
        return 'class="notice"' in open_tag_match.lower() or " class='notice'" in open_tag_match.lower()

    def _parse_row(self, row_html: str) -> Optional[Dict[str, Any]]:
        row_post_no = self._parse_int(self._extract_cell(row_html, "no"))
        if row_post_no is None:
            return None

        board_post_no = row_post_no
        category = self._clean_text(self._extract_cell(row_html, 'cate'))
        title_text, title_link = self._extract_title_and_url(row_html)
        if not title_link or not title_text:
            return None

        collected_at = datetime.now()
        document_srl = self._extract_document_srl(title_link)
        time_text = self._clean_text(self._extract_cell(row_html, "time"))
        views = self._parse_int(self._extract_cell(row_html, "m_no"), default=None)
        if views is None:
            return None
        comment_count = self._parse_int(
            self._extract_reply_count(row_html),
            default=0,
        )
        if row_post_no is None:
            return None

        return {
            "document_srl": document_srl,
            "board_post_no": board_post_no,
            "title": title_text,
            "url": self._normalize_link(title_link),
            "board": "hot",
            "category": category,
            "time_text": time_text,
            "published_at": self._resolve_published_at(time_text, collected_at),
            "views": views,
            "comment_count": comment_count,
            "recommend_count": None,
            "has_images": bool(self._has_images(row_html)),
            "collected_at": collected_at.isoformat(),
        }

    def _extract_cell(self, row_html: str, selector: str) -> str:
        pattern = re.compile(
            rf'<td[^>]*class="[^"]*{re.escape(selector)}[^"]*"[^>]*>(.*?)</td>',
            flags=re.IGNORECASE | re.DOTALL,
        )
        match = pattern.search(row_html)
        return match.group(1).strip() if match else ""

    def _extract_title_and_url(self, row_html: str) -> tuple[str, str]:
        title_cell = self._extract_cell(row_html, "title")
        if not title_cell:
            return "", ""

        anchor_match = re.search(
            r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            title_cell,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not anchor_match:
            return "", ""

        href = anchor_match.group(1).strip()
        text = self._clean_text(anchor_match.group(2))
        if not href.startswith("/hot/"):
            return "", ""
        return text, href

    def _extract_reply_count(self, row_html: str) -> str:
        title_cell = self._extract_cell(row_html, "title")
        if not title_cell:
            return ""

        match = re.search(
            r'<a[^>]+class="replyNum"[^>]*>(.*?)</a>',
            title_cell,
            flags=re.IGNORECASE | re.DOTALL,
        )
        return self._clean_text(match.group(1)) if match else ""

    def _extract_document_srl(self, href: str) -> str:
        match = re.search(r"/hot/(\d+)", href)
        if match:
            return match.group(1)

        query_match = re.search(r"document_srl=(\d+)", href)
        return query_match.group(1) if query_match else ""

    def _has_images(self, row_html: str) -> bool:
        title_cell = self._extract_cell(row_html, "title")
        if not title_cell:
            return False
        return bool(re.search(r'class="[^"]*fa-images[^"]*"', title_cell, flags=re.IGNORECASE))

    def _resolve_published_at(self, time_text: str, collected_at: datetime) -> Optional[str]:
        time_text = (time_text or "").strip()
        if not time_text:
            return None

        time_match = re.match(r"^\d{1,2}:\d{2}$", time_text)
        if time_match:
            try:
                hour, minute = map(int, time_text.split(":"))
                resolved = collected_at.replace(hour=hour, minute=minute, second=0, microsecond=0)
                return resolved.isoformat()
            except Exception:
                return None

        date_match = re.match(r"^(0?[1-9]|1[0-2])\.(0?[1-9]|[1-3][0-9])$", time_text)
        if not date_match:
            return None

        try:
            month = int(date_match.group(1))
            day = int(date_match.group(2))
            return datetime(
                collected_at.year,
                month,
                day,
                0,
                0,
                0,
            ).isoformat()
        except Exception:
            return None

    def _parse_int(self, raw_value: Any, default: Optional[int] = 0) -> Optional[int]:
        value = (self._clean_text(raw_value) if raw_value is not None else "")
        if not value:
            if default is None:
                return None
            return default
        numeric = re.sub(r"[^\d]", "", value)
        if not numeric:
            return default
        try:
            return int(numeric)
        except Exception:
            return default

    def _normalize_link(self, link: str) -> str:
        normalized = html.unescape(str(link).strip())
        if not normalized:
            return ""
        if normalized.startswith("//"):
            return f"https:{normalized}"
        if normalized.startswith("/"):
            return urllib.parse.urljoin("https://theqoo.net", normalized.split("?", 1)[0])
        return normalized.split("?", 1)[0]

    def _parse_reply_count(self, text: str) -> int:
        return self._parse_int(text, default=0)

    def _clean_text(self, text: Any) -> str:
        if text is None:
            return ""
        text = re.sub(r"<script.*?</script>", "", str(text), flags=re.DOTALL)
        text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<.*?>", " ", text)
        text = html.unescape(text)
        text = text.replace("\n", " ").replace("\t", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _dedupe(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        deduped = []
        for item in items:
            key = item.get("url") or item.get("title")
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    def _record_diagnostic(self) -> None:
        try:
            if self.last_status.get("success"):
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="theqoo",
                    reason="",
                    status="ok",
                )
            else:
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="theqoo",
                    reason=self.last_status.get("failed_reason", "unknown_error"),
                    status="fallback_used",
                )
                self.service_diagnostic.record(diagnostic)

            self.last_status["service_diagnostic"] = diagnostic
        except Exception as error:
            print(f"TheQoo Service Diagnostic Failed: {error}")

    def _save_cache(self, items: List[Dict[str, Any]]) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "source": "theqoo",
                "updated_at": datetime.now().isoformat(),
                "items": [
                    {
                        "document_srl": item.get("document_srl"),
                        "board_post_no": item.get("board_post_no"),
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "board": item.get("board"),
                        "category": item.get("category"),
                        "rank": item.get("rank"),
                        "time_text": item.get("time_text"),
                        "published_at": item.get("published_at"),
                        "views": item.get("views"),
                        "comment_count": item.get("comment_count"),
                        "recommend_count": item.get("recommend_count"),
                        "has_images": item.get("has_images"),
                    }
                    for item in items
                ],
            }
            with open(self.cache_path, "w", encoding="utf-8") as handle:
                import json
                json.dump(payload, handle, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_cache(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.cache_path.exists():
            return []
        try:
            with open(self.cache_path, "r", encoding="utf-8") as handle:
                import json
                data = json.load(handle)
            items = data.get("items", [])
            if not isinstance(items, list):
                return []
        except Exception:
            return []

        cached_items = []
        for item in items:
            if not isinstance(item, dict):
                continue

            url = self._normalize_link(item.get("url", ""))
            title = self._clean_text(item.get("title", ""))
            if not url or not title:
                continue

            cached_items.append(
                {
                    "document_srl": str(item.get("document_srl", "")),
                    "board_post_no": self._parse_int(item.get("board_post_no"), default=0),
                    "title": title,
                    "url": url,
                    "board": "hot",
                    "category": self._clean_text(item.get("category", "")),
                    "rank": self._parse_int(item.get("rank"), default=0),
                    "time_text": self._clean_text(item.get("time_text", "")),
                    "published_at": item.get("published_at"),
                    "views": self._parse_int(item.get("views"), default=0),
                    "comment_count": self._parse_int(item.get("comment_count"), default=0),
                    "recommend_count": None,
                    "has_images": bool(item.get("has_images", False)),
                    "source_id": "theqoo",
                    "source_name": source.get("name", self.source_name),
                    "source_type": source.get("type", "community"),
                    "tier": int(source.get("tier", 1)),
                    "weight": int(source.get("weight", 20)),
                    "base_score": 90,
                    "collection_method": "theqoo_hot_cache",
                    "is_fallback": True,
                    "collected_at": datetime.now().isoformat(),
                }
            )
        return cached_items

    def _primary_failed_reason(self, errors: List[Dict[str, str]]) -> str:
        if not errors:
            return "unknown_error"
        priorities = [
            "http_403",
            "blocked_by_contract",
            "connection_refused",
            "timeout",
            "network_error",
            "parse_error",
            "empty_result",
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
                return "http_403"
            return f"network_error"
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
            if "refused" in reason_text or "10061" in reason_text:
                return "connection_refused"
            if "forbidden" in reason_text or "403" in reason_text:
                return "http_403"
            return "network_error"
        if isinstance(error, re.error):
            return "parse_error"
        return "unknown_error"
