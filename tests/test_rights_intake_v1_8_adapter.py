import json
import unittest
from pathlib import Path

from modules.compliance.rights_intake_v1_8_adapter import adapt_v1_8_fixture_file

FIXTURES_PATH = Path(
    "external_workclaude/content_portfolio_v1/RIGHTS_INTAKE_ATTACK_FIXTURES_V1_8_1.json"
)
ACCEPTANCE_MATRIX_PATH = Path(
    "external_workclaude/content_portfolio_v1/RIGHTS_INTAKE_ACCEPTANCE_MATRIX_V1_8_1.json"
)


@unittest.skipUnless(
    FIXTURES_PATH.is_file() and ACCEPTANCE_MATRIX_PATH.is_file(),
    "V1.8.1 read-only fixture/acceptance files are not present in this checkout",
)
class V1_8_AdapterFixtureAcceptanceTests(unittest.TestCase):
    """Runs the V1.9 adapter against Spark's own V1.8.1 fixtures/expectations.

    Both JSON files are read-only CTO/Spark deliverables under
    external_workclaude/content_portfolio_v1/ and are never written to by
    this test or by the adapter it exercises.
    """

    @classmethod
    def setUpClass(cls):
        cls.fixture_data = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
        cls.acceptance = json.loads(ACCEPTANCE_MATRIX_PATH.read_text(encoding="utf-8"))
        cls.output_set_id = cls.fixture_data["base_set_id"]
        cls.expectations = {
            item["case_id"]: item for item in cls.acceptance["fixture_expectations"]
        }
        cls.results = adapt_v1_8_fixture_file(cls.fixture_data["fixtures"], cls.output_set_id)

    def test_expectation_count_matches_fixture_count(self):
        self.assertEqual(len(self.expectations), 11)
        self.assertEqual(len(self.results), 11)
        self.assertEqual(set(self.expectations), set(self.results))

    def test_normal_case_passes_with_no_blocker(self):
        result = self.results["normal"]
        self.assertTrue(result["passed"])
        self.assertEqual(result["blocker_codes"], [])
        self.assertIsNotNone(result["normalized"])

    def test_all_ten_attack_cases_fail_with_expected_blocker(self):
        attack_case_ids = [case_id for case_id in self.expectations if case_id != "normal"]
        self.assertEqual(len(attack_case_ids), 10)
        for case_id in attack_case_ids:
            expected = self.expectations[case_id]
            result = self.results[case_id]
            with self.subTest(case=case_id):
                self.assertFalse(expected["expected_pass"])
                self.assertFalse(result["passed"], f"{case_id} unexpectedly passed")
                self.assertEqual(result["blocker_codes"], expected["expected_blocker_codes"])
                self.assertIsNone(result["normalized"])

    def test_pass_fail_totals_match_acceptance_matrix(self):
        pass_count = sum(1 for result in self.results.values() if result["passed"])
        fail_count = sum(1 for result in self.results.values() if not result["passed"])
        self.assertEqual(pass_count, self.acceptance["expected_pass_count"])
        self.assertEqual(fail_count, self.acceptance["expected_fail_count"])
        self.assertEqual(pass_count, 1)
        self.assertEqual(fail_count, 10)


if __name__ == "__main__":
    unittest.main()
