"""Explicit fail-closed preparation of one rights-cleared local media asset.

The pipeline is deliberately not connected to rendering or the WorkflowEngine.  A
caller must name every operation, and analysis results remain internal proxies.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Sequence

from modules.media_intelligence.image_operations import LocalMediaImageOperations
from modules.tool_adapters.openclip_runtime import OpenClipRuntime
from modules.tool_adapters.paddleocr_runtime import extract_korean_text
from modules.tool_adapters.pyscenedetect_runtime import detect_scenes


SCHEMA_VERSION = "local_media_pre_render_receipt.v1"
SUPPORTED_OPERATIONS = frozenset(
    {
        "detect_scenes",
        "ocr",
        "openclip_topic_score",
        "preserve_original",
        "remove_background",
        "upscale",
    }
)
IMAGE_OPERATIONS = frozenset(
    {"ocr", "openclip_topic_score", "preserve_original", "remove_background", "upscale"}
)
VIDEO_OPERATIONS = frozenset({"detect_scenes", "preserve_original"})
TRANSFORM_OPERATIONS = frozenset({"remove_background", "upscale"})
ANALYSIS_BOUNDARY = {
    "classification": "internal_analysis_only",
    "source_truth": False,
    "rights_evidence": False,
    "performance_evidence": False,
    "production_selection_authority": False,
}
_VOLATILE_RESULT_KEYS = frozenset({"elapsed_seconds", "stderr_tail", "stdout_tail"})


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_value(value: Any) -> Any:
    """Convert adapter receipts to deterministic JSON and drop timing/log noise."""

    if hasattr(value, "to_dict") and callable(value.to_dict):
        value = value.to_dict()
    elif is_dataclass(value):
        value = asdict(value)
    if isinstance(value, Mapping):
        return {
            str(key): _stable_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in _VOLATILE_RESULT_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_stable_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


class LocalMediaPipeline:
    """Prepare exactly one explicitly selected and rights-cleared local asset."""

    def __init__(
        self,
        *,
        image_operations_factory: Callable[[Path], LocalMediaImageOperations] = LocalMediaImageOperations,
        ocr_extractor: Callable[..., Any] = extract_korean_text,
        openclip: OpenClipRuntime | None = None,
        scene_detector: Callable[..., Mapping[str, Any]] = detect_scenes,
    ) -> None:
        self.image_operations_factory = image_operations_factory
        self.ocr_extractor = ocr_extractor
        self.openclip = openclip if openclip is not None else OpenClipRuntime()
        self.scene_detector = scene_detector

    @staticmethod
    def _seal(receipt: Dict[str, Any]) -> Dict[str, Any]:
        sealed = dict(receipt)
        sealed["receipt_hash"] = _canonical_hash(sealed)
        return sealed

    @classmethod
    def _blocked(
        cls,
        reason_code: str,
        detail: str,
        *,
        request: Mapping[str, Any] | None = None,
        source: Mapping[str, Any] | None = None,
        output_root: str = "",
        operations: Sequence[Mapping[str, Any]] = (),
        source_modified: bool = False,
        tools_executed: bool = False,
    ) -> Dict[str, Any]:
        return cls._seal(
            {
                "schema_version": SCHEMA_VERSION,
                "status": "blocked",
                "reason_code": reason_code,
                "detail": detail,
                "request_id": str((request or {}).get("request_id", "")).strip(),
                "asset_id": str((request or {}).get("asset_id", "")).strip(),
                "source": dict(source or {}),
                "output_root": output_root,
                "operations": [dict(item) for item in operations],
                "analysis_boundary": dict(ANALYSIS_BOUNDARY),
                "source_modified": source_modified,
                "tools_executed": tools_executed,
                "pre_render_prepared": False,
                "implicit_execution": False,
            }
        )

    @staticmethod
    def _absolute_path(value: Any) -> Path | None:
        if not isinstance(value, (str, Path)) or not str(value).strip():
            return None
        path = Path(value).expanduser()
        return path.resolve() if path.is_absolute() else None

    @staticmethod
    def _source_editorial_usable(request: Mapping[str, Any]) -> bool:
        return (
            request.get("source_editorial_usable") is True
            and request.get("topic_relevant") is True
            and request.get("attribution_required") is True
            and bool(str(request.get("source_url") or "").strip())
            and request.get("publish_authorized") is False
        )

    def _validate(
        self, request: Mapping[str, Any] | None
    ) -> tuple[Mapping[str, Any], Path, Path, str, list[dict[str, Any]]] | Dict[str, Any]:
        if not isinstance(request, Mapping):
            return self._blocked("REQUEST_MALFORMED", "request must be an object")
        if request.get("owner_selected") is not True:
            return self._blocked(
                "OWNER_SELECTION_REQUIRED",
                "owner_selected must be explicitly true",
                request=request,
            )
        source_editorial_usable = self._source_editorial_usable(request)
        if request.get("rights_cleared") is not True and not source_editorial_usable:
            return self._blocked(
                "RIGHTS_CLEARANCE_REQUIRED",
                "rights_cleared or an attributed, topic-relevant source editorial scope is required",
                request=request,
            )
        for field in ("request_id", "asset_id"):
            if not isinstance(request.get(field), str) or not str(request[field]).strip():
                return self._blocked(
                    f"{field.upper()}_REQUIRED",
                    f"{field} is required",
                    request=request,
                )

        output_root = self._absolute_path(request.get("output_root"))
        if output_root is None or output_root.drive.casefold() != "f:":
            return self._blocked(
                "OUTPUT_ROOT_NOT_ABSOLUTE_F_DRIVE",
                "output_root must be an explicit absolute F: path",
                request=request,
            )
        source = self._absolute_path(request.get("source_path"))
        if source is None:
            return self._blocked(
                "SOURCE_PATH_NOT_ABSOLUTE",
                "source_path must be absolute",
                request=request,
                output_root=str(output_root),
            )
        try:
            if not source.is_file() or source.stat().st_size <= 0:
                raise OSError("source is missing, empty, or not a file")
        except OSError:
            return self._blocked(
                "SOURCE_NOT_READABLE",
                "source_path must identify a readable non-empty local file",
                request=request,
                output_root=str(output_root),
            )

        media_type = request.get("media_type")
        if media_type not in {"image", "video"}:
            return self._blocked(
                "MEDIA_TYPE_REQUIRED",
                "media_type must be image or video",
                request=request,
                output_root=str(output_root),
            )
        raw_operations = request.get("operations")
        if isinstance(raw_operations, (str, bytes)) or not isinstance(raw_operations, Sequence) or not raw_operations:
            return self._blocked(
                "OPERATIONS_REQUIRED",
                "operations must explicitly list at least one per-asset operation",
                request=request,
                output_root=str(output_root),
            )

        operations: list[dict[str, Any]] = []
        names: set[str] = set()
        for index, raw in enumerate(raw_operations):
            if not isinstance(raw, Mapping):
                return self._blocked(
                    "OPERATION_MALFORMED",
                    f"operations[{index}] must be an object",
                    request=request,
                    output_root=str(output_root),
                )
            operation = raw.get("operation")
            if not isinstance(operation, str) or not operation.strip():
                return self._blocked(
                    "OPERATION_REQUIRED",
                    f"operations[{index}].operation is required",
                    request=request,
                    output_root=str(output_root),
                )
            name = operation.strip().lower()
            if name not in SUPPORTED_OPERATIONS:
                return self._blocked(
                    "OPERATION_NOT_SUPPORTED",
                    f"unsupported operation: {name}",
                    request=request,
                    output_root=str(output_root),
                )
            if name in names:
                return self._blocked(
                    "DUPLICATE_OPERATION",
                    f"operation may appear only once: {name}",
                    request=request,
                    output_root=str(output_root),
                )
            if (media_type == "image" and name not in IMAGE_OPERATIONS) or (
                media_type == "video" and name not in VIDEO_OPERATIONS
            ):
                return self._blocked(
                    "OPERATION_MEDIA_TYPE_MISMATCH",
                    f"{name} is not valid for media_type={media_type}",
                    request=request,
                    output_root=str(output_root),
                )
            normalized = dict(raw)
            normalized["operation"] = name
            if name == "openclip_topic_score":
                topics = normalized.get("topics")
                if isinstance(topics, (str, bytes)) or not isinstance(topics, Sequence) or not topics:
                    return self._blocked(
                        "OPENCLIP_TOPICS_REQUIRED",
                        "openclip_topic_score requires a non-empty topics list",
                        request=request,
                        output_root=str(output_root),
                    )
                if any(not isinstance(topic, str) or not topic.strip() for topic in topics):
                    return self._blocked(
                        "OPENCLIP_TOPICS_MALFORMED",
                        "every OpenCLIP topic must be a non-empty string",
                        request=request,
                        output_root=str(output_root),
                    )
                normalized["topics"] = [topic.strip() for topic in topics]
            if name in TRANSFORM_OPERATIONS:
                output = self._absolute_path(normalized.get("output_path"))
                if output is None:
                    return self._blocked(
                        "OUTPUT_PATH_NOT_ABSOLUTE",
                        f"{name} requires an absolute output_path",
                        request=request,
                        output_root=str(output_root),
                    )
                if output == source:
                    return self._blocked(
                        "SOURCE_OVERWRITE_FORBIDDEN",
                        "a derivative output_path must never equal source_path",
                        request=request,
                        output_root=str(output_root),
                    )
                if output_root not in output.parents:
                    return self._blocked(
                        "OUTPUT_OUTSIDE_APPROVED_ROOT",
                        "derivative output_path must be below output_root",
                        request=request,
                        output_root=str(output_root),
                    )
                normalized["output_path"] = str(output)
            names.add(name)
            operations.append(normalized)
        if "preserve_original" in names and len(names) != 1:
            return self._blocked(
                "PRESERVE_ORIGINAL_MUST_BE_SOLE_OPERATION",
                "preserve_original is only valid when no analysis or transform is requested",
                request=request,
                output_root=str(output_root),
            )
        return request, source, output_root, media_type, operations

    @staticmethod
    def _timeout(operation: Mapping[str, Any], default: float, maximum: float) -> float:
        value = operation.get("timeout_seconds", default)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("timeout_seconds must be numeric")
        timeout = float(value)
        if not math.isfinite(timeout) or timeout <= 0 or timeout > maximum:
            raise ValueError(f"timeout_seconds must be > 0 and <= {maximum:g}")
        return timeout

    def _execute_one(
        self,
        *,
        request: Mapping[str, Any],
        source: Path,
        output_root: Path,
        operation: Mapping[str, Any],
    ) -> tuple[bool, dict[str, Any]]:
        name = str(operation["operation"])
        try:
            if name == "preserve_original":
                result = {
                    "status": "completed",
                    "source_preserved": True,
                    "tool_subprocess_executed": False,
                    "detail": "original asset explicitly retained without processing",
                }
                passed = True
            elif name == "ocr":
                raw = self.ocr_extractor(
                    source,
                    timeout_seconds=self._timeout(operation, 30.0, 120.0),
                )
                result = _stable_value(raw)
                passed = (
                    isinstance(result, Mapping)
                    and result.get("status") == "completed"
                    and result.get("success") is True
                    and result.get("input_unchanged") is True
                )
            elif name == "openclip_topic_score":
                raw = self.openclip.score_image_topics(
                    source,
                    operation["topics"],
                    timeout_seconds=self._timeout(operation, 30.0, 60.0),
                )
                result = _stable_value(raw)
                passed = (
                    isinstance(result, Mapping)
                    and result.get("status") == "passed"
                    and result.get("passed") is True
                )
            elif name == "detect_scenes":
                raw = self.scene_detector(
                    source,
                    timeout_seconds=int(self._timeout(operation, 120.0, 300.0)),
                )
                result = _stable_value(raw)
                passed = isinstance(result, Mapping) and result.get("status") == "completed"
            else:
                image_operations = self.image_operations_factory(output_root)
                image_request = {
                    "request_id": f"{str(request['request_id']).strip()}:{name}",
                    "operation": name,
                    "source_path": str(source),
                    "output_path": operation["output_path"],
                    "asset_class": operation.get("asset_class", request.get("asset_class", "")),
                }
                for key in ("derivative_enhancement_allowed", "model", "scale"):
                    if key in operation:
                        image_request[key] = operation[key]
                raw = image_operations.execute(image_request)
                result = _stable_value(raw)
                passed = (
                    isinstance(result, Mapping)
                    and result.get("status") == "completed"
                    and result.get("source_modified") is False
                    and isinstance(result.get("output"), Mapping)
                    and result["output"].get("is_derivative") is True
                    and result["output"].get("asset_class") == "auxiliary"
                )
        except Exception as exc:  # adapters are an untrusted fail-closed boundary
            return False, {
                "operation": name,
                "status": "blocked",
                "reason_code": "TOOL_EXCEPTION",
                "detail": f"{type(exc).__name__}:{str(exc)[:300]}",
                "analysis_boundary": dict(ANALYSIS_BOUNDARY),
            }
        return passed, {
            "operation": name,
            "status": "completed" if passed else "blocked",
            "reason_code": None if passed else "TOOL_DID_NOT_COMPLETE",
            "result": result,
            "analysis_boundary": dict(ANALYSIS_BOUNDARY),
        }

    def prepare(self, request: Mapping[str, Any] | None) -> Dict[str, Any]:
        """Execute only declared operations and return an in-memory pre-render receipt."""

        if not isinstance(request, Mapping):
            return self._blocked("REQUEST_MALFORMED", "request must be an object")
        execute = request.get("execute")
        validate_only = request.get("validate_only")
        if not (
            (execute is True and validate_only is False)
            or (execute is False and validate_only is True)
        ):
            return self._blocked(
                "EXECUTION_MODE_REQUIRED",
                "exactly one explicit mode is required: execute=true/validate_only=false or execute=false/validate_only=true",
                request=request,
            )
        validated = self._validate(request)
        if isinstance(validated, dict):
            return validated
        valid_request, source, output_root, media_type, operations = validated
        try:
            before = {"bytes": source.stat().st_size, "sha256": _file_sha256(source)}
        except OSError:
            return self._blocked(
                "SOURCE_FINGERPRINT_FAILED",
                "source could not be fingerprinted before tool execution",
                request=valid_request,
                output_root=str(output_root),
            )
        source_record = {
            "path": str(source),
            "media_type": media_type,
            "asset_class": str(valid_request.get("asset_class", "")).strip().lower(),
            **before,
            "preserved": True,
        }

        if validate_only is True:
            planned_operations = [
                {
                    "operation": operation["operation"],
                    "status": "not_executed",
                    "reason_code": "VALIDATION_ONLY",
                    "analysis_boundary": dict(ANALYSIS_BOUNDARY),
                }
                for operation in operations
            ]
            return self._seal(
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "validated",
                    "reason_code": None,
                    "detail": "request gates and source fingerprint validated without tool execution",
                    "request_id": str(valid_request["request_id"]).strip(),
                    "asset_id": str(valid_request["asset_id"]).strip(),
                    "owner_selected": True,
                    "rights_cleared": valid_request.get("rights_cleared") is True,
                    "source_editorial_usable": self._source_editorial_usable(valid_request),
                    "topic_relevant": valid_request.get("topic_relevant") is True,
                    "attribution_required": valid_request.get("attribution_required") is True,
                    "source_url": str(valid_request.get("source_url") or "").strip(),
                    "publish_authorized": False,
                    "source": source_record,
                    "output_root": str(output_root),
                    "operations": planned_operations,
                    "analysis_boundary": dict(ANALYSIS_BOUNDARY),
                    "source_modified": False,
                    "tools_executed": False,
                    "pre_render_prepared": False,
                    "implicit_execution": False,
                }
            )

        operation_receipts: list[dict[str, Any]] = []
        tool_subprocess_executed = any(
            operation["operation"] != "preserve_original" for operation in operations
        )
        for operation in operations:
            passed, operation_receipt = self._execute_one(
                request=valid_request,
                source=source,
                output_root=output_root,
                operation=operation,
            )
            operation_receipts.append(operation_receipt)
            if not passed:
                return self._blocked(
                    "TOOL_OPERATION_FAILED",
                    f"operation failed closed: {operation['operation']}",
                    request=valid_request,
                    source=source_record,
                    output_root=str(output_root),
                    operations=operation_receipts,
                    tools_executed=tool_subprocess_executed,
                )

        try:
            after = {"bytes": source.stat().st_size, "sha256": _file_sha256(source)}
        except OSError:
            after = {}
        if after != before:
            source_record["preserved"] = False
            return self._blocked(
                "SOURCE_CHANGED_DURING_PREPARATION",
                "source fingerprint changed during preparation",
                request=valid_request,
                source=source_record,
                output_root=str(output_root),
                operations=operation_receipts,
                source_modified=True,
                tools_executed=tool_subprocess_executed,
            )

        return self._seal(
            {
                "schema_version": SCHEMA_VERSION,
                "status": "completed",
                "reason_code": None,
                "detail": "all explicitly requested operations completed",
                "request_id": str(valid_request["request_id"]).strip(),
                "asset_id": str(valid_request["asset_id"]).strip(),
                "owner_selected": True,
                "rights_cleared": valid_request.get("rights_cleared") is True,
                "source_editorial_usable": self._source_editorial_usable(valid_request),
                "topic_relevant": valid_request.get("topic_relevant") is True,
                "attribution_required": valid_request.get("attribution_required") is True,
                "source_url": str(valid_request.get("source_url") or "").strip(),
                "publish_authorized": False,
                "source": source_record,
                "output_root": str(output_root),
                "operations": operation_receipts,
                "analysis_boundary": dict(ANALYSIS_BOUNDARY),
                "derivative_policy": {
                    "realesrgan_and_rembg_outputs_are_auxiliary_derivatives": True,
                    "derivatives_replace_source_evidence": False,
                },
                "source_modified": False,
                "tools_executed": tool_subprocess_executed,
                "pre_render_prepared": True,
                "implicit_execution": False,
            }
        )


def prepare_local_media(
    request: Mapping[str, Any] | None,
    config: Mapping[str, Any] | None = None,
    dependencies: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """CLI-compatible functional entry point around :class:`LocalMediaPipeline`."""

    prepared_request: Mapping[str, Any] | None = request
    if isinstance(request, Mapping):
        prepared = dict(request)
        if isinstance(config, Mapping) and "output_root" in config:
            prepared["output_root"] = config.get("output_root")
        prepared_request = prepared

    dependency_values = dict(dependencies) if isinstance(dependencies, Mapping) else {}
    allowed = {
        "image_operations_factory",
        "ocr_extractor",
        "openclip",
        "scene_detector",
    }
    unknown = sorted(set(dependency_values) - allowed)
    if dependencies is not None and not isinstance(dependencies, Mapping):
        return LocalMediaPipeline._blocked(
            "DEPENDENCIES_MALFORMED", "dependencies must be an object"
        )
    if unknown:
        return LocalMediaPipeline._blocked(
            "DEPENDENCY_NOT_SUPPORTED",
            f"unsupported dependencies: {', '.join(unknown)}",
            request=request if isinstance(request, Mapping) else None,
        )
    pipeline = LocalMediaPipeline(**dependency_values)
    return pipeline.prepare(prepared_request)


__all__ = [
    "ANALYSIS_BOUNDARY",
    "LocalMediaPipeline",
    "SCHEMA_VERSION",
    "SUPPORTED_OPERATIONS",
    "prepare_local_media",
]
