import json
import os
import unittest
from pathlib import Path
from unittest import mock

from modules.source_intake.daily_collection_executor import execute_daily_shallow_collection
from modules.trend_collector.hankyung_economy_collector import HankyungEconomyCollector


SITEMAP_FIXTURE = """
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
  <url>
    <loc>https://www.hankyung.com/article/2026071556827</loc>
    <news:news>
      <news:publication>
        <news:name>한국경제</news:name>
      </news:publication>
      <news:publication_date>2026.07.15 08:00</news:publication_date>
      <news:title>샘플 경제 기사 제목 1</news:title>
    </news:news>
  </url>
  <url>
    <loc>https://www.hankyung.com/article/bad-id</loc>
    <news:news>
      <news:publication_date>2026.07.15 08:01</news:publication_date>
      <news:title>잘못된 기사 ID</news:title>
    </news:news>
  </url>
</urlset>
"""

ECONOMY_FIXTURE = """
<div class=\"news-list-wrap\">
  <ul class=\"news-list\">
    <li>
      <div class=\"news-item\">
        <h2 class=\"news-tit\"><a href=\"/article/2026071556838\">샘플 경제 기사 제목 2</a></h2>
        <p class=\"txt-date\">2026.07.15 09:01</p>
        <span class=\"depth3\"><a href=\"/economy/economic-policy\">경제정책</a></span>
        <figure class=\"thumb\"><img src=\"//img.hankyung.com/photo/202607/XX.12345678.3.jpg\"/></figure>
      </div>
    </li>
  </ul>
</div>
"""

RANKING_FIXTURE = """
<div class=\"ranking-wrap\">
  <div class=\"ranking-panel\">
    <ul class=\"ranking-news-list\">
      <li>
        <em class=\"rank txt-num\">1</em>
        <div class=\"ranking-range\"><strong class=\"txt-num\">1~10</strong></div>
        <div class=\"news-item\">
          <h2 class=\"news-tit\"><a href=\"/article/2026071556849\">샘플 랭킹 기사 제목</a></h2>
          <p class=\"txt-date\">2026.07.14 14:00</p>
        </div>
      </li>
    </ul>
  </div>
</div>
"""

ALLNEWS_FIXTURE = """
<ul class=\"allnews-list\">
  <li data-aid=\"2026071556852\">
    <div class=\"news-item\">
      <h2 class=\"news-tit\"><a href=\"/article/2026071556852\">샘플 전체뉴스 기사</a></h2>
      <p class=\"txt-date\">2026.07.15 10:02</p>
      <div class=\"thumb\"><img src=\"https://img.hankyung.com/photo/202607/XX.87654321.3.jpg\"/></div>
    </div>
  </li>
</ul>
"""


class _Source:
    def __init__(self, source_id: str = "hankyung_economy"):
        self.entry = {
            "source_id": source_id,
            "name": "한국경제",
            "type": "news_economy",
            "tier": 5,
            "weight": 30,
            "url": "https://www.hankyung.com/economy",
        }


class TestHankyungEconomyCollector(unittest.TestCase):
    def setUp(self):
        self.collector = HankyungEconomyCollector(timeout=2, max_items=3)
        self.source = _Source().entry
        self.default_cache = Path("storage/cache/hankyung_economy_cache.json")
        if self.default_cache.exists():
            self.default_cache.unlink()

    def test_prefers_sitemap_and_normalizes_fields(self):
        self.collector._fetch_url = lambda _url: SITEMAP_FIXTURE  # type: ignore[assignment]
        items = self.collector.collect(self.source)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["source"], "hankyung_economy")
        self.assertEqual(item["article_id"], "2026071556827")
        self.assertEqual(item["title"], "샘플 경제 기사 제목 1")
        self.assertEqual(item["url"], "https://www.hankyung.com/article/2026071556827")
        self.assertEqual(item["publisher"], "hankyung")
        self.assertEqual(item["collection_method"], "hankyung_economy_latest_sitemap")
        self.assertFalse(item["fallback_used"])

    def test_fallback_to_economy_and_all_news_and_does_not_fabricate_rank(self):
        def fake_fetch(url):
            if url.endswith("/sitemap/latest-article.xml"):
                return "<urlset></urlset>"
            if url.endswith("/economy"):
                return ECONOMY_FIXTURE
            if url.endswith("/all-news"):
                return ALLNEWS_FIXTURE
            return ""

        self.collector._fetch_url = fake_fetch  # type: ignore[assignment]
        items = self.collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["rank"], None)
        self.assertEqual(items[0]["source"], "hankyung_economy")
        self.assertEqual(items[0]["collection_method"], "hankyung_economy_economy_list")

    def test_cache_used_when_live_is_blocked(self):
        cache_root = Path("storage/_tmp_hankyung_economy_cache")
        cache_root.mkdir(parents=True, exist_ok=True)
        cache_path = cache_root / "hankyung_economy_cache.json"
        cache_payload = {
            "source": "hankyung_economy",
            "items": [
                {
                    "source": "hankyung_economy",
                    "article_id": "2026071556999",
                    "title": "캐시 기사",
                    "url": "https://www.hankyung.com/article/2026071556999",
                    "published_at": "2026.07.15 10:30",
                    "published_at_iso": "2026-07-15T10:30:00+09:00",
                    "rank": None,
                    "publisher": "hankyung",
                    "fallback_used": False,
                }
            ],
        }
        with open(cache_path, "w", encoding="utf-8") as handle:
            json.dump(cache_payload, handle, ensure_ascii=False)

        self.collector.cache_path = cache_path
        self.collector._fetch_url = lambda _url: (_ for _ in ()).throw(Exception("network down"))  # type: ignore
        items = self.collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertTrue(self.collector.last_status["used_cache"])
        self.assertEqual(self.collector.last_status["collection_method"], "hankyung_economy_cache")
        self.assertEqual(items[0]["title"], "캐시 기사")
        self.assertTrue(items[0]["fallback_used"])

        if cache_root.exists():
            for cache_file in cache_root.glob("*.json"):
                cache_file.unlink()
            if not any(cache_root.iterdir()):
                cache_root.rmdir()
        if self.default_cache.exists():
            self.default_cache.unlink()


class TestHankyungEconomyExecutorWiring(unittest.TestCase):
    def setUp(self):
        class _ExecutorManager:
            def __init__(self):
                self.config = {"trend_sources": []}

        self.manager = _ExecutorManager()
        self.today = "2099-01-06"
        self.output_root = os.path.join("storage", "_tmp_hankyung_economy_executor")

    def tearDown(self):
        if os.path.exists(self.output_root):
            import shutil

            shutil.rmtree(self.output_root, ignore_errors=True)

    def test_executor_uses_hankyung_economy_collector_when_manager_lacks_method(self):
        called = []

        class FakeHankyungEconomyCollector:
            def __init__(self, *args, **kwargs):
                pass

            def collect(self, source):
                called.append(source["source_id"])
                return [
                    {
                        "source": "hankyung_economy",
                        "source_id": "hankyung_economy",
                        "article_id": "2026071556850",
                        "url": "https://www.hankyung.com/article/2026071556850",
                        "title": "실행기 연동 샘플",
                        "published_at": "2026.07.15 08:10",
                        "collected_at": "2026-07-15T10:00:00+09:00",
                        "published_at_iso": "2026-07-15T08:10:00+09:00",
                        "fallback_used": False,
                    }
                ]

        with mock.patch(
            "modules.source_intake.daily_collection_executor.HankyungEconomyCollector",
            FakeHankyungEconomyCollector,
        ):
            result = execute_daily_shallow_collection(
                account_profiles=["news_society_economy"],
                today=self.today,
                output_root=self.output_root,
                source_manager=self.manager,
                capability_map=None,
                allow_direct_collectors=True,
            )

        self.assertTrue(called)
        self.assertEqual(called[0], "hankyung_economy")
        self.assertTrue(any(item["source_id"] == "hankyung_economy" for item in result["items"]))


if __name__ == "__main__":
    unittest.main()
