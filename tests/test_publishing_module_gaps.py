"""Independent coverage for the untested paths of modules/publishing/publishing_module.py.

Priority-2 gap-fill (continuation): `tests/test_publishing_image_gate.py` already covers the
image-sourcing gate path; this file covers the remaining untested surface identified by the
earlier coverage audit: `_load_publishing_config` fallback, `_create_hashtags` normalization,
`_get_default_account`, `_resolve_planner_strategy`, and a full `run()` happy path. `publishing_dir`
is redirected to a temp directory after construction so no real `storage/publishing/` file is
touched. No existing module or test file is modified.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.publishing.publishing_module import PublishingModule


class PublishingConfigFallbackTests(unittest.TestCase):
    def test_missing_config_file_falls_back_to_hardcoded_defaults(self):
        with patch.object(Path, "exists", return_value=False):
            module = PublishingModule()

        fallback = module._fallback_publishing_config()
        self.assertEqual(module.publishing_config, fallback)
        self.assertEqual(module.publishing_config["platform"], "instagram")
        self.assertEqual(module.publishing_config["upload_mode"], "manual")

    def test_malformed_config_json_falls_back_to_hardcoded_defaults(self):
        with patch.object(Path, "exists", return_value=True), \
             patch("modules.publishing.publishing_module.json.load", side_effect=json.JSONDecodeError("bad", "doc", 0)):
            module = PublishingModule()

        self.assertEqual(module.publishing_config, module._fallback_publishing_config())

    def test_fallback_config_has_seven_default_hashtags(self):
        module = PublishingModule.__new__(PublishingModule)
        fallback = module._fallback_publishing_config()
        self.assertEqual(len(fallback["hashtags"]), 7)
        self.assertTrue(all(tag.startswith("#") for tag in fallback["hashtags"]))


class PublishingHashtagTests(unittest.TestCase):
    def _module_with_config(self, config):
        module = PublishingModule.__new__(PublishingModule)
        module.config = {}
        module.publishing_config = config
        return module

    def test_hashtags_without_hash_prefix_get_normalized(self):
        module = self._module_with_config({"hashtags": ["AI", "#already"]})
        result = module._create_hashtags()
        self.assertEqual(result, ["#AI", "#already"])

    def test_empty_or_blank_hashtags_are_dropped(self):
        module = self._module_with_config({"hashtags": ["", "   ", "#valid"]})
        result = module._create_hashtags()
        self.assertEqual(result, ["#valid"])

    def test_hashtags_truncated_to_twenty(self):
        module = self._module_with_config({"hashtags": [f"tag{i}" for i in range(30)]})
        result = module._create_hashtags()
        self.assertEqual(len(result), 20)

    def test_empty_hashtag_config_falls_back_to_hardcoded_seven(self):
        module = self._module_with_config({"hashtags": []})
        result = module._create_hashtags()
        self.assertEqual(len(result), 7)
        self.assertIn("#AI", result)

    def test_missing_hashtags_key_falls_back_to_hardcoded_seven(self):
        module = self._module_with_config({})
        result = module._create_hashtags()
        self.assertEqual(len(result), 7)


class PublishingDefaultAccountTests(unittest.TestCase):
    def _module_with_config(self, config):
        module = PublishingModule.__new__(PublishingModule)
        module.config = {}
        module.publishing_config = config
        return module

    def test_returns_first_enabled_account(self):
        module = self._module_with_config({"accounts": [
            {"account_id": "a1", "enabled": False},
            {"account_id": "a2", "enabled": True},
        ]})
        account = module._get_default_account()
        self.assertEqual(account["account_id"], "a2")

    def test_all_accounts_disabled_falls_back_to_hardcoded_default(self):
        module = self._module_with_config({"accounts": [{"account_id": "a1", "enabled": False}]})
        account = module._get_default_account()
        self.assertEqual(account["account_id"], "account_01")

    def test_empty_accounts_list_falls_back_to_hardcoded_default(self):
        module = self._module_with_config({"accounts": []})
        account = module._get_default_account()
        self.assertEqual(account["account_id"], "account_01")

    def test_missing_accounts_key_falls_back_to_hardcoded_default(self):
        module = self._module_with_config({})
        account = module._get_default_account()
        self.assertEqual(account["account_id"], "account_01")


class PublishingPlannerAndImageSourcingResolutionTests(unittest.TestCase):
    def _module(self):
        module = PublishingModule.__new__(PublishingModule)
        module.config = {}
        module.publishing_config = {}
        return module

    def test_resolve_planner_strategy_uses_existing_influence(self):
        module = self._module()
        influence = {"any_hint_applied": True, "content": {"x": 1}, "image_strategy": {}, "reason": "used"}
        result = module._resolve_planner_strategy({"planner_influence": influence})
        self.assertEqual(result, influence)

    def test_resolve_planner_strategy_defaults_when_missing(self):
        module = self._module()
        result = module._resolve_planner_strategy({})
        self.assertFalse(result["any_hint_applied"])

    def test_resolve_planner_strategy_defaults_when_card_news_result_not_dict(self):
        module = self._module()
        result = module._resolve_planner_strategy("not-a-dict")
        self.assertFalse(result["any_hint_applied"])

    def test_resolve_image_sourcing_status_uses_existing_status(self):
        module = self._module()
        status = {"manual_image_required": True, "recommended_source": "news", "real_image_used_count": 2, "checklist": ["x"]}
        result = module._resolve_image_sourcing_status({"image_sourcing_status": status})
        self.assertEqual(result, status)

    def test_resolve_image_sourcing_status_defaults_when_missing(self):
        module = self._module()
        result = module._resolve_image_sourcing_status({})
        self.assertFalse(result["manual_image_required"])
        self.assertEqual(result["real_image_used_count"], 0)


class PublishingGateTests(unittest.TestCase):
    def _module(self):
        module = PublishingModule.__new__(PublishingModule)
        module.config = {}
        module.publishing_config = {}
        return module

    def test_gate_blocked_when_manual_image_required(self):
        module = self._module()
        operations = module._resolve_publishing_gate({"manual_image_required": True, "real_image_used_count": 3})
        self.assertTrue(operations["publishing_blocked"])
        self.assertIn("manual_image_required", operations["blocking_reasons"])

    def test_gate_blocked_when_real_image_count_zero(self):
        module = self._module()
        operations = module._resolve_publishing_gate({"manual_image_required": False, "real_image_used_count": 0})
        self.assertTrue(operations["publishing_blocked"])
        self.assertIn("real_image_used_count_zero", operations["blocking_reasons"])

    def test_gate_open_when_not_manual_and_real_images_present(self):
        module = self._module()
        operations = module._resolve_publishing_gate({"manual_image_required": False, "real_image_used_count": 4})
        self.assertFalse(operations["publishing_blocked"])
        self.assertEqual(operations["blocking_reasons"], [])

    def test_non_numeric_real_image_used_count_defaults_to_zero_and_blocks(self):
        module = self._module()
        operations = module._resolve_publishing_gate({"manual_image_required": False, "real_image_used_count": "not-a-number"})
        self.assertEqual(operations["real_image_used_count"], 0)
        self.assertTrue(operations["publishing_blocked"])


class PublishingRunFullPathTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        with patch.object(Path, "mkdir"):
            self.module = PublishingModule.__new__(PublishingModule)
        self.module.config = {}
        self.module.publishing_dir = Path(self.tmp_dir.name)
        self.module.publishing_config = self.module._fallback_publishing_config()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_run_ready_path_writes_all_four_output_files(self):
        card_news_result = {
            "title": "테스트 카드뉴스",
            "cards": [{"card_path": "storage/card_news/1.png"}, {"card_path": "storage/card_news/2.png"}],
            "image_sourcing_status": {"manual_image_required": False, "real_image_used_count": 4, "checklist": []},
        }
        result = self.module.run(card_news_result)

        self.assertEqual(result["status"], "publishing_blocked")
        self.assertEqual(result["card_count"], 2)
        for filename in ("publishing_result.json", "publish_queue.json", "caption.txt", "hashtags.txt"):
            self.assertTrue((Path(self.tmp_dir.name) / filename).exists(), f"{filename} was not written")

    def test_run_blocked_path_when_manual_image_required(self):
        card_news_result = {
            "title": "테스트",
            "cards": [],
            "image_sourcing_status": {"manual_image_required": True, "real_image_used_count": 0, "checklist": ["체크1"]},
        }
        result = self.module.run(card_news_result)

        self.assertEqual(result["status"], "publishing_blocked")
        self.assertTrue(result["manual_image_required"])

        with open(Path(self.tmp_dir.name) / "publish_queue.json", "r", encoding="utf-8") as file:
            queue = json.load(file)
        self.assertEqual(queue["status"], "queue_blocked")
        self.assertEqual(queue["items"][0]["status"], "blocked_pending_image_sourcing")

    def test_run_uses_fallback_title_when_missing(self):
        result = self.module.run({"cards": [], "image_sourcing_status": {"manual_image_required": False, "real_image_used_count": 1}})
        self.assertEqual(result["caption"].splitlines()[0], "오늘의 AI 카드뉴스")

    def test_run_full_caption_includes_hashtags(self):
        result = self.module.run({"cards": [], "image_sourcing_status": {"manual_image_required": False, "real_image_used_count": 1}})
        for tag in result["hashtags"]:
            self.assertIn(tag, result["full_caption"])


if __name__ == "__main__":
    unittest.main()
