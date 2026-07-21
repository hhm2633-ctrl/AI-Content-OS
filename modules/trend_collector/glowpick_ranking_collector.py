"""Fallback-first shallow collector for Glowpick public ranking surfaces.

Only visible product-list metadata and aggregate consumer-review signals are
accepted.  Individual review text, AI summaries, medical/effect claims,
images, login/browser flows, and market-wide trend claims are out of scope.
Live fetching is disabled unless a later integration explicitly supplies
``allow_live_fetch``.
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


class GlowpickRankingCollector:
    """Collect platform-specific ranking and visible aggregate evidence."""

    DEFAULT_URL = "https://www.glowpick.com/products/brand-new"
    DEFAULT_CACHE_PATH = Path("storage/cache/glowpick_ranking_cache.json")
    LIVE_REJECTION_REASON = "live_activation_not_approved"
    SIGNAL_BASIS = "glowpick_public_ranking_and_product_list"
    AGGREGATE_PROVENANCE = "visible_glowpick_platform_aggregate"

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
            "source": "glowpick_ranking",
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
            "platform_specific": True,
            "promotion_sensitive": True,
            "experience_review_sensitive": True,
            "universal_trend_claimed": False,
            "market_truth_claimed": False,
            "service_diagnostic": self.service_diagnostic.build_diagnostic_from_reason(
                service="glowpick_ranking",
                reason="",
                status="ok",
            ),
        }

    def collect(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return injected/live rows, a fresh read-only cache, or honest empty."""
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
                collection_method="glowpick_public_ranking",
                is_fallback=False,
            )
            if items:
                self._set_success(items, "glowpick_public_ranking")
                return items
            failures.append("parse_failed")

        cache_items = self._load_cache(source)
        if cache_items:
            reason = self._primary_reason(failures)
            self.last_status.update(
                {
                    "success": True,
                    "count": len(cache_items),
                    "fallback_reason": reason,
                    "final_error_type": reason,
                    "collection_method": "glowpick_ranking_cache",
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
                "collection_method": "glowpick_ranking_no_data",
            }
        )
        self._set_diagnostic(reason, "fallback_used")
        return []

    def parse_public_ranking(self, raw_html: str) -> List[Dict[str, Any]]:
        """Parse product cards without copying review or summary prose."""
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
                ("data-brand", "data-brand-name", "data-brandnm"),
            ) or self._extract_class_text(
                block,
                ("brand-name", "product-brand", "product__brand", "brand"),
            )
            product_title = self._extract_attribute(
                block,
                ("data-product-name", "data-product", "data-goods-name"),
            ) or self._extract_class_text(
                block,
                ("product-name", "product__name", "goods-name", "product-title"),
            )
            if not product_title:
                product_title = self._extract_link_title(block, link)
            if not product_title:
                continue

            seen.add(link)
            explicit_rank = self._extract_explicit_rank(block)
            rating = self._extract_rating(block)
            review_count = self._extract_review_count(block)
            rows.append(
                {
                    "category_scope": category_scope,
                    "rank": explicit_rank,
                    "visible_rank": explicit_rank,
                    "list_position": len(rows) + 1,
                    "rank_basis": (
                        "visible_glowpick_rank"
                        if explicit_rank is not None
                        else "glowpick_page_order_only"
                    ),
                    "brand": self._nullable_text(brand),
                    "product_title": self._clean_text(product_title),
                    "link": link,
                    "rating": rating,
                    "review_count": review_count,
                    "visible_price_text": self._extract_visible_text(
                        block,
                        ("product-price", "price-text", "price"),
                    ),
                    "visible_volume_text": self._extract_visible_text(
                        block,
                        ("product-volume", "volume-text", "capacity", "volume"),
                    ),
                    "award_labels": self._extract_labels(
                        block,
                        ("award", "winner", "ranking-badge"),
                    ),
                    "aggregate_labels": self._extract_labels(
                        block,
                        ("aggregate-label", "rating-label", "review-label"),
                    ),
                    "consumer_review_signal": rating is not None or review_count is not None,
                    "signal_basis": self.SIGNAL_BASIS,
                    "platform_specific": True,
                    "promotion_sensitive": True,
                    "experience_review_sensitive": True,
                    "universal_trend_claimed": False,
                    "market_truth_claimed": False,
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
                if re.search(r'href=["\'][^"\']*/products?/', block, re.I):
                    blocks.append(block)
        if blocks:
            return blocks
        return [
            match.group(0)
            for match in re.finditer(
                r'<div\b[^>]*class=["\'][^"\']*(?:product|ranking|rank-item)[^"\']*["\'][^>]*>[\s\S]*?</div>',
                document,
                flags=re.IGNORECASE,
            )
            if re.search(r'href=["\'][^"\']*/products?/', match.group(0), re.I)
        ]

    def _extract_product_link(self, block: str) -> str:
        for match in re.finditer(
            r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>',
            block,
            flags=re.IGNORECASE,
        ):
            link = self._normalize_link(match.group(1))
            if re.search(r"/products?/", link, re.I):
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
            ("rank-number", "ranking-number", "rank-num", "rank"),
        )
        return self._coerce_positive_int(visible)

    def _extract_rating(self, block: str) -> Optional[float]:
        raw = self._extract_attribute(block, ("data-rating", "data-score")) or self._extract_class_text(
            block,
            ("rating-score", "average-rating", "product-rating"),
        )
        try:
            match = re.search(r"\d+(?:\.\d+)?", self._clean_text(raw))
            value = float(match.group(0)) if match else None
            return value if value is not None and 0.0 <= value <= 5.0 else None
        except Exception:
            return None

    def _extract_review_count(self, block: str) -> Optional[int]:
        raw = self._extract_attribute(
            block,
            ("data-review-count", "data-reviewcount"),
        ) or self._extract_class_text(
            block,
            ("review-count", "reviews-count", "reviewCount"),
        )
        return self._coerce_nonnegative_int(raw)

    def _extract_visible_text(self, block: str, tokens: Tuple[str, ...]) -> Optional[str]:
        value = self._extract_class_text(block, tokens)
        return value if value and re.search(r"\d", value) else None

    def _extract_labels(self, block: str, tokens: Tuple[str, ...]) -> List[str]:
        token_pattern = "|".join(re.escape(token) for token in tokens)
        labels: List[str] = []
        for match in re.finditer(
            rf'<(?:span|em|strong)\b[^>]*class=["\'][^"\']*(?:{token_pattern})[^"\']*["\'][^>]*>([\s\S]*?)</(?:span|em|strong)>',
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
        source_id = str(source.get("source_id") or "glowpick_ranking")
        source_name = str(source.get("name") or source.get("source_name") or "Glowpick")
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
            rating = self._coerce_rating(row.get("rating"))
            review_count = self._coerce_nonnegative_int(row.get("review_count"))
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
                    "rank": self._coerce_positive_int(row.get("rank")),
                    "visible_rank": self._coerce_positive_int(row.get("rank")),
                    "list_position": self._coerce_positive_int(row.get("list_position")),
                    "rank_basis": self._nullable_text(row.get("rank_basis")),
                    "rating": rating,
                    "review_count": review_count,
                    "rating_provenance": self._aggregate_provenance("rating") if rating is not None else None,
                    "review_count_provenance": (
                        self._aggregate_provenance("review_count")
                        if review_count is not None
                        else None
                    ),
                    "visible_price_text": self._nullable_text(row.get("visible_price_text")),
                    "visible_volume_text": self._nullable_text(row.get("visible_volume_text")),
                    "award_labels": self._clean_string_list(row.get("award_labels")),
                    "aggregate_labels": self._clean_string_list(row.get("aggregate_labels")),
                    "consumer_review_signal": rating is not None or review_count is not None,
                    "signal_basis": self.SIGNAL_BASIS,
                    "platform_specific": True,
                    "promotion_sensitive": True,
                    "experience_review_sensitive": True,
                    "universal_trend_claimed": False,
                    "market_truth_claimed": False,
                    "individual_review_text_collected": False,
                    "ai_summary_text_collected": False,
                    "views": None,
                    "likes": None,
                    "sales": None,
                    "reviews": None,
                    "inventory": None,
                    "publisher": None,
                    "published_at": None,
                    "source_id": source_id,
                    "source_name": source_name,
                    "source_type": str(source.get("type") or "consumer_review_ranking"),
                    "collection_method": collection_method,
                    "is_fallback": bool(is_fallback),
                    "collected_at": collected_at,
                }
            )
        return items

    def _aggregate_provenance(self, field: str) -> Dict[str, Any]:
        return {
            "field": field,
            "source": self.AGGREGATE_PROVENANCE,
            "platform": "glowpick",
            "scope": "public_product_listing",
            "platform_specific": True,
            "market_truth_claimed": False,
        }

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
        return self._build_items(rows, source, "glowpick_ranking_cache", True)

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
                service="glowpick_ranking",
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
            link = urllib.parse.urljoin("https://www.glowpick.com/", link)
        if not link.startswith(("http://", "https://")):
            return ""
        host = (urllib.parse.urlparse(link).hostname or "").lower()
        if host not in {"glowpick.com", "www.glowpick.com", "m.glowpick.com"}:
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
        parsed = self._coerce_nonnegative_int(value)
        return parsed if parsed is not None and parsed > 0 else None

    def _coerce_nonnegative_int(self, value: Any) -> Optional[int]:
        try:
            match = re.search(r"\d+", self._clean_text(value).replace(",", ""))
            return int(match.group(0)) if match else None
        except Exception:
            return None

    def _coerce_rating(self, value: Any) -> Optional[float]:
        try:
            if isinstance(value, bool):
                return None
            parsed = float(value)
            return parsed if 0.0 <= parsed <= 5.0 else None
        except (TypeError, ValueError):
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


__all__ = ["GlowpickRankingCollector"]
