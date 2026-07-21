import json
import shutil
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from modules.trend_collector.ppomppu_collector import PpomppuCollector


FIXTURE_HTML = """
<table>
  <tr class="notice"><td><a class="title" href="/notice">공지</a></td></tr>
  <tr class="list-row" data-post-no="100" data-category="휴대폰" data-published-at="2026-07-15 10:00" data-views="1,234" data-comments="12" data-likes="31" data-dislikes="2">
    <td class="title"><a class="title" href="/zboard/view.php?id=ppomppu&amp;no=100">첫 번째 샘플</a></td>
  </tr>
  <tr class="list-row" data-post-no="101" data-category="자유" data-published-at="2026-07-15 10:01" data-views="88">
    <td class="title"><a class="title" href="/zboard/view.php?id=freeboard&amp;no=101">두 번째 샘플</a></td>
  </tr>
</table>
"""


DEDUP_FIXTURE_HTML = """
<table>
  <tr data-views="10"><td><a class="title" href="/zboard/view.php?id=a&amp;no=1">URL 중복</a></td></tr>
  <tr data-views="20"><td><a class="title" href="/zboard/view.php?id=a&amp;no=1">다른 제목</a></td></tr>
  <tr data-views="30"><td><a class="title" href="/zboard/view.php?id=a&amp;no=2">제목 중복</a></td></tr>
  <tr data-views="40"><td><a class="title" href="/zboard/view.php?id=a&amp;no=3">제목 중복</a></td></tr>
</table>
"""


class TestPpomppuCollector(unittest.TestCase):
    def setUp(self):
        self.tmp = Path("storage") / "_tmp_ppomppu_collector"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.tmp / "ppomppu_cache.json"
        self.source = {
            "source_id": "ppomppu",
            "name": "PPOMPPU",
            "url": "https://www.ppomppu.co.kr/hot.php",
            "type": "community",
            "tier": 3,
            "weight": 15,
        }

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _config(self, **overrides):
        config = {"cache_path": str(self.cache_path), "max_retries": 0}
        config.update(overrides)
        return config

    def test_parses_visible_fixture_fields_without_network(self):
        collector = PpomppuCollector(
            config=self._config(fixture_collection_enabled=True),
            fetcher=lambda url: (url, FIXTURE_HTML),
        )
        items = collector.collect(self.source)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["title"], "첫 번째 샘플")
        self.assertEqual(items[0]["views"], 1234)
        self.assertEqual(items[0]["comments"], 12)
        self.assertEqual(items[0]["likes"], 31)
        self.assertEqual(items[0]["dislikes"], 2)
        self.assertEqual(items[0]["rank_position"], 1)
        self.assertEqual(items[1]["comments"], None)
        self.assertEqual(collector.last_status["collection_method"], "ppomppu_fixture_html")

    def test_dedupes_url_then_normalized_title(self):
        collector = PpomppuCollector(
            config=self._config(fixture_collection_enabled=True),
            fetcher=lambda url: (url, DEDUP_FIXTURE_HTML),
        )
        items = collector.collect(self.source)

        self.assertEqual([item["title"] for item in items], ["URL 중복", "제목 중복"])
        self.assertEqual([item["rank_position"] for item in items], [1, 2])

    def test_default_activation_is_fail_closed(self):
        fetcher = mock.Mock(side_effect=AssertionError("network must not run"))
        collector = PpomppuCollector(
            config=self._config(),
            fetcher=fetcher,
        )
        items = collector.collect(self.source)

        self.assertEqual(items, [])
        fetcher.assert_not_called()
        self.assertEqual(
            collector.last_status["failed_reason"],
            PpomppuCollector.LIVE_REJECTION_REASON,
        )

    def test_valid_cache_is_used_after_injected_fixture_failure(self):
        payload = {
            "source": "ppomppu",
            "updated_at": datetime.now().isoformat(),
            "items": [
                {
                    "keyword": "캐시 샘플",
                    "title": "캐시 샘플",
                    "link": "https://www.ppomppu.co.kr/zboard/view.php?id=a&no=9",
                    "url": "https://www.ppomppu.co.kr/zboard/view.php?id=a&no=9",
                    "rank_position": 1,
                    "views": 9,
                }
            ],
        }
        with open(self.cache_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

        collector = PpomppuCollector(
            config=self._config(fixture_collection_enabled=True),
            fetcher=mock.Mock(side_effect=RuntimeError("fixture unavailable")),
        )
        items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertTrue(collector.last_status["used_cache"])
        self.assertEqual(items[0]["collection_method"], "ppomppu_cache")
        self.assertTrue(items[0]["is_fallback"])

    def test_malformed_fixture_records_parse_failure(self):
        collector = PpomppuCollector(
            config=self._config(fixture_collection_enabled=True),
            fetcher=lambda url: (url, "<html>no list</html>"),
        )
        items = collector.collect(self.source)

        self.assertEqual(items, [])
        self.assertEqual(collector.last_status["failed_reason"], "parse_failed")
        self.assertEqual(collector.last_status["service_diagnostic"]["status"], "fallback_used")

    def test_forbidden_body_identity_and_image_fields_are_absent(self):
        collector = PpomppuCollector(
            config=self._config(fixture_collection_enabled=True),
            fetcher=lambda url: (url, FIXTURE_HTML),
        )
        item = collector.collect(self.source)[0]
        forbidden = {
            "article_body",
            "comment_body",
            "image_url",
            "image_binary",
            "user_id",
            "nickname",
            "profile",
            "ip",
        }
        self.assertTrue(forbidden.isdisjoint(item))


if __name__ == "__main__":
    unittest.main()
