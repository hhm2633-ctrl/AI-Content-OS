import json
import tempfile
import unittest
from pathlib import Path

from modules.design_learning.production_profile_compiler import (
    ProductionProfileCompiler,
)


class ReferenceRegistryProfileLookupTests(unittest.TestCase):
    def test_profile_compiler_automatically_reads_configured_registry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry = root / "approved_reference_v2_registry.json"
            registry.write_text(
                json.dumps(
                    {
                        "specimens": [],
                        "blueprints": {},
                    }
                ),
                encoding="utf-8",
            )
            compiler = ProductionProfileCompiler(
                feedback_root=root / "feedback",
                taxonomy_path=root / "taxonomy.json",
                index_path=root / "index.json",
                reference_registry_path=registry,
            )

            profile = compiler.compile(
                {
                    "account": "A",
                    "topic": "registry lookup",
                    "formats": ["card_news"],
                }
            )

            self.assertEqual(
                profile["reference_v2_registry"]["registry_path"],
                str(registry),
            )
            self.assertFalse(
                profile["reference_v2_registry"]["auto_approval_performed"]
            )
            self.assertEqual(
                profile["reference_v2_registry"]["status"],
                "no_owner_approved_references",
            )


if __name__ == "__main__":
    unittest.main()
