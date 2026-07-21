import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from modules.trend_collector.fashionbiz_collector import FashionBizCollector


FASHIONBIZ_LIST_FIXTURE = """
<main>
  <article class="article-card">
    <span class="section-category">패션 트렌드</span>
    <a href="/article/225940"><h2>여름 런웨이에 나타난 새로운 컬러 흐름</h2></a>
    <p class="summary">공개 목록에 표시된 요약입니다.</p>
    <time datetime="2026-07-16">2026.07.16</time>
    <span class="views">조회 1,205</span>
  </article>
  <li class="news-item">
    <a href="https://www.fashionbiz.co.kr/article/225941">신진 브랜드의 리조트 스타일</a>
  </li>
</main>
"""

FASHIONBIZ_GRAPHQL_FIXTURE = """
{
  "data": {
    "seeLatestBestNews": {
      "articles": [
        {
          "cts_id": 225942,
          "title": "공개 목록 API의 패션 기사",
          "openResDate": "2026-07-16T08:20:00.000Z",
          "clickCount": 146,
          "commentCount": 0
        }
      ]
    }
  }
}
"""


class TestFashionBizCollector(unittest.TestCase):
    def setUp(self):
        self.source = {
            "source_id": "fashionbiz",
            "name": "FashionBiz",
            "url": "https://fashionbiz.co.kr/",
            "type": "fashion_editorial",
        }
        self.no_cache = "tests/_nonexistent_fashionbiz_cache.json"

    def test_parser_preserves_visible_fields_and_editorial_basis(self):
        rows = FashionBizCollector(max_items=10).parse_public_list(
            FASHIONBIZ_LIST_FIXTURE
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["title"], "여름 런웨이에 나타난 새로운 컬러 흐름")
        self.assertEqual(rows[0]["link"], "https://fashionbiz.co.kr/article/225940")
        self.assertEqual(rows[0]["section_category"], "패션 트렌드")
        self.assertEqual(rows[0]["summary"], "공개 목록에 표시된 요약입니다.")
        self.assertEqual(rows[0]["visible_date"], "2026-07-16")
        self.assertEqual(rows[0]["views"], 1205)
        self.assertEqual(rows[0]["rank_position"], 1)
        self.assertEqual(rows[0]["rank_basis"], "visible_list_order")
        self.assertEqual(rows[0]["attribution"], "FashionBiz public editorial list")
        self.assertIsNone(rows[0]["comments"])
        self.assertIsNone(rows[0]["likes"])

    def test_missing_optional_fields_remain_none(self):
        second = FashionBizCollector(max_items=10).parse_public_list(
            FASHIONBIZ_LIST_FIXTURE
        )[1]

        self.assertEqual(second["rank_position"], 2)
        self.assertIsNone(second["section_category"])
        self.assertIsNone(second["summary"])
        self.assertIsNone(second["visible_date"])
        self.assertIsNone(second["views"])
        self.assertIsNone(second["comments"])
        self.assertIsNone(second["likes"])
        self.assertIsNone(second["publisher"])

    def test_parser_accepts_public_list_query_and_builds_strict_article_link(self):
        rows = FashionBizCollector(max_items=10).parse_public_list(
            FASHIONBIZ_GRAPHQL_FIXTURE
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "공개 목록 API의 패션 기사")
        self.assertEqual(rows[0]["link"], "https://fashionbiz.co.kr/article/225942")
        self.assertEqual(rows[0]["views"], 146)
        self.assertEqual(rows[0]["comments"], 0)
        self.assertIsNone(rows[0]["likes"])

    def test_parser_excludes_same_host_navigation_links(self):
        html = """
        <ul>
          <li><a href="/notice">공지사항</a></li>
          <li><a href="/member/join">회원가입</a></li>
          <li><a href="/article/225943"><h3>실제 패션 기사</h3></a></li>
        </ul>
        """

        rows = FashionBizCollector(max_items=10).parse_public_list(html)

        self.assertEqual([row["title"] for row in rows], ["실제 패션 기사"])

    def test_disabled_live_returns_honest_empty_without_fetch(self):
        fetcher = mock.Mock(side_effect=AssertionError("network must remain disabled"))
        collector = FashionBizCollector(
            config={"cache_path": self.no_cache}, fetcher=fetcher
        )

        self.assertEqual(collector.collect(self.source), [])
        fetcher.assert_not_called()
        self.assertEqual(
            collector.last_status["failed_reason"],
            FashionBizCollector.LIVE_REJECTION_REASON,
        )
        self.assertEqual(collector.last_status["collection_method"], "fashionbiz_no_data")

    def test_injected_fetcher_produces_non_fallback_editorial_items(self):
        fetcher = mock.Mock(return_value=("https://fashionbiz.co.kr/", "fixture"))
        parser = mock.Mock(
            return_value=[
                {
                    "title": "주입 성공 패션비즈 기사",
                    "link": "https://fashionbiz.co.kr/article/300001",
                    "rank_position": 1,
                    "summary": None,
                    "visible_date": None,
                    "section_category": "패션",
                    "views": None,
                    "comments": None,
                    "likes": None,
                }
            ]
        )
        collector = FashionBizCollector(
            config={"allow_live_fetch": True, "cache_path": self.no_cache},
            fetcher=fetcher,
            parser=parser,
        )

        items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["attribution"], "FashionBiz public editorial list")
        self.assertEqual(items[0]["rank_basis"], "visible_list_order")
        self.assertFalse(items[0]["is_fallback"])
        fetcher.assert_called_once()
        parser.assert_called_once_with("fixture")

    def test_disabled_live_uses_only_fresh_bounded_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            cache_path = Path(directory) / "fashionbiz.json"
            cache_path.write_text(
                json.dumps(
                    {
                        "updated_at": datetime.now().isoformat(),
                        "items": [
                            {
                                "title": "캐시 패션 기사",
                                "link": "https://fashionbiz.co.kr/article/300002",
                                "rank_position": 1,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            collector = FashionBizCollector(config={"cache_path": str(cache_path)})

            items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["is_fallback"])
        self.assertTrue(collector.last_status["used_cache"])
        self.assertEqual(
            collector.last_status["collection_method"], "fashionbiz_editorial_cache"
        )


if __name__ == "__main__":
    unittest.main()
