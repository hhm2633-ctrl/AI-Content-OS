import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from modules.card_news.layout_selector import LayoutSelector
from modules.design_learning.owner_source_learning import (
    ANALYSIS_SCHEMA_VERSION,
    MAX_APPROVED_REFERENCE_PROFILES,
    compile_approved_layout_registry,
    prepare_owner_source_batches,
    validate_analysis_record,
)


LAYOUTS = ["notebook", "dark_editorial", "bold_ai", "character_diary", "comparison", "tutorial", "checklist", "timeline", "warning", "number_list"]


def approved_record(asset_id="sha256:" + "a" * 64):
    return {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "asset_id": asset_id,
        "batch_id": "batch_0001_x",
        "evidence_boundary": {"source": "owner_source_screenshot", "is_performance_evidence": False, "reference_only": True},
        "context": {"account_targets": ["account_a", "shared"], "content_categories": ["사건"], "issue_types": ["긴급"], "moods": ["긴장"], "emotional_arc": [], "seasonality": [], "media_conditions": ["image_available"]},
        "design": {"composition": "photo-led", "layout_structure": "fixed", "visual_hierarchy": "headline-first", "image_strategy": "full", "text_density": "low", "spacing": "wide", "decorative_elements": [], "carousel_consistency": "stable"},
        "palette": {"dominant_colors": ["#111111"], "accent_colors": ["#ffcc00"], "background_tone": "dark", "contrast_style": "high", "color_relationship": "complementary"},
        "typography": {"headline_style": "bold", "body_style": "short", "alignment": "left", "emphasis_method": "size", "readability_notes": "mobile"},
        "content_insight": {"topic_summary": "", "body_structure": "", "claims_or_information": [], "hook_style": "", "cta_style": "", "project_help": ["news cover"], "reusable_rules": [], "do_not_copy": []},
        "recommendation": {"profile_id": "news_urgent_dark_01", "fixed_layout_id": "dark_editorial", "reference_scope": "shared", "usage_conditions": ["urgent"], "adaptation_notes": [], "style_overrides": {"highlight_color": "#ffcc00"}, "layout_blueprint": {"canvas_structure": "photo-led", "image_zones": [], "text_zones": [], "reading_order": [], "repeating_elements": [], "role_variants": {}}},
        "approval": {"status": "OWNER_APPROVED", "approved_by": "owner", "approved_at": "2026-07-22T00:00:00+09:00", "owner_feedback_event_id": "owner-1"},
    }


class TestOwnerSourceDesignLearning(unittest.TestCase):
    def test_prepares_at_most_ten_per_batch_without_touching_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, workspace = root / "source", root / "workspace"
            source.mkdir()
            for index in range(12):
                Image.new("RGB", (20 + index, 20), (index, 0, 0)).save(source / f"{index:02d}.png")
            originals = {path.name: path.read_bytes() for path in source.iterdir()}
            result = prepare_owner_source_batches(source, workspace)
            self.assertEqual(result["batch_count"], 2)
            self.assertEqual([item["asset_count"] for item in result["batches"]], [10, 2])
            self.assertEqual(originals, {path.name: path.read_bytes() for path in source.iterdir()})
            self.assertNotIn(str(source), json.dumps(result, ensure_ascii=False))

    def test_only_explicit_owner_approval_enters_registry(self):
        candidate = approved_record("sha256:" + "b" * 64)
        candidate["approval"] = {"status": "CANDIDATE", "approved_by": "", "approved_at": ""}
        registry = compile_approved_layout_registry([approved_record(), candidate], allowed_layout_ids=LAYOUTS)
        self.assertEqual(registry["approved_profile_count"], 1)
        self.assertFalse(registry["profiles"][0]["is_performance_evidence"])

    def test_approved_record_requires_owner_identity_and_known_fixed_layout(self):
        record = approved_record()
        record["approval"]["approved_by"] = "model"
        record["recommendation"]["fixed_layout_id"] = "invented_layout"
        errors = validate_analysis_record(record, allowed_layout_ids=LAYOUTS)
        self.assertIn("owner_approval_identity_missing", errors)
        self.assertIn("unknown_fixed_layout:invented_layout", errors)

    def test_runtime_selector_uses_matching_approved_profile_and_fails_soft_without_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            registry_path = Path(temporary) / "registry.json"
            registry = compile_approved_layout_registry([approved_record()], allowed_layout_ids=LAYOUTS)
            registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
            selector = LayoutSelector({"approved_layout_registry_path": str(registry_path)})
            selected = selector.select(
                pattern_meta={},
                topic_intelligence={"category": "사건"},
                design_learning_context={"account_id": "account_a", "moods": ["긴장"], "issue_types": ["긴급"], "media_conditions": ["image_available"]},
            )
            self.assertEqual(selected["layout_type"], "dark_editorial")
            self.assertTrue(selected["design_learning_used"])
            self.assertEqual(selected["selected_layout_profile_id"], "news_urgent_dark_01")
            missing = LayoutSelector({"approved_layout_registry_path": str(Path(temporary) / "missing.json")}).select()
            self.assertFalse(missing["design_learning_used"])

    def test_shared_reference_pool_is_capped_at_forty_profiles(self):
        records = []
        for index in range(MAX_APPROVED_REFERENCE_PROFILES + 2):
            record = approved_record("sha256:" + f"{index:064x}")
            record["recommendation"]["profile_id"] = f"shared_reference_{index:02d}"
            records.append(record)
        registry = compile_approved_layout_registry(records, allowed_layout_ids=LAYOUTS)
        self.assertEqual(registry["approved_profile_count"], 40)
        self.assertEqual(registry["max_approved_profile_count"], 40)
        self.assertEqual(registry["rejected_approved_record_count"], 2)


if __name__ == "__main__":
    unittest.main()
