"""Fallback-first collectors for bounded public beauty editorial lists."""

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


class PublicBeautyEditorialCollector:
    """Parse only metadata rendered on a public category/list page."""

    SOURCE_ID = "beauty_editorial"
    SOURCE_NAME = "Beauty Editorial"
    DEFAULT_URL = ""
    ALLOWED_HOSTS = frozenset()
    CACHE_FILENAME = "beauty_editorial_cache.json"
    COLLECTION_METHOD = "beauty_public_editorial_list"
    CACHE_METHOD = "beauty_editorial_cache"
    NO_DATA_METHOD = "beauty_no_data"
    ATTRIBUTION = "Public beauty editorial list"
    LIVE_REJECTION_REASON = "live_activation_not_approved"
    ARTICLE_PATH_PATTERN = re.compile(
        r"^/20\d{2}/\d{1,2}/\d{1,2}/[^/?#]+/?$",
        flags=re.IGNORECASE,
    )
    BEAUTY_CATEGORY_PATTERN = re.compile(
        r"(?:makeup|skin\s*care|skincare|hair|bath\s*&?\s*body|body|"
        r"fragrance|nail|best\s+of\s+beauty|뷰티\s*(?:트렌드|아이템|화보)|"
        r"메이크업|스킨케어|헤어|바디|향수|네일)",
        flags=re.IGNORECASE,
    )
    BEAUTY_TITLE_PATTERN = re.compile(
        r"(?:make[ -]?up|skin\s*care|skincare|\bskin\b|hair|scalp|shampoo|body\s*care|"
        r"fragrance|perfume|nails?|pedicure|manicure|hand\s*care|beauty\s*tools?|"
        r"sheet\s*masks?|face\s*masks?|메이크업|화장(?:품|법)?|립(?:스틱|밤|글로스|틴트)?|"
        r"아이섀도|블러셔|쿠션|파운데이션|컨실러|마스카라|스킨케어|피부|"
        r"선크림|자외선|세럼|앰플|토너|로션|헤어|머리(?:색|결|카락| 관리)|"
        r"두피|샴푸|트리트먼트|바디\s*케어|보디\s*케어|데오도란트|향수|"
        r"프래그런스|네일|페디큐어|매니큐어|핸드\s*케어|핸드크림|손\s*관리|"
        r"뷰티(?:템|\s*씬)?|뷰티\s*툴|브러시|퍼프|괄사|페이스\s*롤러|"
        r"마스크팩|시트\s*마스크|마스크)",
        flags=re.IGNORECASE,
    )
    RELATIONSHIP_PATTERN = re.compile(
        r"(?:연애|연인|애인|남친|여친|이별|썸|관계|relationship|dating)",
        flags=re.IGNORECASE,
    )
    DIET_FOOD_PATTERN = re.compile(
        r"(?:다이어트|식단|체중|뼈말라|삼계탕|채소|과일|음식|먹어|먹는|영양|"
        r"diet|weight\s*loss|food|recipe)",
        flags=re.IGNORECASE,
    )
    WELLNESS_PATTERN = re.compile(
        r"(?:필라테스|요가|헬스|운동|정신\s*건강|명상|수면|웰니스|"
        r"pilates|yoga|workout|fitness|wellness|mental\s*health)",
        flags=re.IGNORECASE,
    )
    APPAREL_PATTERN = re.compile(
        r"(?:카디건|가디건|원피스|드레스|재킷|자켓|셔츠|바지|스커트|신발|"
        r"의류|패션|cardigan|dress|jacket|shirt|pants|skirt|shoes?|fashion)",
        flags=re.IGNORECASE,
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
        self.cache_path = Path(
            self.config.get("cache_path", f"storage/cache/{self.CACHE_FILENAME}")
        )
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
        self.last_status = self._empty_status()
        self.last_status["attempted"] = True
        failures: List[str] = []
        rows: List[Dict[str, Any]] = []

        if self._live_fetch_allowed(source):
            try:
                _, payload = self.fetcher(self._resolve_url(source))
                rows = self.parser(payload)
                if not rows:
                    failures.append("parse_failed")
            except Exception as error:
                failures.append(self._classify_error(error))
        else:
            failures.append(self.LIVE_REJECTION_REASON)

        if rows:
            items = self._build_items(rows, source, self.COLLECTION_METHOD, False)
            if items:
                self.last_status.update(
                    {
                        "success": True,
                        "count": len(items),
                        "collection_method": self.COLLECTION_METHOD,
                    }
                )
                self._set_diagnostic("", "ok")
                return items
            failures.append("parse_failed")

        cached = self._load_cache(source)
        if cached:
            reason = self._primary_reason(failures)
            self.last_status.update(
                {
                    "success": True,
                    "count": len(cached),
                    "fallback_reason": reason,
                    "final_error_type": reason,
                    "collection_method": self.CACHE_METHOD,
                    "used_cache": True,
                }
            )
            self._set_diagnostic(reason, "fallback_used")
            return cached

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
        document = str(raw_html or "")
        if not document.strip():
            return []

        blocks = [
            match.group(0)
            for match in re.finditer(
                r"<li\b[^>]*>[\s\S]*?</li>", document, flags=re.IGNORECASE
            )
        ]
        blocks.append(document)
        rows: List[Dict[str, Any]] = []
        seen = set()
        for block in blocks:
            metadata_block = "" if block == document else block
            for anchor in re.finditer(
                r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',
                block,
                flags=re.IGNORECASE,
            ):
                link = self._normalize_link(anchor.group(1))
                if not link or link in seen:
                    continue
                title_match = re.search(
                    r"<h[2-4]\b[^>]*>([\s\S]*?)</h[2-4]>",
                    anchor.group(2),
                    flags=re.IGNORECASE,
                )
                title = self._clean_text(title_match.group(1)) if title_match else ""
                if not title:
                    continue
                seen.add(link)
                visible_date = self._extract_visible_date(
                    metadata_block, anchor.group(2)
                )
                category = self._extract_category(
                    metadata_block, anchor.group(2)
                )
                topic_eligible, eligibility_reason = self._editorial_topic_eligibility(
                    title, category
                )
                rows.append(
                    {
                        "title": title,
                        "link": link,
                        "category": category,
                        "published_at": visible_date,
                        "visible_date": visible_date,
                        "summary": self._extract_summary(
                            metadata_block, anchor.group(2)
                        ),
                        "editorial_topic_eligible": topic_eligible,
                        "editorial_topic_eligibility_reason": eligibility_reason,
                        "rank_position": len(rows) + 1,
                        "rank_basis": "visible_list_order",
                        "attribution": self.ATTRIBUTION,
                    }
                )
                if len(rows) >= self.max_items:
                    return rows
        return rows

    def _editorial_topic_eligibility(
        self,
        title: Any,
        category: Any,
    ) -> Tuple[bool, str]:
        clean_title = self._clean_text(title)
        clean_category = self._clean_text(category)
        # A generic wellness category is not a beauty signal on its own.
        if clean_category and self.BEAUTY_CATEGORY_PATTERN.search(clean_category):
            return True, "beauty_category_signal"
        if self.BEAUTY_TITLE_PATTERN.search(clean_title):
            return True, "beauty_title_keyword"
        if self.RELATIONSHIP_PATTERN.search(clean_title):
            return False, "relationship_topic"
        if self.DIET_FOOD_PATTERN.search(clean_title):
            return False, "diet_or_food_topic"
        if self.WELLNESS_PATTERN.search(clean_title) or re.search(
            r"(?:웰니스|wellness)", clean_category, flags=re.IGNORECASE
        ):
            return False, "generic_wellness_topic"
        if self.APPAREL_PATTERN.search(clean_title) or re.search(
            r"(?:패션|fashion|apparel)", clean_category, flags=re.IGNORECASE
        ):
            return False, "fashion_apparel_topic"
        return False, "no_consumer_beauty_signal"

    def _extract_category(self, block: str, anchor_html: str) -> Optional[str]:
        for candidate in (anchor_html, block):
            match = re.search(
                r'<(?:p|span)\b[^>]*class=["\'][^"\']*category[^"\']*["\'][^>]*>([\s\S]*?)</(?:p|span)>',
                candidate,
                flags=re.IGNORECASE,
            )
            if match:
                value = self._clean_text(match.group(1))
                if value:
                    return value
        # Vogue's highlighted card renders category/date as two plain spans.
        pair = re.search(
            r"<p\b[^>]*>\s*<span[^>]*>([\s\S]*?)</span>\s*"
            r"<span[^>]*>\s*20\d{2}[./-]\d{1,2}[./-]\d{1,2}\s*</span>",
            anchor_html,
            flags=re.IGNORECASE,
        )
        value = self._clean_text(pair.group(1)) if pair else ""
        return value or None

    def _extract_visible_date(self, block: str, anchor_html: str) -> Optional[str]:
        for candidate in (anchor_html, block):
            match = re.search(
                r"\b20\d{2}[./-]\d{1,2}[./-]\d{1,2}\b", self._clean_text(candidate)
            )
            if match:
                return match.group(0)
        return None

    def _extract_summary(self, block: str, anchor_html: str) -> Optional[str]:
        for candidate in (anchor_html, block):
            match = re.search(
                r'<p\b[^>]*class=["\'][^"\']*(?:summary|premble|description|excerpt)[^"\']*["\'][^>]*>([\s\S]*?)</p>',
                candidate,
                flags=re.IGNORECASE,
            )
            if match:
                value = self._clean_text(match.group(1))
                if value:
                    return value
        return None

    def _build_items(
        self,
        rows: List[Dict[str, Any]],
        source: Dict[str, Any],
        method: str,
        is_fallback: bool,
    ) -> List[Dict[str, Any]]:
        collected_at = datetime.now().astimezone().isoformat()
        items: List[Dict[str, Any]] = []
        for row in rows[: self.max_items]:
            title = self._clean_text(row.get("title"))
            link = self._normalize_link(row.get("link"))
            rank = self._positive_int(row.get("rank_position"))
            if not title or not link or rank is None:
                continue
            topic_eligible, eligibility_reason = self._editorial_topic_eligibility(
                title, row.get("category") or row.get("section_category")
            )
            items.append(
                {
                    "keyword": title,
                    "title": title,
                    "link": link,
                    "url": link,
                    "category": self._nullable_text(row.get("category")),
                    "section_category": self._nullable_text(row.get("category")),
                    "published_at": self._nullable_text(
                        row.get("published_at") or row.get("visible_date")
                    ),
                    "visible_date": self._nullable_text(
                        row.get("visible_date") or row.get("published_at")
                    ),
                    "summary": self._nullable_text(row.get("summary")),
                    "editorial_topic_eligible": topic_eligible,
                    "editorial_topic_eligibility_reason": eligibility_reason,
                    "rank_position": rank,
                    "rank": rank,
                    "rank_basis": "visible_list_order",
                    "publisher": self.SOURCE_NAME,
                    "attribution": self.ATTRIBUTION,
                    "source_id": str(source.get("source_id") or self.SOURCE_ID),
                    "source_name": str(source.get("name") or self.SOURCE_NAME),
                    "source_type": str(
                        source.get("type") or "consumer_beauty_editorial"
                    ),
                    "collection_method": method,
                    "is_fallback": bool(is_fallback),
                    "collected_at": collected_at,
                }
            )
        return items

    def _normalize_link(self, value: Any) -> str:
        link = html.unescape(str(value or "").strip())
        if link.startswith("//"):
            link = f"https:{link}"
        elif link.startswith("/"):
            link = urllib.parse.urljoin(self.DEFAULT_URL, link)
        parsed = urllib.parse.urlparse(link)
        if parsed.scheme not in {"http", "https"}:
            return ""
        if (parsed.hostname or "").lower() not in self.ALLOWED_HOSTS:
            return ""
        if not self.ARTICLE_PATH_PATTERN.fullmatch(parsed.path or ""):
            return ""
        return urllib.parse.urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, "", "", "")
        )

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
            updated = datetime.fromisoformat(str(value))
            now = datetime.now().astimezone() if updated.tzinfo else datetime.now()
            age = now - updated
            return 0 <= age.total_seconds() <= self.cache_ttl_seconds
        except Exception:
            return False

    def _fetch_url(self, url: str) -> Tuple[str, str]:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Encoding": "identity",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            raw = response.read()
            charset = ""
            try:
                charset = response.headers.get_content_charset() or ""
            except Exception:
                charset = ""
            for encoding in (charset, "utf-8", "cp949"):
                if not encoding:
                    continue
                try:
                    return response.geturl(), raw.decode(encoding)
                except (LookupError, UnicodeDecodeError):
                    continue
            return response.geturl(), raw.decode("utf-8", errors="replace")

    def _resolve_url(self, source: Dict[str, Any]) -> str:
        candidate = str(source.get("url") or self.DEFAULT_URL).strip()
        parsed = urllib.parse.urlparse(candidate)
        if parsed.scheme in {"http", "https"} and (
            parsed.hostname or ""
        ).lower() in self.ALLOWED_HOSTS:
            return candidate
        return self.DEFAULT_URL

    def _live_fetch_allowed(self, source: Dict[str, Any]) -> bool:
        return bool(
            self.config.get("allow_live_fetch", False)
            or source.get("allow_live_fetch", False)
        )

    def _set_diagnostic(self, reason: str, status: str) -> None:
        self.last_status["service_diagnostic"] = (
            self.service_diagnostic.build_diagnostic_from_reason(
                service=self.SOURCE_ID, reason=reason, status=status
            )
        )

    def _clean_text(self, value: Any) -> str:
        text = str(value or "")
        text = re.sub(
            r"<script.*?</script>|<style.*?</style>", "", text, flags=re.I | re.S
        )
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", html.unescape(text)).strip()

    def _nullable_text(self, value: Any) -> Optional[str]:
        value = self._clean_text(value)
        return value or None

    def _positive_int(self, value: Any) -> Optional[int]:
        try:
            parsed = int(value)
            return parsed if parsed > 0 else None
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
            "connection_refused",
            "timeout",
            "network_error",
            "parse_failed",
            "unknown_error",
        ):
            if reason in failures:
                return reason
        return failures[0]


class AllureBeautyCollector(PublicBeautyEditorialCollector):
    SOURCE_ID = "allure_beauty"
    SOURCE_NAME = "Allure Korea"
    DEFAULT_URL = "https://www.allurekorea.com/beauty/"
    ALLOWED_HOSTS = frozenset({"allurekorea.com", "www.allurekorea.com"})
    CACHE_FILENAME = "allure_beauty_editorial_cache.json"
    COLLECTION_METHOD = "allure_beauty_public_list"
    CACHE_METHOD = "allure_beauty_cache"
    NO_DATA_METHOD = "allure_beauty_no_data"
    ATTRIBUTION = "Allure Korea Beauty public list"
