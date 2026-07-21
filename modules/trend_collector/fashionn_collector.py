"""Shallow, fallback-first collector for FashionN public editorial lists.

Only metadata visible on a public list page is parsed.  Article detail pages,
images, engagement inference, and browser/login flows are intentionally out of
scope.  Live fetching is policy-disabled unless ``allow_live_fetch`` is set on
the collector config or on the source entry itself.
"""

from __future__ import annotations

import codecs
import gzip
import html
import json
import re
import socket
import zlib
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError

from modules.common.service_diagnostic import ServiceDiagnostic


class FashionNCollector:
    """Collect FashionN editorial-list metadata without deep-page requests."""

    DEFAULT_URL = "https://www.fashionn.com/"
    DEFAULT_CACHE_PATH = Path("storage/cache/fashionn_editorial_cache.json")
    LIVE_REJECTION_REASON = "live_activation_not_approved"

    # Editorial article rows carry a per-item numeric identifier; navigation,
    # category, and menu rows point at section/list/utility pages instead.
    ARTICLE_ID_QUERY_KEYS = frozenset(
        {
            "number",
            "no",
            "num",
            "idx",
            "id",
            "uid",
            "seq",
            "wr_id",
            "aid",
            "art_id",
            "article_id",
            "news_id",
        }
    )
    NAVIGATION_PATH_TOKENS = frozenset(
        {
            "list",
            "login",
            "logout",
            "join",
            "member",
            "mypage",
            "search",
            "category",
            "menu",
            "nav",
            "gnb",
            "lnb",
            "footer",
            "header",
            "policy",
            "terms",
            "privacy",
            "agreement",
            "company",
            "about",
            "contact",
            "sitemap",
            "rss",
            "event",
            "banner",
            "notice",
            "faq",
            "guide",
            "write",
            "modify",
            "delete",
        }
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
        self.cache_path = Path(self.config.get("cache_path", self.DEFAULT_CACHE_PATH))
        self.cache_ttl_seconds = max(
            0,
            int(self.config.get("cache_ttl_seconds", 24 * 60 * 60)),
        )
        self.service_diagnostic = ServiceDiagnostic()
        self._last_charset_info: Dict[str, str] = {}
        self._last_parse_stats: Dict[str, int] = {}
        self.last_status = self._empty_status()

    def _empty_status(self) -> Dict[str, Any]:
        return {
            "source": "fashionn",
            "attempted": False,
            "success": False,
            "count": 0,
            "failed_reason": "",
            "fallback_reason": "",
            "final_error_type": "",
            "error_message": "",
            "collection_method": "",
            "used_cache": False,
            "response_charset": "",
            "charset_source": "",
            "parse_stats": {},
            "cache_path": str(self.cache_path).replace("\\", "/"),
            "service_diagnostic": self.service_diagnostic.build_diagnostic_from_reason(
                service="fashionn",
                reason="",
                status="ok",
            ),
        }

    def collect(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return live list rows, a bounded cache fallback, or an honest empty list."""
        self.last_status = self._empty_status()
        self.last_status["attempted"] = True
        failures: List[str] = []
        rows: List[Dict[str, Any]] = []

        if self._live_fetch_allowed(source):
            self._last_charset_info = {}
            self._last_parse_stats = {}
            try:
                _, raw_html = self.fetcher(self._resolve_url(source))
                rows = self.parser(raw_html)
                if not rows:
                    failures.append("parse_failed")
            except Exception as error:
                failures.append(self._classify_error(error))
            self.last_status["response_charset"] = self._last_charset_info.get("charset", "")
            self.last_status["charset_source"] = self._last_charset_info.get("source", "")
            self.last_status["parse_stats"] = dict(self._last_parse_stats)
        else:
            failures.append(self.LIVE_REJECTION_REASON)

        if rows:
            items = self._build_items(rows, source, "fashionn_public_editorial_list", False)
            self._set_status(items, "fashionn_public_editorial_list")
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
                    "collection_method": "fashionn_editorial_cache",
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
                "collection_method": "fashionn_no_data",
            }
        )
        self._set_diagnostic(reason, "fallback_used")
        return []

    def parse_public_list(self, raw_html: str) -> List[Dict[str, Any]]:
        """Deterministic parser seam for public list HTML.

        List order is exposed as ``rank_position`` with the explicit basis
        ``visible_list_order``.  It is not represented as popularity.
        """
        document = str(raw_html or "")
        if not document.strip():
            return []

        candidates = self._candidate_blocks(document)
        rows: List[Dict[str, Any]] = []
        seen = set()
        rejected_non_article = 0
        for block in candidates:
            title, link = self._extract_title_link(block)
            normalized_link = self._normalize_link(link)
            title = self._clean_text(title)
            if not title or not normalized_link:
                if self._block_has_internal_link(block):
                    rejected_non_article += 1
                continue
            key = normalized_link or title.casefold()
            if key in seen:
                continue
            seen.add(key)

            row = {
                "title": title,
                "link": normalized_link,
                "section_category": self._extract_visible_field(
                    block,
                    ("category", "section", "cate", "board"),
                ) or None,
                "summary": self._extract_visible_field(
                    block,
                    ("summary", "description", "desc", "excerpt", "text"),
                ) or None,
                "visible_date": self._extract_visible_date(block),
                "rank_position": len(rows) + 1,
                "rank": len(rows) + 1,
                "rank_basis": "visible_list_order",
                "attribution": "FashionN public editorial list",
                "publisher": None,
                "views": self._extract_visible_metric(block, ("view", "views", "hit", "read")),
                "comments": self._extract_visible_metric(block, ("comment", "comments", "reply")),
                "likes": self._extract_visible_metric(block, ("like", "likes", "recommend")),
            }
            rows.append(row)
            if len(rows) >= self.max_items:
                break
        self._last_parse_stats = {
            "candidate_blocks": len(candidates),
            "accepted_article_rows": len(rows),
            "rejected_non_article_blocks": rejected_non_article,
        }
        return rows

    def _candidate_blocks(self, document: str) -> List[str]:
        blocks: List[str] = []
        for tag in ("article", "li"):
            blocks.extend(
                match.group(0)
                for match in re.finditer(
                    rf"<{tag}\b[^>]*>[\s\S]*?</{tag}>",
                    document,
                    flags=re.IGNORECASE,
                )
            )
        # Parser-fixture seam for list cards represented as divs.
        blocks.extend(
            match.group(0)
            for match in re.finditer(
                r'<div\b[^>]*class=["\'][^"\']*(?:article|news|list|item|card)[^"\']*["\'][^>]*>[\s\S]*?</div>',
                document,
                flags=re.IGNORECASE,
            )
        )
        return blocks

    def _extract_title_link(self, block: str) -> Tuple[str, str]:
        anchors = re.finditer(
            r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',
            block,
            flags=re.IGNORECASE,
        )
        for anchor in anchors:
            link = self._normalize_link(anchor.group(1))
            title = self._clean_text(anchor.group(2))
            if link and len(title) >= 4 and self._is_article_link(link):
                return title, link
        return "", ""

    def _is_article_link(self, link: str) -> bool:
        """Accept only per-article URLs, not navigation/category/menu pages.

        An editorial article row must carry a numeric content identifier:
        either an id-style query parameter (``number=501`` on FashionN read
        pages) or an all-digit path segment / ``<digits>.html`` filename.
        Any URL whose path contains a navigation token (list, login, search,
        category, ...) is rejected regardless of identifiers.
        """
        if not link:
            return False
        parsed = urllib.parse.urlparse(link)
        path = parsed.path or "/"
        if path in ("", "/") and not parsed.query:
            return False
        path_tokens = {
            token for token in re.split(r"[^0-9a-z]+", path.lower()) if token
        }
        if path_tokens & self.NAVIGATION_PATH_TOKENS:
            return False
        for key, value in urllib.parse.parse_qsl(parsed.query):
            if key.lower() in self.ARTICLE_ID_QUERY_KEYS and re.fullmatch(
                r"\d+", value.strip()
            ):
                return True
        for segment in path.split("/"):
            if re.fullmatch(r"\d{3,}", segment) or re.fullmatch(
                r"\d{3,}\.html?", segment.lower()
            ):
                return True
        return False

    def _block_has_internal_link(self, block: str) -> bool:
        for anchor in re.finditer(
            r'<a\b[^>]*href=["\']([^"\']+)["\']',
            block,
            flags=re.IGNORECASE,
        ):
            if self._normalize_link(anchor.group(1)):
                return True
        return False

    def _extract_visible_field(self, block: str, class_tokens: Tuple[str, ...]) -> str:
        token_pattern = "|".join(re.escape(token) for token in class_tokens)
        match = re.search(
            rf'<(?:span|p|div|em)\b[^>]*class=["\'][^"\']*(?:{token_pattern})[^"\']*["\'][^>]*>([\s\S]*?)</(?:span|p|div|em)>',
            block,
            flags=re.IGNORECASE,
        )
        return self._clean_text(match.group(1)) if match else ""

    def _extract_visible_date(self, block: str) -> Optional[str]:
        datetime_match = re.search(
            r'<time\b[^>]*datetime=["\']([^"\']+)["\'][^>]*>',
            block,
            flags=re.IGNORECASE,
        )
        if datetime_match:
            return self._clean_text(datetime_match.group(1)) or None
        visible = self._extract_visible_field(block, ("date", "time", "published"))
        if visible:
            return visible
        text = self._clean_text(block)
        match = re.search(r"\b(?:20\d{2}[./-])?\d{1,2}[./-]\d{1,2}\b", text)
        return match.group(0) if match else None

    def _extract_visible_metric(
        self,
        block: str,
        class_tokens: Tuple[str, ...],
    ) -> Optional[int]:
        visible = self._extract_visible_field(block, class_tokens)
        if not visible:
            return None
        numeric = re.search(r"\d[\d,]*", visible)
        return self._coerce_nonnegative_int(numeric.group(0)) if numeric else None

    def _build_items(
        self,
        rows: List[Dict[str, Any]],
        source: Dict[str, Any],
        collection_method: str,
        is_fallback: bool,
    ) -> List[Dict[str, Any]]:
        collected_at = datetime.now().astimezone().isoformat()
        source_id = str(source.get("source_id") or "fashionn")
        source_name = str(source.get("name") or source.get("source_name") or "FashionN")
        items: List[Dict[str, Any]] = []
        for row in rows[: self.max_items]:
            title = self._clean_text(row.get("title"))
            link = self._normalize_link(row.get("link"))
            if not title or not link or not self._is_article_link(link):
                continue
            rank = self._coerce_positive_int(row.get("rank_position"))
            if rank is None:
                continue
            items.append(
                {
                    "keyword": title,
                    "title": title,
                    "link": link,
                    "url": link,
                    "summary": self._nullable_text(row.get("summary")),
                    "published_at": self._nullable_text(
                        row.get("visible_date") or row.get("published_at")
                    ),
                    "visible_date": self._nullable_text(
                        row.get("visible_date") or row.get("published_at")
                    ),
                    "category": self._nullable_text(
                        row.get("section_category") or row.get("category")
                    ),
                    "section_category": self._nullable_text(
                        row.get("section_category") or row.get("category")
                    ),
                    "rank_position": rank,
                    "rank": rank,
                    "rank_basis": "visible_list_order",
                    "publisher": self._nullable_text(row.get("publisher"))
                    or self._publisher_from_link(link),
                    "attribution": "FashionN public editorial list",
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

    def _live_fetch_allowed(self, source: Dict[str, Any]) -> bool:
        if bool(self.config.get("allow_live_fetch", False)):
            return True
        return bool((source or {}).get("allow_live_fetch", False))

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
        return self._build_items(rows, source, "fashionn_editorial_cache", True)

    def _cache_is_fresh(self, value: Any) -> bool:
        try:
            updated_at = datetime.fromisoformat(str(value))
            if updated_at.tzinfo is not None:
                age = datetime.now().astimezone() - updated_at
            else:
                age = datetime.now() - updated_at
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
        # Build only: this isolated collector does not write the shared
        # service-diagnostic history.
        self.last_status["service_diagnostic"] = (
            self.service_diagnostic.build_diagnostic_from_reason(
                service="fashionn",
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
                "Accept-Encoding": "identity",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            raw = response.read()
            content_encoding = str(response.headers.get("Content-Encoding") or "")
            declared = ""
            try:
                declared = response.headers.get_content_charset() or ""
            except Exception:
                declared = ""
            raw = self._decompress_body(raw, content_encoding)
            return response.geturl(), self._decode_response(raw, declared)

    def _decompress_body(self, raw: bytes, content_encoding: str) -> bytes:
        """Undo transport compression detected from header or magic bytes.

        Some servers compress even when the request asks for identity; the
        gzip magic prefix ``1f 8b`` is checked so compressed bytes never
        reach charset resolution as if they were text.
        """
        encoding = content_encoding.strip().lower()
        if "gzip" in encoding or raw[:2] == b"\x1f\x8b":
            try:
                return gzip.decompress(raw)
            except Exception:
                return raw
        if "deflate" in encoding:
            for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
                try:
                    return zlib.decompress(raw, wbits)
                except Exception:
                    continue
        return raw

    def _decode_response(self, raw: bytes, declared_charset: str) -> str:
        """Decode response bytes preferring byte evidence over declarations.

        A strict UTF-8 decode of the full payload is checked before the
        declared header/meta charsets: UTF-8 is self-validating, while
        CP949/EUC-KR strictly decodes almost any high-byte pair, so a wrong
        ``charset=euc-kr`` declaration would silently turn genuine UTF-8
        Korean titles into mojibake.  Candidate order: byte-order mark,
        strict UTF-8 probe, Content-Type header charset, ``<meta ... charset>``
        in the leading bytes, strict CP949 probe.  If no candidate strictly
        decodes, the candidate producing the fewest replacement characters
        wins and the lossy outcome is recorded in the charset source.
        """
        candidates: List[Tuple[str, str]] = []
        if raw.startswith(codecs.BOM_UTF8):
            candidates.append(("utf-8-sig", "byte_order_mark"))
        elif raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
            candidates.append(("utf-16", "byte_order_mark"))
        candidates.append(("utf-8", "strict_utf8_bytes"))
        header_charset = self._validate_charset(declared_charset)
        if header_charset:
            candidates.append((header_charset, "content_type_header"))
        meta_match = re.search(
            r'<meta\b[^>]*charset\s*=\s*["\']?\s*([\w.-]+)',
            raw[:4096].decode("ascii", errors="ignore"),
            flags=re.IGNORECASE,
        )
        if meta_match:
            meta_charset = self._validate_charset(meta_match.group(1))
            if meta_charset:
                candidates.append((meta_charset, "meta_charset"))
        candidates.append(("cp949", "byte_probe"))

        for charset, source in candidates:
            try:
                text = raw.decode(charset)
            except (UnicodeDecodeError, LookupError):
                continue
            self._last_charset_info = {"charset": charset, "source": source}
            return text

        best_text = ""
        best_charset = ""
        best_replacements = -1
        tried = set()
        for charset, _ in candidates:
            if charset in tried:
                continue
            tried.add(charset)
            try:
                text = raw.decode(charset, errors="replace")
            except LookupError:
                continue
            replacements = text.count("�")
            if best_replacements < 0 or replacements < best_replacements:
                best_text = text
                best_charset = charset
                best_replacements = replacements
        self._last_charset_info = {
            "charset": best_charset or "utf-8",
            "source": "lossy_minimal_replacement",
        }
        return best_text if best_charset else raw.decode("utf-8", errors="replace")

    def _validate_charset(self, name: str) -> str:
        cleaned = str(name or "").strip().strip('"').strip("'")
        if not cleaned:
            return ""
        try:
            normalized = codecs.lookup(cleaned).name
        except LookupError:
            return ""
        # cp949 is the practical superset of euc-kr on Korean sites.
        return "cp949" if normalized == "euc_kr" else normalized

    def _normalize_link(self, value: Any) -> str:
        link = html.unescape(str(value or "").strip())
        if link.startswith("//"):
            link = f"https:{link}"
        elif link.startswith("/"):
            link = urllib.parse.urljoin(self.DEFAULT_URL, link)
        if not link.startswith(("http://", "https://")):
            return ""
        host = (urllib.parse.urlparse(link).hostname or "").lower()
        if host not in {"fashionn.com", "www.fashionn.com"}:
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

    def _coerce_positive_int(self, value: Any) -> Optional[int]:
        try:
            parsed = int(value)
            return parsed if parsed > 0 else None
        except Exception:
            return None

    def _coerce_nonnegative_int(self, value: Any) -> Optional[int]:
        try:
            numeric = re.search(r"\d+", str(value).replace(",", ""))
            return int(numeric.group(0)) if numeric else None
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
