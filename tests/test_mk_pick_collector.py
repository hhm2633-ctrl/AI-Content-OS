import json
import os
import shutil
import unittest
from pathlib import Path
from unittest import mock
import socket
import urllib.request

from modules.source_intake.daily_collection_executor import execute_daily_shallow_collection
from modules.trend_collector.mk_pick_collector import MkPickCollector


PICK_LIST_FIXTURE = """
<div>
  <a href="https://www.mk.co.kr/news/pick/12098864" class="item">
    <h3 class="main_tit">샘플 제목 1</h3>
    <p class="main_desc">요약 본문 1</p>
    <div class="main_thumb"><img src="https://wimg.mk.co.kr/example_T1.jpg" /></div>
  </a>
  <a href="//www.mk.co.kr/news/pick/12098865" class="item">
    <h3 class="main_tit">샘플 제목 2</h3>
    <p class="main_desc">요약 본문 2</p>
    <div><img src="https://wimg.mk.co.kr/example2.jpg" /></div>
  </a>
  <a href="https://www.mk.co.kr/news/pick/brand/test">
    <h3 class="main_tit">브랜드 페이지</h3>
  </a>
  <a href="https://www.mk.co.kr/news/economy/12000000">
    <h3 class="main_tit">경제 일반 페이지</h3>
  </a>
  <a href="/news/pick/12098866"><h3 class="main_tit">상대 URL 샘플</h3></a>
</div>
"""


SOURCE_ENTRY = {
    "source_id": "mk_economy",
    "name": "매일경제",
    "url": "https://www.mk.co.kr/news/economy/",
    "type": "news_economy",
    "tier": 5,
    "weight": 20,
}


class TestMkPickCollector(unittest.TestCase):
    def setUp(self):
        self.collector = MkPickCollector(timeout=2, max_items=10, config={"live_collection_enabled": True})

    def test_only_collects_authorized_pick_article_links(self):
        self.collector._fetch_url = lambda _url: PICK_LIST_FIXTURE  # type: ignore
        items = self.collector.collect(SOURCE_ENTRY)

        self.assertEqual(len(items), 3)
        urls = [item["url"] for item in items]
        self.assertIn("https://www.mk.co.kr/news/pick/12098864", urls[0])
        self.assertIn("https://www.mk.co.kr/news/pick/12098865", urls[1])
        self.assertIn("https://www.mk.co.kr/news/pick/12098866", urls[2])
        self.assertNotIn("https://www.mk.co.kr/news/pick/brand/test", urls)
        self.assertEqual(items[0]["publisher"], "매일경제")
        self.assertEqual(items[0]["fetched_via"], "live")
        self.assertEqual(items[0]["collection_method"], "mk_economy_pick_html")
        self.assertEqual(self.collector.last_status["collection_method"], "mk_economy_pick_html")

    def test_cache_is_used_when_live_fetch_fails(self):
        cache_root = os.path.join("storage", "_tmp_mk_pick_cache")
        os.makedirs(cache_root, exist_ok=True)
        cache_path = os.path.join(cache_root, "mk_economy_cache.json")
        payload = {
            "source": "mk_economy",
            "items": [
                {
                    "article_id": "12098864",
                    "title": "캐시 기사",
                    "url": "https://www.mk.co.kr/news/pick/12098864",
                    "summary": "캐시 요약",
                    "publisher": "매일경제",
                }
            ],
        }
        with open(cache_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

        try:
            self.collector.cache_path = Path(cache_path)  # type: ignore
            self.collector._fetch_url = lambda _url: (_ for _ in ()).throw(Exception("network down"))  # type: ignore
            items = self.collector.collect(SOURCE_ENTRY)

            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["title"], "캐시 기사")
            self.assertTrue(items[0]["fallback_used"])
            self.assertEqual(self.collector.last_status["used_cache"], True)
            self.assertEqual(self.collector.last_status["collection_method"], "mk_economy_cache")
        finally:
            if os.path.exists(cache_root):
                shutil.rmtree(cache_root, ignore_errors=True)


class TestMkPickExecutorWiring(unittest.TestCase):
    def setUp(self):
        self.today = "2099-01-22"
        self.output_root = os.path.join("storage", "_tmp_mk_pick_executor")
        if os.path.exists(self.output_root):
            shutil.rmtree(self.output_root, ignore_errors=True)
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
            shutil.rmtree(self.output_root, ignore_errors=True)

    def test_executor_uses_mk_pick_collector_when_manager_lacks_method(self):
        called = []

        class FakeMkPickCollector:
            def __init__(self, *args, **kwargs):
                pass

            def collect(self, source):
                called.append(source["source_id"])
                return [
                    {
                        "source": "mk_economy",
                        "source_id": "mk_economy",
                        "source_name": "매일경제",
                        "article_id": "12098864",
                        "title": "실행기 샘플",
                        "url": "https://www.mk.co.kr/news/pick/12098864",
                        "publisher": "매일경제",
                        "collected_at": "2026-07-15T10:00:00+09:00",
                        "collection_method": "mk_economy_pick_html",
                        "fetched_via": "live",
                    }
                ]

        plan = {
            "plan_status": "ok",
            "lanes": [
                {
                    "lane_id": "lane_mk_economy",
                    "shallow_profiles": ["mk_economy"],
                }
            ],
        }

        def fake_factory(source_entry, _config):
            return FakeMkPickCollector().collect(source_entry)

        with mock.patch.dict(
            "modules.source_intake.daily_collection_executor.DIRECT_COLLECTOR_FACTORIES",
            {"mk_economy": fake_factory},
            clear=False,
        ), mock.patch(
            "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
            return_value=plan,
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
                source_manager=None,
            )

        self.assertEqual(called, ["mk_economy"])
        self.assertTrue(any(item["source_id"] == "mk_economy" for item in result["items"]))
        source_result = next(
            entry for entry in result["source_results"] if entry["source_id"] == "mk_economy"
        )
        self.assertTrue(source_result["success"])


if __name__ == "__main__":
    unittest.main()
