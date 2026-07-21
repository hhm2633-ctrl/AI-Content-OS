"""Commerce Phase 2A — Credential Manager (DUMMY IMPLEMENTATION).

This is an explicit, intentional stub. Per this Sprint's hard constraints, no
real API call, login, or credential issuance is authorized -- so this module
must never read, hold, or return a real Naver/Coupang credential, even if one
happens to exist somewhere in the environment.

Design basis:
- `docs/RESEARCH/COMMERCE/SECURITY_COMPLIANCE_GATE.md` §1 (storage location,
  blast-radius reasoning), §8 (dev/sandbox/production environment separation),
  §9 (secret storage + log masking -- "no secret value may ever appear in any
  log line, in full or in part").
- `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.4 (credential storage).

Real behavior (Phase 2B+, NOT implemented here):
- TODO(Phase 2B): read `NAVER_COMMERCE_APP_ID` / `NAVER_COMMERCE_APP_SECRET` /
  `COUPANG_ACCESS_KEY` / `COUPANG_SECRET_KEY` from `.env` (or a dedicated
  secret manager, per SECURITY_COMPLIANCE_GATE.md §1.2's open CTO GATE on
  whether `.env` remains sufficient once real order/PII data is in scope).
- TODO(Phase 2B): implement the confirmed Coupang HMAC signing flow (Access
  Key + Secret Key, message = datetime+method+path+querystring, HmacSHA256,
  `Authorization: CEA algorithm=HmacSHA256, access-key=..., signed-date=...,
  signature=...`) -- CONFIRMED per PLATFORM_API_EVIDENCE_MATRIX.md.
- TODO(Phase 2B/CTO GATE): confirm and implement the Naver signing algorithm
  (bcrypt-based client_secret_sign is CONFIRMED (official channel); the full
  OAuth2 token-request flow around it remains UNKNOWN and must be verified
  directly against apicenter.commerce.naver.com before implementation).
- TODO(Phase 2B): rotation discipline per SECURITY_COMPLIANCE_GATE.md §1.3.
"""

from __future__ import annotations

from typing import Any, Dict

SUPPORTED_PLATFORMS = ("smartstore", "coupang")


class CredentialManager:
    """Always reports "no credentials configured" for every platform.

    This is by design, not a bug: Phase 2A is dry-run only, and this class
    exists so downstream code (`marketplace_base.py`, adapters) can already be
    written against a stable interface without any real secret ever entering
    the process. `has_credentials()` returning False is what forces every
    adapter's `submit()` path to stay blocked (see `marketplace_base.py`).
    """

    def __init__(self, config: Dict[str, Any] = None) -> None:
        self.config = config or {}
        # Explicitly NOT reading os.environ or .env here. See module docstring.

    def has_credentials(self, platform: str) -> bool:
        """Always False in this Sprint's skeleton -- see class docstring."""
        self._validate_platform(platform)
        return False

    def get_credential_status(self, platform: str) -> Dict[str, Any]:
        """Return a safe, secret-free status dict. Never includes a key value,
        a key prefix, or any value that could narrow down a real secret."""
        self._validate_platform(platform)

        return {
            "platform": platform,
            "configured": False,
            "source": "dummy_credential_manager",
            "reason": (
                "Commerce Phase 2A is dry-run only; real credential storage/retrieval "
                "is intentionally not implemented. See module docstring TODOs."
            ),
        }

    def redact(self, value: Any) -> str:
        """Utility for any future logging call that might otherwise be tempted
        to include a credential-shaped value. Always returns a fixed-length
        redaction marker, never a partial value (a partial prefix is still a
        real leak surface -- SECURITY_COMPLIANCE_GATE.md §9 forbids "in full
        or in part")."""
        return "***REDACTED***"

    @staticmethod
    def _validate_platform(platform: str) -> None:
        normalized = str(platform or "").strip().lower()
        if normalized not in SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported platform: {platform!r}. Supported: {SUPPORTED_PLATFORMS}")
