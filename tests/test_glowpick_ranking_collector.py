import json
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from modules.trend_collector.glowpick_ranking_collector import (
    GlowpickRankingCollector,
)


RANKING_FIXTURE = """
<nav><button class="active">에센스/세럼</button></nav>
<ol class="ranking-list">
  <li data-rank="2" data-brand="글로우브랜드" data-product-name="수분 세럼">
    <a href="/products/101">
      <span class="rating-score">4.37</span>
      <span class="review-count">리뷰 1,234</span>
      <span class="product-price">28,000원</span>
      <span class="product-volume">50 ml</span>
      <strong class="award">2026 어워드</strong>
      <em class="aggregate-label">재구매 집계</em>
      <p class="review-body">개인 리뷰 본문은 수집하지 않음</p>
      <p class="ai-summary">효과 요약 문구도 수집하지 않음</p>
    </a>
  </li>
  <li data-brand="두번째브랜드" data-product-name="클렌저">
    <a href="https://www.glowpick.com/products/102"></a>
  </li>
</ol>
"""


CURRENT_NEXT_STREAMING_SHELL_FIXTURE = """
<main class="MainContent-module-scss-module__HqlgCW__appMain glowpick-main">
  <template id="B:1"></template>
  <div class="loading-module-scss-module__sUpgQW__screen">로딩 중</div>
</main>
<script>self.__next_f.push([1,"products,brand-new,__PAGE__"])</script>
"""


SOURCE = {
    "source_id": "glowpick_ranking",
    "name": "Glowpick",
    "url": GlowpickRankingCollector.DEFAULT_URL,
    "type": "consumer_review_ranking",
}


class TestGlowpickRankingCollector(unittest.TestCase):
    def test_current_next_streaming_shell_fails_closed_without_product_cards(self):
        rows = GlowpickRankingCollector().parse_public_ranking(
            CURRENT_NEXT_STREAMING_SHELL_FIXTURE
        )

        self.assertEqual(rows, [])

    def test_fixture_preserves_only_visible_product_and_aggregate_signals(self):
        rows = GlowpickRankingCollector(max_items=10).parse_public_ranking(RANKING_FIXTURE)

        self.assertEqual(len(rows), 2)
        first, second = rows
        self.assertEqual(first["category_scope"], "에센스/세럼")
        self.assertEqual(first["rank"], 2)
        self.assertEqual(first["brand"], "글로우브랜드")
        self.assertEqual(first["product_title"], "수분 세럼")
        self.assertEqual(first["rating"], 4.37)
        self.assertEqual(first["review_count"], 1234)
        self.assertEqual(first["visible_price_text"], "28,000원")
        self.assertEqual(first["visible_volume_text"], "50 ml")
        self.assertEqual(first["award_labels"], ["2026 어워드"])
        self.assertEqual(first["aggregate_labels"], ["재구매 집계"])
        self.assertTrue(first["consumer_review_signal"])
        self.assertTrue(first["platform_specific"])
        self.assertFalse(first["universal_trend_claimed"])
        self.assertNotIn("개인 리뷰 본문", json.dumps(first, ensure_ascii=False))
        self.assertNotIn("효과 요약", json.dumps(first, ensure_ascii=False))

        self.assertIsNone(second["rank"])
        self.assertIsNone(second["rating"])
        self.assertIsNone(second["review_count"])
        self.assertIsNone(second["visible_price_text"])
        self.assertIsNone(second["visible_volume_text"])
        self.assertFalse(second["consumer_review_signal"])

    def test_injected_fetch_builds_provenance_without_market_truth_claim(self):
        fetched = []

        def fetcher(url):
            fetched.append(url)
            return url, RANKING_FIXTURE

        collector = GlowpickRankingCollector(
            config={"allow_live_fetch": True},
            fetcher=fetcher,
        )
        items = collector.collect(SOURCE)

        self.assertEqual(fetched, [GlowpickRankingCollector.DEFAULT_URL])
        self.assertEqual(len(items), 2)
        first = items[0]
        self.assertEqual(first["rating"], 4.37)
        self.assertEqual(first["review_count"], 1234)
        self.assertEqual(first["rating_provenance"]["source"], collector.AGGREGATE_PROVENANCE)
        self.assertEqual(first["review_count_provenance"]["platform"], "glowpick")
        self.assertFalse(first["rating_provenance"]["market_truth_claimed"])
        self.assertTrue(first["platform_specific"])
        self.assertTrue(first["promotion_sensitive"])
        self.assertTrue(first["experience_review_sensitive"])
        self.assertFalse(first["universal_trend_claimed"])
        self.assertFalse(first["market_truth_claimed"])
        self.assertFalse(first["individual_review_text_collected"])
        self.assertFalse(first["ai_summary_text_collected"])
        for missing_field in ("views", "likes", "sales", "reviews", "inventory", "published_at"):
            self.assertIsNone(first[missing_field])
        self.assertEqual(first["collection_method"], "glowpick_public_ranking")
        self.assertFalse(first["is_fallback"])
        self.assertTrue(collector.last_status["success"])

    def test_disabled_live_returns_honest_empty_without_fetch(self):
        def forbidden_fetcher(_url):
            self.fail("disabled collector must not fetch")

        collector = GlowpickRankingCollector(fetcher=forbidden_fetcher)
        collector._load_cache = lambda _source: []

        self.assertEqual(collector.collect(SOURCE), [])
        self.assertFalse(collector.last_status["success"])
        self.assertEqual(
            collector.last_status["failed_reason"],
            GlowpickRankingCollector.LIVE_REJECTION_REASON,
        )
        self.assertEqual(
            collector.last_status["collection_method"],
            "glowpick_ranking_no_data",
        )
        self.assertFalse(collector.last_status["used_cache"])
        self.assertFalse(collector.last_status["universal_trend_claimed"])

    def test_fetch_failure_uses_fresh_read_only_cache(self):
        cache_payload = {
            "updated_at": datetime.now().astimezone().isoformat(),
            "items": [
                {
                    "category_scope": "립 메이크업",
                    "rank": 1,
                    "list_position": 1,
                    "rank_basis": "visible_glowpick_rank",
                    "brand": "캐시브랜드",
                    "product_title": "립 틴트",
                    "link": "https://www.glowpick.com/products/201",
                    "rating": 4.1,
                    "review_count": 88,
                    "visible_price_text": None,
                    "visible_volume_text": "3 g",
                    "award_labels": [],
                    "aggregate_labels": [],
                }
            ],
        }
        collector = GlowpickRankingCollector(
            config={"allow_live_fetch": True},
            fetcher=lambda _url: (_ for _ in ()).throw(TimeoutError("offline")),
        )

        with mock.patch.object(Path, "exists", return_value=True), mock.patch.object(
            Path,
            "read_text",
            return_value=json.dumps(cache_payload, ensure_ascii=False),
        ):
            items = collector.collect(SOURCE)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "캐시브랜드 립 틴트")
        self.assertTrue(items[0]["is_fallback"])
        self.assertTrue(collector.last_status["success"])
        self.assertTrue(collector.last_status["used_cache"])
        self.assertEqual(collector.last_status["fallback_reason"], "timeout")
        self.assertEqual(collector.last_status["collection_method"], "glowpick_ranking_cache")


if __name__ == "__main__":
    unittest.main()
