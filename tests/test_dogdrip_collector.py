import json
import shutil
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from modules.trend_collector.dogdrip_collector import DogdripCollector


FIXTURE_HTML = """
<table>
  <tr class="notice"><td><a class="title" href="/notice">공지</a></td></tr>
  <tr data-category="개드립" data-published-at="2026-07-15 08:30" data-views="7,842" data-comments="55" data-likes="230">
    <td class="title"><a class="link-reset" href="/dogdrip/501">첫 번째 샘플</a></td>
  </tr>
  <tr data-category="유머" data-published-at="2026-07-15 08:40" data-views="120">
    <td class="title"><a class="link-reset" href="/dogdrip/502">두 번째 샘플</a></td>
  </tr>
</table>
"""


DEDUP_FIXTURE_HTML = """
<table>
  <tr data-views="10"><td><a class="link-reset" href="/dogdrip/1">URL 중복</a></td></tr>
  <tr data-views="20"><td><a class="link-reset" href="/dogdrip/1">다른 제목</a></td></tr>
  <tr data-views="30"><td><a class="link-reset" href="/dogdrip/2">제목 중복</a></td></tr>
  <tr data-views="40"><td><a class="link-reset" href="/dogdrip/3">제목 중복</a></td></tr>
</table>
"""


class TestDogdripCollector(unittest.TestCase):
    def setUp(self):
        self.tmp = Path("storage") / "_tmp_dogdrip_collector"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.tmp / "dogdrip_cache.json"
        self.source = {
            "source_id": "dogdrip",
            "name": "Dogdrip",
            "url": "https://www.dogdrip.net/dogdrip",
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
        collector = DogdripCollector(
            config=self._config(fixture_collection_enabled=True),
            fetcher=lambda url: (url, FIXTURE_HTML),
        )
        items = collector.collect(self.source)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["title"], "첫 번째 샘플")
        self.assertEqual(items[0]["link"], "https://www.dogdrip.net/dogdrip/501")
        self.assertEqual(items[0]["views"], 7842)
        self.assertEqual(items[0]["comments"], 55)
        self.assertEqual(items[0]["likes"], 230)
        self.assertEqual(items[0]["category"], "개드립")
        self.assertEqual(items[0]["published_at"], "2026-07-15 08:30")
        self.assertEqual(items[0]["rank_position"], 1)
        self.assertIsNone(items[1]["comments"])
        self.assertIsNone(items[1]["likes"])
        self.assertEqual(
            collector.last_status["collection_method"], "dogdrip_fixture_html"
        )
        self.assertTrue(collector.last_status["success"])

    def test_dedupes_url_then_normalized_title(self):
        collector = DogdripCollector(
            config=self._config(fixture_collection_enabled=True),
            fetcher=lambda url: (url, DEDUP_FIXTURE_HTML),
        )
        items = collector.collect(self.source)

        self.assertEqual([item["title"] for item in items], ["URL 중복", "제목 중복"])
        self.assertEqual([item["rank_position"] for item in items], [1, 2])

    def test_default_activation_is_fail_closed(self):
        fetcher = mock.Mock(side_effect=AssertionError("network must not run"))
        collector = DogdripCollector(
            config=self._config(),
            fetcher=fetcher,
        )
        items = collector.collect(self.source)

        self.assertEqual(items, [])
        fetcher.assert_not_called()
        self.assertEqual(
            collector.last_status["failed_reason"],
            DogdripCollector.LIVE_REJECTION_REASON,
        )

    def test_fixture_gate_without_fetcher_never_collects(self):
        collector = DogdripCollector(
            config=self._config(fixture_collection_enabled=True),
        )
        items = collector.collect(self.source)

        self.assertEqual(items, [])
        self.assertEqual(
            collector.last_status["failed_reason"],
            DogdripCollector.LIVE_REJECTION_REASON,
        )

    def test_valid_cache_is_used_after_injected_fixture_failure(self):
        payload = {
            "source": "dogdrip",
            "updated_at": datetime.now().isoformat(),
            "items": [
                {
                    "keyword": "캐시 샘플",
                    "title": "캐시 샘플",
                    "link": "https://www.dogdrip.net/dogdrip/9",
                    "url": "https://www.dogdrip.net/dogdrip/9",
                    "rank_position": 1,
                    "views": 9,
                }
            ],
        }
        with open(self.cache_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

        collector = DogdripCollector(
            config=self._config(fixture_collection_enabled=True),
            fetcher=mock.Mock(side_effect=RuntimeError("fixture unavailable")),
        )
        items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertTrue(collector.last_status["used_cache"])
        self.assertEqual(items[0]["collection_method"], "dogdrip_cache")
        self.assertTrue(items[0]["is_fallback"])

    def test_malformed_fixture_records_parse_failure(self):
        collector = DogdripCollector(
            config=self._config(fixture_collection_enabled=True),
            fetcher=lambda url: (url, "<html>no list</html>"),
        )
        items = collector.collect(self.source)

        self.assertEqual(items, [])
        self.assertEqual(collector.last_status["failed_reason"], "parse_failed")
        self.assertEqual(
            collector.last_status["service_diagnostic"]["status"], "fallback_used"
        )

    def test_forbidden_body_identity_and_image_fields_are_absent(self):
        collector = DogdripCollector(
            config=self._config(fixture_collection_enabled=True),
            fetcher=lambda url: (url, FIXTURE_HTML),
        )
        item = collector.collect(self.source)[0]
        forbidden = {
            "article_body",
            "body",
            "comment_body",
            "image_url",
            "image_binary",
            "user_id",
            "nickname",
            "writer",
            "profile",
            "ip",
        }
        self.assertTrue(forbidden.isdisjoint(item))

    def test_no_default_or_operational_cache_leakage(self):
        default_path = DogdripCollector.DEFAULT_CACHE_PATH
        existed_before = default_path.exists()
        mtime_before = default_path.stat().st_mtime if existed_before else None

        collector = DogdripCollector(
            config=self._config(fixture_collection_enabled=True),
            fetcher=lambda url: (url, FIXTURE_HTML),
        )
        items = collector.collect(self.source)

        self.assertTrue(items)
        self.assertTrue(self.cache_path.exists())
        self.assertEqual(default_path.exists(), existed_before)
        if existed_before:
            self.assertEqual(default_path.stat().st_mtime, mtime_before)


if __name__ == "__main__":
    unittest.main()

