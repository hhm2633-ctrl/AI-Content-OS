"""Fail-closed subprocess bridge for the installed local CardNews renderer.

Capability probing and smoke checks remain side-effect free.  The production entry
is callable only from a current controller authorization with matching completed
local-media hashes; it writes new files under an explicit F: output root and never
publishes or replaces source evidence.
"""

from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from modules.card_news.production_controller import (
    BATCH_AUTHORIZED,
    REPRESENTATIVE_AUTHORIZED,
    ProductionControllerError,
    canonical_hash,
    validate_state,
)


PROBE_SCHEMA = "cardnews_renderer_runtime_probe_v1"
SMOKE_SCHEMA = "cardnews_renderer_runtime_smoke_v1"
RENDER_REQUEST_SCHEMA = "cardnews_renderer_request_v1"
RENDER_RECEIPT_SCHEMA = "cardnews_renderer_receipt_v1"
NODE_ENV_VAR = "AI_CONTENT_OS_CARDNEWS_RENDERER_NODE"
MAX_SMOKE_TIMEOUT_SECONDS = 30.0
DEFAULT_SMOKE_TIMEOUT_SECONDS = 20.0
MAX_RENDER_TIMEOUT_SECONDS = 90.0
DEFAULT_RENDER_TIMEOUT_SECONDS = 60.0
MAX_RENDER_REQUEST_BYTES = 2 * 1024 * 1024
MAX_SLIDES = 10
ALLOWED_CANVAS_SIZES = frozenset({(1080, 566), (1080, 1080), (1080, 1350), (1080, 1440)})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_F_DRIVE_PATH = re.compile(r"^[Ff]:[\\/]")
_SAFE_OUTPUT_NAME = re.compile(r"^[0-9A-Za-z._-]+\.png$")
_REMOTE_OR_FILE_URL = re.compile(r"(?:https?|ftp)://|file://", re.IGNORECASE)

CANVAS_PROFILES: Mapping[str, Mapping[str, Any]] = {
    "instagram_portrait_4_5": {
        "profile_id": "instagram_portrait_4_5",
        "width": 1080,
        "height": 1350,
        "aspect_ratio": "4:5",
        "safe_previews": {
            "central_square": {"x": 0, "y": 135, "width": 1080, "height": 1080},
            "profile_grid_3_4": {"x": 30, "y": 0, "width": 1020, "height": 1350},
        },
    },
    "instagram_square_1_1": {
        "profile_id": "instagram_square_1_1",
        "width": 1080,
        "height": 1080,
        "aspect_ratio": "1:1",
        "safe_previews": {
            "central_square": {"x": 0, "y": 0, "width": 1080, "height": 1080},
            "profile_grid_3_4": {"x": 135, "y": 0, "width": 810, "height": 1080},
        },
    },
    "instagram_landscape_1_91_1": {
        "profile_id": "instagram_landscape_1_91_1",
        "width": 1080,
        "height": 566,
        "aspect_ratio": "1.91:1",
        "safe_previews": {
            "central_square": {"x": 257, "y": 0, "width": 566, "height": 566},
            "profile_grid_3_4": {"x": 328, "y": 0, "width": 424, "height": 566},
        },
    },
    "instagram_portrait_3_4": {
        "profile_id": "instagram_portrait_3_4",
        "width": 1080,
        "height": 1440,
        "aspect_ratio": "3:4",
        "safe_previews": {
            "central_square": {"x": 0, "y": 180, "width": 1080, "height": 1080},
            "profile_grid_3_4": {"x": 0, "y": 0, "width": 1080, "height": 1440},
        },
    },
}
PROTECTED_SUBJECT_KINDS = frozenset({"hair", "outfit", "product", "comment"})

ENGINE_PACKAGES: Mapping[str, tuple[str, ...]] = {
    "satori": ("satori",),
    "resvg": ("@resvg/resvg-js",),
    "fabric": ("fabric", "esbuild"),
    "motion_canvas": ("@motion-canvas/core", "@motion-canvas/2d", "esbuild"),
}

ENGINE_CAPABILITIES: Mapping[str, str] = {
    "satori": "html_like_tree_to_svg",
    "resvg": "svg_to_png_in_memory",
    "fabric": "browser_canvas_bundle_validation",
    "motion_canvas": "motion_scene_bundle_validation",
}


def _default_tool_root() -> Path:
    return Path(__file__).resolve().parents[2] / "tools" / "cardnews-renderer"


def _read_json_object(path: Path) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"missing:{path.name}"
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"invalid:{path.name}:{type(exc).__name__}"
    if not isinstance(value, dict):
        return None, f"invalid:{path.name}:not_object"
    return value, None


def _resolve_node(candidate: Optional[str | Path]) -> Optional[Path]:
    raw = str(candidate or os.environ.get(NODE_ENV_VAR, "")).strip()
    if raw:
        explicit = Path(raw).expanduser()
        if explicit.is_file():
            return explicit.resolve()
        located = shutil.which(raw)
        return Path(located).resolve() if located else None
    located = shutil.which("node")
    return Path(located).resolve() if located else None


class CardNewsRendererRuntime:
    """Validate and smoke-check the isolated Node renderer package."""

    def __init__(
        self,
        tool_root: Optional[str | Path] = None,
        *,
        node_executable: Optional[str | Path] = None,
    ) -> None:
        self.tool_root = Path(tool_root or _default_tool_root()).expanduser().resolve()
        self.node_executable = _resolve_node(node_executable)

    @property
    def package_path(self) -> Path:
        return self.tool_root / "package.json"

    @property
    def smoke_path(self) -> Path:
        return self.tool_root / "smoke.mjs"

    @property
    def production_render_path(self) -> Path:
        return self.tool_root / "production-render.mjs"

    def _installed_version(self, package_name: str) -> tuple[Optional[str], Optional[str]]:
        manifest = self.tool_root / "node_modules" / Path(package_name) / "package.json"
        payload, error = _read_json_object(manifest)
        if error:
            return None, error.replace("package.json", package_name)
        version = payload.get("version") if payload else None
        if not isinstance(version, str) or not version.strip():
            return None, f"invalid_version:{package_name}"
        return version, None

    def probe(self) -> Dict[str, Any]:
        package, package_error = _read_json_object(self.package_path)
        dependencies: Mapping[str, Any] = {}
        dev_dependencies: Mapping[str, Any] = {}
        errors = []
        if package_error:
            errors.append(package_error)
        elif package is not None:
            raw_dependencies = package.get("dependencies", {})
            raw_dev_dependencies = package.get("devDependencies", {})
            if isinstance(raw_dependencies, dict):
                dependencies = raw_dependencies
            else:
                errors.append("invalid:dependencies:not_object")
            if isinstance(raw_dev_dependencies, dict):
                dev_dependencies = raw_dev_dependencies
            else:
                errors.append("invalid:devDependencies:not_object")

        declared_versions = {**dev_dependencies, **dependencies}
        engines: Dict[str, Any] = {}
        for engine, required_packages in ENGINE_PACKAGES.items():
            package_states = []
            for package_name in required_packages:
                declared_version = declared_versions.get(package_name)
                installed_version, install_error = self._installed_version(package_name)
                declared = isinstance(declared_version, str) and bool(declared_version.strip())
                version_matches = declared and installed_version == declared_version
                package_states.append(
                    {
                        "name": package_name,
                        "declared_version": declared_version if declared else None,
                        "installed_version": installed_version,
                        "ready": bool(version_matches),
                        "reason": (
                            None
                            if version_matches
                            else install_error
                            or ("not_declared" if not declared else "version_mismatch")
                        ),
                    }
                )
            ready = all(item["ready"] for item in package_states)
            engines[engine] = {
                "capability": ENGINE_CAPABILITIES[engine],
                "ready": ready,
                "packages": package_states,
            }
            if not ready:
                errors.append(f"engine_not_ready:{engine}")

        node_ready = self.node_executable is not None
        smoke_ready = self.smoke_path.is_file()
        production_render_ready = self.production_render_path.is_file()
        if not node_ready:
            errors.append("node_not_found")
        if not smoke_ready:
            errors.append("smoke_script_missing")
        if not production_render_ready:
            errors.append("production_render_script_missing")
        ready = package is not None and node_ready and smoke_ready and production_render_ready and all(
            item["ready"] for item in engines.values()
        )
        return {
            "schema_version": PROBE_SCHEMA,
            "status": "ready" if ready else "blocked",
            "ready": ready,
            "tool_root": str(self.tool_root),
            "package_path": str(self.package_path),
            "smoke_path": str(self.smoke_path),
            "production_render_path": str(self.production_render_path),
            "node_executable": str(self.node_executable) if self.node_executable else None,
            "engines": engines,
            "errors": list(dict.fromkeys(errors)),
            "boundaries": {
                "network": False,
                "package_install": False,
                "production_render": False,
                "media_output_files": False,
            },
            "production_engine_roles": {
                "invoked": ["satori", "resvg"],
                "capability_only": ["fabric", "motion_canvas"],
            },
        }

    def smoke_contract(self, *, timeout_seconds: float = DEFAULT_SMOKE_TIMEOUT_SECONDS) -> Dict[str, Any]:
        if isinstance(timeout_seconds, bool) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if timeout_seconds > MAX_SMOKE_TIMEOUT_SECONDS:
            raise ValueError(
                f"timeout_seconds must be <= {MAX_SMOKE_TIMEOUT_SECONDS:g}"
            )
        command = (
            [str(self.node_executable), str(self.smoke_path)]
            if self.node_executable
            else None
        )
        return {
            "command": command,
            "cwd": str(self.tool_root),
            "timeout_seconds": float(timeout_seconds),
            "shell": False,
            "capture_output": True,
            "writes_media_files": False,
        }

    @staticmethod
    def _contains_external_url(value: Any) -> bool:
        if isinstance(value, str):
            return bool(_REMOTE_OR_FILE_URL.search(value))
        if isinstance(value, Mapping):
            return any(CardNewsRendererRuntime._contains_external_url(item) for item in value.values())
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return any(CardNewsRendererRuntime._contains_external_url(item) for item in value)
        return False

    @staticmethod
    def _blocked_render(reason: str, detail: str = "") -> Dict[str, Any]:
        return {
            "schema_version": RENDER_REQUEST_SCHEMA,
            "status": "blocked",
            "ready": False,
            "reason": reason,
            "detail": detail,
            "command": None,
            "subprocess_allowed": False,
            "invoked_engines": [],
            "capability_only_engines": ["fabric", "motion_canvas"],
        }

    @staticmethod
    def _canonical_hash(value: Mapping[str, Any]) -> str:
        canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _valid_bounds(value: Any, *, normalized: bool) -> bool:
        if not isinstance(value, Mapping):
            return False
        numbers = [value.get(name) for name in ("x", "y", "width", "height")]
        if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in numbers):
            return False
        x, y, width, height = (float(item) for item in numbers)
        if x < 0 or y < 0 or width <= 0 or height <= 0:
            return False
        return not normalized or (x + width <= 1 and y + height <= 1)

    @staticmethod
    def _contained(inner: Mapping[str, Any], outer: Mapping[str, Any]) -> bool:
        return (
            float(inner["x"]) >= float(outer["x"])
            and float(inner["y"]) >= float(outer["y"])
            and float(inner["x"]) + float(inner["width"]) <= float(outer["x"]) + float(outer["width"])
            and float(inner["y"]) + float(inner["height"]) <= float(outer["y"]) + float(outer["height"])
        )

    @staticmethod
    def _center_cover_window(source_width: int, source_height: int, target_width: float, target_height: float) -> Dict[str, float]:
        source_ratio = source_width / source_height
        target_ratio = target_width / target_height
        if source_ratio > target_ratio:
            width = target_ratio / source_ratio
            return {"x": (1 - width) / 2, "y": 0.0, "width": width, "height": 1.0}
        height = source_ratio / target_ratio
        return {"x": 0.0, "y": (1 - height) / 2, "width": 1.0, "height": height}

    def _validated_asset_metadata(
        self,
        assets: Any,
        profile: Mapping[str, Any],
        *,
        slide_position: int,
    ) -> tuple[Optional[list[Dict[str, Any]]], Optional[str]]:
        if not isinstance(assets, list):
            return None, "asset_metadata_missing"
        normalized: list[Dict[str, Any]] = []
        previews = profile["safe_previews"]
        for position, raw in enumerate(assets, start=1):
            field = f"slides[{slide_position}].assets[{position}]"
            if not isinstance(raw, Mapping):
                return None, f"asset_metadata_invalid:{field}"
            asset_id = str(raw.get("asset_id") or "").strip()
            source_width, source_height = raw.get("source_width"), raw.get("source_height")
            target_bounds = raw.get("target_bounds")
            focus_bounds = raw.get("focus_bounds")
            crop_strategy = str(raw.get("crop_strategy") or "").strip()
            if not asset_id or any(
                isinstance(value, bool) or not isinstance(value, int) or value < 1
                for value in (source_width, source_height)
            ):
                return None, f"asset_identity_or_size_invalid:{field}"
            if not self._valid_bounds(focus_bounds, normalized=True) or not self._valid_bounds(target_bounds, normalized=False):
                return None, f"asset_bounds_invalid:{field}"
            canvas_bounds = {"x": 0, "y": 0, "width": profile["width"], "height": profile["height"]}
            if not self._contained(target_bounds, canvas_bounds):
                return None, f"asset_target_outside_canvas:{field}"
            if crop_strategy not in {"contain", "no_crop", "focus_fit", "center_cover"}:
                return None, f"crop_strategy_invalid:{field}"
            if crop_strategy == "center_cover":
                crop_window = self._center_cover_window(
                    source_width,
                    source_height,
                    float(target_bounds["width"]),
                    float(target_bounds["height"]),
                )
                if not self._contained(focus_bounds, crop_window):
                    return None, f"center_cover_would_crop_focus:{field}"
            subjects = raw.get("protected_subjects")
            if not isinstance(subjects, list):
                return None, f"protected_subjects_missing:{field}"
            normalized_subjects = []
            for subject_position, subject in enumerate(subjects, start=1):
                subject_field = f"{field}.protected_subjects[{subject_position}]"
                if not isinstance(subject, Mapping):
                    return None, f"protected_subject_invalid:{subject_field}"
                kind = str(subject.get("kind") or "").strip()
                source_bounds = subject.get("source_bounds")
                projected_bounds = subject.get("canvas_bounds")
                if kind not in PROTECTED_SUBJECT_KINDS:
                    return None, f"protected_subject_kind_invalid:{subject_field}"
                if not self._valid_bounds(source_bounds, normalized=True) or not self._valid_bounds(projected_bounds, normalized=False):
                    return None, f"protected_subject_bounds_invalid:{subject_field}"
                if not self._contained(projected_bounds, canvas_bounds):
                    return None, f"protected_subject_outside_canvas:{subject_field}"
                if not all(self._contained(projected_bounds, preview) for preview in previews.values()):
                    return None, f"protected_subject_outside_safe_preview:{subject_field}"
                if crop_strategy == "center_cover":
                    if not self._contained(source_bounds, crop_window):
                        return None, f"center_cover_would_crop_protected_subject:{subject_field}"
                normalized_subjects.append(
                    {"kind": kind, "source_bounds": dict(source_bounds), "canvas_bounds": dict(projected_bounds)}
                )
            normalized.append(
                {
                    "asset_id": asset_id,
                    "source_width": source_width,
                    "source_height": source_height,
                    "target_bounds": dict(target_bounds),
                    "focus_bounds": dict(focus_bounds),
                    "crop_strategy": crop_strategy,
                    "protected_subjects": normalized_subjects,
                    "preservation_check": "metadata_contract_only_pending_visual_qa",
                }
            )
        return normalized, None

    @staticmethod
    def _validate_issued_authorization(
        authorization: Any,
        controller_state: Mapping[str, Any],
        request: Mapping[str, Any],
    ) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        if not isinstance(authorization, Mapping) or authorization.get("authorized") is not True:
            return None, "issued_render_authorization_required"
        token = dict(authorization)
        if token.get("schema_version") != "cardnews_render_authorization_v1":
            return None, "render_authorization_schema_invalid"
        authorization_id = str(token.get("authorization_id") or "").strip()
        unhashed = dict(token)
        unhashed.pop("authorization_id", None)
        if authorization_id != f"render-{canonical_hash(unhashed)[:24]}":
            return None, "render_authorization_tampered"
        if authorization_id in controller_state.get("used_render_authorization_ids", []):
            return None, "render_authorization_reused"
        try:
            expiry = datetime.fromisoformat(str(token.get("expires_at") or "").strip())
        except ValueError:
            return None, "render_authorization_expiry_invalid"
        if expiry.tzinfo is None or datetime.now().astimezone() >= expiry:
            return None, "render_authorization_expired"

        mode = str(request.get("mode") or "representative").strip().lower()
        candidate_id = str(request.get("candidate_id") or "").strip()
        expected_candidates = (
            sorted(controller_state.get("representatives", {}).values())
            if mode == "representative"
            else sorted(controller_state.get("candidate_ids", []))
        )
        if token.get("mode") != mode or sorted(token.get("candidate_ids") or []) != expected_candidates:
            return None, "render_authorization_scope_mismatch"
        if candidate_id not in expected_candidates:
            return None, "candidate_not_authorized"
        for token_field, state_field in (
            ("controller_state_hash", "state_hash"),
            ("controller_id", "controller_id"),
            ("hard_rule_hash", "hard_rule_hash"),
            ("batch_hash", "batch_hash"),
        ):
            if token.get(token_field) != controller_state.get(state_field):
                return None, "render_authorization_binding_mismatch"
        expected_media = {
            item: list(controller_state.get("local_media_receipt_hashes", {}).get(item, []))
            for item in expected_candidates
        }
        if token.get("local_media_receipt_hashes") != expected_media or token.get("local_media_binding_hash") != canonical_hash(expected_media):
            return None, "render_authorization_media_mismatch"
        if request.get("local_media_receipt_hashes") != expected_media.get(candidate_id):
            return None, "local_media_hash_binding_mismatch"
        if str(request.get("input_sha256") or "").strip() != str(token.get("input_sha256") or "").strip():
            return None, "render_authorization_input_mismatch"
        token_root = str(token.get("output_root") or "").rstrip("\\/").casefold()
        request_root = str(request.get("output_root") or "").rstrip("\\/").casefold()
        if not token_root or not (request_root == token_root or request_root.startswith(token_root + "\\") or request_root.startswith(token_root + "/")):
            return None, "render_authorization_output_mismatch"
        tooling = token.get("tooling_authorization") if isinstance(token.get("tooling_authorization"), Mapping) else {}
        if (
            tooling.get("renderer") is not True
            or tooling.get("satori") is not True
            or tooling.get("resvg") is not True
            or tooling.get("fabric") is not False
            or tooling.get("motion") is not False
            or tooling.get("scope") != mode
            or tooling.get("authorization_metadata_only") is not True
            or tooling.get("execution_performed") is not False
        ):
            return None, "render_authorization_tooling_invalid"
        if request.get("output_set_id") != authorization_id:
            return None, "render_authorization_output_set_mismatch"
        if mode == "batch" and token.get("representative_visual_qa_receipt_ids") != controller_state.get("representative_qa_receipt_ids"):
            return None, "render_authorization_representative_qa_mismatch"
        return token, None

    def render_contract(
        self,
        controller_state: Mapping[str, Any],
        request: Mapping[str, Any],
        *,
        authorization: Mapping[str, Any] | None = None,
        timeout_seconds: float = DEFAULT_RENDER_TIMEOUT_SECONDS,
    ) -> Dict[str, Any]:
        """Authorize one bounded local render without starting a subprocess."""

        if isinstance(timeout_seconds, bool) or timeout_seconds <= 0 or timeout_seconds > MAX_RENDER_TIMEOUT_SECONDS:
            raise ValueError(f"timeout_seconds must be > 0 and <= {MAX_RENDER_TIMEOUT_SECONDS:g}")
        if not isinstance(request, Mapping):
            return self._blocked_render("render_request_invalid")
        try:
            validate_state(controller_state)
        except (ProductionControllerError, TypeError, ValueError) as error:
            return self._blocked_render("controller_authorization_invalid", str(error))
        token, authorization_error = self._validate_issued_authorization(
            authorization, controller_state, request
        )
        if authorization_error:
            return self._blocked_render(authorization_error)

        mode = str(request.get("mode") or "representative").strip().lower()
        expected_state = REPRESENTATIVE_AUTHORIZED if mode == "representative" else BATCH_AUTHORIZED if mode == "batch" else ""
        if not expected_state:
            return self._blocked_render("render_mode_invalid")
        if controller_state.get("state") != expected_state:
            return self._blocked_render("controller_state_not_authorized", f"{mode} requires {expected_state}")
        for field in ("state_hash", "batch_hash", "hard_rule_hash"):
            value = str(controller_state.get(field) or "").lower()
            if not _SHA256.fullmatch(value):
                return self._blocked_render("controller_binding_hash_invalid", field)

        candidate_id = str(request.get("candidate_id") or "").strip()
        if not candidate_id:
            return self._blocked_render("candidate_id_missing")
        if mode == "representative":
            authorized_candidates = set((controller_state.get("representatives") or {}).values())
        else:
            authorized_candidates = set(controller_state.get("candidate_ids") or [])
        if candidate_id not in authorized_candidates:
            return self._blocked_render("candidate_not_authorized")

        state_hashes = (controller_state.get("local_media_receipt_hashes") or {}).get(candidate_id)
        request_hashes = request.get("local_media_receipt_hashes")
        if not isinstance(state_hashes, list) or not state_hashes:
            return self._blocked_render("completed_local_media_hashes_missing")
        if not isinstance(request_hashes, list) or sorted(request_hashes) != sorted(state_hashes):
            return self._blocked_render("local_media_hash_binding_mismatch")
        if any(not isinstance(value, str) or not _SHA256.fullmatch(value.lower()) for value in state_hashes):
            return self._blocked_render("local_media_hash_invalid")

        if mode == "batch":
            approved_qa_ids = controller_state.get("representative_qa_receipt_ids")
            if not isinstance(approved_qa_ids, Mapping) or set(approved_qa_ids) != set(controller_state.get("accounts") or []):
                return self._blocked_render("representative_qa_authorization_missing")
            if dict(request.get("representative_qa_receipt_ids") or {}) != dict(approved_qa_ids):
                return self._blocked_render("representative_qa_binding_mismatch")
            if not str(controller_state.get("batch_authorization_hash") or "").strip():
                return self._blocked_render("batch_authorization_hash_missing")

        output_root = str(request.get("output_root") or "").strip()
        if not _F_DRIVE_PATH.match(output_root):
            return self._blocked_render("output_root_must_be_f_drive")
        canvas_profile = request.get("canvas_profile")
        if not isinstance(canvas_profile, Mapping):
            return self._blocked_render("canvas_profile_missing")
        profile_id = str(canvas_profile.get("profile_id") or "").strip()
        expected_profile = CANVAS_PROFILES.get(profile_id)
        if expected_profile is None or dict(canvas_profile) != dict(expected_profile):
            return self._blocked_render("canvas_profile_invalid")
        canvas_profile_hash = self._canonical_hash(canvas_profile)
        slides = request.get("slides")
        if not isinstance(slides, list) or not 1 <= len(slides) <= MAX_SLIDES:
            return self._blocked_render("slide_count_out_of_bounds")

        normalized_slides = []
        seen_pages = set()
        for position, slide in enumerate(slides, start=1):
            if not isinstance(slide, Mapping):
                return self._blocked_render("slide_invalid", f"slides[{position}]")
            page = slide.get("page")
            width, height = slide.get("width"), slide.get("height")
            tree = slide.get("tree")
            classification = str(slide.get("media_classification") or "").strip()
            label = str(slide.get("display_label") or "").strip()
            if isinstance(page, bool) or not isinstance(page, int) or page < 1 or page in seen_pages:
                return self._blocked_render("slide_page_invalid", f"slides[{position}]")
            seen_pages.add(page)
            if (width, height) != (canvas_profile["width"], canvas_profile["height"]):
                return self._blocked_render("carousel_canvas_profile_mismatch", f"slides[{position}]")
            if not isinstance(tree, Mapping) or self._contains_external_url(tree):
                return self._blocked_render("slide_tree_invalid_or_external", f"slides[{position}]")
            if classification not in {"source_evidence", "generated_editorial", "motion_graphic"}:
                return self._blocked_render("media_classification_invalid", f"slides[{position}]")
            if classification != "source_evidence" and not label:
                return self._blocked_render("generated_or_motion_label_missing", f"slides[{position}]")
            if classification == "motion_graphic":
                return self._blocked_render("motion_canvas_not_production_connected", f"slides[{position}]")
            normalized_assets, asset_error = self._validated_asset_metadata(
                slide.get("assets"), canvas_profile, slide_position=position
            )
            if asset_error:
                return self._blocked_render(asset_error)
            output_filename = f"page-{page:03d}.png"
            if not _SAFE_OUTPUT_NAME.fullmatch(output_filename):
                return self._blocked_render("output_filename_invalid")
            normalized_slides.append(
                {
                    "page": page,
                    "width": width,
                    "height": height,
                    "tree": dict(tree),
                    "output_filename": output_filename,
                    "media_classification": classification,
                    "display_label": label,
                    "assets": normalized_assets,
                }
            )

        render_request_id = str(request.get("render_request_id") or "").strip()
        output_set_id = str(request.get("output_set_id") or "").strip()
        if not render_request_id or not output_set_id:
            return self._blocked_render("render_identity_missing")
        probe = self.probe()
        if not probe.get("ready") or self.node_executable is None:
            return self._blocked_render("renderer_probe_not_ready", ",".join(probe.get("errors") or []))

        payload = {
            "schema_version": RENDER_REQUEST_SCHEMA,
            "render_request_id": render_request_id,
            "candidate_id": candidate_id,
            "mode": mode,
            "output_set_id": output_set_id,
            "output_root": output_root,
            "authorization": {
                "authorization_id": token["authorization_id"],
                "controller_id": controller_state.get("controller_id"),
                "controller_state_hash": controller_state.get("state_hash"),
                "batch_hash": controller_state.get("batch_hash"),
                "hard_rule_hash": controller_state.get("hard_rule_hash"),
                "batch_authorization_hash": controller_state.get("batch_authorization_hash"),
                "representative_qa_receipt_ids": dict(controller_state.get("representative_qa_receipt_ids") or {}),
            },
            "controller_state": dict(controller_state),
            "local_media_receipt_hashes": sorted(state_hashes),
            "canvas_profile": dict(canvas_profile),
            "canvas_profile_hash": canvas_profile_hash,
            "slides": normalized_slides,
        }
        stdin_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if len(stdin_json.encode("utf-8")) > MAX_RENDER_REQUEST_BYTES:
            return self._blocked_render("render_request_too_large")
        return {
            "schema_version": RENDER_REQUEST_SCHEMA,
            "status": "ready",
            "ready": True,
            "reason": None,
            "command": [str(self.node_executable), str(self.production_render_path)],
            "cwd": str(self.tool_root),
            "timeout_seconds": float(timeout_seconds),
            "shell": False,
            "stdin_json": stdin_json,
            "subprocess_allowed": True,
            "writes_media_files": True,
            "output_root": output_root,
            "canvas_profile_hash": canvas_profile_hash,
            "invoked_engines": ["satori", "resvg"],
            "capability_only_engines": ["fabric", "motion_canvas"],
        }

    @staticmethod
    def _parse_smoke_payload(stdout: str) -> Optional[Dict[str, Any]]:
        for line in reversed(stdout.splitlines()):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        return None

    @staticmethod
    def _valid_smoke_payload(payload: Optional[Mapping[str, Any]]) -> bool:
        if payload is None:
            return False
        flags = ("korean_font", "satori_svg")
        sizes = ("fabric_browser_bundle_bytes", "motion_bundle_bytes", "resvg_png_bytes")
        return all(payload.get(name) is True for name in flags) and all(
            isinstance(payload.get(name), int)
            and not isinstance(payload.get(name), bool)
            and payload[name] > 0
            for name in sizes
        )

    def run_smoke(
        self,
        *,
        timeout_seconds: float = DEFAULT_SMOKE_TIMEOUT_SECONDS,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> Dict[str, Any]:
        """Invoke only ``smoke.mjs`` with a hard timeout and no shell."""

        contract = self.smoke_contract(timeout_seconds=timeout_seconds)
        probe = self.probe()
        base = {
            "schema_version": SMOKE_SCHEMA,
            "contract": contract,
            "probe": probe,
        }
        if not probe["ready"] or contract["command"] is None:
            return {**base, "status": "blocked", "passed": False, "reason": "probe_not_ready"}

        try:
            completed = runner(
                contract["command"],
                cwd=contract["cwd"],
                timeout=contract["timeout_seconds"],
                capture_output=True,
                text=True,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            return {**base, "status": "timeout", "passed": False, "reason": "smoke_timeout"}
        except OSError as exc:
            return {
                **base,
                "status": "failed",
                "passed": False,
                "reason": f"subprocess_error:{type(exc).__name__}",
            }

        stdout = str(completed.stdout or "")
        stderr = str(completed.stderr or "")
        payload = self._parse_smoke_payload(stdout)
        payload_valid = self._valid_smoke_payload(payload)
        passed = completed.returncode == 0 and payload_valid
        if completed.returncode != 0:
            reason = "nonzero_exit"
        elif not payload_valid:
            reason = "invalid_smoke_payload"
        else:
            reason = None
        return {
            **base,
            "status": "passed" if passed else "failed",
            "passed": passed,
            "reason": reason,
            "returncode": completed.returncode,
            "payload": payload,
            "stdout_tail": stdout[-2000:],
            "stderr_tail": stderr[-2000:],
        }

    def run_render(
        self,
        controller_state: Mapping[str, Any],
        request: Mapping[str, Any],
        *,
        authorization: Mapping[str, Any] | None = None,
        timeout_seconds: float = DEFAULT_RENDER_TIMEOUT_SECONDS,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> Dict[str, Any]:
        """Run the package-owned static entry after every authorization gate passes."""

        contract = self.render_contract(
            controller_state,
            request,
            authorization=authorization,
            timeout_seconds=timeout_seconds,
        )
        base = {"contract": contract, "passed": False}
        if not contract.get("ready") or not contract.get("subprocess_allowed"):
            return {**base, "status": "blocked", "reason": contract.get("reason")}
        try:
            completed = runner(
                contract["command"],
                cwd=contract["cwd"],
                timeout=contract["timeout_seconds"],
                input=contract["stdin_json"],
                capture_output=True,
                text=True,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            return {**base, "status": "timeout", "reason": "render_timeout"}
        except OSError as error:
            return {
                **base,
                "status": "failed",
                "reason": f"subprocess_error:{type(error).__name__}",
            }

        stdout = str(completed.stdout or "")
        stderr = str(completed.stderr or "")
        payload = self._parse_smoke_payload(stdout)
        expected = json.loads(contract["stdin_json"])
        valid = self._valid_render_receipt(payload, expected)
        if completed.returncode != 0:
            reason = "nonzero_exit"
        elif not valid:
            reason = "invalid_render_receipt"
        else:
            reason = None
        passed = completed.returncode == 0 and valid
        return {
            **base,
            "schema_version": RENDER_RECEIPT_SCHEMA,
            "status": "passed" if passed else "failed",
            "passed": passed,
            "reason": reason,
            "returncode": completed.returncode,
            "receipt": payload,
            "authorization_id": expected["authorization"]["authorization_id"],
            "outputs": [
                str(Path(expected["output_root"]) / item["output_filename"])
                for item in expected["slides"]
            ],
            "stdout_tail": stdout[-2000:],
            "stderr_tail": stderr[-2000:],
        }

    @staticmethod
    def _valid_render_receipt(
        payload: Optional[Mapping[str, Any]], expected: Mapping[str, Any]
    ) -> bool:
        if not isinstance(payload, Mapping):
            return False
        authorization = expected["authorization"]
        exact = {
            "schema_version": RENDER_RECEIPT_SCHEMA,
            "status": "render_completed_pending_visual_qa",
            "render_request_id": expected["render_request_id"],
            "candidate_id": expected["candidate_id"],
            "mode": expected["mode"],
            "output_set_id": expected["output_set_id"],
            "controller_state_hash": authorization["controller_state_hash"],
            "batch_hash": authorization["batch_hash"],
            "hard_rule_hash": authorization["hard_rule_hash"],
            "local_media_receipt_hashes": expected["local_media_receipt_hashes"],
            "canvas_profile_hash": expected["canvas_profile_hash"],
            "safe_previews": expected["canvas_profile"]["safe_previews"],
            "output_root": expected["output_root"],
            "invoked_engines": ["satori", "resvg"],
            "capability_only_engines": ["fabric", "motion_canvas"],
            "requires_independent_visual_qa": True,
            "visual_preservation_verified": False,
        }
        if any(payload.get(field) != value for field, value in exact.items()):
            return False
        count = len(expected["slides"])
        if payload.get("expected_slide_count") != count or payload.get("rendered_slide_count") != count:
            return False
        hashes = payload.get("output_hashes")
        if not isinstance(hashes, Mapping) or set(hashes) != {str(item["page"]) for item in expected["slides"]}:
            return False
        if any(not isinstance(value, str) or not _SHA256.fullmatch(value.lower()) for value in hashes.values()):
            return False
        labels = payload.get("media_labels")
        expected_labels = [
            {
                "page": item["page"],
                "media_classification": item["media_classification"],
                "display_label": item["display_label"],
            }
            for item in expected["slides"]
        ]
        return labels == expected_labels


def probe_cardnews_renderer(
    tool_root: Optional[str | Path] = None,
    *,
    node_executable: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Convenience filesystem-only capability probe."""

    return CardNewsRendererRuntime(
        tool_root,
        node_executable=node_executable,
    ).probe()
