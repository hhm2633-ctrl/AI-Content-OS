import json
import os
import shutil
import unittest
import urllib.error
from unittest import mock
import socket
import urllib.request

from modules.source_intake.daily_collection_executor import execute_daily_shallow_collection
from modules.trend_collector.theqoo_collector import TheQooCollector


HOT_LIST_FIXTURE = """
<table class="theqoo_board_table">
  <tbody class="hide_notice">
    <tr class="notice">
      <td class="no">999999</td>
      <td class="cate"><span>공지</span></td>
      <td class="title"><a href="/hot/9990000001">공지 제목</a></td>
      <td class="time">09:00</td>
      <td class="m_no">1,000</td>
    </tr>
    <tr>
      <td class="no">157952</td>
      <td class="cate"><span>이슈</span></td>
      <td class="title">
        <a href="/hot/4279889037?type=list">(펌) 유자녀 돌싱은 재혼하면 안 되겠어요</a>
        <i class="fas fa-images"></i>
        <a href="/hot/4279889037#4279889037_comment" class="replyNum">66</a>
      </td>
      <td class="time">09:52</td>
      <td class="m_no">4,745</td>
    </tr>
    <tr>
      <td class="no">157951</td>
      <td class="cate"><span>유머</span></td>
      <td class="title">
        <a href="/hot/4279889038">(펌) 답변 없는 글</a>
      </td>
      <td class="time">07.15</td>
      <td class="m_no">88</td>
    </tr>
  </tbody>
</table>
"""


class TestTheQooCollector(unittest.TestCase):
    def setUp(self):
        self.source = {
            "source_id": "theqoo",
            "name": "TheQoo",
            "url": "https://theqoo.net/hot",
            "type": "community",
            "tier": 5,
            "weight": 20,
        }

    def test_parsees_non_notice_rows_and_verified_fields_only(self):
        collector = TheQooCollector(config={"live_collection_enabled": True})
        collector._parse_page_index = lambda _url: 1  # type: ignore
        collector._fetch_url = lambda _url: ("https://theqoo.net/hot", HOT_LIST_FIXTURE)  # type: ignore

        items = collector.collect(self.source)

        self.assertEqual(len(items), 2)
        self.assertEqual(collector.last_status["success"], True)

        first = items[0]
        self.assertEqual(first["document_srl"], "4279889037")
        self.assertEqual(first["board_post_no"], 157952)
        self.assertEqual(first["title"], "(펌) 유자녀 돌싱은 재혼하면 안 되겠어요")
        self.assertEqual(first["url"], "https://theqoo.net/hot/4279889037")
        self.assertEqual(first["board"], "hot")
        self.assertEqual(first["category"], "이슈")
        self.assertEqual(first["rank"], 1)
        self.assertEqual(first["time_text"], "09:52")
        self.assertIsNotNone(first["published_at"])
        self.assertEqual(first["views"], 4745)
        self.assertEqual(first["comment_count"], 66)
        self.assertIsNone(first["recommend_count"])
        self.assertTrue(first["has_images"])

        second = items[1]
        self.assertEqual(second["document_srl"], "4279889038")
        self.assertEqual(second["comment_count"], 0)
        self.assertEqual(second["rank"], 2)
        self.assertEqual(second["time_text"], "07.15")
        self.assertEqual(second["views"], 88)
        self.assertIsNone(second["recommend_count"])

    def test_cache_used_when_live_failed(self):
        cache_dir = os.path.join("storage", "_tmp_theqoo_cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, "theqoo_cache.json")
        try:
            cache_payload = {
                "source": "theqoo",
                "items": [
                    {
                        "document_srl": "4200000001",
                        "board_post_no": 150001,
                        "title": "캐시 샘플",
                        "url": "https://theqoo.net/hot/4200000001",
                        "board": "hot",
                        "category": "이슈",
                        "rank": 1,
                        "time_text": "09:00",
                        "views": 1200,
                        "comment_count": 11,
                        "recommend_count": None,
                        "has_images": False,
                    }
                ],
            }
            with open(cache_path, "w", encoding="utf-8") as handle:
                json.dump(cache_payload, handle, ensure_ascii=False)

            collector = TheQooCollector(config={"live_collection_enabled": True})
            collector.cache_path = __import__("pathlib").Path(cache_path)  # type: ignore
            collector._fetch_url = lambda _url: (_ for _ in ()).throw(
                urllib.error.URLError("network down")
            )  # type: ignore

            items = collector.collect(self.source)
            self.assertEqual(len(items), 1)
            self.assertTrue(collector.last_status["used_cache"])
            self.assertEqual(items[0]["source_id"], "theqoo")
            self.assertEqual(items[0]["collection_method"], "theqoo_hot_cache")
            self.assertEqual(items[0]["recommend_count"], None)
        finally:
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir, ignore_errors=True)


class TestTheQooExecutorWiring(unittest.TestCase):
    def setUp(self):
        self.today = "2099-01-21"
        self.output_root = os.path.join("storage", "_tmp_theqoo_executor")
        self.called = []
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

        from modules.trend_collector.trend_source_manager import TrendSourceManager

        class _ExecutorManager(TrendSourceManager):
            def __init__(self):
                self.config = {}

            def _collect_naver_news(self, source):
                return []

            def _collect_nate_pann(self, source):
                return []

            def _collect_fmkorea(self, source):
                return []

            def _collect_bobaedream(self, source):
                return []

            def _collect_newsis(self, source):
                return []

        self.manager = _ExecutorManager()

    def tearDown(self):
        self._urlopen_patch.stop()
        self._socket_bind_patch.stop()
        self._socket_connect_patch.stop()
        if os.path.exists(self.output_root):
            shutil.rmtree(self.output_root, ignore_errors=True)

    def test_executor_calls_theqoo_collector_when_manager_is_generic_manager(self):
        called = []

        class FakeTheQooCollector:
            def __init__(self, *args, **kwargs):
                pass

            def collect(self, source):
                called.append(source["url"])
                return [
                    {
                        "document_srl": "4200000002",
                        "board_post_no": 150002,
                        "title": "(펌) 실행기 테스트",
                        "url": "https://theqoo.net/hot/4200000002",
                        "board": "hot",
                        "category": "정보",
                        "rank": 1,
                        "time_text": "09:58",
                        "published_at": "2026-07-15T09:58:00",
                        "views": 200,
                        "comment_count": 2,
                        "recommend_count": None,
                        "has_images": True,
                        "source_id": "theqoo",
                    }
                ]

        plan = {
            "plan_status": "ok",
            "lanes": [
                {
                    "lane_id": "lane_theqoo",
                    "shallow_profiles": ["theqoo"],
                }
            ],
        }

        def fake_factory(source_entry, _config):
            return FakeTheQooCollector().collect(source_entry)

        with mock.patch.dict(
            "modules.source_intake.daily_collection_executor.DIRECT_COLLECTOR_FACTORIES",
            {"theqoo": fake_factory},
            clear=False,
        ), mock.patch(
            "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
            return_value=plan,
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
                source_manager=self.manager,
                allow_direct_collectors=True,
            )

        self.assertTrue(called)
        self.assertTrue(any(item["source_id"] == "theqoo" for item in result["items"]))
        source_result = next(
            entry for entry in result["source_results"] if entry["source_id"] == "theqoo"
        )
        self.assertTrue(source_result["success"])


if __name__ == "__main__":
    unittest.main()
