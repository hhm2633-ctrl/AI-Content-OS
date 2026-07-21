import unittest
from unittest import mock

from modules.trend_collector.fashionn_collector import FashionNCollector


FASHIONN_LIST_FIXTURE = """
<main>
  <article class="news-card">
    <span class="section-category">패션뉴스</span>
    <a href="/board/read_new.php?table=1006&amp;number=501">
      <h2>2026 서울 패션위크 주요 컬러</h2>
    </a>
    <p class="summary">공개 목록에 보이는 요약만 수집합니다.</p>
    <time datetime="2026-07-16">2026.07.16</time>
    <span class="views">조회 1,234</span>
    <span class="comments">댓글 0</span>
  </article>
  <article class="news-card">
    <a href="https://www.fashionn.com/board/read_new.php?table=1006&amp;number=502">
      여름 리조트 컬렉션 편집 목록
    </a>
  </article>
</main>
"""


class TestFashionNCollector(unittest.TestCase):
    def setUp(self):
        self.source = {
            "source_id": "fashionn",
            "name": "FashionN",
            "url": "https://www.fashionn.com/",
            "type": "fashion_editorial",
        }
        self.no_cache = "tests/_nonexistent_fashionn_cache.json"

    def test_parser_preserves_visible_fields_and_list_order_basis(self):
        collector = FashionNCollector(max_items=10)

        rows = collector.parse_public_list(FASHIONN_LIST_FIXTURE)

        self.assertEqual(len(rows), 2)
        first = rows[0]
        self.assertEqual(first["title"], "2026 서울 패션위크 주요 컬러")
        self.assertEqual(
            first["link"],
            "https://www.fashionn.com/board/read_new.php?table=1006&number=501",
        )
        self.assertEqual(first["section_category"], "패션뉴스")
        self.assertEqual(first["summary"], "공개 목록에 보이는 요약만 수집합니다.")
        self.assertEqual(first["visible_date"], "2026-07-16")
        self.assertEqual(first["rank_position"], 1)
        self.assertEqual(first["rank_basis"], "visible_list_order")
        self.assertEqual(first["attribution"], "FashionN public editorial list")
        self.assertEqual(first["views"], 1234)
        self.assertEqual(first["comments"], 0)
        self.assertIsNone(first["likes"])

    def test_parser_keeps_non_visible_optional_fields_none(self):
        collector = FashionNCollector(max_items=10)

        second = collector.parse_public_list(FASHIONN_LIST_FIXTURE)[1]

        self.assertEqual(second["rank_position"], 2)
        self.assertEqual(second["rank_basis"], "visible_list_order")
        self.assertIsNone(second["section_category"])
        self.assertIsNone(second["summary"])
        self.assertIsNone(second["visible_date"])
        self.assertIsNone(second["views"])
        self.assertIsNone(second["comments"])
        self.assertIsNone(second["likes"])
        self.assertIsNone(second["publisher"])

    def test_disabled_live_returns_honest_empty_without_fetch(self):
        fetcher = mock.Mock(side_effect=AssertionError("network must remain disabled"))
        collector = FashionNCollector(
            config={"cache_path": self.no_cache},
            fetcher=fetcher,
        )

        items = collector.collect(self.source)

        self.assertEqual(items, [])
        fetcher.assert_not_called()
        self.assertFalse(collector.last_status["success"])
        self.assertEqual(
            collector.last_status["failed_reason"],
            FashionNCollector.LIVE_REJECTION_REASON,
        )
        self.assertEqual(collector.last_status["collection_method"], "fashionn_no_data")
        self.assertEqual(collector.last_status["service_diagnostic"]["status"], "fallback_used")

    def test_injected_fetcher_and_parser_produce_non_fallback_collect_result(self):
        fetcher = mock.Mock(return_value=("https://www.fashionn.com/", "fixture"))
        parser = mock.Mock(
            return_value=[
                {
                    "title": "주입력 성공 패션 기사",
                    "link": "https://www.fashionn.com/board/read_new.php?number=700",
                    "summary": None,
                    "visible_date": None,
                    "section_category": "패션뉴스",
                    "rank_position": 1,
                    "views": None,
                    "comments": None,
                    "likes": None,
                }
            ]
        )
        collector = FashionNCollector(
            config={"allow_live_fetch": True, "cache_path": self.no_cache},
            fetcher=fetcher,
            parser=parser,
        )

        items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        fetcher.assert_called_once()
        parser.assert_called_once_with("fixture")
        self.assertTrue(collector.last_status["success"])
        self.assertEqual(
            collector.last_status["collection_method"],
            "fashionn_public_editorial_list",
        )
        self.assertEqual(items[0]["rank_basis"], "visible_list_order")
        self.assertFalse(items[0]["is_fallback"])
        self.assertTrue(items[0]["collected_at"])


if __name__ == "__main__":
    unittest.main()
