import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from modules.trend_collector.apparelnews_collector import ApparelNewsCollector


APPARELNEWS_LIST_FIXTURE = """
<main>
  <article class="news-card">
    <span class="category">패션</span>
    <a href="/news/news_view/?idx=225031"><h3>브랜드가 주목하는 여름 소재 변화</h3></a>
    <p class="excerpt">목록에 실제 노출된 기사 설명입니다.</p>
    <span class="date">2026.07.15</span>
    <span class="comments">댓글 3</span>
  </article>
  <li class="list-item">
    <a href="https://www.apparelnews.co.kr/news/news_view/?idx=225032">
      국내 디자이너 브랜드의 새 컬렉션
    </a>
  </li>
</main>
"""

APPARELNEWS_ACTUAL_SHAPE_FIXTURE = """
<main>
  <ul class="sublist">
    <li><a href="/member/join_account">회원가입</a></li>
    <li>
      <p class="img"><a href="/news/news_view/?page=1&amp;cat=CAT100&amp;idx=226437"><img src="thumb.jpg"></a></p>
      <dl>
        <a href="/news/news_view/?page=1&amp;cat=CAT100&amp;idx=226437">
          <dt>베네통코리아, 의류 기부 캠페인 성료</dt>
          <dd class="txt">목록에 표시된 실제 설명입니다.</dd>
        </a>
        <dd class="info">패션/여성복<span>ㅣ</span>2026/07/16</dd>
      </dl>
    </li>
  </ul>
</main>
"""


class TestApparelNewsCollector(unittest.TestCase):
    def setUp(self):
        self.source = {
            "source_id": "apparelnews",
            "name": "ApparelNews",
            "url": "https://www.apparelnews.co.kr/",
            "type": "fashion_editorial",
        }
        self.no_cache = "tests/_nonexistent_apparelnews_cache.json"

    def test_parser_preserves_visible_fields_and_editorial_basis(self):
        rows = ApparelNewsCollector(max_items=10).parse_public_list(
            APPARELNEWS_LIST_FIXTURE
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["title"], "브랜드가 주목하는 여름 소재 변화")
        self.assertEqual(
            rows[0]["link"],
            "https://www.apparelnews.co.kr/news/news_view/?idx=225031",
        )
        self.assertEqual(rows[0]["section_category"], "패션")
        self.assertEqual(rows[0]["summary"], "목록에 실제 노출된 기사 설명입니다.")
        self.assertEqual(rows[0]["visible_date"], "2026.07.15")
        self.assertEqual(rows[0]["comments"], 3)
        self.assertEqual(rows[0]["rank_basis"], "visible_list_order")
        self.assertEqual(rows[0]["attribution"], "ApparelNews public editorial list")
        self.assertIsNone(rows[0]["views"])
        self.assertIsNone(rows[0]["likes"])

    def test_missing_optional_fields_remain_none(self):
        second = ApparelNewsCollector(max_items=10).parse_public_list(
            APPARELNEWS_LIST_FIXTURE
        )[1]

        self.assertEqual(second["rank_position"], 2)
        self.assertIsNone(second["section_category"])
        self.assertIsNone(second["summary"])
        self.assertIsNone(second["visible_date"])
        self.assertIsNone(second["views"])
        self.assertIsNone(second["comments"])
        self.assertIsNone(second["likes"])
        self.assertIsNone(second["publisher"])

    def test_actual_list_shape_excludes_navigation_and_uses_dt_title_only(self):
        rows = ApparelNewsCollector(max_items=10).parse_public_list(
            APPARELNEWS_ACTUAL_SHAPE_FIXTURE
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "베네통코리아, 의류 기부 캠페인 성료")
        self.assertEqual(rows[0]["summary"], "목록에 표시된 실제 설명입니다.")
        self.assertEqual(rows[0]["section_category"], "패션/여성복")
        self.assertEqual(rows[0]["visible_date"], "2026/07/16")
        self.assertNotIn("회원가입", [row["title"] for row in rows])

    def test_disabled_live_returns_honest_empty_without_fetch(self):
        fetcher = mock.Mock(side_effect=AssertionError("network must remain disabled"))
        collector = ApparelNewsCollector(
            config={"cache_path": self.no_cache}, fetcher=fetcher
        )

        self.assertEqual(collector.collect(self.source), [])
        fetcher.assert_not_called()
        self.assertEqual(
            collector.last_status["failed_reason"],
            ApparelNewsCollector.LIVE_REJECTION_REASON,
        )
        self.assertEqual(collector.last_status["collection_method"], "apparelnews_no_data")

    def test_injected_fetcher_produces_non_fallback_editorial_items(self):
        fetcher = mock.Mock(return_value=("https://www.apparelnews.co.kr/", "fixture"))
        parser = mock.Mock(
            return_value=[
                {
                    "title": "주입 성공 어패럴뉴스 기사",
                    "link": "https://www.apparelnews.co.kr/news/news_view/?idx=300001",
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
        collector = ApparelNewsCollector(
            config={"allow_live_fetch": True, "cache_path": self.no_cache},
            fetcher=fetcher,
            parser=parser,
        )

        items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["attribution"], "ApparelNews public editorial list")
        self.assertEqual(items[0]["rank_basis"], "visible_list_order")
        self.assertFalse(items[0]["is_fallback"])
        fetcher.assert_called_once()
        parser.assert_called_once_with("fixture")

    def test_disabled_live_uses_only_fresh_bounded_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            cache_path = Path(directory) / "apparelnews.json"
            cache_path.write_text(
                json.dumps(
                    {
                        "updated_at": datetime.now().isoformat(),
                        "items": [
                            {
                                "title": "캐시 어패럴 기사",
                                "link": "https://www.apparelnews.co.kr/news/news_view/?idx=300002",
                                "rank_position": 1,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            collector = ApparelNewsCollector(config={"cache_path": str(cache_path)})

            items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["is_fallback"])
        self.assertTrue(collector.last_status["used_cache"])
        self.assertEqual(
            collector.last_status["collection_method"], "apparelnews_editorial_cache"
        )


if __name__ == "__main__":
    unittest.main()
