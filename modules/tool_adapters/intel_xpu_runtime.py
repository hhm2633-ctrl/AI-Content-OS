"""Bounded, offline-first readiness probe for the isolated Intel XPU runtime.

The probe deliberately distinguishes three claims:

* a small tensor operation actually executed on XPU;
* the supported Diffusers pipeline classes imported successfully; and
* model generation remains unverified until weights are loaded and an owner-approved
  generation smoke test is performed.

Importing this module has no subprocess, GPU, network, or filesystem side effects.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict


DEFAULT_XPU_PYTHON = Path(
    r"F:\AI-Content-OS-Data\tools\intel-gpu-probe\venv\Scripts\python.exe"
)
DEFAULT_TIMEOUT_SECONDS = 20.0
MAX_TIMEOUT_SECONDS = 30.0

_DEVICE_EXECUTION_SCRIPT = r"""
import json
import torch

result = {
    "torch_version": torch.__version__,
    "xpu_available": bool(torch.xpu.is_available()),
    "device_name": None,
    "operations": {},
}
if not result["xpu_available"]:
    raise RuntimeError("torch.xpu.is_available() returned false")
result["device_name"] = torch.xpu.get_device_name(0)
for label, dtype in (
    ("float32", torch.float32),
    ("float16", torch.float16),
    ("bfloat16", torch.bfloat16),
):
    value = torch.ones((8, 8), device="xpu", dtype=dtype)
    product = value @ value
    torch.xpu.synchronize()
    observed = float(product[0, 0].cpu())
    if observed != 8.0:
        raise RuntimeError(f"unexpected {label} matmul result: {observed}")
    result["operations"][label] = {"passed": True, "observed": observed}
print(json.dumps(result, ensure_ascii=True))
"""

_PIPELINE_IMPORT_SCRIPT = r"""
import json
from diffusers import Flux2KleinPipeline, Flux2Pipeline, QwenImagePipeline

print(json.dumps({
    "imported": [
        QwenImagePipeline.__name__,
        Flux2Pipeline.__name__,
        Flux2KleinPipeline.__name__,
    ]
}, ensure_ascii=True))
"""


class IntelXpuRuntimeProbe:
    """Run two allow-listed diagnostics in the isolated XPU Python runtime."""

    def __init__(
        self,
        executable: str | Path = DEFAULT_XPU_PYTHON,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.executable = Path(executable)
        self.timeout_seconds = min(float(timeout_seconds), MAX_TIMEOUT_SECONDS)

    @staticmethod
    def _offline_environment() -> Dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "DIFFUSERS_OFFLINE": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        return environment

    def _run(self, script: str, probe_name: str) -> Dict[str, Any]:
        try:
            completed = subprocess.run(
                [str(self.executable), "-I", "-c", script],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                env=self._offline_environment(),
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "blocked",
                "reason_code": "PROBE_TIMEOUT",
                "probe": probe_name,
                "timeout_seconds": self.timeout_seconds,
            }
        except OSError as exc:
            return {
                "status": "blocked",
                "reason_code": "PROBE_PROCESS_ERROR",
                "probe": probe_name,
                "detail": str(exc)[:500],
            }

        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "probe failed").strip()
            return {
                "status": "blocked",
                "reason_code": "PROBE_NONZERO_EXIT",
                "probe": probe_name,
                "returncode": completed.returncode,
                "detail": detail[-1000:],
            }

        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        try:
            payload = json.loads(lines[-1])
        except (IndexError, json.JSONDecodeError):
            return {
                "status": "blocked",
                "reason_code": "PROBE_INVALID_JSON",
                "probe": probe_name,
            }
        if not isinstance(payload, dict):
            return {
                "status": "blocked",
                "reason_code": "PROBE_INVALID_PAYLOAD",
                "probe": probe_name,
            }
        return {"status": "passed", "probe": probe_name, "details": payload}

    @staticmethod
    def _generation_readiness(
        device_execution: Dict[str, Any], pipeline_imports: Dict[str, Any]
    ) -> Dict[str, Any]:
        prerequisites_verified = (
            device_execution.get("status") == "passed"
            and pipeline_imports.get("status") == "passed"
        )
        blockers = [
            "MODEL_WEIGHTS_NOT_VERIFIED",
            "MODEL_INSTANTIATION_NOT_VERIFIED",
            "END_TO_END_GENERATION_NOT_VERIFIED",
        ]
        if not prerequisites_verified:
            blockers.insert(0, "RUNTIME_PREREQUISITES_NOT_VERIFIED")
        return {
            "status": (
                "prerequisites_verified_generation_not_attempted"
                if prerequisites_verified
                else "blocked"
            ),
            "ready": False,
            "prerequisites_verified": prerequisites_verified,
            "generation_attempted": False,
            "weights_downloaded": False,
            "blocker_codes": blockers,
        }

    def probe(self) -> Dict[str, Any]:
        """Return an honest readiness report without downloading or generating media."""

        executable = str(self.executable)
        if not self.executable.is_file():
            missing = {
                "status": "blocked",
                "reason_code": "XPU_PYTHON_NOT_FOUND",
                "executable": executable,
            }
            return {
                "status": "blocked",
                "executable": executable,
                "offline": True,
                "device_execution": dict(missing),
                "pipeline_imports": dict(missing),
                "model_generation_readiness": self._generation_readiness(missing, missing),
            }

        device_execution = self._run(_DEVICE_EXECUTION_SCRIPT, "device_execution")
        pipeline_imports = self._run(_PIPELINE_IMPORT_SCRIPT, "pipeline_imports")
        generation = self._generation_readiness(device_execution, pipeline_imports)
        prerequisites_verified = generation["prerequisites_verified"]
        return {
            "status": (
                "runtime_ready_generation_unverified"
                if prerequisites_verified
                else "blocked"
            ),
            "executable": executable,
            "offline": True,
            "device_execution": device_execution,
            "pipeline_imports": pipeline_imports,
            "model_generation_readiness": generation,
        }


def probe_intel_xpu_runtime(
    executable: str | Path = DEFAULT_XPU_PYTHON,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Convenience entry point for the bounded Intel XPU runtime probe."""

    return IntelXpuRuntimeProbe(
        executable=executable,
        timeout_seconds=timeout_seconds,
    ).probe()


__all__ = [
    "DEFAULT_XPU_PYTHON",
    "IntelXpuRuntimeProbe",
    "probe_intel_xpu_runtime",
]
