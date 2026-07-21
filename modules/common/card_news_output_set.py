"""Fail-closed transaction for a complete CardNews output set.

Consumers must resolve artifacts through ``active.json``.  Files adjacent to the
transaction store, including legacy ``latest`` files, are never candidates.
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from PIL import Image

from modules.card_news.canvas_contract import (
    allowed_card_canvas_sizes_label,
    allowed_card_slide_count_label,
    is_allowed_card_canvas_size,
    is_allowed_card_slide_count,
)
from modules.common.external_storage import resolve_external_path


class OutputSetValidationError(ValueError):
    """The proposed set is incomplete or internally inconsistent."""


class CardNewsOutputSetTransaction:
    """Stage, validate, and atomically select one immutable CardNews set."""

    def __init__(
        self,
        repository_root: Path = Path("."),
        output_set_id: Optional[str] = None,
        heavy_store: Optional[Path] = None,
    ):
        self.root = Path(repository_root).resolve()
        self.output_set_id = (output_set_id or uuid.uuid4().hex).strip()
        if not self.output_set_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in self.output_set_id):
            raise OutputSetValidationError("output_set_id must be nonempty and filesystem-safe")
        self.metadata_store = self.root / "storage" / "output_sets" / "card_news"
        storage_config = self.root / "config" / "source_data_storage.json"
        if heavy_store is not None:
            self.store = Path(heavy_store).resolve()
            self.heavy_bucket_root = self.store
        elif storage_config.is_file():
            self.store = resolve_external_path(
                "card_news", "output_sets", config_path=storage_config, create=True
            ).resolve()
            self.heavy_bucket_root = self.store.parent
        else:
            self.store = self.metadata_store
            self.heavy_bucket_root = self.store
        self.staging = self.store / ".staging" / self.output_set_id
        self.committed = self.store / "sets" / self.output_set_id
        self.active_pointer = self.metadata_store / "active.json"
        self.metadata_manifest = (
            self.metadata_store / "sets" / self.output_set_id / "manifest.json"
        )

    def stage(
        self,
        card_news_result: Dict[str, Any],
        quality_result: Dict[str, Any],
        publishing_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Copy referenced PNGs in count order and write the three result JSONs."""
        payloads = [card_news_result, quality_result, publishing_result]
        if not all(isinstance(item, dict) for item in payloads):
            raise OutputSetValidationError("all results must be JSON objects")
        cards = card_news_result.get("cards")
        if not isinstance(cards, list) or not is_allowed_card_slide_count(len(cards)):
            raise OutputSetValidationError(
                f"card count must be within allowed range: {allowed_card_slide_count_label()}"
            )
        if not all(isinstance(card, dict) for card in cards):
            raise OutputSetValidationError("each card must be an object")
        indices = []
        for card in cards:
            index = card.get("index")
            if not isinstance(index, int) or isinstance(index, bool) or index < 1:
                raise OutputSetValidationError("card indexes must be positive integers")
            indices.append(index)
        if len(set(indices)) != len(cards) or sorted(indices) != list(range(1, len(cards) + 1)):
            raise OutputSetValidationError("cards must have unique contiguous indexes starting at 1")
        cards = sorted(cards, key=lambda item: item["index"])
        source_paths = [card.get("card_path") for card in cards]
        resolved = [self._source_path(path) for path in source_paths]
        if len(set(resolved)) != len(cards):
            raise OutputSetValidationError("card paths must be unique")

        self._discard_staging()
        artifacts_dir = self.staging / "cards"
        artifacts_dir.mkdir(parents=True, exist_ok=False)
        staged_paths = []
        try:
            for index, source in enumerate(resolved, 1):
                self._validate_png(source)
                destination = artifacts_dir / f"card_news_{index}.png"
                shutil.copy2(source, destination)
                self._validate_png(destination)
                # Payload identity is the immutable committed location, even while
                # bytes are still isolated in staging before the directory rename.
                staged_paths.append(
                    self._portable_path(self.committed / "cards" / destination.name)
                )

            card_payload = json.loads(json.dumps(card_news_result))
            card_payload["cards"] = json.loads(json.dumps(cards))
            publishing_payload = json.loads(json.dumps(publishing_result))
            quality_payload = json.loads(json.dumps(quality_result))
            path_mapping = {
                str(source): canonical
                for source, canonical in zip(source_paths, staged_paths)
            }
            card_payload = self._rewrite_paths(card_payload, path_mapping)
            publishing_payload = self._rewrite_paths(publishing_payload, path_mapping)
            for payload in (card_payload, quality_payload, publishing_payload):
                payload["output_set_id"] = self.output_set_id
            for card, path in zip(card_payload["cards"], staged_paths):
                card["card_path"] = path
            publishing_payload["card_paths"] = staged_paths

            self._write_json(self.staging / "08_card_news_result.json", card_payload)
            self._write_json(self.staging / "card_news_quality.json", quality_payload)
            self._write_json(self.staging / "09_publishing_result.json", publishing_payload)
            manifest = self._build_manifest(
                staged_paths,
                release_ready=(
                    quality_payload.get("passed") is True
                    and publishing_payload.get("status") == "publishing_ready"
                ),
            )
            self._write_json(self.staging / "manifest.json", manifest)
            self._validate_directory(self.staging)
            return manifest
        except Exception:
            self._discard_staging()
            raise

    def promote(self) -> Dict[str, Any]:
        """Commit a validated directory and atomically switch the active pointer."""
        if self.committed.is_dir():
            manifest = self._validate_directory(self.committed, require_rebound=True)
            active_id = None
            try:
                active_id = json.loads(
                    self.active_pointer.read_text(encoding="utf-8")
                ).get("output_set_id")
            except (OSError, json.JSONDecodeError, AttributeError):
                pass
            try:
                self._write_metadata_manifest(manifest)
                self._write_active_pointer(manifest)
            except Exception:
                if active_id != self.output_set_id:
                    shutil.rmtree(self.committed, ignore_errors=True)
                    shutil.rmtree(self.metadata_manifest.parent, ignore_errors=True)
                raise
            self._discard_staging()
            return manifest
        manifest = self._validate_directory(self.staging)
        self.committed.parent.mkdir(parents=True, exist_ok=True)
        os.replace(self.staging, self.committed)
        try:
            manifest = self._validate_directory(self.committed, require_rebound=True)
            self._write_metadata_manifest(manifest)
            self._write_active_pointer(manifest)
            return manifest
        except Exception:
            shutil.rmtree(self.committed, ignore_errors=True)
            shutil.rmtree(self.metadata_manifest.parent, ignore_errors=True)
            raise

    def rebind_publishing(self, rebind_fn) -> Dict[str, Any]:
        """Bind Publishing and its queue to committed paths before selection."""
        if self.committed.exists():
            raise OutputSetValidationError("committed candidate already exists")
        self._validate_directory(self.staging)
        self.committed.parent.mkdir(parents=True, exist_ok=True)
        os.replace(self.staging, self.committed)
        try:
            publishing_path = self.committed / "09_publishing_result.json"
            publishing = json.loads(publishing_path.read_text(encoding="utf-8"))
            result_path = self.committed / "08_card_news_result.json"
            committed_card_paths = json.loads(result_path.read_text(encoding="utf-8")).get("cards", [])
            if not isinstance(committed_card_paths, list):
                raise OutputSetValidationError("committed card result is malformed")
            committed_count = len(committed_card_paths)
            if not is_allowed_card_slide_count(committed_count):
                raise OutputSetValidationError("committed card count is out of allowed range")
            committed_paths = [
                self._portable_path(
                    self.committed / f"cards/card_news_{index}.png"
                )
                for index in range(1, committed_count + 1)
            ]
            queue_target = self.committed / "cards" / "09_publish_queue.json"
            rebound = rebind_fn(
                publishing,
                committed_paths,
                self.output_set_id,
                queue_target,
            )
            if not isinstance(rebound, dict) or rebound.get("actual_publish") is not False:
                raise OutputSetValidationError("publishing rebind returned an invalid result")
            self._write_json(publishing_path, rebound)

            manifest_path = self.committed / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifacts = manifest.get("artifacts", {})
            if queue_target.is_file():
                artifacts["publish_queue"] = "cards/09_publish_queue.json"
            else:
                artifacts.pop("publish_queue", None)
            manifest["artifacts"] = artifacts
            manifest["release_ready"] = (
                rebound.get("status") == "publishing_ready"
                and rebound.get("package_ready") is True
            )
            manifest["actual_publish"] = False
            self._write_json(manifest_path, manifest)
            return self._validate_directory(self.committed, require_rebound=True)
        except Exception:
            shutil.rmtree(self.committed, ignore_errors=True)
            raise

    @classmethod
    def resolve_active(cls, repository_root: Path = Path(".")) -> Dict[str, Path]:
        """Resolve only the currently selected, fully validated artifact set."""
        root = Path(repository_root).resolve()
        pointer = root / "storage/output_sets/card_news/active.json"
        try:
            data = json.loads(pointer.read_text(encoding="utf-8"))
            output_set_id = data["output_set_id"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
            raise OutputSetValidationError("no valid active output set") from error
        storage_config = root / "config" / "source_data_storage.json"
        heavy_store = None
        if storage_config.is_file():
            heavy_store = resolve_external_path(
                "card_news", "output_sets", config_path=storage_config
            )
        transaction = cls(root, output_set_id, heavy_store=heavy_store)
        manifest = transaction._validate_directory(
            transaction.committed,
            require_rebound=True,
        )
        if manifest != data:
            raise OutputSetValidationError("active pointer does not match committed manifest")
        return {
            name: transaction._artifact_path(relative)
            for name, relative in manifest["artifacts"].items()
        }

    def _source_path(self, value: Any) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise OutputSetValidationError("each card must reference a path")
        candidate = Path(value)
        path = (candidate if candidate.is_absolute() else self.root / candidate).resolve()
        if not self._is_under(path, self.root) and not self._is_under(
            path, self.heavy_bucket_root
        ):
            raise OutputSetValidationError(
                "card path is outside repository and configured heavy storage"
            )
        if not path.is_file():
            raise OutputSetValidationError("referenced card does not exist")
        return path

    @staticmethod
    def _validate_png(path: Path) -> None:
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                if image.format != "PNG" or not is_allowed_card_canvas_size(image.size):
                    raise OutputSetValidationError(
                        f"card must be a PNG with an allowed canvas size: {allowed_card_canvas_sizes_label()}"
                    )
        except (OSError, ValueError) as error:
            if isinstance(error, OutputSetValidationError):
                raise
            raise OutputSetValidationError("card is not a decodable PNG") from error

    def _build_manifest(self, card_paths: Iterable[str], release_ready: bool) -> Dict[str, Any]:
        artifacts = {
            "card_news_result": "08_card_news_result.json",
            "quality": "card_news_quality.json",
            "publishing": "09_publishing_result.json",
        }
        artifacts.update({f"card_{i}": f"cards/card_news_{i}.png" for i in range(1, len(card_paths) + 1)})
        return {
            "schema_version": 1,
            "output_set_id": self.output_set_id,
            "status": "validated",
            "release_ready": release_ready,
            "actual_publish": False,
            "artifacts": artifacts,
            "card_paths": list(card_paths),
        }

    def _validate_directory(
        self,
        directory: Path,
        require_rebound: bool = False,
    ) -> Dict[str, Any]:
        try:
            card = json.loads((directory / "08_card_news_result.json").read_text(encoding="utf-8"))
            quality = json.loads((directory / "card_news_quality.json").read_text(encoding="utf-8"))
            publishing = json.loads((directory / "09_publishing_result.json").read_text(encoding="utf-8"))
            manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise OutputSetValidationError("output set JSON is missing or invalid") from error
        ids = [item.get("output_set_id") for item in (card, quality, publishing, manifest)]
        if ids != [self.output_set_id] * 4:
            raise OutputSetValidationError("output_set_id mismatch")
        if card.get("status") != "card_news_completed":
            raise OutputSetValidationError("required result status did not pass")
        if not isinstance(quality.get("passed"), bool):
            raise OutputSetValidationError("quality passed must be an explicit boolean")
        if publishing.get("status") not in {"publishing_ready", "publishing_blocked"}:
            raise OutputSetValidationError("publishing status is invalid")
        release_ready = quality["passed"] and publishing["status"] == "publishing_ready"
        if manifest.get("release_ready") is not release_ready:
            raise OutputSetValidationError("manifest release readiness mismatch")
        cards = card.get("cards")
        if not isinstance(cards, list) or not is_allowed_card_slide_count(len(cards)):
            raise OutputSetValidationError("card count must be within allowed range")
        card_indexes = [item.get("index") for item in cards]
        if not card_indexes:
            raise OutputSetValidationError("card result is missing indexes")
        if sorted(card_indexes) != list(range(1, len(cards) + 1)):
            raise OutputSetValidationError("card indexes are not contiguous from 1")
        expected = [
            self._portable_path(self.committed / f"cards/card_news_{i}.png")
            for i in range(1, len(cards) + 1)
        ]
        if [item.get("card_path") for item in cards] != expected or publishing.get("card_paths") != expected or manifest.get("card_paths") != expected:
            raise OutputSetValidationError("artifact path identity mismatch")
        operator_package = publishing.get("operator_upload_package")
        if isinstance(operator_package, dict) and operator_package.get("ordered_card_paths") != expected:
            raise OutputSetValidationError("operator package path identity mismatch")
        if self._contains_run_path(publishing):
            raise OutputSetValidationError("publishing payload contains an expired run path")
        required = {"card_news_result", "quality", "publishing"} | {
            f"card_{i}" for i in range(1, len(cards) + 1)
        }
        artifacts = manifest.get("artifacts", {})
        if not isinstance(artifacts, dict):
            raise OutputSetValidationError("manifest artifacts are invalid")
        queue_path_value = publishing.get("publish_queue_path")
        package = publishing.get("operator_upload_package")
        package_queue_path = package.get("publish_queue_path") if isinstance(package, dict) else None
        embedded_queue = publishing.get("publish_queue")
        if require_rebound and queue_path_value:
            expected_queue = (self.committed / "cards/09_publish_queue.json").resolve()
            if (
                Path(queue_path_value).resolve() != expected_queue
                or not expected_queue.is_file()
                or package_queue_path != queue_path_value
                or artifacts.get("publish_queue") != "cards/09_publish_queue.json"
            ):
                raise OutputSetValidationError("publish queue binding is invalid")
            try:
                persisted_queue = json.loads(expected_queue.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise OutputSetValidationError("publish queue is missing or invalid") from error
            if persisted_queue != embedded_queue:
                raise OutputSetValidationError("publish queue bytes do not match embedded queue")
            if (
                persisted_queue.get("output_set_id") != self.output_set_id
                or persisted_queue.get("actual_publish") is not False
                or self._contains_run_path(persisted_queue)
            ):
                raise OutputSetValidationError("publish queue identity is invalid")
            items = persisted_queue.get("items")
            if not isinstance(items, list) or not items or any(
                not isinstance(item, dict)
                or item.get("output_set_id") != self.output_set_id
                or item.get("actual_publish") is not False
                or item.get("card_paths") != expected
                for item in items
            ):
                raise OutputSetValidationError("publish queue items are invalid")
            required.add("publish_queue")
        elif require_rebound:
            if (
                publishing.get("status") != "publishing_blocked"
                or publishing.get("actual_publish") is not False
                or package_queue_path
                or "publish_queue" in artifacts
            ):
                raise OutputSetValidationError("blocked publishing retained a stale queue reference")
        if manifest.get("status") != "validated" or set(artifacts) != required:
            raise OutputSetValidationError("manifest is incomplete")
        for index in range(1, len(cards) + 1):
            self._validate_png(directory / f"cards/card_news_{index}.png")
        return manifest

    @classmethod
    def _rewrite_paths(cls, value: Any, mapping: Dict[str, str]) -> Any:
        if isinstance(value, dict):
            return {key: cls._rewrite_paths(item, mapping) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._rewrite_paths(item, mapping) for item in value]
        if isinstance(value, str):
            return mapping.get(value, value)
        return value

    @classmethod
    def _contains_run_path(cls, value: Any) -> bool:
        if isinstance(value, dict):
            return any(cls._contains_run_path(item) for item in value.values())
        if isinstance(value, list):
            return any(cls._contains_run_path(item) for item in value)
        return isinstance(value, str) and "/.runs/" in value.replace("\\", "/")

    def _write_active_pointer(self, manifest: Dict[str, Any]) -> None:
        self.metadata_store.mkdir(parents=True, exist_ok=True)
        temporary = self.metadata_store / f".active-{self.output_set_id}.tmp"
        self._write_json(temporary, manifest)
        try:
            os.replace(temporary, self.active_pointer)
        finally:
            temporary.unlink(missing_ok=True)

    def _write_metadata_manifest(self, manifest: Dict[str, Any]) -> None:
        """Persist only lightweight selection metadata in repository storage."""
        self._write_json(self.metadata_manifest, manifest)

    def _portable_path(self, path: Path) -> str:
        resolved = path.resolve()
        try:
            return resolved.relative_to(self.root).as_posix()
        except ValueError:
            return resolved.as_posix()

    def _artifact_path(self, value: Any) -> Path:
        path = Path(str(value))
        return path if path.is_absolute() else self.committed / path

    @staticmethod
    def _is_under(path: Path, parent: Path) -> bool:
        try:
            path.relative_to(parent.resolve())
            return True
        except ValueError:
            return False

    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _discard_staging(self) -> None:
        shutil.rmtree(self.staging, ignore_errors=True)
