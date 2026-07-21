import json
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from modules.trend_collector.beautynury_collector import BeautynuryCollector


BEAUTYNURY_FIXTURE = """
<main>
  <nav>
    <li><a href="/news/lists/cat/10">전체기사</a></li>
    <li><a href="/news/view/not-an-id/cat/10">뉴스레터 신청</a></li>
  </nav>
  <article class="news-card">
    <span class="section-category">화장품</span>
    <a href="/news/view/110001/cat/10/page/1"><h2>여름 메이크업 색상 변화</h2></a>
    <p class="summary">공개 목록에 표시된 편집 기사 요약입니다.</p>
    <time datetime="2026-07-16">2026.07.16</time>
    <span class="reporter">김기자</span>
    <span class="views">조회 321</span>
  </article>
  <li class="news-item">
    <a href="https://www.beautynury.com/news/view/110002/cat/10">
      향수 시장의 새로운 소비 흐름
    </a>
  </li>
  <li><a href="https://example.com/not-allowed">외부 광고 링크</a></li>
</main>
"""


class TestBeautynuryCollector(unittest.TestCase):
    def setUp(self):
        self.source = {
            "source_id": "beautynury",
            "name": "Beautynury",
            "url": BeautynuryCollector.DEFAULT_URL,
            "type": "beauty_editorial",
        }
        self.no_cache = "tests/_nonexistent_beautynury_cache.json"

    def test_parser_preserves_visible_metadata_and_list_order(self):
        rows = BeautynuryCollector(max_items=10).parse_public_list(BEAUTYNURY_FIXTURE)

        self.assertEqual(len(rows), 2)
        first, second = rows
        self.assertEqual(first["title"], "여름 메이크업 색상 변화")
        self.assertEqual(
            first["link"],
            "https://www.beautynury.com/news/view/110001/cat/10/page/1",
        )
        self.assertEqual(first["section_category"], "화장품")
        self.assertEqual(first["summary"], "공개 목록에 표시된 편집 기사 요약입니다.")
        self.assertEqual(first["visible_date"], "2026-07-16")
        self.assertEqual(first["author"], "김기자")
        self.assertEqual(first["views"], 321)
        self.assertIsNone(first["comments"])
        self.assertIsNone(first["likes"])
        self.assertEqual(first["rank_basis"], "visible_list_order")
        self.assertEqual(second["rank_position"], 2)
        self.assertIsNone(second["summary"])
        self.assertIsNone(second["visible_date"])

    def test_disabled_live_is_honest_and_does_not_fetch(self):
        fetcher = mock.Mock(side_effect=AssertionError("network must remain disabled"))
        collector = BeautynuryCollector(
            config={"cache_path": self.no_cache}, fetcher=fetcher
        )

        self.assertEqual(collector.collect(self.source), [])
        fetcher.assert_not_called()
        self.assertFalse(collector.last_status["success"])
        self.assertEqual(
            collector.last_status["failed_reason"],
            BeautynuryCollector.LIVE_REJECTION_REASON,
        )
        self.assertEqual(collector.last_status["collection_method"], "beautynury_no_data")

    def test_injected_fetch_builds_editorial_items_without_claim_inference(self):
        collector = BeautynuryCollector(
            config={"allow_live_fetch": True, "cache_path": self.no_cache},
            fetcher=lambda url: (url, BEAUTYNURY_FIXTURE),
        )

        items = collector.collect(self.source)

        self.assertEqual(len(items), 2)
        first = items[0]
        self.assertTrue(first["beauty_editorial"])
        self.assertTrue(first["editorial_metadata_only"])
        self.assertFalse(first["article_detail_collected"])
        self.assertFalse(first["efficacy_claims_collected"])
        self.assertFalse(first["medical_claims_collected"])
        self.assertEqual(first["collection_method"], "beautynury_public_editorial_list")
        self.assertFalse(first["is_fallback"])
        self.assertEqual(collector.last_status["count"], 2)

    def test_timeout_uses_fresh_read_only_cache(self):
        payload = {
            "updated_at": datetime.now().astimezone().isoformat(),
            "items": [
                {
                    "title": "캐시 뷰티 편집 기사",
                    "link": "https://www.beautynury.com/news/view/110003/cat/10",
                    "rank_position": 1,
                    "summary": None,
                }
            ],
        }
        collector = BeautynuryCollector(
            config={"allow_live_fetch": True},
            fetcher=lambda _url: (_ for _ in ()).throw(TimeoutError("offline")),
        )
        with mock.patch.object(Path, "exists", return_value=True), mock.patch.object(
            Path, "read_text", return_value=json.dumps(payload, ensure_ascii=False)
        ):
            items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["is_fallback"])
        self.assertTrue(collector.last_status["used_cache"])
        self.assertEqual(collector.last_status["fallback_reason"], "timeout")
        self.assertEqual(
            collector.last_status["collection_method"], "beautynury_editorial_cache"
        )


if __name__ == "__main__":
    unittest.main()
