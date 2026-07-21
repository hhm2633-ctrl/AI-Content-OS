import os
import shutil
import unittest
from unittest import mock

from modules.source_intake.daily_collection_executor import execute_daily_shallow_collection
from modules.source_intake.source_capability_map import SourceCapabilityMap
from modules.trend_collector.newsis_collector import NewsisCollector


ARTICLE_LIST_FIXTURE = """
<ul class="articleList2">
  <li>
    <div class="boxStyle05">
      <div class="txtCont">
        <p class="tit"><a href="/view/NISX19700101_0000000001">샘플 제목 1</a></p>
        <p class="txt"><a href="/view/NISX19700101_0000000001">요약 텍스트 1</a></p>
        <p class="time"><span>테스트기자</span>2026.01.01 00:00:01</p>
      </div>
      <div class="thumCont"><img src="//image.newsis.com/FIXTURE_thm.jpg" /></div>
    </div>
  </li>
  <li>
    <div class="boxStyle05">
      <div class="txtCont">
        <p class="tit"><a href="/view/NISX19700101_0000000002">샘플 제목 2</a></p>
        <p class="txt"><a href="/view/NISX19700101_0000000002">요약 텍스트 2</a></p>
        <p class="time"><span>테스트기자</span>2026.01.01 00:00:02</p>
      </div>
      <div class="thumCont"><img src="//image.newsis.com/FIXTURE_thm.jpg" /></div>
    </div>
  </li>
  <li>
    <div class="boxStyle05">
      <div class="txtCont">
        <p class="tit"><a href="/view/NISX19700101_0000000003">샘플 제목 3</a></p>
        <p class="txt"><a href="/view/NISX19700101_0000000003">요약 텍스트 3</a></p>
        <p class="time"><span>테스트기자</span>2026.01.01 00:00:03</p>
      </div>
      <div class="thumCont"><img src="//image.newsis.com/FIXTURE_thm.jpg" /></div>
    </div>
  </li>
</ul>
<div class="rankBox">
  <div class="sectName">
    <div class="tit"><a href="#topnews1">종합</a></div>
  </div>
  <div id="topnews1">
    <ul class="left">
      <li><a href="/view/NISX19700101_0000000011">랭크 항목 1</a></li>
      <li><a href="/view/NISX19700101_0000000012">랭크 항목 2</a></li>
    </ul>
    <ul class="right"><li><a href="/view/NISX19700101_0000000013">랭크 항목 3</a></li><li><a href="/view/NISX19700101_0000000014">랭크 항목 4</a></li>
  </div>
</div>
"""

MALFORMED_RANK_FIXTURE = """
<div class="rankBox">
  <div id="topnews2">
    <ul class="left">
      <li><a href="/view/NISX19700101_0000000021">malformed left 1</a></li>
      <li><a href="/view/NISX19700101_0000000022">malformed left 2</a></li>
    </ul>
    <ul class="right">
      <li><a href="/view/NISX19700101_0000000023">malformed right 1</a></li>
      <li><a href="/view/NISX19700101_0000000024">malformed right 2</a></li>
</div>
"""


class TestNewsisCollector(unittest.TestCase):
    def test_collects_verified_list_fields_and_rank_order(self):
        source = {
            "source_id": "newsis",
            "name": "Newsis",
            "url": "https://www.newsis.com/society/list/?cid=10200&scid=10201",
            "type": "news_wire",
            "tier": 1,
            "weight": 20,
        }

        collector = NewsisCollector(max_items=20)
        collector._fetch_url = lambda _url: ("https://www.newsis.com/society/list/?cid=10200&scid=10201", ARTICLE_LIST_FIXTURE)

        items = collector.collect(source)
        list_items = [item for item in items if item.get("surface") == "list"]
        rank_items = [item for item in items if item.get("surface") == "rank"]

        self.assertEqual(len(list_items), 3)
        self.assertEqual(list_items[0]["headline"], "샘플 제목 1")
        self.assertEqual(list_items[0]["article_id"], "NISX19700101_0000000001")
        self.assertEqual(list_items[0]["link"], "https://www.newsis.com/view/NISX19700101_0000000001")
        self.assertEqual(list_items[0]["category"], "society")
        self.assertEqual(list_items[0]["publisher"], "뉴시스")
        self.assertEqual(list_items[0]["published_at"], "2026.01.01 00:00:01")
        self.assertEqual(list_items[0]["thumbnail"], "https://image.newsis.com/FIXTURE_thm.jpg")

        self.assertEqual(len(rank_items), 4)
        self.assertEqual(rank_items[0]["rank_position"], 1)
        self.assertEqual(rank_items[0]["headline"], "랭크 항목 1")
        self.assertEqual(rank_items[3]["rank_position"], 4)
        self.assertEqual(rank_items[3]["headline"], "랭크 항목 4")

    def test_lenient_rankbox_parsing_handles_malformed_markup(self):
        collector = NewsisCollector(max_items=20)
        parsed = collector._parse_rank_box_tabs(MALFORMED_RANK_FIXTURE)

        self.assertEqual(len(parsed), 4)
        self.assertEqual(parsed[0]["rank"], 13)
        self.assertEqual(parsed[0]["headline"], "malformed left 1")
        self.assertEqual(parsed[1]["rank"], 14)
        self.assertEqual(parsed[1]["headline"], "malformed left 2")
        self.assertEqual(parsed[2]["rank"], 15)
        self.assertEqual(parsed[2]["headline"], "malformed right 1")
        self.assertEqual(parsed[3]["rank"], 16)
        self.assertEqual(parsed[3]["headline"], "malformed right 2")


class TestNewsisExecutorWiring(unittest.TestCase):
    def setUp(self):
        class _ExecutorManager:
            def _collect_naver_news(self, source):
                return []

            def _collect_nate_pann(self, source):
                return []

            def _collect_fmkorea(self, source):
                return []

            def _collect_bobaedream(self, source):
                return []

            def _collect_daum_news(self, source):
                return []

        self.manager = _ExecutorManager()
        self.today = "2099-01-11"
        self.output_root = os.path.join("storage", "_tmp_newsis_executor")

    def tearDown(self):
        if os.path.exists(self.output_root):
            shutil.rmtree(self.output_root, ignore_errors=True)

    def test_executor_uses_newsis_collector_when_available(self):
        called = []
        plan = {
            "plan_status": "ok",
            "lanes": [
                {
                    "lane_id": "lane_newsis",
                    "shallow_profiles": ["newsis"],
                }
            ],
        }

        class FakeNewsisCollector:
            def __init__(self, *args, **kwargs):
                pass

            def collect(self, source):
                called.append(source["url"])
                return [
                    {
                        "headline": "뉴스스 테스트",
                        "link": "https://www.newsis.com/view/NISX19700101_0000000001",
                        "article_id": "NISX19700101_0000000001",
                        "surface": "list",
                        "source_id": "newsis",
                    }
                ]

        with (
            mock.patch(
                "modules.source_intake.daily_collection_executor.NewsisCollector",
                FakeNewsisCollector,
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
                return_value=plan,
            ),
        ):
            result = execute_daily_shallow_collection(
                account_profiles=["news_society_economy"],
                today=self.today,
                output_root=self.output_root,
                source_manager=self.manager,
                allow_direct_collectors=True,
                capability_map=SourceCapabilityMap(),
            )

        self.assertTrue(called)
        self.assertTrue(any(entry["source_id"] == "newsis" for entry in result["source_results"]))
        newsis_entry = next(entry for entry in result["source_results"] if entry["source_id"] == "newsis")
        self.assertTrue(newsis_entry["success"])
        self.assertEqual(len(result["items"]), 1)


if __name__ == "__main__":
    unittest.main()
