import html
import re
import socket
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError

from modules.common.service_diagnostic import ServiceDiagnostic


class DaumNewsCollector:
    def __init__(self, timeout: int = 8, max_items_per_category: int = 20):
        self.timeout = timeout
        self.max_items_per_category = max_items_per_category
        self.service_diagnostic = ServiceDiagnostic()
        self.last_status = self._empty_status()
        self.verified_category_slugs = ["society", "politics"]

    def _empty_status(self) -> Dict[str, Any]:
        return {
            "source": "daum_news",
            "attempted": False,
            "success": False,
            "count": 0,
            "error_message": "",
            "failed_reason": "",
            "fallback_reason": "",
            "final_error_type": "",
            "collection_method": "",
            "used_cache": False,
            "cache_path": "",
            "service_diagnostic": {
                "service": "daum_news",
                "status": "ok",
                "error_type": "",
                "safe_message": "",
                "api_key_present": None,
            },
        }

    def collect(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        errors = []
        self.last_status = self._empty_status()
        self.last_status["attempted"] = True

        try:
            categories = self._extract_category_urls(source)
        except Exception as error:
            reason = self._classify_error(error)
            errors.append({"source": source.get("source_id", "daum_news"), "reason": reason})
            categories = []

        if not categories:
            self.last_status["failed_reason"] = "no_valid_category_urls"
            self.last_status["final_error_type"] = "no_valid_category_urls"
            self.last_status["error_message"] = "No valid Daum category URLs could be resolved."
            self._record_diagnostic()
            return []

        for category_url, category in categories:
            try:
                page_url, html_payload = self._fetch_url(category_url)
                validated_category = self._derive_category_from_url(page_url)

                if validated_category != category:
                    errors.append(
                        {
                            "category": category,
                            "reason": "redirected_category_url",
                        }
                    )
                    continue

                articles = self._parse_category_page(html_payload, validated_category)
                if not articles:
                    errors.append(
                        {
                            "category": category,
                            "reason": "empty_or_stale_category_page",
                        }
                    )
                    continue

                results.extend(articles)
            except Exception as error:
                reason = self._classify_error(error)
                errors.append({"category": category, "reason": reason})

        deduped = self._dedupe(results)
        self.last_status["success"] = bool(deduped)
        self.last_status["count"] = len(deduped)

        if deduped:
            self.last_status["collection_method"] = "daum_news_category_html"
        elif errors:
            self.last_status["failed_reason"] = self._primary_failed_reason(errors)
            self.last_status["final_error_type"] = self.last_status["failed_reason"]
            self.last_status["error_message"] = "; ".join(
                f"{error.get('category', error.get('source', 'unknown'))}: {error['reason']}"
                for error in errors[:5]
            )
        else:
            self.last_status["failed_reason"] = "empty_result"
            self.last_status["final_error_type"] = "empty_result"
            self.last_status["error_message"] = "Daum News returned no items."

        self._record_diagnostic()
        return [
            {**item, "source_id": "daum_news", "source_name": source.get("name", "Daum News"), "source_type": source.get("type", "news")}
            for item in deduped
        ]

    def _extract_category_urls(self, source: Dict[str, Any]) -> List[Tuple[str, str]]:
        base = str(source.get("url", "")).strip()
        parsed = urllib.parse.urlparse(base)
        path = (parsed.path or "/").strip("/").lower()

        if path and path not in {"", "news.daum.net"}:
            if self._is_invalid_daum_category_path(path):
                return []

            if "/" in path:
                parts = [p for p in path.split("/") if p]
                slug = parts[0]
            else:
                slug = path

            if slug in self.verified_category_slugs:
                return [(self._canonical_category_url(slug), slug)]
            return []

        return [
            (self._canonical_category_url(slug), slug)
            for slug in self.verified_category_slugs
        ]

    def _canonical_category_url(self, slug: str) -> str:
        return f"https://news.daum.net/{slug}"

    def _is_invalid_daum_category_path(self, path: str) -> bool:
        normalized = path.strip("/").lower()
        if not normalized:
            return False
        if normalized.startswith("ranking/") or normalized == "ranking":
            return True
        if normalized.startswith("breakingnews/"):
            return True
        if "/" in normalized and normalized.split("/", 1)[0] not in self.verified_category_slugs:
            return True
        return False

    def _derive_category_from_url(self, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        if parsed.netloc != "news.daum.net":
            return ""
        path = parsed.path.strip("/").lower()
        if self._is_invalid_daum_category_path(path):
            return ""
        if "/" in path:
            first_segment = path.split("/", 1)[0]
        else:
            first_segment = path
        if first_segment in self.verified_category_slugs:
            return first_segment
        return ""

    def _fetch_url(self, url: str) -> Tuple[str, str]:
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
            resolved_url = response.geturl()
            html_payload = response.read().decode("utf-8", errors="ignore")
        return resolved_url, html_payload

    def _parse_category_page(
        self,
        raw_html: str,
        category: str,
    ) -> List[Dict[str, Any]]:
        container_match = re.search(
            r'<ul[^>]+class="[^"]*list_newsheadline2[^"]*"[^>]*>(.*?)</ul>',
            raw_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not container_match:
            return []

        container_html = container_match.group(1)
        list_items = re.finditer(
            r"<li\b[^>]*>(.*?)</li>",
            container_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        items = []

        for item_html in list_items:
            raw_item_html = item_html.group(1)
            anchor_match = re.search(
                r'(<a[^>]*class="[^"]*item_newsheadline2[^"]*"[^>]*>(.*?)</a>)',
                raw_item_html,
                flags=re.IGNORECASE | re.DOTALL,
            )

            if not anchor_match:
                continue
            anchor_html = anchor_match.group(1)
            anchor_inner_html = anchor_match.group(2)
            href_match = re.search(r'href="([^"]+)"', anchor_html, flags=re.IGNORECASE)
            rank_match = re.search(
                r'data-tiara-ordnum="(\d+)"',
                anchor_html,
                flags=re.IGNORECASE,
            )
            if not href_match or not rank_match:
                continue

            href = self._normalize_link(href_match.group(1))
            if not href.startswith("https://v.daum.net/v/"):
                continue

            rank = self._to_int(rank_match.group(1))
            if rank is None:
                continue

            anchor_inner_html = anchor_match.group(2)
            headline = self._extract_title(anchor_inner_html)
            if not headline:
                continue

            source_and_time = self._extract_source_and_time(anchor_inner_html)
            summary = self._extract_summary(anchor_inner_html)
            items.append(
                {
                    "headline": headline,
                    "title": headline,
                    "url": href,
                    "link": href,
                    "category": category,
                    "board_or_category": category,
                    "rank_position": rank,
                    "publisher": source_and_time[0],
                    "published_at": source_and_time[1],
                    "summary": summary,
                    "collection_method": "daum_news_category_html",
                    "query": "",
                    "is_fallback": False,
                    "collected_at": datetime.now().isoformat(),
                }
            )

        return items[: self.max_items_per_category]

    def _extract_title(self, anchor_inner_html: str) -> str:
        title_match = re.search(
            r'<strong[^>]*class="[^"]*tit_txt[^"]*"[^>]*>(.*?)</strong>',
            anchor_inner_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not title_match:
            return ""

        return self._clean_text(title_match.group(1))

    def _extract_source_and_time(self, anchor_inner_html: str) -> Tuple[str, str]:
        source = ""
        published_at = ""
        txt_info_pattern = re.compile(
            r'<span[^>]*class="txt_info"[^>]*>(.*?)</span>',
            flags=re.IGNORECASE | re.DOTALL,
        )
        txt_info_matches = [
            self._clean_text(match)
            for match in txt_info_pattern.findall(anchor_inner_html)
        ]
        if txt_info_matches:
            source = txt_info_matches[0]
            if len(txt_info_matches) > 1:
                published_at = txt_info_matches[1]
        return source, published_at

    def _extract_summary(self, anchor_inner_html: str) -> str:
        summary_match = re.search(
            r'<p[^>]*class="[^"]*desc_txt[^"]*"[^>]*>(.*?)</p>',
            anchor_inner_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not summary_match:
            return ""
        return self._clean_text(summary_match.group(1))

    def _normalize_link(self, link: str) -> str:
        url = html.unescape(str(link)).strip()
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return urllib.parse.urljoin("https://news.daum.net", url)
        return url

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

    def _to_int(self, value: Optional[str]) -> Optional[int]:
        if not value or not str(value).strip().isdigit():
            return None
        try:
            return int(str(value).strip())
        except Exception:
            return None

    def _dedupe(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        deduped = []
        for item in items:
            key = item.get("link") or item.get("headline")
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    def _record_diagnostic(self) -> None:
        try:
            if self.last_status.get("success"):
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="daum_news",
                    reason="",
                    status="ok",
                )
            else:
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="daum_news",
                    reason=self.last_status.get("failed_reason", "unknown_error"),
                    status="fallback_used",
                )
                self.service_diagnostic.record(diagnostic)

            self.last_status["service_diagnostic"] = diagnostic
        except Exception as error:
            print(f"Daum News Service Diagnostic Failed: {error}")

    def _classify_error(self, error: Exception) -> str:
        if isinstance(error, HTTPError):
            if error.code == 403:
                return "http_403_forbidden"
            return f"http_{error.code}"

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
            if "refused" in reason_text or "10061" in reason_text:
                return "connection_refused"
            return "network_error"

        if isinstance(error, (re.error, ValueError)):
            return "parse_failed"

        return "unknown_error"

    def _primary_failed_reason(self, errors: List[Dict[str, str]]) -> str:
        priority = [
            "http_403_forbidden",
            "connection_refused",
            "timeout",
            "network_error",
            "parse_failed",
            "empty_or_stale_category_page",
            "redirected_category_url",
            "no_valid_category_urls",
            "no_results",
            "unknown_error",
        ]
        reasons = [item.get("reason", "unknown_error") for item in errors]
        for reason in priority:
            if reason in reasons:
                return reason
        return reasons[0] if reasons else "unknown_error"
