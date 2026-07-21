"""Read-only integrity validator for the Knowledge Library registry.

The validator deliberately parses each record independently so one corrupt JSONL
line cannot hide findings in the remainder of the registry.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qsl, urlsplit

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from modules.knowledge.knowledge_contract import REQUIRED_FIELDS, SourceStatus, validate_source_packet
from modules.knowledge.pattern_contract import Pattern, PatternStatus


DEFAULT_REGISTRY = REPOSITORY_ROOT / "knowledge" / "registry" / "source_registry.jsonl"
DEFAULT_PATTERNS = REPOSITORY_ROOT / "knowledge" / "patterns" / "pattern_registry.jsonl"
SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2, "critical": 3}
TOKEN_KEYS = {"token", "access_token", "api_key", "apikey", "key", "secret", "password", "auth", "signature", "sig"}
TOKEN_TEXT_RE = re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|authorization)\s*[:=]\s*[^\s&]+")
COPYRIGHT_MARKERS = re.compile(r"(?i)(all rights reserved|copyright(?:ed)?|무단\s*(?:전재|복제)|저작권)")
PROMOTED_VALUES = {"promoted", "adopted", "approved", "production"}


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str
    source_id: str | None = None
    location: str | None = None
    field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


def _finding(code: str, severity: str, message: str, *, record: Mapping[str, Any] | None = None,
             location: str | None = None, field: str | None = None) -> Finding:
    source_id = record.get("source_id") if isinstance(record, Mapping) else None
    return Finding(code, severity, message, str(source_id) if source_id else None, location, field)


def _read_records(path: Path) -> tuple[list[tuple[dict[str, Any], str]], list[Finding]]:
    findings: list[Finding] = []
    records: list[tuple[dict[str, Any], str]] = []
    if not path.is_file():
        return records, [Finding("REGISTRY_NOT_FOUND", "critical", "Registry file does not exist", location=str(path))]
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return records, [Finding("REGISTRY_UNREADABLE", "critical", f"Registry cannot be read: {exc}", location=str(path))]
    stripped = text.lstrip()
    if path.suffix.lower() == ".json" or stripped.startswith("["):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            return records, [Finding("MALFORMED_JSON", "critical", exc.msg, location=f"{path}:{exc.lineno}")]
        candidates = payload if isinstance(payload, list) else payload.get("sources", payload.get("records")) if isinstance(payload, dict) else None
        if not isinstance(candidates, list):
            return records, [Finding("INVALID_REGISTRY_ROOT", "critical", "JSON registry must be a list or contain sources/records", location=str(path))]
        for index, raw in enumerate(candidates, 1):
            location = f"{path}#{index}"
            if isinstance(raw, dict): records.append((raw, location))
            else: findings.append(Finding("INVALID_RECORD", "error", "Registry record must be an object", location=location))
        return records, findings
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip(): continue
        location = f"{path}:{line_number}"
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            findings.append(Finding("MALFORMED_JSONL", "critical", exc.msg, location=location)); continue
        if isinstance(raw, dict): records.append((raw, location))
        else: findings.append(Finding("INVALID_RECORD", "error", "JSONL record must be an object", location=location))
    return records, findings


def _token_url(url: Any) -> bool:
    if not isinstance(url, str): return False
    try:
        parts = urlsplit(url)
        return bool(parts.username or parts.password or any(key.casefold() in TOKEN_KEYS and value not in {"", "***REDACTED***"}
                   for key, value in parse_qsl(parts.query, keep_blank_values=True)))
    except ValueError:
        return False


def _resolve_document(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip(): return None
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts: return None
    resolved = (root / candidate).resolve()
    try: resolved.relative_to(root.resolve())
    except ValueError: return None
    return resolved


def validate_registry(path: Path, *, root: Path, now: datetime | None = None,
                      patterns_path: Path | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    records, findings = _read_records(path)
    seen: dict[str, dict[str, str]] = defaultdict(dict)
    valid_count = 0
    for raw, location in records:
        compact = "name" in raw or "locator" in raw
        required_fields = ("source_id", "name", "locator", "tags", "authority", "status", "related_docs", "routed_team", "recheck") if compact else REQUIRED_FIELDS
        nullable_fields = set() if compact else {"original_url", "local_path", "published_at", "recheck_at"}
        for field in required_fields:
            if field not in raw or raw[field] == "" or (raw[field] is None and field not in nullable_fields):
                findings.append(_finding("MISSING_REQUIRED_FIELD", "error", f"Required field is missing: {field}", record=raw, location=location, field=field))
        if "status" not in raw:
            findings.append(_finding("MISSING_STATUS", "error", "Explicit status is required by the library registry", record=raw, location=location, field="status"))
        elif not compact and raw.get("status") not in {item.value for item in SourceStatus}:
            findings.append(_finding("INVALID_STATUS", "error", f"Unknown status: {raw.get('status')!r}", record=raw, location=location, field="status"))
        if compact:
            packet = None
            if all(field in raw and raw[field] not in (None, "") for field in required_fields) and isinstance(raw.get("tags"), list) and isinstance(raw.get("related_docs"), list):
                valid_count += 1
            else:
                findings.append(_finding("SCHEMA_INVALID", "error", "Compact registry fields have invalid types or values", record=raw, location=location))
        else:
            try:
                packet = validate_source_packet(raw)
                valid_count += 1
            except (TypeError, ValueError) as exc:
                findings.append(_finding("SCHEMA_INVALID", "error", str(exc), record=raw, location=location))
                packet = None
        for field in ("source_id", "content_hash", "original_url"):
            value = raw.get(field)
            if not value: continue
            key = str(value).casefold()
            if key in seen[field]:
                findings.append(_finding("DUPLICATE_ID" if field == "source_id" else "DUPLICATE_VALUE", "error",
                    f"Duplicate {field}; first seen at {seen[field][key]}", record=raw, location=location, field=field))
            else: seen[field][key] = location
        if _token_url(raw.get("original_url")):
            findings.append(_finding("TOKEN_BEARING_URL", "critical", "URL contains credentials or a sensitive query value", record=raw, location=location, field="original_url"))
        for field, value in raw.items():
            if isinstance(value, str) and TOKEN_TEXT_RE.search(value):
                findings.append(_finding("SECRET_TEXT", "critical", "Field appears to contain a secret", record=raw, location=location, field=field))
        document_values = raw.get("related_docs" if compact else "related_documents", [])
        for document in document_values if isinstance(document_values, list) else []:
            target = _resolve_document(root, document)
            if target is None:
                findings.append(_finding("UNSAFE_DOCUMENT_PATH", "critical", f"Unsafe related document path: {document!r}", record=raw, location=location, field="related_documents"))
            elif not target.is_file():
                findings.append(_finding("BROKEN_DOCUMENT", "error", f"Related document does not exist: {document}", record=raw, location=location, field="related_documents"))
        stale = str(raw.get("status", "")).casefold() == "stale"
        recheck_at = raw.get("recheck_at")
        if isinstance(recheck_at, str):
            try: stale = stale or datetime.fromisoformat(recheck_at.replace("Z", "+00:00")) <= now
            except (ValueError, TypeError): pass
        if stale:
            findings.append(_finding("STALE_ENTRY", "warning", "Source is stale or past its recheck date", record=raw, location=location))
        is_pattern = str(raw.get("source_type", "")).casefold() in {"pattern", "promoted_pattern", "knowledge_pattern"}
        promoted = str(raw.get("adoption_decision", "")).casefold() in PROMOTED_VALUES or str(raw.get("status", "")).casefold() == "adopted"
        if is_pattern and promoted:
            docs = raw.get("related_documents") if isinstance(raw.get("related_documents"), list) else []
            if not docs:
                findings.append(_finding("PROMOTED_PATTERN_ORPHAN", "error", "Promoted pattern has no related document", record=raw, location=location))
            if not raw.get("original_url") and not raw.get("local_path"):
                findings.append(_finding("PROMOTED_PATTERN_SOURCELESS", "critical", "Promoted pattern has no source", record=raw, location=location))
        blob = "\n".join(str(raw.get(field, "")) for field in ("summary", "project_relevance"))
        restricted = str(raw.get("rights_status", "")).casefold() not in {"owned", "licensed", "public_domain", "fair_use_excerpt", "open"}
        if restricted and (len(blob) > 8000 or (len(blob) > 2000 and COPYRIGHT_MARKERS.search(blob))):
            findings.append(_finding("COPYRIGHTED_BLOB", "critical", "Large copyrighted or rights-unclear text blob is stored in metadata", record=raw, location=location))
        if packet and packet.local_path:
            target = _resolve_document(root, packet.local_path)
            if target is None:
                findings.append(_finding("UNSAFE_SOURCE_PATH", "critical", "local_path escapes repository root", record=raw, location=location, field="local_path"))
            elif not target.exists():
                findings.append(_finding("BROKEN_SOURCE_PATH", "error", f"local_path does not exist: {packet.local_path}", record=raw, location=location, field="local_path"))
    pattern_records = 0
    valid_patterns = 0
    if patterns_path is not None:
        patterns, pattern_findings = _read_records(patterns_path)
        findings.extend(pattern_findings)
        pattern_records = len(patterns)
        source_ids = {str(raw.get("source_id")) for raw, _ in records if raw.get("source_id")}
        seen_versions: set[tuple[str, str]] = set()
        seen_pattern_ids: Counter[str] = Counter()
        for raw, location in patterns:
            pattern_id = str(raw.get("pattern_id", ""))
            version = str(raw.get("version", ""))
            key = (pattern_id, version)
            if key in seen_versions:
                findings.append(_finding("DUPLICATE_PATTERN_VERSION", "error", f"Duplicate pattern version: {pattern_id} {version}", location=location))
            seen_versions.add(key)
            seen_pattern_ids[pattern_id] += 1
            try:
                pattern = Pattern.from_dict(raw)
                valid_patterns += 1
            except (TypeError, ValueError) as exc:
                findings.append(_finding("PATTERN_SCHEMA_INVALID", "error", str(exc), location=location))
                continue
            if pattern.status is PatternStatus.PROMOTED:
                if not pattern.source_claim_ids:
                    findings.append(Finding("PROMOTED_PATTERN_SOURCELESS", "critical", "PROMOTED pattern has no source_claim_ids", pattern.pattern_id, location))
                missing_claims = sorted(set(pattern.source_claim_ids) - source_ids)
                if missing_claims:
                    findings.append(Finding("PROMOTED_PATTERN_ORPHAN", "critical", f"Source claims not found in source registry: {', '.join(missing_claims)}", pattern.pattern_id, location, "source_claim_ids"))
            if pattern.expires_at:
                try:
                    expires = datetime.fromisoformat(pattern.expires_at.replace("Z", "+00:00"))
                    if expires.tzinfo is None: expires = expires.replace(tzinfo=timezone.utc)
                    if expires <= now:
                        findings.append(Finding("STALE_PATTERN", "warning", "Pattern is past expires_at", pattern.pattern_id, location, "expires_at"))
                except ValueError:
                    pass
        # Multiple rows per pattern_id are valid append-only history; exact versions are not.
    findings.sort(key=lambda item: (-SEVERITY_ORDER[item.severity], item.code, item.location or ""))
    counts = Counter(item.severity for item in findings)
    status = "NO-GO" if counts["critical"] or counts["error"] else "GO"
    return {"schema_version": 1, "status": status, "registry": str(path), "pattern_registry": str(patterns_path) if patterns_path else None, "records_checked": len(records),
            "valid_records": valid_count, "finding_counts": {level: counts[level] for level in SEVERITY_ORDER},
            "patterns_checked": pattern_records, "valid_patterns": valid_patterns,
            "findings": [item.to_dict() for item in findings]}


def _render_text(report: Mapping[str, Any]) -> str:
    counts = report["finding_counts"]
    lines = [f"Knowledge Library validation: {report['status']}",
             f"Registry: {report['registry']}",
             f"Records: {report['records_checked']} checked, {report['valid_records']} schema-valid",
             f"Patterns: {report['patterns_checked']} checked, {report['valid_patterns']} schema-valid",
             "Findings: " + ", ".join(f"{key}={counts[key]}" for key in ("critical", "error", "warning", "info"))]
    for finding in report["findings"]:
        where = finding.get("location", report["registry"])
        source = f" [{finding['source_id']}]" if finding.get("source_id") else ""
        lines.append(f"- {finding['severity'].upper()} {finding['code']}{source} {where}: {finding['message']}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a Knowledge Library JSON/JSONL registry without modifying it.")
    parser.add_argument("registry", nargs="?", type=Path, default=None, help="registry path")
    parser.add_argument("--registry", type=Path, dest="registry_option", help=f"explicit registry path (default: {DEFAULT_REGISTRY})")
    parser.add_argument("--patterns", type=Path, default=DEFAULT_PATTERNS, help=f"pattern registry path (default: {DEFAULT_PATTERNS})")
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT, help="repository root for relative document checks")
    parser.add_argument("--format", choices=("text", "json"), default="text", dest="output_format")
    parser.add_argument("--fail-on-warning", action="store_true", help="return non-zero when warnings are present")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    registry = args.registry_option or args.registry or DEFAULT_REGISTRY
    report = validate_registry(registry, root=args.root.resolve(), patterns_path=args.patterns)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.output_format == "json" else _render_text(report))
    counts = report["finding_counts"]
    return 1 if report["status"] == "NO-GO" or (args.fail_on_warning and counts["warning"]) else 0


if __name__ == "__main__":
    sys.exit(main())
