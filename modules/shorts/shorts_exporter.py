import hashlib
import json
import shutil
import stat
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ShortsExporter:
    """Export a Phase 1 Shorts plan as an offline manual-editing package."""

    PACKAGE_VERSION = "2a.1"
    REQUIRED_CONTRACTS = (
        "shorts_brief_result",
        "shorts_script_result",
        "shorts_scene_plan_result",
        "shorts_asset_plan_result",
        "shorts_caption_result",
        "shorts_audio_plan_result",
        "shorts_render_plan_result",
        "shorts_qa_result",
        "shorts_publish_prep_result",
    )
    ALLOWED_COPYRIGHT = {
        "owned",
        "licensed",
        "public_domain",
        "official_reuse_allowed",
        "user_supplied_with_permission",
    }
    SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".webm", ".png", ".jpg", ".jpeg", ".webp"}
    FILES = {
        "source_contracts": "source_contracts.json",
        "editing_package": "editing_package.json",
        "timeline_manifest": "timeline_manifest.json",
        "captions_srt": "captions.srt",
        "asset_validation": "asset_validation.json",
        "manual_checklist": "manual_checklist.json",
    }
    CHECKLIST = (
        "Confirm every scene asset, topic relevance, and usage rights",
        "Record or approve voice",
        "Select licensed music",
        "Verify caption timing against the edited video",
        "Watch the complete 1080x1920 final video",
        "Confirm likeness, copyright, and AI disclosure",
        "Review account, caption, and hashtags before manual upload",
    )

    SECRET_KEY_PARTS = ("api_key", "apikey", "token", "secret", "password", "authorization", "credential")

    def __init__(self, export_root: Optional[Path] = None, asset_root: Optional[Path] = None):
        self.export_root = Path(export_root) if export_root is not None else Path("storage/shorts/exports")
        self.asset_root = Path(asset_root) if asset_root is not None else self.export_root.parent

    def run(
        self,
        shorts_result: Any,
        user_assets: Optional[List[Dict[str, Any]]] = None,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        if not isinstance(shorts_result, dict) or not any(
            isinstance(shorts_result.get(key), dict) for key in self.REQUIRED_CONTRACTS
        ):
            return self._fallback("No valid Phase 1 Shorts contracts were provided.")

        try:
            source_contracts = self._redact_secrets({
                key: shorts_result.get(key) if isinstance(shorts_result.get(key), dict) else {}
                for key in self.REQUIRED_CONTRACTS
            })
            missing = [key for key, value in source_contracts.items() if not value]
            duplicate_scene_ids = self._duplicate_scene_ids(source_contracts)
            if duplicate_scene_ids:
                return self._fallback(
                    "Duplicate scene IDs are not allowed.",
                    blocker_code="DUPLICATE_SCENE_ID",
                )
            if self._duplicate_asset_scene_ids(user_assets):
                return self._fallback(
                    "Duplicate user asset scene IDs are not allowed.",
                    blocker_code="DUPLICATE_ASSET_SCENE_ID",
                )
            package_id = self._package_id(source_contracts, user_assets)
        except Exception:
            return self._fallback("Shorts export preflight failed.", blocker_code="PREFLIGHT_FAILED")
        package_dir = self.export_root / package_id

        if package_dir.is_symlink():
            return self._fallback("Export package path must not be a symlink.", package_id, blocker_code="PACKAGE_SYMLINK")
        if package_dir.exists() and not package_dir.is_dir():
            return self._fallback("Export package path is occupied by a non-directory.", package_id, blocker_code="PACKAGE_PATH_COLLISION")
        if package_dir.exists() and not overwrite:
            return self._fallback(
                "Export package already exists and overwrite is disabled.",
                package_id=package_id,
                blocker_code="OVERWRITE_DISABLED",
            )

        warnings = [f"Missing or invalid contract: {key}" for key in missing]
        staging_dir: Optional[Path] = None
        backup_dir: Optional[Path] = None
        try:
            self.export_root.mkdir(parents=True, exist_ok=True)
            staging_dir = Path(
                tempfile.mkdtemp(prefix=f".{package_id}.staging-", dir=self.export_root)
            )
            (staging_dir / "assets").mkdir()
            (staging_dir / "licenses").mkdir()

            cues, cue_warnings = self._build_cues(source_contracts)
            warnings.extend(cue_warnings)
            timeline, timeline_warnings = self._build_timeline(source_contracts, cues)
            warnings.extend(timeline_warnings)
            srt = self._build_srt(cues)
            asset_validation, asset_warnings, license_items = self._validate_assets(
                timeline["scenes"], user_assets, staging_dir
            )
            warnings.extend(asset_warnings)
            self._attach_assets(timeline, asset_validation)

            if asset_validation["fallback_used"]:
                warnings.append("One or more scenes require a validated user asset.")
            timeline["warnings"] = list(dict.fromkeys(warnings))

            checklist = self._manual_checklist(asset_validation)
            editing_package = self._editing_package(source_contracts, package_id, timeline)
            self._write_json(staging_dir / self.FILES["source_contracts"], source_contracts)
            self._write_json(staging_dir / self.FILES["editing_package"], editing_package)
            self._write_json(staging_dir / self.FILES["timeline_manifest"], timeline)
            (staging_dir / self.FILES["captions_srt"]).write_text(srt, encoding="utf-8")
            self._write_json(staging_dir / self.FILES["asset_validation"], asset_validation)
            self._write_json(staging_dir / self.FILES["manual_checklist"], checklist)
            self._write_json(staging_dir / "licenses" / "README.json", {"items": license_items})
            self._verify_staging(staging_dir)

            if package_dir.exists():
                backup_dir = self.export_root / f".{package_id}.backup-{uuid.uuid4().hex}"
                package_dir.replace(backup_dir)
            try:
                staging_dir.replace(package_dir)
                staging_dir = None
            except Exception:
                if backup_dir is not None and backup_dir.exists() and not package_dir.exists():
                    backup_dir.replace(package_dir)
                    backup_dir = None
                raise
            if backup_dir is not None:
                try:
                    self._remove_internal_tree(backup_dir)
                    backup_dir = None
                except Exception:
                    try:
                        self._remove_final_tree(package_dir, package_id)
                        backup_dir.replace(package_dir)
                        backup_dir = None
                    except Exception:
                        raise RuntimeError("atomic_restore_failed")
                    raise RuntimeError("backup_cleanup_failed")
        except Exception as error:
            blockers = [{"code": "EXPORT_FAILED", "stage": "staging_or_publish", "retryable": True}]
            if str(error) == "atomic_restore_failed":
                blockers.append({"code": "ATOMIC_RESTORE_FAILED", "stage": "overwrite", "retryable": False})
            elif str(error) == "backup_cleanup_failed":
                blockers.append({"code": "BACKUP_CLEANUP_FAILED", "stage": "overwrite", "retryable": True})
            if staging_dir is not None and staging_dir.exists():
                try:
                    self._remove_internal_tree(staging_dir)
                except Exception:
                    blockers.append({"code": "STAGING_CLEANUP_FAILED", "stage": "cleanup", "retryable": True})
            if backup_dir is not None and backup_dir.exists() and not package_dir.exists():
                try:
                    backup_dir.replace(package_dir)
                except Exception:
                    blockers.append({"code": "BACKUP_RESTORE_FAILED", "stage": "overwrite", "retryable": False})
            return self._fallback(
                "Editing package export failed.",
                package_id=package_id,
                blockers=blockers,
            )

        partial = bool(warnings)
        return {
            "module": "ShortsEditingPackageExporter",
            "status": "shorts_editing_package_partial" if partial else "shorts_editing_package_created",
            "package_version": self.PACKAGE_VERSION,
            "package_id": package_id,
            "export_root": package_id,
            "files": dict(self.FILES),
            "rendered_video_path": None,
            "rendered": False,
            "published": False,
            "external_calls_attempted": False,
            "manual_action_required": True,
            "fallback_used": partial,
            "reason": "; ".join(dict.fromkeys(warnings)),
            "blockers": [],
        }

    def _package_id(
        self, contracts: Dict[str, Dict[str, Any]], user_assets: Optional[List[Dict[str, Any]]]
    ) -> str:
        scene_result = contracts["shorts_scene_plan_result"]
        caption_result = contracts["shorts_caption_result"]
        canonical = {
            "brief": contracts["shorts_brief_result"],
            "script": contracts["shorts_script_result"],
            "scenes": scene_result.get("scenes", []),
            "captions": self._canonical_captions(caption_result.get("captions", [])),
            "assets": self._canonical_asset_identities(user_assets),
        }
        encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24]
        return f"shorts-{digest}"

    def _build_timeline(
        self, contracts: Dict[str, Dict[str, Any]], cues: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], List[str]]:
        scene_result = contracts["shorts_scene_plan_result"]
        script_result = contracts["shorts_script_result"]
        raw_scenes = scene_result.get("scenes") if isinstance(scene_result.get("scenes"), list) else []
        warnings: List[str] = []
        scenes = []
        cursor = 0.0

        for order, raw in enumerate(raw_scenes, 1):
            if not isinstance(raw, dict):
                warnings.append(f"Scene {order} is not an object and was skipped.")
                continue
            duration = self._nonnegative_number(raw.get("duration_seconds"))
            if duration <= 0:
                warnings.append(f"Scene {self._safe_label(raw.get('scene_id', order))} has invalid duration and was skipped.")
                continue
            scene_id = raw.get("scene_id", order)
            end = cursor + duration
            scenes.append(
                {
                    "scene_id": scene_id,
                    "order": len(scenes) + 1,
                    "start_seconds": cursor,
                    "end_seconds": end,
                    "duration_seconds": duration,
                    "script_line_ids": raw.get("script_line_ids", [])
                    if isinstance(raw.get("script_line_ids"), list)
                    else [],
                    "visual_type": str(raw.get("visual_type") or "text_over_background"),
                    "transition": str(raw.get("transition") or "cut"),
                    "asset": {
                        "package_path": None,
                        "validation_status": "manual_asset_required",
                        "render_allowed": False,
                    },
                    "caption_ids": [],
                }
            )
            cursor = end

        script_duration = self._nonnegative_number(script_result.get("total_estimated_seconds"))
        if abs(script_duration - cursor) > 0.001:
            warnings.append(
                f"Scene duration total ({cursor}) does not match script duration ({script_duration})."
            )
        for cue in cues:
            for scene in scenes:
                if scene["scene_id"] == cue["scene_id"]:
                    scene["caption_ids"].append(cue["cue_id"])

        if not scenes:
            warnings.append("No valid scenes are available for the timeline.")
        return {
            "schema_version": self.PACKAGE_VERSION,
            "canvas": {
                "width": 1080,
                "height": 1920,
                "pixel_aspect_ratio": "1:1",
                "orientation": "vertical",
            },
            "render_plan": {
                "target": "vertical_1080x1920",
                "width": 1080,
                "height": 1920,
                "renderer": None,
                "manual_editing_required": True,
                "codec_validation": "not_performed_phase_2b_gate",
            },
            "timebase": {"unit": "seconds", "fps": None},
            "duration_seconds": cursor,
            "rendering_supported": False,
            "caption_source": "script_text_only",
            "transcription_used": False,
            "scenes": scenes,
            "warnings": [],
        }, warnings

    def _build_cues(
        self, contracts: Dict[str, Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        caption_result = contracts["shorts_caption_result"]
        script_result = contracts["shorts_script_result"]
        scene_result = contracts["shorts_scene_plan_result"]
        raw_scenes = scene_result.get("scenes") if isinstance(scene_result.get("scenes"), list) else []
        scene_duration = sum(
            self._nonnegative_number(scene.get("duration_seconds"))
            for scene in raw_scenes
            if isinstance(scene, dict)
        )
        duration = scene_duration or self._nonnegative_number(script_result.get("total_estimated_seconds"))
        raw_captions = caption_result.get("captions") if isinstance(caption_result.get("captions"), list) else []
        sortable = [
            (index, item) for index, item in enumerate(raw_captions) if isinstance(item, dict)
        ]
        sortable.sort(
            key=lambda pair: (
                self._nonnegative_number(pair[1].get("start_seconds")),
                str(pair[1].get("scene_id")),
                pair[0],
            )
        )
        cues = []
        warnings = []
        previous_end = 0.0

        for _, item in sortable:
            start = self._nonnegative_number(item.get("start_seconds"))
            end = self._nonnegative_number(item.get("end_seconds"))
            text = " ".join(str(item.get("text") or "").replace("\r", "\n").splitlines()).strip()
            scene_id = item.get("scene_id", "unknown")
            if not text:
                warnings.append(f"Caption for scene {self._safe_label(scene_id)} is empty and was skipped.")
                continue
            if end <= start or start < previous_end or end > duration + 0.001:
                warnings.append(f"Caption for scene {self._safe_label(scene_id)} has invalid timing and was skipped.")
                continue
            cues.append({
                "cue_id": len(cues) + 1,
                "scene_id": scene_id,
                "start_seconds": start,
                "end_seconds": end,
                "text": text,
            })
            previous_end = end
        if not cues:
            warnings.append("No valid captions are available for SRT export.")
        if sortable and abs(previous_end - duration) > 0.001:
            warnings.append(f"Final caption end ({previous_end}) does not match timeline duration ({duration}).")
        return cues, warnings

    def _build_srt(self, cues: List[Dict[str, Any]]) -> str:
        return "\n".join(
            f"{cue['cue_id']}\n{self._srt_time(cue['start_seconds'])} --> "
            f"{self._srt_time(cue['end_seconds'])}\n{cue['text']}\n"
            for cue in cues
        )

    def _validate_assets(
        self,
        scenes: List[Dict[str, Any]],
        user_assets: Optional[List[Dict[str, Any]]],
        package_dir: Path,
    ) -> Tuple[Dict[str, Any], List[str], List[Dict[str, Any]]]:
        supplied = user_assets if isinstance(user_assets, list) else []
        by_scene: Dict[Any, Dict[str, Any]] = {}
        warnings = []
        scene_ids = {scene["scene_id"] for scene in scenes}
        for candidate in supplied:
            if not isinstance(candidate, dict):
                warnings.append("A user asset entry is not an object and was ignored.")
                continue
            scene_id = candidate.get("scene_id")
            if scene_id not in scene_ids:
                warnings.append(f"User asset references unknown scene {self._safe_label(scene_id)} and was ignored.")
                continue
            if scene_id in by_scene:
                warnings.append(f"Duplicate user asset for scene {self._safe_label(scene_id)} was ignored.")
                continue
            by_scene[scene_id] = candidate

        items = []
        licenses = []
        for scene in scenes:
            scene_id = scene["scene_id"]
            candidate = by_scene.get(scene_id, {})
            raw_path = str(candidate.get("file_path") or "")
            source_check = self._inspect_local_file(raw_path)
            source = source_check["path"]
            path_safe = source_check["contained"]
            exists = source_check["exists"]
            is_file = source_check["regular_file"]
            extension = source.suffix.lower() if source else ""
            supported = extension in self.SUPPORTED_EXTENSIONS
            magic_valid = bool(source_check["approved_for_read"] and source and self._valid_magic(source, extension))
            topic_relevant = candidate.get("topic_relevant") if candidate else None
            copyright_status = str(candidate.get("copyright_status") or "unknown")
            license_ref = str(candidate.get("license_reference") or "").strip()
            provided_by = str(candidate.get("provided_by") or "")
            provided_by_ok = provided_by == "user"
            license_check = self._inspect_local_file(license_ref)
            license_path = license_check["path"]
            license_exists = license_check["approved_for_read"]
            license_ok = copyright_status != "licensed" or license_exists
            render_allowed = bool(
                source_check["approved_for_read"]
                and supported
                and magic_valid
                and topic_relevant is True
                and copyright_status in self.ALLOWED_COPYRIGHT
                and license_ok
                and provided_by_ok
            )
            item_warnings = []
            package_path = None
            validation_status = "validated" if render_allowed else "manual_asset_required"

            if not candidate:
                item_warnings.append("No user-provided asset")
            if candidate and not source_check["contained"]:
                item_warnings.append("Asset path is outside the allowed asset root")
            if candidate and source_check["symlink"]:
                item_warnings.append("Asset symlinks are not allowed")
            if candidate and not is_file:
                item_warnings.append("Asset file does not exist or is not a regular file")
            if candidate and not supported:
                item_warnings.append("Unsupported asset extension")
            if candidate and supported and not magic_valid:
                item_warnings.append("Asset content signature does not match its extension")
            if candidate and topic_relevant is not True:
                item_warnings.append("Topic relevance is not approved")
            if candidate and copyright_status not in self.ALLOWED_COPYRIGHT:
                item_warnings.append("Copyright status is not approved")
            if candidate and not license_ok:
                item_warnings.append("Licensed asset requires an existing license evidence file")
            if candidate and copyright_status == "licensed" and not license_check["contained"]:
                item_warnings.append("License evidence is outside the allowed asset root")
            if candidate and copyright_status == "licensed" and license_check["symlink"]:
                item_warnings.append("License evidence symlinks are not allowed")
            if candidate and not provided_by_ok:
                item_warnings.append("provided_by must be 'user'")

            if render_allowed and source:
                destination = package_dir / "assets" / f"scene-{scene['order']:03d}{extension}"
                source_hash = self._file_sha256(source)
                try:
                    shutil.copy2(source, destination)
                    if self._file_sha256(destination) != source_hash:
                        raise OSError("copy_verification_failed")
                    package_path = destination.relative_to(package_dir).as_posix()
                    licenses.append(
                        {
                            "scene_id": scene_id,
                            "package_path": package_path,
                            "copyright_status": copyright_status,
                            "license_reference": license_check["safe_reference"],
                            "license_evidence_exists": license_exists,
                            "license_evidence_sha256": self._file_sha256(license_path)
                            if license_exists and license_path
                            else None,
                            "provided_by": provided_by,
                        }
                    )
                except Exception:
                    try:
                        destination.unlink(missing_ok=True)
                    except OSError:
                        pass
                    render_allowed = False
                    validation_status = "asset_copy_failed"
                    package_path = None
                    item_warnings.append("Asset copy failed")

            items.append(
                {
                    "scene_id": scene_id,
                    "source_path": source_check["safe_reference"],
                    "package_path": package_path,
                    "exists": exists,
                    "is_file": is_file,
                    "supported_extension": supported,
                    "magic_valid": magic_valid,
                    "validation_depth": "magic_header_only",
                    "codec_validation": "not_performed_phase_2b_gate"
                    if extension in {".mp4", ".mov", ".webm"}
                    else "not_applicable",
                    "topic_relevant": topic_relevant,
                    "copyright_status": copyright_status,
                    "license_reference_present": bool(license_ref),
                    "license_evidence_exists": license_exists,
                    "provided_by": provided_by or None,
                    "provided_by_valid": provided_by_ok,
                    "render_allowed": render_allowed,
                    "validation_status": validation_status,
                    "warnings": item_warnings,
                }
            )

        manual_count = sum(not item["render_allowed"] for item in items)
        return {
            "status": "asset_validation_completed",
            "all_assets_ready": bool(items) and manual_count == 0,
            "manual_asset_required_count": manual_count,
            "items": items,
            "fallback_used": manual_count > 0,
            "reason": "One or more scenes require a validated user asset." if manual_count else "",
        }, warnings, licenses

    def _canonical_asset_identities(
        self, user_assets: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        identities = []
        for candidate in user_assets if isinstance(user_assets, list) else []:
            if not isinstance(candidate, dict):
                identities.append({"invalid_type": type(candidate).__name__})
                continue
            source_text = str(candidate.get("file_path") or "")
            license_text = str(candidate.get("license_reference") or "")
            source_check = self._inspect_local_file(source_text)
            license_check = self._inspect_local_file(license_text)
            source = source_check["path"] if source_check["approved_for_read"] else None
            license_path = license_check["path"] if license_check["approved_for_read"] else None
            asset_identity = self._safe_file_identity(source)
            license_identity = self._safe_file_identity(license_path)
            identities.append({
                "scene_id": candidate.get("scene_id"),
                "asset_type": candidate.get("asset_type"),
                "extension": source.suffix.lower() if source else "",
                "asset_sha256": asset_identity["sha256"],
                "asset_size": asset_identity["size"],
                "topic_relevant": candidate.get("topic_relevant"),
                "copyright_status": candidate.get("copyright_status"),
                "provided_by": candidate.get("provided_by"),
                "license_evidence_sha256": license_identity["sha256"],
            })
        return sorted(
            identities,
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, default=str),
        )

    def _inspect_local_file(self, raw_value: str) -> Dict[str, Any]:
        result = {
            "path": None,
            "safe_reference": None,
            "exists": False,
            "regular_file": False,
            "contained": False,
            "symlink": False,
            "approved_for_read": False,
        }
        if not raw_value:
            return result
        try:
            supplied = Path(raw_value).expanduser()
            if ".." in supplied.parts:
                return result
            root_lexical = self.asset_root.absolute()
            if root_lexical.is_symlink():
                result["symlink"] = True
                return result
            candidate = supplied if supplied.is_absolute() else root_lexical / supplied
            candidate_lexical = candidate.absolute()
            if not candidate_lexical.is_relative_to(root_lexical):
                return result
            relative = candidate_lexical.relative_to(root_lexical)
            cursor = root_lexical
            for part in relative.parts:
                cursor = cursor / part
                if cursor.is_symlink():
                    result["symlink"] = True
                    return result
            file_stat = candidate_lexical.lstat()
            result["exists"] = True
            if not stat.S_ISREG(file_stat.st_mode):
                return result
            root_resolved = self.asset_root.resolve(strict=True)
            resolved = candidate_lexical.resolve(strict=True)
            export_resolved = self.export_root.resolve(strict=False)
            if not resolved.is_relative_to(root_resolved) or resolved.is_relative_to(export_resolved):
                return result
            result.update({
                "path": resolved,
                "safe_reference": resolved.relative_to(root_resolved).as_posix(),
                "regular_file": True,
                "contained": True,
                "approved_for_read": True,
            })
        except (OSError, RuntimeError, ValueError):
            return result
        return result

    @staticmethod
    def _canonical_captions(value: Any) -> List[Any]:
        captions = value if isinstance(value, list) else []
        return sorted(
            captions,
            key=lambda item: (
                str(item.get("scene_id")) if isinstance(item, dict) else "",
                str(item.get("start_seconds")) if isinstance(item, dict) else "",
                str(item.get("end_seconds")) if isinstance(item, dict) else "",
                str(item.get("text")) if isinstance(item, dict) else str(item),
            ),
        )

    @staticmethod
    def _duplicate_asset_scene_ids(user_assets: Optional[List[Dict[str, Any]]]) -> List[Any]:
        seen = set()
        duplicates = []
        for candidate in user_assets if isinstance(user_assets, list) else []:
            if not isinstance(candidate, dict):
                continue
            scene_id = candidate.get("scene_id")
            marker = json.dumps(scene_id, ensure_ascii=False, sort_keys=True, default=str)
            if marker in seen and scene_id not in duplicates:
                duplicates.append(scene_id)
            seen.add(marker)
        return duplicates

    def _redact_secrets(self, value: Any, seen: Optional[set] = None) -> Any:
        seen = seen or set()
        if isinstance(value, (dict, list)):
            marker = id(value)
            if marker in seen:
                return "[REDACTED_CYCLE]"
            seen.add(marker)
        if isinstance(value, dict):
            redacted = {}
            for key, item in value.items():
                key_text = str(key)
                normalized = key_text.lower().replace("-", "_")
                if any(part in normalized for part in self.SECRET_KEY_PARTS):
                    redacted[key_text] = "[REDACTED]"
                elif "path" in normalized and isinstance(item, str) and Path(item).is_absolute():
                    redacted[key_text] = "[REDACTED_PATH]"
                else:
                    redacted[key_text] = self._redact_secrets(item, seen)
            seen.discard(id(value))
            return redacted
        if isinstance(value, list):
            redacted = [self._redact_secrets(item, seen) for item in value]
            seen.discard(id(value))
            return redacted
        return value

    @staticmethod
    def _safe_label(value: Any) -> str:
        text = str(value)
        if len(text) > 64 or any(character in text for character in ("/", "\\", ":", "\n", "\r")):
            return "invalid"
        return text

    @staticmethod
    def _duplicate_scene_ids(contracts: Dict[str, Dict[str, Any]]) -> List[Any]:
        scene_result = contracts["shorts_scene_plan_result"]
        scenes = scene_result.get("scenes") if isinstance(scene_result.get("scenes"), list) else []
        seen = set()
        duplicates = []
        for scene in scenes:
            if not isinstance(scene, dict):
                continue
            scene_id = scene.get("scene_id")
            marker = json.dumps(scene_id, ensure_ascii=False, sort_keys=True, default=str)
            if marker in seen and scene_id not in duplicates:
                duplicates.append(scene_id)
            seen.add(marker)
        return duplicates

    @staticmethod
    def _valid_magic(path: Path, extension: str) -> bool:
        try:
            with path.open("rb") as source:
                header = source.read(16)
        except OSError:
            return False
        if extension == ".png":
            return header.startswith(b"\x89PNG\r\n\x1a\n")
        if extension in {".jpg", ".jpeg"}:
            return header.startswith(b"\xff\xd8\xff")
        if extension == ".webp":
            return len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP"
        if extension in {".mp4", ".mov"}:
            return len(header) >= 12 and header[4:8] == b"ftyp"
        if extension == ".webm":
            return header.startswith(b"\x1a\x45\xdf\xa3")
        return False

    @staticmethod
    def _file_sha256(path: Optional[Path]) -> Optional[str]:
        if path is None:
            return None
        try:
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest()
        except OSError:
            return None

    @classmethod
    def _safe_file_identity(cls, path: Optional[Path]) -> Dict[str, Any]:
        if path is None:
            return {"sha256": None, "size": None}
        try:
            if not path.is_file():
                return {"sha256": None, "size": None}
            return {"sha256": cls._file_sha256(path), "size": path.stat().st_size}
        except OSError:
            return {"sha256": None, "size": None}

    def _verify_staging(self, staging_dir: Path) -> None:
        required = list(self.FILES.values()) + ["licenses/README.json"]
        for relative in required:
            path = staging_dir / relative
            if not path.is_file():
                raise OSError(f"Staging package is incomplete: {relative}")
        for key in (
            "source_contracts",
            "editing_package",
            "timeline_manifest",
            "asset_validation",
            "manual_checklist",
        ):
            json.loads((staging_dir / self.FILES[key]).read_text(encoding="utf-8"))
        validation = json.loads(
            (staging_dir / self.FILES["asset_validation"]).read_text(encoding="utf-8")
        )
        expected_assets = {
            item["package_path"]
            for item in validation.get("items", [])
            if isinstance(item, dict) and item.get("package_path")
        }
        actual_assets = {
            path.relative_to(staging_dir).as_posix()
            for path in (staging_dir / "assets").iterdir()
            if path.is_file() and not path.is_symlink()
        }
        if actual_assets != expected_assets:
            raise OSError("Staging asset manifest mismatch")

    def _remove_internal_tree(self, path: Path) -> None:
        root = self.export_root.resolve()
        if path.parent.resolve() != root or not path.name.startswith("."):
            raise OSError("Refusing to remove a path outside the exporter staging boundary.")
        shutil.rmtree(path)

    def _remove_final_tree(self, path: Path, package_id: str) -> None:
        root = self.export_root.resolve()
        if path.parent.resolve() != root or path.name != package_id or path.is_symlink():
            raise OSError("Refusing to remove an unsafe final package path.")
        shutil.rmtree(path)

    def _attach_assets(self, timeline: Dict[str, Any], validation: Dict[str, Any]) -> None:
        items = {item["scene_id"]: item for item in validation["items"]}
        for scene in timeline["scenes"]:
            item = items.get(scene["scene_id"], {})
            scene["asset"] = {
                "package_path": item.get("package_path"),
                "validation_status": item.get("validation_status", "manual_asset_required"),
                "render_allowed": bool(item.get("render_allowed")),
            }

    def _editing_package(
        self, contracts: Dict[str, Dict[str, Any]], package_id: str, timeline: Dict[str, Any]
    ) -> Dict[str, Any]:
        brief = contracts["shorts_brief_result"]
        source_ref = brief.get("source_content_ref") if isinstance(brief.get("source_content_ref"), dict) else {}
        return {
            "package_version": self.PACKAGE_VERSION,
            "package_id": package_id,
            "title": str(source_ref.get("title") or (brief.get("topic") or {}).get("title") or "Untitled"),
            "target": {"width": 1080, "height": 1920, "orientation": "vertical"},
            "duration_seconds": timeline["duration_seconds"],
            "scene_count": len(timeline["scenes"]),
            "caption_format": "srt",
            "timeline_manifest": self.FILES["timeline_manifest"],
            "asset_validation": self.FILES["asset_validation"],
            "production_mode": "manual_editing_required",
            "rendered": False,
            "published": False,
        }

    def _manual_checklist(self, validation: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "manual_checklist_created",
            "manual_action_required": True,
            "completed": False,
            "asset_items_pending": validation["manual_asset_required_count"],
            "items": [
                {"check_id": index, "label": label, "completed": False}
                for index, label in enumerate(self.CHECKLIST, 1)
            ],
        }

    def _fallback(
        self,
        reason: str,
        package_id: Optional[str] = None,
        blocker_code: str = "INVALID_INPUT",
        blockers: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        blocker_items = blockers or [
            {"code": blocker_code, "stage": "preflight", "retryable": False}
        ]
        return {
            "module": "ShortsEditingPackageExporter",
            "status": "shorts_editing_package_fallback",
            "package_version": self.PACKAGE_VERSION,
            "package_id": package_id,
            "export_root": package_id,
            "files": {},
            "rendered_video_path": None,
            "rendered": False,
            "published": False,
            "external_calls_attempted": False,
            "manual_action_required": True,
            "fallback_used": True,
            "reason": reason,
            "blockers": blocker_items,
        }

    @staticmethod
    def _nonnegative_number(value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        return number if number >= 0 else 0.0

    @staticmethod
    def _srt_time(seconds: float) -> str:
        milliseconds = round(seconds * 1000)
        hours, remainder = divmod(milliseconds, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        whole_seconds, millis = divmod(remainder, 1000)
        return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{millis:03d}"

    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


ShortsEditingPackageExporter = ShortsExporter
