"""Affiliate Revenue Router Phase 1 -- shared, dependency-free safety utilities.

Small, pure helper functions reused by `affiliate_contract.py`,
`affiliate_policy_gate.py`, and `affiliate_revenue_router.py`. No network I/O,
no file I/O, no imports from other AI-Content-OS engines -- self-contained per
this project's "reuse pattern, not code, across engines" convention (the URL
safety check mirrors the shape already proven in
`modules/card_news/evidence_input_validator.py::_valid_public_url`, rewritten
here rather than imported).
"""

from __future__ import annotations

import hashlib
import ipaddress
import math
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse


def is_safe_public_url(value: Any) -> bool:
    """True only for a credential-free public http(s) URL.

    Rejects embedded userinfo (`user:pass@host`), localhost, and private/
    loopback/link-local/reserved IP literals -- the same rejection surface as
    `evidence_input_validator.py`'s validator, applied here to affiliate
    destination/source/policy-evidence URLs instead of CardNews image
    sources.
    """
    if not isinstance(value, str) or not value.strip():
        return False

    try:
        parsed = urlparse(value.strip())
    except (ValueError, UnicodeError):
        return False

    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    if parsed.username is not None or parsed.password is not None:
        return False

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return False

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return True

    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
    )


def safe_number(value: Any) -> Optional[float]:
    """Return a finite, non-negative float, or `None` for anything else.

    Rejects booleans (which are technically `int` in Python), strings,
    `NaN`/`Infinity`, and negative values -- a malformed or adversarial
    commission/price value degrades to "unknown", never a crash and never a
    silently-trusted number.
    """
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return number


def parse_tz_datetime(value: Any) -> Optional[datetime]:
    """Return a UTC-normalized, timezone-aware `datetime`, or `None`.

    A naive `datetime`/ISO string (no explicit offset) is treated as invalid
    -- this module never guesses a timezone for a freshness-critical field.
    """
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            return None
        return value.astimezone(timezone.utc)

    if isinstance(value, str) and value.strip():
        normalized = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed.astimezone(timezone.utc)

    return None


def normalize_id_component(value: Any) -> str:
    """Sanitize a value for safe use inside a composite candidate/request id.

    Strips path-separator-shaped and other non-identifier characters so a
    hostile `request_id`/`program_id`/`offer_id` (e.g. containing `../`) can
    never make a generated composite id look like a filesystem path -- this
    module performs no file I/O itself, but ids may be echoed into logs or a
    future storage layer.
    """
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "")).strip("._")
    return (safe or "unspecified")[:80]


_JWT_SHAPE_PATTERN = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")
_SECRET_KEYWORD_PATTERN = re.compile(r"(token|secret|api[_-]?key|apikey|password|passwd|credential|auth)", re.IGNORECASE)
_HIGH_ENTROPY_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]{32,}")


def looks_like_sensitive_identifier(value: Any) -> bool:
    """True when a caller-supplied id string looks like it carries a secret,
    a JWT, a filesystem path, or another value that should never be echoed
    back verbatim in a result (NO-GO fix 12).

    Conservative/over-inclusive on purpose: a false positive here only means
    an ordinary-looking id gets replaced by an opaque hash, which is a
    harmless correlation inconvenience; a false negative would leak a secret.
    """
    text = str(value or "")
    if not text:
        return False
    if _JWT_SHAPE_PATTERN.match(text):
        return True
    if "/" in text or "\\" in text or ".." in text:
        return True
    if _SECRET_KEYWORD_PATTERN.search(text):
        return True
    if _HIGH_ENTROPY_TOKEN_PATTERN.search(text):
        return True
    return False


def make_id_output_safe(value: Any) -> str:
    """Return `value` unchanged if it looks like an ordinary id, or an
    irreversible opaque token (`opaque:<sha256-prefix>`) if it looks like it
    might carry a secret/path/JWT (see `looks_like_sensitive_identifier`).

    Deterministic (the same input always yields the same opaque token, so
    repeated requests can still be correlated) but never reversible back to
    the original value.
    """
    text = str(value or "")
    if not text:
        return text
    if not looks_like_sensitive_identifier(text):
        return text
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"opaque:{digest}"


def extract_hostname(value: Any) -> str:
    """Return the lowercased hostname of a URL, or `""` if it cannot be parsed."""
    if not isinstance(value, str) or not value.strip():
        return ""
    try:
        parsed = urlparse(value.strip())
    except (ValueError, UnicodeError):
        return ""
    return (parsed.hostname or "").rstrip(".").lower()
