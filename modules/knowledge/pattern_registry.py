"""Append-only JSONL registry for validated learning patterns."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from modules.knowledge.pattern_contract import Pattern, PatternStatus, parse_version


class PatternRegistryError(ValueError):
    pass


class PatternRegistry:
    ACTIVE_STATUSES = {PatternStatus.CANDIDATE, PatternStatus.VERIFIED, PatternStatus.PROMOTED}
    ALLOWED_TRANSITIONS = {
        PatternStatus.CANDIDATE: {PatternStatus.VERIFIED, PatternStatus.REJECTED},
        PatternStatus.VERIFIED: {PatternStatus.PROMOTED, PatternStatus.REJECTED},
        PatternStatus.PROMOTED: {PatternStatus.DEPRECATED},
        PatternStatus.DEPRECATED: set(),
        PatternStatus.REJECTED: set(),
    }

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or "knowledge/patterns/pattern_registry.jsonl")

    def load_all(self) -> List[Pattern]:
        if not self.path.exists():
            return []
        patterns: List[Pattern] = []
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, 1):
                    if not line.strip():
                        continue
                    try:
                        patterns.append(Pattern.from_dict(json.loads(line)))
                    except (json.JSONDecodeError, ValueError, TypeError) as exc:
                        raise PatternRegistryError(
                            f"invalid registry record at line {line_number}: {exc}"
                        ) from exc
        except OSError as exc:
            raise PatternRegistryError(f"could not read registry: {exc}") from exc
        self._validate_history(patterns)
        return patterns

    def list_patterns(self, *, status: Optional[PatternStatus] = None, current_only: bool = True) -> List[Pattern]:
        patterns = list(self.current().values()) if current_only else self.load_all()
        if status is not None:
            wanted = PatternStatus(status)
            patterns = [pattern for pattern in patterns if pattern.status is wanted]
        return sorted(patterns, key=lambda item: (item.domain.casefold(), item.name.casefold(), parse_version(item.version)))

    def current(self) -> Dict[str, Pattern]:
        current: Dict[str, Pattern] = {}
        for pattern in self.load_all():
            previous = current.get(pattern.pattern_id)
            if previous is None or parse_version(pattern.version) > parse_version(previous.version):
                current[pattern.pattern_id] = pattern
        return current

    def get(self, pattern_id: str) -> Optional[Pattern]:
        return self.current().get(pattern_id)

    def require(self, pattern_id: str) -> Pattern:
        pattern = self.get(pattern_id)
        if pattern is None:
            raise PatternRegistryError(f"unknown pattern_id: {pattern_id}")
        return pattern

    def register(self, pattern: Pattern) -> Pattern:
        return self._register(pattern, promotion_authorized=False)

    def _register(self, pattern: Pattern, *, promotion_authorized: bool) -> Pattern:
        if not isinstance(pattern, Pattern):
            pattern = Pattern.from_dict(pattern)
        if pattern.status is PatternStatus.PROMOTED and not promotion_authorized:
            raise PatternRegistryError("PROMOTED patterns must use promote() with explicit gates")
        history = self.load_all()
        self._validate_addition(pattern, history)
        self._append_safely(pattern)
        return pattern

    add = register

    def promote(
        self,
        pattern: Pattern,
        *,
        performance_met: bool,
        human_approved: bool,
    ) -> Pattern:
        """Register a PROMOTED version after both external gates are explicit."""
        if pattern.status is not PatternStatus.PROMOTED:
            raise PatternRegistryError("promotion record must have PROMOTED status")
        if performance_met is not True:
            raise PatternRegistryError("promotion requires demonstrated performance")
        if human_approved is not True:
            raise PatternRegistryError("promotion requires explicit human approval")
        pattern.validate_promotion_contract()
        return self._register(pattern, promotion_authorized=True)

    def _validate_addition(self, pattern: Pattern, history: List[Pattern]) -> None:
        current = self._current_from(history)
        previous = current.get(pattern.pattern_id)
        if previous:
            if parse_version(pattern.version) <= parse_version(previous.version):
                raise PatternRegistryError("version must progress beyond the current version")
            if pattern.status not in self.ALLOWED_TRANSITIONS[previous.status]:
                raise PatternRegistryError(f"invalid status transition: {previous.status.value} -> {pattern.status.value}")
        elif any(item.pattern_id == pattern.pattern_id and item.version == pattern.version for item in history):
            raise PatternRegistryError("duplicate pattern version")

        fingerprint = self._fingerprint(pattern)
        for other in current.values():
            if other.pattern_id != pattern.pattern_id and other.status in self.ACTIVE_STATUSES:
                if self._fingerprint(other) == fingerprint:
                    raise PatternRegistryError(f"semantic duplicate of current pattern: {other.pattern_id}")

        if pattern.supersedes and pattern.supersedes not in current:
            raise PatternRegistryError(f"supersedes target does not exist: {pattern.supersedes}")
        prospective = dict(current)
        prospective[pattern.pattern_id] = pattern
        self._check_cycles(prospective)

    def _validate_history(self, patterns: List[Pattern]) -> None:
        seen = set()
        accumulated: List[Pattern] = []
        for pattern in patterns:
            key = (pattern.pattern_id, parse_version(pattern.version))
            if key in seen:
                raise PatternRegistryError(f"duplicate pattern version: {pattern.pattern_id} {pattern.version}")
            seen.add(key)
            self._validate_addition(pattern, accumulated)
            accumulated.append(pattern)

    @staticmethod
    def _current_from(patterns: Iterable[Pattern]) -> Dict[str, Pattern]:
        result: Dict[str, Pattern] = {}
        for pattern in patterns:
            if pattern.pattern_id not in result or parse_version(pattern.version) > parse_version(result[pattern.pattern_id].version):
                result[pattern.pattern_id] = pattern
        return result

    @staticmethod
    def _fingerprint(pattern: Pattern) -> tuple:
        normalize = lambda value: re.sub(r"[^a-z0-9가-힣]+", " ", value.casefold()).strip()
        return (
            normalize(pattern.domain),
            normalize(pattern.name),
            normalize(pattern.recommended_action),
            tuple(sorted(normalize(item) for item in pattern.preconditions)),
        )

    @staticmethod
    def _check_cycles(patterns: Dict[str, Pattern]) -> None:
        for start in patterns:
            visited = set()
            cursor = start
            while cursor in patterns and patterns[cursor].supersedes:
                if cursor in visited:
                    raise PatternRegistryError("supersedes cycle detected")
                visited.add(cursor)
                cursor = patterns[cursor].supersedes  # type: ignore[assignment]

    def _append_safely(self, pattern: Pattern) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existing = b""
        if self.path.exists():
            existing = self.path.read_bytes()
            if existing and not existing.endswith(b"\n"):
                existing += b"\n"
        record = (json.dumps(pattern.to_dict(), ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        temporary_name = None
        try:
            with tempfile.NamedTemporaryFile("wb", delete=False, dir=self.path.parent) as handle:
                temporary_name = handle.name
                handle.write(existing)
                handle.write(record)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.path)
        except OSError as exc:
            if temporary_name:
                Path(temporary_name).unlink(missing_ok=True)
            raise PatternRegistryError(f"could not write registry: {exc}") from exc
