import copy
import unittest

from modules.source_intake.collection_quality_assessor import (
    STATUS_EMPTY,
    STATUS_LIMITED,
    STATUS_USABLE_SHALLOW,
    assess_collection_quality,
)


def _item(index, **overrides):
    item = {
        "title": f"item {index}",
        "link": f"https://example.com/{index}",
        "source_id": f"source_{index % 2}",
        "is_fallback": False,
        "summary": "visible summary",
        "publisher": "publisher",
        "published_at": "2026-07-15 10:00",
        "views": index,
        "comments": index,
        "likes": index,
        "dislikes": None,
    }
    item.update(overrides)
    return item


class TestCollectionQualityAssessor(unittest.TestCase):
    def test_empty_input_is_empty_and_honest(self):
        result = assess_collection_quality([])
        self.assertEqual(result["status"], STATUS_EMPTY)
        self.assertEqual(result["item_count"], 0)
        self.assertFalse(result["cardnews_readiness_claimed"])
        self.assertFalse(result["factual_verification_claimed"])

    def test_complete_live_items_are_usable_shallow(self):
        result = assess_collection_quality([_item(i) for i in range(5)])
        self.assertEqual(result["status"], STATUS_USABLE_SHALLOW)
        self.assertEqual(result["usable_shallow_item_count"], 5)
        self.assertEqual(result["usable_shallow_ratio"], 1.0)
        self.assertEqual(result["source_count"], 2)

    def test_all_fallback_items_are_limited(self):
        result = assess_collection_quality(
            [_item(1, is_fallback=True), _item(2, is_fallback=True)]
        )
        self.assertEqual(result["status"], STATUS_LIMITED)
        self.assertEqual(result["fallback_ratio"], 1.0)
        self.assertEqual(result["usable_shallow_item_count"], 0)

    def test_mixed_items_report_ratios_without_overclaim(self):
        items = [_item(i) for i in range(4)]
        items[0]["is_fallback"] = True
        result = assess_collection_quality(items)
        self.assertEqual(result["fallback_ratio"], 0.25)
        self.assertEqual(result["usable_shallow_ratio"], 0.75)
        self.assertEqual(result["status"], STATUS_LIMITED)

    def test_missing_required_fields_reduce_usable_count(self):
        result = assess_collection_quality(
            [_item(1), _item(2, link=""), _item(3, source_id="")]
        )
        self.assertEqual(result["usable_shallow_item_count"], 1)
        self.assertEqual(
            result["required_field_completeness"]["link"]["missing"], 1
        )
        self.assertEqual(
            result["required_field_completeness"]["source_id"]["missing"], 1
        )

    def test_missing_metrics_are_unavailable_not_zero(self):
        result = assess_collection_quality(
            [_item(1, views=None, comments=None, likes=None, dislikes=None)]
        )
        for field in ("views", "comments", "likes", "dislikes"):
            self.assertEqual(
                result["visible_metric_availability"][field]["available"], 0
            )
            self.assertEqual(
                result["visible_metric_availability"][field]["missing"], 1
            )

    def test_existing_metric_aliases_count_as_visible(self):
        item = _item(1, comments=None, likes=None)
        item["comment_count"] = 7
        item["recommend_count"] = 3
        result = assess_collection_quality([item])
        self.assertEqual(
            result["visible_metric_availability"]["comments"]["available"], 1
        )
        self.assertEqual(
            result["visible_metric_availability"]["likes"]["available"], 1
        )

    def test_nested_visible_metrics_count_as_available(self):
        item = _item(
            1,
            views=None,
            comments=None,
            likes=None,
            dislikes=None,
            visible_metrics={
                "views": 3588,
                "comments": 40,
                "likes": 62,
                "dislikes": None,
            },
        )
        result = assess_collection_quality([item])
        self.assertEqual(
            result["visible_metric_availability"]["views"]["available"], 1
        )
        self.assertEqual(
            result["visible_metric_availability"]["comments"]["available"], 1
        )
        self.assertEqual(
            result["visible_metric_availability"]["likes"]["available"], 1
        )
        self.assertEqual(
            result["visible_metric_availability"]["dislikes"]["missing"], 1
        )

    def test_nested_explicit_zero_is_available_without_fabrication(self):
        item = _item(
            1,
            views=None,
            comments=None,
            likes=None,
            dislikes=None,
            visible_metrics={"comments": 0},
        )
        result = assess_collection_quality([item])
        self.assertEqual(
            result["visible_metric_availability"]["comments"]["available"], 1
        )
        self.assertEqual(
            result["visible_metric_availability"]["views"]["available"], 0
        )

    def test_malformed_nested_visible_metrics_stay_missing(self):
        item = _item(
            1,
            views=None,
            comments=None,
            likes=None,
            dislikes=None,
            visible_metrics="not-a-dict",
        )
        result = assess_collection_quality([item])
        for field in ("views", "comments", "likes", "dislikes"):
            self.assertEqual(
                result["visible_metric_availability"][field]["available"], 0
            )

    def test_malformed_rows_fail_closed(self):
        result = assess_collection_quality([None, "bad", _item(1)])
        self.assertEqual(result["item_count"], 1)
        self.assertEqual(result["malformed_item_count"], 2)

    def test_input_is_not_mutated(self):
        items = [_item(1)]
        source_results = [{"source_id": "source_0", "success": True}]
        expected_items = copy.deepcopy(items)
        expected_results = copy.deepcopy(source_results)
        assess_collection_quality(items, source_results)
        self.assertEqual(items, expected_items)
        self.assertEqual(source_results, expected_results)


if __name__ == "__main__":
    unittest.main()
