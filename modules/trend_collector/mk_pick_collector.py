"""Low-cost MK Pick collector for policy-safe daily collection."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class MkPickCollector:
    SOURCE = "mk_economy"
    SOURCE_NAME = "매일경제"
    BASE_URL = "https://www.mk.co.kr"

    PICK_URL = f"{BASE_URL}/news/pick"
    PICK_ALL_URL = f"{BASE_URL}/news/pick/all"
    CACHE_PATH = Path("storage/cache/mk_economy_cache.json")

    ITEM_LINK = re.compile(
        r"""<a[^>]+href="([^"]*?/news/pick/\d+)"[^>]*>(.*?)</a>""",
        re.IGNORECASE | re.DOTALL,
    )
    TITLE = re.compile(r"""<h3[^>]+class="[^"]*\bmain_tit\b[^"]*"[^>]*>(.*?)</h3>""", re.IGNORECASE | re.DOTALL)
    SUMMARY = re.compile(r"""<p[^>]+class="[^"]*\bmain_desc\b[^"]*"[^>]*>(.*?)</p>""", re.IGNORECASE | re.DOTALL)
    PUBLISHED_AT = re.compile(
        r"""<span[^>]+class="[^"]*\bdate\b[^"]*"[^>]*>(.*?)</span>""",
        re.IGNORECASE | re.DOTALL,
    )
    THUMBNAIL = re.compile(
        r"""<div[^>]+class="[^"]*\bmain_thumb\b[^"]*"[^>]*>.*?<img[^>]+src="([^"]+)"[^>]*>""",
        re.IGNORECASE | re.DOTALL,
    )
    LINK_TAG = re.compile(r'<img[^>]+src="([^"]+)"[^>]*>', re.IGNORECASE)
    ARTICLE_ID = re.compile(r"/news/pick/([0-9]+)")
    SPACES = re.compile(r"\s+")

    def __init__(
        self,
        timeout: int = 8,
        max_items: int = 20,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.timeout = timeout
        self.max_items = max_items
        self.config = config or {}
        self.cache_path = Path(str(self.config.get("cache_path", self.CACHE_PATH)))
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

        collected: List[Dict[str, Any]] = []
        for index_url in (self.PICK_URL, self.PICK_ALL_URL):
            try:
                raw_html = self._fetch_url(index_url)
            except Exception as error:
                failures.append(self._classify_error(error))
                continue

            parsed = self._parse(raw_html)
            if parsed:
                collected.extend(parsed)
                if len(collected) >= self.max_items:
                    break

        collected = self._dedupe(self._coerce_items(collected, source)[: self.max_items])
        if collected:
            for item in collected:
                item["collection_method"] = "mk_economy_pick_html"
                item["fetched_via"] = "live"
            self.last_status["success"] = True
            self.last_status["count"] = len(collected)
            self.last_status["collection_method"] = "mk_economy_pick_html"
            self._save_cache(collected)
            return collected

        cache_items = self._load_cache(source)
        if cache_items:
            for item in cache_items:
                item["fetched_via"] = "cache"
            self.last_status["used_cache"] = True
            self.last_status["success"] = False
            self.last_status["fallback_reason"] = failures[0] if failures else "cache_fallback"
            self.last_status["failed_reason"] = self.last_status["fallback_reason"]
            self.last_status["error_message"] = self.last_status["fallback_reason"]
            self.last_status["collection_method"] = f"{self.SOURCE}_cache"
            self.last_status["count"] = len(cache_items)
            return cache_items

        self.last_status["failed_reason"] = failures[0] if failures else "no_verified_items"
        self.last_status["error_message"] = self.last_status["failed_reason"]
        self.last_status["collection_method"] = f"{self.SOURCE}_no_data"
        return []

    def _coerce_items(
        self,
        items: List[Dict[str, Any]],
        source: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for item in items:
            article_id = str(item.get("article_id") or "").strip()
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            if not article_id or not title or not url:
                continue

            result.append(
                {
                    "source": self.SOURCE,
                    "source_id": self.SOURCE,
                    "source_name": source.get("name", self.SOURCE_NAME),
                    "source_type": source.get("type", "news_economy"),
                    "publisher": self.SOURCE_NAME,
                    "article_id": article_id,
                    "title": title,
                    "url": self._normalize_link(url),
                    "summary": self._strip(item.get("summary")),
                    "thumbnail_url": self._strip(item.get("thumbnail_url")),
                    "published_at": self._strip(item.get("published_at")),
                    "published_at_iso": self._normalize_list_date(item.get("published_at")),
                    "collected_at": datetime.now().replace(tzinfo=timezone(timedelta(hours=9))).isoformat(),
                    "collection_method": "",
                    "fetched_via": "",
                    "board_or_category": "경제",
                    "fallback_used": False,
                }
            )
        return result

    def _parse(self, raw_html: str) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for href, block in self.ITEM_LINK.findall(raw_html or ""):
            if not self._is_authorized_pick_url(href):
                continue
            title_match = self.TITLE.search(block)
            summary_match = self.SUMMARY.search(block)
            published_at_match = self.PUBLISHED_AT.search(block)
            if not title_match:
                continue
            article_id = self.ARTICLE_ID.findall(href)
            if not article_id:
                continue
            item = {
                "article_id": article_id[0],
                "url": href,
                "title": self._clean_text(title_match.group(1)),
                "summary": self._clean_text(summary_match.group(1)) if summary_match else None,
                "published_at": (
                    self._clean_text(published_at_match.group(1)) if published_at_match else None
                ),
                "thumbnail_url": self._extract_thumbnail(block),
            }
            result.append(item)
        return result

    def _is_authorized_pick_url(self, href: str) -> bool:
        value = (href or "").strip()
        if not value:
            return False

        if value.startswith("//"):
            value = f"https:{value}"

        return bool(re.match(r"^(?:https?://www\.mk\.co\.kr)?/news/pick/\d+$", value))

    def _extract_thumbnail(self, block: str) -> Optional[str]:
        thumb_match = self.THUMBNAIL.search(block)
        if not thumb_match:
            generic_img = self.LINK_TAG.search(block)
            if not generic_img:
                return None
            return self._normalize_src(generic_img.group(1))
        return self._normalize_src(thumb_match.group(1))

    def _normalize_link(self, value: str) -> str:
        if not value:
            return ""
        value = value.strip()
        if value.startswith("//"):
            return f"https:{value}"
        if value.startswith("/"):
            return f"{self.BASE_URL}{value}"
        return value

    def _normalize_src(self, value: str) -> Optional[str]:
        if not value:
            return None
        value = self._clean_text(value)
        if value.startswith("//"):
            return f"https:{value}"
        return value

    @classmethod
    def _normalize_list_date(cls, value: Any) -> Optional[str]:
        cleaned = cls._strip(value)
        if not cleaned:
            return None
        try:
            return datetime.strptime(cleaned, "%Y.%m.%d").date().isoformat()
        except ValueError:
            return None

    def _fetch_url(self, url: str) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": "MK Economy Pick Policy-Safe Collector",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        with urlopen(request, timeout=self.timeout) as response:
            return response.read().decode("utf-8", errors="ignore")

    def _dedupe(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        deduped: List[Dict[str, Any]] = []
        for item in items:
            key = item.get("article_id") or item.get("url")
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    def _save_cache(self, items: List[Dict[str, Any]]) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "source": self.SOURCE,
                "updated_at": datetime.now().replace(tzinfo=timezone(timedelta(hours=9))).isoformat(),
                "items": items,
            }
            with open(self.cache_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
        except Exception:
            pass

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

        raw_items = payload.get("items")
        if not isinstance(raw_items, list):
            return []

        parsed = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            parsed.append(self._build_cache_item(item, source))
        return [item for item in parsed if item]

    def _build_cache_item(self, item: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
        title = self._strip(item.get("title"))
        article_id = self._strip(item.get("article_id"))
        url = self._normalize_link(str(item.get("url", "")))
        if not title or not article_id or not url:
            return {}
        return {
            "source": self.SOURCE,
            "source_id": self.SOURCE,
            "source_name": source.get("name", self.SOURCE_NAME),
            "source_type": source.get("type", "news_economy"),
            "publisher": self.SOURCE_NAME,
            "article_id": article_id,
            "title": title,
            "url": url,
            "summary": self._strip(item.get("summary")),
            "thumbnail_url": self._strip(item.get("thumbnail_url")),
            "published_at": self._strip(item.get("published_at")),
            "published_at_iso": self._strip(item.get("published_at_iso")),
            "collected_at": datetime.now().replace(tzinfo=timezone(timedelta(hours=9))).isoformat(),
            "collection_method": f"{self.SOURCE}_cache",
            "fetched_via": "cache",
            "board_or_category": "경제",
            "fallback_used": True,
        }

    @classmethod
    def _clean_text(cls, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", " ", str(text))
        text = cls.SPACES.sub(" ", text)
        return text.strip()

    @classmethod
    def _strip(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        cleaned = cls._clean_text(str(value))
        return cleaned or None

    @classmethod
    def _classify_error(cls, error: Exception) -> str:
        if isinstance(error, HTTPError):
            return f"http_{error.code}"
        if isinstance(error, URLError):
            reason = str(getattr(error, "reason", "")).lower()
            if "timed out" in reason or "timeout" in reason:
                return "timeout"
            return "network_error"
        return "network_error"
