import json
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from modules.trend_collector.cosin_collector import CosinCollector


COSIN_FIXTURE = """
<section>
  <nav>
    <li><a href="/news/article_list_all.html">시작페이지로</a></li>
    <li><a href="/news/section_list_all.html?sec_no=310">뉴스레터 신청</a></li>
  </nav>
  <article class="article-card">
    <span class="category">코스메틱</span>
    <a href="/news/article.html?no=60001"><strong>뷰티 패키지 디자인 트렌드</strong></a>
    <p class="description">공개 기사 목록에 노출된 설명입니다.</p>
    <span class="date">2026-07-16</span>
    <span class="writer">박기자</span>
    <span class="comments">댓글 4</span>
  </article>
  <li class="article-list">
    <a href="https://www.cosinkorea.com/news/article.html?no=60002">
      글로벌 화장품 산업 동향
    </a>
  </li>
  <li><a href="https://outside.example/news">외부 링크 제외</a></li>
</section>
"""


class TestCosinCollector(unittest.TestCase):
    def setUp(self):
        self.source = {
            "source_id": "cosin",
            "name": "Cosin Korea",
            "url": CosinCollector.DEFAULT_URL,
            "type": "beauty_editorial",
        }
        self.no_cache = "tests/_nonexistent_cosin_cache.json"

    def test_parser_preserves_visible_metadata_and_rejects_external_links(self):
        rows = CosinCollector(max_items=10).parse_public_list(COSIN_FIXTURE)

        self.assertEqual(len(rows), 2)
        first, second = rows
        self.assertEqual(first["title"], "뷰티 패키지 디자인 트렌드")
        self.assertEqual(
            first["link"], "https://www.cosinkorea.com/news/article.html?no=60001"
        )
        self.assertEqual(first["section_category"], "코스메틱")
        self.assertEqual(first["summary"], "공개 기사 목록에 노출된 설명입니다.")
        self.assertEqual(first["visible_date"], "2026-07-16")
        self.assertEqual(first["author"], "박기자")
        self.assertEqual(first["comments"], 4)
        self.assertIsNone(first["views"])
        self.assertIsNone(first["likes"])
        self.assertEqual(first["attribution"], "Cosin Korea public editorial list")
        self.assertEqual(second["rank_position"], 2)
        self.assertIsNone(second["summary"])

    def test_disabled_live_is_honest_and_does_not_fetch(self):
        fetcher = mock.Mock(side_effect=AssertionError("network must remain disabled"))
        collector = CosinCollector(
            config={"cache_path": self.no_cache}, fetcher=fetcher
        )

        self.assertEqual(collector.collect(self.source), [])
        fetcher.assert_not_called()
        self.assertFalse(collector.last_status["success"])
        self.assertEqual(
            collector.last_status["failed_reason"], CosinCollector.LIVE_REJECTION_REASON
        )
        self.assertEqual(collector.last_status["collection_method"], "cosin_no_data")

    def test_injected_fetch_builds_cosin_editorial_contract(self):
        collector = CosinCollector(
            config={"allow_live_fetch": True, "cache_path": self.no_cache},
            fetcher=lambda url: (url, COSIN_FIXTURE),
        )

        items = collector.collect(self.source)

        self.assertEqual(len(items), 2)
        first = items[0]
        self.assertEqual(first["source_id"], "cosin")
        self.assertEqual(first["publisher"], "Cosin Korea")
        self.assertTrue(first["beauty_editorial"])
        self.assertFalse(first["efficacy_claims_collected"])
        self.assertFalse(first["medical_claims_collected"])
        self.assertEqual(first["collection_method"], "cosin_public_editorial_list")
        self.assertFalse(first["is_fallback"])
        self.assertEqual(collector.last_status["count"], 2)

    def test_network_failure_uses_fresh_read_only_cache(self):
        payload = {
            "updated_at": datetime.now().astimezone().isoformat(),
            "items": [
                {
                    "title": "캐시 코스인 편집 기사",
                    "link": "https://www.cosinkorea.com/news/article.html?no=60003",
                    "rank_position": 1,
                    "views": None,
                    "comments": None,
                    "likes": None,
                }
            ],
        }
        collector = CosinCollector(
            config={"allow_live_fetch": True},
            fetcher=lambda _url: (_ for _ in ()).throw(OSError("offline")),
        )
        with mock.patch.object(Path, "exists", return_value=True), mock.patch.object(
            Path, "read_text", return_value=json.dumps(payload, ensure_ascii=False)
        ):
            items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["is_fallback"])
        self.assertTrue(collector.last_status["used_cache"])
        self.assertEqual(collector.last_status["fallback_reason"], "unknown_error")
        self.assertEqual(collector.last_status["collection_method"], "cosin_editorial_cache")


if __name__ == "__main__":
    unittest.main()
