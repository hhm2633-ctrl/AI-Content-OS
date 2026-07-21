import json
import os
import shutil
import urllib.error
import uuid
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.source_intake.daily_collection_executor import execute_daily_shallow_collection
from modules.trend_collector.news1_collector import News1Collector


def _next_data_fixture() -> str:
    payload = {
        "props": {
            "pageProps": {
                "data": [
                    {
                        "id": 6228304,
                        "title": "내년 최저임금 1만700원…",
                        "url": "/society/6228304",
                        "section": "경제",
                        "pubdate": "2026-07-15 00:10:26",
                        "summary": "요약 텍스트",
                    },
                    {
                        "id": 6228305,
                        "title": "추가 이슈",
                        "url": "/society/6228305",
                        "section": "경제",
                        "pubdate": "2026-07-15 00:11:00",
                        "summary": "두번째 요약",
                    },
                ]
            }
        }
    }
    return (
        "<html><head><script id=\"__NEXT_DATA__\" type=\"application/json\">"
        f"{json.dumps(payload, ensure_ascii=False)}"
        "</script></head><body></body></html>"
    )


def _fallback_html_fixture() -> str:
    return (
        "<div class=\"row-bottom-border-2\"><div class=\"row\">"
        '<h2 class="n1-header-title-1-2"><a href="/society/111">백신 접종 일정 발표</a></h2>'
        '<span class="n1-header-desc-1">보건부가 핵심 일정을 발표했습니다.</span>'
        '<div class="entry-meta"><span>신문</span><span>보건부 기자</span></div>'
        "</div></div>"
    )


class TestNews1Collector(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.join("storage", f"_tmp_news1_{uuid.uuid4().hex}")
        os.makedirs(self.tmp, exist_ok=True)
        self.source = {
            "source_id": "news1",
            "name": "News1",
            "type": "news_wire",
            "url": "https://www.news1.kr",
            "tier": 1,
            "weight": 20,
        }

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_collect_uses_next_data_primary(self):
        collector = News1Collector()

        def fake_fetch(url):
            return ("https://www.news1.kr/latest", _next_data_fixture())

        collector._fetch_url = fake_fetch
        items = collector.collect(self.source)

        self.assertEqual(len(items), 2)
        self.assertTrue(collector.last_status["success"])
        self.assertEqual(items[0]["collection_method"], "news1_next_data")
        self.assertEqual(items[0]["title"], "내년 최저임금 1만700원…")
        self.assertEqual(items[0]["link"], "https://www.news1.kr/society/6228304")
        self.assertEqual(items[0]["category"], "경제")
        self.assertEqual(items[0]["rank_position"], 1)
        self.assertEqual(items[0]["publisher"], "뉴스1")
        self.assertEqual(items[0]["published_at"], "2026-07-15 00:10:26")

    def test_collect_falls_back_to_html_when_next_data_missing(self):
        collector = News1Collector()

        def fake_fetch(url):
            return ("https://www.news1.kr/latest", _fallback_html_fixture())

        collector._fetch_url = fake_fetch
        items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["collection_method"], "news1_html_fallback")
        self.assertEqual(items[0]["title"], "백신 접종 일정 발표")
        self.assertEqual(items[0]["link"], "https://www.news1.kr/society/111")
        self.assertEqual(items[0]["publisher"], "보건부 기자")

    def test_collect_uses_cache_if_live_parse_fails(self):
        collector = News1Collector()
        collector.cache_path = Path(self.tmp) / "news1_cache.json"
        with open(collector.cache_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "source": "news1",
                    "updated_at": "2026-07-15T00:10:00",
                    "items": [
                        {
                            "title": "캐시기사 제목",
                            "url": "/trend/1",
                            "category": "정치",
                            "rank_position": 1,
                            "publisher": "뉴스1",
                            "published_at": "2026-07-15 00:10:11",
                        }
                    ],
                },
                handle,
                ensure_ascii=False,
            )

        def fake_fetch(_url):
            raise urllib.error.URLError("network down")

        collector._fetch_url = fake_fetch
        items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertFalse(collector.last_status["success"])
        self.assertTrue(collector.last_status["used_cache"])
        self.assertEqual(items[0]["collection_method"], "news1_cache")
        self.assertEqual(items[0]["title"], "캐시기사 제목")

    def test_daily_executor_routes_news1_to_news1_collector(self):
        with patch(
            "modules.source_intake.daily_collection_executor.News1Collector",
        ) as MockCollector:
            mock_instance = MockCollector.return_value
            mock_instance.collect.return_value = [
                {
                    "keyword": "운영 테스트",
                    "source_id": "news1",
                    "source_name": "News1",
                    "source_type": "news_wire",
                    "tier": 1,
                    "weight": 20,
                    "base_score": 90,
                    "collection_method": "news1_next_data",
                    "is_fallback": False,
                    "title": "운영 테스트",
                    "link": "https://www.news1.kr/latest/1",
                    "summary": "",
                }
            ]

            result = execute_daily_shallow_collection(
                account_profiles=["news_society_economy"],
                today="2099-01-10",
                output_root=os.path.join(self.tmp, "daily"),
            )

            self.assertEqual(result["status"], "completed")
            self.assertTrue(any(source["source_id"] == "news1" for source in result["source_results"]))
            news1_entry = next(
                source
                for source in result["source_results"]
                if source["source_id"] == "news1"
            )
            self.assertEqual(news1_entry["source_id"], "news1")
