import json
import unittest
from unittest import mock

from modules.trend_collector.musinsa_monthly_ranking_collector import (
    MusinsaMonthlyRankingCollector,
)


def musinsa_json_fixture():
    payload = {
        "items": [
            {
                "rank": 1,
                "brandName": "브랜드A",
                "goodsName": "오버핏 셔츠",
                "goodsLinkUrl": "/products/1001",
                "period": "2026-07",
                "gender": "전체",
                "category": "상의",
                "basisLabel": "MUSINSA 2026-07 월간 랭킹",
            },
            {
                "goodsName": "누락 필드 테스트 팬츠",
                "goodsLinkUrl": "https://www.musinsa.com/products/1002",
            },
        ]
    }
    return json.dumps(payload, ensure_ascii=False)


CURRENT_PUBLIC_SHELL_FIXTURE = """
<html><body><div id="__next"></div>
<script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"vertical":"musinsa","ranking":{}}},"page":"/main/musinsa/ranking"}
</script></body></html>
"""


class TestMusinsaMonthlyRankingCollector(unittest.TestCase):
    def setUp(self):
        self.source = {
            "source_id": "musinsa_monthly_ranking",
            "name": "MUSINSA",
            "url": "https://www.musinsa.com/main/musinsa/ranking",
            "type": "platform_ranking",
        }
        self.no_cache = "tests/_nonexistent_musinsa_monthly_cache.json"

    def test_parser_preserves_explicit_platform_monthly_ranking_metadata(self):
        collector = MusinsaMonthlyRankingCollector(max_items=10)

        rows = collector.parse_public_monthly_ranking(musinsa_json_fixture())

        self.assertEqual(len(rows), 2)
        first = rows[0]
        self.assertEqual(first["period"], "2026-07")
        self.assertEqual(first["gender_scope"], "전체")
        self.assertEqual(first["category_scope"], "상의")
        self.assertEqual(first["rank_position"], 1)
        self.assertEqual(first["brand"], "브랜드A")
        self.assertEqual(first["item_title"], "오버핏 셔츠")
        self.assertEqual(first["link"], "https://www.musinsa.com/products/1001")
        self.assertEqual(first["ranking_basis_label"], "MUSINSA 2026-07 월간 랭킹")
        self.assertEqual(first["missing_fields"], [])

    def test_parser_marks_missing_rank_scope_brand_and_basis_without_inference(self):
        collector = MusinsaMonthlyRankingCollector(max_items=10)
        missing_fixture = json.dumps(
            {
                "items": [
                    {
                        "goodsName": "누락 필드 테스트 팬츠",
                        "goodsLinkUrl": "https://www.musinsa.com/products/1002",
                    }
                ]
            },
            ensure_ascii=False,
        )

        second = collector.parse_public_monthly_ranking(missing_fixture)[0]

        self.assertIsNone(second["rank_position"])
        self.assertIsNone(second["brand"])
        self.assertIsNone(second["period"])
        self.assertIsNone(second["gender_scope"])
        self.assertIsNone(second["category_scope"])
        self.assertIsNone(second["ranking_basis_label"])
        self.assertCountEqual(
            second["missing_fields"],
            [
                "period",
                "gender_scope",
                "category_scope",
                "rank_position",
                "brand",
                "ranking_basis_label",
            ],
        )

    def test_disabled_live_returns_honest_empty_without_fetch(self):
        fetcher = mock.Mock(side_effect=AssertionError("network must remain disabled"))
        collector = MusinsaMonthlyRankingCollector(
            config={"cache_path": self.no_cache},
            fetcher=fetcher,
        )

        items = collector.collect(self.source)

        self.assertEqual(items, [])
        fetcher.assert_not_called()
        self.assertFalse(collector.last_status["success"])
        self.assertEqual(
            collector.last_status["failed_reason"],
            MusinsaMonthlyRankingCollector.LIVE_REJECTION_REASON,
        )
        self.assertEqual(
            collector.last_status["collection_method"],
            "musinsa_monthly_ranking_no_data",
        )
        self.assertEqual(collector.last_status["service_diagnostic"]["status"], "fallback_used")
        self.assertFalse(collector.last_status["universal_trend_claimed"])

    def test_injected_fetcher_parser_preserve_platform_scope_and_honesty(self):
        fetcher = mock.Mock(return_value=(self.source["url"], "fixture"))
        parser = mock.Mock(
            return_value=[
                {
                    "period": "2026-07",
                    "gender_scope": "여성",
                    "category_scope": "아우터",
                    "rank_position": 3,
                    "brand": "브랜드B",
                    "item_title": "라이트 재킷",
                    "link": "https://www.musinsa.com/products/2003",
                    "ranking_basis_label": "MUSINSA 월간 랭킹",
                }
            ]
        )
        collector = MusinsaMonthlyRankingCollector(
            config={"allow_live_fetch": True, "cache_path": self.no_cache},
            fetcher=fetcher,
            parser=parser,
        )

        items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        fetcher.assert_called_once()
        parser.assert_called_once_with("fixture")
        item = items[0]
        self.assertEqual(item["rank_position"], 3)
        self.assertEqual(item["ranking_scope"], "platform_specific_monthly_ranking")
        self.assertEqual(item["platform_specific_basis_label"], "MUSINSA 월간 랭킹")
        self.assertFalse(item["universal_trend_claimed"])
        self.assertIsNone(item["views"])
        self.assertIsNone(item["likes"])
        self.assertIsNone(item["sales"])
        self.assertIsNone(item["publisher"])
        self.assertIsNone(item["published_at"])
        self.assertFalse(item["is_fallback"])
        self.assertTrue(item["collected_at"])

    def test_current_public_shell_without_products_has_exact_fail_closed_reason(self):
        collector = MusinsaMonthlyRankingCollector(
            max_items=3,
            config={"allow_live_fetch": True, "cache_path": self.no_cache},
            fetcher=lambda url: (url, CURRENT_PUBLIC_SHELL_FIXTURE),
        )

        items = collector.collect(self.source)

        self.assertEqual(items, [])
        self.assertEqual(collector.last_status["count"], 0)
        self.assertEqual(
            collector.last_status["failed_reason"],
            MusinsaMonthlyRankingCollector.PUBLIC_SHELL_REASON,
        )
        self.assertEqual(
            collector.last_status["collection_method"],
            "musinsa_monthly_ranking_no_data",
        )
        self.assertFalse(collector.last_status["universal_trend_claimed"])


if __name__ == "__main__":
    unittest.main()
