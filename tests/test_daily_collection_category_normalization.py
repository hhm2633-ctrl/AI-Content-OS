import unittest

from modules.source_intake.daily_collection_executor import _normalize_shallow_item


class DailyCollectionCategoryNormalizationTest(unittest.TestCase):
    def normalize(self, item):
        _normalize_shallow_item(item, [], "2026-07-22T00:00:00+09:00")
        return item

    def test_economy_alias_is_normalized_and_raw_value_is_preserved(self):
        item = self.normalize({"source_id": "mk_economy", "category": "\uacbd\uc81c"})

        self.assertEqual(item["board_or_category"], "economy")
        self.assertEqual(item["board_or_category_raw"], "\uacbd\uc81c")

    def test_category_path_supplies_missing_category(self):
        item = self.normalize({"source_id": "edaily", "category_path": ["market", "stock"]})

        self.assertEqual(item["board_or_category"], "stock")

    def test_source_scope_supplies_conservative_fallbacks(self):
        news = self.normalize({"source_id": "naver_news"})
        economy = self.normalize({"source_id": "edaily"})

        self.assertEqual(news["board_or_category"], "news")
        self.assertEqual(economy["board_or_category"], "economy")


if __name__ == "__main__":
    unittest.main()
