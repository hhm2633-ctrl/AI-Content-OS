import html
import re
import socket
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError

from modules.common.service_diagnostic import ServiceDiagnostic
from modules.trend_collector.naver_api_hub_client import NaverApiHubClient


class NaverNewsCollector:
    # Anchor/attribute scanning must not depend on attribute order, quote
    # style, or extra attributes injected by markup changes.
    _ANCHOR_PATTERN = re.compile(
        r"<a\b([^>]*)>(.*?)</a\s*>",
        flags=re.IGNORECASE | re.DOTALL,
    )
    _ATTRIBUTE_PATTERN = re.compile(
        r"""([\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')"""
    )
    # Lenient RSS recovery for payloads ET refuses (unbound prefixes,
    # stray entities) while <item> blocks are still intact.
    _LENIENT_ITEM_PATTERN = re.compile(
        r"<(?:[\w.-]+:)?item(?=[\s>])[^>]*>(.*?)</(?:[\w.-]+:)?item\s*>",
        flags=re.IGNORECASE | re.DOTALL,
    )

    def __init__(
        self,
        timeout: int = 8,
        max_items_per_query: int = 5,
        api_hub_client: Optional[NaverApiHubClient] = None,
    ):
        self.timeout = timeout
        self.max_items_per_query = max_items_per_query
        self.service_diagnostic = ServiceDiagnostic()
        self.api_hub_client = (
            api_hub_client
            if api_hub_client is not None
            else NaverApiHubClient(timeout=timeout)
        )
        self.last_status = self._empty_status()

    def _empty_status(self) -> Dict[str, Any]:
        return {
            "source": "naver_news",
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
            "api_hub": {
                "attempted": False,
                "used": False,
                "credentials_present": None,
                "error_type": "",
                "safe_message": "",
            },
            "service_diagnostic": {
                "service": "naver_news",
                "status": "ok",
                "error_type": "",
                "safe_message": "",
                "api_key_present": None,
            },
        }

    def collect(
        self,
        query_keywords: List[str],
        source: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        results = []
        errors = []
        self.last_status = self._empty_status()
        self.last_status["attempted"] = True

        for query in query_keywords:
            try:
                results.extend(self._collect_by_query(query=query, source=source))
            except Exception as error:
                reason = self._classify_error(error)
                errors.append(
                    {
                        "query": query,
                        "reason": reason,
                        "message": reason,
                    }
                )
                print(f"Naver News Collect Failed: {query} / final_error_type={reason}")

        deduped = self._dedupe(results)
        self.last_status["success"] = bool(deduped)
        self.last_status["count"] = len(deduped)

        if deduped:
            self.last_status["collection_method"] = deduped[0].get(
                "collection_method",
                "naver_news_rss",
            )
        elif errors:
            self.last_status["failed_reason"] = self._primary_failed_reason(errors)
            self.last_status["final_error_type"] = self.last_status["failed_reason"]
            self.last_status["error_message"] = "; ".join(
                f"{item['query']}: {item['reason']}"
                for item in errors[:5]
            )
        else:
            self.last_status["failed_reason"] = "no_results"
            self.last_status["final_error_type"] = "no_results"
            self.last_status["error_message"] = "Naver News returned no parsable items."

        self._record_diagnostic()

        return deduped

    def _record_diagnostic(self) -> None:
        try:
            if self.last_status.get("success"):
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="naver_news",
                    reason="",
                    status="ok",
                )
            else:
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="naver_news",
                    reason=self.last_status.get("failed_reason", "unknown_error"),
                    status="fallback_used",
                )
                self.service_diagnostic.record(diagnostic)

            self.last_status["service_diagnostic"] = diagnostic
        except Exception as error:
            print(f"Naver News Service Diagnostic Failed: {error}")

    def _collect_by_query(
        self,
        query: str,
        source: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """API Hub -> RSS -> HTML search chain for a single query.

        An RSS payload that cannot be parsed no longer aborts the query: the
        HTML search path is still attempted, and the original ParseError is
        re-raised only if HTML also yields nothing, so the parse_failed
        reason code is preserved for the outer fallback chain.
        """
        api_hub_items = self._collect_from_api_hub(query=query, source=source)

        if api_hub_items:
            return api_hub_items

        rss_parse_error: Optional[ET.ParseError] = None

        try:
            rss_items = self._collect_from_rss(query=query, source=source)
        except ET.ParseError as error:
            rss_items = []
            rss_parse_error = error

        if rss_items:
            return rss_items

        html_items = self._collect_from_search_result(query=query, source=source)

        if html_items:
            return html_items

        if rss_parse_error is not None:
            raise rss_parse_error

        return []

    def _collect_from_api_hub(
        self,
        query: str,
        source: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Optional NAVER API HUB path ahead of the bounded RSS/HTML chain.

        Any API failure is recorded as a diagnostic in last_status["api_hub"]
        and returns [] so the existing RSS -> HTML -> cache -> settings ->
        placeholder fallback chain stays intact. This method never raises.
        """
        api_status = self.last_status.get("api_hub")

        if self.api_hub_client is None or not isinstance(api_status, dict):
            return []

        try:
            result = self.api_hub_client.search_news(
                query=query,
                display=self.max_items_per_query,
            )
            credentials_present = bool(result.get("credentials_present"))
            api_status["credentials_present"] = credentials_present

            if result.get("status") == "ok":
                api_status["attempted"] = True
                api_status["used"] = True
                api_status["error_type"] = ""
                api_status["safe_message"] = ""
                trends = []

                for index, item in enumerate(
                    result.get("items", [])[: self.max_items_per_query],
                    start=1,
                ):
                    title = str(item.get("title", "")).strip()

                    if not title:
                        continue

                    trends.append(
                        self._build_trend_item(
                            query=query,
                            title=title,
                            link=str(item.get("link", "")),
                            summary=str(item.get("description", "")),
                            published_at=str(item.get("pubDate", "")),
                            index=index,
                            source=source,
                            collection_method="naver_news_api_hub",
                        )
                    )

                return trends

            api_status["attempted"] = bool(api_status.get("attempted")) or credentials_present

            if not api_status.get("used"):
                api_status["error_type"] = result.get("error_type", "")
                api_status["safe_message"] = result.get("safe_message", "")

            return []
        except Exception:
            api_status["attempted"] = True

            if not api_status.get("used"):
                api_status["error_type"] = "unknown_error"
                api_status["safe_message"] = (
                    "NAVER API HUB call failed unexpectedly; using RSS fallback."
                )

            return []

    def _collect_from_rss(
        self,
        query: str,
        source: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        encoded_query = urllib.parse.quote(query)
        url = f"https://search.naver.com/search.naver?where=rss&query={encoded_query}"
        raw_xml = self._fetch_url(url)

        return self._parse_rss_payload(query=query, source=source, raw_xml=raw_xml)

    def _parse_rss_payload(
        self,
        query: str,
        source: Dict[str, Any],
        raw_xml: str,
    ) -> List[Dict[str, Any]]:
        """Parse an RSS payload, tolerating namespaces and case variance.

        HTML payloads (the RSS endpoint serving a search page) and
        unrecoverably malformed XML raise ET.ParseError so the caller can
        try the HTML search path while keeping the parse_failed reason.
        """
        if self._looks_like_html(raw_xml):
            raise ET.ParseError("rss payload is an html document")

        try:
            root = ET.fromstring(raw_xml)
        except ET.ParseError as parse_error:
            lenient_items = self._parse_rss_items_lenient(
                query=query,
                source=source,
                raw_xml=raw_xml,
            )

            if lenient_items:
                return lenient_items

            raise parse_error

        items = self._find_rss_items(root)
        trends = []

        for index, item in enumerate(items[:self.max_items_per_query], start=1):
            title = self._clean_text(self._find_text(item, "title"))
            link = self._clean_text(
                self._find_text(item, "originallink")
                or self._find_text(item, "link")
            )
            summary = self._clean_text(self._find_text(item, "description"))
            published_at = self._clean_text(self._find_text(item, "pubDate"))

            if not title:
                continue

            trends.append(
                self._build_trend_item(
                    query=query,
                    title=title,
                    link=link,
                    summary=summary,
                    published_at=published_at,
                    index=index,
                    source=source,
                    collection_method="naver_news_rss",
                )
            )

        return trends

    def _find_rss_items(self, root: ET.Element) -> List[ET.Element]:
        items = []

        for element in root.iter():
            if self._xml_local_name(element.tag) == "item":
                items.append(element)

        return items

    def _xml_local_name(self, tag: Any) -> str:
        # Comments/processing instructions surface non-string tags in ET.
        if not isinstance(tag, str):
            return ""

        return tag.rsplit("}", 1)[-1].strip().lower()

    def _parse_rss_items_lenient(
        self,
        query: str,
        source: Dict[str, Any],
        raw_xml: str,
    ) -> List[Dict[str, Any]]:
        trends = []

        for match in self._LENIENT_ITEM_PATTERN.finditer(raw_xml):
            if len(trends) >= self.max_items_per_query:
                break

            block = match.group(1)
            title = self._clean_text(self._extract_tag_text(block, "title"))

            if not title:
                continue

            link = self._clean_text(
                self._extract_tag_text(block, "originallink")
                or self._extract_tag_text(block, "link")
            )
            summary = self._clean_text(self._extract_tag_text(block, "description"))
            published_at = self._clean_text(self._extract_tag_text(block, "pubDate"))

            trends.append(
                self._build_trend_item(
                    query=query,
                    title=title,
                    link=link,
                    summary=summary,
                    published_at=published_at,
                    index=len(trends) + 1,
                    source=source,
                    collection_method="naver_news_rss",
                )
            )

        return trends

    def _extract_tag_text(self, block: str, tag_name: str) -> str:
        escaped = re.escape(tag_name)
        pattern = re.compile(
            rf"<(?:[\w.-]+:)?{escaped}(?=[\s>/])[^>]*>(.*?)</(?:[\w.-]+:)?{escaped}\s*>",
            flags=re.IGNORECASE | re.DOTALL,
        )
        match = pattern.search(block)

        if not match:
            return ""

        return self._strip_cdata(match.group(1))

    def _strip_cdata(self, text: str) -> str:
        return re.sub(
            r"<!\[CDATA\[(.*?)\]\]>",
            r"\1",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

    def _looks_like_html(self, text: str) -> bool:
        stripped = (text or "").lstrip().lower()
        return stripped.startswith("<!doctype html") or stripped.startswith("<html")

    def _collect_from_search_result(
        self,
        query: str,
        source: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        encoded_query = urllib.parse.quote(query)
        url = (
            "https://search.naver.com/search.naver"
            f"?where=news&query={encoded_query}&sort=1"
        )
        raw_html = self._fetch_url(url)
        articles = self._parse_search_result_articles(raw_html)
        trends = []

        for index, article in enumerate(articles[:self.max_items_per_query], start=1):
            title = article.get("title", "")

            if not title:
                continue

            trends.append(
                self._build_trend_item(
                    query=query,
                    title=title,
                    link=article.get("link", ""),
                    summary=article.get("summary", ""),
                    published_at="",
                    index=index,
                    source=source,
                    collection_method="naver_news_html",
                )
            )

        return trends

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
            },
        )

        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return response.read().decode("utf-8", errors="ignore")

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

            if "forbidden" in reason_text or "403" in reason_text:
                return "http_403_forbidden"

            return "network_error"

        if isinstance(error, ET.ParseError):
            return "parse_failed"

        return "unknown_error"

    def _primary_failed_reason(self, errors: List[Dict[str, str]]) -> str:
        priority = [
            "http_403_forbidden",
            "connection_refused",
            "timeout",
            "network_error",
            "parse_failed",
            "no_results",
            "unknown_error",
        ]
        reasons = [item.get("reason", "unknown_error") for item in errors]

        for reason in priority:
            if reason in reasons:
                return reason

        return reasons[0] if reasons else "unknown_error"

    def _parse_search_result_articles(self, raw_html: str) -> List[Dict[str, str]]:
        """Extract visible title/link/summary from search-result markup.

        Anchors are matched by parsed attributes instead of positional
        regexes, so attribute reordering or new attributes cannot break
        extraction. Supports the legacy news_tit layout and the newer
        data-heatmap-target layout. Missing fields stay empty strings —
        nothing is fabricated.
        """
        anchors = self._extract_anchor_tags(raw_html)
        articles = self._extract_news_tit_articles(anchors)

        if articles:
            return articles

        return self._extract_heatmap_articles(anchors)

    def _extract_anchor_tags(self, raw_html: str) -> List[Dict[str, Any]]:
        anchors = []

        for match in self._ANCHOR_PATTERN.finditer(raw_html):
            attributes = {}

            for attr in self._ATTRIBUTE_PATTERN.finditer(match.group(1)):
                name = attr.group(1).lower()
                value = attr.group(2) if attr.group(2) is not None else attr.group(3)
                attributes[name] = value or ""

            anchors.append(
                {
                    "attributes": attributes,
                    "inner_html": match.group(2),
                }
            )

        return anchors

    def _extract_news_tit_articles(
        self,
        anchors: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        articles = []

        for anchor in anchors:
            attributes = anchor["attributes"]

            if "news_tit" not in attributes.get("class", ""):
                continue

            title = (
                self._clean_text(attributes.get("title", ""))
                or self._clean_text(anchor["inner_html"])
            )

            if not title:
                continue

            articles.append(
                {
                    "title": title,
                    "link": html.unescape(attributes.get("href", "")),
                    "summary": "",
                }
            )

        return articles

    def _extract_heatmap_articles(
        self,
        anchors: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        articles = []
        current: Optional[Dict[str, str]] = None

        for anchor in anchors:
            target = anchor["attributes"].get("data-heatmap-target", "")

            if target == ".tit":
                if current is not None:
                    articles.append(current)
                    current = None

                title = self._clean_text(anchor["inner_html"])

                if not title:
                    continue

                current = {
                    "title": title,
                    "link": html.unescape(anchor["attributes"].get("href", "")),
                    "summary": "",
                }
            elif target == ".body" and current is not None and not current["summary"]:
                current["summary"] = self._clean_text(anchor["inner_html"])

        if current is not None:
            articles.append(current)

        return articles

    def _build_trend_item(
        self,
        query: str,
        title: str,
        link: str,
        summary: str,
        published_at: str,
        index: int,
        source: Dict[str, Any],
        collection_method: str,
    ) -> Dict[str, Any]:
        return {
            "keyword": title,
            "link": link,
            "summary": summary,
            "publisher": self._extract_publisher(link),
            "published_at": published_at,
            "query": query,
            "source_id": source.get("source_id", "naver_news"),
            "source_name": source.get("name", "Naver News"),
            "source_type": source.get("type", "news"),
            "tier": int(source.get("tier", 1)),
            "weight": int(source.get("weight", 30)),
            "base_score": 120 - index,
            "trend_reason": f"Naver News query: {query}",
            "collection_method": collection_method,
            "is_fallback": False,
            "collected_at": datetime.now().isoformat(),
        }

    def _extract_publisher(self, link: str) -> str:
        if not link:
            return ""

        domain = urllib.parse.urlparse(link).netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    def _find_text(self, item: ET.Element, tag_name: str) -> str:
        target = tag_name.strip().lower()

        for child in list(item):
            if self._xml_local_name(child.tag) == target:
                return self._element_text(child)

        for descendant in item.iter():
            if descendant is not item and self._xml_local_name(descendant.tag) == target:
                return self._element_text(descendant)

        return ""

    def _element_text(self, element: ET.Element) -> str:
        return "".join(element.itertext())

    def _clean_text(self, text: Optional[str]) -> str:
        if not text:
            return ""

        text = re.sub(r"<.*?>", "", str(text))
        text = html.unescape(text)
        text = text.replace("\n", " ").replace("\t", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

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
