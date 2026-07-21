"""Strict, metadata-only contract for Knowledge Library source records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import re
from pathlib import PureWindowsPath
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class KnowledgeContractError(ValueError):
    """Raised when a source packet is unsafe or violates the schema."""


class SourceStatus(str, Enum):
    RECEIVED = "RECEIVED"
    VERIFIED = "VERIFIED"
    ANALYZED = "ANALYZED"
    ROUTED = "ROUTED"
    ADOPTED = "ADOPTED"
    HELD = "HELD"
    REJECTED = "REJECTED"
    STALE = "STALE"


REQUIRED_FIELDS = (
    "source_id", "title", "source_type", "original_url", "local_path",
    "received_at", "provided_by", "user_intent", "content_hash", "publisher",
    "published_at", "rights_status", "authority_level", "verification_status",
    "analysis_status", "summary", "project_relevance", "risks", "tags",
    "related_domains", "routed_teams", "adoption_decision", "decision_reason",
    "recheck_at", "related_documents",
)
ALLOWED_FIELDS = frozenset((*REQUIRED_FIELDS, "status"))
LIST_FIELDS = frozenset(("risks", "tags", "related_domains", "routed_teams", "related_documents"))
NULLABLE_FIELDS = frozenset(("original_url", "local_path", "published_at", "recheck_at"))
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
_HASH_RE = re.compile(r"^(?:sha256:)?([0-9a-fA-F]{64})$")
_SECRET_RE = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|passwd|authorization)\s*[:=]\s*[^\s&]+"
)
_SENSITIVE_QUERY = {"token", "access_token", "api_key", "apikey", "key", "secret", "password", "auth"}


def _text(value: Any, name: str, *, max_length: int = 4000, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise KnowledgeContractError(f"{name} must be a string")
    value = " ".join(value.strip().split())
    if not value:
        raise KnowledgeContractError(f"{name} must not be empty")
    if len(value) > max_length:
        raise KnowledgeContractError(f"{name} exceeds {max_length} characters")
    return _SECRET_RE.sub(lambda m: m.group(0).split(":", 1)[0].split("=", 1)[0] + ":***REDACTED***", value)


def normalize_url(value: Any) -> str | None:
    value = _text(value, "original_url", max_length=2048, nullable=True)
    if value is None:
        return None
    parts = urlsplit(value)
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        raise KnowledgeContractError("original_url must be an absolute http(s) URL")
    if parts.username or parts.password:
        raise KnowledgeContractError("original_url must not contain credentials")
    host = parts.hostname.lower()
    port = f":{parts.port}" if parts.port else ""
    query = urlencode(
        sorted((key, "***REDACTED***" if key.lower() in _SENSITIVE_QUERY else val)
               for key, val in parse_qsl(parts.query, keep_blank_values=True))
    )
    return urlunsplit((parts.scheme.lower(), host + port, parts.path or "/", query, ""))


def normalize_local_path(value: Any) -> str | None:
    value = _text(value, "local_path", max_length=1024, nullable=True)
    if value is None:
        return None
    path = PureWindowsPath(value)
    if path.is_absolute() or path.drive or value.startswith(("\\\\", "//")) or ".." in path.parts:
        raise KnowledgeContractError("local_path must be a safe repository-relative path")
    normalized = "/".join(part for part in path.parts if part not in (".", ""))
    if not normalized:
        raise KnowledgeContractError("local_path must not be empty")
    return normalized


def _timestamp(value: Any, name: str, *, nullable: bool = False) -> str | None:
    value = _text(value, name, max_length=64, nullable=nullable)
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise KnowledgeContractError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise KnowledgeContractError(f"{name} must include a timezone")
    return parsed.isoformat()


def _string_list(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise KnowledgeContractError(f"{name} must be a list")
    cleaned = {_text(item, name, max_length=256) for item in value}
    return tuple(sorted(cleaned, key=lambda item: (item.casefold(), item)))


@dataclass(frozen=True)
class SourcePacket:
    source_id: str
    title: str
    source_type: str
    original_url: str | None
    local_path: str | None
    received_at: str
    provided_by: str
    user_intent: str
    content_hash: str
    publisher: str
    published_at: str | None
    rights_status: str
    authority_level: str
    verification_status: str
    analysis_status: str
    summary: str
    project_relevance: str
    risks: tuple[str, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    related_domains: tuple[str, ...] = field(default_factory=tuple)
    routed_teams: tuple[str, ...] = field(default_factory=tuple)
    adoption_decision: str = "HELD"
    decision_reason: str = "Not yet decided"
    recheck_at: str | None = None
    related_documents: tuple[str, ...] = field(default_factory=tuple)
    status: SourceStatus = SourceStatus.RECEIVED

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "SourcePacket":
        if not isinstance(raw, Mapping):
            raise KnowledgeContractError("packet must be an object")
        unknown = set(raw) - ALLOWED_FIELDS
        missing = set(REQUIRED_FIELDS) - set(raw)
        if unknown or missing:
            raise KnowledgeContractError(f"schema mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}")
        source_id = _text(raw["source_id"], "source_id", max_length=128)
        if not _ID_RE.fullmatch(source_id):
            raise KnowledgeContractError("source_id has an invalid format")
        match = _HASH_RE.fullmatch(str(raw["content_hash"]).strip())
        if not match:
            raise KnowledgeContractError("content_hash must be a SHA-256 digest")
        status_value = raw.get("status", SourceStatus.RECEIVED.value)
        try:
            status = SourceStatus(status_value)
        except ValueError as exc:
            raise KnowledgeContractError("invalid status") from exc
        values: dict[str, Any] = {
            "source_id": source_id,
            "original_url": normalize_url(raw["original_url"]),
            "local_path": normalize_local_path(raw["local_path"]),
            "received_at": _timestamp(raw["received_at"], "received_at"),
            "published_at": _timestamp(raw["published_at"], "published_at", nullable=True),
            "recheck_at": _timestamp(raw["recheck_at"], "recheck_at", nullable=True),
            "content_hash": f"sha256:{match.group(1).lower()}",
            "status": status,
        }
        for name in LIST_FIELDS:
            values[name] = _string_list(raw[name], name)
        for name in REQUIRED_FIELDS:
            if name not in values:
                limit = 16000 if name in {"summary", "project_relevance", "decision_reason"} else 1000
                values[name] = _text(raw[name], name, max_length=limit)
        if values["original_url"] is None and values["local_path"] is None:
            raise KnowledgeContractError("one of original_url or local_path is required")
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        for name in LIST_FIELDS:
            result[name] = list(result[name])
        return result

    @property
    def canonical_hash(self) -> str:
        return hashlib.sha256(repr(sorted(self.to_dict().items())).encode("utf-8")).hexdigest()


def validate_source_packet(raw: Mapping[str, Any] | SourcePacket) -> SourcePacket:
    return raw if isinstance(raw, SourcePacket) else SourcePacket.from_dict(raw)
