import html
import json
import re
import socket
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError

from modules.common.service_diagnostic import ServiceDiagnostic


class NateNewsRankCollector:
    """Low-cost HTML collector for Nate News ranking pages.

    This collector is constrained by the fixture-first contract:
    - server-rendered static HTML parsing
    - no fabricated metrics
    - failures are diagnostic, non-fatal
    - fallback chain: cache -> settings keyword -> placeholder
    """

    def __init__(self, timeout: int = 8, max_items: int = 30, config: Optional[Dict[str, Any]] = None):
        self.timeout = timeout
        self.max_items = max_items
        self.config = config or {}
        self.service_diagnostic = ServiceDiagnostic()
        self.cache_path = Path("storage/cache/nate_news_rank_cache.json")
        self.last_status = self._empty_status()
        self.valid_categories = {
            "all",
            "sisa",
            "pol",
            "eco",
            "soc",
            "int",
            "its",
            "pho",
            "spo",
            "ent",
        }
        self.allowed_rank_types = {"interest", "cmt"}
        self.url_template = "https://news.nate.com/rank/{rank_type}?sc={sc}&p=day&date={date}"
        self.source_name = "Nate News Rank"

    def collect(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.last_status = self._empty_status()
        self.last_status["attempted"] = True

        errors: List[Dict[str, str]] = []
        items: List[Dict[str, Any]] = []
        results: List[Dict[str, Any]] = []

        category = self._extract_category(source.get("url", ""))
        rank_type = self._extract_rank_type(source.get("url", ""))
        today = self._extract_date()
        requested_url = self.url_template.format(
            rank_type=rank_type,
            sc=category,
            date=today,
        )

        if self._live_collection_allowed():
            try:
                fetched_url, raw_html = self._fetch_url(requested_url)
            except Exception as error:
                errors.append({"reason": self._classify_error(error), "message": str(error)})
            else:
                if not self._is_expected_rank_endpoint(fetched_url, rank_type, category, today):
                    errors.append(
                        {
                            "reason": "redirected_url",
                            "message": f"Unexpected URL for Nate rank request: {fetched_url}",
                        }
                    )
                else:
                    parsed_items = self._parse_rank_page(raw_html, category)
                    if parsed_items:
                        results.extend(self._build_items(parsed_items, source, rank_type))
                    else:
                        errors.append({"reason": "empty_result", "message": "No parseable items."})

        else:
            errors.append({"reason": "blocked_by_contract", "message": "live_collection_blocked_by_policy"})

        deduped = self._dedupe(results)[: self.max_items]
        if deduped:
            self.last_status["success"] = True
            self.last_status["count"] = len(deduped)
            self.last_status["collection_method"] = "nate_news_rank_html"
            self._save_cache(deduped)
            self._record_diagnostic()
            return deduped

        cache_items = self._load_cache(source)
        if cache_items:
            self.last_status["used_cache"] = True
            self.last_status["collection_method"] = "nate_news_rank_cache"
            self.last_status["count"] = len(cache_items)
            self.last_status["count"] = len(cache_items)
            self.last_status["failed_reason"] = self._primary_failed_reason(errors)
            self.last_status["final_error_type"] = self.last_status["failed_reason"]
            self.last_status["fallback_reason"] = self.last_status["failed_reason"]
            self.last_status["success"] = False
            self._record_diagnostic()
            return cache_items

        settings_items = self._build_settings_fallback(source, self._primary_failed_reason(errors))
        if settings_items:
            self.last_status["collection_method"] = "settings_keyword_fallback"
            self.last_status["fallback_reason"] = self._primary_failed_reason(errors)
            self.last_status["count"] = len(settings_items)
            self._record_diagnostic()
            return settings_items

        placeholder_items = self._build_placeholder_fallback(source, self._primary_failed_reason(errors))
        self.last_status["collection_method"] = "placeholder_fallback"
        self.last_status["fallback_reason"] = self._primary_failed_reason(errors)
        self.last_status["count"] = len(placeholder_items)
        self._record_diagnostic()
        return placeholder_items

    def _empty_status(self) -> Dict[str, Any]:
        return {
            "source": "nate_news_rank",
            "attempted": False,
            "success": False,
            "count": 0,
            "error_message": "",
            "failed_reason": "",
            "fallback_reason": "",
            "final_error_type": "",
            "collection_method": "",
            "used_cache": False,
            "cache_path": str(self.cache_path),
            "service_diagnostic": {
                "service": "nate_news_rank",
                "status": "ok",
                "error_type": "",
                "safe_message": "",
                "api_key_present": None,
            },
        }

    def _live_collection_allowed(self) -> bool:
        # Explicit policy gate; defaults to fixture/cache-only.
        return bool(self.config.get("live_collection_enabled", False))

    def _extract_category(self, source_url: str) -> str:
        parsed = urllib.parse.urlparse(source_url or "")
        query = urllib.parse.parse_qs(parsed.query or "")
        category = str(query.get("sc", ["all"])[0] or "all").strip().lower()
        return category if category in self.valid_categories else "all"

    def _extract_rank_type(self, source_url: str) -> str:
        parsed = urllib.parse.urlparse(source_url or "")
        path = (parsed.path or "/rank/interest").lower()
        if "/rank/" in path:
            rank_type = path.split("/rank/", 1)[1].strip("/")
            if rank_type and rank_type in self.allowed_rank_types:
                return rank_type
        return "interest"

    def _is_expected_rank_endpoint(
        self,
        fetched_url: str,
        rank_type: str,
        category: str,
        date_text: str,
    ) -> bool:
        if not fetched_url:
            return False

        parsed = urllib.parse.urlparse(fetched_url)
        if parsed.netloc != "news.nate.com":
            return False
        if not parsed.path.startswith(f"/rank/{rank_type}"):
            return False

        query = urllib.parse.parse_qs(parsed.query or "")
        requested_sc = query.get("sc", [None])[0]
        requested_date = query.get("date", [None])[0]
        return (requested_sc == category) and (requested_date == date_text)

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
            final_url = response.geturl()
            return final_url, response.read().decode("utf-8", errors="ignore")

    def _parse_rank_page(self, raw_html: str, category: str) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        items.extend(self._parse_rich_items(raw_html, category))
        items.extend(self._parse_compact_items(raw_html, category))
        return items

    def _parse_rich_items(self, raw_html: str, category: str) -> List[Dict[str, Any]]:
        parsed: List[Dict[str, Any]] = []
        rich_html = raw_html.split('<ul class="mduSubject mduRankSubject">', 1)[0]
        block_pattern = re.compile(
            r'<div[^>]+class="[^"]*mduSubject[^"]*"[^>]*>(.*?)</div>\s*</div>',
            re.IGNORECASE | re.DOTALL,
        )
        for block in block_pattern.findall(rich_html):
            rank = self._extract_rank_from_block(block)
            if not rank:
                continue

            raw_link = self._extract_link(block)[0]
            article_id = self._extract_article_id(raw_link)
            if not article_id:
                continue

            headline = self._extract_headline(block, compact=False)
            if not headline:
                continue

            parsed.append(
                {
                    "rank": rank,
                    "title": headline,
                    "url": self._normalize_link(raw_link),
                    "article_id": article_id,
                    "publisher": self._extract_publisher(block),
                    "published_date": self._extract_published_date(block),
                    "category": category,
                    "snippet": self._extract_snippet(block),
                    "thumbnail_url": self._extract_thumbnail_url(block),
                    "rank_change": self._extract_rank_change(block),
                    "comment_count": self._extract_comment_count(block),
                }
            )

        return parsed

    def _extract_date(self) -> str:
        return datetime.now().strftime("%Y%m%d")

    def _parse_compact_items(self, raw_html: str, category: str) -> List[Dict[str, Any]]:
        parsed: List[Dict[str, Any]] = []
        compact_pattern = re.compile(
            r'<ul[^>]+class="[^"]*mduSubject[^"]*"[^>]*>(.*?)</ul>',
            re.IGNORECASE | re.DOTALL,
        )
        compact_match = compact_pattern.search(raw_html)
        if not compact_match:
            return []

        compact_html = compact_match.group(1)
        item_pattern = re.compile(
            r'<li[^>]*>.*?<dl[^>]+class="[^"]*mduRank[^"]*"[^>]*>.*?<dt[^>]*><em[^>]*>(\d+)</em>(.*?)</dl>.*?<a[^>]+href="([^"]+)"[^>]*>\s*<h2[^>]*>(.*?)</h2>.*?<span[^>]+class="medium"[^>]*>(.*?)</span>',
            re.IGNORECASE | re.DOTALL,
        )
        for rank_text, block_html, raw_link, headline, publisher in item_pattern.findall(compact_html):
            rank = self._to_int(rank_text)
            if not rank:
                continue

            article_id = self._extract_article_id(raw_link)
            if not article_id:
                continue

            title = self._clean_text(headline)
            if not title:
                continue

            parsed.append(
                {
                    "rank": rank,
                    "title": title,
                    "url": self._normalize_link(raw_link),
                    "article_id": article_id,
                    "publisher": self._clean_text(publisher),
                    "published_date": None,
                    "category": category,
                    "snippet": None,
                    "thumbnail_url": None,
                    "rank_change": self._extract_rank_change(block_html),
                    "comment_count": self._extract_comment_count(block_html),
                }
            )

        return parsed

    def _extract_rank_from_block(self, block_html: str) -> Optional[int]:
        rank_match = re.search(
            r'<dl[^>]+class="[^"]*mduRank[^"]*"[^>]*>.*?<dt[^>]*>\s*<em[^>]*>(\d+)</em>',
            block_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not rank_match:
            return None
        return self._to_int(rank_match.group(1))

    def _extract_link(self, block_html: str, compact: bool = False) -> (str, str):
        if compact:
            link_pattern = re.compile(
                r'<a[^>]+href="([^"]*//news\.nate\.com/view/[^\"]+)"',
                re.IGNORECASE,
            )
        else:
            link_pattern = re.compile(
                r'<div[^>]+class="[^"]*mlt01[^"]*"[^>]*>.*?<a[^>]+class="[^"]*lt1[^"]*"[^>]+href="([^"]+)"',
                re.IGNORECASE | re.DOTALL,
            )

        link_match = link_pattern.search(block_html)
        if not link_match:
            return "", ""

        raw_link = link_match.group(1)
        normalized = self._normalize_link(raw_link)
        return normalized, raw_link

    def _extract_headline(self, block_html: str, compact: bool = False) -> str:
        selector = r"<h2[^>]*class=\"tit\"[^>]*>(.*?)</h2>" if not compact else r"<h2[^>]*>(.*?)</h2>"
        title_match = re.search(selector, block_html, flags=re.IGNORECASE | re.DOTALL)
        if not title_match:
            return ""
        return self._clean_text(title_match.group(1))

    def _extract_snippet(self, block_html: str) -> Optional[str]:
        snippet_match = re.search(
            r"<span[^>]+class=\"tb\"[^>]*>(.*?)</span>",
            block_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not snippet_match:
            return None
        text = self._clean_text(snippet_match.group(1))
        return text or None

    def _extract_thumbnail_url(self, block_html: str) -> Optional[str]:
        thumb_match = re.search(
            r'<em[^>]+class="mediatype"[^>]*>.*?<img[^>]+src="([^"]+)"',
            block_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not thumb_match:
            return None
        return self._normalize_link(thumb_match.group(1))

    def _extract_publisher(self, block_html: str) -> str:
        pub_match = re.search(
            r'<span[^>]+class="medium"[^>]*>(.*?)</span>',
            block_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not pub_match:
            return ""
        text = self._clean_text(pub_match.group(1))
        return text.split("|")[0].strip() if text else ""

    def _extract_published_date(self, block_html: str) -> Optional[str]:
        date_match = re.search(
            r'<span[^>]+class="medium"[^>]*>.*?<em[^>]*>(\d{4}-\d{2}-\d{2})</em>',
            block_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not date_match:
            return None
        return date_match.group(1)

    def _extract_rank_change(self, block_html: str) -> Optional[Dict[str, Any]]:
        # rank change exists on interest/pop only; absent or comment mode => None
        rank_change_match = re.search(
            r'<span\s+class="(up|down|noupdown)"[^>]*>.*?</span>',
            block_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not rank_change_match:
            return None

        direction = rank_change_match.group(1).lower()
        if direction == "noupdown":
            return {"direction": "none", "delta": 0}

        value_match = re.search(r"<em>(\d+)</em>", rank_change_match.group(0), flags=re.IGNORECASE | re.DOTALL)
        if not value_match:
            return {"direction": "none", "delta": 0} if direction else None
        return {
            "direction": direction,
            "delta": self._to_int(value_match.group(1)) or 0,
        }

    def _extract_comment_count(self, block_html: str) -> Optional[int]:
        comment_match = re.search(
            r'<span[^>]+class="comment"[^>]*>.*?<em>(\d+)</em>',
            block_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not comment_match:
            return None
        return self._to_int(comment_match.group(1))

    def _extract_article_id(self, raw_url: str) -> Optional[str]:
        match = re.search(r"/view/(\d{8}n\d{5})", raw_url)
        return match.group(1) if match else None

    def _build_items(
        self,
        parsed_items: List[Dict[str, Any]],
        source: Dict[str, Any],
        rank_type: str,
    ) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []

        for item in parsed_items:
            if not all(k in item for k in ("rank", "title", "url", "article_id", "publisher", "category")):
                continue

            rank_change = item.get("rank_change")
            comment_count = item.get("comment_count")
            if rank_type != "cmt":
                comment_count = None

            item_payload = {
                "rank": item["rank"],
                "title": item["title"],
                "url": self._strip_query_param(item["url"]),
                "article_id": item["article_id"],
                "publisher": item["publisher"] or source.get("name") or self.source_name,
                "published_date": item.get("published_date"),
                "published_at": item.get("published_date") or "",
                "category": item["category"],
                "rank_change": rank_change,
                "comment_count": comment_count,
                "snippet": item.get("snippet"),
                "summary": item.get("snippet") or "",
                "thumbnail_url": item.get("thumbnail_url"),
                "collection_method": "nate_news_rank_html",
                "is_fallback": False,
                "source_id": "nate_news_rank",
                "source_name": source.get("name", self.source_name),
                "source_type": source.get("type", "news"),
                "tier": int(source.get("tier", 1)),
                "weight": int(source.get("weight", 20)),
                "base_score": 120 - item["rank"],
                "collected_at": datetime.now().isoformat(),
            }
            items.append(item_payload)

        return items

    def _build_settings_fallback(
        self,
        source: Dict[str, Any],
        fallback_reason: str,
    ) -> List[Dict[str, Any]]:
        keywords = list(self.config.get("trend_sources", []))
        if not keywords:
            fallback_source = source.get("name") or "Nate News Rank"
            keywords = [fallback_source]

        results = []
        for index, keyword in enumerate(keywords[:3], start=1):
            results.append(
                {
                    "rank": index,
                    "title": str(keyword),
                    "url": "",
                    "article_id": "",
                    "publisher": "settings.json",
                    "published_date": None,
                    "published_at": "",
                    "category": self._extract_category(source.get("url", "")),
                    "rank_change": None,
                    "comment_count": None,
                    "snippet": None,
                    "summary": "",
                    "thumbnail_url": None,
                    "collection_method": "settings_keyword_fallback",
                    "is_fallback": True,
                    "source_id": "nate_news_rank",
                    "source_name": source.get("name", self.source_name),
                    "source_type": source.get("type", "news"),
                    "tier": int(source.get("tier", 1)),
                    "weight": int(source.get("weight", 20)),
                    "base_score": 95 - index,
                    "base_score_reason": f"Nate News Rank settings fallback: {fallback_reason}",
                    "collected_at": datetime.now().isoformat(),
                }
            )
        return results

    def _build_placeholder_fallback(
        self,
        source: Dict[str, Any],
        fallback_reason: str,
    ) -> List[Dict[str, Any]]:
        placeholders = [
            "경제 동향", "사회 이슈", "국제 이슈"
        ]
        results = []
        for index, keyword in enumerate(placeholders, start=1):
            results.append(
                {
                    "rank": index,
                    "title": keyword,
                    "url": "",
                    "article_id": "",
                    "publisher": "",
                    "published_date": None,
                    "published_at": "",
                    "category": self._extract_category(source.get("url", "")),
                    "rank_change": None,
                    "comment_count": None,
                    "snippet": None,
                    "summary": "",
                    "thumbnail_url": None,
                    "collection_method": "placeholder_fallback",
                    "is_fallback": True,
                    "source_id": "nate_news_rank",
                    "source_name": source.get("name", self.source_name),
                    "source_type": source.get("type", "news"),
                    "tier": int(source.get("tier", 1)),
                    "weight": int(source.get("weight", 20)),
                    "base_score": 90 - index,
                    "base_score_reason": f"Nate News Rank placeholder fallback: {fallback_reason}",
                    "collected_at": datetime.now().isoformat(),
                }
            )
        return results

    def _save_cache(self, items: List[Dict[str, Any]]) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "source": "nate_news_rank",
                "updated_at": datetime.now().isoformat(),
                "items": [
                    {
                        "rank": item.get("rank"),
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "article_id": item.get("article_id"),
                        "publisher": item.get("publisher"),
                        "published_date": item.get("published_date"),
                        "published_at": item.get("published_at", item.get("published_date")),
                        "category": item.get("category"),
                        "rank_change": item.get("rank_change"),
                        "comment_count": item.get("comment_count"),
                        "snippet": item.get("snippet"),
                        "summary": item.get("summary", item.get("snippet")),
                        "thumbnail_url": item.get("thumbnail_url"),
                    }
                    for item in items
                ],
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
                data = json.load(handle)
            items = data.get("items", [])
        except Exception:
            return []

        if not isinstance(items, list):
            return []

        results = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = self._clean_text(item.get("title"))
            if not title:
                continue
            results.append(
                {
                    "rank": self._to_int(item.get("rank")) or 0,
                    "title": title,
                    "url": self._normalize_link(item.get("url", "")),
                    "article_id": self._extract_article_id(item.get("url", "")) or item.get("article_id", ""),
                    "publisher": self._clean_text(item.get("publisher", "")),
                    "published_date": item.get("published_date"),
                    "published_at": self._clean_text(
                        item.get("published_at", item.get("published_date", ""))
                    ),
                    "category": self._extract_category(source.get("url", "")),
                    "rank_change": item.get("rank_change"),
                    "comment_count": item.get("comment_count"),
                    "snippet": item.get("snippet"),
                    "summary": self._clean_text(
                        item.get("summary", item.get("snippet", ""))
                    ),
                    "thumbnail_url": item.get("thumbnail_url"),
                    "collection_method": "nate_news_rank_cache",
                    "is_fallback": True,
                    "source_id": "nate_news_rank",
                    "source_name": source.get("name", self.source_name),
                    "source_type": source.get("type", "news"),
                    "tier": int(source.get("tier", 1)),
                    "weight": int(source.get("weight", 20)),
                    "base_score": 85 - int(item.get("rank", 1) or 1),
                    "collected_at": datetime.now().isoformat(),
                }
            )
        return results

    def _strip_query_param(self, value: str) -> str:
        parsed = urllib.parse.urlparse(str(value))
        if not parsed.scheme and parsed.netloc:
            return value
        return urllib.parse.urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                "",
                parsed.fragment,
            )
        )

    def _normalize_link(self, link: str) -> str:
        value = html.unescape(str(link)).strip()
        if not value:
            return ""
        if value.startswith("//"):
            return "https:" + value
        if value.startswith("/"):
            return urllib.parse.urljoin("https://news.nate.com", value)
        return value

    def _to_int(self, text: Any) -> Optional[int]:
        if text is None:
            return None
        text = str(text).strip()
        if not text.isdigit():
            return None
        try:
            return int(text)
        except Exception:
            return None

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

    def _record_diagnostic(self) -> None:
        try:
            if self.last_status.get("success"):
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="nate_news_rank",
                    reason="",
                    status="ok",
                )
            else:
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="nate_news_rank",
                    reason=self.last_status.get("failed_reason", "unknown_error"),
                    status="fallback_used",
                )
                self.service_diagnostic.record(diagnostic)
            self.last_status["service_diagnostic"] = diagnostic
        except Exception as error:
            print(f"Nate News Rank Service Diagnostic Failed: {error}")

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
            "redirected_url",
            "empty_result",
            "unknown_error",
        ]
        reasons = [error.get("reason", "unknown_error") for error in errors]
        for priority in priorities:
            if priority in reasons:
                return priority
        return reasons[0]

    def _classify_error(self, error: Exception) -> str:
        if isinstance(error, HTTPError):
            if error.code == 403:
                return "http_403"
            return "network_error"

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
                return "http_403"
            if "refused" in reason_text or "10061" in reason_text:
                return "connection_refused"
            return "network_error"

        if isinstance(error, re.error):
            return "parse_error"

        return "unknown_error"
