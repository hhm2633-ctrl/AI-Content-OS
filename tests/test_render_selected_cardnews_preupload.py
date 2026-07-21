import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts.render_selected_cardnews_preupload import (
    LEGACY_RENDERER_DISABLED_REASON,
    _fragment_digest,
    main,
    render_batch,
)


class RenderSelectedCardnewsPreuploadTest(unittest.TestCase):
    def test_fragment_digest_compatibility_remains_available(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fragments = root / "fragments"
            fragments.mkdir()
            (fragments / "account_A.json").write_text(
                json.dumps({"records": []}), encoding="utf-8"
            )
            first = _fragment_digest(fragments)
            self.assertTrue(first)
            self.assertEqual(first, _fragment_digest(fragments))

    def test_render_batch_always_blocks_before_output_or_authorization_consumption(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fragments = root / "fragments"
            output = root / "out"
            fragments.mkdir()
            authorization = {
                "schema_version": "cardnews_render_authorization_v1",
                "authorization_id": "auth-1",
                "authorized": True,
            }
            with self.assertRaisesRegex(PermissionError, LEGACY_RENDERER_DISABLED_REASON):
                render_batch(fragments, output, authorization=authorization)
            self.assertFalse(output.exists())
            self.assertFalse((root / ".controller_authorizations").exists())

    def test_cli_blocks_with_stable_reason_before_reading_authorization(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "out"
            missing_authorization = root / "does-not-exist.json"
            stdout = io.StringIO()
            argv = [
                "render_selected_cardnews_preupload.py",
                "--input-root", str(root / "fragments"),
                "--output-root", str(output),
                "--authorization", str(missing_authorization),
            ]
            with patch("sys.argv", argv), redirect_stdout(stdout):
                exit_code = main()
            self.assertEqual(exit_code, 2)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload, {
                "status": "blocked",
                "reason": LEGACY_RENDERER_DISABLED_REASON,
            })
            self.assertFalse(output.exists())
            self.assertFalse(missing_authorization.exists())


if __name__ == "__main__":
    unittest.main()
