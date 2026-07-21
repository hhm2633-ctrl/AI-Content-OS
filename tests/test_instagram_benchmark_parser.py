"""Independent coverage for modules/competitor_engine/instagram_benchmark_parser.py.

Priority-2 gap-fill test: `modules/competitor_engine/` (a 10-file engine) has
zero tests anywhere in the repo today. This parser already accepts an
injectable `path` constructor kwarg, so it can be tested entirely against
synthetic in-memory markdown fixtures written to a temp directory -- no real
`benchmark/INSTAGRAM_BENCHMARK.md` file is read or modified, and no existing
module or test file is touched.
"""

import tempfile
import unittest
from pathlib import Path

from modules.competitor_engine.instagram_benchmark_parser import InstagramBenchmarkParser


SAMPLE_MARKDOWN = """# Instagram Benchmark

### @sample_account
Category: 자기계발
Priority: high
Observed Pattern:
- 손글씨 노트 스타일로 신뢰감 형성
- 질문형 후킹으로 시작

Common Hooks:
- "이거 모르면 손해입니다"

AI-Content-OS 적용:
- 체크리스트 형태로 재구성
- 저장 유도 CTA 강화

### @another_account
Category: 비교 콘텐츠
Priority: medium
Observed Pattern:
- 두 제품을 비교하는 표 형식

## Key Learnings
- This section and anything after it must never be parsed as an account.
### @should_not_be_parsed
Category: ignored
"""

EMPTY_SECTION_MARKDOWN = """# Instagram Benchmark

### @bare_account
"""

MALFORMED_MARKDOWN = """# Instagram Benchmark

###
Category: no handle above
"""


class InstagramBenchmarkParserTests(unittest.TestCase):
    def _parser_for(self, markdown_text: str) -> InstagramBenchmarkParser:
        tmp_dir = tempfile.mkdtemp()
        path = Path(tmp_dir) / "INSTAGRAM_BENCHMARK.md"
        path.write_text(markdown_text, encoding="utf-8")
        return InstagramBenchmarkParser(path=path)

    def test_missing_file_returns_safe_unavailable_result(self):
        parser = InstagramBenchmarkParser(path=Path("this/path/does/not/exist.md"))
        result = parser.parse()

        self.assertEqual(result["status"], "instagram_benchmark_unavailable")
        self.assertEqual(result["accounts"], [])
        self.assertTrue(result["fallback_used"])

    def test_parses_expected_number_of_accounts(self):
        parser = self._parser_for(SAMPLE_MARKDOWN)
        result = parser.parse()

        self.assertEqual(result["status"], "instagram_benchmark_parsed")
        self.assertFalse(result["fallback_used"])
        self.assertEqual(len(result["accounts"]), 2)

    def test_content_after_stop_marker_is_never_parsed_as_an_account(self):
        parser = self._parser_for(SAMPLE_MARKDOWN)
        result = parser.parse()

        handles = [account["account"] for account in result["accounts"]]
        self.assertNotIn("@should_not_be_parsed", handles)

    def test_category_and_priority_fields_are_extracted(self):
        parser = self._parser_for(SAMPLE_MARKDOWN)
        result = parser.parse()

        first_account = result["accounts"][0]
        self.assertEqual(first_account["account"], "@sample_account")
        self.assertEqual(first_account["category"], "자기계발")
        self.assertEqual(first_account["priority"], "high")

    def test_observed_pattern_bullets_are_collected(self):
        parser = self._parser_for(SAMPLE_MARKDOWN)
        result = parser.parse()

        first_account = result["accounts"][0]
        self.assertEqual(len(first_account["observed_pattern"]), 2)
        self.assertIn("손글씨 노트 스타일로 신뢰감 형성", first_account["observed_pattern"])

    def test_layout_signal_inferred_from_handwriting_keyword(self):
        parser = self._parser_for(SAMPLE_MARKDOWN)
        result = parser.parse()

        first_account = result["accounts"][0]
        self.assertEqual(first_account["layout_signal"], "notebook")

    def test_layout_signal_inferred_from_comparison_keyword(self):
        parser = self._parser_for(SAMPLE_MARKDOWN)
        result = parser.parse()

        second_account = result["accounts"][1]
        self.assertEqual(second_account["layout_signal"], "comparison")

    def test_cta_signals_matched_from_applications_section(self):
        parser = self._parser_for(SAMPLE_MARKDOWN)
        result = parser.parse()

        first_account = result["accounts"][0]
        self.assertIn("save", first_account["cta_signals"])

    def test_pattern_signal_falls_back_to_category_when_no_observed_pattern(self):
        parser = self._parser_for(EMPTY_SECTION_MARKDOWN)
        result = parser.parse()

        account = result["accounts"][0]
        self.assertEqual(account["account"], "@bare_account")
        self.assertEqual(account["observed_pattern"], [])
        self.assertEqual(account["pattern_signal"], "")  # no category either -- empty, not fabricated

    def test_image_strategy_signal_defaults_to_text_overlay_when_no_keyword_matches(self):
        parser = self._parser_for(EMPTY_SECTION_MARKDOWN)
        result = parser.parse()

        self.assertEqual(result["accounts"][0]["image_strategy_signal"], "text_overlay")

    def test_blank_handle_section_is_skipped_not_crashed_on(self):
        parser = self._parser_for(MALFORMED_MARKDOWN)
        result = parser.parse()

        self.assertEqual(result["status"], "instagram_benchmark_parsed")
        self.assertEqual(result["accounts"], [])

    def test_unreadable_file_falls_back_safely(self):
        tmp_dir = tempfile.mkdtemp()
        # A directory where a file is expected -- read_text() will raise.
        path = Path(tmp_dir) / "is_a_directory.md"
        path.mkdir()
        parser = InstagramBenchmarkParser(path=path)

        result = parser.parse()
        self.assertEqual(result["status"], "instagram_benchmark_error")
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["accounts"], [])

    def test_parse_is_deterministic_for_same_file(self):
        parser = self._parser_for(SAMPLE_MARKDOWN)
        result_one = parser.parse()
        result_two = parser.parse()
        self.assertEqual(result_one, result_two)


if __name__ == "__main__":
    unittest.main()
