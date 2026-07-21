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


class MoneyTodayCollector:
    def __init__(self, timeout: int = 8, max_items: int = 12):
        self.timeout = timeout
        self.max_items = max_items
        self.service_diagnostic = ServiceDiagnostic()
        self.last_status = self._empty_status()
        self.news_site_host = "www.mt.co.kr"
        self.sitemap_url = "https://www.mt.co.kr/sitemap/latest.xml"
        self.breakingnews_url = "https://www.mt.co.kr/breakingnews"
        self.home_url = "https://www.mt.co.kr/"

    def _empty_status(self) -> Dict[str, Any]:
        return {
            "source": "moneytoday",
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
                "service": "moneytoday",
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

        collect_methods = [
            ("sitemap", self._collect_from_sitemap),
            ("homepage_ranking", self._collect_from_homepage_ranking),
        ]

        for method_name, collect_method in collect_methods:
            try:
                results.extend(collect_method(source=source))

                if results:
                    break
            except Exception as error:
                reason = self._classify_error(error)
                errors.append(
                    {
                        "method": method_name,
                        "reason": reason,
                        "message": reason,
                    }
                )
                print(f"MoneyToday Collect Failed: {method_name} / final_error_type={reason}")

        if not results:
            try:
                results.extend(self._collect_from_breakingnews(source=source))
            except Exception as error:
                reason = self._classify_error(error)
                errors.append(
                    {
                        "method": "breakingnews",
                        "reason": reason,
                        "message": reason,
                    }
                )
                print(
                    "MoneyToday Collect Failed: breakingnews / "
                    f"final_error_type={reason}"
                )

        deduped = self._dedupe(results)[: self.max_items]
        self.last_status["success"] = bool(deduped)
        self.last_status["count"] = len(deduped)

        if deduped:
            self.last_status["collection_method"] = deduped[0].get(
                "collection_method",
                "moneytoday_latest",
            )
        elif errors:
            self.last_status["failed_reason"] = self._primary_failed_reason(errors)
            self.last_status["final_error_type"] = self.last_status["failed_reason"]
            self.last_status["error_message"] = "; ".join(
                f"{item['method']}: {item['reason']}" for item in errors[:5]
            )
        else:
            self.last_status["failed_reason"] = "no_results"
            self.last_status["final_error_type"] = "no_results"
            self.last_status["error_message"] = "MoneyToday returned no parsable items."

        self._record_diagnostic()

        return deduped

    def _record_diagnostic(self) -> None:
        try:
            if self.last_status.get("success"):
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="moneytoday",
                    reason="",
                    status="ok",
                )
            else:
                diagnostic = self.service_diagnostic.build_diagnostic_from_reason(
                    service="moneytoday",
                    reason=self.last_status.get("failed_reason", "unknown_error"),
                    status="fallback_used",
                )
                self.service_diagnostic.record(diagnostic)

            self.last_status["service_diagnostic"] = diagnostic
        except Exception as error:
            print(f"MoneyToday Service Diagnostic Failed: {error}")

    def _collect_from_sitemap(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_xml = self._fetch_url(self.sitemap_url)
        root = ET.fromstring(raw_xml)
        items = root.findall(".//item")
        if not items:
            items = root.findall(".//url")

        trends = []
        for index, item in enumerate(items, start=1):
            title = self._find_text(item, "title")
            link = self._find_text(item, "loc")
            published_raw = (
                self._find_text(item, "news:publication_date")
                or self._find_text(item, "{http://www.google.com/schemas/sitemap-news/0.9}publication_date")
                or self._find_text(item, "lastmod")
            )
            if not title or not link:
                continue

            normalized = self._normalize_link(link)
            if not normalized:
                continue

            trends.append(
                self._build_trend_item(
                    title=title,
                    link=normalized,
                    summary="",
                    published_at=self._format_kst_datetime(published_raw),
                    reporter="",
                    article_id=self._extract_article_id(normalized),
                    category=self._extract_category(normalized),
                    query="",
                    index=index,
                    source=source,
                    collection_method="moneytoday_sitemap",
                    rank=None,
                )
            )

        return trends

    def _collect_from_homepage_ranking(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_html = self._fetch_url(self.home_url)
        rank_widgets = self._parse_rank_widgets(raw_html)

        trends = []
        index = 1

        for item in rank_widgets:
            title = item.get("title", "")
            link = item.get("link", "")

            if not title or not link:
                continue

            trends.append(
                self._build_trend_item(
                    title=title,
                    link=self._normalize_link(link),
                    summary="",
                    published_at="",
                    reporter="",
                    article_id=self._extract_article_id(link),
                    category=self._extract_category(link),
                    query="",
                    index=index,
                    source=source,
                    collection_method="moneytoday_ranking",
                    rank=item.get("rank"),
                )
            )
            index += 1

        return trends

    def _collect_from_breakingnews(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_html = self._fetch_url(self.breakingnews_url)
        articles = self._parse_breakingnews_articles(raw_html)

        trends = []
        for index, article in enumerate(articles, start=1):
            title = article.get("title", "")
            link = article.get("link", "")

            if not title or not link:
                continue

            trends.append(
                self._build_trend_item(
                    title=title,
                    link=self._normalize_link(link),
                    summary=article.get("summary", ""),
                    published_at=article.get("published_at", ""),
                    reporter=article.get("reporter", ""),
                    article_id=article.get("article_id", ""),
                    category=self._extract_category(link),
                    query="",
                    index=index,
                    source=source,
                    collection_method="moneytoday_breakingnews",
                    rank=None,
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
                "Referer": "https://www.mt.co.kr/",
                "Accept-Language": "ko-KR,ko;q=0.9",
            },
        )

        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return response.read().decode("utf-8", errors="ignore")

    def _classify_error(self, error: Exception) -> str:
        if isinstance(error, HTTPError):
            if error.code == 403:
                return "http_403"
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
                return "http_403"

            return "network_error"

        if isinstance(error, ET.ParseError):
            return "parse_failed"

        return "unknown_error"

    def _primary_failed_reason(self, errors: List[Dict[str, str]]) -> str:
        priority = [
            "http_403",
            "connection_refused",
            "timeout",
            "network_error",
            "parse_failed",
            "parse_error",
            "no_results",
            "empty_result",
            "unknown_error",
        ]
        reasons = [item.get("reason", "unknown_error") for item in errors]

        for reason in priority:
            if reason in reasons:
                return reason

        return reasons[0] if reasons else "unknown_error"

    def _find_text(self, item: ET.Element, tag_name: str) -> str:
        if tag_name.startswith("{") and "}" in tag_name:
            found = item.find(f".//{tag_name}")
            if found is not None and found.text:
                return self._clean_text(found.text)

            return ""

        try:
            found = item.find(f".//{tag_name}")
        except Exception:
            found = None
        if found is not None and found.text:
            return self._clean_text(found.text)

        try:
            found = item.find(f".//news:{tag_name}")
        except Exception:
            found = None
        if found is not None and found.text:
            return self._clean_text(found.text)

        for element in item.iter():
            local_tag = element.tag.split("}")[-1]
            if local_tag == tag_name and element.text:
                return self._clean_text(element.text)

        return ""

    def _parse_rank_widgets(self, raw_html: str) -> List[Dict[str, Any]]:
        results = []

        widget_pattern = re.compile(
            r'<div[^>]*class="[^"]*\brank\b[^"]*"[^>]*>(.*?)'
            r'<div[^>]*class="[^"]*section_title[^"]*"[^>]*>(.*?)</div>(.*?)'
            r'(?=<div[^>]*class="[^"]*\brank\b[^"]*"[^>]*>|$)',
            re.IGNORECASE | re.DOTALL,
        )
        list_pattern = re.compile(
            r'<li[^>]*class="[^"]*list_item[^"]*"[^>]*>(.*?)</li>',
            re.IGNORECASE | re.DOTALL,
        )
        rank_pattern = re.compile(
            r'<label[^>]*>(.*?)</label>',
            re.IGNORECASE | re.DOTALL,
        )
        item_link_pattern = re.compile(
            r'<h3[^>]*class="[^"]*hd_line[^"]*"[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )

        for match in widget_pattern.finditer(raw_html):
            section_html = match.group(3) if match else ""
            for item_html in list_pattern.findall(section_html):
                link = ""
                title = ""
                rank_text = ""
                rank_match = rank_pattern.search(item_html)
                if rank_match:
                    rank_text = self._clean_text(rank_match.group(1))

                link_match = item_link_pattern.search(item_html)
                if link_match:
                    link = self._clean_text(link_match.group(1), keep_space=False)
                    title = self._clean_text(link_match.group(2))

                if not title or not link:
                    continue

                results.append(
                    {
                        "title": title,
                        "link": link,
                        "rank": self._parse_rank(rank_text),
                    }
                )

        return results

    def _parse_breakingnews_articles(self, raw_html: str) -> List[Dict[str, str]]:
        block_pattern = re.compile(
            r'<li[^>]*class="[^"]*article_item[^"]*"[^>]*>(.*?)</li>',
            re.IGNORECASE | re.DOTALL,
        )
        link_pattern = re.compile(r'<a[^>]+href="([^"]+)"', re.IGNORECASE)
        title_pattern = re.compile(
            r'<h3[^>]*class="[^"]*headline[^"]*"[^>]*>(.*?)</h3>',
            re.IGNORECASE | re.DOTALL,
        )
        summary_pattern = re.compile(
            r'<p[^>]*class="[^"]*description[^"]*"[^>]*>(.*?)</p>',
            re.IGNORECASE | re.DOTALL,
        )
        date_pattern = re.compile(
            r'<div[^>]*class="[^"]*article_date[^"]*"[^>]*>(.*?)</div>',
            re.IGNORECASE | re.DOTALL,
        )
        reporter_pattern = re.compile(
            r'<div[^>]*class="[^"]*writer[^"]*"[^>]*>(.*?)</div>',
            re.IGNORECASE | re.DOTALL,
        )
        article_id_pattern = re.compile(
            r'<button[^>]*data-aid="(\d{19})"[^>]*>',
            re.IGNORECASE,
        )

        items = []
        for item_html in block_pattern.findall(raw_html):
            link_match = link_pattern.search(item_html)
            title_match = title_pattern.search(item_html)
            if not title_match:
                continue

            link = self._clean_text(link_match.group(1), keep_space=False) if link_match else ""
            title = self._clean_text(title_match.group(1))
            if not title or not link:
                continue

            summary = self._clean_text(
                summary_pattern.search(item_html).group(1)
                if summary_pattern.search(item_html)
                else ""
            )
            published_at = self._clean_text(
                date_pattern.search(item_html).group(1)
                if date_pattern.search(item_html)
                else ""
            )
            reporter = self._clean_text(
                reporter_pattern.search(item_html).group(1)
                if reporter_pattern.search(item_html)
                else ""
            )
            article_id_match = article_id_pattern.search(item_html)
            article_id = article_id_match.group(1) if article_id_match else ""

            items.append(
                {
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "published_at": published_at,
                    "reporter": reporter,
                    "article_id": article_id,
                }
            )

            if len(items) >= self.max_items:
                break

        return items

    def _build_trend_item(
        self,
        title: str,
        link: str,
        summary: str,
        published_at: str,
        reporter: str,
        article_id: str,
        category: str,
        query: str,
        index: int,
        source: Dict[str, Any],
        collection_method: str,
        rank: Optional[int],
    ) -> Dict[str, Any]:
        return {
            "keyword": title,
            "link": link,
            "summary": summary,
            "publisher": "머니투데이",
            "published_at": published_at,
            "query": query,
            "source_id": "moneytoday",
            "source_name": source.get("name", "머니투데이"),
            "source_type": source.get("type", "news"),
            "tier": int(source.get("tier", 1)),
            "weight": int(source.get("weight", 22)),
            "base_score": 118 - index,
            "trend_reason": f"머니투데이 수집({collection_method})",
            "collection_method": collection_method,
            "is_fallback": False,
            "collected_at": datetime.now().isoformat(),
            "article_id": article_id or self._extract_article_id(link),
            "category": category,
            "reporter": reporter,
            "rank_position": rank,
        }

    def _extract_category(self, url: str) -> str:
        try:
            parsed = urllib.parse.urlparse(url)
            segments = [segment for segment in parsed.path.split("/") if segment]
            if len(segments) >= 1:
                return segments[0]
        except Exception:
            pass

        return ""

    def _extract_article_id(self, url: str) -> str:
        match = re.search(r"/(\d{19})(?:/|$)", url)
        if match:
            return match.group(1)

        parsed = urllib.parse.urlparse(url)
        if "mtview.php" in parsed.path:
            query = urllib.parse.parse_qs(parsed.query or "")
            no = query.get("no", [""])
            return str(no[0]).strip()

        return ""

    def _parse_rank(self, value: str) -> Optional[int]:
        try:
            text = self._clean_text(value)
            if not text:
                return None
            return int(text)
        except Exception:
            return None

    def _format_kst_datetime(self, raw: str) -> str:
        if not raw:
            return ""

        parsed = self._parse_datetime(raw)
        if not parsed:
            return self._clean_text(raw)

        try:
            return parsed.strftime("%Y.%m.%d %H:%M")
        except Exception:
            return self._clean_text(raw)

    def _parse_datetime(self, raw: str) -> Optional[datetime]:
        text = self._clean_text(raw)
        if not text:
            return None

        for fmt in [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y.%m.%d %H:%M",
            "%Y-%m-%d",
        ]:
            try:
                return datetime.fromisoformat(text)
            except Exception:
                pass
            try:
                return datetime.strptime(text, fmt)
            except Exception:
                continue

        return None

    def _normalize_link(self, link: str) -> str:
        normalized = html.unescape(str(link)).strip()

        if not normalized:
            return ""

        if normalized.startswith("//"):
            return "https:" + normalized

        if normalized.startswith("/"):
            return urllib.parse.urljoin(f"https://{self.news_site_host}", normalized)

        if self.news_site_host in normalized:
            parsed = urllib.parse.urlparse(normalized)
            if "news.mt.co.kr" in parsed.netloc:
                return self._normalize_legacy_news_link(normalized)
            return normalized

        if normalized.startswith("http"):
            return normalized

        return urllib.parse.urljoin(f"https://{self.news_site_host}", normalized)

    def _normalize_legacy_news_link(self, link: str) -> str:
        parsed = urllib.parse.urlparse(link)
        if "mtview.php" not in parsed.path:
            return link

        query = urllib.parse.parse_qs(parsed.query or "")
        article_id = query.get("no", [""])[0] if isinstance(query, dict) else ""
        if article_id:
            return f"https://{self.news_site_host}/finance/0000/00/00/{article_id}"

        return link

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

    def _clean_text(self, text: Optional[str], keep_space: bool = True) -> str:
        if not text:
            return ""

        cleaned = re.sub(r"<.*?>", " ", str(text), flags=re.DOTALL)
        cleaned = html.unescape(cleaned)
        cleaned = cleaned.replace("\n", " ").replace("\t", " ").replace("\r", " ")
        if keep_space:
            cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()
