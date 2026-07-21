import html
import re
import socket
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError

from modules.common.service_diagnostic import ServiceDiagnostic
from modules.source_intake.source_intake_schema import (
    build_media_flags,
    build_visible_metrics,
)


class NatePannCollector:
    def __init__(self, timeout: int = 8, max_items: int = 10):
        self.timeout = timeout
        self.max_items = max_items
        self.service_diagnostic = ServiceDiagnostic()
        self.last_status = self._empty_status()
        self.endpoints = [
            {
                "url": "https://pann.nate.com/talk/ranking",
                "label": "ranking",
            },
            {
                "url": "https://pann.nate.com/talk/talker",
                "label": "talker",
            },
            {
                "url": "https://pann.nate.com/talk/c20002",
                "label": "issue",
            },
        ]

    def _empty_status(self) -> Dict[str, Any]:
        return {
            "source": "nate_pann",
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
                "service": "nate_pann",
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

        for endpoint in self.endpoints:
            try:
                raw_html = self._fetch_url(endpoint["url"])
                articles = self._parse_articles(raw_html)

                if not articles:
                    errors.append(
                        {
                            "endpoint": endpoint["label"],
                            "reason": "empty_result",
                            "message": "No parsable Nate Pann article links found.",
                        }
                    )
                    continue

                results.extend(
                    self._build_items(
                        articles=articles,
                        source=source,
                        collection_method="nate_pann_html",
                    )
                )
            except Exception as error:
                reason = self._classify_error(error)
                errors.append(
                    {
                        "endpoint": endpoint["label"],
                        "reason": reason,
                        "message": reason,
                    }
                )
                print(f"Nate Pann Collect Failed: {endpoint['label']} / final_error_type={reason}")

        deduped = self._dedupe(results)[:self.max_items]
        self.last_status["success"] = bool(deduped)
        self.last_status["count"] = len(deduped)

        if deduped:
            self.last_status["collection_method"] = "nate_pann_html"
        elif errors:
            self.last_status["failed_reason"] = self._primary_failed_reason(errors)
            self.last_status["final_error_type"] = self.last_status["failed_reason"]
            self.last_status["error_message"] = "; ".join(
                f"{item['endpoint']}: {item['reason']}"
                for item in errors[:5]
            )
        else:
            self.last_status["failed_reason"] = "empty_result"
            self.last_status["final_error_type"] = "empty_result"
            self.last_status["error_message"] = "Nate Pann returned no items."

        self._record_diagnostic()

        return deduped

    def _record_diagnostic(self) -> None:
        try:
            if self.last_status.get("success"):
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="nate_pann",
                    reason="",
                    status="ok",
                )
            else:
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="nate_pann",
                    reason=self.last_status.get("failed_reason", "unknown_error"),
                    status="fallback_used",
                )
                self.service_diagnostic.record(diagnostic)

            self.last_status["service_diagnostic"] = diagnostic
        except Exception as error:
            print(f"Nate Pann Service Diagnostic Failed: {error}")

    def _fetch_url(self, url: str) -> str:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,*/*;q=0.8"
                ),
                "Referer": "https://pann.nate.com/",
            },
        )

        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return response.read().decode("utf-8", errors="ignore")

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

            if "refused" in reason_text or "10061" in reason_text:
                return "connection_refused"

            if "forbidden" in reason_text or "403" in reason_text:
                return "http_403"

            return "network_error"

        if isinstance(error, re.error):
            return "parse_error"

        return "unknown_error"

    def _primary_failed_reason(self, errors: List[Dict[str, str]]) -> str:
        priority = [
            "http_403",
            "connection_refused",
            "timeout",
            "network_error",
            "parse_error",
            "empty_result",
            "unknown_error",
        ]
        reasons = [item.get("reason", "unknown_error") for item in errors]

        for reason in priority:
            if reason in reasons:
                return reason

        return reasons[0] if reasons else "unknown_error"

    def _parse_articles(self, raw_html: str) -> List[Dict[str, Any]]:
        articles = self._parse_article_blocks(raw_html)

        if articles:
            return articles

        return self._parse_articles_legacy(raw_html)

    def _parse_article_blocks(self, raw_html: str) -> List[Dict[str, Any]]:
        """Parse Nate Pann ranking/talker list <li> blocks with visible metrics.

        Real list markup (2026-07 capture):
            <li>
              <div class="thumb"><a href="/talk/ID"><img ... /></a></div>
              <dl>
                <dt><h2><a href="/talk/ID" title="...">제목</a></h2>
                    <span class="reple-num">(98)</span></dt>
                <dd class="txt"><a href="/talk/ID">본문 요약...</a></dd>
                <dd class="info"><span class="count">조회 74,428</span>
                    <span class="rcm">추천 249</span></dd>
              </dl>
            </li>

        Metrics that are not present in a block stay None — never guessed.
        """
        articles = []
        block_pattern = re.compile(r"<li\b[^>]*>(.*?)</li>", re.IGNORECASE | re.DOTALL)
        title_pattern = re.compile(
            r'<dt[^>]*>\s*<h2[^>]*>\s*<a[^>]+href="([^"]*/talk/[^"]*?)(?:\?[^"]*)?"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        comment_pattern = re.compile(
            r'class="reple-num"[^>]*>\s*\(([^)<]*)\)', re.IGNORECASE
        )
        views_pattern = re.compile(
            r'<span[^>]+class="count"[^>]*>(.*?)</span>', re.IGNORECASE | re.DOTALL
        )
        likes_pattern = re.compile(
            r'<span[^>]+class="rcm"[^>]*>(.*?)</span>', re.IGNORECASE | re.DOTALL
        )
        summary_pattern = re.compile(
            r'<dd[^>]+class="txt"[^>]*>\s*<a[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL
        )

        for block_match in block_pattern.finditer(raw_html):
            block = block_match.group(1)
            title_match = title_pattern.search(block)

            if not title_match:
                continue

            title = self._clean_text(title_match.group(2))

            if not self._is_valid_title(title):
                continue

            summary_match = summary_pattern.search(block)
            views_match = views_pattern.search(block)
            comment_match = comment_pattern.search(block)
            likes_match = likes_pattern.search(block)
            image_count = len(re.findall(r"<img\b", block, flags=re.IGNORECASE))

            articles.append(
                {
                    "title": title,
                    "link": self._normalize_link(title_match.group(1)),
                    "summary": self._clean_text(summary_match.group(1)) if summary_match else "",
                    "board_or_category": "",
                    "visible_metrics": {
                        "views": self._parse_metric_number(
                            views_match.group(1) if views_match else None
                        ),
                        "comments": self._parse_metric_number(
                            comment_match.group(1) if comment_match else None
                        ),
                        "likes": self._parse_metric_number(
                            likes_match.group(1) if likes_match else None
                        ),
                    },
                    "media_flags": {
                        "has_image": True if image_count > 0 else None,
                        "image_count": image_count if image_count > 0 else None,
                        "has_video": None,
                    },
                }
            )

        return articles

    def _parse_metric_number(self, text: Optional[str]) -> Optional[int]:
        """'1,234' / '조회 1,234' / '댓글 56' / '1.2만' -> int; unparsable -> None."""
        if text is None:
            return None

        cleaned = self._clean_text(str(text))

        if not cleaned:
            return None

        match = re.search(r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(만|천)?", cleaned)

        if not match:
            return None

        try:
            value = float(match.group(1).replace(",", ""))
        except ValueError:
            return None

        unit = match.group(2)

        if unit == "만":
            value *= 10000
        elif unit == "천":
            value *= 1000

        if value < 0 or value != int(value):
            return None

        return int(value)

    def _parse_articles_legacy(self, raw_html: str) -> List[Dict[str, Any]]:
        articles = []
        patterns = [
            r'<a[^>]+href="([^"]*/talk/[^"]*?)(?:\?[^"]*)?"[^>]*>(.*?)</a>',
            r'<a[^>]+href="([^"]*/bbs/[^"]*?)(?:\?[^"]*)?"[^>]*>(.*?)</a>',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, raw_html, flags=re.IGNORECASE | re.DOTALL)

            for link, title_html in matches:
                title = self._clean_text(title_html)
                normalized_link = self._normalize_link(link)

                if not self._is_valid_title(title):
                    continue

                articles.append(
                    {
                        "title": title,
                        "link": normalized_link,
                        "summary": "",
                    }
                )

        return articles

    def _build_items(
        self,
        articles: List[Dict[str, str]],
        source: Dict[str, Any],
        collection_method: str,
    ) -> List[Dict[str, Any]]:
        items = []

        for index, article in enumerate(articles[:self.max_items], start=1):
            title = article.get("title", "")

            if not title:
                continue

            items.append(
                {
                    "keyword": title,
                    "link": article.get("link", ""),
                    "summary": article.get("summary", ""),
                    "publisher": "pann.nate.com",
                    "published_at": "",
                    "query": "",
                    "source_id": "nate_pann",
                    "source_name": source.get("name", "Nate Pann"),
                    "source_type": source.get("type", "community"),
                    "tier": int(source.get("tier", 1)),
                    "weight": int(source.get("weight", 30)),
                    "base_score": 115 - index,
                    "trend_reason": "Nate Pann ranking/talker/issue article",
                    "collection_method": collection_method,
                    "is_fallback": False,
                    "collected_at": datetime.now().isoformat(),
                    "rank_position": index,
                    "board_or_category": article.get("board_or_category", ""),
                    "visible_metrics": build_visible_metrics(article.get("visible_metrics")),
                    "media_flags": build_media_flags(article.get("media_flags")),
                }
            )

        return items

    def _normalize_link(self, link: str) -> str:
        link = html.unescape(str(link)).strip()

        if not link:
            return ""

        if link.startswith("//"):
            return "https:" + link

        if link.startswith("/"):
            return urllib.parse.urljoin("https://pann.nate.com", link)

        if link.startswith("http"):
            return link

        return urllib.parse.urljoin("https://pann.nate.com", link)

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

    def _is_valid_title(self, title: str) -> bool:
        if len(title) < 4:
            return False

        blocked = {
            "톡톡",
            "톡커들의 선택 명예의 전당",
            "판포토",
            "이슈",
            "랭킹",
            "전체",
            "댓글",
            "이전",
            "다음",
        }

        return title not in blocked

    def _dedupe(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        deduped = []

        for item in items:
            key = item.get("link") or item.get("keyword")

            if not key or key in seen:
                continue

            seen.add(key)
            deduped.append(item)

        return deduped
