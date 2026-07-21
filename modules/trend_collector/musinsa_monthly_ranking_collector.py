"""Shallow collector for MUSINSA public monthly-ranking metadata.

The collector does not open product details, read reviews, download images,
or treat a platform ranking as a universal market trend.  Missing ranking
scope and basis fields stay explicit instead of being inferred.
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
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError

from modules.common.service_diagnostic import ServiceDiagnostic


class MusinsaMonthlyRankingCollector:
    """Collect only visible public MUSINSA monthly-ranking list metadata."""

    DEFAULT_URL = "https://www.musinsa.com/main/musinsa/ranking"
    DEFAULT_CACHE_PATH = Path("storage/cache/musinsa_monthly_ranking_cache.json")
    LIVE_REJECTION_REASON = "live_activation_not_approved"
    PUBLIC_SHELL_REASON = "public_shell_without_product_metadata"

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
        self.parser = parser or self.parse_public_monthly_ranking
        self.cache_path = Path(self.config.get("cache_path", self.DEFAULT_CACHE_PATH))
        self.cache_ttl_seconds = max(
            0,
            int(self.config.get("cache_ttl_seconds", 24 * 60 * 60)),
        )
        self.service_diagnostic = ServiceDiagnostic()
        self.last_parse_reason = ""
        self.last_status = self._empty_status()

    def _empty_status(self) -> Dict[str, Any]:
        return {
            "source": "musinsa_monthly_ranking",
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
            "ranking_scope": "platform_specific_monthly_ranking",
            "universal_trend_claimed": False,
            "service_diagnostic": self.service_diagnostic.build_diagnostic_from_reason(
                service="musinsa_monthly_ranking",
                reason="",
                status="ok",
            ),
        }

    def collect(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return public ranking rows, bounded cache data, or an empty list."""
        self.last_status = self._empty_status()
        self.last_status["attempted"] = True
        failures: List[str] = []
        rows: List[Dict[str, Any]] = []

        if bool(self.config.get("allow_live_fetch", False)):
            try:
                _, raw_payload = self.fetcher(self._resolve_url(source))
                rows = self.parser(raw_payload)
                if not rows:
                    failures.append(self.last_parse_reason or "parse_failed")
            except Exception as error:
                failures.append(self._classify_error(error))
        else:
            failures.append(self.LIVE_REJECTION_REASON)

        if rows:
            items = self._build_items(
                rows,
                source,
                "musinsa_public_monthly_ranking",
                False,
            )
            self._set_success(items, "musinsa_public_monthly_ranking")
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
                    "collection_method": "musinsa_monthly_ranking_cache",
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
                "collection_method": "musinsa_monthly_ranking_no_data",
            }
        )
        self._set_diagnostic(reason, "fallback_used")
        return []

    def parse_public_monthly_ranking(self, raw_payload: str) -> List[Dict[str, Any]]:
        """Deterministic parser seam for fixture HTML or embedded public JSON."""
        document = str(raw_payload or "")
        self.last_parse_reason = ""
        if not document.strip():
            self.last_parse_reason = "empty_result"
            return []

        context = self._extract_visible_context(document)
        payload = self._load_json_payload(document)
        if payload is not None:
            rows = self._parse_json_ranking(payload, context)
            if rows:
                return rows[: self.max_items]
        rows = self._parse_html_ranking(document, context)[: self.max_items]
        if not rows:
            self.last_parse_reason = (
                self.PUBLIC_SHELL_REASON
                if "__NEXT_DATA__" in document
                else "parse_failed"
            )
        return rows

    def _parse_json_ranking(
        self,
        payload: Any,
        context: Dict[str, Optional[str]],
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        seen = set()
        for candidate in self._walk_dicts(payload):
            rank = self._first_positive_int(candidate, ("rank", "ranking", "rankNo", "rank_no"))
            item_title = self._first_text(
                candidate,
                ("goodsName", "goods_name", "itemName", "item_name", "productName", "name"),
            )
            brand = self._first_text(
                candidate,
                ("brandName", "brand_name", "brand", "brandNm"),
            )
            link = self._normalize_link(
                self._first_text(
                    candidate,
                    ("link", "url", "goodsLinkUrl", "goods_url", "href"),
                )
            )
            if not item_title or not link:
                continue
            key = (rank, link)
            if key in seen:
                continue
            seen.add(key)
            row_context = {
                "period": self._first_text(candidate, ("period", "rankingPeriod", "month")) or context["period"],
                "gender_scope": self._first_text(candidate, ("gender", "genderScope", "sex")) or context["gender_scope"],
                "category_scope": self._first_text(candidate, ("category", "categoryName", "categoryNm")) or context["category_scope"],
                "ranking_basis_label": self._first_text(candidate, ("basisLabel", "rankingBasis", "basis")) or context["ranking_basis_label"],
            }
            rows.append(self._ranking_row(rank, brand, item_title, link, row_context))
        return self._dedupe_by_rank_link(rows)

    def _parse_html_ranking(
        self,
        document: str,
        context: Dict[str, Optional[str]],
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
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
        blocks.extend(
            match.group(0)
            for match in re.finditer(
                r'<div\b[^>]*class=["\'][^"\']*(?:ranking|rank|goods|product|item|card)[^"\']*["\'][^>]*>[\s\S]*?</div>',
                document,
                flags=re.IGNORECASE,
            )
        )

        for block in blocks:
            rank = self._extract_visible_rank(block)
            brand = self._extract_class_text(block, ("brand", "brand-name", "brand_name"))
            item_title, link = self._extract_item_link(block)
            link = self._normalize_link(link)
            if rank is None or not item_title or not link:
                continue
            row_context = dict(context)
            row_context["gender_scope"] = (
                self._extract_data_attribute(block, ("gender", "gender-scope"))
                or row_context["gender_scope"]
            )
            row_context["category_scope"] = (
                self._extract_data_attribute(block, ("category", "category-name"))
                or row_context["category_scope"]
            )
            rows.append(self._ranking_row(rank, brand, item_title, link, row_context))
        return self._dedupe_by_rank_link(rows)

    def _ranking_row(
        self,
        rank: Optional[int],
        brand: Optional[str],
        item_title: str,
        link: str,
        context: Dict[str, Optional[str]],
    ) -> Dict[str, Any]:
        row = {
            "period": self._nullable_text(context.get("period")),
            "gender_scope": self._nullable_text(context.get("gender_scope")),
            "category_scope": self._nullable_text(context.get("category_scope")),
            "rank_position": rank,
            "rank": rank,
            "brand": self._nullable_text(brand),
            "item_title": self._clean_text(item_title),
            "link": link,
            "ranking_basis_label": self._nullable_text(context.get("ranking_basis_label")),
        }
        row["missing_fields"] = [
            field
            for field in (
                "period",
                "gender_scope",
                "category_scope",
                "rank_position",
                "brand",
                "ranking_basis_label",
            )
            if row[field] is None
        ]
        return row

    def _extract_visible_context(self, document: str) -> Dict[str, Optional[str]]:
        visible_text = self._clean_text(document)
        period_match = re.search(
            r"\b(20\d{2}[./-]\s?(?:0?[1-9]|1[0-2])(?:월|\b))",
            visible_text,
        )
        basis_match = re.search(
            r"([^.!?\n]{0,50}(?:월간|monthly)[^.!?\n]{0,50}(?:랭킹|ranking)[^.!?\n]{0,50})",
            visible_text,
            flags=re.IGNORECASE,
        )
        gender = self._extract_labeled_text(visible_text, ("성별", "gender"))
        category = self._extract_labeled_text(visible_text, ("카테고리", "category"))
        return {
            "period": self._clean_text(period_match.group(1)) if period_match else None,
            "gender_scope": gender or None,
            "category_scope": category or None,
            "ranking_basis_label": self._clean_text(basis_match.group(1)) if basis_match else None,
        }

    def _extract_labeled_text(self, text: str, labels: Tuple[str, ...]) -> str:
        label_pattern = "|".join(re.escape(label) for label in labels)
        match = re.search(
            rf"(?:{label_pattern})\s*[:：]\s*([^|,/·]{{1,30}})",
            text,
            flags=re.IGNORECASE,
        )
        return self._clean_text(match.group(1)) if match else ""

    def _extract_visible_rank(self, block: str) -> Optional[int]:
        attribute = self._extract_data_attribute(block, ("rank", "ranking", "rank-no"))
        rank = self._coerce_positive_int(attribute)
        if rank is not None:
            return rank
        rank_text = self._extract_class_text(block, ("rank", "ranking", "rank-num", "rank_num"))
        match = re.search(r"\b(\d{1,4})\b", rank_text)
        return self._coerce_positive_int(match.group(1)) if match else None

    def _extract_item_link(self, block: str) -> Tuple[str, str]:
        anchors = re.finditer(
            r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',
            block,
            flags=re.IGNORECASE,
        )
        for anchor in anchors:
            link = self._normalize_link(anchor.group(1))
            title = self._extract_class_text(
                anchor.group(2),
                ("name", "goods", "item", "product", "title"),
            ) or self._clean_text(anchor.group(2))
            if link and len(title) >= 2:
                return title, link
        return "", ""

    def _extract_class_text(self, block: str, tokens: Tuple[str, ...]) -> str:
        token_pattern = "|".join(re.escape(token) for token in tokens)
        match = re.search(
            rf'<(?:span|p|div|strong|em)\b[^>]*class=["\'][^"\']*(?:{token_pattern})[^"\']*["\'][^>]*>([\s\S]*?)</(?:span|p|div|strong|em)>',
            block,
            flags=re.IGNORECASE,
        )
        return self._clean_text(match.group(1)) if match else ""

    def _extract_data_attribute(self, block: str, names: Tuple[str, ...]) -> str:
        name_pattern = "|".join(re.escape(name) for name in names)
        match = re.search(
            rf'\bdata-(?:{name_pattern})=["\']([^"\']+)["\']',
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
        source_id = str(source.get("source_id") or "musinsa_monthly_ranking")
        source_name = str(source.get("name") or source.get("source_name") or "MUSINSA")
        items: List[Dict[str, Any]] = []
        for row in rows[: self.max_items]:
            rank = self._coerce_positive_int(row.get("rank_position"))
            item_title = self._clean_text(row.get("item_title"))
            link = self._normalize_link(row.get("link"))
            if not item_title or not link:
                continue
            brand = self._nullable_text(row.get("brand"))
            display_title = f"{brand} {item_title}" if brand else item_title
            normalized = {
                "keyword": display_title,
                "title": display_title,
                "brand": brand,
                "item_title": item_title,
                "link": link,
                "url": link,
                "period": self._nullable_text(row.get("period")),
                "gender_scope": self._nullable_text(row.get("gender_scope")),
                "category_scope": self._nullable_text(row.get("category_scope")),
                "rank_position": rank,
                "rank": rank,
                "ranking_basis_label": self._nullable_text(row.get("ranking_basis_label")),
                "platform_specific_basis_label": self._nullable_text(
                    row.get("ranking_basis_label")
                ),
                "ranking_scope": "platform_specific_monthly_ranking",
                "universal_trend_claimed": False,
                "views": None,
                "likes": None,
                "sales": None,
                "publisher": None,
                "published_at": None,
                "source_id": source_id,
                "source_name": source_name,
                "source_type": str(source.get("type") or "platform_ranking"),
                "collection_method": collection_method,
                "is_fallback": bool(is_fallback),
                "collected_at": collected_at,
            }
            normalized["missing_fields"] = [
                field
                for field in (
                    "period",
                    "gender_scope",
                    "category_scope",
                    "rank_position",
                    "brand",
                    "ranking_basis_label",
                )
                if normalized[field] is None
            ]
            items.append(normalized)
        return self._dedupe_by_rank_link(items)

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
        return self._build_items(rows, source, "musinsa_monthly_ranking_cache", True)

    def _cache_is_fresh(self, value: Any) -> bool:
        try:
            updated_at = datetime.fromisoformat(str(value))
            now = datetime.now().astimezone() if updated_at.tzinfo else datetime.now()
            age_seconds = (now - updated_at).total_seconds()
            return 0 <= age_seconds <= self.cache_ttl_seconds
        except Exception:
            return False

    def _load_json_payload(self, document: str) -> Optional[Any]:
        try:
            return json.loads(document)
        except Exception:
            pass
        match = re.search(
            r'<script\b[^>]*(?:id=["\']__NEXT_DATA__["\']|type=["\']application/json["\'])[^>]*>([\s\S]*?)</script>',
            document,
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        try:
            return json.loads(html.unescape(match.group(1)).strip())
        except Exception:
            return None

    def _walk_dicts(self, value: Any) -> Iterable[Dict[str, Any]]:
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from self._walk_dicts(child)
        elif isinstance(value, list):
            for child in value:
                yield from self._walk_dicts(child)

    def _dedupe_by_rank_link(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        result: List[Dict[str, Any]] = []
        for row in rows:
            key = (row.get("rank_position"), row.get("link") or row.get("url"))
            if not key[1] or key in seen:
                continue
            seen.add(key)
            result.append(row)
        return result[: self.max_items]

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
        # The shared diagnostic history is intentionally not written here.
        self.last_status["service_diagnostic"] = (
            self.service_diagnostic.build_diagnostic_from_reason(
                service="musinsa_monthly_ranking",
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
                "Accept": "text/html,application/xhtml+xml,application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return response.geturl(), response.read().decode("utf-8", errors="ignore")

    def _normalize_link(self, value: Any) -> str:
        link = html.unescape(str(value or "").strip())
        if link.startswith("//"):
            link = f"https:{link}"
        elif link.startswith("/"):
            link = urllib.parse.urljoin("https://www.musinsa.com/", link)
        if not link.startswith(("http://", "https://")):
            return ""
        host = (urllib.parse.urlparse(link).hostname or "").lower()
        if host not in {"musinsa.com", "www.musinsa.com"} and not host.endswith(".musinsa.com"):
            return ""
        return link

    def _first_text(self, data: Dict[str, Any], keys: Tuple[str, ...]) -> str:
        for key in keys:
            if key in data:
                cleaned = self._clean_text(data.get(key))
                if cleaned:
                    return cleaned
        return ""

    def _first_positive_int(self, data: Dict[str, Any], keys: Tuple[str, ...]) -> Optional[int]:
        for key in keys:
            if key in data:
                parsed = self._coerce_positive_int(data.get(key))
                if parsed is not None:
                    return parsed
        return None

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
