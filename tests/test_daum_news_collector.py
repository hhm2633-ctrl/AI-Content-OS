import json
import unittest
import urllib.error
from pathlib import Path

from modules.trend_collector.daum_news_collector import DaumNewsCollector


def _fixture_html() -> str:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "external_workclaude"
        / "source_collector_work_orders"
        / "2026-07-14"
        / "DAUM_NEWS_FIXTURE_CONTRACT.json"
    )
    with open(fixture_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    return payload["sanitized_minimal_html_fixture"]


class TestDaumNewsCollector(unittest.TestCase):
    def setUp(self):
        self.collector = DaumNewsCollector()
        self.source = {
            "source_id": "daum_news",
            "name": "Daum News",
            "type": "news",
            "url": "https://news.daum.net/society",
        }

    def test_collects_only_observed_fields_from_fixture(self):
        def fake_fetch(_url):
            return (
                "https://news.daum.net/society",
                _fixture_html(),
            )

        self.collector._fetch_url = fake_fetch
        items = self.collector.collect(self.source)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["headline"], "예시 헤드라인 텍스트")
        self.assertEqual(item["link"], "https://v.daum.net/v/20260715040308416")
        self.assertEqual(item["category"], "society")
        self.assertEqual(item["rank_position"], 1)
        self.assertEqual(item["publisher"], "예시언론사")
        self.assertEqual(item["published_at"], "22분 전")
        self.assertEqual(item["source_id"], "daum_news")

    def test_rejects_redirected_category_page(self):
        def fake_fetch(_url):
            return ("https://news.daum.net/", "<html><body>homepage</body></html>")

        self.collector._fetch_url = fake_fetch
        items = self.collector.collect(self.source)

        self.assertEqual(items, [])
        self.assertEqual(self.collector.last_status["failed_reason"], "redirected_category_url")
        self.assertFalse(self.collector.last_status["success"])

    def test_rejects_stale_or_invalid_category_url_without_fetch(self):
        called = []

        def fake_fetch(_url):
            called.append(_url)
            return ("https://news.daum.net/ranking/popular", "<html></html>")

        self.collector._fetch_url = fake_fetch
        source = {
            "source_id": "daum_news",
            "name": "Daum News",
            "type": "news",
            "url": "https://news.daum.net/ranking/popular",
        }
        items = self.collector.collect(source)

        self.assertEqual(items, [])
        self.assertEqual(self.collector.last_status["failed_reason"], "no_valid_category_urls")
        self.assertEqual(len(called), 0)

    def test_network_error_does_not_crash_and_returns_diagnostic(self):
        def fake_fetch(_url):
            raise urllib.error.URLError("network down")

        self.collector._fetch_url = fake_fetch
        items = self.collector.collect(self.source)

        self.assertEqual(items, [])
        self.assertFalse(self.collector.last_status["success"])
        self.assertIn("network", self.collector.last_status["failed_reason"])


if __name__ == "__main__":
    unittest.main()
