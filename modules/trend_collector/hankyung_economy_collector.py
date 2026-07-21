"""Low-cost 한국경제 economy collector for shallow intake."""

from __future__ import annotations

import html
import json
import re
import socket
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError


class HankyungEconomyCollector:
    SOURCE = "hankyung_economy"
    SOURCE_NAME = "한국경제"
    BASE_URL = "https://www.hankyung.com"

    SITEMAP_URL = f"{BASE_URL}/sitemap/latest-article.xml"
    ECONOMY_LIST_URL = f"{BASE_URL}/economy"
    ALL_NEWS_LIST_URL = f"{BASE_URL}/all-news"

    CACHE_PATH = Path("storage/cache/hankyung_economy_cache.json")
    REQUEST_MARKER = re.compile(r"\bwindow._cf_chl_opt\b|Just a moment")
    ARTICLE_ID = re.compile(r"/article/([0-9]{12,13}[A-Za-z]?)")
    WS = re.compile(r"\s+")

    def __init__(
        self,
        timeout: int = 8,
        max_items: int = 25,
        max_requests_per_run: int = 3,
        min_delay_seconds_between_requests: int = 3,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.timeout = timeout
        self.max_items = max_items
        self.max_requests_per_run = max_requests_per_run
        self.min_delay_seconds = min_delay_seconds_between_requests
        self.config = config or {}
        self.cache_path = self._resolve_cache_path()
        self.last_status = self._empty_status()
        self._last_request = 0.0
        self._request_count = 0

    def _resolve_cache_path(self) -> Path:
        return Path(str(self.config.get("cache_path", self.CACHE_PATH)))

    def _empty_status(self) -> Dict[str, Any]:
        return {
            "source": self.SOURCE,
            "attempted": False,
            "success": False,
            "count": 0,
            "error_message": "",
            "failed_reason": "",
            "fallback_reason": "",
            "collection_method": "",
            "used_cache": False,
            "cache_path": str(self.cache_path).replace("\\", "/"),
        }

    def collect(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.last_status = self._empty_status()
        self.last_status["attempted"] = True
        self._request_count = 0
        self._last_request = 0.0

        failures: List[str] = []
        plan = (
            (self._collect_from_sitemap, "hankyung_economy_latest_sitemap"),
            (self._collect_from_economy_list, "hankyung_economy_economy_list"),
            (self._collect_from_all_news, "hankyung_economy_all_news"),
        )

        for method, method_name in plan:
            try:
                items = method(source)
                if items:
                    for item in items:
                        item["collection_method"] = method_name
                    self._save_cache(items)
                    self.last_status["success"] = True
                    self.last_status["count"] = len(items)
                    self.last_status["collection_method"] = method_name
                    return items
            except Exception as error:
                failures.append(f"{method_name}:{self._classify_error(error)}")
                if self._is_cloudflare_blocked(str(error)):
                    break
                if "request_budget_exhausted" in self._classify_error(error):
                    break

        cached = self._load_cache()
        if cached:
            self.last_status["used_cache"] = True
            self.last_status["fallback_reason"] = failures[0] if failures else "cache_fallback"
            self.last_status["failed_reason"] = self.last_status["fallback_reason"]
            self.last_status["collection_method"] = f"{self.SOURCE}_cache"
            self.last_status["count"] = len(cached)
            for item in cached:
                item["fallback_used"] = True
            return cached

        if not failures:
            self.last_status["failed_reason"] = "no_verified_items"
        else:
            self.last_status["failed_reason"] = failures[0]
        self.last_status["error_message"] = self.last_status["failed_reason"]
        self.last_status["collection_method"] = f"{self.SOURCE}_no_data"
        return []

    def _collect_from_sitemap(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_xml = self._fetch_url(self.SITEMAP_URL)
        root = ET.fromstring(raw_xml)
        ns = {
            "s": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "news": "http://www.google.com/schemas/sitemap-news/0.9",
        }

        result: List[Dict[str, Any]] = []
        for url_node in root.findall("s:url", ns):
            if len(result) >= self.max_items:
                break

            loc = (url_node.findtext("s:loc", "", namespaces=ns) or "").strip()
            title = self._clean_text(url_node.findtext("news:news/news:title", "", namespaces=ns) or "")
            published_raw = (url_node.findtext("news:news/news:publication_date", "", namespaces=ns) or "").strip()
            article_id = self._extract_article_id(loc)

            if not loc or not title or not article_id:
                continue

            result.append(
                self._build_item(
                    source_id=self.SOURCE,
                    source_name=self.SOURCE_NAME,
                    article_id=article_id,
                    title=title,
                    url=f"{self.BASE_URL}/article/{article_id}",
                    published_at=self._to_display_datetime(published_raw),
                    published_at_iso=self._normalize_kst_datetime(published_raw),
                    summary=None,
                    category=None,
                    category_slug=None,
                    rank=None,
                    thumbnail_url=None,
                    fallback_used=False,
                    source=source,
                )
            )
        result = self._dedupe(result)
        if result:
            try:
                list_items = self._collect_from_economy_list(source)
            except Exception:
                list_items = []
            summaries = {
                item.get("article_id"): item.get("summary")
                for item in list_items
                if item.get("article_id") and item.get("summary")
            }
            for item in result:
                item["summary"] = self._strip(summaries.get(item.get("article_id")))
        return result

    def _collect_from_economy_list(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_html = self._fetch_url(self.ECONOMY_LIST_URL)
        if self._is_cloudflare_blocked(raw_html):
            raise RuntimeError("cloudflare_challenge")

        container = self._extract_block(raw_html, r'<ul[^>]*class="[^"]*news-list[^"]*"[^>]*>(.*?)</ul>')
        if not container:
            return []

        blocks = re.findall(
            r'<div[^>]*class="[^"]*news-item[^"]*"[^>]*>(.*?)</div\s*>',
            container,
            flags=re.IGNORECASE | re.DOTALL,
        )
        result: List[Dict[str, Any]] = []
        for block in blocks:
            url = self._extract_attr(block, r'<h2[^>]*class="[^"]*news-tit[^"]*"[^>]*>\s*<a[^>]*href="([^"]+)"', "href")
            title = self._extract_text(block, r'<h2[^>]*class="[^"]*news-tit[^"]*"[^>]*>\s*<a[^>]*>(.*?)</a>')
            article_id = self._extract_article_id(url)
            if not url or not title or not article_id:
                continue

            published_at_raw = self._extract_text(block, r'<p[^>]*class="[^"]*txt-date[^"]*"[^>]*>(.*?)</p>')
            summary = self._extract_text(block, r'<p[^>]*class="[^"]*lead[^"]*"[^>]*>(.*?)</p>')
            category = self._extract_text(block, r'<span[^>]*class="[^"]*depth3[^"]*"[^>]*>\s*<a[^>]*>(.*?)</a>')
            category_slug = self._extract_category_slug(block)
            thumbnail = self._extract_attr(block, r'<figure[^>]*class="[^"]*thumb[^"]*"[^>]*>.*?<img[^>]*src="([^"]+)"', "src")

            result.append(
                self._build_item(
                    source_id=self.SOURCE,
                    source_name=source.get("name", self.SOURCE_NAME),
                    article_id=article_id,
                    title=title,
                    url=self._normalize_link(url),
                    published_at=self._to_display_datetime(published_at_raw),
                    published_at_iso=self._normalize_kst_datetime(published_at_raw),
                    summary=self._strip(summary),
                    category=self._strip(category),
                    category_slug=self._strip(category_slug),
                    rank=None,
                    thumbnail_url=self._normalize_link(thumbnail),
                    fallback_used=False,
                    source=source,
                )
            )
            if len(result) >= self.max_items:
                break
        return self._dedupe(result)

    def _collect_from_all_news(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_html = self._fetch_url(self.ALL_NEWS_LIST_URL)
        if self._is_cloudflare_blocked(raw_html):
            raise RuntimeError("cloudflare_challenge")

        container = self._extract_block(raw_html, r'<ul[^>]*class="[^"]*allnews-list[^"]*"[^>]*>(.*?)</ul>')
        if not container:
            return []

        items = re.finditer(
            r'<li[^>]*data-aid="([^"]+)"[^>]*>(.*?)</li>',
            container,
            flags=re.IGNORECASE | re.DOTALL,
        )

        result: List[Dict[str, Any]] = []
        for article_id, block in items:
            url = self._extract_attr(block, r'<h2[^>]*class="[^"]*news-tit[^"]*"[^>]*>\s*<a[^>]*href="([^"]+)"', "href")
            title = self._extract_text(block, r'<h2[^>]*class="[^"]*news-tit[^"]*"[^>]*>\s*<a[^>]*>(.*?)</a>')
            if not title or not url:
                continue

            published_at_raw = self._extract_text(block, r'<p[^>]*class="[^"]*txt-date[^"]*"[^>]*>(.*?)</p>')
            summary = self._extract_text(block, r'<p[^>]*class="[^"]*lead[^"]*"[^>]*>(.*?)</p>')
            thumbnail = self._extract_attr(block, r'<div[^>]*class="[^"]*thumb[^"]*"[^>]*>.*?<img[^>]*src="([^"]+)"', "src")

            result.append(
                self._build_item(
                    source_id=self.SOURCE,
                    source_name=source.get("name", self.SOURCE_NAME),
                    article_id=self._extract_article_id(url) or article_id,
                    title=title,
                    url=self._normalize_link(url),
                    published_at=self._to_display_datetime(published_at_raw),
                    published_at_iso=self._normalize_kst_datetime(published_at_raw),
                    summary=self._strip(summary),
                    category=None,
                    category_slug=None,
                    rank=None,
                    thumbnail_url=self._normalize_link(thumbnail),
                    fallback_used=False,
                    source=source,
                )
            )
            if len(result) >= self.max_items:
                break
        return self._dedupe(result)

    def _build_item(
        self,
        source_id: str,
        source_name: str,
        article_id: str,
        title: str,
        url: str,
        published_at: str,
        published_at_iso: str,
        summary: Optional[str],
        category: Optional[str],
        category_slug: Optional[str],
        rank: Optional[int],
        thumbnail_url: Optional[str],
        fallback_used: bool,
        source: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "source": source_id,
            "source_id": source_id,
            "source_name": source_name,
            "source_type": source.get("type", "news_economy"),
            "article_id": article_id,
            "title": self._strip(title),
            "url": self._normalize_link(url),
            "published_at": self._strip(published_at),
            "published_at_iso": self._strip(published_at_iso),
            "summary": self._strip(summary),
            "category": self._strip(category),
            "category_slug": self._strip(category_slug),
            "rank": rank,
            "publisher": "hankyung",
            "collected_at": datetime.now().replace(tzinfo=timezone(timedelta(hours=9))).isoformat(),
            "fallback_used": bool(fallback_used),
            "thumbnail_url": self._strip(thumbnail_url),
            "board_or_category": self._strip(category) or "economy",
            "collection_method": "",
            "fetched_via": "live",
        }

    def _extract_text(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        return self._clean_text(match.group(1))

    def _extract_block(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        return match.group(1)

    def _extract_attr(self, text: str, pattern: str, _unused: str) -> str:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        return html.unescape(match.group(1).strip())

    def _extract_article_id(self, value: str) -> str:
        if not value:
            return ""
        match = self.ARTICLE_ID.search(str(value))
        return match.group(1) if match else ""

    def _extract_category_slug(self, block: str) -> str:
        link = self._extract_attr(block, r'<span[^>]*class="[^"]*depth3[^"]*"[^>]*>\s*<a[^>]*href="([^"]+)"', "href")
        if not link:
            return ""
        parsed = urllib.parse.urlparse(link)
        path = (parsed.path or "").strip("/")
        return path.split("/")[-1]

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        cleaned = re.sub(r"<script.*?</script>", "", str(text), flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"<style.*?</style>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        cleaned = html.unescape(cleaned)
        return self.WS.sub(" ", cleaned).strip()

    def _strip(self, value: Optional[Any]) -> Optional[str]:
        if value is None:
            return None
        value = self._clean_text(str(value))
        return value or None

    def _to_display_datetime(self, value: str) -> str:
        iso = self._normalize_kst_datetime(value)
        if not iso:
            return ""
        return iso.replace("T", " ")[:16]

    def _normalize_kst_datetime(self, value: str) -> str:
        cleaned = self._clean_text(value)
        if not cleaned:
            return ""
        for fmt in ("%Y.%m.%d %H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S%z", "%Y.%m.%d %H:%M:%S"):
            try:
                dt = datetime.strptime(cleaned, fmt)
                return dt.replace(tzinfo=timezone(timedelta(hours=9))).isoformat()
            except ValueError:
                continue
        try:
            dt = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone(timedelta(hours=9)))
            return dt.isoformat()
        except ValueError:
            return ""

    def _normalize_link(self, value: str) -> str:
        text = self._strip(value)
        if not text:
            return ""
        if text.startswith("//"):
            return f"https:{text}"
        if text.startswith("/"):
            return f"{self.BASE_URL}{text}"
        return text

    def _is_cloudflare_blocked(self, content: str) -> bool:
        return bool(self.REQUEST_MARKER.search(content))

    def _fetch_url(self, url: str) -> str:
        if self._request_count >= self.max_requests_per_run:
            raise RuntimeError("request_budget_exhausted")
        self._throttle()
        self._request_count += 1

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/115.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            content = response.read().decode("utf-8", errors="ignore")
        if self._is_cloudflare_blocked(content):
            raise RuntimeError("cloudflare_challenge")
        return content

    def _throttle(self) -> None:
        if self._last_request:
            now = time.time()
            elapsed = now - self._last_request
            if elapsed < self.min_delay_seconds:
                time.sleep(self.min_delay_seconds - elapsed)
        self._last_request = time.time()

    def _dedupe(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        result: List[Dict[str, Any]] = []
        for item in items:
            key = item.get("article_id") or item.get("url")
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    def _classify_error(self, error: Exception) -> str:
        if "request_budget_exhausted" in str(error):
            return "request_budget_exhausted"
        if isinstance(error, HTTPError):
            return f"http_{error.code}"
        if isinstance(error, URLError):
            reason = str(getattr(error, "reason", "")).lower()
            if "timed out" in reason or "timeout" in reason:
                return "timeout"
            if "forbidden" in reason or "403" in reason:
                return "http_403"
            if "refused" in reason or "10061" in reason:
                return "connection_refused"
            return "network_error"
        if isinstance(error, socket.timeout):
            return "timeout"
        if self._is_cloudflare_blocked(str(error)):
            return "cloudflare_challenge"
        return "unknown_error"

    def _save_cache(self, items: List[Dict[str, Any]]) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "source": self.SOURCE,
                "updated_at": datetime.now().isoformat(),
                "items": items,
            }
            with open(self.cache_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_cache(self) -> List[Dict[str, Any]]:
        if not self.cache_path.exists():
            return []
        try:
            with open(self.cache_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            return []
        if not isinstance(data, dict):
            return []
        items = data.get("items", [])
        if not isinstance(items, list):
            return []

        result: List[Dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            article_id = self._strip(item.get("article_id"))
            title = self._strip(item.get("title"))
            if not article_id or not title:
                continue
            result.append(
                {
                    "source": item.get("source", self.SOURCE),
                    "source_id": item.get("source_id", self.SOURCE),
                    "article_id": article_id,
                    "title": title,
                    "url": self._normalize_link(str(item.get("url", ""))),
                    "published_at": self._strip(item.get("published_at")) or "",
                    "published_at_iso": self._strip(item.get("published_at_iso")) or "",
                    "summary": self._strip(item.get("summary")),
                    "category": self._strip(item.get("category")),
                    "category_slug": self._strip(item.get("category_slug")),
                    "rank": item.get("rank"),
                    "publisher": item.get("publisher", "hankyung"),
                    "collected_at": datetime.now().replace(tzinfo=timezone(timedelta(hours=9))).isoformat(),
                    "fallback_used": True,
                    "thumbnail_url": self._strip(item.get("thumbnail_url")),
                    "board_or_category": self._strip(item.get("category")) or "economy",
                    "fetched_via": "cache",
                }
            )
        return self._dedupe(result)
