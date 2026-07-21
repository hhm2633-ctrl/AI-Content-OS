"""Commerce Phase 2A — Audit Logger.

Append-only JSONL audit log for every dry-run payload build, validation, and
(future, Phase 2B+) real API interaction. Mirrors the shape already proposed
in `docs/RESEARCH/COMMERCE/ORDER_FULFILLMENT_STATE_MACHINE.md` §8 and
`docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.12, and the project's own
existing append-log convention (`trend_run_log.jsonl`, `knowledge_history.json`).

Hard rule (`docs/RESEARCH/COMMERCE/SECURITY_COMPLIANCE_GATE.md` §9): no secret
value, signature, or token may ever be written to this log, in full or in
part, at any verbosity level. This module never accepts a raw credential as an
argument -- only hashes, statuses, and free-text summaries the caller has
already sanitized. `credential_manager.redact()` exists specifically so a
caller has no excuse to pass a real value here.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_AUDIT_DIR = Path("storage/commerce/audit")

# Fields that must never appear in a logged entry, even if a caller mistakenly
# includes them -- defense in depth on top of "never pass a secret here".
_FORBIDDEN_KEYS = {
    "secret", "secret_key", "access_key", "api_key", "app_secret", "client_secret",
    "client_secret_sign", "signature", "token", "oauth_token", "password", "authorization",
}

_FORBIDDEN_KEY_MARKERS = (
    "secret", "credential", "password", "passwd", "token", "authorization",
    "signature", "apikey", "accesskey", "privatekey",
)

_FORBIDDEN_KEY_ALIASES = {"auth", "clientkey"}


class AuditLogger:
    def __init__(self, audit_dir: Optional[Path] = None) -> None:
        self.audit_dir = Path(audit_dir or DEFAULT_AUDIT_DIR)

    def log(self, entry: Dict[str, Any]) -> Optional[Path]:
        """Append one sanitized entry to today's audit log file.

        Never raises -- an audit-log write failure must not block or crash
        the dry-run pipeline (fail-safe, consistent with every other Engine's
        storage-write behavior in this project). Returns the written path, or
        None if the write failed.
        """
        try:
            self.audit_dir.mkdir(parents=True, exist_ok=True)
        except Exception as error:
            print(f"Commerce Audit Logger: could not create audit dir: {error}")
            return None

        sanitized = self._sanitize(entry)
        sanitized.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        sanitized.setdefault("mode", "dry_run")

        log_date = datetime.now(timezone.utc).strftime("%Y%m%d")
        log_path = self.audit_dir / f"commerce_audit_{log_date}.jsonl"

        try:
            with open(log_path, "a", encoding="utf-8") as file:
                file.write(json.dumps(sanitized, ensure_ascii=False) + "\n")
            return log_path
        except Exception as error:
            print(f"Commerce Audit Logger: write failed: {error}")
            return None

    def log_payload_built(
        self,
        platform: str,
        request_id: Optional[str],
        gaps: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Optional[Path]:
        return self.log({
            "type": "payload_built",
            "platform": platform,
            "phase1_request_id": request_id,
            "ready_field_count": len(gaps.get("ready", [])),
            "missing_field_count": len(gaps.get("missing", [])),
            "pending_confirmation_field_count": len(gaps.get("pending_confirmation", [])),
            "idempotency_key": idempotency_key,
        })

    def log_validation(
        self,
        platform: str,
        request_id: Optional[str],
        valid: bool,
        blocked_reason_count: int,
    ) -> Optional[Path]:
        return self.log({
            "type": "validation",
            "platform": platform,
            "phase1_request_id": request_id,
            "valid": valid,
            "blocked_reason_count": blocked_reason_count,
        })

    def log_approval_check(
        self,
        platform: str,
        capability: str,
        approved: bool,
        reason: str,
    ) -> Optional[Path]:
        return self.log({
            "type": "approval_check",
            "platform": platform,
            "capability": capability,
            "approved": approved,
            "reason": reason,
        })

    def log_submit_blocked(self, platform: str, reason: str) -> Optional[Path]:
        """Every Phase 2A `submit()` call is blocked by construction -- this
        records that fact so the audit trail shows the block actually
        happened, not just that it was supposed to."""
        return self.log({
            "type": "submit_blocked",
            "platform": platform,
            "reason": reason,
            "real_api_call_attempted": False,
        })

    def _sanitize(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(entry, dict):
            return {"type": "malformed_entry", "original_type": type(entry).__name__}

        sanitized: Dict[str, Any] = {}

        for key, value in entry.items():
            if self._is_forbidden_key(key):
                sanitized[key] = "***REDACTED***"
                continue

            sanitized[key] = self._sanitize_value(value)

        return sanitized

    @staticmethod
    def _is_forbidden_key(key: Any) -> bool:
        lowered_key = str(key).casefold()
        if lowered_key in _FORBIDDEN_KEYS:
            return True

        compact_key = re.sub(r"[^a-z0-9]", "", lowered_key)
        return (
            compact_key in _FORBIDDEN_KEY_ALIASES
            or any(marker in compact_key for marker in _FORBIDDEN_KEY_MARKERS)
        )

    def _sanitize_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return self._sanitize(value)
        if isinstance(value, (list, tuple)):
            return [self._sanitize_value(item) for item in value]
        if isinstance(value, str) and self._looks_like_secret(value):
            return "***REDACTED***"
        return value

    @staticmethod
    def _looks_like_secret(value: str) -> bool:
        candidate = value.strip()
        lowered = candidate.casefold()

        if re.match(r"^(?:bearer|basic)\s+\S+$", candidate, re.IGNORECASE):
            return True
        if re.search(
            r"(?:secret|credential|password|passwd|token|authorization|signature|"
            r"api[_-]?key|access[_-]?key|private[_-]?key)\s*[:=]\s*\S+",
            lowered,
        ):
            return True
        if re.fullmatch(r"[A-Za-z0-9_-]{8,}(?:\.[A-Za-z0-9_-]{8,}){2,}", candidate):
            return True

        # Fail closed for long single-token credential material. Unlike the
        # old alphanumeric-only check, common separators and base64 padding do
        # not create a redaction bypass.
        return (
            len(candidate) >= 20
            and not any(char.isspace() for char in candidate)
            and any(char.isalpha() for char in candidate)
            and any(char.isdigit() for char in candidate)
            and all(char.isalnum() or char in "-_.+/=" for char in candidate)
        )
