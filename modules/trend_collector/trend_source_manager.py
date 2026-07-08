import json
import re
import html
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List


class TrendSourceManager:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.source_config = self._load_source_config()

    def _load_source_config(self) -> Dict[str, Any]:
        config_path = Path("config/trend_sources.json")

        if not config_path.exists():
            return self._fallback_source_config()

        try:
            with open(config_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return self._fallback_source_config()

    def _fallback_source_config(self) -> Dict[str, Any]:
        return {
            "sources": [
                {
                    "source_id": "naver_news",
                    "name": "네이버 뉴스",
                    "enabled": True,
                    "tier": 1,
                    "weight": 30,
                    "type": "news"
                },
                {
                    "source_id": "manual",
                    "name": "Manual Fallback",
                    "enabled": True,
                    "tier": 99,
                    "weight": 5,
                    "type": "manual"
                }
            ]
        }

    def get_enabled_sources(self) -> List[Dict[str, Any]]:
        sources = self.source_config.get("sources", [])
        enabled_sources = []

        for source in sources:
            if isinstance(source, dict) and source.get("enabled", False):
                enabled_sources.append(source)

        enabled_sources.sort(
            key=lambda item: (
                int(item.get("tier", 99)),
                -int(item.get("weight", 0))
            )
        )

        return enabled_sources

    def collect_from_enabled_sources(self) -> List[Dict[str, Any]]:
        enabled_sources = self.get_enabled_sources()
        collected = []

        for source in enabled_sources:
            source_id = source.get("source_id", "unknown")

            if source_id == "naver_news":
                collected.extend(self._collect_naver_news(source))
                continue

            if source_id == "manual":
                collected.extend(self.build_manual_trends())
                continue

            collected.extend(self._placeholder_collect(source))

        if not collected:
            collected = self.build_manual_trends()

        return collected

    def _collect_naver_news(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        print("Naver News Collect Started")

        query_keywords = self.config.get("naver_news_keywords", [])

        if not query_keywords:
            query_keywords = [
                "AI 자동화",
                "부업",
                "콘텐츠 자동화",
                "인스타그램 수익화",
                "스마트스토어"
            ]

        results = []

        for query in query_keywords:
            try:
                results.extend(self._fetch_naver_news_by_query(query, source))
            except Exception as error:
                print(f"Naver News Collect Failed: {query} / {error}")

        if not results:
            print("Naver News Empty. Manual fallback will be used.")

        print("Naver News Collect Finished")
        return results

    def _fetch_naver_news_by_query(self, query: str, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        encoded_query = urllib.parse.quote(query)
        url = f"https://search.naver.com/search.naver?where=news&query={encoded_query}&sort=1"

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with urllib.request.urlopen(request, timeout=8) as response:
            raw_html = response.read().decode("utf-8", errors="ignore")

        titles = self._parse_naver_news_titles(raw_html)
        trends = []

        for index, title in enumerate(titles[:5], start=1):
            trends.append({
                "keyword": title,
                "source_id": source.get("source_id", "naver_news"),
                "source_name": source.get("name", "네이버 뉴스"),
                "source_type": source.get("type", "news"),
                "tier": int(source.get("tier", 1)),
                "weight": int(source.get("weight", 30)),
                "base_score": 110 - index,
                "trend_reason": f"네이버 뉴스 검색어: {query}"
            })

        return trends

    def _parse_naver_news_titles(self, raw_html: str) -> List[str]:
        titles = []

        patterns = [
            r'<a[^>]*class="[^"]*news_tit[^"]*"[^>]*title="([^"]+)"',
            r'<a[^>]*class="[^"]*news_tit[^"]*"[^>]*>(.*?)</a>'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, raw_html, flags=re.IGNORECASE | re.DOTALL)

            for match in matches:
                clean_title = self._clean_text(match)

                if clean_title and clean_title not in titles:
                    titles.append(clean_title)

        return titles

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"<.*?>", "", text)
        text = html.unescape(text)
        text = text.replace("\n", " ").replace("\t", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def build_manual_trends(self) -> List[Dict[str, Any]]:
        manual_keywords = self.config.get("trend_sources", [])

        if not manual_keywords:
            manual_keywords = [
                "AI 자동화",
                "인스타 카드뉴스",
                "부업 자동화",
                "콘텐츠 자동화",
                "스마트스토어 자동화",
                "AI 이미지 생성",
                "블로그 자동화",
                "쇼츠 자동화"
            ]

        trends = []

        for index, keyword in enumerate(manual_keywords, start=1):
            trends.append({
                "keyword": keyword,
                "source_id": "manual",
                "source_name": "Manual Fallback",
                "source_type": "manual",
                "tier": 99,
                "weight": 5,
                "base_score": 100 - index,
                "trend_reason": "settings.json fallback keyword"
            })

        return trends

    def _placeholder_collect(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        source_id = source.get("source_id", "unknown")
        source_name = source.get("name", source_id)
        source_type = source.get("type", "unknown")
        tier = int(source.get("tier", 99))
        weight = int(source.get("weight", 0))

        keyword_map = {
            "nate_pann": ["요즘 사람들 부업 고민", "직장인 퇴사 준비", "생활비 부담"],
            "bobaedream": ["자영업 현실", "물가 부담", "온라인 판매 부업"],
            "fmkorea": ["AI 밈 콘텐츠", "인스타 알고리즘", "쇼츠 수익화"],
            "dcinside": ["AI 그림 자동화", "블로그 자동화", "콘텐츠 반복 작업"],
            "ppomppu": ["절약 부업", "생활비 줄이기", "쇼핑 트렌드"],
            "google_trends": ["AI 콘텐츠", "부업 추천", "인스타 수익화"],
            "youtube": ["AI 쇼츠 만들기", "무자본 부업", "카드뉴스 만들기"],
            "reddit": ["AI automation tools", "content workflow", "side hustle automation"],
            "x": ["AI trend", "creator economy", "automation workflow"]
        }

        keywords = keyword_map.get(source_id, [])
        trends = []

        for index, keyword in enumerate(keywords, start=1):
            trends.append({
                "keyword": keyword,
                "source_id": source_id,
                "source_name": source_name,
                "source_type": source_type,
                "tier": tier,
                "weight": weight,
                "base_score": 100 - index,
                "trend_reason": f"{source_name} placeholder trend"
            })

        return trends