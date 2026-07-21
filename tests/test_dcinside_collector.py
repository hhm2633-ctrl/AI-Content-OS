import json
import os
import shutil
import urllib.error
import unittest
from pathlib import Path
from datetime import datetime
from unittest import mock

from modules.trend_collector.dcinside_collector import DcinsideCollector


def dcinside_fixture_html() -> str:
    return """
<table class="gall_list">
  <tbody>
    <tr class="ub-content us-post" data-no="445680" data-type="icon_txt">
      <td class="gall_tit ub-word">
        <a href="/board/view/?id=dcbest&no=445680&page=1">첫번째</a>
      </td>
      <td class="gall_writer ub-writer" data-nick="" data-uid="" data-ip="x.y.z.w"></td>
      <td class="gall_date" title="2026-07-15 00:00:00">07.15</td>
      <td class="gall_count">12</td>
      <td class="gall_recommend">3</td>
    </tr>
    <tr class="ub-content us-post" data-no="445681" data-type="icon_txt">
      <td class="gall_tit ub-word">
        <a href="/board/view/?id=dcbest&no=445681&page=1">둘째</a>
      </td>
      <td class="gall_writer ub-writer" data-nick="" data-uid="" data-ip="x.y.z.w"></td>
      <td class="gall_date" title="2026-07-15 00:01:00">07.15</td>
      <td class="gall_count">8</td>
      <td class="gall_recommend">2</td>
    </tr>
    <tr class="ub-content" data-no="공지" data-type="icon_notice">
      <td class="gall_tit ub-word">
        <a href="/board/view/?id=dcbest&no=100">공지</a>
      </td>
      <td class="gall_writer ub-writer" data-nick="" data-uid="" data-ip="x.y.z.w"></td>
      <td class="gall_date" title="2026-07-15 00:02:00">07.15</td>
      <td class="gall_count">-</td>
      <td class="gall_recommend">-</td>
    </tr>
  </tbody>
</table>
"""


def dcinside_home_best_fixture_html() -> str:
    return """
<ul><li><a href="https://gall.dcinside.com/board/view/?id=dcbest&amp;no=445873"
class="main_log" section_code="realtime_best_p">
<div class="box besttxt"><p>홈 실시간 베스트</p><span class="num">[125]</span></div>
<div class="box best_info"><span class="name">유머</span><span class="time">19:55</span></div>
</a></li></ul>
"""


def write_cache(path: Path, items):
    payload = {
        "source": "dcinside",
        "updated_at": datetime.now().isoformat(),
        "items": items,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


class TestDcinsideCollector(unittest.TestCase):
    def setUp(self):
        self.tmp = Path("storage") / "_tmp_dcinside_collector"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.tmp / "dcinside_cache.json"
        self.source = {
            "source_id": "dcinside",
            "name": "디시인사이드",
            "type": "community",
            "tier": 1,
            "weight": 20,
            "board_id": "dcbest",
            "url": "https://gall.dcinside.com/board/lists/",
        }

    def _config(self, **overrides):
        config = {"cache_path": str(self.cache_path), "max_retries": 0}
        config.update(overrides)
        return config

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_collect_delegates_to_parser(self):
        board_calls = []

        def fake_parser(board_id, raw_html):
            board_calls.append((board_id, raw_html))
            return []

        collector = DcinsideCollector(
            config=self._config(
                allow_live_fetch=True,
                dcinside_live_url="https://gall.dcinside.com/board/lists/?id=dcbest",
            ),
            fetcher=lambda _url: (
                "https://gall.dcinside.com/board/lists/?id=dcbest",
                dcinside_fixture_html(),
            ),
            parser=fake_parser,
        )

        collector.collect(self.source)

        self.assertEqual(len(board_calls), 1)
        self.assertEqual(board_calls[0][0], "dcbest")
        self.assertIn("gall_tit", board_calls[0][1])

    def test_collect_maps_parser_output_to_expected_fields(self):
        collector = DcinsideCollector(
            config=self._config(
                allow_live_fetch=True,
                dcinside_live_url="https://gall.dcinside.com/board/lists/?id=dcbest",
            ),
            fetcher=lambda _url: (
                "https://gall.dcinside.com/board/lists/?id=dcbest",
                dcinside_fixture_html(),
            ),
        )

        items = collector.collect(self.source)

        self.assertEqual(len(items), 2)
        self.assertTrue(collector.last_status["success"])
        self.assertEqual(collector.last_status["collection_method"], "dcinside_board_parse")
        self.assertEqual(items[0]["title"], "첫번째")
        self.assertEqual(items[0]["link"], "https://gall.dcinside.com/board/view/?id=dcbest&no=445680&page=1")
        self.assertEqual(items[0]["published_at"], "2026-07-15 00:00:00")
        self.assertEqual(items[0]["category"], "dcbest")
        self.assertEqual(items[0]["rank_position"], 1)
        self.assertEqual(items[0]["views"], 12)
        self.assertEqual(items[0]["likes"], 3)

    def test_explicit_live_mode_uses_registered_public_homepage_surface(self):
        public_source = dict(self.source, url="https://www.dcinside.com/")
        public_source.pop("board_id")
        collector = DcinsideCollector(
            config=self._config(allow_live_fetch=True),
            fetcher=lambda url: (url, dcinside_home_best_fixture_html()),
        )

        items = collector.collect(public_source)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "홈 실시간 베스트")
        self.assertEqual(items[0]["comments"], 125)
        self.assertIsNone(items[0]["views"])
        self.assertIsNone(items[0]["likes"])
        self.assertEqual(collector.last_status["collection_method"], "dcinside_board_parse")

    def test_url_then_title_dedup_is_deterministic(self):
        source_rows = [
            {"title": "중복", "url": "https://gall.dcinside.com/board/view/?id=dcbest&no=1", "posted_at": "2026-07-15 00:00:01", "rank": 1},
            {"title": "다른 제목", "url": "https://gall.dcinside.com/board/view/?id=dcbest&no=1", "posted_at": "2026-07-15 00:00:02", "rank": 2},
            {"title": "타이틀 충돌", "url": "https://gall.dcinside.com/board/view/?id=dcbest&no=2", "posted_at": "2026-07-15 00:00:03", "rank": 3},
            {"title": "타이틀 충돌", "url": "https://gall.dcinside.com/board/view/?id=dcbest&no=3", "posted_at": "2026-07-15 00:00:04", "rank": 4},
        ]

        collector = DcinsideCollector(
            config=self._config(
                allow_live_fetch=True,
                dcinside_live_url="https://gall.dcinside.com/board/lists/?id=dcbest",
            ),
            fetcher=lambda _url: (
                "https://gall.dcinside.com/board/lists/?id=dcbest",
                dcinside_fixture_html(),
            ),
            parser=lambda board_id, raw_html: source_rows,
        )

        items = collector.collect(self.source)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["title"], "중복")
        self.assertEqual(items[0]["link"], "https://gall.dcinside.com/board/view/?id=dcbest&no=1")
        self.assertEqual(items[1]["title"], "타이틀 충돌")
        self.assertEqual(items[1]["rank_position"], 2)

    def test_forbidden_identity_and_body_fields_are_absent(self):
        collector = DcinsideCollector(
            config=self._config(
                allow_live_fetch=True,
                dcinside_live_url="https://gall.dcinside.com/board/lists/?id=dcbest",
            ),
            fetcher=lambda _url: (
                "https://gall.dcinside.com/board/lists/?id=dcbest",
                dcinside_fixture_html(),
            ),
        )

        items = collector.collect(self.source)
        item = items[0]

        forbidden_fields = {
            "article_body",
            "image_binary",
            "image_url_republication",
            "writer",
            "user_id",
            "profile",
            "post_no",
            "post_type",
            "origin_board_tag",
            "recommends",
        }
        self.assertTrue(forbidden_fields.isdisjoint(set(item.keys())))

    def test_live_activation_disabled_is_fail_closed(self):
        fetch_mock = mock.Mock(side_effect=RuntimeError("network should not run"))
        collector = DcinsideCollector(config=self._config(), fetcher=fetch_mock)
        items = collector.collect(self.source)

        self.assertEqual(items, [])
        self.assertEqual(collector.last_status["failed_reason"], DcinsideCollector.LIVE_REJECTION_REASON)
        self.assertEqual(collector.last_status["final_error_type"], DcinsideCollector.LIVE_REJECTION_REASON)
        self.assertEqual(collector.last_status["service_diagnostic"]["status"], "fallback_used")
        self.assertFalse(collector.last_status["success"])
        fetch_mock.assert_not_called()

    def test_valid_cache_is_used_when_live_parse_fails(self):
        cache_path = self.tmp / "dcinside_cache.json"
        write_cache(
            cache_path,
            [
                {
                    "title": "캐시 샘플",
                    "link": "https://gall.dcinside.com/board/view/?id=dcbest&no=500",
                    "published_at": "2026-07-15 07:00:00",
                    "category": "dcbest",
                    "rank_position": 2,
                }
            ],
        )

        collector = DcinsideCollector(
            config={
                "allow_live_fetch": True,
                "dcinside_live_url": "https://gall.dcinside.com/board/lists/?id=dcbest",
                "cache_path": str(cache_path),
                "max_retries": 0,
            },
            fetcher=mock.Mock(side_effect=urllib.error.URLError("offline")),
        )
        items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertTrue(collector.last_status["used_cache"])
        self.assertEqual(collector.last_status["collection_method"], "dcinside_cache")
        self.assertTrue(collector.last_status["success"])
        self.assertEqual(collector.last_status["service_diagnostic"]["status"], "fallback_used")
        self.assertEqual(items[0]["title"], "캐시 샘플")
        self.assertEqual(items[0]["is_fallback"], True)

    def test_malformed_fixture_records_parse_reason(self):
        collector = DcinsideCollector(
            config=self._config(
                allow_live_fetch=True,
                dcinside_live_url="https://gall.dcinside.com/board/lists/?id=dcbest",
            ),
            fetcher=lambda _url: (
                "https://gall.dcinside.com/board/lists/?id=dcbest",
                "<html><body>not dcinside</body></html>",
            ),
        )

        items = collector.collect(self.source)

        self.assertEqual(items, [])
        self.assertFalse(collector.last_status["success"])
        self.assertEqual(collector.last_status["collection_method"], "dcinside_no_data")
        self.assertEqual(collector.last_status["failed_reason"], "malformed_fixture")
        self.assertEqual(collector.last_status["service_diagnostic"]["status"], "fallback_used")

    def test_diagnostic_honesty_marks_network_cache_fallback(self):
        cache_path = self.tmp / "dcinside_cache_error.json"
        write_cache(
            cache_path,
            [
                {
                    "title": "캐시 진단 샘플",
                    "link": "https://gall.dcinside.com/board/view/?id=dcbest&no=600",
                    "published_at": "2026-07-15 07:30:00",
                    "category": "dcbest",
                    "rank_position": 3,
                }
            ],
        )

        collector = DcinsideCollector(
            config={
                "allow_live_fetch": True,
                "dcinside_live_url": "https://gall.dcinside.com/board/lists/?id=dcbest",
                "cache_path": str(cache_path),
                "max_retries": 0,
            },
            fetcher=mock.Mock(side_effect=urllib.error.URLError("offline")),
        )
        items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertEqual(collector.last_status["final_error_type"], "network_error")
        self.assertEqual(collector.last_status["fallback_reason"], "network_error")
        self.assertEqual(items[0]["is_fallback"], True)
        self.assertEqual(items[0]["collection_method"], "dcinside_cache")
