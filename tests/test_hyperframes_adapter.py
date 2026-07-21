import unittest
from pathlib import Path

from modules.agent_console.tool_manifest import HyperFramesDiagnosticsAdapter


class TestHyperFramesAdapter(unittest.TestCase):
    def setUp(self):
        self.repository = Path.cwd().resolve()
        self.adapter = HyperFramesDiagnosticsAdapter(self.repository)

    def test_builds_owner_gated_f_drive_render_command_without_rendering(self):
        output = Path("F:/AI-Content-OS-Data/renders/adapter-check.mp4")
        command = self.adapter.render_command(
            project_dir=self.repository,
            output_path=output,
            output_format="mp4",
        )
        self.assertIn("render", command)
        self.assertIn("hyperframes@0.7.63", command)
        self.assertIn("--offline", command)
        self.assertEqual(command[-1], str(output.resolve()))
        with self.assertRaises(PermissionError):
            self.adapter.render_local(
                project_dir=self.repository,
                output_path=output,
                owner_approved=False,
            )

    def test_rejects_c_drive_render_output(self):
        forbidden_parent = self.repository / ".tmp_hyperframes_forbidden" / "unexpected"
        self.assertFalse(forbidden_parent.exists())
        with self.assertRaises(PermissionError):
            self.adapter.render_local(
                project_dir=self.repository,
                output_path=forbidden_parent / "forbidden.mp4",
                owner_approved=True,
            )
        self.assertFalse(forbidden_parent.exists())


if __name__ == "__main__":
    unittest.main()
