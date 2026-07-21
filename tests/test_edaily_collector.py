import json
import os
import unittest
from pathlib import Path
from unittest import mock
import socket
import urllib.request

from modules.source_intake.daily_collection_executor import execute_daily_shallow_collection
from modules.trend_collector.edaily_collector import EdailyCollector


SITEMAP_FIXTURE = """
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  <url>
    <loc>https://www.edaily.co.kr/News/Read?newsId=99000000000000001&amp;mediaCodeNo=257</loc>
    <news:news>
      <news:publication>
        <news:name>이데일리</news:name>
      </news:publication>
      <news:publication_date>2026-07-15T10:17:00+09:00</news:publication_date>
      <news:title>샘플 기사 제목</news:title>
    </news:news>
    <image:image>
      <image:loc>https://image.edaily.co.kr/images/content/sample.jpg</image:loc>
    </image:image>
  </url>
  <url>
    <loc>https://www.edaily.co.kr/News/Read?newsId=bad-newsid&amp;mediaCodeNo=257</loc>
    <news:news>
      <news:publication_date>2026-07-15T10:17:00+09:00</news:publication_date>
      <news:title>제목은 있지만 유효하지 않은 ID</news:title>
    </news:news>
  </url>
</urlset>
"""

MORELIST_FIXTURE = """
[
  {
    "NEWS_ID": "99000000000000002",
    "HEADLINE_HTML_DEL": "카테고리 기사 제목",
    "BODY_SHORT": "요약문",
    "Category1CodeName": "증권",
    "Category2CodeName": "증권뉴스",
    "Category3CodeName": "종목",
    "Journalist": "홍길동 기자",
    "JID": "sample",
    "ConfirmDateFormat01": "2026-07-15 오전 09:31:00",
    "IMG_B": "https://image.edaily.co.kr/images/content/stock.jpg",
    "READ_CNT": 0
  }
]
"""


class _Source:
    def __init__(self, source_id="edaily"):
        self.entry = {
            "source_id": source_id,
            "name": "이데일리",
            "type": "news_economy",
            "tier": 5,
            "weight": 40,
            "url": "https://www.edaily.co.kr/article/stock",
        }


class TestEdailyCollector(unittest.TestCase):
    def setUp(self):
        self.collector = EdailyCollector(timeout=2, max_items=3, config={})
        self.source = _Source().entry

    def test_prefers_sitemap_and_normalizes_fields(self):
        self.collector._fetch_url = lambda _url: SITEMAP_FIXTURE  # type: ignore[assignment]

        items = self.collector.collect(self.source)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["source"], "edaily")
        self.assertEqual(item["news_id"], "99000000000000001")
        self.assertEqual(item["title"], "샘플 기사 제목")
        self.assertEqual(item["list_type"], "latest")
        self.assertEqual(item["published_at"], "2026-07-15T10:17:00+09:00")
        self.assertEqual(
            item["url"],
            "https://www.edaily.co.kr/News/Read?newsId=99000000000000001&mediaCodeNo=257",
        )
        self.assertEqual(self.collector.last_status["collection_method"], "edaily_latest_sitemap")

    def test_fallback_to_category_json_when_sitemap_has_no_valid_items(self):
        def fake_fetch(url):
            if "latest-article.xml" in url:
                return "<urlset><url></url></urlset>"
            return MORELIST_FIXTURE

        self.collector._fetch_url = fake_fetch  # type: ignore[assignment]

        items = self.collector.collect(self.source)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["list_type"], "category")
        self.assertEqual(item["news_id"], "99000000000000002")
        self.assertEqual(item["category_path"], ["증권", "증권뉴스", "종목"])
        self.assertEqual(item["reporter"], "홍길동 기자")
        self.assertEqual(item["reporter_id"], "sample")
        self.assertNotIn("READ_CNT", item)
        self.assertNotIn("read_cnt", item)

    def test_cache_used_when_live_fails(self):
        cache_root = Path("storage/_tmp_edaily_cache")
        cache_root.mkdir(parents=True, exist_ok=True)
        self.collector.cache_path = cache_root / "edaily_cache.json"
        cache_payload = {
            "source": "edaily",
            "items": [
                {
                    "source": "edaily",
                    "news_id": "99000000000000099",
                    "url": "https://www.edaily.co.kr/News/Read?newsId=99000000000000099&mediaCodeNo=257",
                    "title": "캐시 기사",
                    "list_type": "latest",
                    "published_at": "2026-07-15T10:00:00+09:00",
                }
            ],
        }
        with open(self.collector.cache_path, "w", encoding="utf-8") as handle:
            json.dump(cache_payload, handle, ensure_ascii=False)

        self.collector._fetch_url = lambda _url: (_ for _ in ()).throw(Exception("network down"))  # type: ignore
        items = self.collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "캐시 기사")
        self.assertTrue(self.collector.last_status["used_cache"])
        self.assertEqual(self.collector.last_status["collection_method"], "edaily_cache")

        if cache_root.exists():
            for cache_file in cache_root.glob("*.json"):
                cache_file.unlink()
            if not any(cache_root.iterdir()):
                cache_root.rmdir()

    def test_combines_category_summary_rows_with_unique_sitemap_rows(self):
        def fake_fetch(url):
            if "MoreList" in url:
                return MORELIST_FIXTURE
            return SITEMAP_FIXTURE

        self.collector._fetch_url = fake_fetch  # type: ignore[assignment]

        items = self.collector.collect(self.source)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["news_id"], "99000000000000002")
        self.assertEqual(items[0]["summary"], "요약문")
        self.assertEqual(items[1]["news_id"], "99000000000000001")
        self.assertEqual(
            self.collector.last_status["collection_method"],
            "edaily_category_json_plus_sitemap",
        )


class TestEdailyExecutorWiring(unittest.TestCase):
    def setUp(self):
        class _ExecutorManager:
            def __init__(self):
                self.config = {"trend_sources": []}

            def _collect_naver_news(self, source):
                return []

            def _collect_nate_news_rank(self, source):
                return []

            def _collect_fmkorea(self, source):
                return []

            def _collect_bobaedream(self, source):
                return []

            def _collect_newsis(self, source):
                return []

            def _collect_theqoo(self, source):
                return []

            def _collect_daum_news(self, source):
                return []

        self.manager = _ExecutorManager()
        self.today = "2099-01-05"
        self.output_root = os.path.join("storage", "_tmp_edaily_executor")
        self._socket_connect_patch = mock.patch(
            "socket.create_connection",
            side_effect=OSError("network disabled in executor tests"),
        )
        self._socket_bind_patch = mock.patch(
            "socket.socket.connect",
            side_effect=OSError("network disabled in executor tests"),
        )
        self._urlopen_patch = mock.patch(
            "urllib.request.urlopen",
            side_effect=RuntimeError("network disabled in executor tests"),
        )
        self._socket_connect_patch.start()
        self._socket_bind_patch.start()
        self._urlopen_patch.start()

    def tearDown(self):
        self._urlopen_patch.stop()
        self._socket_bind_patch.stop()
        self._socket_connect_patch.stop()
        if os.path.exists(self.output_root):
            import shutil

            shutil.rmtree(self.output_root, ignore_errors=True)

    def test_executor_uses_edaily_collector_when_manager_lacks_method(self):
        called = []

        class FakeEdailyCollector:
            def __init__(self, *args, **kwargs):
                pass

            def collect(self, source):
                called.append(source["source_id"])
                return [
                    {
                        "source": "edaily",
                        "source_id": "edaily",
                        "news_id": "99000000000000003",
                        "url": "https://www.edaily.co.kr/News/Read?newsId=99000000000000003&mediaCodeNo=257",
                        "title": "실행기 연동 샘플",
                        "published_at": "2026-07-15T10:00:00+09:00",
                        "collected_at": "2026-07-15T10:00:00+09:00",
                        "list_type": "latest",
                    }
                ]

        plan = {
            "plan_status": "ok",
            "lanes": [
                {
                    "lane_id": "lane_edaily",
                    "shallow_profiles": ["edaily"],
                }
            ],
        }

        def fake_factory(source_entry, _config):
            return FakeEdailyCollector().collect(source_entry)

        with mock.patch.dict(
            "modules.source_intake.daily_collection_executor.DIRECT_COLLECTOR_FACTORIES",
            {"edaily": fake_factory},
            clear=False,
        ), mock.patch(
            "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
            return_value=plan,
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
                source_manager=self.manager,
                capability_map=None,
                allow_direct_collectors=True,
            )

        self.assertEqual(len(called), 1)
        self.assertEqual(called[0], "edaily")
        self.assertTrue(any(item["source_id"] == "edaily" for item in result["items"]))


if __name__ == "__main__":
    unittest.main()
