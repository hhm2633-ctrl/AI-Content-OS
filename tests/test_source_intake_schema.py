import json
import os
import shutil
import tempfile
import unittest

from modules.source_intake.source_intake_schema import (
    AD_SIGNAL_ALLOWED_KEYS,
    CHANNEL_CANDIDATES,
    DEEP_DIVE_STAGE_CONTRACT,
    RIGHTS_STATUS_REFERENCE_ONLY,
    build_shallow_item,
    build_visible_metrics,
    deep_dive_external_dir,
    shallow_index_dir,
    source_data_root,
    validate_shallow_item,
    write_shallow_index,
)


def make_item(**overrides):
    base = dict(
        source_id="nate_pann",
        source_type="community",
        title="테스트 제목입니다",
        url="https://pann.nate.com/talk/123",
        rank_position=1,
        board_or_category="talk_ranking",
        channel_candidates=["issue_daily", "dopamine_issue"],
        published_at="2026-07-14T09:00:00",
        collected_at="2026-07-14T12:00:00",
        visible_metrics={"views": 1000, "comments": 50, "likes": 20},
    )
    base.update(overrides)
    return build_shallow_item(**base)


class TestShallowItemSchema(unittest.TestCase):
    def test_valid_item_passes(self):
        item = make_item()
        ok, errors = validate_shallow_item(item)
        self.assertTrue(ok, errors)
        self.assertEqual(item["rights_status"], RIGHTS_STATUS_REFERENCE_ONLY)

    def test_metrics_default_to_null_not_fabricated(self):
        item = make_item(visible_metrics=None)
        ok, errors = validate_shallow_item(item)
        self.assertTrue(ok, errors)
        self.assertTrue(all(v is None for v in item["visible_metrics"].values()))
        self.assertEqual(item["metrics_origin"], "absent")

    def test_negative_counts_rejected(self):
        item = make_item()
        item["visible_metrics"]["views"] = -5
        ok, errors = validate_shallow_item(item)
        self.assertFalse(ok)
        self.assertIn("negative_metric:views", errors)

    def test_non_int_metric_rejected(self):
        item = make_item()
        item["visible_metrics"]["comments"] = "많음"
        ok, errors = validate_shallow_item(item)
        self.assertFalse(ok)
        self.assertIn("metric_not_int_or_null:comments", errors)

    def test_fabricated_origin_marker_rejected(self):
        item = make_item()
        item["metrics_origin"] = "fabricated"
        ok, errors = validate_shallow_item(item)
        self.assertFalse(ok)
        self.assertIn("forbidden_metrics_origin:fabricated", errors)

    def test_fabricated_metrics_flag_rejected(self):
        item = make_item()
        item["fabricated_metrics"] = True
        ok, errors = validate_shallow_item(item)
        self.assertFalse(ok)
        self.assertIn("fabricated_metrics_marker_present", errors)

    def test_builder_coerces_negative_and_string_counts_to_null(self):
        metrics = build_visible_metrics(
            {"views": -10, "comments": "1,234", "likes": "abc", "shares": 3}
        )
        self.assertIsNone(metrics["views"])
        self.assertEqual(metrics["comments"], 1234)
        self.assertIsNone(metrics["likes"])
        self.assertEqual(metrics["shares"], 3)

    def test_rights_status_must_be_reference_only(self):
        item = make_item()
        item["rights_status"] = "owned"
        ok, errors = validate_shallow_item(item)
        self.assertFalse(ok)
        self.assertIn("rights_status_must_be_reference_only", errors)

    def test_unknown_channel_candidates_dropped_by_builder(self):
        item = make_item(channel_candidates=["issue_daily", "not_a_channel"])
        self.assertEqual(item["channel_candidates"], ["issue_daily"])
        for channel in item["channel_candidates"]:
            self.assertIn(channel, CHANNEL_CANDIDATES)


class TestAdSignalPolicy(unittest.TestCase):
    def test_ad_signals_text_only_allowed(self):
        item = make_item(
            ad_signals={
                "ad_text": "지금 구매하면 50% 할인",
                "ad_domain": "smartstore.naver.com",
                "ad_category_guess": "fashion",
            }
        )
        ok, errors = validate_shallow_item(item)
        self.assertTrue(ok, errors)
        self.assertEqual(sorted(item["ad_signals"].keys()), sorted(AD_SIGNAL_ALLOWED_KEYS))

    def test_ad_image_keys_rejected(self):
        item = make_item()
        item["ad_signals"]["ad_image_path"] = "storage/ads/banner.png"
        ok, errors = validate_shallow_item(item)
        self.assertFalse(ok)
        self.assertTrue(any("ad_image_path" in error for error in errors))

    def test_builder_never_creates_ad_image_field(self):
        item = make_item(ad_signals={"ad_image_path": "x.png", "ad_text": "광고"})
        self.assertNotIn("ad_image_path", item["ad_signals"])
        self.assertEqual(item["ad_signals"]["ad_text"], "광고")


class TestStorageContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_shallow_index_path_contract(self):
        path = shallow_index_dir("2026-07-14")
        self.assertEqual(
            path.replace("\\", "/"),
            "storage/source_intake/2026-07-14/shallow_index",
        )

    def test_write_shallow_index_writes_only_json_no_ad_dirs(self):
        items = [make_item()]
        result = write_shallow_index(items, "2026-07-14", "nate_pann", base_dir=self.tmp)
        self.assertEqual(result["status"], "written")
        self.assertEqual(result["written_count"], 1)

        with open(result["path"], "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertEqual(payload["item_count"], 1)

        # only shallow_index exists; no ad image / raw html / screenshot dirs
        day_dir = os.path.join(self.tmp, "2026-07-14")
        self.assertEqual(os.listdir(day_dir), ["shallow_index"])

    def test_invalid_items_are_rejected_not_written(self):
        bad = make_item()
        bad["visible_metrics"]["likes"] = -1
        result = write_shallow_index([bad], "2026-07-14", "nate_pann", base_dir=self.tmp)
        self.assertEqual(result["status"], "skipped_empty")
        self.assertEqual(result["rejected_count"], 1)

    def test_deep_dive_stages_are_owner_selected_in_v1(self):
        for stage, contract in DEEP_DIVE_STAGE_CONTRACT.items():
            self.assertTrue(contract["enabled_in_v1"], stage)
            self.assertEqual(contract["activation"], "owner_selected_only")
            self.assertEqual(contract["when"], "after_topic_selection")
            self.assertEqual(contract["storage_root"], "external_source_data_root")

    def test_external_source_data_root_defaults_to_f_drive(self):
        self.assertEqual(source_data_root("missing_config.json"), "F:/AI-Content-OS-Data")

    def test_deep_dive_external_dir_uses_external_root(self):
        path = deep_dive_external_dir(
            "2026-07-14",
            "comments",
            "fmkorea",
            base_dir="F:/AI-Content-OS-Data",
        )
        self.assertEqual(
            path.replace("\\", "/"),
            "F:/AI-Content-OS-Data/source_intake/2026-07-14/deep_dive/comments/fmkorea",
        )


if __name__ == "__main__":
    unittest.main()
