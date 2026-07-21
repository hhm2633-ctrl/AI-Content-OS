import json
import os
import unittest
import urllib.error
from unittest import mock
from pathlib import Path

from modules.source_intake.daily_collection_executor import execute_daily_shallow_collection
from modules.trend_collector.nate_news_rank_collector import NateNewsRankCollector
from modules.trend_collector.trend_source_manager import TrendSourceManager


INTEREST_FIXTURE = """
<div class="mduSubjectList">
  <div class="mduSubject">
    <dl class="mduRank rank1"><dt><em>1</em></dt><dd><span class="noupdown"><em>-</em></span></dd></dl>
    <div class="mlt01">
      <a class="lt1" href="//news.nate.com/view/20260715n00001?mid=n1006" class="lt1">
        <h2 class="tit">샘플 헤드라인: 리치 아이템 (썸네일·요약 포함)</h2>
      </a>
    </div>
    <span class="tb">샘플 요약 텍스트...</span>
    <em class="mediatype"><img src="//thumbnews.nateimg.co.kr/news90/sample.jpg"></em>
    <span class="medium">샘플일보<em>2026-07-15</em></span>
  </div>
</div>
<ul class="mduSubject mduRankSubject">
  <li>
    <dl class="mduRank rank6"><dt><em>6</em></dt><dd><span class="up"><em>1</em></span></dd></dl>
    <a href="//news.nate.com/view/20260715n00006?mid=n1007"><h2>샘플 헤드라인: 컴팩트 아이템 1</h2></a>
    <span class="medium">샘플컴</span>
  </li>
  <li>
    <dl class="mduRank rank7"><dt><em>7</em></dt><dd><span class="up"><em>3</em></span></dd></dl>
    <a href="//news.nate.com/view/20260715n00007?mid=n1007"><h2>샘플 헤드라인: 컴팩트 아이템 2</h2></a>
    <span class="medium">샘플경제</span>
  </li>
</ul>
"""


CMT_FIXTURE = """
<div class="mduSubjectList">
  <div class="mduSubject">
    <dl class="mduRank rank1"><dt><em>1</em></dt><dd><span class="comment">댓글<em>913</em></span></dd></dl>
    <div class="mlt01">
      <a class="lt1" href="//news.nate.com/view/20260715n00001?mid=n1006" class="lt1">
        <h2 class="tit">샘플 헤드라인: cmt 아이템</h2>
      </a>
    </div>
    <span class="tb">샘플 요약 텍스트...</span>
    <em class="mediatype"><img src="//thumbnews.nateimg.co.kr/news90/sample.jpg"></em>
    <span class="medium">샘플일보<em>2026-07-15</em></span>
  </div>
</div>
"""


class _Source:
    def __init__(self):
        self.url = "https://news.nate.com/rank/?mid=n1006"
        self.entry = {
            "name": "Nate News Rank",
            "type": "news",
            "tier": 5,
            "weight": 30,
            "source_id": "nate_news_rank",
            "url": self.url,
        }


class TestNateNewsRankCollector(unittest.TestCase):
    def setUp(self):
        self.collector = NateNewsRankCollector(
            config={"live_collection_enabled": True}
        )
        self.source = _Source().entry

    def test_collects_interest_rich_and_compact_items_from_fixture(self):
        def fake_fetch(url):
            return (
                "https://news.nate.com/rank/interest?sc=all&p=day&date=20260715",
                INTEREST_FIXTURE,
            )

        self.collector._extract_date = lambda: "20260715"  # type: ignore
        self.collector._fetch_url = fake_fetch
        items = self.collector.collect(self.source)

        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["rank"], 1)
        self.assertEqual(items[0]["title"], "샘플 헤드라인: 리치 아이템 (썸네일·요약 포함)")
        self.assertEqual(items[0]["url"], "https://news.nate.com/view/20260715n00001")
        self.assertEqual(items[0]["article_id"], "20260715n00001")
        self.assertEqual(items[0]["category"], "all")
        self.assertEqual(items[0]["published_date"], "2026-07-15")
        self.assertEqual(items[0]["snippet"], "샘플 요약 텍스트...")
        self.assertEqual(items[0]["thumbnail_url"], "https://thumbnews.nateimg.co.kr/news90/sample.jpg")
        self.assertIsNone(items[0]["comment_count"])
        self.assertEqual(items[0]["rank_change"], {"direction": "none", "delta": 0})

        compact_item = items[2]
        self.assertEqual(compact_item["rank"], 7)
        self.assertEqual(compact_item["snippet"], None)
        self.assertEqual(compact_item["thumbnail_url"], None)
        self.assertEqual(compact_item["published_date"], None)
        self.assertEqual(compact_item["rank_change"], {"direction": "up", "delta": 3})

    def test_collects_comment_count_only_on_cmt(self):
        source = _Source().entry.copy()
        source["url"] = "https://news.nate.com/rank/cmt?sc=all&p=day"

        def fake_fetch(url):
            return (
                "https://news.nate.com/rank/cmt?sc=all&p=day&date=20260715",
                CMT_FIXTURE,
            )

        collector = NateNewsRankCollector(config={"live_collection_enabled": True})
        collector._extract_date = lambda: "20260715"  # type: ignore
        collector._fetch_url = fake_fetch

        items = collector.collect(source)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["comment_count"], 913)
        self.assertIsNone(items[0]["rank_change"])

    def test_empty_visible_publisher_falls_back_to_source_name(self):
        parsed = [{
            "rank": 1,
            "title": "기사 제목",
            "url": "https://news.nate.com/view/20260716n00001",
            "article_id": "20260716n00001",
            "publisher": "",
            "category": "all",
        }]

        items = self.collector._build_items(parsed, self.source, "interest")

        self.assertEqual(items[0]["publisher"], "Nate News Rank")

    def test_cache_used_when_live_fails(self):
        cache_dir = os.path.join("storage", "_tmp_nate_news_rank_cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, "nate_news_rank_cache.json")
        try:
            cache_payload = {
                "source": "nate_news_rank",
                "items": [
                    {
                        "rank": 1,
                        "title": "캐시 헤드라인",
                        "url": "https://news.nate.com/view/20260715n00001",
                        "article_id": "20260715n00001",
                        "publisher": "캐시언론사",
                    }
                ],
            }
            with open(cache_path, "w", encoding="utf-8") as handle:
                json.dump(cache_payload, handle, ensure_ascii=False)

            collector = NateNewsRankCollector(config={"live_collection_enabled": True})
            collector.cache_path = Path(cache_path)  # type: ignore
            def fake_fetch(_):
                raise urllib.error.URLError("network down")

            collector._fetch_url = fake_fetch
            items = collector.collect(self.source)

            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["title"], "캐시 헤드라인")
            self.assertTrue(collector.last_status["used_cache"])
            self.assertEqual(collector.last_status["collection_method"], "nate_news_rank_cache")
        finally:
            if os.path.exists(cache_dir):
                for file_name in os.listdir(cache_dir):
                    if file_name == "nate_news_rank_cache.json":
                        os.remove(os.path.join(cache_dir, file_name))


class TestNateNewsRankExecutorWiring(unittest.TestCase):
    def setUp(self):
        class _ExecutorManager(TrendSourceManager):
            def __init__(self):
                self.config = {"trend_sources": []}

            def _collect_naver_news(self, source):
                return []

            def _collect_nate_pann(self, source):
                return []

            def _collect_fmkorea(self, source):
                return []

            def _collect_bobaedream(self, source):
                return []

        self.manager = _ExecutorManager()
        self.today = "2099-01-05"
        self.output_root = os.path.join("storage", "_tmp_nate_news_rank_executor")

    def tearDown(self):
        if os.path.exists(self.output_root):
            import shutil

            shutil.rmtree(self.output_root, ignore_errors=True)

    def test_executor_uses_local_nate_news_rank_collector_when_manager_lacks_method(self):
        called = []

        plan = {
            "plan_status": "ok",
            "lanes": [
                {
                    "lane_id": "lane_nate_news_rank",
                    "shallow_profiles": ["nate_news_rank"],
                }
            ],
        }

        class FakeNateNewsRankCollector:
            def __init__(self, *args, **kwargs):
                pass

            def collect(self, source):
                called.append(source["url"])
                return [
                    {
                        "rank": 1,
                        "title": "테스트 제목",
                        "url": "https://news.nate.com/view/20260715n00001",
                        "article_id": "20260715n00001",
                        "publisher": "샘플일보",
                        "published_date": "2026-07-15",
                        "category": "all",
                        "rank_change": None,
                        "comment_count": None,
                        "snippet": None,
                        "thumbnail_url": None,
                    }
                ]

        with (
            mock.patch(
                "modules.source_intake.daily_collection_executor.NateNewsRankCollector",
                FakeNateNewsRankCollector,
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
                capability_map=None,
            )

        self.assertTrue(called)
        self.assertEqual(len(result["items"]), 1)
        self.assertTrue(any(item["source_id"] == "nate_news_rank" for item in result["items"]))
        self.assertEqual(
            [entry for entry in result["source_results"] if entry["source_id"] == "nate_news_rank"][0]["success"],
            True,
        )


if __name__ == "__main__":
    unittest.main()
