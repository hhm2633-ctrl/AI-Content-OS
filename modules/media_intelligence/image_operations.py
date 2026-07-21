"""Fail-closed composition layer for local image restoration operations.

This module never guesses an operation and never changes the source file.  It
also keeps transformed evidence distinguishable from original source evidence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

from modules.tool_adapters.realesrgan_runtime import RealEsrganRuntimeAdapter
from modules.tool_adapters.rembg_runtime import RembgRuntimeAdapter


DEFAULT_OUTPUT_ROOT = Path(
    r"F:\AI-Content-OS-Data\external_tools\outputs\image_operations"
)
SUPPORTED_OPERATIONS = frozenset({"remove_background", "upscale"})
REMBG_ALLOWED_ASSET_CLASSES = frozenset({"auxiliary", "product", "generated"})
SOURCE_EVIDENCE = "source_evidence"


class LocalMediaImageOperations:
    """Policy gate and dispatcher for explicitly requested local image operations."""

    def __init__(
        self,
        output_root: str | Path = DEFAULT_OUTPUT_ROOT,
        *,
        realesrgan: RealEsrganRuntimeAdapter | None = None,
        rembg: RembgRuntimeAdapter | None = None,
    ) -> None:
        self.output_root = Path(output_root).resolve()
        self.realesrgan = realesrgan or RealEsrganRuntimeAdapter()
        self.rembg = rembg or RembgRuntimeAdapter()

    @staticmethod
    def _blocked(operation: Any, reason_code: str, detail: str) -> Dict[str, Any]:
        return {
            "schema_version": "local_media_image_operation_receipt.v1",
            "status": "blocked",
            "operation": operation if isinstance(operation, str) else None,
            "operation_explicit": isinstance(operation, str) and bool(operation.strip()),
            "reason_code": reason_code,
            "detail": detail,
            "source_modified": False,
            "output_created": False,
        }

    def _validated_paths(
        self, request: Mapping[str, Any], operation: str
    ) -> tuple[Path, Path] | Dict[str, Any]:
        if not self.output_root.is_absolute() or self.output_root.drive.lower() != "f:":
            return self._blocked(
                operation,
                "OUTPUT_ROOT_NOT_F_DRIVE",
                "configured output_root must be an absolute F: path",
            )
        source_value = request.get("source_path")
        output_value = request.get("output_path")
        if not isinstance(source_value, (str, Path)) or not str(source_value).strip():
            return self._blocked(operation, "SOURCE_PATH_MISSING", "source_path is required")
        if not isinstance(output_value, (str, Path)) or not str(output_value).strip():
            return self._blocked(operation, "OUTPUT_PATH_MISSING", "output_path is required")
        source = Path(source_value).resolve()
        output = Path(output_value).resolve()
        if source == output:
            return self._blocked(
                operation,
                "SOURCE_OVERWRITE_FORBIDDEN",
                "output_path must never equal source_path",
            )
        if self.output_root not in output.parents:
            return self._blocked(
                operation,
                "OUTPUT_OUTSIDE_APPROVED_ROOT",
                "output_path must be a child of the configured F: output_root",
            )
        return source, output

    @staticmethod
    def _completed_receipt(
        request: Mapping[str, Any],
        operation: str,
        source: Path,
        output: Path,
        adapter_result: Mapping[str, Any],
    ) -> Dict[str, Any]:
        asset_class = str(request.get("asset_class", "")).strip().lower()
        is_evidence = asset_class == SOURCE_EVIDENCE
        derivative_kind = "background_removed" if operation == "remove_background" else "upscaled"
        return {
            "schema_version": "local_media_image_operation_receipt.v1",
            "status": "completed",
            "request_id": str(request.get("request_id", "")).strip(),
            "operation": operation,
            "operation_explicit": True,
            "source": {
                "path": str(source),
                "asset_class": asset_class,
                "preserved": True,
            },
            "output": {
                "path": str(output),
                "asset_class": "auxiliary",
                "is_derivative": True,
                "derivative_kind": derivative_kind,
                "derivative_label": f"DERIVATIVE_{derivative_kind.upper()}",
                "derivative_of": str(source),
                "derivative_of_source_evidence": is_evidence,
                "not_original_evidence": is_evidence,
            },
            "evidence_policy": {
                "source_was_evidence": is_evidence,
                "derivative_enhancement_allowed": request.get("derivative_enhancement_allowed") is True,
                "original_evidence_preserved": True,
            },
            "source_modified": False,
            "output_created": True,
            "adapter_result": dict(adapter_result),
        }

    def execute(self, request: Mapping[str, Any] | None) -> Dict[str, Any]:
        """Validate an explicit request, execute one adapter, and return a receipt."""

        if not isinstance(request, Mapping):
            return self._blocked(None, "REQUEST_MALFORMED", "request must be an object")
        operation_value = request.get("operation")
        if not isinstance(operation_value, str) or not operation_value.strip():
            return self._blocked(
                operation_value,
                "OPERATION_REQUIRED",
                "operation must be explicitly supplied",
            )
        operation = operation_value.strip().lower()
        if operation not in SUPPORTED_OPERATIONS:
            return self._blocked(operation, "OPERATION_NOT_SUPPORTED", "operation is not allow-listed")
        request_id = request.get("request_id")
        if not isinstance(request_id, str) or not request_id.strip():
            return self._blocked(operation, "REQUEST_ID_REQUIRED", "request_id is required")
        asset_class_value = request.get("asset_class")
        if not isinstance(asset_class_value, str) or not asset_class_value.strip():
            return self._blocked(operation, "ASSET_CLASS_REQUIRED", "asset_class is required")
        asset_class = asset_class_value.strip().lower()

        paths = self._validated_paths(request, operation)
        if isinstance(paths, dict):
            return paths
        source, output = paths

        if operation == "remove_background":
            if asset_class not in REMBG_ALLOWED_ASSET_CLASSES:
                return self._blocked(
                    operation,
                    "REMBG_ASSET_CLASS_BLOCKED",
                    "remove_background is allowed only for auxiliary, product, or generated assets",
                )
            adapter_result = self.rembg.cutout(source, output)
        else:
            is_evidence = asset_class == SOURCE_EVIDENCE
            if is_evidence and request.get("derivative_enhancement_allowed") is not True:
                return self._blocked(
                    operation,
                    "EVIDENCE_DERIVATIVE_APPROVAL_REQUIRED",
                    "source evidence upscale requires derivative_enhancement_allowed=true",
                )
            model = request.get("model", "realesrgan-x4plus")
            scale = request.get("scale", 4)
            if not isinstance(model, str) or not isinstance(scale, int) or isinstance(scale, bool):
                return self._blocked(
                    operation,
                    "UPSCALE_OPTIONS_MALFORMED",
                    "model must be a string and scale must be an integer",
                )
            adapter_result = self.realesrgan.upscale(
                source,
                output,
                model=model,
                scale=scale,
            )

        if not isinstance(adapter_result, Mapping) or adapter_result.get("status") != "completed":
            return {
                **self._blocked(
                    operation,
                    "ADAPTER_OPERATION_FAILED",
                    "underlying adapter did not complete the requested operation",
                ),
                "adapter_result": dict(adapter_result) if isinstance(adapter_result, Mapping) else None,
            }
        return self._completed_receipt(request, operation, source, output, adapter_result)


__all__ = ["DEFAULT_OUTPUT_ROOT", "LocalMediaImageOperations"]
