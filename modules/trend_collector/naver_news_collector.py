import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional


class NaverNewsCollector:
    def __init__(self, timeout: int = 8, max_items_per_query: int = 5):
        self.timeout = timeout
        self.max_items_per_query = max_items_per_query

    def collect(
        self,
        query_keywords: List[str],
        source: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        results = []

        for query in query_keywords:
            try:
                results.extend(self._collect_by_query(query=query, source=source))
            except Exception as error:
                print(f"Naver News Collect Failed: {query} / {error}")

        return self._dedupe(results)

    def _collect_by_query(
        self,
        query: str,
        source: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        rss_items = self._collect_from_rss(query=query, source=source)

        if rss_items:
            return rss_items

        return self._collect_from_search_result(query=query, source=source)

    def _collect_from_rss(
        self,
        query: str,
        source: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        encoded_query = urllib.parse.quote(query)
        url = f"https://search.naver.com/search.naver?where=rss&query={encoded_query}"
        raw_xml = self._fetch_url(url)

        root = ET.fromstring(raw_xml)
        items = root.findall(".//item")
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

    def _parse_search_result_articles(self, raw_html: str) -> List[Dict[str, str]]:
        articles = []
        pattern = (
            r'<a[^>]*class="[^"]*news_tit[^"]*"[^>]*'
            r'href="([^"]+)"[^>]*title="([^"]+)"[^>]*>'
        )
        matches = re.findall(pattern, raw_html, flags=re.IGNORECASE | re.DOTALL)

        for link, title in matches:
            clean_title = self._clean_text(title)

            if clean_title:
                articles.append(
                    {
                        "title": clean_title,
                        "link": html.unescape(link),
                        "summary": "",
                    }
                )

        if articles:
            return articles

        fallback_pattern = r'<a[^>]*class="[^"]*news_tit[^"]*"[^>]*>(.*?)</a>'
        fallback_matches = re.findall(
            fallback_pattern,
            raw_html,
            flags=re.IGNORECASE | re.DOTALL,
        )

        for title in fallback_matches:
            clean_title = self._clean_text(title)

            if clean_title:
                articles.append(
                    {
                        "title": clean_title,
                        "link": "",
                        "summary": "",
                    }
                )

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
        found = item.find(tag_name)

        if found is None or found.text is None:
            return ""

        return found.text

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
