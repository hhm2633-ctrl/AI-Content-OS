import unittest

from modules.brandconnect.brandconnect_product_catalog import normalize_brandconnect_catalog
from modules.brandconnect.catalog_function_relation_builder import build_catalog_function_relations


class CatalogFunctionRelationBuilderTests(unittest.TestCase):
    def test_builds_observable_function_relations_without_commercial_actions(self):
        products = normalize_brandconnect_catalog({"products": [
            {"product_id": "S", "name": "두피 케어 샴푸", "category": "화장품/미용"},
            {"product_id": "B", "name": "앞머리 뿌리볼륨 헤어스프레이", "category": "화장품/미용"},
            {"product_id": "H", "name": "아이스 냉감 기능성 반팔 티셔츠", "category": "남성패션"},
            {"product_id": "C", "name": "크롭 윈드브레이커 재킷", "category": "여성패션"},
            {"product_id": "U", "name": "크롭 브라 탑 속옷", "category": "여성패션"},
            {"product_id": "X", "name": "알카라인 건전지", "category": "생활/건강"},
        ]})["products"]
        result = build_catalog_function_relations(products)
        self.assertEqual(set(result["relations"]), {"S", "B", "H", "C"})
        self.assertIn("hair_shampoo_cleanse", result["relations"]["S"]["profile_ids"])
        self.assertIn("hair_humidity_hold", result["relations"]["B"]["profile_ids"])
        self.assertIn("fashion_heat_cooling", result["relations"]["H"]["profile_ids"])
        self.assertIn("fashion_crop_layer", result["relations"]["C"]["profile_ids"])
        self.assertTrue(all(len(row["short_story"]) < 30 for row in result["story_rows"]))
        self.assertFalse(result["network_used"])
        self.assertFalse(result["link_issuance"])
        self.assertFalse(result["publishing"])


if __name__ == "__main__":
    unittest.main()
