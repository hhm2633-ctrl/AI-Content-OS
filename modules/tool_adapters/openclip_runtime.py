"""Fail-closed capability probe for the isolated local OpenCLIP runtime."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any, Callable, Dict, Mapping, Optional, Sequence


PROBE_SCHEMA = "openclip_runtime_probe_v1"
SCORE_SCHEMA = "openclip_image_topic_score_v1"
PROVENANCE_SCHEMA = "openclip_install_provenance_v1"
ALLOWED_IMAGE_SUFFIXES = frozenset({".jpeg", ".jpg", ".png", ".webp"})
MAX_IMAGE_BYTES = 50 * 1024 * 1024
MAX_TOPICS = 16
MAX_TOPIC_LENGTH = 300
DEFAULT_SCORE_TIMEOUT_SECONDS = 30.0
MAX_SCORE_TIMEOUT_SECONDS = 60.0
PINNED_MODEL_REPOSITORY = "timm/resnet50_clip.openai"
PINNED_MODEL_NAME = "RN50-quickgelu"
PINNED_MODEL_REVISION = "ec3d92cf63a5f9d591f0d611b736895966c73076"
DEFAULT_RUNTIME_ROOT = Path("F:/AI-Content-OS-Data/external_tools/runtimes/openclip")
DEFAULT_MODEL_ROOT = Path(
    "F:/AI-Content-OS-Data/external_tools/models/openclip/"
    "timm--resnet50_clip.openai--ec3d92cf63a5"
)
DEFAULT_PROVENANCE_PATH = Path(
    "F:/AI-Content-OS-Data/external_tools/provenance/openclip/install_manifest.json"
)

_SCORE_SCRIPT = """
import json
import sys

import open_clip
from PIL import Image
import torch

weight_path, image_path, topics_json = sys.argv[1:4]
topics = json.loads(topics_json)
model, _, preprocess = open_clip.create_model_and_transforms(
    "RN50-quickgelu", pretrained=weight_path, device="cpu"
)
tokenizer = open_clip.get_tokenizer("RN50-quickgelu")
model.eval()
torch.set_grad_enabled(False)
image = preprocess(Image.open(image_path).convert("RGB")).unsqueeze(0)
text = tokenizer(topics)
image_embedding = model.encode_image(image)
text_embeddings = model.encode_text(text)
image_embedding = image_embedding / image_embedding.norm(dim=-1, keepdim=True)
text_embeddings = text_embeddings / text_embeddings.norm(dim=-1, keepdim=True)
scores = (image_embedding @ text_embeddings.T).squeeze(0).tolist()
print(json.dumps({
    "offline": True,
    "model_name": "RN50-quickgelu",
    "embedding_dim": int(image_embedding.shape[-1]),
    "image_norm": float(image_embedding.norm()),
    "text_norms": [float(value) for value in text_embeddings.norm(dim=-1)],
    "topics": topics,
    "cosine_similarity": scores,
}))
""".strip()


def _read_json(path: Path) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "provenance_missing"
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"provenance_invalid:{type(exc).__name__}"
    if not isinstance(payload, dict):
        return None, "provenance_invalid:not_object"
    return payload, None


def _sha256(path: Path) -> Optional[str]:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _resolve_recorded_path(recorded: Any, fallback: Path) -> Path:
    if isinstance(recorded, str) and recorded.strip():
        return Path(recorded).expanduser().resolve()
    return fallback.resolve()


def _valid_revision(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(
        character in "0123456789abcdefABCDEF" for character in value
    )


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _normalized_smoke_ready(smoke: Any) -> bool:
    if not isinstance(smoke, Mapping) or smoke.get("passed") is not True or smoke.get("offline") is not True:
        return False
    image_norm = smoke.get("image_norm")
    text_norms = smoke.get("text_norms")
    scores = smoke.get("cosine_similarity")
    if not isinstance(image_norm, (int, float)) or not math.isclose(float(image_norm), 1.0, abs_tol=1e-4):
        return False
    if not isinstance(text_norms, list) or not text_norms:
        return False
    if not all(isinstance(value, (int, float)) and math.isclose(float(value), 1.0, abs_tol=1e-4) for value in text_norms):
        return False
    return isinstance(scores, list) and len(scores) == len(text_norms) and all(
        isinstance(value, (int, float)) and math.isfinite(float(value)) for value in scores
    )


class OpenClipRuntime:
    """Validate local runtime, licenses, pinned weights, and offline smoke receipt."""

    def __init__(
        self,
        *,
        runtime_root: str | Path = DEFAULT_RUNTIME_ROOT,
        model_root: str | Path = DEFAULT_MODEL_ROOT,
        provenance_path: str | Path = DEFAULT_PROVENANCE_PATH,
    ) -> None:
        self.runtime_root = Path(runtime_root).expanduser().resolve()
        self.model_root = Path(model_root).expanduser().resolve()
        self.provenance_path = Path(provenance_path).expanduser().resolve()

    def probe(self) -> Dict[str, Any]:
        manifest, manifest_error = _read_json(self.provenance_path)
        if manifest_error or manifest is None:
            return {
                "schema_version": PROBE_SCHEMA,
                "status": "blocked",
                "ready": False,
                "errors": [manifest_error or "provenance_invalid"],
                "boundaries": self._boundaries(),
            }

        runtime = manifest.get("runtime") if isinstance(manifest.get("runtime"), Mapping) else {}
        code_license = manifest.get("code_license") if isinstance(manifest.get("code_license"), Mapping) else {}
        weights = manifest.get("weights") if isinstance(manifest.get("weights"), Mapping) else {}
        python_path = self.runtime_root / "Scripts" / "python.exe"
        code_license_path = _resolve_recorded_path(code_license.get("installed_license_path"), self.runtime_root / "LICENSE")
        weight_path = _resolve_recorded_path(weights.get("weight_path"), self.model_root / "open_clip_model.safetensors")

        code_bytes = code_license_path.stat().st_size if code_license_path.is_file() else None
        weight_bytes = weight_path.stat().st_size if weight_path.is_file() else None
        code_hash = _sha256(code_license_path) if code_bytes is not None else None
        weight_hash = _sha256(weight_path) if weight_bytes is not None else None

        checks = {
            "provenance_schema": manifest.get("schema_version") == PROVENANCE_SCHEMA,
            "runtime_python": python_path.is_file(),
            "runtime_version": runtime.get("open_clip_torch") == "3.3.0",
            "code_license": (
                code_license.get("spdx") == "MIT"
                and code_license.get("commercial_reuse") is True
                and _is_within(code_license_path, self.runtime_root)
                and code_bytes == code_license.get("license_bytes")
                and code_hash == code_license.get("license_sha256")
            ),
            "weight_repository": weights.get("repository") == PINNED_MODEL_REPOSITORY,
            "weight_model": weights.get("model_name") == PINNED_MODEL_NAME,
            "weight_revision": (
                _valid_revision(weights.get("revision"))
                and weights.get("revision") == PINNED_MODEL_REVISION
            ),
            "weight_access": weights.get("private") is False and weights.get("gated") is False,
            "weight_license": weights.get("license_spdx") == "MIT" and weights.get("commercial_reuse") is True,
            "weight_integrity": (
                weight_path == (self.model_root / "open_clip_model.safetensors").resolve()
                and weight_bytes == weights.get("weight_bytes")
                and weight_hash == weights.get("weight_sha256")
            ),
            "offline_smoke": _normalized_smoke_ready(manifest.get("smoke")),
        }
        errors = [f"{name}_check_failed" for name, ready in checks.items() if not ready]
        ready = all(checks.values())
        return {
            "schema_version": PROBE_SCHEMA,
            "status": "ready" if ready else "blocked",
            "ready": ready,
            "runtime_root": str(self.runtime_root),
            "model_root": str(self.model_root),
            "provenance_path": str(self.provenance_path),
            "python_executable": str(python_path),
            "model": {
                "repository": weights.get("repository"),
                "model_name": weights.get("model_name"),
                "revision": weights.get("revision"),
                "path": str(weight_path),
                "bytes": weight_bytes,
                "sha256": weight_hash,
            },
            "licenses": {
                "code": {
                    "spdx": code_license.get("spdx"),
                    "commercial_reuse": code_license.get("commercial_reuse"),
                    "path": str(code_license_path),
                    "sha256": code_hash,
                },
                "weights": {
                    "spdx": weights.get("license_spdx"),
                    "commercial_reuse": weights.get("commercial_reuse"),
                    "evidence": weights.get("license_evidence"),
                },
            },
            "capabilities": {
                "image_embedding": ready,
                "text_embedding": ready,
                "normalized_similarity": ready,
                "offline_cpu": ready,
            },
            "checks": checks,
            "errors": errors,
            "boundaries": self._boundaries(),
        }

    @staticmethod
    def _validate_score_input(
        image_path: str | Path,
        topics: Sequence[str],
        timeout_seconds: float,
    ) -> tuple[Path, list[str], float]:
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise ValueError("timeout_seconds must be numeric")
        timeout = float(timeout_seconds)
        if timeout <= 0 or timeout > MAX_SCORE_TIMEOUT_SECONDS:
            raise ValueError(f"timeout_seconds must be > 0 and <= {MAX_SCORE_TIMEOUT_SECONDS:g}")
        image = Path(image_path).expanduser().resolve()
        if not image.is_file():
            raise FileNotFoundError(f"image does not exist: {image}")
        if image.suffix.casefold() not in ALLOWED_IMAGE_SUFFIXES:
            raise ValueError("image suffix must be one of: .jpeg, .jpg, .png, .webp")
        image_bytes = image.stat().st_size
        if image_bytes <= 0 or image_bytes > MAX_IMAGE_BYTES:
            raise ValueError(f"image must be non-empty and <= {MAX_IMAGE_BYTES} bytes")
        if isinstance(topics, (str, bytes)) or not isinstance(topics, Sequence):
            raise ValueError("topics must be a sequence of strings")
        cleaned = []
        for topic in topics:
            if not isinstance(topic, str) or not topic.strip():
                raise ValueError("every topic must be a non-empty string")
            value = topic.strip()
            if len(value) > MAX_TOPIC_LENGTH:
                raise ValueError(f"each topic must be <= {MAX_TOPIC_LENGTH} characters")
            cleaned.append(value)
        if not cleaned or len(cleaned) > MAX_TOPICS:
            raise ValueError(f"topics must contain between 1 and {MAX_TOPICS} entries")
        return image, cleaned, timeout

    @staticmethod
    def _parse_score_payload(stdout: str) -> Optional[Dict[str, Any]]:
        for line in reversed(stdout.splitlines()):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        return None

    @staticmethod
    def _score_payload_valid(payload: Any, topics: Sequence[str]) -> bool:
        if not isinstance(payload, Mapping):
            return False
        if payload.get("offline") is not True or payload.get("model_name") != "RN50-quickgelu":
            return False
        if payload.get("topics") != list(topics):
            return False
        image_norm = payload.get("image_norm")
        text_norms = payload.get("text_norms")
        scores = payload.get("cosine_similarity")
        if not isinstance(image_norm, (int, float)) or not math.isclose(float(image_norm), 1.0, abs_tol=1e-4):
            return False
        if not isinstance(text_norms, list) or len(text_norms) != len(topics):
            return False
        if not all(isinstance(value, (int, float)) and math.isclose(float(value), 1.0, abs_tol=1e-4) for value in text_norms):
            return False
        return isinstance(scores, list) and len(scores) == len(topics) and all(
            isinstance(value, (int, float))
            and math.isfinite(float(value))
            and -1.0001 <= float(value) <= 1.0001
            for value in scores
        )

    def score_image_topics(
        self,
        image_path: str | Path,
        topics: Sequence[str],
        *,
        timeout_seconds: float = DEFAULT_SCORE_TIMEOUT_SECONDS,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> Dict[str, Any]:
        """Return bounded offline cosine scores as an internal relevance proxy."""

        image, cleaned_topics, timeout = self._validate_score_input(
            image_path, topics, timeout_seconds
        )
        probe = self.probe()
        base = {
            "schema_version": SCORE_SCHEMA,
            "score_semantics": "internal_semantic_relevance_proxy",
            "not_evidence_for": [
                "factual_accuracy",
                "source_support",
                "rights_or_license",
                "published_performance",
            ],
            "image_path": str(image),
            "topics": cleaned_topics,
            "runtime_probe": probe,
        }
        if not probe.get("ready"):
            return {
                **base,
                "status": "blocked",
                "passed": False,
                "reason": "runtime_probe_not_ready",
            }

        command = [
            probe["python_executable"],
            "-c",
            _SCORE_SCRIPT,
            probe["model"]["path"],
            str(image),
            json.dumps(cleaned_topics, ensure_ascii=False),
        ]
        environment = os.environ.copy()
        environment.update(
            {
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "HF_HUB_DISABLE_TELEMETRY": "1",
                "TOKENIZERS_PARALLELISM": "false",
            }
        )
        try:
            completed = runner(
                command,
                cwd=str(self.model_root),
                env=environment,
                timeout=timeout,
                capture_output=True,
                text=True,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            return {**base, "status": "timeout", "passed": False, "reason": "score_timeout"}
        except OSError as exc:
            return {
                **base,
                "status": "failed",
                "passed": False,
                "reason": f"subprocess_error:{type(exc).__name__}",
            }

        stdout = str(completed.stdout or "")
        stderr = str(completed.stderr or "")
        payload = self._parse_score_payload(stdout)
        payload_valid = self._score_payload_valid(payload, cleaned_topics)
        passed = completed.returncode == 0 and payload_valid
        if completed.returncode != 0:
            reason = "nonzero_exit"
        elif not payload_valid:
            reason = "invalid_normalized_embedding_receipt"
        else:
            reason = None
        ranked = []
        if passed and payload is not None:
            ranked = sorted(
                (
                    {"topic": topic, "cosine_similarity": float(score)}
                    for topic, score in zip(cleaned_topics, payload["cosine_similarity"])
                ),
                key=lambda item: item["cosine_similarity"],
                reverse=True,
            )
        return {
            **base,
            "status": "passed" if passed else "failed",
            "passed": passed,
            "reason": reason,
            "returncode": completed.returncode,
            "embedding_receipt": payload,
            "ranked_topics": ranked,
            "stdout_tail": stdout[-2000:],
            "stderr_tail": stderr[-2000:],
            "execution_contract": {
                "model_name": "RN50-quickgelu",
                "model_revision": probe["model"]["revision"],
                "offline": True,
                "shell": False,
                "timeout_seconds": timeout,
            },
        }

    @staticmethod
    def _boundaries() -> Dict[str, bool]:
        return {
            "offline_only": True,
            "owner_assets": False,
            "remote_service": False,
            "model_download": False,
            "training_or_finetuning": False,
            "production_selection": False,
        }


def probe_openclip_runtime() -> Dict[str, Any]:
    return OpenClipRuntime().probe()
