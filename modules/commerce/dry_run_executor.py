"""Commerce Phase 2A — Dry Run Executor.

Orchestrates one platform's full dry-run pipeline: build payload -> validate
-> check approval status -> persist a dry-run artifact -> audit log. This is
the "Dry Run First" entry point `commerce_engine.py` calls per platform.

Never makes a network call, never touches real credentials, never writes
outside `storage/commerce/dryrun/`.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from modules.commerce.audit_logger import AuditLogger
from modules.commerce.marketplace_base import MarketplaceAdapterBase

DEFAULT_DRYRUN_DIR = Path("storage/commerce/dryrun")


class DryRunExecutor:
    def __init__(
        self,
        dryrun_dir: Optional[Path] = None,
        audit_logger: Optional[AuditLogger] = None,
    ) -> None:
        self.dryrun_dir = Path(dryrun_dir or DEFAULT_DRYRUN_DIR)
        self.audit_logger = audit_logger or AuditLogger()

    def run(
        self,
        adapter: MarketplaceAdapterBase,
        commerce_result: Dict[str, Any],
        persist: bool = True,
    ) -> Dict[str, Any]:
        """Execute one adapter's dry-run pipeline and return the full result.

        Never raises on a malformed `commerce_result` -- `adapter.dry_run()`
        already degrades safely (payload_builder returns all-missing fields
        rather than raising), so this method's only additional job is
        persistence + top-level audit logging, both of which are
        best-effort/non-fatal.
        """
        dry_run_result = adapter.dry_run(commerce_result)

        dry_run_result["executor_metadata"] = {
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "persisted": False,
            "output_path": None,
        }

        if persist:
            output_path = self._persist(adapter.platform_name, commerce_result, dry_run_result)
            dry_run_result["executor_metadata"]["persisted"] = output_path is not None
            dry_run_result["executor_metadata"]["output_path"] = str(output_path) if output_path else None

        return dry_run_result

    def _persist(
        self,
        platform: str,
        commerce_result: Dict[str, Any],
        dry_run_result: Dict[str, Any],
    ) -> Optional[Path]:
        request_id = self._safe_request_id(
            commerce_result.get("request_id") if isinstance(commerce_result, dict) else None
        )
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target_dir = self.dryrun_dir / request_id
        target_path = target_dir / f"{platform}_dryrun_{timestamp}.json"

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as file:
                json.dump(dry_run_result, file, ensure_ascii=False, indent=2)
            return target_path
        except Exception as error:
            print(f"Commerce Dry Run Executor: persist failed: {error}")
            return None

    @staticmethod
    def _safe_request_id(value: Any) -> str:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "commerce_request")).strip("._")
        return (safe or "commerce_request")[:80]
