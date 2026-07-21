"""Offline-safe resolver for the isolated Sentence Transformers environment."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from email.parser import Parser
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any, Callable, Mapping, Optional, Sequence


SENTENCE_TRANSFORMERS_RUNTIME_ROOT_ENV = "SENTENCE_TRANSFORMERS_RUNTIME_ROOT"
SENTENCE_TRANSFORMERS_MODEL_ROOT_ENV = "SENTENCE_TRANSFORMERS_MODEL_ROOT"
DEFAULT_SENTENCE_TRANSFORMERS_RUNTIME_ROOT = Path(
    r"F:\AI-Content-OS-Data\tools\sentence-transformers"
)
DEFAULT_SENTENCE_TRANSFORMERS_MODEL_ROOT = Path(
    r"F:\AI-Content-OS-Data\external_tools\models\sentence-transformers"
    r"\paraphrase-multilingual-MiniLM-L12-v2"
)
DEFAULT_SENTENCE_TRANSFORMERS_MODEL_REVISION = (
    "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
)
OFFLINE_ENVIRONMENT = (
    ("HF_HUB_OFFLINE", "1"),
    ("TRANSFORMERS_OFFLINE", "1"),
    ("HF_DATASETS_OFFLINE", "1"),
)
SIMILARITY_SCHEMA_VERSION = "sentence_transformers_text_similarity_v1"
MAX_SIMILARITY_PAIRS = 128
MAX_TEXT_LENGTH = 1000
MAX_TOTAL_TEXT_LENGTH = 64_000
DEFAULT_SIMILARITY_TIMEOUT_SECONDS = 30.0
MAX_SIMILARITY_TIMEOUT_SECONDS = 60.0

_SIMILARITY_SCRIPT = r"""
import json
import sys

from sentence_transformers import SentenceTransformer

model_root = sys.argv[1]
request = json.loads(sys.stdin.read())
pairs = request["pairs"]
texts = []
indexes = {}
pair_indexes = []
for left, right in pairs:
    row = []
    for value in (left, right):
        if value not in indexes:
            indexes[value] = len(texts)
            texts.append(value)
        row.append(indexes[value])
    pair_indexes.append(row)

model = SentenceTransformer(model_root, local_files_only=True, device="cpu")
embeddings = model.encode(
    texts,
    normalize_embeddings=True,
    convert_to_numpy=True,
    show_progress_bar=False,
)
scores = [float(embeddings[left] @ embeddings[right]) for left, right in pair_indexes]
print(json.dumps({"offline": True, "scores": scores}))
""".strip()


@dataclass(frozen=True)
class SentenceTransformersRuntime:
    ready: bool
    root: str
    python_executable: str
    package_path: str
    version: str
    license: str
    license_path: str
    notice_path: str
    source: str
    offline_environment: tuple[tuple[str, str], ...]
    diagnostics: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SentenceTransformersModel:
    ready: bool
    root: str
    revision: str
    license: str
    source: str
    required_files: tuple[str, ...]
    diagnostics: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _root(environment: Mapping[str, str]) -> tuple[Path, str]:
    override = str(
        environment.get(SENTENCE_TRANSFORMERS_RUNTIME_ROOT_ENV, "")
    ).strip().strip('"')
    if override:
        return Path(override).expanduser(), "environment_root"
    return DEFAULT_SENTENCE_TRANSFORMERS_RUNTIME_ROOT, "default_root"


def _metadata(root: Path) -> tuple[Path | None, dict[str, str]]:
    site_packages = root / "Lib" / "site-packages"
    candidates = sorted(site_packages.glob("sentence_transformers-*.dist-info/METADATA"))
    if not candidates:
        return None, {}
    path = candidates[-1]
    try:
        message = Parser().parsestr(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return path, {}
    return path, {
        "version": str(message.get("Version", "")),
        "license": str(message.get("License-Expression") or message.get("License") or ""),
    }


def resolve_sentence_transformers_runtime(
    *, env: Mapping[str, str] | None = None
) -> SentenceTransformersRuntime:
    environment = os.environ if env is None else env
    root, source = _root(environment)
    python = root / "Scripts" / "python.exe"
    package = root / "Lib" / "site-packages" / "sentence_transformers" / "__init__.py"
    metadata_path, metadata = _metadata(root)
    license_path = metadata_path.parent / "licenses" / "LICENSE" if metadata_path else Path()
    notice_path = metadata_path.parent / "licenses" / "NOTICE.txt" if metadata_path else Path()
    diagnostics: list[str] = []
    if not root.is_dir():
        diagnostics.append(f"runtime_root_missing:{root}")
    if not python.is_file() or python.stat().st_size <= 0:
        diagnostics.append(f"python_executable_missing:{python}")
    if not package.is_file():
        diagnostics.append(f"package_import_file_missing:{package}")
    if metadata_path is None:
        diagnostics.append(f"package_metadata_missing:{root / 'Lib' / 'site-packages'}")
    elif not metadata.get("version"):
        diagnostics.append(f"package_version_missing:{metadata_path}")
    if metadata_path is None or not license_path.is_file():
        diagnostics.append(
            f"license_file_missing:{license_path if metadata_path else root / 'Lib' / 'site-packages'}"
        )

    return SentenceTransformersRuntime(
        ready=not diagnostics,
        root=str(root),
        python_executable=str(python) if python.is_file() else "",
        package_path=str(package) if package.is_file() else "",
        version=metadata.get("version", ""),
        license=metadata.get("license", ""),
        license_path=str(license_path) if metadata_path and license_path.is_file() else "",
        notice_path=str(notice_path) if metadata_path and notice_path.is_file() else "",
        source=source,
        offline_environment=OFFLINE_ENVIRONMENT,
        diagnostics=tuple(diagnostics),
    )


def resolve_sentence_transformers_model(
    *, env: Mapping[str, str] | None = None
) -> SentenceTransformersModel:
    """Resolve the pinned local multilingual model without network access."""

    environment = os.environ if env is None else env
    override = str(
        environment.get(SENTENCE_TRANSFORMERS_MODEL_ROOT_ENV, "")
    ).strip().strip('"')
    root = Path(override).expanduser() if override else DEFAULT_SENTENCE_TRANSFORMERS_MODEL_ROOT
    source = "environment_model_root" if override else "default_model_root"
    required = (
        "model.safetensors",
        "modules.json",
        "config.json",
        "tokenizer.json",
        "1_Pooling/config.json",
    )
    diagnostics: list[str] = []
    if not root.is_dir():
        diagnostics.append(f"model_root_missing:{root}")
    for relative in required:
        path = root / relative
        if not path.is_file() or path.stat().st_size <= 0:
            diagnostics.append(f"model_file_missing:{path}")

    return SentenceTransformersModel(
        ready=not diagnostics,
        root=str(root),
        revision=DEFAULT_SENTENCE_TRANSFORMERS_MODEL_REVISION,
        license="Apache-2.0",
        source=source,
        required_files=required,
        diagnostics=tuple(diagnostics),
    )


def _validate_similarity_request(
    pairs: Sequence[Sequence[str]], timeout_seconds: float
) -> tuple[list[tuple[str, str]], float]:
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
        raise ValueError("timeout_seconds must be numeric")
    timeout = float(timeout_seconds)
    if timeout <= 0 or timeout > MAX_SIMILARITY_TIMEOUT_SECONDS:
        raise ValueError(
            f"timeout_seconds must be > 0 and <= {MAX_SIMILARITY_TIMEOUT_SECONDS:g}"
        )
    if isinstance(pairs, (str, bytes)) or not isinstance(pairs, Sequence):
        raise ValueError("pairs must be a sequence of two-string sequences")
    if not pairs or len(pairs) > MAX_SIMILARITY_PAIRS:
        raise ValueError(
            f"pairs must contain between 1 and {MAX_SIMILARITY_PAIRS} entries"
        )

    cleaned: list[tuple[str, str]] = []
    total_length = 0
    for pair in pairs:
        if isinstance(pair, (str, bytes)) or not isinstance(pair, Sequence) or len(pair) != 2:
            raise ValueError("each pair must contain exactly two strings")
        values: list[str] = []
        for text in pair:
            if not isinstance(text, str) or not text.strip():
                raise ValueError("pair texts must be non-empty strings")
            value = " ".join(text.strip().split())
            if len(value) > MAX_TEXT_LENGTH:
                raise ValueError(f"each text must be <= {MAX_TEXT_LENGTH} characters")
            total_length += len(value)
            values.append(value)
        cleaned.append((values[0], values[1]))
    if total_length > MAX_TOTAL_TEXT_LENGTH:
        raise ValueError(f"total pair text must be <= {MAX_TOTAL_TEXT_LENGTH} characters")
    return cleaned, timeout


def _last_json_object(stdout: str) -> Optional[dict[str, Any]]:
    for line in reversed(stdout.splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def score_text_pairs(
    pairs: Sequence[Sequence[str]],
    *,
    timeout_seconds: float = DEFAULT_SIMILARITY_TIMEOUT_SECONDS,
    env: Mapping[str, str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """Score bounded text pairs with the pinned local model only.

    The cosine values are an internal semantic-relevance proxy. They are not
    factual, source, rights, popularity, or performance evidence.
    """

    cleaned, timeout = _validate_similarity_request(pairs, timeout_seconds)
    runtime = resolve_sentence_transformers_runtime(env=env)
    model = resolve_sentence_transformers_model(env=env)
    boundaries = {
        "offline_only": True,
        "local_pinned_model_only": True,
        "score_semantics": "internal_semantic_similarity_proxy",
        "not_fact_evidence": True,
        "not_rights_evidence": True,
        "not_performance_evidence": True,
    }
    if not runtime.ready or not model.ready:
        return {
            "schema_version": SIMILARITY_SCHEMA_VERSION,
            "status": "unavailable",
            "ready": False,
            "scores": [],
            "pair_count": len(cleaned),
            "errors": [*runtime.diagnostics, *model.diagnostics],
            "fallback": "existing_deterministic_similarity",
            "boundaries": boundaries,
        }

    child_environment = dict(os.environ if env is None else env)
    child_environment.update(dict(OFFLINE_ENVIRONMENT))
    # Force UTF-8 stdio in the child process. Without this, the child's
    # own locale (e.g. cp949 on Korean Windows) decodes the UTF-8 JSON
    # written to its stdin incorrectly, corrupting non-ASCII text into
    # invalid surrogate characters before it ever reaches the tokenizer.
    child_environment["PYTHONIOENCODING"] = "utf-8"
    child_environment["PYTHONUTF8"] = "1"
    command = [runtime.python_executable, "-c", _SIMILARITY_SCRIPT, model.root]
    try:
        completed = runner(
            command,
            input=json.dumps({"pairs": cleaned}, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=child_environment,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "schema_version": SIMILARITY_SCHEMA_VERSION,
            "status": "timeout",
            "ready": False,
            "scores": [],
            "pair_count": len(cleaned),
            "errors": ["similarity_timeout"],
            "fallback": "existing_deterministic_similarity",
            "boundaries": boundaries,
        }
    except OSError as exc:
        return {
            "schema_version": SIMILARITY_SCHEMA_VERSION,
            "status": "failed",
            "ready": False,
            "scores": [],
            "pair_count": len(cleaned),
            "errors": [f"similarity_process_error:{type(exc).__name__}"],
            "fallback": "existing_deterministic_similarity",
            "boundaries": boundaries,
        }

    payload = _last_json_object(completed.stdout or "")
    raw_scores = payload.get("scores") if isinstance(payload, Mapping) else None
    valid_scores = (
        completed.returncode == 0
        and isinstance(payload, Mapping)
        and payload.get("offline") is True
        and isinstance(raw_scores, list)
        and len(raw_scores) == len(cleaned)
        and all(
            isinstance(score, (int, float))
            and not isinstance(score, bool)
            and math.isfinite(float(score))
            and -1.000001 <= float(score) <= 1.000001
            for score in raw_scores
        )
    )
    if not valid_scores:
        return {
            "schema_version": SIMILARITY_SCHEMA_VERSION,
            "status": "failed",
            "ready": False,
            "scores": [],
            "pair_count": len(cleaned),
            "errors": [f"invalid_similarity_output:returncode={completed.returncode}"],
            "fallback": "existing_deterministic_similarity",
            "boundaries": boundaries,
        }
    return {
        "schema_version": SIMILARITY_SCHEMA_VERSION,
        "status": "completed",
        "ready": True,
        "scores": [round(float(score), 6) for score in raw_scores],
        "pair_count": len(cleaned),
        "model": {
            "root": model.root,
            "revision": model.revision,
            "runtime_version": runtime.version,
        },
        "errors": [],
        "fallback": None,
        "boundaries": boundaries,
    }


__all__ = [
    "DEFAULT_SENTENCE_TRANSFORMERS_RUNTIME_ROOT",
    "DEFAULT_SENTENCE_TRANSFORMERS_MODEL_ROOT",
    "DEFAULT_SENTENCE_TRANSFORMERS_MODEL_REVISION",
    "OFFLINE_ENVIRONMENT",
    "SIMILARITY_SCHEMA_VERSION",
    "MAX_SIMILARITY_PAIRS",
    "MAX_TEXT_LENGTH",
    "MAX_TOTAL_TEXT_LENGTH",
    "DEFAULT_SIMILARITY_TIMEOUT_SECONDS",
    "MAX_SIMILARITY_TIMEOUT_SECONDS",
    "SENTENCE_TRANSFORMERS_RUNTIME_ROOT_ENV",
    "SENTENCE_TRANSFORMERS_MODEL_ROOT_ENV",
    "SentenceTransformersModel",
    "SentenceTransformersRuntime",
    "resolve_sentence_transformers_model",
    "resolve_sentence_transformers_runtime",
    "score_text_pairs",
]
