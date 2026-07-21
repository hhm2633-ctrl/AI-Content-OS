import json
import tempfile
import unittest
from pathlib import Path

from modules.commerce import contract_loader
from modules.commerce.contract_loader import (
    COUPANG_CONTRACT,
    SMARTSTORE_CONTRACT,
    ContractLoadError,
    conditional_fields,
    load_contract,
    required_fields,
    workflow_control_defaults,
)


class ContractLoaderTests(unittest.TestCase):
    def test_load_contract_returns_builtin_for_known_platforms(self):
        self.assertEqual(load_contract("smartstore", config_path=Path("does_not_exist.json")), SMARTSTORE_CONTRACT)
        self.assertEqual(load_contract("coupang", config_path=Path("does_not_exist.json")), COUPANG_CONTRACT)

    def test_load_contract_rejects_unsupported_platform(self):
        with self.assertRaises(ContractLoadError):
            load_contract("gmarket")

    def test_required_fields_only_returns_required_classification(self):
        for field in required_fields("smartstore"):
            self.assertEqual(SMARTSTORE_CONTRACT[field]["classification"], "required")

    def test_conditional_fields_only_returns_conditional_classification(self):
        for field in conditional_fields("coupang"):
            self.assertEqual(COUPANG_CONTRACT[field]["classification"], "conditional")

    def test_workflow_control_defaults_coupang_is_never_go_live(self):
        self.assertIs(workflow_control_defaults("coupang")["requested"], False)

    def test_workflow_control_defaults_unknown_platform_is_empty(self):
        self.assertEqual(workflow_control_defaults("gmarket"), {})

    def test_no_field_references_nonexistent_verified_product_facts_root(self):
        # Regression guard: CommerceModule's real result has no
        # `verified_product_facts` key (confirmed by direct code reading) --
        # a contract field must never point there.
        for contract in (SMARTSTORE_CONTRACT, COUPANG_CONTRACT):
            for field_name, spec in contract.items():
                source = spec.get("phase1_source")
                if source:
                    self.assertNotIn(
                        "verified_product_facts", source,
                        msg=f"{field_name} still points at the nonexistent verified_product_facts root",
                    )

    def test_unknown_platform_field_never_guessed_stays_none(self):
        # UNKNOWN evidence-tier fields must keep platform_field=None rather
        # than a guessed key name (Fail Closed contract).
        self.assertIsNone(COUPANG_CONTRACT["price"]["platform_field"])
        self.assertIsNone(COUPANG_CONTRACT["stock"]["platform_field"])

    def test_marketplaces_json_override_merges_additively(self):
        override_config = {
            "contract_overrides": {
                "smartstore": {"category": {"platform_field": "originProduct.newLeafCategoryId"}}
            }
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "marketplaces.json"
            config_path.write_text(json.dumps(override_config), encoding="utf-8")

            merged = load_contract("smartstore", config_path=config_path)

            self.assertEqual(merged["category"]["platform_field"], "originProduct.newLeafCategoryId")
            # Every other field must survive untouched.
            self.assertEqual(merged["product_name"], SMARTSTORE_CONTRACT["product_name"])
            self.assertEqual(len(merged), len(SMARTSTORE_CONTRACT))

    def test_malformed_marketplaces_json_falls_back_to_builtin(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "marketplaces.json"
            config_path.write_text("{not valid json", encoding="utf-8")

            self.assertEqual(load_contract("smartstore", config_path=config_path), SMARTSTORE_CONTRACT)

    def test_real_config_file_is_valid_and_loadable(self):
        # The actual config/commerce/marketplaces.json shipped this Sprint
        # must be well-formed and safely mergeable.
        real_path = Path(contract_loader.__file__).resolve().parents[2] / "config" / "commerce" / "marketplaces.json"
        merged = load_contract("smartstore", config_path=real_path)
        self.assertEqual(merged, SMARTSTORE_CONTRACT)


if __name__ == "__main__":
    unittest.main()
