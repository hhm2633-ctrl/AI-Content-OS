"""Offline, fail-closed readiness probe for local publishing references.

Mixpost and TryPost are inspected as source references only.  This module never
boots PHP, loads Composer autoloaders, starts workers, or calls publishing APIs.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


SCHEMA_VERSION = "publishing_reference_runtime_v1"
DEFAULT_REFERENCE_ROOTS: Mapping[str, Path] = {
    "mixpost": Path(
        "F:/AI-Content-OS-Data/tools/publishing-source/"
        "inovector--mixpost/mixpost-main"
    ),
    "trypost": Path(
        "F:/AI-Content-OS-Data/tools/publishing-source/"
        "trypost-it--trypost/trypost-main"
    ),
}

PROJECT_PROFILES: Mapping[str, Mapping[str, Any]] = {
    "mixpost": {
        "composer_name": "inovector/mixpost",
        "source_slug": "inovector/mixpost",
        "license": "MIT",
        "autoload_namespace": "Inovector\\Mixpost\\",
        "autoload_target": "src",
        "platform_mode": "directories",
        "platform_path": "src/SocialProviders",
    },
    "trypost": {
        "composer_name": "trypost-it/trypost",
        "source_slug": "trypost-it/trypost",
        "license": "AGPL-3.0-only",
        "autoload_namespace": "App\\",
        "autoload_target": "app/",
        "platform_mode": "php_enum",
        "platform_path": "app/Enums/SocialAccount/Platform.php",
    },
}

_EXCLUDED_MEASUREMENT_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    "storage",
}
_VERSION_PATTERN = re.compile(r"^[vV]?\d+\.\d+(?:\.\d+)?(?:[-+][0-9A-Za-z.-]+)?$")
_COMPOSER_PRETTY_VERSION = re.compile(r"'pretty_version'\s*=>\s*'([^']+)'", re.IGNORECASE)
_PHP_ENUM_CASE = re.compile(r"\bcase\s+[A-Za-z_][A-Za-z0-9_]*\s*=\s*['\"]([^'\"]+)['\"]\s*;")


def _read_json(path: Path) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"missing:{path.name}"
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"invalid:{path.name}:{type(exc).__name__}"
    if not isinstance(payload, dict):
        return None, f"invalid:{path.name}:not_object"
    return payload, None


def _read_text(path: Path, *, max_bytes: int = 128_000) -> Optional[str]:
    try:
        with path.open("rb") as stream:
            raw = stream.read(max_bytes + 1)
    except OSError:
        return None
    if len(raw) > max_bytes:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _source_url(composer: Mapping[str, Any]) -> Optional[str]:
    support = composer.get("support")
    if isinstance(support, Mapping) and isinstance(support.get("source"), str):
        return support["source"].strip() or None
    homepage = composer.get("homepage")
    return homepage.strip() if isinstance(homepage, str) and homepage.strip() else None


def _version_evidence(root: Path, composer: Mapping[str, Any]) -> Dict[str, Any]:
    manifest_version = composer.get("version")
    if isinstance(manifest_version, str) and _VERSION_PATTERN.fullmatch(manifest_version.strip()):
        return {"ready": True, "value": manifest_version.strip(), "source": "composer.json"}

    version_file = _read_text(root / "VERSION", max_bytes=200)
    if version_file and _VERSION_PATTERN.fullmatch(version_file.strip()):
        return {"ready": True, "value": version_file.strip(), "source": "VERSION"}

    head = _read_text(root / ".git" / "HEAD", max_bytes=500)
    if head:
        head = head.strip()
        if re.fullmatch(r"[0-9a-fA-F]{40}", head):
            return {"ready": True, "value": head.lower(), "source": ".git/HEAD"}
        if head.startswith("ref: "):
            ref_path = root / ".git" / head[5:].strip()
            ref_value = _read_text(ref_path, max_bytes=200)
            if ref_value and re.fullmatch(r"[0-9a-fA-F]{40}", ref_value.strip()):
                return {"ready": True, "value": ref_value.strip().lower(), "source": str(ref_path.relative_to(root))}

    installed = _read_text(root / "vendor" / "composer" / "installed.php")
    installed_version = None
    if installed:
        match = _COMPOSER_PRETTY_VERSION.search(installed)
        installed_version = match.group(1) if match else None
        if installed_version and "no-version-set" not in installed_version.lower() and _VERSION_PATTERN.fullmatch(installed_version):
            return {"ready": True, "value": installed_version, "source": "vendor/composer/installed.php"}
    return {
        "ready": False,
        "value": installed_version,
        "source": "vendor/composer/installed.php" if installed_version else None,
        "reason": "source_version_unpinned",
    }


def _license_evidence(root: Path, declared: Any, expected: str) -> Dict[str, Any]:
    license_path = next(
        (root / name for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING") if (root / name).is_file()),
        None,
    )
    text = _read_text(license_path) if license_path else None
    declared_matches = isinstance(declared, str) and declared.casefold() == expected.casefold()
    if expected == "MIT":
        text_matches = bool(text and "MIT License" in text)
    else:
        text_matches = bool(text and "GNU AFFERO GENERAL PUBLIC LICENSE" in text.upper())
    ready = declared_matches and text_matches
    return {
        "ready": ready,
        "declared": declared if isinstance(declared, str) else None,
        "expected": expected,
        "path": str(license_path) if license_path else None,
        "reason": None if ready else "license_evidence_missing_or_mismatched",
    }


def _platform_evidence(root: Path, profile: Mapping[str, Any]) -> Dict[str, Any]:
    path = root / str(profile["platform_path"])
    values = []
    if profile["platform_mode"] == "directories" and path.is_dir():
        values = sorted(child.name.casefold() for child in path.iterdir() if child.is_dir())
    elif profile["platform_mode"] == "php_enum" and path.is_file():
        text = _read_text(path)
        if text:
            values = sorted(set(_PHP_ENUM_CASE.findall(text)))
    return {
        "ready": bool(values),
        "path": str(path),
        "platforms": values,
        "reason": None if values else "platform_evidence_missing",
    }


def _autoload_evidence(root: Path, composer: Mapping[str, Any], profile: Mapping[str, Any]) -> Dict[str, Any]:
    autoload = composer.get("autoload")
    psr4 = autoload.get("psr-4") if isinstance(autoload, Mapping) else None
    namespace = str(profile["autoload_namespace"])
    expected_target = str(profile["autoload_target"])
    declared_target = psr4.get(namespace) if isinstance(psr4, Mapping) else None
    target = root / expected_target
    vendor_autoload = root / "vendor" / "autoload.php"
    ready = declared_target == expected_target and target.is_dir() and vendor_autoload.is_file()
    return {
        "ready": ready,
        "namespace": namespace,
        "declared_target": declared_target,
        "expected_target": expected_target,
        "target_exists": target.is_dir(),
        "vendor_autoload_exists": vendor_autoload.is_file(),
        "reason": None if ready else "autoload_evidence_incomplete",
    }


def _measure_source(root: Path) -> Dict[str, int]:
    file_count = 0
    byte_count = 0
    for current, directories, files in os.walk(root, followlinks=False):
        directories[:] = [name for name in directories if name not in _EXCLUDED_MEASUREMENT_DIRS]
        current_path = Path(current)
        for name in files:
            path = current_path / name
            try:
                if path.is_symlink():
                    continue
                byte_count += path.stat().st_size
                file_count += 1
            except OSError:
                continue
    return {"source_file_count": file_count, "source_bytes": byte_count}


class PublishingReferenceRuntime:
    """Inspect local source copies without executing either application."""

    def __init__(self, roots: Optional[Mapping[str, str | Path]] = None) -> None:
        selected = roots or DEFAULT_REFERENCE_ROOTS
        self.roots = {name: Path(path).expanduser().resolve() for name, path in selected.items()}

    def probe_project(self, project: str) -> Dict[str, Any]:
        if project not in PROJECT_PROFILES:
            return {
                "project": project,
                "status": "blocked",
                "reference_ready": False,
                "errors": ["unsupported_project"],
            }
        root = self.roots.get(project)
        profile = PROJECT_PROFILES[project]
        if root is None or not root.is_dir():
            return {
                "project": project,
                "status": "blocked",
                "reference_ready": False,
                "root": str(root) if root else None,
                "errors": ["reference_root_missing"],
            }

        composer, manifest_error = _read_json(root / "composer.json")
        composer = composer or {}
        source_url = _source_url(composer)
        identity_ready = composer.get("name") == profile["composer_name"]
        source_ready = bool(source_url and str(profile["source_slug"]).casefold() in source_url.casefold())
        php_requirement = composer.get("require", {}).get("php") if isinstance(composer.get("require"), Mapping) else None
        runtime_platform_ready = isinstance(php_requirement, str) and bool(php_requirement.strip())
        version = _version_evidence(root, composer)
        license_evidence = _license_evidence(root, composer.get("license"), str(profile["license"]))
        autoload = _autoload_evidence(root, composer, profile)
        platforms = _platform_evidence(root, profile)
        checks = {
            "manifest": manifest_error is None,
            "identity": identity_ready,
            "source": source_ready,
            "version": version["ready"],
            "license": license_evidence["ready"],
            "runtime_platform": runtime_platform_ready,
            "autoload": autoload["ready"],
            "social_platforms": platforms["ready"],
        }
        errors = []
        if manifest_error:
            errors.append(manifest_error)
        errors.extend(f"{name}_evidence_missing" for name, ready in checks.items() if not ready and name != "manifest")
        ready = all(checks.values())
        return {
            "project": project,
            "status": "reference_ready" if ready else "blocked",
            "reference_ready": ready,
            "root": str(root),
            "identity": {
                "ready": identity_ready,
                "composer_name": composer.get("name"),
                "expected": profile["composer_name"],
            },
            "source": {"ready": source_ready, "url": source_url},
            "version": version,
            "license": license_evidence,
            "runtime_platform": {
                "ready": runtime_platform_ready,
                "php_requirement": php_requirement,
            },
            "autoload": autoload,
            "social_platforms": platforms,
            "measurement": _measure_source(root),
            "errors": list(dict.fromkeys(errors)),
            "boundaries": {
                "reference_only": True,
                "application_execution": False,
                "autoload_execution": False,
                "database": False,
                "server_or_worker": False,
                "network_or_api": False,
                "publishing": False,
            },
        }

    def probe(self) -> Dict[str, Any]:
        projects = {name: self.probe_project(name) for name in PROJECT_PROFILES}
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "reference_ready" if all(item["reference_ready"] for item in projects.values()) else "blocked",
            "reference_ready": all(item["reference_ready"] for item in projects.values()),
            "projects": projects,
        }


def probe_publishing_references(
    roots: Optional[Mapping[str, str | Path]] = None,
) -> Dict[str, Any]:
    return PublishingReferenceRuntime(roots).probe()

