import tempfile
import unittest
from pathlib import Path

from modules.shorts.shorts_module import ShortsModule


def _content():
    return {
        "title": "AI 자동화 가이드",
        "caption": "작은 업무부터 자동화하세요.",
        "hashtags": ["#AI", "#자동화"],
        "pattern_prompt_meta": {"pattern_type": "tutorial", "hook_type": "attention", "cta_type": "save"},
        "slides": [
            {"role": "hook", "headline": "지금 시작", "body": "반복 업무를 줄여보세요."},
            {"role": "problem", "headline": "문제 선택", "body": "작은 반복부터 고르세요."},
            {"role": "solution", "headline": "순서 적용", "body": "자동화하고 결과를 검수하세요."},
            {"role": "cta", "headline": "저장하기", "body": "필요할 때 다시 확인하세요."},
        ],
    }


class TestShortsPhaseOne(unittest.TestCase):
    def test_produces_all_nine_offline_contracts(self):
        result = ShortsModule().run(_content(), {"keyword": "AI 자동화"}, save_results=False)
        self.assertEqual(result["status"], "shorts_planning_completed")
        self.assertFalse(result["external_calls_attempted"])
        self.assertEqual(len([key for key in result if key.endswith("_result")]), 9)

    def test_script_duration_and_caption_timeline_are_deterministic(self):
        result = ShortsModule().run(_content(), save_results=False)
        script = result["shorts_script_result"]
        captions = result["shorts_caption_result"]["captions"]
        self.assertEqual(script["total_estimated_seconds"], 25.0)
        self.assertTrue(script["duration_limit_ok"])
        self.assertEqual(captions[-1]["end_seconds"], 25.0)

    def test_assets_are_never_render_allowed_without_provenance(self):
        result = ShortsModule().run(_content(), save_results=False)
        assets = result["shorts_asset_plan_result"]["assets"]
        self.assertTrue(assets)
        self.assertTrue(all(not asset["render_allowed"] for asset in assets))
        self.assertTrue(result["shorts_publish_prep_result"]["manual_action_required"])

    def test_over_budget_script_trims_only_complete_trailing_lines(self):
        content = _content()
        content["slides"].extend([
            {"role": "solution", "headline": "추가 단계", "body": "이 대사는 통째로 제거 대상입니다."},
            {"role": "cta", "headline": "마지막 행동", "body": "이 대사도 통째로 제거 대상입니다."},
        ])
        result = ShortsModule().run(content, save_results=False)
        script = result["shorts_script_result"]
        self.assertGreater(script["original_duration_seconds"], 30)
        self.assertTrue(script["trim_required"])
        self.assertGreater(script["trimmed_line_count"], 0)
        self.assertLessEqual(script["total_estimated_seconds"], 30)
        original_lines = {
            f"{slide['headline']} {slide['body']}" for slide in content["slides"]
        }
        self.assertTrue(all(line["text"] in original_lines for line in script["script_lines"]))

    def test_missing_or_malformed_content_falls_back_without_raising(self):
        for value in (None, "invalid", 123, {"slides": "invalid"}):
            with self.subTest(value=value):
                result = ShortsModule().run(value, save_results=False)
                self.assertEqual(result["status"], "shorts_planning_fallback")
                self.assertFalse(result["external_calls_attempted"])

    def test_writes_stage_results_only_to_selected_output_directory(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            output = Path(directory)
            result = ShortsModule(output_dir=output).run(_content())
            self.assertEqual(result["status"], "shorts_planning_completed")
            self.assertEqual(len(list(output.glob("*.json"))), 10)

    def test_shorts_remains_outside_workflow_and_card_news(self):
        source = Path("modules/shorts/shorts_module.py").read_text(encoding="utf-8")
        workflow = Path("src/workflow_engine.py").read_text(encoding="utf-8")
        self.assertNotIn("modules.card_news", source)
        self.assertNotIn("modules.shorts", workflow)


if __name__ == "__main__":
    unittest.main()
