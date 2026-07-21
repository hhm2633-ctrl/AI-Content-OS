"""Shallow, fallback-first collector for FashionBiz public editorial lists.

Only metadata visibly present on a public list page is parsed. Article detail
pages, images, inferred engagement, browser/login flows, and commerce signals
are intentionally out of scope. Live fetching is disabled unless explicitly
enabled with ``allow_live_fetch``.
"""

from __future__ import annotations

import html
import json
import re
import socket
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError

from modules.common.service_diagnostic import ServiceDiagnostic


class FashionBizCollector:
    """Collect FashionBiz list metadata without article-detail requests."""

    DEFAULT_URL = "https://fashionbiz.co.kr/list/article"
    GRAPHQL_URL = "https://www.fashionbiz.co.kr/api/graphql"
    DEFAULT_CACHE_PATH = Path("storage/cache/fashionbiz_editorial_cache.json")
    LIVE_REJECTION_REASON = "live_activation_not_approved"
    ALLOWED_HOSTS = {"fashionbiz.co.kr", "www.fashionbiz.co.kr"}

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
            0,
            int(self.config.get("cache_ttl_seconds", 24 * 60 * 60)),
        )
        self.service_diagnostic = ServiceDiagnostic()
        self.last_status = self._empty_status()

    def _empty_status(self) -> Dict[str, Any]:
        return {
            "source": "fashionbiz",
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
                service="fashionbiz", reason="", status="ok"
            ),
        }

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
                rows, source, "fashionbiz_public_editorial_list", False
            )
            self._set_status(items, "fashionbiz_public_editorial_list")
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
                    "collection_method": "fashionbiz_editorial_cache",
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
                "collection_method": "fashionbiz_no_data",
            }
        )
        self._set_diagnostic(reason, "fallback_used")
        return []

    def parse_public_list(self, raw_html: str) -> List[Dict[str, Any]]:
        document = str(raw_html or "")
        if not document.strip():
            return []

        graphql_rows = self._parse_graphql_list(document)
        if graphql_rows is not None:
            return graphql_rows

        rows: List[Dict[str, Any]] = []
        seen = set()
        for block in self._candidate_blocks(document):
            title, link = self._extract_title_link(block)
            if not title or not link or link in seen:
                continue
            seen.add(link)
            rows.append(self._visible_row(block, title, link, len(rows) + 1))
            if len(rows) >= self.max_items:
                break
        return rows

    def _parse_graphql_list(self, document: str) -> Optional[List[Dict[str, Any]]]:
        """Parse the public list query response used by the client-rendered site."""
        try:
            payload = json.loads(document)
        except (TypeError, ValueError):
            return None
        if not isinstance(payload, dict):
            return []
        container = ((payload.get("data") or {}).get("seeLatestBestNews") or {})
        articles = container.get("articles")
        if not isinstance(articles, list):
            return []

        rows: List[Dict[str, Any]] = []
        seen = set()
        for article in articles:
            if not isinstance(article, dict):
                continue
            article_id = self._coerce_positive_int(article.get("cts_id"))
            title = self._clean_text(article.get("title"))
            if article_id is None or not title or article_id in seen:
                continue
            seen.add(article_id)
            rows.append(
                {
                    "title": title,
                    "link": f"https://fashionbiz.co.kr/article/{article_id}",
                    "section_category": None,
                    "summary": None,
                    "visible_date": self._nullable_text(article.get("openResDate")),
                    "rank_position": len(rows) + 1,
                    "rank": len(rows) + 1,
                    "rank_basis": "visible_list_order",
                    "attribution": "FashionBiz public editorial list",
                    "publisher": None,
                    "views": self._coerce_nonnegative_int(article.get("clickCount")),
                    "comments": self._coerce_nonnegative_int(
                        article.get("commentCount")
                    ),
                    "likes": None,
                }
            )
            if len(rows) >= self.max_items:
                break
        return rows

    def _visible_row(
        self, block: str, title: str, link: str, position: int
    ) -> Dict[str, Any]:
        return {
            "title": title,
            "link": link,
            "section_category": self._extract_visible_field(
                block, ("category", "section", "cate", "board", "tag")
            )
            or None,
            "summary": self._extract_visible_field(
                block, ("summary", "description", "desc", "excerpt", "lead")
            )
            or None,
            "visible_date": self._extract_visible_date(block),
            "rank_position": position,
            "rank": position,
            "rank_basis": "visible_list_order",
            "attribution": "FashionBiz public editorial list",
            "publisher": None,
            "views": self._extract_visible_metric(block, ("view", "views", "hit", "read")),
            "comments": self._extract_visible_metric(
                block, ("comment", "comments", "reply")
            ),
            "likes": self._extract_visible_metric(
                block, ("like", "likes", "recommend")
            ),
        }

    def _candidate_blocks(self, document: str) -> List[str]:
        blocks: List[str] = []
        for tag in ("article", "li"):
            blocks.extend(
                match.group(0)
                for match in re.finditer(
                    rf"<{tag}\b[^>]*>[\s\S]*?</{tag}>", document, flags=re.I
                )
            )
        blocks.extend(
            match.group(0)
            for match in re.finditer(
                r'<div\b[^>]*class=["\'][^"\']*(?:article|news|list|item|card)[^"\']*["\'][^>]*>[\s\S]*?</div>',
                document,
                flags=re.I,
            )
        )
        return blocks

    def _extract_title_link(self, block: str) -> Tuple[str, str]:
        for anchor in re.finditer(
            r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',
            block,
            flags=re.I,
        ):
            link = self._normalize_link(anchor.group(1))
            if not self._is_editorial_link(link):
                continue
            title_markup = anchor.group(2)
            heading = re.search(
                r"<(?:h[1-6]|dt)\b[^>]*>([\s\S]*?)</(?:h[1-6]|dt)>",
                title_markup,
                flags=re.I,
            )
            title = self._clean_text(heading.group(1) if heading else title_markup)
            if link and len(title) >= 4:
                return title, link
        return "", ""

    def _is_editorial_link(self, link: str) -> bool:
        path = urllib.parse.urlparse(link).path
        return bool(re.fullmatch(r"/article/\d+/?", path))

    def _extract_visible_field(self, block: str, tokens: Tuple[str, ...]) -> str:
        token_pattern = "|".join(re.escape(token) for token in tokens)
        match = re.search(
            rf'<(?:span|p|div|em|dd|dt)\b[^>]*class=["\'][^"\']*(?:{token_pattern})[^"\']*["\'][^>]*>([\s\S]*?)</(?:span|p|div|em|dd|dt)>',
            block,
            flags=re.I,
        )
        return self._clean_text(match.group(1)) if match else ""

    def _extract_visible_date(self, block: str) -> Optional[str]:
        match = re.search(
            r'<time\b[^>]*datetime=["\']([^"\']+)["\'][^>]*>', block, flags=re.I
        )
        if match:
            return self._clean_text(match.group(1)) or None
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
        match = re.search(r"\d[\d,]*", visible) if visible else None
        return self._coerce_nonnegative_int(match.group(0)) if match else None

    def _build_items(
        self,
        rows: List[Dict[str, Any]],
        source: Dict[str, Any],
        collection_method: str,
        is_fallback: bool,
    ) -> List[Dict[str, Any]]:
        collected_at = datetime.now().astimezone().isoformat()
        source_id = str(source.get("source_id") or "fashionbiz")
        source_name = str(source.get("name") or source.get("source_name") or "FashionBiz")
        items: List[Dict[str, Any]] = []
        for row in rows[: self.max_items]:
            title = self._clean_text(row.get("title"))
            link = self._normalize_link(row.get("link"))
            rank = self._coerce_positive_int(row.get("rank_position"))
            if not title or not link or rank is None:
                continue
            section = self._nullable_text(row.get("section_category") or row.get("category"))
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
                    "category": section,
                    "section_category": section,
                    "rank_position": rank,
                    "rank": rank,
                    "rank_basis": "visible_list_order",
                    "publisher": self._nullable_text(row.get("publisher"))
                    or self._publisher_from_link(link),
                    "attribution": "FashionBiz public editorial list",
                    "views": self._coerce_nonnegative_int(row.get("views")),
                    "comments": self._coerce_nonnegative_int(row.get("comments")),
                    "likes": self._coerce_nonnegative_int(row.get("likes")),
                    "source_id": source_id,
                    "source_name": source_name,
                    "source_type": str(source.get("type") or "fashion_editorial"),
                    "collection_method": collection_method,
                    "is_fallback": bool(is_fallback),
                    "collected_at": collected_at,
                }
            )
        return items

    def _publisher_from_link(self, link: str) -> Optional[str]:
        host = (urllib.parse.urlparse(link).hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host or None

    def _load_cache(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.cache_path.exists():
            return []
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or not self._cache_is_fresh(payload.get("updated_at")):
                return []
            rows = payload.get("items")
            if not isinstance(rows, list):
                return []
        except Exception:
            return []
        return self._build_items(rows, source, "fashionbiz_editorial_cache", True)

    def _cache_is_fresh(self, value: Any) -> bool:
        try:
            updated_at = datetime.fromisoformat(str(value))
            now = datetime.now().astimezone() if updated_at.tzinfo else datetime.now()
            age = now - updated_at
            return 0 <= age.total_seconds() <= self.cache_ttl_seconds
        except Exception:
            return False

    def _set_status(self, items: List[Dict[str, Any]], method: str) -> None:
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
                service="fashionbiz", reason=reason, status=status
            )
        )

    def _resolve_url(self, source: Dict[str, Any]) -> str:
        url = str(source.get("url") or self.DEFAULT_URL).strip()
        return url if url.startswith(("http://", "https://")) else self.DEFAULT_URL

    def _fetch_url(self, url: str) -> Tuple[str, str]:
        query = """
        query SeeLatestBestNews($orderBy: Int!, $take: Int!, $cursor: Int!) {
          seeLatestBestNews(orderBy: $orderBy, take: $take, cursor: $cursor) {
            articles { cts_id title openResDate clickCount commentCount }
          }
        }
        """
        body = json.dumps(
            {
                "query": query,
                "variables": {"orderBy": 1, "take": self.max_items, "cursor": 0},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.GRAPHQL_URL,
            data=body,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Origin": "https://fashionbiz.co.kr",
                "Referer": url,
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
        return link if host in self.ALLOWED_HOSTS else ""

    def _clean_text(self, value: Any) -> str:
        text = str(value or "")
        text = re.sub(r"<script.*?</script>|<style.*?</style>", "", text, flags=re.I | re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", html.unescape(text)).strip()

    def _nullable_text(self, value: Any) -> Optional[str]:
        cleaned = self._clean_text(value)
        return cleaned or None

    def _coerce_positive_int(self, value: Any) -> Optional[int]:
        try:
            parsed = int(value)
            return parsed if parsed > 0 else None
        except Exception:
            return None

    def _coerce_nonnegative_int(self, value: Any) -> Optional[int]:
        try:
            match = re.search(r"\d+", str(value).replace(",", ""))
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
