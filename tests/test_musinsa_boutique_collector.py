import unittest

from modules.trend_collector.musinsa_boutique_collector import (
    MusinsaBoutiqueCollector,
)


BOUTIQUE_FIXTURE = """
<ul class="boutique-list">
  <li data-rank="4" data-brand-name="Luxury A" data-goods-name="Structured Bag"
      data-category="Bag">
    <a href="/products/4100"><span class="price">2,900,000원</span></a>
  </li>
  <li data-brand-name="Luxury B" data-goods-name="Tailored Jacket">
    <a href="https://www.musinsa.com/products/4200"></a>
  </li>
</ul>
"""

CURRENT_PUBLIC_SHELL_FIXTURE = """
<html><body><div id="__next"></div>
<script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"vertical":"boutique","recommend":{}}},"page":"/main/boutique/recommend"}
</script></body></html>
"""

SOURCE = {
    "source_id": "wrong_caller_id",
    "name": "MUSINSA Boutique",
    "url": MusinsaBoutiqueCollector.DEFAULT_URL,
    "type": "fashion_reference",
}


class TestMusinsaBoutiqueCollector(unittest.TestCase):
    def test_visible_metadata_keeps_explicit_rank_separate_from_list_position(self):
        collector = MusinsaBoutiqueCollector(max_items=10)

        rows = collector.parse_public_boutique_list(BOUTIQUE_FIXTURE)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["rank"], 4)
        self.assertEqual(rows[0]["list_position"], 1)
        self.assertEqual(rows[0]["rank_basis"], "visible_platform_rank")
        self.assertEqual(rows[0]["brand"], "Luxury A")
        self.assertEqual(rows[0]["category_scope"], "Bag")
        self.assertEqual(rows[0]["visible_price_text"], "2,900,000원")
        self.assertIsNone(rows[1]["rank"])
        self.assertEqual(rows[1]["list_position"], 2)
        self.assertEqual(rows[1]["rank_basis"], "platform_list_order_only")

    def test_collect_labels_luxury_reference_without_equivalence_claims(self):
        collector = MusinsaBoutiqueCollector(
            config={"allow_live_fetch": True},
            fetcher=lambda url: (url, BOUTIQUE_FIXTURE),
        )

        items = collector.collect(SOURCE)

        self.assertEqual(len(items), 2)
        first = items[0]
        self.assertEqual(first["source_id"], "musinsa_boutique")
        self.assertEqual(first["source_role"], "luxury_reference")
        self.assertEqual(first["vertical"], "fashion")
        self.assertEqual(first["signal_scope"], "platform_specific")
        self.assertFalse(first["universal_trend_claimed"])
        self.assertFalse(first["exact_match_claimed"])
        self.assertFalse(first["dupe_equivalence_claimed"])
        self.assertFalse(first["authentic_use_equivalence_claimed"])
        self.assertIsNone(first["views"])
        self.assertIsNone(first["likes"])
        self.assertIsNone(first["sales"])
        self.assertEqual(first["collection_method"], "musinsa_boutique_public_list")
        self.assertFalse(first["is_fallback"])

    def test_disabled_live_is_nonfatal_and_does_not_fetch(self):
        calls = []

        def forbidden_fetch(url):
            calls.append(url)
            raise AssertionError("fetch must stay disabled")

        collector = MusinsaBoutiqueCollector(fetcher=forbidden_fetch)
        collector._load_cache = lambda _source: []

        self.assertEqual(collector.collect(SOURCE), [])
        self.assertEqual(calls, [])
        self.assertFalse(collector.last_status["success"])
        self.assertEqual(
            collector.last_status["failed_reason"],
            MusinsaBoutiqueCollector.LIVE_REJECTION_REASON,
        )
        self.assertEqual(collector.last_status["source_role"], "luxury_reference")
        self.assertEqual(collector.last_status["vertical"], "fashion")
        self.assertFalse(collector.last_status["universal_trend_claimed"])

    def test_current_public_shell_without_products_is_reported_honestly(self):
        collector = MusinsaBoutiqueCollector(
            max_items=3,
            config={"allow_live_fetch": True},
            fetcher=lambda url: (url, CURRENT_PUBLIC_SHELL_FIXTURE),
        )

        self.assertEqual(collector.collect(SOURCE), [])
        self.assertEqual(
            collector.last_status["failed_reason"],
            MusinsaBoutiqueCollector.PUBLIC_SHELL_REASON,
        )
        self.assertEqual(collector.last_status["count"], 0)


if __name__ == "__main__":
    unittest.main()
