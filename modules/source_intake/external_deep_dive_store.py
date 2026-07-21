"""Persist selected-topic heavy source artifacts outside the repository.

This writer is intentionally limited to owner-selected deep-dive material.  It
does not collect from the network and never moves or deletes existing files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Union

from modules.source_intake.source_intake_schema import (
    DEEP_DIVE_STAGE_CONTRACT,
    deep_dive_external_dir,
)


ArtifactPayload = Union[bytes, bytearray, str, Mapping[str, Any], list]


def _safe_leaf(value: str, field: str) -> str:
    leaf = str(value or "").strip()
    if not leaf or Path(leaf).name != leaf or leaf in {".", ".."}:
        raise ValueError(f"invalid_{field}")
    return leaf


def write_deep_dive_artifact(
    *,
    date_str: str,
    stage: str,
    source_id: str,
    filename: str,
    payload: ArtifactPayload,
    base_dir: str | None = None,
) -> Path:
    """Write one heavy artifact beneath the configured external F: root.

    ``base_dir`` exists for isolated tests and explicit operator overrides.  In
    production the configured ``F:/AI-Content-OS-Data`` root is used.
    """

    normalized_stage = str(stage or "").strip()
    if normalized_stage not in DEEP_DIVE_STAGE_CONTRACT:
        raise ValueError("unsupported_deep_dive_stage")

    safe_source_id = _safe_leaf(source_id, "source_id")
    safe_filename = _safe_leaf(filename, "filename")
    target_dir = Path(
        deep_dive_external_dir(
            str(date_str),
            normalized_stage,
            safe_source_id,
            base_dir=base_dir,
        )
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / safe_filename

    if isinstance(payload, (bytes, bytearray)):
        target.write_bytes(bytes(payload))
    elif isinstance(payload, str):
        target.write_text(payload, encoding="utf-8")
    elif isinstance(payload, (Mapping, list)):
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        raise TypeError("unsupported_artifact_payload")

    return target


__all__ = ["write_deep_dive_artifact"]
