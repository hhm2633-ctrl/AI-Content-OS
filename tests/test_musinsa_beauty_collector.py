import unittest

from modules.trend_collector.musinsa_beauty_collector import MusinsaBeautyCollector


BEAUTY_FIXTURE = """
<ul class="beauty-list">
  <li data-rank="2" data-brand-name="Beauty A" data-goods-name="Barrier Serum"
      data-category="Skincare">
    <a href="/products/5100"><span class="price">38,000원</span></a>
  </li>
  <li data-brand-name="Beauty B" data-goods-name="Soft Lip Tint">
    <a href="https://www.musinsa.com/products/5200"></a>
  </li>
</ul>
"""

CURRENT_PUBLIC_SHELL_FIXTURE = """
<html><body><div id="__next"></div>
<script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"vertical":"beauty","recommend":{}}},"page":"/main/beauty/recommend"}
</script></body></html>
"""

SOURCE = {
    "source_id": "caller_override_must_not_win",
    "name": "MUSINSA Beauty",
    "url": MusinsaBeautyCollector.DEFAULT_URL,
    "type": "beauty_retail",
}


class TestMusinsaBeautyCollector(unittest.TestCase):
    def test_visible_metadata_keeps_rank_and_page_position_distinct(self):
        collector = MusinsaBeautyCollector(max_items=10)

        rows = collector.parse_public_beauty_list(BEAUTY_FIXTURE)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["rank"], 2)
        self.assertEqual(rows[0]["list_position"], 1)
        self.assertEqual(rows[0]["rank_basis"], "visible_platform_rank")
        self.assertEqual(rows[0]["category_scope"], "Skincare")
        self.assertEqual(rows[0]["visible_price_text"], "38,000원")
        self.assertIsNone(rows[1]["rank"])
        self.assertEqual(rows[1]["list_position"], 2)
        self.assertEqual(rows[1]["rank_basis"], "platform_list_order_only")

    def test_collect_labels_beauty_retail_as_platform_specific_only(self):
        collector = MusinsaBeautyCollector(
            config={"allow_live_fetch": True},
            fetcher=lambda url: (url, BEAUTY_FIXTURE),
        )

        items = collector.collect(SOURCE)

        self.assertEqual(len(items), 2)
        first = items[0]
        self.assertEqual(first["source_id"], "musinsa_beauty")
        self.assertEqual(first["source_role"], "beauty_retail")
        self.assertEqual(first["vertical"], "beauty")
        self.assertEqual(first["signal_scope"], "platform_specific")
        self.assertFalse(first["universal_trend_claimed"])
        self.assertFalse(first["exact_match_claimed"])
        self.assertFalse(first["dupe_equivalence_claimed"])
        self.assertFalse(first["authentic_use_equivalence_claimed"])
        self.assertIsNone(first["views"])
        self.assertIsNone(first["likes"])
        self.assertIsNone(first["sales"])
        self.assertEqual(first["collection_method"], "musinsa_beauty_public_list")
        self.assertFalse(first["is_fallback"])

    def test_disabled_live_is_nonfatal_and_does_not_fetch(self):
        calls = []

        def forbidden_fetch(url):
            calls.append(url)
            raise AssertionError("fetch must stay disabled")

        collector = MusinsaBeautyCollector(fetcher=forbidden_fetch)
        collector._load_cache = lambda _source: []

        self.assertEqual(collector.collect(SOURCE), [])
        self.assertEqual(calls, [])
        self.assertFalse(collector.last_status["success"])
        self.assertEqual(
            collector.last_status["failed_reason"],
            MusinsaBeautyCollector.LIVE_REJECTION_REASON,
        )
        self.assertEqual(collector.last_status["source_role"], "beauty_retail")
        self.assertEqual(collector.last_status["vertical"], "beauty")
        self.assertFalse(collector.last_status["universal_trend_claimed"])

    def test_current_public_shell_without_products_is_reported_honestly(self):
        collector = MusinsaBeautyCollector(
            max_items=3,
            config={"allow_live_fetch": True},
            fetcher=lambda url: (url, CURRENT_PUBLIC_SHELL_FIXTURE),
        )

        self.assertEqual(collector.collect(SOURCE), [])
        self.assertEqual(
            collector.last_status["failed_reason"],
            MusinsaBeautyCollector.PUBLIC_SHELL_REASON,
        )
        self.assertEqual(collector.last_status["count"], 0)


if __name__ == "__main__":
    unittest.main()
