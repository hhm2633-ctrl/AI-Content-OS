"""Fallback-first shallow collector for Olive Young's public ranking page.

Only metadata visible on the ranking surface is parsed. Product details,
reviews, images, login/browser flows, affiliate links, and market-wide trend
claims are intentionally out of scope. Live fetching is disabled unless an
explicit ``allow_live_fetch`` flag is supplied by a later integration step.
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


class OliveYoungRankingCollector:
    """Collect public retailer-ranking metadata without deep product fetches."""

    DEFAULT_URL = "https://www.oliveyoung.co.kr/store/main/getBestList.do"
    DEFAULT_CACHE_PATH = Path("storage/cache/oliveyoung_ranking_cache.json")
    LIVE_REJECTION_REASON = "live_activation_not_approved"
    SIGNAL_BASIS = "oliveyoung_retailer_ranking_page"

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
        self.parser = parser or self.parse_public_ranking
        self.cache_path = Path(self.config.get("cache_path", self.DEFAULT_CACHE_PATH))
        self.cache_ttl_seconds = max(
            0,
            int(self.config.get("cache_ttl_seconds", 6 * 60 * 60)),
        )
        self.service_diagnostic = ServiceDiagnostic()
        self.last_status = self._empty_status()

    def _empty_status(self) -> Dict[str, Any]:
        return {
            "source": "oliveyoung_ranking",
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
            "ranking_scope": "retailer_specific",
            "promotion_sensitive": True,
            "universal_trend_claimed": False,
            "service_diagnostic": self.service_diagnostic.build_diagnostic_from_reason(
                service="oliveyoung_ranking",
                reason="",
                status="ok",
            ),
        }

    def collect(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return live rows, a fresh read-only cache fallback, or an empty list."""
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
                rows,
                source,
                collection_method="oliveyoung_public_ranking",
                is_fallback=False,
            )
            self._set_success(items, "oliveyoung_public_ranking")
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
                    "collection_method": "oliveyoung_ranking_cache",
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
                "collection_method": "oliveyoung_ranking_no_data",
            }
        )
        self._set_diagnostic(reason, "fallback_used")
        return []

    def parse_public_ranking(self, raw_html: str) -> List[Dict[str, Any]]:
        """Parse deterministic fixtures or public ranking HTML.

        ``list_position`` records document order. ``rank`` is populated only
        when an explicit rank is present in the card; it is never fabricated.
        """
        document = str(raw_html or "")
        if not document.strip():
            return []

        category_scope = self._extract_category_scope(document)
        rows: List[Dict[str, Any]] = []
        seen = set()

        for block in self._candidate_blocks(document):
            link = self._extract_product_link(block)
            if not link or link in seen:
                continue

            brand = self._extract_attribute(
                block,
                ("data-ref-brandnm", "data-brand-name", "data-brandnm"),
            ) or self._extract_class_text(
                block,
                ("tx_brand", "prd_brand", "product-brand", "brand-name"),
            )
            product_title = self._extract_attribute(
                block,
                ("data-ref-goodsnm", "data-goods-name", "data-product-name"),
            ) or self._extract_class_text(
                block,
                ("tx_name", "prd_name", "product-name", "goods-name"),
            )
            if not product_title:
                product_title = self._extract_link_title(block, link)
            if not product_title:
                continue

            seen.add(link)
            explicit_rank = self._extract_explicit_rank(block)
            rows.append(
                {
                    "category_scope": category_scope,
                    "rank": explicit_rank,
                    "visible_rank": explicit_rank,
                    "list_position": len(rows) + 1,
                    "rank_basis": (
                        "visible_retailer_rank"
                        if explicit_rank is not None
                        else "retailer_page_order_only"
                    ),
                    "brand": self._nullable_text(brand),
                    "product_title": self._clean_text(product_title),
                    "link": link,
                    "visible_price_text": self._extract_visible_price(block),
                    "promotion_labels": self._extract_promotion_labels(block),
                    "signal_basis": self.SIGNAL_BASIS,
                    "ranking_scope": "retailer_specific",
                    "promotion_sensitive": True,
                    "universal_trend_claimed": False,
                }
            )
            if len(rows) >= self.max_items:
                break
        return rows

    def _candidate_blocks(self, document: str) -> List[str]:
        blocks: List[str] = []
        for tag in ("li", "article"):
            for match in re.finditer(
                rf"<{tag}\b[^>]*>[\s\S]*?</{tag}>",
                document,
                flags=re.IGNORECASE,
            ):
                block = match.group(0)
                if "getGoodsDetail.do" in block or "goodsNo=" in block:
                    blocks.append(block)
        if blocks:
            return blocks
        return [
            match.group(0)
            for match in re.finditer(
                r'<div\b[^>]*class=["\'][^"\']*(?:product|goods|prd|ranking|rank)[^"\']*["\'][^>]*>[\s\S]*?</div>',
                document,
                flags=re.IGNORECASE,
            )
            if "getGoodsDetail.do" in match.group(0) or "goodsNo=" in match.group(0)
        ]

    def _extract_product_link(self, block: str) -> str:
        for match in re.finditer(
            r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>',
            block,
            flags=re.IGNORECASE,
        ):
            link = self._normalize_link(match.group(1))
            if "goodsNo=" in link or "/goods/" in link:
                return link
        return ""

    def _extract_link_title(self, block: str, normalized_link: str) -> str:
        for match in re.finditer(
            r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',
            block,
            flags=re.IGNORECASE,
        ):
            if self._normalize_link(match.group(1)) != normalized_link:
                continue
            visible = self._clean_text(match.group(2))
            if visible:
                return visible
            image_alt = re.search(
                r'<img\b[^>]*alt=["\']([^"\']+)["\']',
                match.group(2),
                flags=re.IGNORECASE,
            )
            return self._clean_text(image_alt.group(1)) if image_alt else ""
        return ""

    def _extract_explicit_rank(self, block: str) -> Optional[int]:
        attribute = self._extract_attribute(
            block,
            ("data-rank", "data-ranking", "data-rank-no"),
        )
        rank = self._coerce_positive_int(attribute)
        if rank is not None:
            return rank
        visible = self._extract_class_text(
            block,
            ("rank", "ranking", "best_num", "best-number", "rank-num"),
        )
        match = re.search(r"\b(\d{1,3})\b", visible)
        return self._coerce_positive_int(match.group(1)) if match else None

    def _extract_visible_price(self, block: str) -> Optional[str]:
        visible = self._extract_class_text(
            block,
            ("tx_cur", "sale-price", "price-2", "prd_price", "product-price"),
        )
        if not visible:
            return None
        return visible if re.search(r"\d", visible) else None

    def _extract_promotion_labels(self, block: str) -> List[str]:
        labels: List[str] = []
        for match in re.finditer(
            r'<(?:span|em|strong)\b[^>]*class=["\'][^"\']*(?:flag|badge|tag|icon)[^"\']*["\'][^>]*>([\s\S]*?)</(?:span|em|strong)>',
            block,
            flags=re.IGNORECASE,
        ):
            label = self._clean_text(match.group(1))
            if label and label not in labels:
                labels.append(label)
        return labels[:10]

    def _extract_category_scope(self, document: str) -> Optional[str]:
        selected = re.search(
            r'<(?:button|a|option)\b[^>]*(?:aria-selected=["\']true["\']|class=["\'][^"\']*(?:active|on|selected)[^"\']*["\'])[^>]*>([\s\S]*?)</(?:button|a|option)>',
            document,
            flags=re.IGNORECASE,
        )
        return self._nullable_text(selected.group(1)) if selected else None

    def _extract_attribute(self, block: str, names: Tuple[str, ...]) -> str:
        for name in names:
            match = re.search(
                rf'\b{re.escape(name)}=["\']([^"\']+)["\']',
                block,
                flags=re.IGNORECASE,
            )
            if match:
                return self._clean_text(match.group(1))
        return ""

    def _extract_class_text(self, block: str, tokens: Tuple[str, ...]) -> str:
        token_pattern = "|".join(re.escape(token) for token in tokens)
        match = re.search(
            rf'<(?:span|p|div|strong|em)\b[^>]*class=["\'][^"\']*(?:{token_pattern})[^"\']*["\'][^>]*>([\s\S]*?)</(?:span|p|div|strong|em)>',
            block,
            flags=re.IGNORECASE,
        )
        return self._clean_text(match.group(1)) if match else ""

    def _build_items(
        self,
        rows: List[Dict[str, Any]],
        source: Dict[str, Any],
        collection_method: str,
        is_fallback: bool,
    ) -> List[Dict[str, Any]]:
        collected_at = datetime.now().astimezone().isoformat()
        source_id = str(source.get("source_id") or "oliveyoung_ranking")
        source_name = str(source.get("name") or source.get("source_name") or "Olive Young")
        items: List[Dict[str, Any]] = []
        seen = set()

        for row in rows[: self.max_items]:
            product_title = self._clean_text(row.get("product_title"))
            link = self._normalize_link(row.get("link"))
            if not product_title or not link or link in seen:
                continue
            seen.add(link)
            brand = self._nullable_text(row.get("brand"))
            display_title = f"{brand} {product_title}" if brand else product_title
            explicit_rank = self._coerce_positive_int(row.get("rank"))
            items.append(
                {
                    "keyword": display_title,
                    "title": display_title,
                    "brand": brand,
                    "product_title": product_title,
                    "link": link,
                    "url": link,
                    "category": self._nullable_text(row.get("category_scope")),
                    "category_scope": self._nullable_text(row.get("category_scope")),
                    "rank": explicit_rank,
                    "visible_rank": explicit_rank,
                    "list_position": self._coerce_positive_int(row.get("list_position")),
                    "rank_basis": self._nullable_text(row.get("rank_basis")),
                    "visible_price_text": self._nullable_text(row.get("visible_price_text")),
                    "promotion_labels": self._clean_string_list(row.get("promotion_labels")),
                    "signal_basis": self.SIGNAL_BASIS,
                    "ranking_scope": "retailer_specific",
                    "promotion_sensitive": True,
                    "universal_trend_claimed": False,
                    "views": None,
                    "likes": None,
                    "sales": None,
                    "rating": None,
                    "reviews": None,
                    "inventory": None,
                    "publisher": None,
                    "published_at": None,
                    "source_id": source_id,
                    "source_name": source_name,
                    "source_type": str(source.get("type") or "retailer_ranking"),
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
            if not isinstance(payload, dict) or not self._cache_is_fresh(payload.get("updated_at")):
                return []
            rows = payload.get("items")
            if not isinstance(rows, list):
                return []
        except Exception:
            return []
        return self._build_items(rows, source, "oliveyoung_ranking_cache", True)

    def _cache_is_fresh(self, value: Any) -> bool:
        try:
            updated_at = datetime.fromisoformat(str(value))
            now = datetime.now().astimezone() if updated_at.tzinfo else datetime.now()
            age_seconds = (now - updated_at).total_seconds()
            return 0 <= age_seconds <= self.cache_ttl_seconds
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
                service="oliveyoung_ranking",
                reason=reason,
                status=status,
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
            link = urllib.parse.urljoin("https://www.oliveyoung.co.kr/", link)
        if not link.startswith(("http://", "https://")):
            return ""
        host = (urllib.parse.urlparse(link).hostname or "").lower()
        if host not in {"oliveyoung.co.kr", "www.oliveyoung.co.kr", "m.oliveyoung.co.kr"}:
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

    def _clean_string_list(self, value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        result: List[str] = []
        for item in value:
            cleaned = self._clean_text(item)
            if cleaned and cleaned not in result:
                result.append(cleaned)
        return result[:10]

    def _coerce_positive_int(self, value: Any) -> Optional[int]:
        try:
            match = re.search(r"\d+", self._clean_text(value).replace(",", ""))
            if not match:
                return None
            parsed = int(match.group(0))
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
        priorities = (
            self.LIVE_REJECTION_REASON,
            "http_403",
            "connection_refused",
            "timeout",
            "network_error",
            "parse_failed",
            "no_results",
            "unknown_error",
        )
        for reason in priorities:
            if reason in failures:
                return reason
        return failures[0]
