"""Side-effect-free resolver for the isolated SeleniumBase environment."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from email.parser import Parser
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping


SELENIUMBASE_RUNTIME_ROOT_ENV = "SELENIUMBASE_RUNTIME_ROOT"
SELENIUMBASE_DRIVER_ROOT_ENV = "SELENIUMBASE_DRIVER_ROOT"
DEFAULT_SELENIUMBASE_RUNTIME_ROOT = Path(
    r"F:\AI-Content-OS-Data\tools\seleniumbase"
)
PINNED_CHROMEDRIVER_VERSION = "150.0.7871.124"
DEFAULT_SELENIUMBASE_DRIVER_ROOT = (
    DEFAULT_SELENIUMBASE_RUNTIME_ROOT / "drivers" / PINNED_CHROMEDRIVER_VERSION
)
DEFAULT_CHROMEDRIVER_PATH = (
    DEFAULT_SELENIUMBASE_DRIVER_ROOT
    / "package"
    / "chromedriver-win64"
    / "chromedriver.exe"
)
DEFAULT_CHROMEDRIVER_PROVENANCE_PATH = (
    DEFAULT_SELENIUMBASE_DRIVER_ROOT / "install_manifest.json"
)
CHROMEDRIVER_PROVENANCE_SCHEMA = "seleniumbase_chromedriver_provenance_v1"


@dataclass(frozen=True)
class SeleniumBaseRuntime:
    ready: bool
    root: str
    python_executable: str
    package_path: str
    version: str
    license: str
    license_path: str
    source: str
    driver_root: str
    driver_path: str
    driver_version: str
    driver_bytes: int
    driver_sha256: str
    driver_provenance_path: str
    diagnostics: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _root(environment: Mapping[str, str]) -> tuple[Path, str]:
    override = str(environment.get(SELENIUMBASE_RUNTIME_ROOT_ENV, "")).strip().strip('"')
    if override:
        return Path(override).expanduser(), "environment_root"
    return DEFAULT_SELENIUMBASE_RUNTIME_ROOT, "default_root"


def _driver_root(environment: Mapping[str, str]) -> Path:
    override = str(environment.get(SELENIUMBASE_DRIVER_ROOT_ENV, "")).strip().strip('"')
    return Path(override).expanduser() if override else DEFAULT_SELENIUMBASE_DRIVER_ROOT


def _read_manifest(path: Path) -> tuple[dict[str, Any], str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, f"driver_provenance_missing:{path}"
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {}, f"driver_provenance_invalid:{type(exc).__name__}"
    if not isinstance(payload, dict):
        return {}, "driver_provenance_invalid:not_object"
    return payload, ""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata(root: Path) -> tuple[Path | None, dict[str, str]]:
    site_packages = root / "Lib" / "site-packages"
    candidates = sorted(site_packages.glob("seleniumbase-*.dist-info/METADATA"))
    if not candidates:
        return None, {}
    path = candidates[-1]
    try:
        message = Parser().parsestr(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return path, {}
    return path, {
        "name": str(message.get("Name", "")),
        "version": str(message.get("Version", "")),
        "license": str(message.get("License-Expression") or message.get("License") or ""),
    }


def resolve_seleniumbase_runtime(
    *, env: Mapping[str, str] | None = None
) -> SeleniumBaseRuntime:
    environment = os.environ if env is None else env
    root, source = _root(environment)
    driver_root = _driver_root(environment)
    driver_path = driver_root / "package" / "chromedriver-win64" / "chromedriver.exe"
    provenance_path = driver_root / "install_manifest.json"
    python = root / "Scripts" / "python.exe"
    package = root / "Lib" / "site-packages" / "seleniumbase" / "__init__.py"
    metadata_path, metadata = _metadata(root)
    license_path = (
        metadata_path.parent / "licenses" / "LICENSE"
        if metadata_path is not None
        else Path()
    )
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

    manifest, manifest_error = _read_manifest(provenance_path)
    if manifest_error:
        diagnostics.append(manifest_error)
    driver_record = manifest.get("driver") if isinstance(manifest.get("driver"), Mapping) else {}
    source_record = manifest.get("source") if isinstance(manifest.get("source"), Mapping) else {}
    runtime_policy = (
        manifest.get("runtime_policy")
        if isinstance(manifest.get("runtime_policy"), Mapping)
        else {}
    )
    driver_bytes = driver_path.stat().st_size if driver_path.is_file() else 0
    driver_hash = _sha256(driver_path) if driver_bytes > 0 else ""
    if not driver_path.is_file() or driver_bytes <= 0:
        diagnostics.append(f"chromedriver_missing:{driver_path}")
    if manifest and manifest.get("schema_version") != CHROMEDRIVER_PROVENANCE_SCHEMA:
        diagnostics.append("driver_provenance_schema_mismatch")
    if manifest and source_record.get("provider") != "Chrome for Testing":
        diagnostics.append("driver_provider_not_official_cft")
    if manifest and source_record.get("version") != PINNED_CHROMEDRIVER_VERSION:
        diagnostics.append("driver_version_not_pinned")
    if manifest and int(driver_record.get("bytes") or 0) != driver_bytes:
        diagnostics.append("driver_bytes_mismatch")
    if manifest and str(driver_record.get("sha256") or "").casefold() != driver_hash.casefold():
        diagnostics.append("driver_sha256_mismatch")
    if manifest and not (
        runtime_policy.get("offline_local_driver_only") is True
        and runtime_policy.get("selenium_manager_forbidden") is True
        and runtime_policy.get("runtime_download_forbidden") is True
    ):
        diagnostics.append("driver_runtime_policy_invalid")

    return SeleniumBaseRuntime(
        ready=not diagnostics,
        root=str(root),
        python_executable=str(python) if python.is_file() else "",
        package_path=str(package) if package.is_file() else "",
        version=metadata.get("version", ""),
        license=metadata.get("license", ""),
        license_path=str(license_path) if metadata_path and license_path.is_file() else "",
        source=source,
        driver_root=str(driver_root),
        driver_path=str(driver_path) if driver_path.is_file() else "",
        driver_version=str(source_record.get("version") or ""),
        driver_bytes=driver_bytes,
        driver_sha256=driver_hash,
        driver_provenance_path=str(provenance_path) if provenance_path.is_file() else "",
        diagnostics=tuple(diagnostics),
    )


__all__ = [
    "DEFAULT_SELENIUMBASE_RUNTIME_ROOT",
    "DEFAULT_SELENIUMBASE_DRIVER_ROOT",
    "DEFAULT_CHROMEDRIVER_PATH",
    "DEFAULT_CHROMEDRIVER_PROVENANCE_PATH",
    "PINNED_CHROMEDRIVER_VERSION",
    "SELENIUMBASE_RUNTIME_ROOT_ENV",
    "SELENIUMBASE_DRIVER_ROOT_ENV",
    "SeleniumBaseRuntime",
    "resolve_seleniumbase_runtime",
]
