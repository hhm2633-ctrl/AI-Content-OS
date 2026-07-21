import json
import os
import shutil
import unittest

from modules.source_intake.daily_collection_runner import run_daily_collection_plan


class TestDailyCollectionRunner(unittest.TestCase):
    def setUp(self):
        self.today = "2099-01-02"
        self.default_path = os.path.join("storage", "source_intake", self.today, "daily_collection_plan.json")
        self.output_root = os.path.join("storage", "source_intake")
        self.custom_root = os.path.join("storage", "_tmp_runner_output")
        if os.path.exists(self.default_path):
            os.remove(self.default_path)
        if os.path.exists(os.path.join(self.output_root, self.today)):
            shutil.rmtree(os.path.join(self.output_root, self.today), ignore_errors=True)
        if os.path.exists(self.custom_root):
            shutil.rmtree(self.custom_root, ignore_errors=True)

    def tearDown(self):
        if os.path.exists(os.path.join(self.output_root, self.today)):
            shutil.rmtree(os.path.join(self.output_root, self.today), ignore_errors=True)
        if os.path.exists(self.custom_root):
            shutil.rmtree(self.custom_root, ignore_errors=True)

    def test_run_daily_collection_plan_default_path(self):
        result = run_daily_collection_plan(account_profiles=["news_society_economy"], today=self.today)

        self.assertEqual(result["status"], "written")
        self.assertEqual(result["plan_path"], self.default_path)
        self.assertTrue(os.path.isfile(result["plan_path"]))

    def test_run_daily_collection_plan_custom_output_root(self):
        result = run_daily_collection_plan(
            account_profiles=["news_society_economy"],
            today=self.today,
            output_root=self.custom_root,
        )
        expected = os.path.join(self.custom_root, self.today, "daily_collection_plan.json")
        self.assertEqual(result["status"], "written")
        self.assertEqual(result["plan_path"], expected)
        self.assertTrue(os.path.isfile(result["plan_path"]))

    def test_run_daily_collection_plan_writes_valid_json(self):
        result = run_daily_collection_plan(account_profiles=["news_society_economy"], today=self.today)

        with open(result["plan_path"], "r", encoding="utf-8") as handle:
            loaded = json.load(handle)

        self.assertEqual(loaded["date"], self.today)
        self.assertEqual(loaded["schema_version"], result["plan"]["schema_version"])
        self.assertEqual(result["plan"], loaded)

    def test_unknown_lane_fail_closed(self):
        result = run_daily_collection_plan(account_profiles=["ghost_lane"], today=self.today)
        plan = result["plan"]

        self.assertEqual(result["status"], "written")
        self.assertIn("ghost_lane", plan["unknown_lanes"])
        self.assertEqual(plan["plan_status"], "empty_plan")
        self.assertEqual(plan["lanes"][0]["lane_id"], "ghost_lane")
        self.assertEqual(plan["lanes"][0]["shallow_profiles"], [])

    def test_no_commerce_detail_in_plan(self):
        result = run_daily_collection_plan(account_profiles=["news_society_economy"], today=self.today)
        serialized = json.dumps(result["plan"])

        self.assertNotIn("commerce_detail", serialized)
