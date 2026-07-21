import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_cardnews_production_packages import build_packages


class BuildCardNewsProductionPackagesTests(unittest.TestCase):
    def test_writes_one_ready_and_one_missing_receipt_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selection = root / "selection.json"
            state = root / "state.json"
            output = root / "packages"
            selected = []
            for candidate_id in ("A-1", "A-2"):
                selected.append(
                    {
                        "candidate_id": candidate_id,
                        "account": "A",
                        "category": "국내뉴스",
                        "title": f"후보 {candidate_id}",
                        "source_urls": [f"https://news.example/{candidate_id}"],
                        "selection_status": "selected",
                    }
                )
            selection.write_text(
                json.dumps(
                    {
                        "schema_version": "cardnews_final_selection_v1",
                        "status": "selected",
                        "accounts": {
                            "A": {"selected": selected},
                            "B": {"selected": []},
                            "C": {"selected": []},
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            state.write_text(
                json.dumps(
                    {
                        "jobs": [
                            {
                                "candidate_id": "A-1",
                                "status": "completed",
                                "handoff": {
                                    "summary": "공개 기사 내용을 정리한다.",
                                    "outputs": {
                                        "cardnews_plan": {
                                            "slides": ["1 훅: 첫 장", "2 설명: 둘째 장"],
                                            "caption_draft": "별도 피드 본문입니다.",
                                        }
                                    },
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            manifest = build_packages(selection, state, output)

            self.assertEqual(manifest["package_count"], 2)
            self.assertEqual(manifest["ready_count"], 1)
            self.assertEqual(manifest["blocked_count"], 1)
            self.assertEqual(manifest["batch_bridge"]["ready_count"], 1)
            self.assertFalse(manifest["render_executed"])
            ready = json.loads((output / "A-1.json").read_text(encoding="utf-8"))
            blocked = json.loads((output / "A-2.json").read_text(encoding="utf-8"))
            self.assertEqual(ready["status"], "production_package_ready")
            self.assertEqual(blocked["reason_code"], "missing_agent_console_result")


if __name__ == "__main__":
    unittest.main()
