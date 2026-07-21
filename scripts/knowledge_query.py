"""Read-only query CLI for the Knowledge Library JSONL registry.

The CLI deliberately reads JSONL directly instead of instantiating
``KnowledgeRegistry``: one malformed line must be reported without hiding valid
records.  It never creates, repairs, or rewrites library data.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path, PurePath
import re
import sys
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_CANDIDATES = (
    ROOT / "knowledge" / "registry" / "source_registry.jsonl",
    ROOT / "library" / "knowledge_registry.jsonl",
    ROOT / "storage" / "knowledge" / "library_registry.jsonl",
    ROOT / "storage" / "knowledge" / "knowledge_registry.jsonl",
    ROOT / "docs" / "KNOWLEDGE" / "library_registry.jsonl",
)
DEFAULT_PATTERN_REGISTRY = ROOT / "knowledge" / "patterns" / "pattern_registry.jsonl"
AUTHORITY_ORDER = {
    "official": 0, "primary": 1, "authoritative": 1, "verified": 2,
    "secondary": 3, "community": 4, "unknown": 5,
}
SECRET_RE = re.compile(
    r"(?i)((?:api[_-]?key|access[_-]?token|client[_-]?secret|password|passwd|authorization)\s*[:=]\s*)[^\s&]+"
)
PRIVATE_PATH_RE = re.compile(
    r"(?i)(?:[a-z]:[\\/](?:users|documents and settings)[\\/][^\s\"']+|/(?:home|users)/[^\s\"']+)"
)
SENSITIVE_QUERY = {"token", "access_token", "api_key", "apikey", "key", "secret", "password", "auth"}


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item is not None]
    return []


def _first(record: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in record:
            return record[name]
    return None


def _redact_url(value: str) -> str:
    try:
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            return value
        host = parts.hostname or ""
        if parts.port:
            host += f":{parts.port}"
        query = urlencode([
            (key, "***REDACTED***" if key.casefold() in SENSITIVE_QUERY else val)
            for key, val in parse_qsl(parts.query, keep_blank_values=True)
        ])
        return urlunsplit((parts.scheme, host, parts.path, query, ""))
    except (ValueError, UnicodeError):
        return "[REDACTED_URL]"


def redact(value: Any, *, key: str = "") -> Any:
    """Recursively remove secrets, credentials, and private absolute paths."""
    if isinstance(value, Mapping):
        return {str(k): redact(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item, key=key) for item in value]
    if not isinstance(value, str):
        return value
    normalized_key = key.casefold().replace("-", "_")
    if normalized_key in {
        "secret", "client_secret", "password", "passwd", "token",
        "access_token", "api_key", "apikey", "authorization",
    }:
        return "***REDACTED***"
    if re.match(r"(?i)^(?:[a-z]:[\\/](?:users|documents and settings)[\\/]|/(?:home|users)/)", value):
        return "[REDACTED_PRIVATE_PATH]"
    cleaned = SECRET_RE.sub(r"\1***REDACTED***", value)
    cleaned = PRIVATE_PATH_RE.sub("[REDACTED_PRIVATE_PATH]", cleaned)
    return _redact_url(cleaned)


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def freshness_of(record: Mapping[str, Any], *, now: datetime | None = None) -> str:
    explicit = str(record.get("freshness", "")).casefold()
    if explicit in {"fresh", "stale", "unknown"}:
        return explicit
    if str(record.get("status", "")).casefold() == "stale":
        return "stale"
    recheck = _parse_time(record.get("recheck_at"))
    if recheck is not None:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        return "stale" if recheck <= current else "fresh"
    return "unknown"


def _authority_rank(record: Mapping[str, Any]) -> tuple[int, str]:
    authority = str(_first(record, "authority_level", "authority") or "unknown").casefold()
    rank = next((score for label, score in AUTHORITY_ORDER.items() if label in authority), 5)
    return rank, str(record.get("source_id", record.get("id", "")))


def _contains(record: Mapping[str, Any], needle: str) -> bool:
    fields = (
        record.get("source_id"), record.get("title"), record.get("name"), record.get("summary"),
        record.get("project_relevance"), record.get("publisher"), record.get("tags"),
        record.get("related_domains"), record.get("routed_teams"), record.get("routed_team"),
        record.get("locator"), record.get("related_docs"),
    )
    return needle.casefold() in " ".join(str(item) for item in fields if item is not None).casefold()


def _matches_values(actual: Any, expected: Sequence[str]) -> bool:
    if not expected:
        return True
    values = {item.casefold() for item in _as_list(actual)}
    return all(item.casefold() in values for item in expected)


def load_registry(path: Path, *, registry_kind: str = "source") -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return valid object rows and non-fatal diagnostics; never mutate *path*."""
    records: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    raw = json.loads(line)
                    if not isinstance(raw, dict):
                        raise ValueError("row is not a JSON object")
                    records.append(raw)
                except (json.JSONDecodeError, ValueError) as exc:
                    diagnostics.append({"code": "malformed_jsonl", "registry": registry_kind, "line": number, "message": str(exc)})
    except OSError as exc:
        diagnostics.append({"code": "registry_unavailable", "registry": registry_kind, "message": str(exc)})
    return records, diagnostics


def _unique(items: Iterable[Any]) -> list[Any]:
    """Stable de-duplication for scalar and JSON-shaped related metadata."""
    result: list[Any] = []
    seen: set[str] = set()
    for item in items:
        try:
            marker = json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
        except (TypeError, ValueError):
            marker = repr(item)
        if marker not in seen:
            seen.add(marker)
            result.append(item)
    return result


def query_knowledge(
    registry: str | Path, *, patterns_registry: str | Path | None = None,
    text: str | None = None, tags: Sequence[str] = (),
    domains: Sequence[str] = (), status: Sequence[str] = (), authority: Sequence[str] = (),
    freshness: Sequence[str] = (), source_type: Sequence[str] = (),
    routed_team: Sequence[str] = (), limit: int | None = None,
) -> dict[str, Any]:
    """Build a safe, deterministic KnowledgeBundle from a JSONL registry."""
    path = Path(registry)
    records, diagnostics = load_registry(path)
    selected = []
    for record in records:
        if text and not _contains(record, text): continue
        if not _matches_values(record.get("tags"), tags): continue
        if not _matches_values(_first(record, "related_domains", "domains", "domain"), domains): continue
        if not _matches_values(record.get("status"), status): continue
        if not _matches_values(_first(record, "authority_level", "authority"), authority): continue
        if not _matches_values(freshness_of(record), freshness): continue
        if not _matches_values(record.get("source_type"), source_type): continue
        if not _matches_values(_first(record, "routed_teams", "routed_team"), routed_team): continue
        enriched = dict(record)
        enriched["freshness"] = freshness_of(record)
        selected.append(enriched)
    selected.sort(key=_authority_rank)
    if limit is not None:
        selected = selected[:max(0, limit)]

    documents: list[str] = []
    contradictions: list[Any] = []
    for record in selected:
        documents.extend(_as_list(_first(record, "related_documents", "related_docs", "documents")))
        contradictions.extend(_as_list(record.get("contradictions")))
        contradictions.extend(risk for risk in _as_list(record.get("risks")) if "contradict" in risk.casefold() or "충돌" in risk)
    states = {"stale": [], "unknown": []}
    for record in selected:
        state = freshness_of(record)
        if state in states:
            states[state].append(record.get("source_id", record.get("id", "unknown")))
    pattern_path = Path(patterns_registry) if patterns_registry is not None else DEFAULT_PATTERN_REGISTRY
    pattern_rows, pattern_diagnostics = load_registry(pattern_path, registry_kind="pattern")
    diagnostics.extend(pattern_diagnostics)
    selected_ids = {str(item.get("source_id", "")) for item in selected if item.get("source_id")}
    related_history = [
        item for item in pattern_rows
        if selected_ids.intersection(_as_list(item.get("source_claim_ids")))
    ]
    # The append-only registry may contain multiple versions.  A bundle returns
    # the latest numeric version per pattern_id while leaving malformed rows in diagnostics.
    related_by_id: dict[str, dict[str, Any]] = {}
    for item in related_history:
        pattern_id = str(item.get("pattern_id", ""))
        if not pattern_id:
            continue
        previous = related_by_id.get(pattern_id)
        def version_key(record: Mapping[str, Any]) -> tuple[int, ...]:
            try:
                return tuple(int(part) for part in str(record.get("version", "0")).split("."))
            except ValueError:
                return (0,)
        if previous is None or version_key(item) > version_key(previous):
            related_by_id[pattern_id] = item
    related_patterns = sorted(related_by_id.values(), key=lambda item: str(item.get("pattern_id", "")))
    bundle = {
        "bundle_type": "KnowledgeBundle",
        "registry": str(path),
        "count": len(selected),
        "sources": selected,
        "documents": _unique(documents),
        "pattern_registry": str(pattern_path),
        "pattern_ids": [item["pattern_id"] for item in related_patterns],
        "patterns": related_patterns,
        "stale": states["stale"],
        "unknown": states["unknown"],
        "contradictions": _unique(contradictions),
        "diagnostics": diagnostics,
        "read_only": True,
    }
    return redact(bundle)


def _default_registry() -> Path:
    return next((path for path in DEFAULT_REGISTRY_CANDIDATES if path.is_file()), DEFAULT_REGISTRY_CANDIDATES[0])


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Knowledge Library query")
    parser.add_argument("--registry", type=Path, default=None, help="JSONL registry path")
    parser.add_argument("--patterns", type=Path, default=None, help="pattern JSONL registry path")
    parser.add_argument("--text", help="case-insensitive text search")
    parser.add_argument("--tag", action="append", default=[], help="required tag (repeatable)")
    parser.add_argument("--domain", action="append", default=[], help="required related domain (repeatable)")
    parser.add_argument("--status", action="append", default=[], help="required source status (repeatable)")
    parser.add_argument("--authority", action="append", default=[], help="required authority level (repeatable)")
    parser.add_argument("--freshness", action="append", choices=("fresh", "stale", "unknown"), default=[])
    parser.add_argument("--source-type", action="append", default=[], help="required source type (repeatable)")
    parser.add_argument("--routed-team", action="append", default=[], help="required routed team (repeatable)")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    return parser


def _render_text(bundle: Mapping[str, Any]) -> str:
    lines = [f"KnowledgeBundle: {bundle['count']} source(s)"]
    for source in bundle["sources"]:
        authority = source.get("authority_level", source.get("authority", "unknown"))
        lines.append(f"- {source.get('source_id', source.get('id', '?'))}: {source.get('title', '(untitled)')} [{authority}; {source['freshness']}]")
    lines.extend((
        f"Documents: {', '.join(bundle['documents']) or '-'}",
        f"Patterns: {', '.join(bundle['pattern_ids']) or '-'}",
        f"Stale: {', '.join(bundle['stale']) or '-'}",
        f"Unknown freshness: {', '.join(bundle['unknown']) or '-'}",
        f"Contradictions: {' | '.join(map(str, bundle['contradictions'])) or '-'}",
        f"Diagnostics: {len(bundle['diagnostics'])}",
    ))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    bundle = query_knowledge(
        args.registry or _default_registry(), patterns_registry=args.patterns,
        text=args.text, tags=args.tag, domains=args.domain,
        status=args.status, authority=args.authority, freshness=args.freshness,
        source_type=args.source_type, routed_team=args.routed_team, limit=args.limit,
    )
    if args.format == "json":
        print(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(_render_text(bundle))
    source_unavailable = any(
        item["code"] == "registry_unavailable" and item.get("registry") == "source"
        for item in bundle["diagnostics"]
    )
    return 2 if source_unavailable else 0


if __name__ == "__main__":
    sys.exit(main())
