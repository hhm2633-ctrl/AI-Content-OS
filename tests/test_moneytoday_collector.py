import unittest
from unittest import mock
from urllib.error import URLError

from modules.source_intake.daily_collection_executor import execute_daily_shallow_collection
from modules.trend_collector.moneytoday_collector import MoneyTodayCollector
from modules.trend_collector.trend_source_manager import TrendSourceManager


SITEMAP_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
  <url>
    <loc>https://www.mt.co.kr/economy/2026/07/15/2026071500000000001</loc>
    <lastmod>2026-07-15T09:12:00+09:00</lastmod>
    <news:news>
      <news:publication_date>2026-07-15T09:12:00+09:00</news:publication_date>
      <news:title>샘플 시장 브리핑</news:title>
    </news:news>
  </url>
</urlset>
"""
EMPTY_SITEMAP_FIXTURE = "<urlset xmlns:news=\"http://www.google.com/schemas/sitemap-news/0.9\"></urlset>"

HOMEPAGE_RANK_FIXTURE = """
<div class="rank">
  <div class="section_title">증권 랭킹뉴스</div>
  <ul class="list_area">
    <li class="list_item">
      <figure class="rank_img"><label>1</label><img src="/thumb/news1.jpg"/></figure>
      <h3 class="hd_line"><a href="/stock/2026/07/15/2026071500000000002">샘플 랭킹 기사 1</a></h3>
    </li>
  </ul>
</div>
"""
EMPTY_RANKING_FIXTURE = """
<div class="rank">
  <div class="section_title">증권 랭킹뉴스</div>
  <ul class="list_area"></ul>
</div>
"""

BREAKINGNEWS_FIXTURE = """
<ul class="list_wrap">
  <li class="article_item">
    <a href="/economy/2026/07/15/2026071500000000003">샘플 최신 헤드라인</a>
    <h3 class="headline"><a href="/economy/2026/07/15/2026071500000000003">샘플 최신 헤드라인</a></h3>
    <p class="description">요약 본문 샘플입니다.</p>
    <div class="article_date">2026.07.15 10:03</div>
    <div class="writer">홍길동 기자</div>
    <button data-aid="2026071500000000003"></button>
    <figure class="thumb"><img src="/thumb/2026/07/15/3.jpg"/></figure>
  </li>
</ul>
"""


class TestMoneyTodayCollector(unittest.TestCase):
    def setUp(self):
        self.source = {
            "name": "머니투데이",
            "type": "news",
            "tier": 1,
            "weight": 22,
        }

    def test_collect_from_sitemap_parses_fixture_contract_fields(self):
        collector = MoneyTodayCollector(max_items=2)

        with mock.patch.object(collector, "_fetch_url", return_value=SITEMAP_FIXTURE):
            items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertEqual(
            items[0]["keyword"],
            "샘플 시장 브리핑",
        )
        self.assertEqual(
            items[0]["link"],
            "https://www.mt.co.kr/economy/2026/07/15/2026071500000000001",
        )
        self.assertEqual(items[0]["article_id"], "2026071500000000001")
        self.assertEqual(items[0]["category"], "economy")
        self.assertEqual(items[0]["publisher"], "머니투데이")
        self.assertEqual(items[0]["published_at"], "2026.07.15 09:12")
        self.assertEqual(items[0]["collection_method"], "moneytoday_sitemap")
        self.assertIsNone(items[0]["rank_position"])

    def test_parsing_and_fallback_to_breakingnews_when_upstream_sources_empty(self):
        collector = MoneyTodayCollector(max_items=3)
        fetch_calls = []
        fixtures = [EMPTY_SITEMAP_FIXTURE, EMPTY_RANKING_FIXTURE, BREAKINGNEWS_FIXTURE]

        def fake_fetch(url):
            fetch_calls.append(url)
            return fixtures[len(fetch_calls) - 1]

        with mock.patch.object(collector, "_fetch_url", side_effect=fake_fetch):
            items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["collection_method"], "moneytoday_breakingnews")
        self.assertEqual(items[0]["published_at"], "2026.07.15 10:03")
        self.assertEqual(items[0]["reporter"], "홍길동 기자")
        self.assertEqual(items[0]["summary"], "요약 본문 샘플입니다.")
        self.assertEqual(len(fetch_calls), 3)

    def test_parse_rank_and_breakingnews_normalization(self):
        collector = MoneyTodayCollector()

        rank_items = collector._parse_rank_widgets(HOMEPAGE_RANK_FIXTURE)
        self.assertEqual(len(rank_items), 1)
        self.assertEqual(rank_items[0]["title"], "샘플 랭킹 기사 1")
        self.assertEqual(rank_items[0]["rank"], 1)
        self.assertEqual(
            rank_items[0]["link"],
            "/stock/2026/07/15/2026071500000000002",
        )

        article_items = collector._parse_breakingnews_articles(BREAKINGNEWS_FIXTURE)
        self.assertEqual(len(article_items), 1)
        self.assertEqual(article_items[0]["title"], "샘플 최신 헤드라인")
        self.assertEqual(article_items[0]["article_id"], "2026071500000000003")
        self.assertEqual(article_items[0]["published_at"], "2026.07.15 10:03")
        self.assertEqual(article_items[0]["link"], "/economy/2026/07/15/2026071500000000003")

    def test_diagnostics_fail_closed_when_all_collection_methods_error(self):
        collector = MoneyTodayCollector()

        with mock.patch.object(collector, "_fetch_url", side_effect=URLError("offline")):
            items = collector.collect(self.source)

        self.assertEqual(items, [])
        self.assertEqual(collector.last_status["success"], False)
        self.assertEqual(collector.last_status["failed_reason"], "network_error")
        self.assertEqual(collector.last_status["final_error_type"], "network_error")
        self.assertEqual(
            collector.last_status["service_diagnostic"]["status"],
            "fallback_used",
        )
        self.assertIn("sitemap: network_error", collector.last_status["error_message"])

    def test_trend_source_manager_compatibility_no_live_network(self):
        source_config = {
            "sources": [
                {
                    "source_id": "moneytoday",
                    "name": "머니투데이",
                    "enabled": True,
                    "tier": 1,
                    "weight": 22,
                    "type": "news",
                }
            ],
            "trend_sources": [
                "시장 동향",
            ],
        }

        with mock.patch(
            "modules.trend_collector.trend_source_manager.TrendSourceManager._load_source_config",
            return_value=source_config,
        ):
            manager = TrendSourceManager(
                {
                    "trend_collector": {
                        "retry_enabled": False,
                        "max_retries": 0,
                    },
                    "trend_sources": ["시장 동향"],
                }
            )

            with mock.patch.object(
                manager.retry_policy,
                "run_collect",
                return_value=(
                    [
                        {
                            "keyword": "머니투데이 호환성 테스트",
                            "link": "https://www.mt.co.kr/economy/2026/07/15/2026071500000000004",
                            "source_id": "moneytoday",
                            "source_name": "머니투데이",
                            "source_type": "news",
                            "base_score": 100,
                        }
                    ],
                    {
                        "attempted": True,
                        "success": True,
                        "count": 1,
                        "error_message": "",
                        "failed_reason": "",
                        "fallback_reason": "",
                        "collection_method": "moneytoday_cache",
                        "used_cache": False,
                        "cache_path": "storage/cache/moneytoday_cache.json",
                        "service_diagnostic": {
                            "service": "moneytoday",
                            "status": "ok",
                            "error_type": "",
                            "safe_message": "",
                            "api_key_present": None,
                        },
                    },
                ),
            ):
                items = manager.collect_from_enabled_sources()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source_id"], "moneytoday")
        self.assertEqual(manager.last_collection_summary["moneytoday"]["count"], 1)
        self.assertEqual(manager.last_collection_summary["moneytoday"]["success"], True)


if __name__ == "__main__":
    unittest.main()
