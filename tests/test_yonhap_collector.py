import json
import os
import shutil
import unittest
from pathlib import Path
from datetime import datetime
from urllib.error import URLError
from unittest import mock

from modules.trend_collector.yonhap_collector import YonhapCollector


def yonhap_fixture_html() -> str:
    payload = {
        "items": [
            {
                "title": "연합뉴스 샘플 제목 1",
                "url": "/society/202607150001",
                "published_at": "2026-07-15 09:00:00",
                "category": "사회",
            },
            {
                "headline": "연합뉴스 샘플 제목 2",
                "link": "/economy/202607150002",
                "publish_time": "2026-07-15 09:01:00",
                "category": "경제",
                "rank_position": 1,
            },
        ]
    }
    return (
        "<html><head><script id=\"__NEXT_DATA__\">"
        f"{json.dumps(payload, ensure_ascii=False)}"
        "</script></head><body></body></html>"
    )


def yonhap_dedupe_fixture_html() -> str:
    payload = {
        "items": [
            {"title": "중복 제목", "url": "/duplicate/1", "published_at": "2026-07-15 10:00:00", "category": "사회"},
            {"title": "중복 제목", "url": "/duplicate/1", "published_at": "2026-07-15 10:01:00", "category": "사회"},
            {"title": "제목 A", "url": "/unique/a", "published_at": "2026-07-15 10:02:00", "category": "사회"},
            {"title": "타이틀 충돌", "url": "/title/first", "published_at": "2026-07-15 10:03:00", "category": "사회"},
            {"title": "타이틀 충돌", "url": "/title/second", "published_at": "2026-07-15 10:04:00", "category": "사회"},
        ]
    }
    return (
        "<html><head><script id=\"__NEXT_DATA__\">"
        f"{json.dumps(payload, ensure_ascii=False)}"
        "</script></head><body></body></html>"
    )


def forbidden_fields_fixture_html() -> str:
    payload = {
        "items": [
            {
                "title": "금지 필드 테스트",
                "url": "/forbidden/1",
                "published_at": "2026-07-15 11:00:00",
                "category": "정치",
            }
        ]
    }
    return (
        "<html><head><script id=\"__NEXT_DATA__\">"
        f"{json.dumps(payload, ensure_ascii=False)}"
        "</script></head><body></body></html>"
    )


def malformed_fixture_html() -> str:
    return "<html><body><div>not json</div></body></html>"


def yonhap_public_home_fixture_html() -> str:
    return """
    <a href="https://www.yna.co.kr/view/AKR20260715000100001?section=politics/all">
      대통령 국무회의 주요 발언 공개
    </a>
    <a href="https://www.yna.co.kr/view/AKR20260715000200002?section=economy/all">
      국내 증시 주요 지표 상승 마감
    </a>
    """


def write_cache(path: Path, items):
    payload = {
        "source": "yonhap",
        "updated_at": datetime.now().isoformat(),
        "items": items,
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


class TestYonhapCollector(unittest.TestCase):
    def setUp(self):
        self.tmp = Path("storage") / "_tmp_yonhap_collector"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.tmp / "yonhap_cache.json"
        self.source = {
            "source_id": "yonhap",
            "name": "연합뉴스",
            "type": "news_wire",
            "tier": 1,
            "weight": 20,
            "url": "https://www.yna.co.kr/",
        }

    def _config(self, **overrides):
        config = {"cache_path": str(self.cache_path)}
        config.update(overrides)
        return config

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_collect_parses_fixture_fields_with_rank_and_category(self):
        collector = YonhapCollector(
            config=self._config(
                allow_live_fetch=True,
                yonhap_live_url="https://www.yna.co.kr/news",
            ),
            fetcher=lambda _url: ("https://www.yna.co.kr/news", yonhap_fixture_html()),
        )

        items = collector.collect(self.source)

        self.assertEqual(len(items), 2)
        self.assertTrue(collector.last_status["success"])
        self.assertEqual(collector.last_status["collection_method"], "yonhap_live_parse")
        self.assertEqual(items[0]["title"], "연합뉴스 샘플 제목 1")
        self.assertEqual(items[0]["link"], "https://www.yna.co.kr/society/202607150001")
        self.assertEqual(items[0]["published_at"], "2026-07-15 09:00:00")
        self.assertEqual(items[0]["category"], "사회")
        self.assertEqual(items[0]["rank_position"], 1)
        self.assertEqual(items[1]["rank_position"], 2)
        self.assertEqual(items[0]["publisher"], "연합뉴스")
        self.assertEqual(items[0]["collection_method"], "yonhap_live_parse")

    def test_dedupes_by_url_then_title_deterministically(self):
        collector = YonhapCollector(
            config=self._config(
                allow_live_fetch=True,
                yonhap_live_url="https://www.yna.co.kr/news",
            ),
            fetcher=lambda _url: ("https://www.yna.co.kr/news", yonhap_dedupe_fixture_html()),
        )

        items = collector.collect(self.source)

        self.assertEqual(len(items), 3)
        links = [item["link"] for item in items]
        titles = [item["title"] for item in items]
        self.assertEqual(links[0], "https://www.yna.co.kr/duplicate/1")
        self.assertEqual(links[1], "https://www.yna.co.kr/unique/a")
        self.assertEqual(titles[2], "타이틀 충돌")
        self.assertEqual(items[0]["rank_position"], 1)
        self.assertEqual(items[1]["rank_position"], 2)
        self.assertEqual(items[2]["rank_position"], 3)

    def test_public_homepage_visible_links_are_parsed_without_body_collection(self):
        collector = YonhapCollector(
            config=self._config(
                allow_live_fetch=True,
                yonhap_live_url="https://www.yna.co.kr/",
            ),
            fetcher=lambda _url: ("https://www.yna.co.kr/", yonhap_public_home_fixture_html()),
        )

        items = collector.collect(self.source)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["category"], "politics")
        self.assertEqual(items[1]["category"], "economy")
        self.assertNotIn("article_body", items[0])

    def test_forbidden_fields_are_absent(self):
        collector = YonhapCollector(
            config=self._config(
                allow_live_fetch=True,
                yonhap_live_url="https://www.yna.co.kr/news",
            ),
            fetcher=lambda _url: ("https://www.yna.co.kr/news", forbidden_fields_fixture_html()),
        )

        items = collector.collect(self.source)
        item = items[0]

        forbidden = {
            "article_body",
            "image_binary",
            "image_url_republication",
            "comments",
            "user_id",
            "profile",
            "private_api_payload",
        }
        self.assertTrue(forbidden.isdisjoint(set(item.keys())))

    def test_live_activation_disabled_results_in_explicit_fail_closed_status(self):
        fetch_mock = mock.Mock(side_effect=RuntimeError("network should not run"))
        collector = YonhapCollector(config=self._config(), fetcher=fetch_mock)
        items = collector.collect(self.source)

        self.assertEqual(items, [])
        self.assertFalse(collector.last_status["success"])
        self.assertEqual(collector.last_status["failed_reason"], YonhapCollector.LIVE_REJECTION_REASON)
        self.assertEqual(collector.last_status["final_error_type"], YonhapCollector.LIVE_REJECTION_REASON)
        self.assertEqual(collector.last_status["service_diagnostic"]["status"], "fallback_used")
        fetch_mock.assert_not_called()

    def test_valid_cache_is_used_when_live_parse_fails(self):
        cache_path = self.tmp / "yonhap_cache.json"
        write_cache(
            cache_path,
            [
                {
                    "title": "캐시 샘플",
                    "link": "/cache/1",
                    "published_at": "2026-07-15 08:00:00",
                    "category": "정치",
                    "rank_position": 2,
                },
            ],
        )

        collector = YonhapCollector(
            config={
                "allow_live_fetch": True,
                "yonhap_live_url": "https://www.yna.co.kr/news",
                "cache_path": str(cache_path),
                "max_retries": 0,
            },
            fetcher=mock.Mock(side_effect=URLError("offline")),
        )

        items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertTrue(collector.last_status["used_cache"])
        self.assertEqual(collector.last_status["collection_method"], "yonhap_cache")
        self.assertTrue(collector.last_status["success"])
        self.assertEqual(collector.last_status["service_diagnostic"]["status"], "fallback_used")
        self.assertEqual(items[0]["title"], "캐시 샘플")

    def test_malformed_fixture_returns_no_data_and_records_parse_reason(self):
        collector = YonhapCollector(
            config=self._config(
                allow_live_fetch=True,
                yonhap_live_url="https://www.yna.co.kr/news",
            ),
            fetcher=lambda _url: ("https://www.yna.co.kr/news", malformed_fixture_html()),
        )

        items = collector.collect(self.source)

        self.assertEqual(items, [])
        self.assertFalse(collector.last_status["success"])
        self.assertEqual(collector.last_status["collection_method"], "yonhap_no_data")
        self.assertEqual(collector.last_status["failed_reason"], "malformed_fixture")
        self.assertEqual(collector.last_status["service_diagnostic"]["status"], "fallback_used")

    def test_diagnostic_honesty_marks_partial_cache_fallback_when_allowed(self):
        cache_path = self.tmp / "yonhap_cache_honesty.json"
        write_cache(
            cache_path,
            [
                {
                    "title": "캐시 진단 샘플",
                    "link": "/cache/honesty",
                    "published_at": "2026-07-15 07:00:00",
                    "category": "정치",
                    "rank_position": 3,
                }
            ],
        )

        collector = YonhapCollector(
            config={
                "allow_live_fetch": True,
                "yonhap_live_url": "https://www.yna.co.kr/news",
                "cache_path": str(cache_path),
            },
            fetcher=mock.Mock(side_effect=URLError("offline")),
        )
        items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertEqual(collector.last_status["final_error_type"], "network_error")
        self.assertEqual(collector.last_status["fallback_reason"], "network_error")
        self.assertEqual(items[0]["is_fallback"], True)
        self.assertEqual(items[0]["collection_method"], "yonhap_cache")
