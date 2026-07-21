import unittest

from modules.source_intake.topic_input_quality_gate import run_topic_input_quality_gate


class TestTopicInputQualityGate(unittest.TestCase):
    def test_url_and_title_duplicates_collapse_deterministically_and_preserve_first(self):
        payload = {
            "trends": [
                {
                    "source_id": "source-a",
                    "source_name": "Alpha",
                    "keyword": "뉴스 A",
                    "title": "  시장 분석  ",
                    "link": "https://example.com/market?t=1&utm_source=feed",
                },
                {
                    "source_id": "source-b",
                    "source_name": "Beta",
                    "keyword": "중복 2",
                    "title": "다른 제목",
                    "link": "https://example.com/market?utm_medium=social&t=1",
                },
                {
                    "source_id": "source-c",
                    "source_name": "Gamma",
                    "title": "시장분석",
                    "link": "https://other.example.com/other",
                },
                {
                    "source_id": "source-d",
                    "source_name": "Delta",
                    "title": "  시장   분석",
                    "link": "https://example.com/market?utm_source=ads&t=1&utm_medium=ig",
                },
            ],
            "source_diagnostics": {"status": "ok", "ready_count": 4, "schema_version": "topic_input_source_diagnostics_v1"},
        }

        result = run_topic_input_quality_gate(payload)

        self.assertEqual(len(result["candidates"]), 2)
        first = result["candidates"][0]
        self.assertEqual(first["source_id"], "source-a")
        self.assertEqual(first["source_agreement"]["agreement_count"], 3)
        self.assertEqual(first["source_agreement"]["agreement_level"], "multi_source_observed")
        self.assertEqual(
            [item["source_id"] for item in first["source_agreement"]["sources"]],
            ["source-a", "source-b", "source-d"],
        )
        self.assertEqual(
            first["source_agreement"]["sources"][0]["link"],
            "https://example.com/market?t=1&utm_source=feed",
        )
        self.assertEqual(
            first["source_agreement"]["sources"][1]["link"],
            "https://example.com/market?utm_medium=social&t=1",
        )
        self.assertIsNone(first["source_agreement"]["sources"][0]["likes"])
        self.assertIsNone(first["source_agreement"]["sources"][0]["comments"])

    def test_distinct_source_ids_count_and_do_not_double_count_repeats(self):
        payload = {
            "trends": [
                {
                    "source_id": "source-a",
                    "source_name": "Alpha",
                    "keyword": "테크뉴스",
                    "title": "중복 제목",
                },
                {
                    "source_id": "source-a",
                    "source_name": "Alpha Duplicate",
                    "title": "중복 제목",
                    "link": "https://example.com/article",
                },
                {
                    "source_id": "source-b",
                    "source_name": "Beta",
                    "keyword": "다른",
                    "title": "중복 제목",
                },
                {
                    "source_id": "source-b",
                    "source_name": "Beta Duplicate",
                    "title": "완전 다른 제목",
                    "link": "https://example.com/other",
                },
            ],
            "source_diagnostics": {"status": "ok", "ready_count": 4, "schema_version": "topic_input_source_diagnostics_v1"},
        }

        result = run_topic_input_quality_gate(payload)

        self.assertEqual(len(result["candidates"]), 2)
        primary = result["candidates"][0]
        secondary = result["candidates"][1]
        self.assertEqual(primary["source_agreement"]["agreement_level"], "multi_source_observed")
        self.assertEqual(primary["source_agreement"]["agreement_count"], 2)
        self.assertEqual(
            [item["source_id"] for item in primary["source_agreement"]["sources"]],
            ["source-a", "source-b"],
        )
        self.assertEqual(secondary["source_agreement"]["agreement_level"], "single_source")
        self.assertEqual(secondary["source_agreement"]["agreement_count"], 1)
        self.assertEqual(len(secondary["source_agreement"]["sources"]), 1)

    def test_malformed_or_empty_input_fail_closed_without_fabricated_candidates(self):
        malformed_output = {
            "trends": ["bad-item"],
            "source_diagnostics": {"status": "ok", "schema_version": "topic_input_source_diagnostics_v1"},
        }
        malformed_result = run_topic_input_quality_gate(malformed_output)
        self.assertEqual(malformed_result["candidates"], [])
        self.assertEqual(malformed_result["quality_diagnostics"]["status"], "closed")
        self.assertEqual(malformed_result["quality_diagnostics"]["reason_code"], "malformed_trend")
        self.assertEqual(malformed_result["quality_diagnostics"].get("quality_gate_version"), "topic_input_quality_gate_v1")

        empty_result = run_topic_input_quality_gate(
            {
                "trends": [],
                "source_diagnostics": {"status": "ok", "schema_version": "topic_input_source_diagnostics_v1"},
            }
        )
        self.assertEqual(empty_result["candidates"], [])
        self.assertEqual(empty_result["quality_diagnostics"]["status"], "closed")
        self.assertEqual(empty_result["quality_diagnostics"]["reason_code"], "no_candidates")
        self.assertNotIn("selected_topic", empty_result["quality_diagnostics"])

    def test_explicit_zero_engagement_remains_observed_zero(self):
        result = run_topic_input_quality_gate({
            "trends": [{"source_id": "source-a", "title": "제로 반응", "likes": 0, "comments": 0}],
            "source_diagnostics": {"status": "ok", "schema_version": "topic_input_source_diagnostics_v1"},
        })
        source = result["candidates"][0]["source_agreement"]["sources"][0]
        self.assertEqual(0, source["likes"])
        self.assertEqual(0, source["comments"])

    def test_malformed_ipv6_url_fails_closed_without_exception(self):
        result = run_topic_input_quality_gate({
            "trends": [{"source_id": "source-a", "title": "잘못된 URL", "link": "https://["}],
            "source_diagnostics": {"status": "ok", "schema_version": "topic_input_source_diagnostics_v1"},
        })
        self.assertEqual("closed", result["quality_diagnostics"]["status"])
        self.assertEqual("malformed_trend", result["quality_diagnostics"]["reason_code"])


if __name__ == "__main__":
    unittest.main()
