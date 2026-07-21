"""Side-effect-free resolver for the isolated PaddleOCR CPU runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from email.parser import Parser
import json
import math
import os
from pathlib import Path
import subprocess
import time
from typing import Mapping


PADDLEOCR_RUNTIME_ROOT_ENV = "PADDLEOCR_RUNTIME_ROOT"
PADDLEOCR_MODEL_ROOT_ENV = "PADDLEOCR_MODEL_ROOT"
DEFAULT_PADDLEOCR_RUNTIME_ROOT = Path(
    r"F:\AI-Content-OS-Data\external_tools\runtimes\paddleocr"
)
DEFAULT_PADDLEOCR_MODEL_ROOT = Path(
    r"F:\AI-Content-OS-Data\external_tools\models\paddleocr\official_models"
)
PADDLEOCR_VERSION = "3.7.0"
PADDLEPADDLE_VERSION = "3.2.0"
TEXT_DETECTION_MODEL_NAME = "PP-OCRv5_mobile_det"
TEXT_RECOGNITION_MODEL_NAME = "korean_PP-OCRv5_mobile_rec"
LICENSE = "Apache-2.0"
MODEL_REQUIRED_FILES = ("inference.json", "inference.pdiparams", "inference.yml")
OFFLINE_ENVIRONMENT = (
    ("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True"),
)
SUPPORTED_IMAGE_SUFFIXES = frozenset({".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"})
MAX_IMAGE_BYTES = 25 * 1024 * 1024
MIN_TIMEOUT_SECONDS = 1.0
MAX_TIMEOUT_SECONDS = 120.0
DEFAULT_TIMEOUT_SECONDS = 30.0
_RESULT_MARKER = "__PADDLEOCR_RECEIPT__"
_WORKER_CODE = r'''
import json
import sys
from paddleocr import PaddleOCR

image_path, detection_dir, recognition_dir = sys.argv[1:4]
ocr = PaddleOCR(
    text_detection_model_name="PP-OCRv5_mobile_det",
    text_detection_model_dir=detection_dir,
    text_recognition_model_name="korean_PP-OCRv5_mobile_rec",
    text_recognition_model_dir=recognition_dir,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    device="cpu",
    cpu_threads=2,
    enable_mkldnn=False,
)
lines = []
scores = []
for result in ocr.predict(image_path):
    payload = result.json if hasattr(result, "json") else dict(result)
    if isinstance(payload, str):
        payload = json.loads(payload)
    body = payload.get("res", payload)
    lines.extend(str(value) for value in body.get("rec_texts", []) if str(value).strip())
    scores.extend(float(value) for value in body.get("rec_scores", []))
print("__PADDLEOCR_RECEIPT__" + json.dumps({"lines": lines, "scores": scores}, ensure_ascii=True))
'''


@dataclass(frozen=True)
class PaddleOCRRuntime:
    ready: bool
    runtime_root: str
    model_root: str
    python_executable: str
    paddleocr_version: str
    paddlepaddle_version: str
    license: str
    paddleocr_license_path: str
    paddlepaddle_license_path: str
    text_detection_model_name: str
    text_detection_model_dir: str
    text_recognition_model_name: str
    text_recognition_model_dir: str
    device: str
    offline_environment: tuple[tuple[str, str], ...]
    diagnostics: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def inference_kwargs(self) -> dict[str, object]:
        """Return explicit local-only PaddleOCR constructor arguments."""

        return {
            "text_detection_model_name": self.text_detection_model_name,
            "text_detection_model_dir": self.text_detection_model_dir,
            "text_recognition_model_name": self.text_recognition_model_name,
            "text_recognition_model_dir": self.text_recognition_model_dir,
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
            "device": self.device,
            "cpu_threads": 2,
            "enable_mkldnn": False,
        }


@dataclass(frozen=True)
class PaddleOCRExtractionReceipt:
    success: bool
    status: str
    image_path: str
    input_bytes: int
    input_unchanged: bool
    text: str
    lines: tuple[str, ...]
    scores: tuple[float, ...]
    elapsed_seconds: float
    timeout_seconds: float
    paddleocr_version: str
    paddlepaddle_version: str
    text_detection_model_name: str
    text_recognition_model_name: str
    device: str
    cpu_threads: int
    reason: str
    diagnostics: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _extraction_receipt(
    *,
    runtime: PaddleOCRRuntime,
    success: bool,
    status: str,
    image_path: str = "",
    input_bytes: int = 0,
    input_unchanged: bool = True,
    lines: tuple[str, ...] = (),
    scores: tuple[float, ...] = (),
    elapsed_seconds: float = 0.0,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    reason: str = "",
    diagnostics: tuple[str, ...] = (),
) -> PaddleOCRExtractionReceipt:
    return PaddleOCRExtractionReceipt(
        success=success,
        status=status,
        image_path=image_path,
        input_bytes=input_bytes,
        input_unchanged=input_unchanged,
        text="\n".join(lines),
        lines=lines,
        scores=scores,
        elapsed_seconds=round(elapsed_seconds, 3),
        timeout_seconds=timeout_seconds,
        paddleocr_version=runtime.paddleocr_version,
        paddlepaddle_version=runtime.paddlepaddle_version,
        text_detection_model_name=runtime.text_detection_model_name,
        text_recognition_model_name=runtime.text_recognition_model_name,
        device="cpu",
        cpu_threads=2,
        reason=reason,
        diagnostics=diagnostics,
    )


def _path_from_env(
    environment: Mapping[str, str], name: str, default: Path
) -> Path:
    override = str(environment.get(name, "")).strip().strip('"')
    return Path(override).expanduser() if override else default


def _distribution(root: Path, name: str) -> tuple[Path | None, dict[str, str]]:
    candidates = sorted((root / "Lib" / "site-packages").glob(f"{name}-*.dist-info/METADATA"))
    if not candidates:
        return None, {}
    metadata_path = candidates[-1]
    try:
        message = Parser().parsestr(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return metadata_path, {}
    return metadata_path, {
        "version": str(message.get("Version", "")),
        "license": str(message.get("License-Expression") or message.get("License") or ""),
    }


def _check_model(model_dir: Path, diagnostics: list[str]) -> None:
    if not model_dir.is_dir():
        diagnostics.append(f"model_directory_missing:{model_dir}")
    for name in MODEL_REQUIRED_FILES:
        path = model_dir / name
        if not path.is_file() or path.stat().st_size <= 0:
            diagnostics.append(f"model_file_missing:{path}")


def resolve_paddleocr_runtime(
    *, env: Mapping[str, str] | None = None
) -> PaddleOCRRuntime:
    """Inspect the pinned runtime and models without importing or launching PaddleOCR."""

    environment = os.environ if env is None else env
    runtime_root = _path_from_env(
        environment, PADDLEOCR_RUNTIME_ROOT_ENV, DEFAULT_PADDLEOCR_RUNTIME_ROOT
    )
    model_root = _path_from_env(
        environment, PADDLEOCR_MODEL_ROOT_ENV, DEFAULT_PADDLEOCR_MODEL_ROOT
    )
    python = runtime_root / "Scripts" / "python.exe"
    paddleocr_metadata, paddleocr = _distribution(runtime_root, "paddleocr")
    paddle_metadata, paddle = _distribution(runtime_root, "paddlepaddle")
    paddleocr_license = paddleocr_metadata.parent / "LICENSE" if paddleocr_metadata else Path()
    paddle_license = paddle_metadata.parent / "LICENSE" if paddle_metadata else Path()
    detection_dir = model_root / TEXT_DETECTION_MODEL_NAME
    recognition_dir = model_root / TEXT_RECOGNITION_MODEL_NAME
    diagnostics: list[str] = []

    if not runtime_root.is_dir():
        diagnostics.append(f"runtime_root_missing:{runtime_root}")
    if not python.is_file() or python.stat().st_size <= 0:
        diagnostics.append(f"python_executable_missing:{python}")
    for dist_name, metadata_path, metadata, expected, license_path in (
        ("paddleocr", paddleocr_metadata, paddleocr, PADDLEOCR_VERSION, paddleocr_license),
        ("paddlepaddle", paddle_metadata, paddle, PADDLEPADDLE_VERSION, paddle_license),
    ):
        if metadata_path is None:
            diagnostics.append(f"package_metadata_missing:{dist_name}")
        elif metadata.get("version") != expected:
            diagnostics.append(
                f"package_version_mismatch:{dist_name}:{metadata.get('version', '')}:{expected}"
            )
        if metadata_path is None or not license_path.is_file():
            diagnostics.append(f"license_file_missing:{dist_name}")

    _check_model(detection_dir, diagnostics)
    _check_model(recognition_dir, diagnostics)

    return PaddleOCRRuntime(
        ready=not diagnostics,
        runtime_root=str(runtime_root),
        model_root=str(model_root),
        python_executable=str(python) if python.is_file() else "",
        paddleocr_version=paddleocr.get("version", ""),
        paddlepaddle_version=paddle.get("version", ""),
        license=LICENSE,
        paddleocr_license_path=(
            str(paddleocr_license) if paddleocr_metadata and paddleocr_license.is_file() else ""
        ),
        paddlepaddle_license_path=(
            str(paddle_license) if paddle_metadata and paddle_license.is_file() else ""
        ),
        text_detection_model_name=TEXT_DETECTION_MODEL_NAME,
        text_detection_model_dir=str(detection_dir),
        text_recognition_model_name=TEXT_RECOGNITION_MODEL_NAME,
        text_recognition_model_dir=str(recognition_dir),
        device="cpu",
        offline_environment=OFFLINE_ENVIRONMENT,
        diagnostics=tuple(diagnostics),
    )


def extract_korean_text(
    image_path: str | os.PathLike[str],
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    env: Mapping[str, str] | None = None,
) -> PaddleOCRExtractionReceipt:
    """Extract Korean text from one local image with the pinned offline CPU runtime."""

    runtime = resolve_paddleocr_runtime(env=env)
    try:
        timeout = float(timeout_seconds)
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT_SECONDS
        return _extraction_receipt(
            runtime=runtime,
            success=False,
            status="rejected",
            timeout_seconds=timeout,
            reason="invalid_timeout",
        )
    if isinstance(timeout_seconds, bool) or not math.isfinite(timeout) or not (
        MIN_TIMEOUT_SECONDS <= timeout <= MAX_TIMEOUT_SECONDS
    ):
        return _extraction_receipt(
            runtime=runtime,
            success=False,
            status="rejected",
            timeout_seconds=timeout,
            reason="invalid_timeout",
        )

    raw_path = os.fspath(image_path).strip() if isinstance(image_path, (str, os.PathLike)) else ""
    if not raw_path:
        return _extraction_receipt(
            runtime=runtime,
            success=False,
            status="rejected",
            timeout_seconds=timeout,
            reason="image_path_required",
        )
    try:
        source = Path(raw_path).expanduser().resolve(strict=True)
        before = source.stat()
    except (OSError, RuntimeError):
        return _extraction_receipt(
            runtime=runtime,
            success=False,
            status="rejected",
            image_path=raw_path,
            timeout_seconds=timeout,
            reason="image_not_found",
        )
    if not source.is_file():
        return _extraction_receipt(
            runtime=runtime,
            success=False,
            status="rejected",
            image_path=str(source),
            timeout_seconds=timeout,
            reason="image_not_file",
        )
    if source.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
        return _extraction_receipt(
            runtime=runtime,
            success=False,
            status="rejected",
            image_path=str(source),
            input_bytes=before.st_size,
            timeout_seconds=timeout,
            reason="unsupported_image_suffix",
        )
    if before.st_size <= 0 or before.st_size > MAX_IMAGE_BYTES:
        return _extraction_receipt(
            runtime=runtime,
            success=False,
            status="rejected",
            image_path=str(source),
            input_bytes=before.st_size,
            timeout_seconds=timeout,
            reason="image_size_out_of_bounds",
        )
    if not runtime.ready:
        return _extraction_receipt(
            runtime=runtime,
            success=False,
            status="failed",
            image_path=str(source),
            input_bytes=before.st_size,
            timeout_seconds=timeout,
            reason="runtime_not_ready",
            diagnostics=runtime.diagnostics,
        )

    child_env = os.environ.copy()
    if env is not None:
        child_env.update({str(key): str(value) for key, value in env.items()})
    child_env.update(
        {
            "PADDLE_PDX_CACHE_HOME": str(Path(runtime.model_root).parent),
            "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK": "True",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "http://127.0.0.1:9",
            "NO_PROXY": "",
            "FLAGS_use_mkldnn": "0",
        }
    )
    command = [
        runtime.python_executable,
        "-c",
        _WORKER_CODE,
        str(source),
        runtime.text_detection_model_dir,
        runtime.text_recognition_model_dir,
    ]
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=child_env,
        )
    except subprocess.TimeoutExpired:
        return _extraction_receipt(
            runtime=runtime,
            success=False,
            status="timed_out",
            image_path=str(source),
            input_bytes=before.st_size,
            elapsed_seconds=time.perf_counter() - started,
            timeout_seconds=timeout,
            reason="ocr_timeout",
        )
    except OSError as exc:
        return _extraction_receipt(
            runtime=runtime,
            success=False,
            status="failed",
            image_path=str(source),
            input_bytes=before.st_size,
            elapsed_seconds=time.perf_counter() - started,
            timeout_seconds=timeout,
            reason="runtime_launch_failed",
            diagnostics=(f"{type(exc).__name__}:{str(exc)[:500]}",),
        )

    elapsed = time.perf_counter() - started
    try:
        after = source.stat()
        unchanged = (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    except OSError:
        unchanged = False
    if not unchanged:
        return _extraction_receipt(
            runtime=runtime,
            success=False,
            status="failed",
            image_path=str(source),
            input_bytes=before.st_size,
            input_unchanged=False,
            elapsed_seconds=elapsed,
            timeout_seconds=timeout,
            reason="input_changed_during_extraction",
        )
    if completed.returncode != 0:
        diagnostic = completed.stderr.strip()[-1000:]
        return _extraction_receipt(
            runtime=runtime,
            success=False,
            status="failed",
            image_path=str(source),
            input_bytes=before.st_size,
            elapsed_seconds=elapsed,
            timeout_seconds=timeout,
            reason="ocr_process_failed",
            diagnostics=(diagnostic,) if diagnostic else (),
        )

    marker_line = next(
        (line for line in reversed(completed.stdout.splitlines()) if line.startswith(_RESULT_MARKER)),
        "",
    )
    try:
        payload = json.loads(marker_line[len(_RESULT_MARKER) :]) if marker_line else None
        if not isinstance(payload, dict):
            raise ValueError("receipt payload is not an object")
        lines = tuple(str(item) for item in payload.get("lines", ()) if str(item).strip())
        scores = tuple(float(item) for item in payload.get("scores", ()))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return _extraction_receipt(
            runtime=runtime,
            success=False,
            status="failed",
            image_path=str(source),
            input_bytes=before.st_size,
            elapsed_seconds=elapsed,
            timeout_seconds=timeout,
            reason="invalid_ocr_receipt",
            diagnostics=(f"{type(exc).__name__}:{str(exc)[:500]}",),
        )

    return _extraction_receipt(
        runtime=runtime,
        success=True,
        status="completed",
        image_path=str(source),
        input_bytes=before.st_size,
        lines=lines,
        scores=scores,
        elapsed_seconds=elapsed,
        timeout_seconds=timeout,
    )


__all__ = [
    "DEFAULT_PADDLEOCR_MODEL_ROOT",
    "DEFAULT_PADDLEOCR_RUNTIME_ROOT",
    "DEFAULT_TIMEOUT_SECONDS",
    "LICENSE",
    "MAX_IMAGE_BYTES",
    "MAX_TIMEOUT_SECONDS",
    "MIN_TIMEOUT_SECONDS",
    "MODEL_REQUIRED_FILES",
    "OFFLINE_ENVIRONMENT",
    "PADDLEOCR_MODEL_ROOT_ENV",
    "PADDLEOCR_RUNTIME_ROOT_ENV",
    "PADDLEOCR_VERSION",
    "PADDLEPADDLE_VERSION",
    "PaddleOCRExtractionReceipt",
    "PaddleOCRRuntime",
    "SUPPORTED_IMAGE_SUFFIXES",
    "TEXT_DETECTION_MODEL_NAME",
    "TEXT_RECOGNITION_MODEL_NAME",
    "extract_korean_text",
    "resolve_paddleocr_runtime",
]
