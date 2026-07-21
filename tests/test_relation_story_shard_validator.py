import json
import unittest
import uuid
from pathlib import Path

from modules.brandconnect.relation_story_shard_validator import (
    validate_relation_story_shard,
    run_relation_story_shard_validation,
)


BEAUTY_SHARD = Path("artifacts/brandconnect_relation_learning_2026-07-18/beauty_story_relations.jsonl")
BEAUTY_REPORT = Path("artifacts/brandconnect_relation_learning_2026-07-18/beauty_story_report.json")
FIXTURE_ROOT = Path("tests/.tmp_relation_shard_validator")


def _fixture_path(name: str) -> Path:
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    return FIXTURE_ROOT / f"{name}_{uuid.uuid4().hex}.json"


def _cleanup(paths):
    for path in paths:
        if path.exists():
            path.unlink()


def _write_jsonl(path: Path, rows):
    text = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    path.write_text(text, encoding="utf-8")


def _row_template(product_id="P-1", short_story="짧은 스토리"):
    return {
        "product_id": product_id,
        "product_name": "테스트 제품",
        "derived_terms": ["term"],
        "season_context": "봄",
        "practical_topic": "계절별 유지",
        "short_story": short_story,
        "product_role": "피부 관리용",
        "blog_seed": "블로그 seed",
        "confidence": 0.9,
        "fallback_used": False,
    }


def _lifestyle_row_template(product_id="P-1", short_story="짧은 스토리"):
    return {
        "product_id": product_id,
        "product_name": "테스트 제품",
        "derived_terms": ["term"],
        "season_context": {
            "best_context": "출근·등교 전",
            "context_type": "daily_environment",
            "best_window": "연중",
        },
        "practical_topic": "출근 전 5분 루틴으로 이어지는 가벼운 시작",
        "short_story": short_story,
        "product_role": "일상 루틴에서 후보를 잇는 역할",
        "blog_seed": {
            "title": "출근 전 가벼운 일상 루틴",
            "angle": "일상 장면에서 시작 동선을 정리하는 소재",
            "status": "future_blog_seed_not_publish_draft",
        },
        "confidence": 0.9,
        "fallback_used": False,
    }


def _write_minimal_report(path: Path, overrides=None):
    payload = {
        "schema_version": "x",
        "product_count": 1,
        "story_count": 1,
        "practical_topic_count": 1,
        "under_30_violation_count": 0,
        "duplicate_story_count": 0,
        "empty_practical_topic_count": 0,
        "missing_required_field_count": 0,
        "product_id_coverage_valid": True,
        "valid": True,
    }
    if overrides:
        payload.update(overrides)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class RelationStoryShardValidatorTests(unittest.TestCase):
    def test_beauty_sample_is_valid_and_matches_report_counts(self):
        result = validate_relation_story_shard(shard_path=str(BEAUTY_SHARD), report_path=str(BEAUTY_REPORT))
        self.assertTrue(result["valid"])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["row_count"], result["metrics"]["product_count"])
        self.assertTrue(result["metrics"]["report_count_agreement"])

    def test_run_relation_story_shard_validation_alias_exists(self):
        result = run_relation_story_shard_validation(shard_path=str(BEAUTY_SHARD), report_path=str(BEAUTY_REPORT))
        self.assertIn("schema_version", result)

    def test_duplicate_product_ids_are_rejected(self):
        shard_path = _fixture_path("duplicate_product")
        report_path = _fixture_path("duplicate_report")
        _write_jsonl(
            shard_path,
            [_row_template("P-1", "스토리1"), _row_template("P-1", "스토리2")],
        )
        _write_minimal_report(
            report_path,
            {
                "product_count": 2,
                "story_count": 2,
                "practical_topic_count": 2,
                "under_30_violation_count": 0,
                "duplicate_story_count": 0,
                "empty_practical_topic_count": 0,
                "missing_required_field_count": 0,
            },
        )
        try:
            result = validate_relation_story_shard(shard_path=str(shard_path), report_path=str(report_path))
            self.assertFalse(result["valid"])
            self.assertEqual(result["status"], "invalid")
            self.assertTrue(any(error.get("code") == "duplicate_product_id" for error in result["errors"]))
        finally:
            _cleanup([shard_path, report_path])

    def test_short_story_length_constraint_is_enforced(self):
        shard_path = _fixture_path("long_short_story")
        report_path = _fixture_path("long_short_story_report")
        _write_jsonl(shard_path, [_row_template("P-1", "a" * 30)])
        _write_minimal_report(
            report_path,
            {
                "product_count": 1,
                "story_count": 1,
                "practical_topic_count": 1,
                "under_30_violation_count": 1,
            },
        )
        try:
            result = validate_relation_story_shard(shard_path=str(shard_path), report_path=str(report_path))
            self.assertFalse(result["valid"])
            self.assertIn("short_story_too_long", {item["code"] for item in result["errors"]})
        finally:
            _cleanup([shard_path, report_path])

    def test_report_mismatch_is_detected(self):
        shard_path = _fixture_path("report_mismatch")
        report_path = _fixture_path("report_mismatch_report")
        _write_jsonl(shard_path, [_row_template("P-1", "스토리")])
        _write_minimal_report(
            report_path,
            {
                "product_count": 2,
                "story_count": 1,
                "practical_topic_count": 1,
                "under_30_violation_count": 0,
            },
        )
        try:
            result = validate_relation_story_shard(shard_path=str(shard_path), report_path=str(report_path))
            self.assertFalse(result["valid"])
            self.assertTrue(any(error.get("code") == "report_count_mismatch" for error in result["errors"]))
        finally:
            _cleanup([shard_path, report_path])

    def test_invalid_rows_do_not_crash_validator(self):
        shard_path = _fixture_path("parse_error")
        report_path = _fixture_path("parse_error_report")
        shard_path.write_text("{not valid json}\n", encoding="utf-8")
        _write_minimal_report(report_path, {"product_count": 1})
        try:
            result = validate_relation_story_shard(shard_path=str(shard_path), report_path=str(report_path))
            self.assertFalse(result["valid"])
            self.assertTrue(any(error["code"] == "jsonl_parse_error" for error in result["errors"]))
        finally:
            _cleanup([shard_path, report_path])

    def test_lifestyle_field_shapes_and_report_key_aliases(self):
        shard_path = _fixture_path("lifestyle_shape")
        report_path = _fixture_path("lifestyle_shape_report")
        _write_jsonl(shard_path, [_lifestyle_row_template("P-1", "아침 루틴, 출근은 가벼운 가글 점검·0001")])
        _write_minimal_report(
            report_path,
            {
                "product_count": 1,
                "story_count": 1,
                "practical_topic_count": 1,
                "under_30_violations": 0,
                "duplicate_short_story_count": 0,
                "missing_required_field_rows": 0,
                "source_product_count": 1,
                "source_id_coverage": True,
                "validation": {"result": "PASS"},
            },
        )
        try:
            result = validate_relation_story_shard(shard_path=str(shard_path), report_path=str(report_path))
            self.assertTrue(result["valid"])
            self.assertEqual(result["status"], "ok")
            self.assertTrue(result["metrics"]["report_count_agreement"])
            self.assertEqual(result["metrics"]["product_count"], 1)
        finally:
            _cleanup([shard_path, report_path])


if __name__ == "__main__":
    unittest.main()
