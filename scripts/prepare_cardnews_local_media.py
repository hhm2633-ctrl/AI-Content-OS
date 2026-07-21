"""Validate or explicitly execute one package-only local-media request.

The command is fail-closed: it does not execute media tools unless ``--execute``
is supplied, never writes over the input/source, and writes receipts only below
the configured absolute F: output root.  It does not render or publish.
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "external_tools" / "local_media_pipeline.json"
TERMINAL_FAILURE_STATUSES = frozenset({"blocked", "failed"})


def _load_object(path: Path, label: str) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"{label}_must_be_json_object")
    return dict(value)


def _blocked(reason_code: str, detail: str) -> Dict[str, Any]:
    return {
        "schema_version": "local_media_cli_receipt.v1",
        "status": "blocked",
        "reason_code": reason_code,
        "detail": detail,
        "package_only": True,
        "tools_executed": False,
        "render_executed": False,
        "publish_executed": False,
    }


def _configured_output_root(config: Mapping[str, Any]) -> Path:
    value = config.get("output_root")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("CONFIG_OUTPUT_ROOT_MISSING")
    root = Path(value).resolve()
    if not root.is_absolute() or root.drive.lower() != "f:":
        raise ValueError("CONFIG_OUTPUT_ROOT_NOT_ABSOLUTE_F_DRIVE")
    return root


def _receipt_path_error(
    input_path: Path,
    receipt_path: Path,
    output_root: Path,
    request: Mapping[str, Any],
) -> Dict[str, Any] | None:
    resolved_input = input_path.resolve()
    resolved_receipt = receipt_path.resolve()
    if not resolved_receipt.is_absolute() or resolved_receipt.drive.lower() != "f:":
        return _blocked(
            "OUTPUT_RECEIPT_NOT_ABSOLUTE_F_DRIVE",
            "output receipt must be an absolute F: path",
        )
    if resolved_receipt == output_root or output_root not in resolved_receipt.parents:
        return _blocked(
            "OUTPUT_RECEIPT_OUTSIDE_CONFIGURED_ROOT",
            "output receipt must be below the configured output_root",
        )
    if resolved_receipt == resolved_input:
        return _blocked(
            "INPUT_OVERWRITE_FORBIDDEN",
            "output receipt must not overwrite the input JSON",
        )

    source_values: list[Any] = [request.get("source_path")]
    assets = request.get("assets")
    if isinstance(assets, list):
        source_values.extend(
            asset.get("source_path")
            for asset in assets
            if isinstance(asset, Mapping)
        )
    for value in source_values:
        if isinstance(value, (str, Path)) and str(value).strip():
            if resolved_receipt == Path(value).resolve():
                return _blocked(
                    "SOURCE_OVERWRITE_FORBIDDEN",
                    "output receipt must not overwrite a declared source",
                )
    return None


def _call_core(request: Mapping[str, Any], config: Mapping[str, Any]) -> Dict[str, Any]:
    module = importlib.import_module("modules.media_intelligence.local_media_pipeline")
    result = module.prepare_local_media(dict(request), config=dict(config))
    if not isinstance(result, Mapping):
        return _blocked("CORE_RECEIPT_MALFORMED", "core result must be a JSON object")
    return dict(result)


def _write_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(receipt), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Explicit request JSON")
    parser.add_argument(
        "--output-receipt",
        required=True,
        type=Path,
        help="Receipt JSON below the configured absolute F: output root",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Explicitly allow configured local preparation tools to run",
    )
    args = parser.parse_args(argv)

    receipt: Dict[str, Any]
    safe_receipt_path: Path | None = None
    try:
        config = _load_object(args.config, "config")
        output_root = _configured_output_root(config)
        request = _load_object(args.input, "input")
        path_error = _receipt_path_error(
            args.input, args.output_receipt, output_root, request
        )
        if path_error is not None:
            receipt = path_error
        else:
            safe_receipt_path = args.output_receipt.resolve()
            prepared_request = dict(request)
            prepared_request["execute"] = bool(args.execute)
            prepared_request["validate_only"] = not args.execute
            receipt = _call_core(prepared_request, config)
    except (OSError, ValueError, json.JSONDecodeError, ImportError) as exc:
        receipt = _blocked("CLI_INPUT_OR_CONFIG_INVALID", str(exc))
    except Exception as exc:  # fail closed at the package boundary
        receipt = _blocked("LOCAL_MEDIA_CORE_ERROR", str(exc))

    if safe_receipt_path is not None:
        try:
            _write_receipt(safe_receipt_path, receipt)
        except OSError as exc:
            receipt = _blocked("OUTPUT_RECEIPT_WRITE_FAILED", str(exc))

    print(json.dumps(receipt, ensure_ascii=False, separators=(",", ":")))
    status = str(receipt.get("status") or "").strip().lower()
    return 1 if status in TERMINAL_FAILURE_STATUSES else 0


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
