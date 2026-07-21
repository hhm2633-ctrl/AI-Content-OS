"""Bounded CPU-only adapter for the isolated pinned rembg runtime."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from typing import Any, Dict


DEFAULT_RUNTIME_ROOT = Path(r"F:\AI-Content-OS-Data\external_tools\runtimes\rembg")
DEFAULT_MODEL_ROOT = Path(r"F:\AI-Content-OS-Data\external_tools\models\rembg")
PINNED_REMBG_VERSION = "2.0.76"
PINNED_MODEL = "u2netp"
PINNED_MODEL_MD5 = "8e83ca70e441ab06c318d82300c84806"
ALLOWED_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp"})

_CUTOUT_SCRIPT = r"""
import sys
from pathlib import Path
from PIL import Image
from rembg import new_session, remove

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
session = new_session("u2netp", providers=["CPUExecutionProvider"])
with Image.open(source) as image:
    result = remove(image.convert("RGB"), session=session)
    result.save(destination)
"""


class RembgRuntimeAdapter:
    """Remove a local image background using a preinstalled, checksum-pinned model."""

    def __init__(
        self,
        runtime_root: str | Path = DEFAULT_RUNTIME_ROOT,
        model_root: str | Path = DEFAULT_MODEL_ROOT,
        *,
        timeout_seconds: float = 120.0,
    ) -> None:
        if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.runtime_root = Path(runtime_root)
        self.model_root = Path(model_root)
        self.executable = self.runtime_root / "venv" / "Scripts" / "python.exe"
        self.model_path = self.model_root / "u2netp.onnx"
        self.timeout_seconds = min(float(timeout_seconds), 300.0)

    def _model_md5(self) -> str:
        digest = hashlib.md5(usedforsecurity=False)
        with self.model_path.open("rb") as model_file:
            for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def readiness(self) -> Dict[str, Any]:
        missing = [
            str(path)
            for path in (self.executable, self.model_path)
            if not path.is_file()
        ]
        if missing:
            return {"status": "blocked", "missing_paths": missing}
        observed_md5 = self._model_md5()
        if observed_md5.lower() != PINNED_MODEL_MD5:
            return {
                "status": "blocked",
                "reason_code": "MODEL_CHECKSUM_MISMATCH",
                "expected_md5": PINNED_MODEL_MD5,
                "observed_md5": observed_md5,
            }
        return {
            "status": "ready",
            "rembg_version": PINNED_REMBG_VERSION,
            "model": PINNED_MODEL,
            "model_md5": observed_md5,
            "provider": "CPUExecutionProvider",
        }

    def cutout(self, input_path: str | Path, output_path: str | Path) -> Dict[str, Any]:
        source = Path(input_path).resolve()
        destination = Path(output_path).resolve()
        if source == destination:
            return {"status": "blocked", "reason_code": "INPUT_OUTPUT_PATH_COLLISION"}
        if source.suffix.lower() not in ALLOWED_SUFFIXES or destination.suffix.lower() != ".png":
            return {"status": "blocked", "reason_code": "IMAGE_SUFFIX_NOT_ALLOWED"}
        readiness = self.readiness()
        if readiness["status"] != "ready":
            return {"status": "blocked", "reason_code": "RUNTIME_NOT_READY", "readiness": readiness}
        if not source.is_file():
            return {"status": "blocked", "reason_code": "INPUT_NOT_FOUND"}
        if not destination.parent.is_dir():
            return {"status": "blocked", "reason_code": "OUTPUT_DIRECTORY_NOT_FOUND"}
        if destination.exists():
            return {"status": "blocked", "reason_code": "OUTPUT_ALREADY_EXISTS"}

        environment = os.environ.copy()
        environment.update(
            {
                "U2NET_HOME": str(self.model_root),
                "OMP_NUM_THREADS": "2",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        environment.pop("MODEL_CHECKSUM_DISABLED", None)
        try:
            completed = subprocess.run(
                [str(self.executable), "-I", "-c", _CUTOUT_SCRIPT, str(source), str(destination)],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                env=environment,
            )
        except subprocess.TimeoutExpired:
            return {"status": "blocked", "reason_code": "RUNTIME_TIMEOUT"}
        except OSError as exc:
            return {"status": "blocked", "reason_code": "RUNTIME_PROCESS_ERROR", "detail": str(exc)[:500]}
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "runtime failed").strip()
            return {
                "status": "blocked",
                "reason_code": "RUNTIME_NONZERO_EXIT",
                "returncode": completed.returncode,
                "detail": detail[-1000:],
            }
        if not destination.is_file():
            return {"status": "blocked", "reason_code": "OUTPUT_NOT_CREATED"}
        return {
            "status": "completed",
            "rembg_version": PINNED_REMBG_VERSION,
            "model": PINNED_MODEL,
            "provider": "CPUExecutionProvider",
            "input_path": str(source),
            "output_path": str(destination),
        }


__all__ = ["PINNED_MODEL_MD5", "PINNED_REMBG_VERSION", "RembgRuntimeAdapter"]
