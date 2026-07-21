"""Fallback-first shallow collector for Beautynury public editorial lists."""

from __future__ import annotations

import html
import json
import re
import socket
import ssl
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError

from modules.common.service_diagnostic import ServiceDiagnostic


class BeautynuryCollector:
    """Collect only metadata visible on a Beautynury public list page."""

    DEFAULT_URL = "https://www.beautynury.com/news/lists/cat/10"
    DEFAULT_CACHE_PATH = Path("storage/cache/beautynury_editorial_cache.json")
    LIVE_REJECTION_REASON = "live_activation_not_approved"
    SOURCE_ID = "beautynury"
    SOURCE_NAME = "Beautynury"
    ATTRIBUTION = "Beautynury public editorial list"
    LIVE_METHOD = "beautynury_public_editorial_list"
    CACHE_METHOD = "beautynury_editorial_cache"
    NO_DATA_METHOD = "beautynury_no_data"
    ALLOWED_HOSTS = {"beautynury.com", "www.beautynury.com"}
    ARTICLE_PATH_PATTERN = re.compile(
        r"^/news/view/\d+/cat/\d+(?:/page/\d+)?/?$", re.IGNORECASE
    )

    def __init__(
        self,
        timeout: int = 8,
        max_items: int = 30,
        config: Optional[Dict[str, Any]] = None,
        fetcher: Optional[Callable[[str], Tuple[str, str]]] = None,
        parser: Optional[Callable[[str], List[Dict[str, Any]]]] = None,
    ) -> None:
        self.timeout = int(timeout)
        self.max_items = max(1, int(max_items))
        self.config = config or {}
        self.fetcher = fetcher or self._fetch_url
        self.parser = parser or self.parse_public_list
        self.cache_path = Path(self.config.get("cache_path", self.DEFAULT_CACHE_PATH))
        self.cache_ttl_seconds = max(
            0, int(self.config.get("cache_ttl_seconds", 24 * 60 * 60))
        )
        self.service_diagnostic = ServiceDiagnostic()
        self.last_status = self._empty_status()

    def _empty_status(self) -> Dict[str, Any]:
        return {
            "source": self.SOURCE_ID,
            "attempted": False,
            "success": False,
            "count": 0,
            "failed_reason": "",
            "fallback_reason": "",
            "final_error_type": "",
            "error_message": "",
            "collection_method": "",
            "used_cache": False,
            "cache_path": str(self.cache_path).replace("\\", "/"),
            "service_diagnostic": self.service_diagnostic.build_diagnostic_from_reason(
                service=self.SOURCE_ID, reason="", status="ok"
            ),
        }

    def collect(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return one bounded live page, fresh cache data, or an honest empty list."""
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
            items = self._build_items(rows, source, self.LIVE_METHOD, False)
            self._set_success(items, self.LIVE_METHOD)
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
                    "collection_method": self.CACHE_METHOD,
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
                "collection_method": self.NO_DATA_METHOD,
            }
        )
        self._set_diagnostic(reason, "fallback_used")
        return []

    def parse_public_list(self, raw_html: str) -> List[Dict[str, Any]]:
        """Parse deterministic public-list cards without opening detail pages."""
        document = str(raw_html or "")
        if not document.strip():
            return []

        rows: List[Dict[str, Any]] = []
        seen = set()
        for title, link, block in self._article_candidates(document):
            if not title or not link or link in seen:
                continue
            seen.add(link)
            rank = len(rows) + 1
            rows.append(
                {
                    "title": title,
                    "link": link,
                    "section_category": self._extract_visible_field(
                        block, ("category", "section", "cate", "subject")
                    )
                    or None,
                    "summary": self._extract_summary(block),
                    "visible_date": self._extract_visible_date(block),
                    "author": self._extract_author(block),
                    "rank_position": rank,
                    "rank": rank,
                    "rank_basis": "visible_list_order",
                    "attribution": self.ATTRIBUTION,
                    "views": self._extract_visible_metric(block, ("view", "views", "hit")),
                    "comments": self._extract_visible_metric(
                        block, ("comment", "comments", "reply")
                    ),
                    "likes": self._extract_visible_metric(
                        block, ("like", "likes", "recommend")
                    ),
                }
            )
            if len(rows) >= self.max_items:
                break
        return rows

    def _article_candidates(self, document: str) -> List[Tuple[str, str, str]]:
        """Locate strict article anchors globally, then recover their nearest card."""
        candidates: List[Tuple[str, str, str]] = []
        for anchor in re.finditer(
            r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',
            document,
            flags=re.IGNORECASE,
        ):
            link = self._normalize_link(anchor.group(1))
            if not link or not self._is_article_link(link):
                continue
            anchor_body = anchor.group(2)
            heading = re.search(
                r"<(?:h[1-6]|strong)\b[^>]*>([\s\S]*?)</(?:h[1-6]|strong)>",
                anchor_body,
                flags=re.IGNORECASE,
            )
            title = self._clean_text(heading.group(1) if heading else anchor_body)
            if len(title) < 4:
                continue
            candidates.append(
                (title, link, self._nearest_card(document, anchor.start(), anchor.end()))
            )
        return candidates

    def _nearest_card(self, document: str, start: int, end: int) -> str:
        """Return the nearest list/article wrapper without parsing the full DOM."""
        choices: List[Tuple[int, str]] = []
        for tag in ("article", "li"):
            opening = list(
                re.finditer(rf"<{tag}\b[^>]*>", document[:start], flags=re.IGNORECASE)
            )
            if opening:
                choices.append((opening[-1].start(), tag))
        if not choices:
            return document[start:end]
        opening_start, tag = max(choices, key=lambda value: value[0])
        closing = re.search(rf"</{tag}>", document[end:], flags=re.IGNORECASE)
        if not closing:
            return document[start:end]
        return document[opening_start : end + closing.end()]

    def _candidate_blocks(self, document: str) -> List[str]:
        blocks: List[str] = []
        for tag in ("article", "li"):
            blocks.extend(
                match.group(0)
                for match in re.finditer(
                    rf"<{tag}\b[^>]*>[\s\S]*?</{tag}>",
                    document,
                    flags=re.IGNORECASE,
                )
            )
        blocks.extend(
            match.group(0)
            for match in re.finditer(
                r'<div\b[^>]*class=["\'][^"\']*(?:article|news|list|item|card)[^"\']*["\'][^>]*>[\s\S]*?</div>',
                document,
                flags=re.IGNORECASE,
            )
        )
        return blocks

    def _extract_title_link(self, block: str) -> Tuple[str, str]:
        for anchor in re.finditer(
            r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',
            block,
            flags=re.IGNORECASE,
        ):
            link = self._normalize_link(anchor.group(1))
            if not link or not self._is_article_link(link):
                continue
            anchor_body = anchor.group(2)
            heading = re.search(
                r"<(?:h[1-6]|strong)\b[^>]*>([\s\S]*?)</(?:h[1-6]|strong)>",
                anchor_body,
                flags=re.IGNORECASE,
            )
            title = self._clean_text(heading.group(1) if heading else anchor_body)
            if link and len(title) >= 4:
                return title, link
        return "", ""

    def _is_article_link(self, link: str) -> bool:
        parsed = urllib.parse.urlparse(link)
        return bool(self.ARTICLE_PATH_PATTERN.fullmatch(parsed.path))

    def _extract_summary(self, block: str) -> Optional[str]:
        visible = self._extract_visible_field(
            block, ("summary", "description", "desc", "excerpt")
        )
        if visible:
            return visible
        match = re.search(r"<p\b[^>]*>([\s\S]*?)</p>", block, flags=re.IGNORECASE)
        return self._nullable_text(match.group(1)) if match else None

    def _extract_author(self, block: str) -> Optional[str]:
        visible = self._extract_visible_field(block, ("author", "writer", "reporter"))
        if visible:
            return visible
        name_container = re.search(
            r'<(?:div|ul)\b[^>]*class=["\'][^"\']*(?:name_con|art_info)[^"\']*["\'][^>]*>([\s\S]*?)</(?:div|ul)>',
            block,
            flags=re.IGNORECASE,
        )
        if not name_container:
            return None
        first_name = re.search(
            r'<(?:span|li)\b[^>]*(?:class=["\'][^"\']*name[^"\']*["\'])?[^>]*>([\s\S]*?)</(?:span|li)>',
            name_container.group(1),
            flags=re.IGNORECASE,
        )
        return self._nullable_text(first_name.group(1)) if first_name else None

    def _extract_visible_field(self, block: str, tokens: Tuple[str, ...]) -> str:
        pattern = "|".join(re.escape(token) for token in tokens)
        match = re.search(
            rf'<(?:span|p|div|em|strong)\b[^>]*class=["\'][^"\']*(?:{pattern})[^"\']*["\'][^>]*>([\s\S]*?)</(?:span|p|div|em|strong)>',
            block,
            flags=re.IGNORECASE,
        )
        return self._clean_text(match.group(1)) if match else ""

    def _extract_visible_date(self, block: str) -> Optional[str]:
        match = re.search(
            r'<time\b[^>]*datetime=["\']([^"\']+)["\'][^>]*>',
            block,
            flags=re.IGNORECASE,
        )
        if match:
            return self._nullable_text(match.group(1))
        visible = self._extract_visible_field(block, ("date", "time", "published"))
        if visible:
            return visible
        match = re.search(
            r"\b(?:20\d{2}[./-])?\d{1,2}[./-]\d{1,2}\b", self._clean_text(block)
        )
        return match.group(0) if match else None

    def _extract_visible_metric(
        self, block: str, tokens: Tuple[str, ...]
    ) -> Optional[int]:
        visible = self._extract_visible_field(block, tokens)
        return self._coerce_nonnegative_int(visible) if visible else None

    def _build_items(
        self,
        rows: List[Dict[str, Any]],
        source: Dict[str, Any],
        collection_method: str,
        is_fallback: bool,
    ) -> List[Dict[str, Any]]:
        collected_at = datetime.now().astimezone().isoformat()
        source_id = str(source.get("source_id") or self.SOURCE_ID)
        source_name = str(
            source.get("name") or source.get("source_name") or self.SOURCE_NAME
        )
        items: List[Dict[str, Any]] = []
        for row in rows[: self.max_items]:
            title = self._clean_text(row.get("title"))
            link = self._normalize_link(row.get("link"))
            rank = self._coerce_positive_int(row.get("rank_position"))
            if not title or not link or rank is None:
                continue
            category = self._nullable_text(
                row.get("section_category") or row.get("category")
            )
            visible_date = self._nullable_text(
                row.get("visible_date") or row.get("published_at")
            )
            items.append(
                {
                    "keyword": title,
                    "title": title,
                    "link": link,
                    "url": link,
                    "summary": self._nullable_text(row.get("summary")),
                    "published_at": visible_date,
                    "visible_date": visible_date,
                    "category": category,
                    "section_category": category,
                    "author": self._nullable_text(row.get("author")),
                    "rank_position": rank,
                    "rank": rank,
                    "rank_basis": "visible_list_order",
                    "publisher": source_name,
                    "attribution": self.ATTRIBUTION,
                    "views": self._coerce_nonnegative_int(row.get("views")),
                    "comments": self._coerce_nonnegative_int(row.get("comments")),
                    "likes": self._coerce_nonnegative_int(row.get("likes")),
                    "beauty_editorial": True,
                    "editorial_metadata_only": True,
                    "article_detail_collected": False,
                    "efficacy_claims_collected": False,
                    "medical_claims_collected": False,
                    "source_id": source_id,
                    "source_name": source_name,
                    "source_type": str(source.get("type") or "beauty_editorial"),
                    "collection_method": collection_method,
                    "is_fallback": bool(is_fallback),
                    "collected_at": collected_at,
                }
            )
        return items

    def _load_cache(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.cache_path.exists():
            return []
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or not self._cache_is_fresh(
                payload.get("updated_at")
            ):
                return []
            rows = payload.get("items")
            if not isinstance(rows, list):
                return []
        except Exception:
            return []
        return self._build_items(rows, source, self.CACHE_METHOD, True)

    def _cache_is_fresh(self, value: Any) -> bool:
        try:
            updated_at = datetime.fromisoformat(str(value))
            now = datetime.now().astimezone() if updated_at.tzinfo else datetime.now()
            age = now - updated_at
            return 0 <= age.total_seconds() <= self.cache_ttl_seconds
        except Exception:
            return False

    def _set_success(self, items: List[Dict[str, Any]], method: str) -> None:
        self.last_status.update(
            {
                "success": bool(items),
                "count": len(items),
                "collection_method": method,
                "used_cache": False,
            }
        )
        self._set_diagnostic("", "ok")

    def _set_diagnostic(self, reason: str, status: str) -> None:
        self.last_status["service_diagnostic"] = (
            self.service_diagnostic.build_diagnostic_from_reason(
                service=self.SOURCE_ID, reason=reason, status=status
            )
        )

    def _resolve_url(self, source: Dict[str, Any]) -> str:
        url = str(source.get("url") or self.DEFAULT_URL).strip()
        return url if url.startswith(("http://", "https://")) else self.DEFAULT_URL

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

    def _normalize_link(self, value: Any) -> str:
        link = html.unescape(str(value or "").strip())
        if link.startswith("//"):
            link = f"https:{link}"
        elif link.startswith("/"):
            link = urllib.parse.urljoin(self.DEFAULT_URL, link)
        if not link.startswith(("http://", "https://")):
            return ""
        host = (urllib.parse.urlparse(link).hostname or "").lower()
        if host not in self.ALLOWED_HOSTS:
            return ""
        return link

    def _clean_text(self, value: Any) -> str:
        text = str(value or "")
        text = re.sub(r"<script.*?</script>|<style.*?</style>", "", text, flags=re.I | re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", html.unescape(text)).strip()

    def _nullable_text(self, value: Any) -> Optional[str]:
        cleaned = self._clean_text(value)
        return cleaned or None

    def _coerce_positive_int(self, value: Any) -> Optional[int]:
        parsed = self._coerce_nonnegative_int(value)
        return parsed if parsed is not None and parsed > 0 else None

    def _coerce_nonnegative_int(self, value: Any) -> Optional[int]:
        try:
            match = re.search(r"\d+", self._clean_text(value).replace(",", ""))
            return int(match.group(0)) if match else None
        except Exception:
            return None

    def _classify_error(self, error: Exception) -> str:
        if isinstance(error, HTTPError):
            return f"http_{error.code}"
        if isinstance(error, (TimeoutError, socket.timeout)):
            return "timeout"
        if isinstance(error, URLError):
            reason = getattr(error, "reason", "")
            if isinstance(reason, ssl.SSLError):
                return "ssl_handshake_failed"
            if isinstance(reason, (TimeoutError, socket.timeout)):
                return "timeout"
            if isinstance(reason, ConnectionRefusedError):
                return "connection_refused"
            return "network_error"
        return "unknown_error"

    def _primary_reason(self, failures: List[str]) -> str:
        if not failures:
            return "no_results"
        for reason in (
            self.LIVE_REJECTION_REASON,
            "http_403",
            "ssl_handshake_failed",
            "connection_refused",
            "timeout",
            "network_error",
            "parse_failed",
            "no_results",
            "unknown_error",
        ):
            if reason in failures:
                return reason
        return failures[0]


__all__ = ["BeautynuryCollector"]
