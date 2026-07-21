import unittest

from modules.content.commerce_story_content_adapter import (
    build_commerce_story_content_inputs,
)


def _candidate(candidate_id, *, status="ready", briefs=None, missing=None, title=""):
    return {
        "candidate_id": candidate_id,
        "title": title,
        "status": status,
        "briefs": briefs or [],
        "missing_products": missing or [],
    }


def _brief(
    product_id,
    *,
    product_name,
    short_story,
    practical_topic="실사용 루틴 정리",
    category="beauty",
    source_shard="beauty:2026-07-18",
    row_index=0,
    blog_seed=None,
):
    return {
        "product_id": product_id,
        "product_name": product_name,
        "short_story": short_story,
        "practical_topic": practical_topic,
        "product_role": f"{product_name} 연결 문구",
        "season_context": "건조한 날씨",
        "relation_reason": "상황별 사용 포인트",
        "category": category,
        "source_shard": source_shard,
        "row_index": row_index,
        "blog_seed": blog_seed
        or {
            "status": "future_blog_seed_not_publish_draft",
            "topic": "사용 맥락 중심",
            "review_count": 12,
            "stock_status": "매우많음",
            "price": "12000원",
        },
    }


class CommerceStoryContentAdapterTests(unittest.TestCase):
    def test_ready_brief_becomes_card_copy_feed_caption_and_blog_seed(self):
        result = build_commerce_story_content_inputs(
            {
                "schema_version": "candidate_commerce_story_briefs.v1",
                "candidates": [
                    _candidate(
                        "C1",
                        title="건성 피부 케어",
                        briefs=[
                            _brief(
                                "P1",
                                product_name="마일드 토너",
                                short_story="건성 피부를 위한 초간단 1단계 보습",
                            )
                        ],
                    )
                ],
            }
        )
        self.assertEqual(result["status"], "ready")
        first = result["content_candidates"][0]
        self.assertEqual(first["status"], "ready")
        self.assertEqual(len(first["content_inputs"]), 1)

        adapted = first["content_inputs"][0]
        self.assertEqual(adapted["card_copy"]["short_story"], "건성 피부를 위한 초간단 1단계 보습")
        self.assertLess(len(adapted["card_copy"]["short_story"]), 30)
        self.assertEqual(
            adapted["traceability"]["candidate_id"],
            "C1",
        )
        self.assertEqual(adapted["traceability"]["product_id"], "P1")
        self.assertEqual(
            adapted["feed_caption"],
            "마일드 토너 - 건성 피부를 위한 초간단 1단계 보습",
        )

    def test_missing_briefs_are_non_blocking(self):
        result = build_commerce_story_content_inputs(
            {
                "schema_version": "candidate_commerce_story_briefs.v1",
                "candidates": [
                    _candidate(
                        "C2",
                        title="매장 재구매 필요",
                        status="awaiting_shards",
                        briefs=[],
                        missing=["P2"],
                    )
                ],
            }
        )
        self.assertEqual(result["status"], "awaiting_briefs")
        candidate = result["content_candidates"][0]
        self.assertEqual(candidate["status"], "awaiting_shards")
        self.assertEqual(candidate["content_inputs"], [])
        self.assertEqual(candidate["missing_products"], ["P2"])

    def test_forbidden_future_seed_claim_keys_are_dropped(self):
        result = build_commerce_story_content_inputs(
            {
                "schema_version": "candidate_commerce_story_briefs.v1",
                "candidates": [
                    _candidate(
                        "C3",
                        status="ready",
                        title="가격 없는 소개",
                        briefs=[
                            _brief(
                                "P3",
                                product_name="클렌저",
                                short_story="아침 스킨케어 시작",
                                blog_seed={
                                    "title": "초간단 클렌저 가이드",
                                    "stock_status": "out_of_stock",
                                    "price": "무료",
                                    "review_count": 0,
                                    "notes": "이 값은 금지",
                                },
                            )
                        ],
                    )
                ],
            }
        )
        future_seed = result["content_candidates"][0]["content_inputs"][0]["future_blog_seed"]
        self.assertNotIn("stock_status", future_seed)
        self.assertNotIn("price", future_seed)
        self.assertNotIn("review_count", future_seed)
        self.assertEqual(future_seed["title"], "초간단 클렌저 가이드")
        self.assertEqual(future_seed["notes"], "이 값은 금지")

    def test_duplicate_candidates_and_products_attach_once_in_first_seen_order(self):
        result = build_commerce_story_content_inputs(
            {
                "schema_version": "candidate_commerce_story_briefs.v1",
                "candidates": [
                    _candidate(
                        "C1",
                        title="첫 후보",
                        briefs=[
                            _brief("P2", product_name="두 번째 상품", short_story="두 번째 이야기"),
                            _brief("P1", product_name="첫 번째 상품", short_story="첫 번째 이야기"),
                        ],
                        missing=["P3"],
                    ),
                    _candidate(
                        "C2",
                        title="다음 후보",
                        briefs=[_brief("P4", product_name="다음 상품", short_story="다음 이야기")],
                    ),
                    _candidate(
                        "C1",
                        title="중복 후보 제목",
                        briefs=[
                            _brief("P1", product_name="바뀐 이름", short_story="중복 이야기"),
                            _brief("P3", product_name="세 번째 상품", short_story="세 번째 이야기"),
                        ],
                        missing=["P3", "P5"],
                    ),
                ],
            }
        )

        self.assertEqual(
            [item["candidate_id"] for item in result["content_candidates"]],
            ["C1", "C2"],
        )
        first = result["content_candidates"][0]
        self.assertEqual(
            [item["traceability"]["product_id"] for item in first["content_inputs"]],
            ["P2", "P1", "P3"],
        )
        self.assertEqual(first["missing_products"], ["P3", "P5"])
        self.assertEqual(first["duplicate_product_count"], 1)
        self.assertEqual(result["duplicate_candidate_count"], 1)
        self.assertEqual(result["duplicate_product_count"], 1)

    def test_nested_volatile_blog_claims_are_removed_without_inventing_copy(self):
        result = build_commerce_story_content_inputs(
            {
                "schema_version": "candidate_commerce_story_briefs.v1",
                "candidates": [
                    _candidate(
                        "C4",
                        briefs=[
                            _brief(
                                "",
                                product_name="",
                                short_story="비 오는 날의 준비",
                                blog_seed={
                                    "title": "비 오는 날 준비",
                                    "sections": [
                                        {"body": "우산을 챙기는 맥락", "Rating": "5.0"},
                                        {"discount": "50%", "body": "외출 전 확인"},
                                    ],
                                },
                            )
                        ],
                    )
                ],
            }
        )

        adapted = result["content_candidates"][0]["content_inputs"][0]
        self.assertEqual(adapted["feed_caption"], "비 오는 날의 준비")
        self.assertEqual(
            adapted["future_blog_seed"],
            {
                "title": "비 오는 날 준비",
                "sections": [
                    {"body": "우산을 챙기는 맥락"},
                    {"body": "외출 전 확인"},
                ],
            },
        )

    def test_duplicate_candidate_does_not_consume_briefs_from_non_ready_row(self):
        result = build_commerce_story_content_inputs(
            {
                "schema_version": "candidate_commerce_story_briefs.v1",
                "candidates": [
                    _candidate(
                        "C5",
                        status="awaiting_shards",
                        briefs=[_brief("P5", product_name="미승인 상품", short_story="미승인 문구")],
                    ),
                    _candidate("C5", status="awaiting_shards", briefs=[]),
                ],
            }
        )

        candidate = result["content_candidates"][0]
        self.assertEqual(candidate["content_inputs"], [])
        self.assertEqual(candidate["status"], "awaiting_shards")

    def test_ready_duplicate_does_not_revive_non_ready_brief(self):
        result = build_commerce_story_content_inputs(
            {
                "schema_version": "candidate_commerce_story_briefs.v1",
                "candidates": [
                    _candidate(
                        "C6",
                        status="awaiting_shards",
                        briefs=[_brief("P6", product_name="미승인 상품", short_story="미승인 문구")],
                    ),
                    _candidate(
                        "C6",
                        status="ready",
                        briefs=[_brief("P7", product_name="승인 상품", short_story="승인 문구")],
                    ),
                ],
            }
        )

        inputs = result["content_candidates"][0]["content_inputs"]
        self.assertEqual(
            [item["traceability"]["product_id"] for item in inputs],
            ["P7"],
        )

    def test_non_mapping_payload_is_blocked(self):
        result = build_commerce_story_content_inputs("bad input")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason_code"], "malformed_story_briefs")


if __name__ == "__main__":
    unittest.main()
