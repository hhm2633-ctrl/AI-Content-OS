import unittest

from modules.source_intake.collector_readiness_registry import CollectorReadinessRegistry
from modules.source_intake.validated_topic_input_adapter import run_validated_topic_input_adapter


class TestValidatedTopicInputAdapter(unittest.TestCase):
    def test_ready_items_pass_and_non_ready_unknown_source_items_are_filtered_with_diagnostics(self):
        registry = CollectorReadinessRegistry(
            source_statuses={
                "ready_news": "ready",
                "blocked_news": "blocked",
                "partial_news": "partial",
            },
            total_sources=3,
            source_count_sources=3,
        )

        payload = {
            "schema_version": "daily_shallow_collection_v1",
            "items": [
                {
                    "source_id": "ready_news",
                    "source_name": "Ready 뉴스",
                    "source_type": "news",
                    "source_lane_id": "lane-news-01",
                    "keyword": "AI 자동화",
                    "summary": "요약 텍스트",
                    "publisher": "메인 언론사",
                    "collected_at": "2026-07-14T00:00:00.100000",
                    "rank_position": 1,
                    "board_or_category": "테크",
                    "category": "정치",
                    "link": "https://example.com/ready",
                    "published_at": "2026-07-14T00:00:00",
                    "collection_method": "live",
                    "is_fallback": False,
                    "visible_metrics": {
                        "views": 100,
                        "comments": 4,
                        "likes": 12,
                        "dislikes": 1,
                        "scraps": 0,
                        "shares": 3,
                    },
                    "media_flags": {
                        "has_image": True,
                        "has_video": False,
                        "image_count": 2,
                    },
                    "metrics_origin": "parsed",
                    "base_score": 150,
                    "score": 170,
                },
                {
                    "source_id": "blocked_news",
                    "source_name": "Blocked 뉴스",
                    "source_type": "news",
                    "keyword": "제외 대상",
                    "collection_method": "blocked",
                    "is_fallback": False,
                },
                {
                    "source_id": "unknown_news",
                    "source_name": "Unknown",
                    "source_type": "news",
                    "title": "제목 기반 항목",
                    "collection_method": "fallback",
                    "is_fallback": True,
                },
                {
                    "source_id": "ready_news",
                    "source_name": "Ready 뉴스 2",
                    "source_type": "news",
                    "source_lane_id": "lane-news-02",
                    "title": "둘째 준비 항목",
                    "summary": "둘째 요약",
                    "publisher": "메인 언론사",
                    "collected_at": "2026-07-14T00:00:01.200000",
                    "rank_position": 2,
                    "board_or_category": "IT",
                    "link": "https://example.com/ready-2",
                    "collection_method": "live",
                    "is_fallback": False,
                    "base_score": 80,
                },
            ],
        }

        result = run_validated_topic_input_adapter(payload, registry)

        self.assertEqual(len(result["trends"]), 2)
        self.assertEqual(result["trends"][0]["source_id"], "ready_news")
        self.assertEqual(result["trends"][1]["source_id"], "ready_news")
        self.assertEqual(result["trends"][0]["score"], 170.0)
        self.assertEqual(result["trends"][0]["base_score"], 150.0)
        self.assertEqual(result["trends"][1]["score"], 80.0)
        self.assertEqual(result["trends"][1]["base_score"], 80.0)
        self.assertEqual(result["trends"][1]["source_id"], "ready_news")
        self.assertEqual(result["trends"][1]["keyword"], "둘째 준비 항목")
        self.assertEqual(result["trends"][1]["title"], "둘째 준비 항목")
        self.assertEqual(result["trends"][0]["source_lane_id"], "lane-news-01")
        self.assertEqual(result["trends"][0]["rank_position"], 1)
        self.assertEqual(result["trends"][0]["summary"], "요약 텍스트")
        self.assertEqual(result["trends"][0]["publisher"], "메인 언론사")
        self.assertEqual(result["trends"][0]["collected_at"], "2026-07-14T00:00:00.100000")
        self.assertEqual(result["trends"][0]["board_or_category"], "테크")
        self.assertEqual(result["trends"][0]["category"], "정치")
        self.assertEqual(
            result["trends"][0]["visible_metrics"],
            {
                "views": 100,
                "comments": 4,
                "likes": 12,
                "dislikes": 1,
                "scraps": 0,
                "shares": 3,
            },
        )
        self.assertEqual(
            result["trends"][0]["media_flags"],
            {
                "has_image": True,
                "has_video": False,
                "image_count": 2,
            },
        )
        self.assertEqual(result["trends"][0]["metrics_origin"], "parsed")
        self.assertEqual(result["source_diagnostics"]["filtered_count"], 2)
        self.assertIn("source_not_ready", result["source_diagnostics"]["filtered_sources"])
        self.assertIn("unknown_source", result["source_diagnostics"]["filtered_sources"])

    def test_malformed_payload_or_items_fail_closed(self):
        registry = CollectorReadinessRegistry(
            source_statuses={"ready_news": "ready"},
            total_sources=1,
            source_count_sources=1,
        )

        malformed_payload = {"schema_version": "daily_shallow_collection_v1", "not_items": []}
        payload_result = run_validated_topic_input_adapter(malformed_payload, registry)
        self.assertEqual(payload_result["trends"], [])
        self.assertEqual(payload_result["source_diagnostics"]["status"], "closed")
        self.assertEqual(payload_result["source_diagnostics"]["reason_code"], "malformed_items")
        self.assertIn("payload.items", payload_result["source_diagnostics"]["reason"])

        malformed_items = {
            "schema_version": "daily_shallow_collection_v1",
            "items": ["not-a-dict", {"source_id": "ready_news"}],
        }
        item_result = run_validated_topic_input_adapter(malformed_items, registry)
        self.assertEqual(item_result["trends"], [])
        self.assertEqual(item_result["source_diagnostics"]["status"], "closed")
        self.assertEqual(item_result["source_diagnostics"]["reason_code"], "malformed_items")
        self.assertIn("payload.items[0]", item_result["source_diagnostics"]["reason"])

    def test_zero_eligible_items_returns_empty_trends_and_no_fabricated_topic(self):
        registry = CollectorReadinessRegistry(
            source_statuses={
                "blocked_news": "blocked",
                "partial_news": "partial",
            },
            total_sources=2,
            source_count_sources=2,
        )

        payload = {
            "schema_version": "daily_shallow_collection_v1",
            "items": [
                {
                    "source_id": "blocked_news",
                    "source_name": "Blocked",
                    "source_type": "news",
                    "keyword": "블록 대상",
                    "collection_method": "fallback",
                },
                {
                    "source_id": "partial_news",
                    "source_name": "Partial",
                    "source_type": "news",
                    "keyword": "부분 허용",
                    "collection_method": "partial",
                },
            ],
        }

        result = run_validated_topic_input_adapter(payload, registry)

        self.assertEqual(result["trends"], [])
        self.assertEqual(result["source_diagnostics"]["status"], "closed")
        self.assertEqual(result["source_diagnostics"]["reason_code"], "no_ready_items")
        self.assertNotIn("selected_topic", result)

    def test_input_is_not_mutated_when_adapted(self):
        registry = CollectorReadinessRegistry(
            source_statuses={"ready_news": "ready"},
            total_sources=1,
            source_count_sources=1,
        )

        payload = {
            "schema_version": "daily_shallow_collection_v1",
            "items": [
                {
                    "source_id": "ready_news",
                    "source_name": "Ready 뉴스",
                    "source_type": "news",
                    "keyword": "변경 감시",
                    "title": "원본 보존",
                    "base_score": 50,
                    "score": 52,
                },
            ],
        }
        snapshot = {
            "schema_version": payload["schema_version"],
            "items": [dict(item) for item in payload["items"]],
        }

        run_validated_topic_input_adapter(payload, registry)

        self.assertEqual(payload, snapshot)


if __name__ == "__main__":
    unittest.main()
