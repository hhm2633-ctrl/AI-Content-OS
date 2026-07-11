import unittest

from modules.instagram_research.instagram_post_schema import (
    ALLOWED_POST_TYPES,
    POST_SCHEMA_FIELDS,
    ForbiddenFieldError,
    assert_no_forbidden_fields,
    build_empty_post,
    normalize_post_type,
    validate_post_record,
)
from modules.instagram_research.instagram_normalizer import build_post_record


class TestInstagramPostSchema(unittest.TestCase):
    def test_assert_no_forbidden_fields_passes_for_clean_input(self):
        assert_no_forbidden_fields({"account_handle": "brand", "caption_text": "hi"})

    def test_assert_no_forbidden_fields_rejects_cookie(self):
        with self.assertRaises(ForbiddenFieldError):
            assert_no_forbidden_fields({"cookie": "abc"})

    def test_assert_no_forbidden_fields_rejects_password(self):
        with self.assertRaises(ForbiddenFieldError):
            assert_no_forbidden_fields({"password": "abc"})

    def test_assert_no_forbidden_fields_rejects_session(self):
        with self.assertRaises(ForbiddenFieldError):
            assert_no_forbidden_fields({"session_id": "abc"})

    def test_build_post_record_contains_all_schema_fields(self):
        record = build_post_record({"account_handle": "brand"})
        for field in POST_SCHEMA_FIELDS:
            self.assertIn(field, record)

    def test_build_post_record_defaults_missing_fields_to_none(self):
        record = build_post_record({})
        self.assertIsNone(record["account_handle"])
        self.assertIsNone(record["screenshot_path"])
        self.assertIsNone(record["slide_count"])
        self.assertIsNone(record["image_count"])

    def test_build_post_record_handles_invalid_input_without_raising(self):
        self.assertEqual(build_post_record(None)["post_type"], "unknown")
        self.assertEqual(build_post_record("garbage")["post_type"], "unknown")
        self.assertEqual(build_post_record(123)["field_availability"], {})

    def test_build_post_record_ignores_unknown_fields(self):
        record = build_post_record({"account_handle": "brand", "totally_unknown_field": "x"})
        self.assertNotIn("totally_unknown_field", record)

    def test_build_post_record_raises_on_forbidden_field(self):
        with self.assertRaises(ForbiddenFieldError):
            build_post_record({"account_handle": "brand", "password": "hunter2"})

    def test_field_availability_defaults_to_empty_dict(self):
        record = build_post_record({"account_handle": "brand"})
        self.assertEqual(record["field_availability"], {})

    def test_hashtags_default_to_empty_list_when_none(self):
        record = build_post_record({"account_handle": "brand"})
        self.assertEqual(record["hashtags"], [])

    def test_normalize_post_type_accepts_supported_values(self):
        for value in ALLOWED_POST_TYPES:
            self.assertEqual(normalize_post_type(value), value)

    def test_normalize_post_type_falls_back_to_unknown(self):
        self.assertEqual(normalize_post_type("not_a_real_type"), "unknown")
        self.assertEqual(normalize_post_type(None), "unknown")
        self.assertEqual(normalize_post_type(123), "unknown")

    def test_validate_post_record_accepts_valid_record(self):
        record = build_empty_post()
        record["post_type"] = "carousel"
        record["caption_length"] = 10
        record["hashtag_count"] = 2
        result = validate_post_record(record)
        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], [])

    def test_validate_post_record_flags_invalid_post_type(self):
        record = build_empty_post()
        record["post_type"] = "not_a_real_type"
        result = validate_post_record(record)
        self.assertFalse(result["valid"])
        self.assertIn("invalid_post_type", result["errors"])

    def test_validate_post_record_rejects_bool_for_numeric_field(self):
        record = build_empty_post()
        record["post_type"] = "reel"
        record["caption_length"] = True
        result = validate_post_record(record)
        self.assertFalse(result["valid"])
        self.assertIn("caption_length_is_bool_not_numeric", result["errors"])

    def test_validate_post_record_rejects_negative_numeric_field(self):
        record = build_empty_post()
        record["post_type"] = "reel"
        record["slide_count"] = -1
        result = validate_post_record(record)
        self.assertFalse(result["valid"])
        self.assertIn("slide_count_negative", result["errors"])

    def test_zero_is_preserved_and_distinct_from_none(self):
        record = build_post_record({"account_handle": "brand", "caption_text": ""})
        self.assertEqual(record["hashtag_count"], 0)
        self.assertIsNone(record["slide_count"])
        self.assertNotEqual(record["hashtag_count"], record["slide_count"])


if __name__ == "__main__":
    unittest.main()
