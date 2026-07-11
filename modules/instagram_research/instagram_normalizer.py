import re
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Tuple, Sequence

from .instagram_post_schema import assert_no_forbidden_fields, build_empty_post, normalize_post_type

_OG_DESCRIPTION_RE = re.compile(
    r"^(?P<likes>[\d,.가-힣\s]+?)\s*(?:likes|개)?,\s*"
    r"(?P<comments>[\d,.가-힣\s]+?)\s*(?:comments|개)?\s*-\s*"
    r"(?P<handle>[^-]+?)\s*-\s*"
    r"(?P<date>[^:\"]+?)"
    r"(?::\s*\"(?P<caption>.*)\"\.?\s*)?$",
    re.DOTALL,
)

_HASHTAG_RE = re.compile(r"#+([^\s#]+)")

_EMOJI_RANGE_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF"
    "]"
)

_SHORTCODE_RE = re.compile(r"/(?:p|reel)/([^/?#]+)/?")

_VISIBLE_COUNT_RE = re.compile(r"^([\d,]+(?:\.\d+)?)\s*(만|천)?\s*(?:개)?$")

INSTAGRAM_DOMAIN = "https://www.instagram.com"

EXPECTED_SCREENSHOT_DIR = "storage/research/instagram/screenshots"


def normalize_url(url: Optional[str]) -> Optional[str]:
    if not isinstance(url, str) or not url.strip():
        return None
    normalized = url.strip().split("?")[0].split("#")[0]
    if normalized.startswith("/"):
        normalized = INSTAGRAM_DOMAIN + normalized
    elif not normalized.startswith("http://") and not normalized.startswith("https://"):
        normalized = INSTAGRAM_DOMAIN + "/" + normalized.lstrip("/")
    while len(normalized) > 1 and normalized.endswith("/"):
        normalized = normalized[:-1]
    return normalized


def extract_shortcode(post_url: Optional[str]) -> Optional[str]:
    if not isinstance(post_url, str):
        return None
    match = _SHORTCODE_RE.search(post_url)
    if not match:
        return None
    return match.group(1)


def parse_og_description(og_description: Optional[str]) -> Dict[str, Optional[str]]:
    """Parse Instagram's server-rendered og:description meta content.

    Format observed: '<likes> likes, <comments> comments - <handle> - <date>: "<caption>".'
    The caption clause is absent when the post has no caption text.
    """
    result: Dict[str, Optional[str]] = {
        "visible_like_text": None,
        "visible_comment_text": None,
        "posted_at_text": None,
        "caption_text": None,
    }
    if not isinstance(og_description, str) or not og_description.strip():
        return result

    match = _OG_DESCRIPTION_RE.match(og_description.strip())
    if not match:
        return result

    likes = match.group("likes")
    comments = match.group("comments")
    date = match.group("date")
    caption = match.group("caption")

    result["visible_like_text"] = likes.strip() if likes else None
    result["visible_comment_text"] = comments.strip() if comments else None
    result["posted_at_text"] = date.strip() if date else None
    if caption is not None:
        result["caption_text"] = caption.replace("\\n", "\n")
    return result


def normalize_hashtags(caption_text: Optional[str]) -> List[str]:
    if not isinstance(caption_text, str) or not caption_text:
        return []
    tags = []
    seen = set()
    for group in _HASHTAG_RE.findall(caption_text):
        tag = "#" + group
        if tag not in seen:
            seen.add(tag)
            tags.append(tag)
    return tags


def count_emojis(text: Optional[str]) -> int:
    if not isinstance(text, str) or not text:
        return 0
    return len(_EMOJI_RANGE_RE.findall(text))


def count_emoji(text: Optional[str]) -> Optional[int]:
    """Like count_emojis, but preserves None input as None (missing vs. zero)."""
    if text is None:
        return None
    if not isinstance(text, str):
        return None
    return len(_EMOJI_RANGE_RE.findall(text))


def count_hashtags(hashtags: Optional[List[str]]) -> Optional[int]:
    """Counts an already-extracted hashtag list. None input stays None
    (missing/unobserved), distinct from an observed empty list (0)."""
    if hashtags is None:
        return None
    if not isinstance(hashtags, list):
        return None
    return len(hashtags)


def parse_visible_count_text(text: Optional[str]) -> Optional[int]:
    """Parses a visible like/view/comment count string into an integer.
    Handles comma-formatted numbers ('1,234', '1,234개') and Korean 만/천
    units ('1.2만' -> 12000, '5천' -> 5000). Returns None for missing/
    unparseable input."""
    if not isinstance(text, str) or not text.strip():
        return None
    match = _VISIBLE_COUNT_RE.match(text.strip())
    if not match:
        return None
    number_str = match.group(1).replace(",", "")
    try:
        number = float(number_str)
    except ValueError:
        return None
    unit = match.group(2)
    if unit == "만":
        number *= 10000
    elif unit == "천":
        number *= 1000
    return int(round(number))


def sanitize_screenshot_path(
    path: Optional[str], expected_dir: str = EXPECTED_SCREENSHOT_DIR
) -> Optional[str]:
    """Returns the path unchanged if it is a relative path confined to
    expected_dir, or None if it is absolute, escapes via '..', or falls
    outside expected_dir."""
    if not isinstance(path, str) or not path.strip():
        return None
    normalized = path.strip().replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[a-zA-Z]:", normalized):
        return None
    parts = PurePosixPath(normalized).parts
    if ".." in parts:
        return None
    expected_parts = PurePosixPath(expected_dir).parts
    if parts[: len(expected_parts)] != expected_parts:
        return None
    return normalized


def compute_caption_metrics(caption_text: Optional[str]) -> Dict[str, Any]:
    """caption_text is None when a post genuinely has no caption (confirmed
    absence, not a failed observation) -> zeros are legitimate here."""
    if caption_text is None:
        return {
            "caption_length": 0,
            "first_line": None,
            "line_break_count": 0,
            "hashtags": [],
            "hashtag_count": 0,
            "emoji_count": 0,
        }
    lines = caption_text.split("\n")
    return {
        "caption_length": len(caption_text),
        "first_line": lines[0].strip() if lines and lines[0].strip() else (lines[0] if lines else None),
        "line_break_count": caption_text.count("\n"),
        "hashtags": normalize_hashtags(caption_text),
        "hashtag_count": len(normalize_hashtags(caption_text)),
        "emoji_count": count_emojis(caption_text),
    }


def normalize_caption(caption_text: Optional[str]) -> Dict[str, Any]:
    """Alias of compute_caption_metrics, kept as the named entry point
    other engines/tests refer to for caption normalization."""
    return compute_caption_metrics(caption_text)


def build_post_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one manually-observed post dict into the full post schema.
    Malformed/missing fields degrade to None/'unknown' and never raise.
    Exception: a forbidden credential/session-like key in raw raises
    ForbiddenFieldError (security boundary, not a data-quality issue)."""
    assert_no_forbidden_fields(raw)
    record = build_empty_post()
    if not isinstance(raw, dict):
        record["post_type"] = "unknown"
        record["field_availability"] = {}
        return record

    account_handle = raw.get("account_handle")
    post_url = normalize_url(raw.get("post_url"))
    og_parsed = parse_og_description(raw.get("og_description"))
    caption_text = raw.get("caption_text", og_parsed["caption_text"])
    caption_metrics = compute_caption_metrics(caption_text)

    record.update({
        "account_handle": account_handle,
        "account_url": normalize_url(raw.get("account_url")),
        "post_url": post_url,
        "post_shortcode": extract_shortcode(post_url),
        "observed_at": raw.get("observed_at"),
        "posted_at_text": raw.get("posted_at_text") or og_parsed["posted_at_text"],
        "post_type": normalize_post_type(raw.get("post_type")),
        "caption_text": caption_text,
        "caption_length": caption_metrics["caption_length"],
        "first_line": caption_metrics["first_line"],
        "line_break_count": caption_metrics["line_break_count"],
        "hashtags": caption_metrics["hashtags"],
        "hashtag_count": caption_metrics["hashtag_count"],
        "emoji_count": caption_metrics["emoji_count"],
        "visible_like_text": raw.get("visible_like_text") or og_parsed["visible_like_text"],
        "visible_view_text": raw.get("visible_view_text"),
        "visible_comment_text": raw.get("visible_comment_text") or og_parsed["visible_comment_text"],
        "slide_count": raw.get("slide_count"),
        "image_count": raw.get("image_count"),
        "is_sponsored_visible": raw.get("is_sponsored_visible"),
        "is_brand_account_observed": raw.get("is_brand_account_observed"),
        "screenshot_path": sanitize_screenshot_path(raw.get("screenshot_path")),
        "source_method": raw.get("source_method", "playwright_mcp_manual_observation"),
        "field_availability": raw.get("field_availability", {}),
    })
    return record


def dedupe_posts(posts: Optional[Sequence[Dict[str, Any]]]) -> Tuple[List[Dict[str, Any]], int]:
    """Dedupe by (account_handle, post_shortcode). Keeps first occurrence.
    None/non-sequence input is treated as an empty list."""
    if not posts:
        return [], 0
    seen = set()
    deduped = []
    duplicate_count = 0
    for post in posts:
        if not isinstance(post, dict):
            continue
        key = (post.get("account_handle"), post.get("post_shortcode") or post.get("post_url"))
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        deduped.append(post)
    return deduped, duplicate_count
