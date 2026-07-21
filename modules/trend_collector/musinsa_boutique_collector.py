"""Fallback-first shallow collector for MUSINSA Boutique public lists."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from modules.trend_collector.musinsa_monthly_ranking_collector import (
    MusinsaMonthlyRankingCollector,
)


class MusinsaBoutiqueCollector(MusinsaMonthlyRankingCollector):
    """Parse visible Boutique list metadata as a luxury reference signal only."""

    DEFAULT_URL = "https://www.musinsa.com/main/boutique"
    DEFAULT_CACHE_PATH = Path("storage/cache/musinsa_boutique_cache.json")
    SOURCE_ROLE = "luxury_reference"
    SIGNAL_SCOPE = "platform_specific"
    VERTICAL = "fashion"
    PUBLIC_SHELL_REASON = "public_shell_without_product_metadata"

    def __init__(
        self,
        timeout: int = 8,
        max_items: int = 30,
        config: Optional[Dict[str, Any]] = None,
        fetcher: Optional[Callable[[str], Tuple[str, str]]] = None,
        parser: Optional[Callable[[str], List[Dict[str, Any]]]] = None,
    ) -> None:
        super().__init__(
            timeout=timeout,
            max_items=max_items,
            config=config,
            fetcher=fetcher,
            parser=parser or self.parse_public_boutique_list,
        )
        self.last_parse_reason = ""

    def _empty_status(self) -> Dict[str, Any]:
        status = super()._empty_status()
        status.update(
            {
                "source": "musinsa_boutique",
                "source_role": self.SOURCE_ROLE,
                "vertical": self.VERTICAL,
                "signal_scope": self.SIGNAL_SCOPE,
                "universal_trend_claimed": False,
                "exact_match_claimed": False,
                "dupe_equivalence_claimed": False,
                "authentic_use_equivalence_claimed": False,
            }
        )
        return status

    def collect(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.last_status = self._empty_status()
        self.last_status["attempted"] = True
        failures: List[str] = []
        rows: List[Dict[str, Any]] = []
        if bool(self.config.get("allow_live_fetch", False)):
            try:
                _, payload = self.fetcher(self._resolve_url(source))
                rows = self.parser(payload)
                if not rows:
                    failures.append(self.last_parse_reason or "parse_failed")
            except Exception as error:
                failures.append(self._classify_error(error))
        else:
            failures.append(self.LIVE_REJECTION_REASON)

        if rows:
            items = self._build_items(rows, source, "musinsa_boutique_public_list", False)
            self._set_success(items, "musinsa_boutique_public_list")
            return items

        cached = self._load_cache(source)
        if cached:
            reason = self._primary_reason(failures)
            self.last_status.update(
                {
                    "success": True,
                    "count": len(cached),
                    "fallback_reason": reason,
                    "final_error_type": reason,
                    "collection_method": "musinsa_boutique_cache",
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
                "collection_method": "musinsa_boutique_no_data",
            }
        )
        self._set_diagnostic(reason, "fallback_used")
        return []

    def parse_public_boutique_list(self, raw_payload: str) -> List[Dict[str, Any]]:
        document = str(raw_payload or "")
        self.last_parse_reason = ""
        if not document.strip():
            self.last_parse_reason = "empty_result"
            return []
        payload = self._load_json_payload(document)
        rows = self._parse_json_rows(payload) if payload is not None else []
        if not rows:
            rows = self._parse_html_rows(document)
        if not rows:
            self.last_parse_reason = (
                self.PUBLIC_SHELL_REASON
                if "__NEXT_DATA__" in document
                else "parse_failed"
            )
        return rows[: self.max_items]

    def _parse_json_rows(self, payload: Any) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for candidate in self._walk_dicts(payload):
            title = self._first_text(
                candidate,
                ("goodsName", "itemName", "productName", "goods_name", "name"),
            )
            link = self._normalize_link(
                self._first_text(candidate, ("goodsLinkUrl", "link", "url", "href"))
            )
            if not title or not link:
                continue
            explicit_rank = self._first_positive_int(
                candidate,
                ("rank", "ranking", "rankNo", "rank_no"),
            )
            rows.append(
                self._row(
                    title=title,
                    link=link,
                    brand=self._first_text(candidate, ("brandName", "brand", "brand_name")),
                    category=self._first_text(candidate, ("categoryName", "category", "category_name")),
                    explicit_rank=explicit_rank,
                    list_position=len(rows) + 1,
                    visible_price=self._first_text(candidate, ("priceText", "displayPrice")),
                )
            )
        return self._dedupe(rows)

    def _parse_html_rows(self, document: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for block in self._candidate_blocks(document):
            link_match = re.search(
                r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',
                block,
                flags=re.IGNORECASE,
            )
            if not link_match:
                continue
            link = self._normalize_link(link_match.group(1))
            title = self._extract_attribute(
                block,
                ("data-goods-name", "data-item-name", "data-product-name"),
            ) or self._extract_class_text(link_match.group(2), ("name", "title", "product"))
            if not title or not link:
                continue
            rank_text = self._extract_attribute(block, ("data-rank", "data-ranking"))
            rows.append(
                self._row(
                    title=title,
                    link=link,
                    brand=self._extract_attribute(block, ("data-brand-name", "data-brand"))
                    or self._extract_class_text(block, ("brand",)),
                    category=self._extract_attribute(block, ("data-category", "data-category-name")),
                    explicit_rank=self._coerce_positive_int(rank_text),
                    list_position=len(rows) + 1,
                    visible_price=self._extract_class_text(block, ("price",)),
                )
            )
        return self._dedupe(rows)

    def _row(
        self,
        title: str,
        link: str,
        brand: Any,
        category: Any,
        explicit_rank: Optional[int],
        list_position: int,
        visible_price: Any,
    ) -> Dict[str, Any]:
        return {
            "brand": self._nullable_text(brand),
            "item_title": self._clean_text(title),
            "link": link,
            "category_scope": self._nullable_text(category),
            "rank": explicit_rank,
            "visible_rank": explicit_rank,
            "list_position": list_position,
            "rank_basis": "visible_platform_rank" if explicit_rank else "platform_list_order_only",
            "visible_price_text": self._nullable_text(visible_price),
        }

    def _build_items(
        self,
        rows: List[Dict[str, Any]],
        source: Dict[str, Any],
        collection_method: str,
        is_fallback: bool,
    ) -> List[Dict[str, Any]]:
        collected_at = datetime.now().astimezone().isoformat()
        items: List[Dict[str, Any]] = []
        for row in rows[: self.max_items]:
            title = self._clean_text(row.get("item_title"))
            link = self._normalize_link(row.get("link"))
            if not title or not link:
                continue
            brand = self._nullable_text(row.get("brand"))
            explicit_rank = self._coerce_positive_int(row.get("rank"))
            items.append(
                {
                    "keyword": f"{brand} {title}" if brand else title,
                    "title": f"{brand} {title}" if brand else title,
                    "brand": brand,
                    "item_title": title,
                    "link": link,
                    "url": link,
                    "category_scope": self._nullable_text(row.get("category_scope")),
                    "rank": explicit_rank,
                    "visible_rank": explicit_rank,
                    "list_position": self._coerce_positive_int(row.get("list_position")),
                    "rank_basis": self._nullable_text(row.get("rank_basis")),
                    "visible_price_text": self._nullable_text(row.get("visible_price_text")),
                    "source_role": self.SOURCE_ROLE,
                    "vertical": self.VERTICAL,
                    "signal_scope": self.SIGNAL_SCOPE,
                    "universal_trend_claimed": False,
                    "exact_match_claimed": False,
                    "dupe_equivalence_claimed": False,
                    "authentic_use_equivalence_claimed": False,
                    "views": None,
                    "likes": None,
                    "sales": None,
                    "publisher": None,
                    "published_at": None,
                    "source_id": "musinsa_boutique",
                    "source_name": str(source.get("name") or "MUSINSA Boutique"),
                    "source_type": str(source.get("type") or "fashion_reference"),
                    "collection_method": collection_method,
                    "is_fallback": bool(is_fallback),
                    "collected_at": collected_at,
                }
            )
        return self._dedupe(items)

    def _load_cache(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.cache_path.exists():
            return []
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            rows = payload.get("items") if self._cache_is_fresh(payload.get("updated_at")) else []
            if not isinstance(rows, list):
                return []
        except Exception:
            return []
        return self._build_items(rows, source, "musinsa_boutique_cache", True)

    def _candidate_blocks(self, document: str) -> List[str]:
        blocks: List[str] = []
        for tag in ("li", "article"):
            blocks.extend(
                match.group(0)
                for match in re.finditer(
                    rf"<{tag}\b[^>]*>[\s\S]*?</{tag}>",
                    document,
                    flags=re.IGNORECASE,
                )
            )
        return blocks

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
        pattern = "|".join(re.escape(token) for token in tokens)
        match = re.search(
            rf'<(?:span|p|div|strong|em)\b[^>]*class=["\'][^"\']*(?:{pattern})[^"\']*["\'][^>]*>([\s\S]*?)</(?:span|p|div|strong|em)>',
            block,
            flags=re.IGNORECASE,
        )
        return self._clean_text(match.group(1)) if match else ""

    def _dedupe(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        seen = set()
        for row in rows:
            link = row.get("link") or row.get("url")
            if not link or link in seen:
                continue
            seen.add(link)
            result.append(row)
        return result[: self.max_items]

    def _set_diagnostic(self, reason: str, status: str) -> None:
        self.last_status["service_diagnostic"] = (
            self.service_diagnostic.build_diagnostic_from_reason(
                service="musinsa_boutique",
                reason=reason,
                status=status,
            )
        )
