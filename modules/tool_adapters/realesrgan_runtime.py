"""Bounded adapter for the pinned Real-ESRGAN ncnn Vulkan runtime."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict


DEFAULT_RUNTIME_ROOT = Path(
    r"F:\AI-Content-OS-Data\external_tools\runtimes\realesrgan-ncnn-vulkan"
)
PINNED_RELEASE = "v0.2.5.0/windows-20220424"
ALLOWED_MODELS = frozenset(
    {"realesr-animevideov3", "realesrgan-x4plus", "realesrgan-x4plus-anime"}
)
ALLOWED_SCALES = frozenset({2, 3, 4})
ALLOWED_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp"})


class RealEsrganRuntimeAdapter:
    """Execute one local-image upscale with no shell, network, or service."""

    def __init__(
        self,
        runtime_root: str | Path = DEFAULT_RUNTIME_ROOT,
        *,
        timeout_seconds: float = 120.0,
    ) -> None:
        if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.runtime_root = Path(runtime_root)
        self.executable = self.runtime_root / "realesrgan-ncnn-vulkan.exe"
        self.timeout_seconds = min(float(timeout_seconds), 300.0)

    def readiness(self) -> Dict[str, Any]:
        required = [
            self.executable,
            self.runtime_root / "LICENSE",
            self.runtime_root / "models" / "realesrgan-x4plus.bin",
            self.runtime_root / "models" / "realesrgan-x4plus.param",
        ]
        missing = [str(path) for path in required if not path.is_file()]
        return {
            "status": "ready" if not missing else "blocked",
            "release": PINNED_RELEASE,
            "executable": str(self.executable),
            "missing_paths": missing,
        }

    def upscale(
        self,
        input_path: str | Path,
        output_path: str | Path,
        *,
        model: str = "realesrgan-x4plus",
        scale: int = 4,
    ) -> Dict[str, Any]:
        source = Path(input_path).resolve()
        destination = Path(output_path).resolve()
        if source == destination:
            return {"status": "blocked", "reason_code": "INPUT_OUTPUT_PATH_COLLISION"}
        if model not in ALLOWED_MODELS:
            return {"status": "blocked", "reason_code": "MODEL_NOT_ALLOW_LISTED"}
        if scale not in ALLOWED_SCALES:
            return {"status": "blocked", "reason_code": "SCALE_NOT_ALLOW_LISTED"}
        if source.suffix.lower() not in ALLOWED_SUFFIXES or destination.suffix.lower() not in ALLOWED_SUFFIXES:
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

        command = [
            str(self.executable),
            "-i",
            str(source),
            "-o",
            str(destination),
            "-n",
            model,
            "-s",
            str(scale),
            "-f",
            destination.suffix.lower().lstrip("."),
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=self.runtime_root,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
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
            "release": PINNED_RELEASE,
            "model": model,
            "scale": scale,
            "input_path": str(source),
            "output_path": str(destination),
        }


__all__ = ["PINNED_RELEASE", "RealEsrganRuntimeAdapter"]
