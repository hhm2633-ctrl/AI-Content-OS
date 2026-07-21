import json
import tempfile
import unittest
from pathlib import Path

from modules.agent_console.cardnews_flow_bridge import sync_selected_cardnews_candidates
from modules.agent_console.console import AgentConsole


class AgentConsoleCardNewsFlowBridgeTests(unittest.TestCase):
    def _selection(self):
        return {
            "schema_version": "cardnews_final_selection_v1",
            "accounts": {
                "A": {
                    "selected": [
                        {
                            "request_id": "owner_review:A-1",
                            "candidate_id": "A-1",
                            "account": "A",
                            "category": "국내뉴스",
                            "title": "selected news",
                            "grade": "1",
                            "source_urls": ["https://example.com/a"],
                            "requested_media": ["article image"],
                        }
                    ]
                },
                "B": {"selected": []},
                "C": {"selected": []},
            },
        }

    def test_selected_candidate_is_gated_and_fields_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            console = AgentConsole(Path(temporary), repository_root=Path.cwd())
            result = sync_selected_cardnews_candidates(self._selection(), console)

            self.assertEqual(result["status"], "synced")
            self.assertTrue(result["owner_approval_required"])
            job = console.snapshot()["jobs"][0]
            self.assertEqual(job["status"], "awaiting_second_stage")
            self.assertFalse(job["execution_approved"])
            self.assertEqual(console.ready_jobs(), [])
            context = json.loads(Path(job["context_path"]).read_text(encoding="utf-8"))
            self.assertEqual(context["candidate_id"], "A-1")
            self.assertEqual(context["account"], "A")
            self.assertEqual(context["category"], "국내뉴스")
            self.assertEqual(context["grade"], "1")
            self.assertEqual(context["source_urls"], ["https://example.com/a"])
            self.assertFalse(context["execution_enabled"])
            self.assertFalse(context["network_executed"])
            self.assertFalse(result["publishing"])

    def test_explicit_execution_approval_promotes_only_final_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            console = AgentConsole(Path(temporary), repository_root=Path.cwd())
            queue = {
                "schema_version": "owner_ranked_deep_dive_queue_v1",
                "requests": [
                    {
                        "request_id": "owner_review:A-1",
                        "candidate_id": "A-1",
                        "account": "A",
                        "category": "국내뉴스",
                        "title": "selected news",
                        "grade": "1",
                    },
                    {
                        "request_id": "owner_review:A-2",
                        "candidate_id": "A-2",
                        "account": "A",
                        "category": "국내뉴스",
                        "title": "held news",
                        "grade": "2",
                    },
                ],
            }
            result = sync_selected_cardnews_candidates(
                self._selection(), console, owner_queue=queue, execution_approved=True
            )
            self.assertTrue(result["execution_enabled"])
            statuses = {job["candidate_id"]: job["status"] for job in console.snapshot()["jobs"]}
            self.assertEqual(statuses["A-1"], "queued")
            self.assertEqual(statuses["A-2"], "awaiting_second_stage")

    def test_sync_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            console = AgentConsole(Path(temporary), repository_root=Path.cwd())
            first = sync_selected_cardnews_candidates(self._selection(), console)
            second = sync_selected_cardnews_candidates(self._selection(), console)

            self.assertEqual(first["sync"]["created"], 1)
            self.assertEqual(second["sync"]["created"], 0)
            self.assertEqual(second["sync"]["updated"], 1)
            self.assertEqual(len(console.snapshot()["jobs"]), 1)

    def test_unselected_and_invalid_candidates_are_not_enqueued(self):
        with tempfile.TemporaryDirectory() as temporary:
            console = AgentConsole(Path(temporary), repository_root=Path.cwd())
            selection = self._selection()
            selection["accounts"]["A"]["selected"][0]["selection_status"] = "not_selected"
            result = sync_selected_cardnews_candidates(selection, console)

            self.assertEqual(result["reason_code"], "no_valid_selected_candidates")
            self.assertEqual(console.snapshot()["jobs"], [])


if __name__ == "__main__":
    unittest.main()
