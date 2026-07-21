import html
import re
import socket
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError

from modules.common.service_diagnostic import ServiceDiagnostic


class NewsisCollector:
    """Low-cost Newsis collector using verified server-rendered selectors only.

    Verified contracts used:
    - list pages: ul.articleList2 > li > div.boxStyle05
    - ranking: div.rankBox with topnews* tabs and ul.left / ul.right
    """

    CID_SCID_DEFAULT = (10200, 10201)

    def __init__(self, timeout: int = 8, max_items: int = 30, config: Optional[Dict[str, Any]] = None):
        self.timeout = timeout
        self.max_items = max_items
        self.config = config or {}
        self.service_diagnostic = ServiceDiagnostic()
        self.last_status = self._empty_status()
        self.cid_to_section = {
            "10300": "politic",
            "10100": "world",
            "10400": "economy",
            "15000": "money",
            "13000": "business",
            "13100": "health",
            "10200": "society",
            "14000": "metro",
            "10800": "region",
            "10700": "culture",
            "10500": "sports",
            "10600": "entertainment",
        }
        self.section_to_category = {v: v for v in self.cid_to_section.values()}

    def _empty_status(self) -> Dict[str, Any]:
        return {
            "source": "newsis",
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
                "service": "newsis",
                "status": "ok",
                "error_type": "",
                "safe_message": "",
                "api_key_present": None,
            },
        }

    def collect(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.last_status = self._empty_status()
        self.last_status["attempted"] = True
        source_url = str(source.get("url", "") or "").strip()
        result: List[Dict[str, Any]] = []
        errors: List[Dict[str, str]] = []

        target_url = self._build_target_url(source_url)
        try:
            fetched_url, raw_html = self._fetch_url(target_url)
            if self._is_error_page(fetched_url, raw_html):
                errors.append({"reason": "error_page"})
            else:
                list_items = self._parse_article_list(raw_html, source, self._derive_category(fetched_url))
                if list_items:
                    result.extend(list_items)

                rank_items = self._parse_rank_box(raw_html, source)
                result.extend(rank_items)

        except Exception as error:
            errors.append({"reason": self._classify_error(error), "message": str(error)})

        deduped = self._dedupe(result)
        if deduped:
            self.last_status["success"] = True
            self.last_status["count"] = len(deduped)
            self.last_status["collection_method"] = "newsis_server_rendered"
            self._record_diagnostic()
            return deduped

        self.last_status["failed_reason"] = self._primary_failed_reason(errors)
        self.last_status["final_error_type"] = self.last_status["failed_reason"]
        self.last_status["error_message"] = self.last_status["failed_reason"] or "no verified items"
        self.last_status["count"] = 0
        self._record_diagnostic()
        return []

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
            return response.geturl(), response.read().decode("utf-8", errors="ignore")

    def _build_target_url(self, source_url: str) -> str:
        parsed = urllib.parse.urlparse(source_url)
        path = (parsed.path or "").strip("/")

        if path and path.endswith("list"):
            query = urllib.parse.parse_qs(parsed.query or "")
            cid = (query.get("cid") or [str(self.CID_SCID_DEFAULT[0])])[0]
            scid = (query.get("scid") or [str(self.CID_SCID_DEFAULT[1])])[0]
            return f"https://www.newsis.com/{path}/?cid={cid}&scid={scid}"

        if path and path in self.section_to_category:
            return f"https://www.newsis.com/{path}/list/?cid={self._section_to_cid(path)}&scid={self._default_scid(path)}"

        return (
            f"https://www.newsis.com/society/list/?cid={self.CID_SCID_DEFAULT[0]}&"
            f"scid={self.CID_SCID_DEFAULT[1]}"
        )

    def _section_to_cid(self, section: str) -> str:
        for key, value in self.cid_to_section.items():
            if value == section:
                return key
        return str(self.CID_SCID_DEFAULT[0])

    def _default_scid(self, section: str) -> str:
        overrides = {
            "society": "10201",
            "politic": "10301",
            "world": "10101",
            "economy": "10401",
            "money": "15001",
            "business": "13001",
            "health": "13101",
            "metro": "14001",
            "region": "10801",
            "culture": "10701",
            "sports": "10501",
            "entertainment": "10601",
        }
        return overrides.get(section, str(self.CID_SCID_DEFAULT[1]))

    def _derive_category(self, fetched_url: str) -> str:
        parsed = urllib.parse.urlparse(fetched_url)
        path = (parsed.path or "").strip("/")
        if not path or "list" not in path:
            return ""
        return path.split("/")[0]

    def _is_error_page(self, fetched_url: str, raw_html: str) -> bool:
        if not fetched_url or "/error/" in fetched_url:
            return True

        cleaned = (raw_html or "").lower()
        return "error" in cleaned and "newsis" in cleaned and "404" in cleaned

    def _parse_article_list(
        self,
        raw_html: str,
        source: Dict[str, Any],
        category: str,
    ) -> List[Dict[str, Any]]:
        container = self._extract_between(raw_html, r'<ul[^>]*class="[^"]*articleList2[^"]*"[^>]*>', r"</ul>")
        if not container:
            return []

        items: List[Dict[str, Any]] = []
        item_pattern = re.compile(
            r"<li[^>]*>(.*?)</li>",
            flags=re.IGNORECASE | re.DOTALL,
        )
        for rank, item_html in enumerate(item_pattern.findall(container), start=1):
            parsed = self._parse_article_item(item_html, source, category, rank)
            if parsed:
                items.append(parsed)
                if len(items) >= self.max_items:
                    break

        return items

    def _parse_article_item(
        self,
        item_html: str,
        source: Dict[str, Any],
        category: str,
        rank: int,
    ) -> Optional[Dict[str, Any]]:
        headline = self._extract_text_from_selector(item_html, r'<p[^>]*class="[^"]*tit[^"]*"[^>]*>.*?<a[^>]*>(.*?)</a>')
        raw_link = self._extract_attr_from_selector(item_html, r'<p[^>]*class="[^"]*tit[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)"', "href")
        article_id = self._extract_article_id(raw_link)
        if not headline or not raw_link or not article_id:
            return None

        summary = self._extract_text_from_selector(item_html, r'<p[^>]*class="[^"]*txt[^"]*"[^>]*>.*?<a[^>]*>(.*?)</a>')
        reporter = self._extract_text_from_selector(item_html, r'<p[^>]*class="time"[^>]*>.*?<span[^>]*>(.*?)</span>')
        time_text = self._extract_text_from_selector(item_html, r'<p[^>]*class="time"[^>]*>(.*?)</p>') or ""
        published_at = self._normalize_published_at(time_text, reporter)
        thumbnail = self._extract_attr_from_selector(item_html, r'<div[^>]*class="[^"]*thumCont[^"]*"[^>]*>.*?<img[^>]+src="([^"]+)"', "src")

        link = self._normalize_link(raw_link)
        if not link:
            return None

        return {
            "surface": "list",
            "headline": headline,
            "title": headline,
            "link": link,
            "article_id": article_id,
            "summary": summary,
            "reporter": reporter,
            "published_at": published_at,
            "thumbnail": self._normalize_link(thumbnail),
            "publisher": "뉴시스",
            "category": category or self._derive_category_from_source(source),
            "board_or_category": category or self._derive_category_from_source(source),
            "rank_position": rank,
            "source_id": source.get("source_id", "newsis"),
            "source_name": source.get("name", "뉴시스"),
            "source_type": source.get("type", "news_wire"),
            "tier": int(source.get("tier", 1)),
            "weight": int(source.get("weight", 20)),
            "collection_method": "newsis_articleList2",
            "is_fallback": False,
            "collected_at": datetime.now().isoformat(),
        }

    def _parse_rank_box(self, raw_html: str, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        rank_items = self._parse_rank_box_tabs(raw_html)
        if not rank_items:
            return []

        results: List[Dict[str, Any]] = []
        for item in rank_items:
            if not item.get("headline") or not item.get("href"):
                continue

            link = self._normalize_link(item["href"])
            if not link:
                continue

            article_id = self._extract_article_id(link)
            results.append({
                "surface": "rank",
                "headline": item["headline"],
                "title": item["headline"],
                "link": link,
                "article_id": article_id,
                "rank_position": item["rank"],
                "publisher": "뉴시스",
                "source_id": source.get("source_id", "newsis"),
                "source_name": source.get("name", "뉴시스"),
                "source_type": source.get("type", "news_wire"),
                "tier": int(source.get("tier", 1)),
                "weight": int(source.get("weight", 20)),
                "collection_method": "newsis_rank_box",
                "is_fallback": False,
                "collected_at": datetime.now().isoformat(),
            })
        return results[: self.max_items]

    def _parse_rank_box_tabs(self, raw_html: str) -> List[Dict[str, Any]]:
        rank_rows: List[Dict[str, Any]] = []
        if "rankBox" not in raw_html:
            return []

        tab_pattern = re.compile(
            r'<div[^>]+id="topnews(\d+)"[^>]*>(.*?)(?=<div[^>]+id="topnews\d+"|</div>\s*</div>\s*<div[^>]*class="[^"]*sectName|$)',
            flags=re.IGNORECASE | re.DOTALL,
        )
        for match in tab_pattern.finditer(raw_html):
            tab_index = match.group(1)
            block = match.group(2)
            left_items = self._extract_anchors_from_list(
                block,
                r'<ul[^>]*class="[^"]*left[^"]*"[^>]*>(.*?)(?=<ul[^>]*class="[^"]*right[^"]*"[^>]*>|</div>|$)',
            )
            right_items = self._extract_anchors_from_list(
                block,
                r'<ul[^>]*class="[^"]*right[^"]*"[^>]*>(.*?)(?=</div>|$)',
            )
            combined = left_items + right_items
            base_rank = (int(tab_index) - 1) * 12
            for offset, value in enumerate(combined[:12], start=1):
                rank_rows.append(
                    {
                        "rank": base_rank + offset,
                        "headline": value.get("headline", ""),
                        "href": value.get("href", ""),
                    }
                )
        if rank_rows:
            return rank_rows

        # Fallback path for malformed rank block without explicit topnews ids.
        return self._parse_rank_box_fallback(raw_html)

    def _parse_rank_box_fallback(self, raw_html: str) -> List[Dict[str, Any]]:
        tab_blocks = re.findall(
            r'<div[^>]+id="topnews(\d+)"[^>]*>(.*?)</div>',
            raw_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        rank_rows: List[Dict[str, Any]] = []
        for tab_index, block in tab_blocks:
            raw_anchors = self._extract_anchors(block, anchors_only=True)
            if not raw_anchors:
                continue
            base_rank = (int(tab_index) - 1) * 12
            for offset, item in enumerate(raw_anchors[:12], start=1):
                rank_rows.append({"rank": base_rank + offset, "headline": item.get("headline", ""), "href": item.get("href", "")})
        return rank_rows

    def _extract_anchors_from_list(self, html_text: str, list_pattern: str) -> List[Dict[str, str]]:
        list_match = re.search(list_pattern, html_text, flags=re.IGNORECASE | re.DOTALL)
        if not list_match:
            return []
        return self._extract_anchors(list_match.group(1))

    def _extract_anchors(self, text: str, anchors_only: bool = False) -> List[Dict[str, str]]:
        items = []
        for anchor in re.finditer(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', text, flags=re.IGNORECASE | re.DOTALL):
            href = self._normalize_link(anchor.group(1))
            headline = self._clean_text(anchor.group(2))
            if not headline or not href:
                continue
            if anchors_only and not href.startswith("https://www.newsis.com/view/"):
                continue
            items.append({"href": href, "headline": headline})
        return items

    def _extract_text_from_selector(self, raw_html: str, pattern: str) -> str:
        match = re.search(pattern, raw_html, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        return self._clean_text(match.group(1))

    def _extract_attr_from_selector(self, raw_html: str, pattern: str, attr_name: str) -> str:
        match = re.search(pattern, raw_html, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        if attr_name == "href":
            return html.unescape(match.group(1).strip())
        value = html.unescape(match.group(1).strip())
        return value

    def _extract_between(self, raw_html: str, start_pattern: str, end_pattern: str) -> str:
        match = re.search(start_pattern, raw_html, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        start = match.end()
        end_match = re.search(end_pattern, raw_html[start:], flags=re.IGNORECASE | re.DOTALL)
        if not end_match:
            return raw_html[start:]
        return raw_html[start:start + end_match.start()]

    def _extract_article_id(self, link: str) -> str:
        normalized = self._clean_text(link)
        match = re.search(r"(NIS[XI]\d{8}_\d{10})", normalized)
        return match.group(1) if match else ""

    def _normalize_published_at(self, time_text: str, reporter: str) -> str:
        clean_time = self._clean_text(time_text)
        if reporter:
            reporter_clean = self._clean_text(reporter)
            if clean_time.startswith(reporter_clean):
                clean_time = clean_time[len(reporter_clean):].strip()
        match = re.search(r"\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2}", clean_time)
        return match.group(0) if match else ""

    def _normalize_link(self, url: Any) -> str:
        link = self._clean_text(str(url))
        if not link:
            return ""
        if link.startswith("//"):
            return f"https:{link}"
        if link.startswith("/"):
            return urllib.parse.urljoin("https://www.newsis.com", link)
        if link.startswith("http://") or link.startswith("https://"):
            return link
        return ""

    def _derive_category_from_source(self, source: Dict[str, Any]) -> str:
        url = str(source.get("url", "")).strip()
        parsed = urllib.parse.urlparse(url)
        path = (parsed.path or "").strip("/").lower()
        if "/" in path:
            return path.split("/", 1)[0]
        return "newsis"

    def _dedupe(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        deduped = []
        for item in items:
            key = item.get("link") or item.get("headline")
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped[: self.max_items]

    def _record_diagnostic(self) -> None:
        try:
            if self.last_status.get("success"):
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="newsis",
                    reason="",
                    status="ok",
                )
            else:
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="newsis",
                    reason=self.last_status.get("failed_reason", "unknown_error"),
                    status="fallback_used",
                )
                self.service_diagnostic.record(diagnostic)
            self.last_status["service_diagnostic"] = diagnostic
        except Exception as error:
            print(f"Newsis Service Diagnostic Failed: {error}")

    def _clean_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        text = re.sub(r"<script.*?</script>", "", str(text), flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style.*?</style>", "", str(text), flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<.*?>", " ", text)
        text = html.unescape(text)
        text = text.replace("\n", " ").replace("\t", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _classify_error(self, error: Exception) -> str:
        if isinstance(error, HTTPError):
            if error.code == 403:
                return "http_403_forbidden"
            return f"http_{error.code}"
        if isinstance(error, TimeoutError) or isinstance(error, socket.timeout):
            return "timeout"
        if isinstance(error, URLError):
            reason = getattr(error, "reason", "")
            reason_text = str(reason).lower()
            if "timed out" in reason_text or "timeout" in reason_text:
                return "timeout"
            if "forbidden" in reason_text or "403" in reason_text:
                return "http_403_forbidden"
            if "refused" in reason_text or "10061" in reason_text:
                return "connection_refused"
            return "network_error"
        return "unknown_error"

    def _primary_failed_reason(self, errors: Iterable[Dict[str, str]]) -> str:
        reasons = [item.get("reason", "unknown_error") for item in errors]
        if not reasons:
            return "empty_result"
        priority = [
            "http_403_forbidden",
            "http_403",
            "timeout",
            "connection_refused",
            "network_error",
            "parse_error",
            "error_page",
            "empty_result",
            "unknown_error",
        ]
        for reason in priority:
            if reason in reasons:
                return reason
        return reasons[0]
