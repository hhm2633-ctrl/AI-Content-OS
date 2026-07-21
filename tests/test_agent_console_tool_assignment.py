import unittest

from modules.agent_console.tool_assignment_policy import assign_deferred_tools
from modules.agent_console.tool_manifest import LazyToolRegistry, ToolSpec, default_tool_specs


ALL_LOCAL = ("filesystem", "project_cli", "graphify", "hyperframes")


class TestAgentConsoleToolAssignment(unittest.TestCase):
    def test_category_research_defaults_to_bounded_local_tools(self):
        result = assign_deferred_tools(
            {"category": "news", "title": "today's candidate research"},
            allowed_tools=ALL_LOCAL,
        )
        self.assertEqual(result["assigned_tools"], ["filesystem", "project_cli"])
        self.assertNotIn("graphify", result["assigned_tools"])
        self.assertFalse(result["execution_started"])

    def test_graphify_is_only_available_to_code_or_architecture_jobs(self):
        denied = assign_deferred_tools(
            {"category": "story", "title": "source research", "requested_tools": ["graphify"]},
            allowed_tools=ALL_LOCAL,
        )
        self.assertEqual(denied["assigned_tools"], [])
        self.assertIn("job_policy_denied", {item["reason_code"] for item in denied["denied"]})

        assigned = assign_deferred_tools(
            {"category": "story", "title": "module architecture review", "requested_tools": ["graphify"]},
            allowed_tools=ALL_LOCAL,
        )
        self.assertEqual(assigned["assigned_tools"], ["graphify"])

    def test_hyperframes_is_limited_to_motion_render_planning(self):
        denied = assign_deferred_tools(
            {"category": "fashion", "title": "lookbook research", "requested_tools": ["hyperframes"]},
            allowed_tools=ALL_LOCAL,
        )
        self.assertEqual(denied["assigned_tools"], [])

        assigned = assign_deferred_tools(
            {"category": "fashion", "title": "motion render plan", "requested_tools": ["hyperframes"]},
            allowed_tools=ALL_LOCAL,
        )
        self.assertEqual(assigned["assigned_tools"], ["hyperframes"])

        execution_request = assign_deferred_tools(
            {"category": "fashion", "title": "render video now", "requested_tools": ["hyperframes"]},
            allowed_tools=ALL_LOCAL,
        )
        self.assertEqual(execution_request["assigned_tools"], [])

    def test_explicit_requests_and_agent_allow_list_are_both_required(self):
        result = assign_deferred_tools(
            {
                "category": "beauty",
                "title": "code architecture test",
                "requested_tools": ["filesystem", "graphify", "project_cli"],
            },
            allowed_tools=("filesystem", "graphify"),
        )
        self.assertEqual(result["assigned_tools"], ["filesystem", "graphify"])
        self.assertIn(
            {"tool_id": "project_cli", "reason_code": "agent_not_allowed"},
            result["denied"],
        )

    def test_unknown_browser_naeo_and_publish_are_denied(self):
        result = assign_deferred_tools(
            {
                "category": "news",
                "title": "publish this post",
                "requested_tools": ["browser", "naeo_blog", "mystery", "publish"],
            },
            allowed_tools=("browser", "naeo_blog", "mystery", "publish"),
            registered_tools=("browser", "naeo_blog", "publish"),
        )
        self.assertEqual(result["assigned_tools"], [])
        by_tool = {item["tool_id"]: item["reason_code"] for item in result["denied"]}
        self.assertEqual(by_tool["browser"], "tool_forbidden")
        self.assertEqual(by_tool["naeo_blog"], "tool_forbidden")
        self.assertEqual(by_tool["publish"], "tool_forbidden")
        self.assertEqual(by_tool["mystery"], "unknown_tool")

    def test_registry_exposes_policy_without_loading_factories(self):
        calls = []
        registry = LazyToolRegistry()
        for tool_id in ALL_LOCAL:
            registry.register(ToolSpec(tool_id, "local", "test"), lambda: calls.append(tool_id))
        result = registry.assign_for_job(
            {"category": "beauty", "title": "candidate research"},
            allowed_tools=ALL_LOCAL,
        )
        self.assertEqual(result["assigned_tools"], ["filesystem", "project_cli"])
        self.assertEqual(calls, [])
        self.assertEqual(registry.loaded_tool_ids, ())

    def test_naeo_descriptor_is_completely_removed(self):
        self.assertNotIn("naeo_blog", default_tool_specs())


if __name__ == "__main__":
    unittest.main()
