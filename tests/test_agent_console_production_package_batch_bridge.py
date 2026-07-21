import copy
import unittest

from modules.agent_console.production_package_batch_bridge import (
    build_production_package_batch_inputs,
)


def selection():
    return {
        "schema_version": "cardnews_final_selection_v1",
        "status": "selected",
        "accounts": {
            "A": {"selected": [{"candidate_id": "A-1", "account": "A", "title": "뉴스"}]},
            "B": {"selected": [{"candidate_id": "B-1", "account": "B", "title": "스토리"}]},
            "C": {"selected": [{"candidate_id": "C-1", "account": "C", "title": "패션"}]},
        },
    }


def job(candidate_id, account, *, status="completed", bundle=None):
    outputs = {"brief": "bounded result"}
    if bundle is not None:
        outputs["deep_bundle"] = bundle
    return {
        "job_id": f"job-{candidate_id}",
        "candidate_id": candidate_id,
        "account": account,
        "status": status,
        "handoff": {"summary": "done", "outputs": outputs, "warnings": []},
    }


def bundle(candidate_id, account):
    return {
        "candidate_id": candidate_id,
        "account": account,
        "status": "completed",
        "summary": f"evidence for {candidate_id}",
        "source_refs": [{"url": f"https://example.test/{candidate_id}"}],
    }


class ProductionPackageBatchBridgeTests(unittest.TestCase):
    def test_builds_deterministic_account_separated_inputs_without_execution(self):
        selected = selection()
        console = {"jobs": [job("A-1", "A"), job("B-1", "B"), job("C-1", "C")]}
        bundles = [bundle("C-1", "C"), bundle("A-1", "A"), bundle("B-1", "B")]
        originals = copy.deepcopy((selected, console, bundles))

        first = build_production_package_batch_inputs(selected, console, bundles)
        second = build_production_package_batch_inputs(selected, console, bundles)

        self.assertEqual(first, second)
        self.assertEqual((selected, console, bundles), originals)
        self.assertEqual(first["status"], "ready")
        self.assertEqual([item["account"] for item in first["package_inputs"]], ["A", "B", "C"])
        self.assertEqual(first["accounts"]["A"]["records"][0]["candidate_id"], "A-1")
        self.assertFalse(first["package_executed"])
        self.assertFalse(first["render_executed"])
        self.assertFalse(first["publish_executed"])
        self.assertFalse(first["external_calls_executed"])

    def test_missing_and_noncompleted_results_are_reported_without_fabrication(self):
        selected = selection()
        console = {
            "jobs": [
                job("A-1", "A", status="running"),
                job("B-1", "B"),
                job("C-1", "C"),
            ]
        }
        bundles = {
            "B-1": {**bundle("B-1", "B"), "status": "running"},
            "C-1": bundle("C-1", "C"),
        }
        result = build_production_package_batch_inputs(selected, console, bundles)

        self.assertEqual(result["status"], "partial")
        reasons = {item["candidate_id"]: item["reason_code"] for item in result["missing_result_receipts"]}
        self.assertEqual(reasons["A-1"], "agent_console_result_not_completed")
        self.assertEqual(reasons["B-1"], "deep_bundle_not_completed")
        self.assertEqual([item["candidate_id"] for item in result["package_inputs"]], ["C-1"])
        self.assertTrue(all(item["package_input"] is None for item in result["missing_result_receipts"]))

    def test_completed_spark_handoff_can_supply_explicit_completed_bundle(self):
        selected = selection()
        selected["accounts"]["B"]["selected"] = []
        selected["accounts"]["C"]["selected"] = []
        deep = bundle("A-1", "A")
        spark_job = job("A-1", "A")
        spark_job["handoff"]["outputs"] = {
            "spark_receipt": {
                "schema_version": "spark_host_receipt_v1",
                "status": "completed",
                "outputs": {"deep_bundle": deep},
            }
        }

        result = build_production_package_batch_inputs(selected, {"jobs": [spark_job]})

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["package_inputs"][0]["deep_bundle"]["candidate_id"], "A-1")

    def test_batch_is_bounded_and_does_not_silently_drop_finalists(self):
        selected = selection()
        selected["accounts"]["B"]["selected"] = []
        selected["accounts"]["C"]["selected"] = []
        selected["accounts"]["A"]["selected"] = [
            {"candidate_id": f"A-{index}", "account": "A", "title": str(index)}
            for index in range(1, 6)
        ]
        jobs = [job(f"A-{index}", "A", bundle=bundle(f"A-{index}", "A")) for index in range(1, 6)]

        result = build_production_package_batch_inputs(selected, {"jobs": jobs})

        self.assertEqual(result["ready_count"], 4)
        self.assertEqual(result["accounts"]["A"]["records"][4]["reason_code"], "per_account_limit_exceeded")
        self.assertEqual(result["selected_count"], 5)

    def test_invalid_selection_fails_closed(self):
        result = build_production_package_batch_inputs({}, {"jobs": []})
        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["reason_code"], "invalid_final_selection")
        self.assertEqual(result["package_inputs"], [])


if __name__ == "__main__":
    unittest.main()
