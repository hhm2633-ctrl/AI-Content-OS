import unittest

from modules.trend_collector.oliveyoung_ranking_collector import (
    OliveYoungRankingCollector,
)


RANKING_FIXTURE = """
<nav><button class="selected">스킨케어</button></nav>
<ol class="best-list">
  <li data-rank="3">
    <a href="/store/goods/getGoodsDetail.do?goodsNo=A000000001"
       data-ref-brandnm="테스트브랜드"
       data-ref-goodsnm="수분 세럼">
      <span class="tx_cur">19,900원</span>
      <span class="badge">오늘드림</span>
      <em class="flag">1+1</em>
    </a>
  </li>
  <li>
    <a href="https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000002"
       data-ref-brandnm="두번째브랜드"
       data-ref-goodsnm="클렌징 폼"></a>
  </li>
</ol>
"""


SOURCE = {
    "source_id": "oliveyoung_ranking",
    "name": "Olive Young",
    "url": OliveYoungRankingCollector.DEFAULT_URL,
    "type": "retailer_ranking",
}


class TestOliveYoungRankingCollector(unittest.TestCase):
    def test_fixture_preserves_explicit_rank_and_visible_retailer_signals(self):
        collector = OliveYoungRankingCollector(max_items=10)

        rows = collector.parse_public_ranking(RANKING_FIXTURE)

        self.assertEqual(len(rows), 2)
        first, second = rows
        self.assertEqual(first["category_scope"], "스킨케어")
        self.assertEqual(first["rank"], 3)
        self.assertEqual(first["visible_rank"], 3)
        self.assertEqual(first["list_position"], 1)
        self.assertEqual(first["rank_basis"], "visible_retailer_rank")
        self.assertEqual(first["visible_price_text"], "19,900원")
        self.assertEqual(first["promotion_labels"], ["오늘드림", "1+1"])
        self.assertEqual(first["ranking_scope"], "retailer_specific")
        self.assertTrue(first["promotion_sensitive"])
        self.assertFalse(first["universal_trend_claimed"])

        self.assertIsNone(second["rank"])
        self.assertIsNone(second["visible_rank"])
        self.assertEqual(second["list_position"], 2)
        self.assertEqual(second["rank_basis"], "retailer_page_order_only")
        self.assertIsNone(second["visible_price_text"])
        self.assertEqual(second["promotion_labels"], [])

    def test_injected_fetch_collects_without_fabricating_volatile_fields(self):
        fetched_urls = []

        def fetcher(url):
            fetched_urls.append(url)
            return url, RANKING_FIXTURE

        collector = OliveYoungRankingCollector(
            max_items=10,
            config={"allow_live_fetch": True},
            fetcher=fetcher,
        )

        items = collector.collect(SOURCE)

        self.assertEqual(fetched_urls, [OliveYoungRankingCollector.DEFAULT_URL])
        self.assertEqual(len(items), 2)
        first = items[0]
        self.assertEqual(first["rank"], 3)
        self.assertEqual(first["visible_rank"], 3)
        self.assertEqual(first["visible_price_text"], "19,900원")
        self.assertEqual(first["promotion_labels"], ["오늘드림", "1+1"])
        self.assertEqual(first["ranking_scope"], "retailer_specific")
        self.assertTrue(first["promotion_sensitive"])
        self.assertFalse(first["universal_trend_claimed"])
        for unavailable_field in ("sales", "reviews", "inventory"):
            self.assertIsNone(first[unavailable_field])
        self.assertEqual(first["collection_method"], "oliveyoung_public_ranking")
        self.assertFalse(first["is_fallback"])
        self.assertTrue(collector.last_status["success"])
        self.assertEqual(collector.last_status["count"], 2)
        self.assertEqual(
            collector.last_status["collection_method"],
            "oliveyoung_public_ranking",
        )

    def test_disabled_live_returns_honest_empty_result_without_fetching(self):
        def forbidden_fetcher(_url):
            self.fail("disabled collector must not invoke its fetcher")

        collector = OliveYoungRankingCollector(fetcher=forbidden_fetcher)
        collector._load_cache = lambda _source: []

        items = collector.collect(SOURCE)

        self.assertEqual(items, [])
        self.assertTrue(collector.last_status["attempted"])
        self.assertFalse(collector.last_status["success"])
        self.assertEqual(collector.last_status["count"], 0)
        self.assertEqual(
            collector.last_status["failed_reason"],
            OliveYoungRankingCollector.LIVE_REJECTION_REASON,
        )
        self.assertEqual(
            collector.last_status["collection_method"],
            "oliveyoung_ranking_no_data",
        )
        self.assertFalse(collector.last_status["used_cache"])
        self.assertEqual(collector.last_status["ranking_scope"], "retailer_specific")
        self.assertTrue(collector.last_status["promotion_sensitive"])
        self.assertFalse(collector.last_status["universal_trend_claimed"])


if __name__ == "__main__":
    unittest.main()
