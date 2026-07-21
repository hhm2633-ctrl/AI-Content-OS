"""Validated contract for reusable learning patterns."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class PatternStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    VERIFIED = "VERIFIED"
    PROMOTED = "PROMOTED"
    DEPRECATED = "DEPRECATED"
    REJECTED = "REJECTED"


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, field: str, *, allow_empty: bool = True) -> List[str]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be a list of strings")
    result = []
    for item in value:
        text = _nonempty(item, field)
        if text not in result:
            result.append(text)
    if not allow_empty and not result:
        raise ValueError(f"{field} must not be empty")
    return result


def parse_version(value: str) -> tuple[int, ...]:
    """Return a comparable numeric version tuple (for example ``1.2.0``)."""
    text = _nonempty(value, "version")
    parts = text.split(".")
    if not all(part.isdigit() for part in parts):
        raise ValueError("version must contain dot-separated non-negative integers")
    normalized = [int(part) for part in parts]
    while len(normalized) > 1 and normalized[-1] == 0:
        normalized.pop()
    return tuple(normalized)


def _iso_datetime(value: Optional[str], field: str) -> Optional[str]:
    if value in (None, ""):
        return None
    text = _nonempty(value, field)
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 datetime") from exc
    return text


@dataclass
class Pattern:
    pattern_id: str
    name: str
    domain: str
    source_claim_ids: List[str]
    preconditions: List[str]
    recommended_action: str
    prohibited_actions: List[str]
    success_metrics: List[str]
    failure_signals: List[str]
    confidence: float
    status: PatternStatus
    version: str
    reviewed_at: Optional[str]
    owner_skill: str
    supersedes: Optional[str]
    expires_at: Optional[str]

    def __post_init__(self) -> None:
        self.pattern_id = _nonempty(self.pattern_id, "pattern_id")
        self.name = _nonempty(self.name, "name")
        self.domain = _nonempty(self.domain, "domain")
        self.source_claim_ids = _string_list(self.source_claim_ids, "source_claim_ids")
        self.preconditions = _string_list(self.preconditions, "preconditions")
        self.recommended_action = _nonempty(self.recommended_action, "recommended_action")
        self.prohibited_actions = _string_list(self.prohibited_actions, "prohibited_actions")
        self.success_metrics = _string_list(self.success_metrics, "success_metrics")
        self.failure_signals = _string_list(self.failure_signals, "failure_signals")
        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise ValueError("confidence must be a number from 0 to 1")
        self.confidence = float(self.confidence)
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be a number from 0 to 1")
        try:
            self.status = PatternStatus(self.status)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid pattern status") from exc
        parse_version(self.version)
        self.reviewed_at = _iso_datetime(self.reviewed_at, "reviewed_at")
        self.owner_skill = _nonempty(self.owner_skill, "owner_skill")
        self.supersedes = None if self.supersedes in (None, "") else _nonempty(self.supersedes, "supersedes")
        self.expires_at = _iso_datetime(self.expires_at, "expires_at")
        if self.supersedes == self.pattern_id:
            raise ValueError("a pattern cannot supersede itself")
        if self.status is PatternStatus.PROMOTED:
            self.validate_promotion_contract()

    def validate_promotion_contract(self) -> None:
        if not self.source_claim_ids:
            raise ValueError("PROMOTED patterns require source_claim_ids")
        if not self.success_metrics:
            raise ValueError("PROMOTED patterns require success_metrics")
        if not self.reviewed_at:
            raise ValueError("PROMOTED patterns require reviewed_at human review evidence")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Pattern":
        if not isinstance(data, dict):
            raise ValueError("pattern record must be an object")
        expected = set(cls.__dataclass_fields__)
        missing = expected.difference(data)
        extra = set(data).difference(expected)
        if missing:
            raise ValueError(f"missing pattern fields: {', '.join(sorted(missing))}")
        if extra:
            raise ValueError(f"unknown pattern fields: {', '.join(sorted(extra))}")
        return cls(**data)
