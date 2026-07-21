import json
import hashlib
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional


class CommerceStorageError(Exception):
    """Safe, structured storage failure that never contains filesystem details."""

    def __init__(self, code: str, cleanup_failed: bool = False):
        super().__init__(code)
        self.code = code
        self.cleanup_failed = cleanup_failed


class CommerceStorage:
    """Atomic, injectable persistence boundary for Commerce artifacts."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir or "storage/commerce")

    def save(self, result: Dict[str, Any]) -> Dict[str, str]:
        request_id = self._safe_request_id(result.get("request_id"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        target = self.output_dir / request_id
        if target.exists():
            raise CommerceStorageError("request_id_conflict")
        try:
            temp = Path(tempfile.mkdtemp(prefix=f".{request_id}-", dir=str(self.output_dir)))
        except Exception as error:
            raise CommerceStorageError("temporary_directory_create_failed") from error
        try:
            packages = result.get("platform_packages", {})
            paths = {
                "result": target / "commerce_result.json",
                "smartstore": target / "smartstore_package.txt",
                "coupang": target / "coupang_package.txt",
            }
            written_paths = {
                "result": str(paths["result"]),
                **{platform: str(paths[platform]) for platform in ("smartstore", "coupang")
                   if platform in packages},
            }
            # Persist the final paths, not staging paths, so the JSON and returned
            # runtime object describe the exact same atomic result.
            result["output_paths"] = list(written_paths.values())
            self._write_json(temp / "commerce_result.json", result)
            for platform in ("smartstore", "coupang"):
                if platform in packages:
                    self._write_text(
                        temp / f"{platform}_package.txt",
                        self._package_text(packages[platform]),
                    )
            os.replace(temp, target)
            return written_paths
        except Exception as error:
            cleanup_failed = False
            if temp.exists():
                try:
                    shutil.rmtree(temp)
                except Exception:
                    cleanup_failed = True
            code = "temporary_cleanup_failed" if cleanup_failed else "atomic_write_failed"
            raise CommerceStorageError(code, cleanup_failed=cleanup_failed) from error

    @staticmethod
    def _package_text(package: Dict[str, Any]) -> str:
        return "\n\n".join((f"product_name: {package.get('product_name', '')}",
                             f"search_keywords: {package.get('search_keywords', '')}",
                             f"options: {json.dumps(package.get('options', []), ensure_ascii=False)}",
                             str(package.get("detail_description", "")),
                             f"notice_information: {json.dumps(package.get('notice_information', {}), ensure_ascii=False)}"))

    @staticmethod
    def _safe_request_id(value: Any) -> str:
        raw = str(value or "commerce_request").strip()
        ordinary = bool(re.fullmatch(r"[A-Za-z0-9._-]{1,80}", raw))
        secret_like = bool(re.search(
            r"(?i)(?:secret|token|password|passwd|api[_-]?key|authorization|bearer|sk-(?:proj-)?)[=:._-]*[A-Za-z0-9_-]+",
            raw,
        ))
        if ordinary and not secret_like and raw not in {".", ".."}:
            return raw
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
        return f"commerce_{digest}"

    normalize_request_id = _safe_request_id

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        CommerceStorage._write_text(
            path,
            json.dumps(value, ensure_ascii=False, indent=2),
        )

    @staticmethod
    def _write_text(path: Path, value: str) -> None:
        """Write a complete staging file and make its contents durable."""
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
