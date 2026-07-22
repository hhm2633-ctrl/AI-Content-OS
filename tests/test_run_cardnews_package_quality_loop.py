import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_cardnews_package_quality_loop import run_quality_loop


def record(candidate_id="A-1", approved=False):
    slides = [
        {"role": "cover", "headline": "첫 장의 핵심", "body": "확인된 원문에서 중요한 장면을 짚었습니다."},
        {"role": "context", "headline": "이어지는 맥락", "body": "앞 장과 다른 사실을 짧게 설명합니다."},
        {"role": "meaning", "headline": "마지막으로 볼 점", "body": "독자가 이해할 지점을 자연스럽게 마무리합니다."},
    ]
    value = {
        "candidate_id": candidate_id, "account": "A", "category": "뉴스", "title": "선정 주제",
        "evidence": {"sources": ["https://example.test/source"]},
        "story": {"summary": "원문 근거가 세 장면으로 이어진다."},
        "slides": slides,
        "feed_caption": "공개된 원문에서 확인된 내용을 카드 밖에서도 자연스럽게 읽히도록 두 문장으로 정리했습니다. 각 장면은 서로 다른 정보를 담고 있습니다.",
        "media_plan": [
            {"slide_role": row["role"], "media_type": "editorial", "source_credit": "https://example.test/source", "asset_status": "original_editorial_graphic"}
            for row in slides
        ],
    }
    if approved:
        value["status"] = "production_package_ready"
        value["reason_code"] = "strict_package_composed"
        value["gates"] = {
            "package_approval": {
                "status": "approved",
                "approved": True,
                "scope": "production_package",
                "candidate_id": candidate_id,
                "approved_by": "project_owner",
                "receipt_id": f"explicit-{candidate_id}",
            }
        }
    return value


class RunCardNewsPackageQualityLoopTests(unittest.TestCase):
    def test_stops_early_when_all_quality_gates_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repair = root / "repair"
            packages = root / "packages"
            repair.mkdir()
            (repair / "account_A.json").write_text(json.dumps({"records": [record(approved=True)]}, ensure_ascii=False), encoding="utf-8")
            result = run_quality_loop(repair, packages, 10)
            self.assertEqual(result["ready_count"], 1)
            self.assertEqual(result["quality_loop"]["cycles_executed"], 1)
            self.assertFalse(result["render_executed"])

    def test_stable_failure_stops_without_wasting_ten_cycles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repair = root / "repair"
            packages = root / "packages"
            repair.mkdir()
            value = record(approved=True)
            value["feed_caption"] = "짧음"
            (repair / "account_A.json").write_text(json.dumps({"records": [value]}, ensure_ascii=False), encoding="utf-8")
            result = run_quality_loop(repair, packages, 10)
            self.assertEqual(result["ready_count"], 0)
            self.assertEqual(result["quality_loop"]["cycles_executed"], 2)
            self.assertEqual(result["packages"][0]["status"], "blocked")

    def test_independent_revise_receipt_blocks_automated_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repair = root / "repair"
            reviews = root / "reviews"
            packages = root / "packages"
            repair.mkdir()
            reviews.mkdir()
            (repair / "account_A.json").write_text(json.dumps({"records": [record(approved=True)]}, ensure_ascii=False), encoding="utf-8")
            (reviews / "review_A.json").write_text(
                json.dumps({"cycle": 6, "records": [{"candidate_id": "A-1", "decision": "revise", "issues": ["첫 장 수정"]}]}, ensure_ascii=False),
                encoding="utf-8",
            )
            result = run_quality_loop(repair, packages, 3, reviews)
            self.assertEqual(result["ready_count"], 0)
            self.assertEqual(result["quality_loop"]["editorial_cycles_executed"], 6)
            package = json.loads((packages / "A-1.json").read_text(encoding="utf-8"))
            self.assertIn("independent_review_revise", package["missing_requirements"])

    def test_replaced_candidate_is_removed_from_latest_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repair = root / "repair"
            packages = root / "packages"
            repair.mkdir()
            path = repair / "account_A.json"
            path.write_text(json.dumps({"records": [record("A-old")]}, ensure_ascii=False), encoding="utf-8")
            run_quality_loop(repair, packages, 10)

            path.write_text(json.dumps({"records": [record("A-new")]}, ensure_ascii=False), encoding="utf-8")
            result = run_quality_loop(repair, packages, 10)

            self.assertEqual(result["package_count"], 1)
            self.assertEqual(result["packages"][0]["candidate_id"], "A-new")

    def test_quality_pass_cannot_promote_missing_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repair = root / "repair"
            packages = root / "packages"
            repair.mkdir()
            (repair / "account_A.json").write_text(
                json.dumps({"records": [record()]}, ensure_ascii=False),
                encoding="utf-8",
            )

            result = run_quality_loop(repair, packages, 10)
            package = json.loads((packages / "A-1.json").read_text(encoding="utf-8"))

            self.assertEqual(result["ready_count"], 0)
            self.assertEqual(result["pending_count"], 1)
            self.assertEqual(package["status"], "production_package_pending_approval")
            self.assertFalse(package["gates"]["package_approval"]["approved"])


if __name__ == "__main__":
    unittest.main()
