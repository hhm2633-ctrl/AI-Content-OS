from typing import Any, Dict

POST_SCHEMA_FIELDS = (
    "account_handle",
    "account_url",
    "post_url",
    "post_shortcode",
    "observed_at",
    "posted_at_text",
    "post_type",
    "caption_text",
    "caption_length",
    "first_line",
    "line_break_count",
    "hashtags",
    "hashtag_count",
    "emoji_count",
    "visible_like_text",
    "visible_view_text",
    "visible_comment_text",
    "slide_count",
    "image_count",
    "is_sponsored_visible",
    "is_brand_account_observed",
    "screenshot_path",
    "source_method",
    "field_availability",
)

ALLOWED_POST_TYPES = ("carousel", "reel", "single_image", "unknown")

SENSITIVE_KEYS = (
    "password",
    "passwd",
    "cookie",
    "cookies",
    "session",
    "session_id",
    "sessionid",
    "auth_token",
    "access_token",
    "csrftoken",
)


def build_empty_post() -> Dict[str, Any]:
    return {field: None for field in POST_SCHEMA_FIELDS}


def contains_sensitive_keys(record: Any) -> bool:
    """Recursively scan a record for forbidden credential/session-like keys."""
    if isinstance(record, dict):
        for key, value in record.items():
            if isinstance(key, str) and key.strip().lower() in SENSITIVE_KEYS:
                return True
            if contains_sensitive_keys(value):
                return True
        return False
    if isinstance(record, (list, tuple, set)):
        return any(contains_sensitive_keys(item) for item in record)
    return False


def normalize_post_type(value: Any) -> str:
    if isinstance(value, str) and value in ALLOWED_POST_TYPES:
        return value
    return "unknown"


NUMERIC_FIELDS = (
    "caption_length",
    "line_break_count",
    "hashtag_count",
    "emoji_count",
    "slide_count",
    "image_count",
)


class ForbiddenFieldError(ValueError):
    """Raised when a raw record contains a credential/session-like field."""


def assert_no_forbidden_fields(record: Any) -> None:
    """Security boundary: refuse to even normalize a record carrying a
    credential/session-like key, rather than silently dropping it."""
    if contains_sensitive_keys(record):
        raise ForbiddenFieldError(
            "Record contains a forbidden credential/session-like field"
        )


def validate_post_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Validate an already-normalized post record. Never raises; returns a report."""
    if not isinstance(record, dict):
        return {"valid": False, "errors": ["record_not_a_dict"]}

    errors = []
    if record.get("post_type") not in ALLOWED_POST_TYPES:
        errors.append("invalid_post_type")

    for field in NUMERIC_FIELDS:
        value = record.get(field)
        if value is None:
            continue
        if isinstance(value, bool):
            errors.append(f"{field}_is_bool_not_numeric")
        elif not isinstance(value, (int, float)):
            errors.append(f"{field}_not_numeric")
        elif value < 0:
            errors.append(f"{field}_negative")

    return {"valid": len(errors) == 0, "errors": errors}
