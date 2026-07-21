import html
import json
import re
import urllib.parse
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
import xml.etree.ElementTree as ET


class NaverNewsParserV2:
    """Fixture-first Naver News HTML/XML parser.

    This module is parser-only and intentionally does not fetch URLs.
    """

    def parse_query(
        self,
        query: str,
        source: Dict[str, Any],
        rss_payload: str,
        search_payload: str,
    ) -> List[Dict[str, Any]]:
        rss_items = self._collect_from_rss_xml(query=query, source=source, raw_xml=rss_payload)
        if rss_items:
            return rss_items

        return self._collect_from_search_result(query=query, source=source, raw_html=search_payload)

    def parse_search_payload(
        self,
        query: str,
        source: Dict[str, Any],
        raw_html: str,
    ) -> List[Dict[str, Any]]:
        return self._collect_from_search_result(query=query, source=source, raw_html=raw_html)

    def parse_ranking_payload(
        self,
        source: Dict[str, Any],
        raw_html: str,
    ) -> List[Dict[str, Any]]:
        return self._parse_ranking_payload(source=source, raw_html=raw_html)

    def parse_section_payload(
        self,
        section_id: str,
        source: Dict[str, Any],
        raw_html: str,
    ) -> List[Dict[str, Any]]:
        return self._parse_section_payload(
            section_id=section_id,
            source=source,
            raw_html=raw_html,
        )

    def decode_euc_kr_html(self, raw_bytes: bytes) -> str:
        return self._decode_html_bytes(raw_bytes=raw_bytes, charset="euc-kr")

    def looks_like_html(self, text: str) -> bool:
        stripped = text.lstrip().lower()
        return stripped.startswith("<!doctype html") or stripped.startswith("<html")

    def build_failure(self, reason: str, message: str = "") -> Dict[str, str]:
        return {"failed_reason": reason, "message": message}

    def _collect_from_rss_xml(
        self,
        query: str,
        source: Dict[str, Any],
        raw_xml: str,
    ) -> List[Dict[str, Any]]:
        if self.looks_like_html(raw_xml):
            return []

        try:
            root = ET.fromstring(raw_xml)
        except ET.ParseError:
            return []

        items = []

        for index, item in enumerate(root.findall(".//item"), start=1):
            if len(items) >= 5:
                break

            title = self._clean_text(self._find_xml_text(item, "title"))
            if not title:
                continue

            link = self._clean_text(
                self._find_xml_text(item, "originallink")
                or self._find_xml_text(item, "link")
            )
            summary = self._clean_text(self._find_xml_text(item, "description"))
            published_at = self._clean_text(self._find_xml_text(item, "pubDate"))

            items.append(
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

        return items

    def _collect_from_search_result(
        self,
        query: str,
        source: Dict[str, Any],
        raw_html: str,
    ) -> List[Dict[str, Any]]:
        articles = self._parse_search_result_articles(raw_html=raw_html)
        trends = []

        for index, article in enumerate(articles[:5], start=1):
            if not article.get("title"):
                continue

            trends.append(
                self._build_trend_item(
                    query=query,
                    title=article.get("title", ""),
                    link=article.get("link", ""),
                    summary=article.get("summary", ""),
                    published_at=article.get("published_at", ""),
                    index=index,
                    source=source,
                    collection_method="naver_news_html",
                    category=article.get("category"),
                    rank=article.get("rank"),
                )
            )

        return trends

    def _parse_search_result_articles(self, raw_html: str) -> List[Dict[str, str]]:
        articles = []

        title_blocks = re.finditer(
            (
                r'<a[^>]*nocr="1"[^>]*data-heatmap-target="\.tit"[^>]*'
                r'href="([^"]+)"[^>]*>(.*?)</a>'
                r'(.*?)'
                r'<a[^>]*data-heatmap-target="\.body"[^>]*>(.*?)</a>'
            ),
            raw_html,
            flags=re.IGNORECASE | re.DOTALL,
        )

        for match in title_blocks:
            link = self._clean_text(match.group(1))
            headline_html = match.group(2)
            tail_html = match.group(3)
            summary_html = match.group(4)

            title = self._extract_headline_ko(headline_html)
            if not title:
                continue

            summary = self._clean_text(summary_html)
            profile_block = self._extract_profile_block(title_match_end=match.end(2), source_html=tail_html)
            publisher = profile_block.get("publisher", "")
            published_at = profile_block.get("published_at", "")
            if not publisher:
                publisher = self._extract_publisher(link)

            articles.append(
                {
                    "title": title,
                    "link": html.unescape(link),
                    "summary": summary,
                    "published_at": published_at,
                    "publisher": publisher,
                }
            )

        return articles

    def _extract_profile_block(self, title_match_end: int, source_html: str) -> Dict[str, str]:
        profile = re.search(
            (
                r'<div[^>]*class="[^"]*sds-comps-profile-info-title[^"]*"[^>]*>'
                r'(.*?)</div>'
            ),
            source_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not profile:
            return {}

        body = profile.group(1)
        publisher = self._clean_text(
            re.search(
                r'<span[^>]*class="[^"]*sds-comps-text-type-body2[^"]*"[^>]*>(.*?)</span>',
                body,
                flags=re.IGNORECASE | re.DOTALL,
            ).group(1)
            if re.search(
                r'<span[^>]*class="[^"]*sds-comps-text-type-body2[^"]*"[^>]*>(.*?)</span>',
                body,
                flags=re.IGNORECASE | re.DOTALL,
            )
            else ""
        )

        published_at = self._clean_text(
            re.search(
                r'([0-9]+[시간분초]?[ ]?전|어제[가-힣]?\s*[0-9: ]*)',
                body,
            ).group(1)
            if re.search(r'([0-9]+[시간분초]?[ ]?전|어제[가-힣]?\s*[0-9: ]*)', body)
            else ""
        )
        return {"publisher": publisher, "published_at": published_at}

    def _extract_headline_ko(self, html_snippet: str) -> str:
        return self._clean_text(
            re.sub(
                r'<[^>]+>',
                "",
                html_snippet or "",
            )
        )

    def _parse_ranking_payload(
        self,
        source: Dict[str, Any],
        raw_html: str,
    ) -> List[Dict[str, Any]]:
        items = []
        press_section_pattern = re.compile(
            r'<strong[^>]*class="[^"]*rankingnews_name[^"]*"[^>]*>(.*?)</strong>(.*?)(?=<strong[^>]*class="[^"]*rankingnews_name[^"]*"[^>]*>|$)',
            flags=re.IGNORECASE | re.DOTALL,
        )
        title_pattern = re.compile(
            r'<a[^>]*class="[^"]*list_title[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            flags=re.IGNORECASE | re.DOTALL,
        )
        rank_pattern = re.compile(
            r'<em[^>]*class="[^"]*list_ranking_num[^"]*"[^>]*>(\d+)<span[^>]*>위</span></em>',
            flags=re.IGNORECASE | re.DOTALL,
        )
        press_pattern = re.compile(
            r'<strong[^>]*class="[^"]*rankingnews_name[^"]*"[^>]*>(.*?)</strong>',
            flags=re.IGNORECASE | re.DOTALL,
        )

        for section_idx, section_html in enumerate(
            re.finditer(press_section_pattern, raw_html),
            start=1,
        ):
            press_name = self._clean_text(section_html.group(1)) or "Unknown"
            block_html = section_html.group(2)
            titles = []
            for match in title_pattern.finditer(block_html):
                titles.append(
                    {
                        "pos": match.start(),
                        "link": self._clean_text(match.group(1)),
                        "title": self._clean_text(match.group(2)),
                    }
                )
            ranks = []
            for match in rank_pattern.finditer(block_html):
                ranks.append({"pos": match.start(), "rank": self._safe_int(match.group(1), default=None)})
            pair_count = min(len(titles), len(ranks))

            for index in range(pair_count):
                title = titles[index].get("title")
                link = titles[index].get("link")
                rank = ranks[index].get("rank")
                if not title or not link or rank is None:
                    continue
                items.append(
                    {
                        "keyword": title,
                        "link": self._coerce_https(link),
                        "publisher": press_name,
                        "published_at": "",
                        "category": "",
                        "rank": rank,
                        "query": source.get("keyword", ""),
                        "source_id": source.get("source_id", "naver_news"),
                        "source_name": source.get("name", "Naver News"),
                        "source_type": source.get("type", "news"),
                        "tier": int(source.get("tier", 1)),
                        "weight": int(source.get("weight", 30)),
                        "base_score": 120 - len(items),
                        "trend_reason": f"Naver News ranking: {source.get('source_id', 'naver_news')}",
                        "collection_method": "naver_news_ranking",
                        "is_fallback": False,
                        "collected_at": datetime.now().isoformat(),
                    }
                )

        return items

    def _parse_section_payload(
        self,
        section_id: str,
        source: Dict[str, Any],
        raw_html: str,
    ) -> List[Dict[str, Any]]:
        item_pattern = re.compile(
            r'<div[^>]*class="[^"]*sa_item[^"]*"[^>]*>.*?'
            r'<a[^>]*class="[^"]*sa_text_title[^"]*"[^>]*href="([^"]+)"[^>]*'
            r'data-nlog-params="([^"]+)"[^>]*>.*?'
            r'<strong[^>]*class="[^"]*sa_text_strong[^"]*"[^>]*>(.*?)</strong>.*?'
            r'<span[^>]*class="[^"]*sa_text_press[^"]*"[^>]*>(.*?)</span>.*?'
            r'<span[^>]*class="[^"]*sa_text_datetime[^"]*"[^>]*><b>(.*?)</b></span>',
            flags=re.IGNORECASE | re.DOTALL,
        )

        items = []

        for match in item_pattern.finditer(raw_html):
            link = self._clean_text(match.group(1))
            nlog_raw = match.group(2)
            title = self._clean_text(match.group(3))
            publisher = self._clean_text(match.group(4))
            published_at = self._clean_text(match.group(5))

            nlog_json = self._safe_loads(nlog_raw)
            actual_section_id = self._safe_text(nlog_json.get("section1_id"), default=section_id)
            rank = self._safe_int(nlog_json.get("rank"), default=None)
            if not title or not link or rank is None:
                continue

            items.append(
                {
                    "keyword": title,
                    "link": self._coerce_https(link),
                    "publisher": publisher,
                    "published_at": published_at,
                    "category": actual_section_id,
                    "rank": rank,
                    "query": source.get("keyword", ""),
                    "source_id": source.get("source_id", "naver_news"),
                    "source_name": source.get("name", "Naver News"),
                    "source_type": source.get("type", "news"),
                    "tier": int(source.get("tier", 1)),
                    "weight": int(source.get("weight", 30)),
                    "base_score": 120 - len(items),
                    "trend_reason": f"Naver News section: {actual_section_id}",
                    "collection_method": "naver_news_section",
                    "is_fallback": False,
                    "collected_at": datetime.now().isoformat(),
                }
            )

        return items

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
        category: Optional[str] = None,
        rank: Optional[int] = None,
    ) -> Dict[str, Any]:
        item = {
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
        if category is not None:
            item["category"] = category
        if rank is not None:
            item["rank"] = rank
        if summary:
            item["summary"] = summary
        return item

    def _extract_publisher(self, link: str) -> str:
        if not link:
            return ""
        domain = urllib.parse.urlparse(link).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain

    def _find_xml_text(self, item: ET.Element, tag_name: str) -> str:
        found = item.find(tag_name)
        if found is None or found.text is None:
            return ""
        return found.text

    def _clean_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", "", str(text))
        text = html.unescape(text)
        text = text.replace("\n", " ").replace("\t", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _safe_text(self, value: Any, default: str = "") -> str:
        if value is None:
            return default
        return str(value)

    def _safe_int(self, value: Any, default: Optional[int] = 0) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _safe_loads(self, raw: str) -> Dict[str, Any]:
        if not raw:
            return {}
        try:
            return json.loads(raw.replace("&quot;", '"'))
        except Exception:
            return {}

    def _coerce_https(self, url: str) -> str:
        if url.startswith("//"):
            return f"https:{url}"
        return url

    def _decode_html_bytes(self, raw_bytes: bytes, charset: str = "utf-8") -> str:
        try:
            return raw_bytes.decode(charset, errors="strict")
        except Exception:
            return raw_bytes.decode("utf-8", errors="ignore")
