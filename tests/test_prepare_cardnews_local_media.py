import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "prepare_cardnews_local_media.py"
SPEC = importlib.util.spec_from_file_location("prepare_cardnews_local_media", SCRIPT_PATH)
cli = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(cli)


class PrepareCardNewsLocalMediaCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.input_path = self.root / "request.json"
        self.config_path = self.root / "config.json"
        self.input_path.write_text(
            json.dumps({"request_id": "media-1", "assets": []}), encoding="utf-8"
        )
        self.config_path.write_text(
            json.dumps(
                {
                    "schema_version": "local_media_pipeline_config_v1",
                    "output_root": "F:/AI-Content-OS-Data/external_tools/outputs/local_media_pipeline",
                }
            ),
            encoding="utf-8",
        )
        self.receipt_path = Path(
            "F:/AI-Content-OS-Data/external_tools/outputs/local_media_pipeline/tests/receipt.json"
        )

    def tearDown(self):
        self.temp.cleanup()

    def _run(self, *, execute=False, result=None):
        args = [
            "--input",
            str(self.input_path),
            "--config",
            str(self.config_path),
            "--output-receipt",
            str(self.receipt_path),
        ]
        if execute:
            args.append("--execute")
        core = Mock(return_value=result or {"status": "validated"})
        module = SimpleNamespace(prepare_local_media=core)
        with patch.object(cli.importlib, "import_module", return_value=module) as importer:
            with patch.object(cli, "_write_receipt") as writer:
                exit_code = cli.run(args)
        importer.assert_called_once_with("modules.media_intelligence.local_media_pipeline")
        return exit_code, core, writer

    def test_defaults_to_validate_only(self):
        exit_code, core, writer = self._run()
        self.assertEqual(exit_code, 0)
        request = core.call_args.args[0]
        self.assertIs(request["execute"], False)
        self.assertIs(request["validate_only"], True)
        writer.assert_called_once()

    def test_execute_flag_is_forwarded_explicitly(self):
        exit_code, core, _ = self._run(execute=True, result={"status": "completed"})
        self.assertEqual(exit_code, 0)
        request = core.call_args.args[0]
        self.assertIs(request["execute"], True)
        self.assertIs(request["validate_only"], False)

    def test_rejects_non_f_output_without_call_or_write(self):
        output = self.root / "receipt.json"
        with patch.object(cli.importlib, "import_module") as importer:
            with patch.object(cli, "_write_receipt") as writer:
                exit_code = cli.run(
                    [
                        "--input",
                        str(self.input_path),
                        "--config",
                        str(self.config_path),
                        "--output-receipt",
                        str(output),
                    ]
                )
        self.assertEqual(exit_code, 1)
        importer.assert_not_called()
        writer.assert_not_called()

    def test_blocked_core_receipt_returns_nonzero_and_is_written(self):
        exit_code, _, writer = self._run(
            result={"status": "blocked", "reason_code": "NO_EXPLICIT_OPERATION"}
        )
        self.assertEqual(exit_code, 1)
        self.assertEqual(writer.call_args.args[1]["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
