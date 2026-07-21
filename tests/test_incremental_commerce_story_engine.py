"""Focused tests for the incremental commerce story engine."""

import json
import os
import tempfile
import unittest

from modules.brandconnect.incremental_commerce_story_engine import (
    build_candidate_story_briefs,
    ingest_relation_shard,
    ingested_categories,
    iter_jsonl_file,
    new_engine_state,
)

BEAUTY_ROWS = [
    {
        "product_id": "B-1",
        "product_name": "치크&아이 풀세트",
        "season_context": "겨울, 실내외 온도 차가 큰 아침",
        "practical_topic": "혈색을 정돈하는 방법",
        "short_story": "겨울 아침, 혈색 한 점",
        "product_role": "겨울 포인트 메이크업에 치크·색조 제품으로 연결",
        "blog_seed": "겨울 아침 혈색 정돈 정보형 글",
        "confidence": 0.9,
        "fallback_used": False,
    },
    {"product_id": "", "product_name": "무효 상품"},
]

LIFESTYLE_ROWS = [
    {
        "product_id": "L-1",
        "product_name": "쿨민트 가글 1L",
        "season_context": {
            "best_context": "출근·등교 전 매일 아침",
            "relation_reason": "구강 관리 용도를 반복되는 아침 상황과 연결",
        },
        "practical_topic": "아침·외출 전 가글 구강 루틴",
        "short_story": "약속 전, 가글 자리를 살폈다",
        "product_role": "구강 콘텐츠 연결 상품 후보",
        "blog_seed": {
            "title": "아침 가글 루틴",
            "status": "future_blog_seed_not_publish_draft",
            "boundary": "no personal-use, purchase, price, stock, review, or efficacy claim",
        },
        "confidence": 0.86,
        "fallback_used": False,
    }
]

FASHION_ROWS = [
    {
        "product_id": "F-1",
        "product_name": "쿨링 무지 반팔 티셔츠",
        "derived_terms": ["패션의류", "여름", "셔츠"],
        "season_context": {
            "season": "여름",
            "month_range": "6~8월",
            "weather": "더위·강한 햇빛",
            "temperature": "25°C 이상",
            "humidity": "높음",
            "daily_environment": "출퇴근·야외활동",
            "selection_basis": "상품명의 '쿨' 신호",
        },
        "practical_topic": "셔츠 한 장의 세 가지 장면 스타일링",
        "short_story": "여름 아침, 셔츠 한 장",
        "product_role": "여름 코디 콘텐츠에 셔츠 제품으로 연결",
        "blog_seed": {
            "seed_title": "여름 쿨링 티셔츠 스타일링",
            "story_hook": "더운 출근길",
            "outline": ["장면", "선택 기준"],
            "claim_boundary": "no personal-use or performance claim",
        },
        "confidence": 0.8,
        "fallback_used": True,
    }
]

FASHION_REPORT = {
    "schema_version": "brandconnect_fashion_story_report_v1",
    "output_row_count": 1,
    "validation": {"source_id_coverage": True, "counts_agree": True, "valid_jsonl": True},
}


def seeded_state():
    state = new_engine_state()
    ingest_relation_shard(state, "beauty:2026-07-18", "beauty", BEAUTY_ROWS)
    ingest_relation_shard(state, "lifestyle:2026-07-18", "lifestyle", LIFESTYLE_ROWS)
    return state


class IngestTest(unittest.TestCase):
    def test_beauty_and_lifestyle_shapes_normalize(self):
        state = seeded_state()
        beauty = state["products"]["B-1"]
        self.assertEqual(beauty["relation_reason_source"], "product_role")
        self.assertEqual(beauty["relation_reason"], "겨울 포인트 메이크업에 치크·색조 제품으로 연결")
        self.assertEqual(beauty["season_context"], "겨울, 실내외 온도 차가 큰 아침")
        lifestyle = state["products"]["L-1"]
        self.assertEqual(lifestyle["relation_reason_source"], "explicit")
        self.assertEqual(lifestyle["relation_reason"], "구강 관리 용도를 반복되는 아침 상황과 연결")
        self.assertEqual(lifestyle["season_context"], "출근·등교 전 매일 아침")
        self.assertEqual(lifestyle["blog_seed"]["title"], "아침 가글 루틴")
        self.assertEqual(ingested_categories(state), ["beauty", "lifestyle"])

    def test_completed_shard_is_never_reprocessed(self):
        state = seeded_state()
        before = dict(state["products"])
        summary = ingest_relation_shard(state, "beauty:2026-07-18", "beauty", BEAUTY_ROWS)
        self.assertEqual(summary["status"], "already_completed")
        self.assertEqual(summary["accepted"], 0)
        self.assertEqual(state["products"], before)

    def test_malformed_rows_dropped_with_reasons(self):
        state = new_engine_state()
        rows = [json.dumps(BEAUTY_ROWS[0], ensure_ascii=False), "not-json", 42, {"product_name": "no id"}]
        summary = ingest_relation_shard(state, "s1", "beauty", rows)
        self.assertEqual(summary["accepted"], 1)
        self.assertEqual(
            sorted(d["reason"] for d in summary["dropped"]),
            ["invalid_json", "malformed_row", "missing_product_id_or_name"],
        )

    def test_invalid_report_rejects_shard(self):
        state = new_engine_state()
        summary = ingest_relation_shard(state, "s1", "beauty", BEAUTY_ROWS, report={"valid": False})
        self.assertEqual(summary["status"], "rejected_invalid_report")
        self.assertEqual(state["products"], {})

    def test_report_count_agreement_recorded(self):
        state = new_engine_state()
        summary = ingest_relation_shard(
            state, "s1", "beauty", BEAUTY_ROWS, report={"valid": True, "product_count": 2}
        )
        self.assertTrue(summary["report_count_match"])

    def test_generator_uniqueness_suffix_is_not_reader_facing_copy(self):
        state = new_engine_state()
        row = dict(BEAUTY_ROWS[0], short_story="겨울 아침, 혈색 한 점·27")
        ingest_relation_shard(state, "s1", "beauty", [row])
        self.assertEqual(state["products"]["B-1"]["short_story"], "겨울 아침, 혈색 한 점")

    def test_streams_jsonl_file_without_full_load(self):
        state = new_engine_state()
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "shard.jsonl")
            with open(path, "w", encoding="utf-8") as handle:
                for row in LIFESTYLE_ROWS:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.write("broken-line\n")
            summary = ingest_relation_shard(state, "s1", "lifestyle", iter_jsonl_file(path))
        self.assertEqual(summary["accepted"], 1)
        self.assertEqual(summary["dropped"][0]["reason"], "invalid_json")


class CandidateBriefTest(unittest.TestCase):
    CANDIDATES = [
        {"candidate_id": "C-1", "title": "겨울 혈색 메이크업", "matches": [{"product_id": "B-1"}]},
        {"candidate_id": "C-2", "title": "여름 셔츠 코디", "matches": [{"product_id": "F-1"}]},
    ]

    def test_briefs_are_traceable_and_supplied_only(self):
        result = build_candidate_story_briefs(seeded_state(), self.CANDIDATES)
        ready = result["candidates"][0]
        self.assertEqual(ready["status"], "ready")
        brief = ready["briefs"][0]
        self.assertEqual(brief["source_shard"], "beauty:2026-07-18")
        self.assertEqual(brief["category"], "beauty")
        self.assertEqual(brief["row_index"], 0)
        self.assertFalse(brief["link_issued"])
        for forbidden in ("price", "stock_status", "review_count", "affiliate_link"):
            self.assertNotIn(forbidden, brief)
        self.assertEqual(result["proposal_status"], "future_blog_seeds_not_publish_drafts")
        self.assertFalse(result["network_used"])
        self.assertFalse(result["link_issuance"])
        self.assertFalse(result["publishing"])

    def test_missing_shard_yields_awaiting_not_invented(self):
        result = build_candidate_story_briefs(seeded_state(), self.CANDIDATES)
        waiting = result["candidates"][1]
        self.assertEqual(waiting["status"], "awaiting_shards")
        self.assertEqual(waiting["briefs"], [])
        self.assertEqual(waiting["missing_products"], ["F-1"])

    def test_fashion_variant_schema_normalizes(self):
        state = new_engine_state()
        summary = ingest_relation_shard(state, "fashion:2026-07-18", "fashion", FASHION_ROWS, report=FASHION_REPORT)
        self.assertEqual(summary["status"], "completed")
        self.assertTrue(summary["report_count_match"])
        story = state["products"]["F-1"]
        self.assertEqual(story["relation_reason"], "상품명의 '쿨' 신호")
        self.assertEqual(story["relation_reason_source"], "selection_basis")
        self.assertEqual(story["season_context"], "여름 · 더위·강한 햇빛 · 출퇴근·야외활동")
        self.assertEqual(story["blog_seed"]["seed_title"], "여름 쿨링 티셔츠 스타일링")

    def test_fashion_report_validation_false_rejects(self):
        state = new_engine_state()
        report = {"output_row_count": 1, "validation": {"counts_agree": False}}
        summary = ingest_relation_shard(state, "fashion:bad", "fashion", FASHION_ROWS, report=report)
        self.assertEqual(summary["status"], "rejected_invalid_report")
        self.assertEqual(state["products"], {})

    def test_late_fashion_shard_merges_without_touching_earlier(self):
        state = seeded_state()
        first = build_candidate_story_briefs(state, self.CANDIDATES)
        ingest_relation_shard(state, "fashion:2026-07-19", "fashion", FASHION_ROWS)
        second = build_candidate_story_briefs(state, self.CANDIDATES)
        self.assertEqual(second["candidates"][0], first["candidates"][0])
        self.assertEqual(second["candidates"][1]["status"], "ready")
        self.assertEqual(second["candidates"][1]["briefs"][0]["product_id"], "F-1")
        self.assertEqual(ingested_categories(state), ["beauty", "fashion", "lifestyle"])


if __name__ == "__main__":
    unittest.main()
