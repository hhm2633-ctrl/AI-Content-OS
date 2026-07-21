"""Low-cost Edaily collector for daily shallow intake.

Collection priority:
1) category JSON feed (`/article/MoreList`)
2) latest-article sitemap
3) realtime/category HTML fallback

Only normalized, verified fields are emitted. Unknown/failing sources fall back to cache.
"""

from __future__ import annotations

import html
import json
import re
import socket
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError


class EdailyCollector:
    BASE_URL = "https://www.edaily.co.kr"
    LATEST_SITEMAP_URL = "https://www.edaily.co.kr/sitemap/latest-article.xml"
    REALTIME_URL = "https://www.edaily.co.kr/News/RealTimeNews?tab=0&page=1"
    MORELIST_URL = "https://www.edaily.co.kr/article/MoreList?categoryCode={category_code}&page=1&pagesize=20&date="
    CATEGORY_URL = "https://www.edaily.co.kr/article/{slug}"
    CATEGORY_TO_CODE = {"stock": "16100"}
    SOURCE = "edaily"
    SOURCE_NAME = "이데일리"

    def __init__(self, timeout: int = 8, max_items: int = 25, config: Optional[Dict[str, Any]] = None):
        self.timeout = timeout
        self.max_items = max_items
        self.config = config or {}
        self.cache_path = Path("storage/cache/edaily_cache.json")
        self.last_status = self._empty_status()

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
        failures: List[str] = []
        category_items: List[Dict[str, Any]] = []
        sitemap_items: List[Dict[str, Any]] = []

        try:
            slug = self._resolve_slug(source.get("url", ""))
            category_items = self._collect_from_morelist(
                source, category_code=self._resolve_category_code(slug)
            )
        except Exception as error:
            failures.append(f"category_json_failed:{self._classify_error(error)}")

        try:
            sitemap_items = self._collect_from_sitemap(source)
        except Exception as error:
            failures.append(f"sitemap_failed:{self._classify_error(error)}")

        items = self._dedupe_items(category_items + sitemap_items)[: self.max_items]
        if items:
            if category_items and sitemap_items:
                method = "edaily_category_json_plus_sitemap"
            elif category_items:
                method = "edaily_category_json"
            else:
                method = "edaily_latest_sitemap"
            self._save_cache(items)
            self._record_success(items, method)
            return items

        try:
            items = self._collect_from_realtime_fallback(source)
            if items:
                self._record_success(items, "edaily_realtime_fallback")
                return items
        except Exception as error:
            failures.append(f"realtime_fallback_failed:{self._classify_error(error)}")

        cached = self._load_cache()
        if cached:
            self.last_status["used_cache"] = True
            self.last_status["fallback_reason"] = failures[0] if failures else "cache_fallback"
            self.last_status["failed_reason"] = self.last_status["fallback_reason"]
            self.last_status["collection_method"] = "edaily_cache"
            self.last_status["count"] = len(cached)
            return cached

        reason = failures[0] if failures else "no_results"
        self.last_status["failed_reason"] = reason
        self.last_status["error_message"] = reason
        self.last_status["collection_method"] = "edaily_no_data"
        return []

    def _record_success(self, items: List[Dict[str, Any]], method: str) -> None:
        self.last_status["success"] = True
        self.last_status["count"] = len(items)
        self.last_status["collection_method"] = method

    def _collect_from_sitemap(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_xml = self._fetch_url(self.LATEST_SITEMAP_URL)
        root = ET.fromstring(raw_xml)
        ns = {
            "s": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "news": "http://www.google.com/schemas/sitemap-news/0.9",
            "image": "http://www.google.com/schemas/sitemap-image/1.1",
        }
        results: List[Dict[str, Any]] = []
        for url_node in root.findall("s:url", ns):
            if len(results) >= self.max_items:
                break

            loc = (url_node.findtext("s:loc", "", namespaces=ns) or "").strip()
            title = (url_node.findtext("news:news/news:title", "", namespaces=ns) or "").strip()
            publication_date = (
                url_node.findtext("news:news/news:publication_date", "", namespaces=ns) or ""
            ).strip()
            if not loc or not title:
                continue

            article_id = self._extract_news_id(loc)
            if not self._valid_news_id(article_id):
                continue

            parsed_url = (
                f"https://www.edaily.co.kr/News/Read?newsId={article_id}&mediaCodeNo=257"
            )
            item = self._build_item(
                source=source,
                news_id=article_id,
                url=parsed_url,
                title=title,
                published_at=self._normalize_iso_timestamp(publication_date),
                summary=None,
                list_type="latest",
                collection_method="edaily_latest_sitemap",
                publisher=source.get("name") or self.SOURCE_NAME,
                thumbnail_url=url_node.findtext("image:image/image:loc", "", namespaces=ns),
            )
            results.append(item)

        return self._dedupe_items(results)

    def _collect_from_morelist(self, source: Dict[str, Any], category_code: str) -> List[Dict[str, Any]]:
        url = self.MORELIST_URL.format(category_code=category_code)
        raw = self._fetch_url(url)
        payload = json.loads(raw)
        if not isinstance(payload, list):
            return []

        results: List[Dict[str, Any]] = []
        for item in payload[: self.max_items]:
            if not isinstance(item, dict):
                continue
            news_id = str(item.get("NEWS_ID", "")).strip()
            if not self._valid_news_id(news_id):
                continue
            title = self._clean_text(item.get("HEADLINE_HTML_DEL", "") or item.get("HEADLINE", ""))
            if not title:
                continue

            category_path = self._collect_category_path(item)
            published_at = self._normalize_kst_to_iso(item.get("ConfirmDateFormat01") or item.get("ConfirmDateFormat02", ""))
            results.append(
                self._build_item(
                    source=source,
                    news_id=news_id,
                    url=f"{self.BASE_URL}/News/Read?newsId={news_id}&mediaCodeNo=257",
                    title=title,
                    published_at=published_at,
                    summary=self._clean_text(item.get("BODY_SHORT", "")) or None,
                    list_type="category",
                    category_path=category_path,
                    category_slug=self._resolve_slug(source.get("url", "")),
                    reporter=self._clean_text(item.get("Journalist", "")) or None,
                    reporter_id=self._clean_text(item.get("JID", "")) or None,
                    thumbnail_url=self._clean_text(item.get("IMG_B", "")) or None,
                    publisher=source.get("name") or self.SOURCE_NAME,
                )
            )
        return self._dedupe_items(results)

    def _collect_from_realtime_fallback(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw = self._fetch_url(self.REALTIME_URL)
        if not raw:
            return []
        section_match = re.search(
            r'<section[^>]+id="taparea_a"[^>]*>(.*?)</section>',
            raw,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not section_match:
            return []
        section = section_match.group(1)
        anchors = re.finditer(
            r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            section,
            flags=re.IGNORECASE | re.DOTALL,
        )
        results = []
        for index, match in enumerate(anchors, start=1):
            href = (match.group(1) or "").strip()
            html_snippet = match.group(2) or ""
            title = self._clean_text(re.sub(r"<[^>]+>", "", html_snippet))
            news_id = self._extract_news_id(href)
            if not self._valid_news_id(news_id) or not title:
                continue
            results.append(
                self._build_item(
                    source=source,
                    news_id=news_id,
                    url=f"{self.BASE_URL}/News/Read?newsId={news_id}&mediaCodeNo=257",
                    title=title,
                    published_at="",
                    summary=None,
                    list_type="trending",
                    category_slug="stock",
                    thumbnail_url=None,
                    publisher=source.get("name") or self.SOURCE_NAME,
                )
            )
            if len(results) >= self.max_items:
                break
        return self._dedupe_items(results)

    def _build_item(
        self,
        source: Dict[str, Any],
        news_id: str,
        url: str,
        title: str,
        published_at: str,
        summary: Optional[str],
        list_type: str,
        collection_method: str = "edaily",
        category_path: Optional[List[str]] = None,
        category_slug: Optional[str] = None,
        reporter: Optional[str] = None,
        reporter_id: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        publisher: Optional[str] = None,
        rank: Optional[int] = None,
    ) -> Dict[str, Any]:
        item: Dict[str, Any] = {
            "source": self.SOURCE,
            "source_id": source.get("source_id", self.SOURCE),
            "source_name": source.get("name", self.SOURCE_NAME),
            "news_id": news_id,
            "url": url,
            "link": url,
            "title": self._clean_text(title),
            "published_at": published_at,
            "collected_at": datetime.now().replace(tzinfo=timezone.utc).astimezone().isoformat(),
            "list_type": list_type,
            "collection_method": collection_method,
        }
        if publisher:
            item["publisher"] = publisher
        if summary:
            item["summary"] = summary
        if category_path:
            item["category_path"] = category_path
        if category_slug:
            item["category_slug"] = category_slug
        if reporter:
            item["reporter"] = reporter
        if reporter_id:
            item["reporter_id"] = reporter_id
        if thumbnail_url:
            item["thumbnail_url"] = thumbnail_url
        if rank is not None:
            item["rank"] = rank
        return item

    def _dedupe_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        deduped: List[Dict[str, Any]] = []
        for item in items:
            key = item.get("news_id") or item.get("url")
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    def _collect_category_path(self, item: Dict[str, Any]) -> List[str]:
        path = []
        for field in ("Category1CodeName", "Category2CodeName", "Category3CodeName"):
            part = self._clean_text(item.get(field, ""))
            if part:
                path.append(part)
        return path

    def _resolve_slug(self, source_url: str) -> str:
        path = source_url.split("?", 1)[0].rstrip("/")
        m = re.search(r"/article/([^/?#]+)", path)
        if m:
            slug = m.group(1)
            if slug in self.CATEGORY_TO_CODE:
                return slug
        return "stock"

    def _resolve_category_code(self, slug: str) -> str:
        return self.CATEGORY_TO_CODE.get(slug, "16100")

    def _extract_news_id(self, value: str) -> str:
        if not value:
            return ""
        query = urllib.parse.unquote(value)
        if "newsId=" in query:
            qs = urllib.parse.urlparse(query).query
            params = urllib.parse.parse_qs(qs)
            candidates = params.get("newsId") or []
            if candidates:
                return re.sub(r"\D", "", str(candidates[0]))
        if "newsId" in query:
            match = re.search(r"newsId[:=](\\d{17})", query)
            if match:
                return match.group(1)
        matches = re.findall(r"\b(\d{17})\b", query)
        return matches[0] if matches else ""

    def _valid_news_id(self, value: str) -> bool:
        return bool(re.fullmatch(r"\d{17}", str(value)))

    def _normalize_kst_to_iso(self, value: str) -> str:
        if not value:
            return ""
        parsed = self._to_datetime(value)
        if not parsed:
            return ""
        return parsed.isoformat()

    def _to_datetime(self, value: str) -> Optional[datetime]:
        cleaned = self._clean_text(value).replace(" ", " ")
        kst = cleaned.replace("오전", "AM").replace("오후", "PM")
        for fmt in ("%Y-%m-%d %p %I:%M:%S", "%y.%m.%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(kst, fmt)
                return dt.replace(tzinfo=timezone(timedelta(hours=9)))
            except ValueError:
                continue
        try:
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone(timedelta(hours=9)))
            return dt
        except ValueError:
            return None

    def _normalize_iso_timestamp(self, value: str) -> str:
        parsed = self._to_datetime(value)
        if not parsed:
            return ""
        return parsed.isoformat()

    def _clean_text(self, text: Any) -> str:
        if not text:
            return ""
        text = re.sub(r"<script.*?</script>", "", str(text), flags=re.DOTALL)
        text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        return html.unescape(text).replace("\n", " ").replace("\t", " ").strip()

    def _fetch_url(self, url: str) -> str:
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
            return response.read().decode("utf-8", errors="ignore")

    def _classify_error(self, error: Exception) -> str:
        if isinstance(error, HTTPError):
            return f"http_{error.code}"
        if isinstance(error, URLError):
            reason = str(error.reason).lower()
            if "timed out" in reason or "timeout" in reason:
                return "timeout"
            if "refused" in reason or "10061" in reason:
                return "connection_refused"
            return "network_error"
        if isinstance(error, socket.timeout):
            return "timeout"
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
        items = data.get("items", [])
        if not isinstance(items, list):
            return []
        results = []
        for item in items:
            if isinstance(item, dict) and item.get("news_id"):
                results.append(item)
        return results
