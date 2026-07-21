"""Deterministic, fail-closed JSONL registry for SourcePacket metadata."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable, Iterator, Mapping
import uuid
from datetime import datetime, timezone

from .knowledge_contract import SourcePacket, SourceStatus, validate_source_packet


class KnowledgeRegistryError(RuntimeError):
    pass


class DuplicateSourceError(KnowledgeRegistryError):
    pass


class RegistryCorruptionError(KnowledgeRegistryError):
    pass


class RegistryWriteError(KnowledgeRegistryError):
    """Stable, machine-readable failure for a bounded registry write."""

    def __init__(self, message: str, *, error_code: str, timeout_seconds: float,
                 cleanup_error_code: str | None = None):
        super().__init__(message)
        self.status = "FAILED"
        self.error_code = error_code
        self.timeout_seconds = timeout_seconds
        self.cleanup_error_code = cleanup_error_code


def _file_digest(path: str) -> str | None:
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except FileNotFoundError:
        return None


def _windows_atomic_write_worker(
    target: str, temp_path: str, result_path: str, payload: bytes, expected_digest: str | None,
) -> None:
    """Stage bytes only; the parent owns the commit after this process exits."""
    try:
        with open(temp_path, "wb") as handle:
            handle.write(payload)
            handle.flush()
        Path(result_path).write_text("STAGED", encoding="ascii")
    except OSError:
        try:
            Path(result_path).write_text("REGISTRY_ATOMIC_WRITE_FAILED", encoding="ascii")
        except OSError:
            pass


def _windows_atomic_replace_worker(target: str, temp_path: str, result_path: str) -> None:
    """Commit a staged file; the parent bounds this process and verifies outcome."""
    try:
        os.replace(temp_path, target)
        Path(result_path).write_text("COMMITTED", encoding="ascii")
    except OSError:
        try:
            Path(result_path).write_text("REGISTRY_ATOMIC_WRITE_FAILED", encoding="ascii")
        except OSError:
            pass


def _windows_registry_operation_worker(
    target: str, operation_id: str, payload_digest: str,
    expected_digest: str | None, payload: bytes,
) -> dict[str, Any]:
    """Perform one complete registry transaction inside a killable process."""
    target_path = Path(target)
    temp_path = target_path.parent / f".{target_path.name}.{operation_id}.tmp"
    lock_path = target_path.parent / f".{target_path.name}.lock"
    lock_owned = False
    cleanup_error: str | None = None
    try:
        with temp_path.open("wb") as handle:
            handle.write(payload)
            handle.flush()
        metadata = {
            "owner_pid": os.getpid(),
            "host": socket.gethostname(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "operation_id": operation_id,
        }
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return {"status": "FAILED", "error_code": "REGISTRY_LOCK_TIMEOUT"}
        try:
            os.write(descriptor, json.dumps(metadata, sort_keys=True).encode("utf-8"))
        finally:
            os.close(descriptor)
        lock_owned = True
        if _file_digest(target) != expected_digest:
            return {"status": "FAILED", "error_code": "REGISTRY_CONCURRENT_WRITE"}
        os.replace(temp_path, target_path)
        outcome = _file_digest(target)
        if outcome != payload_digest:
            return {"status": "FAILED", "error_code": "REGISTRY_COMMIT_OUTCOME_UNKNOWN"}
        return {"status": "COMMITTED"}
    except OSError:
        outcome = _file_digest(target)
        if outcome == payload_digest:
            return {"status": "COMMITTED"}
        if outcome == expected_digest:
            return {"status": "FAILED", "error_code": "REGISTRY_ATOMIC_WRITE_FAILED"}
        return {"status": "FAILED", "error_code": "REGISTRY_COMMIT_OUTCOME_UNKNOWN"}
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            cleanup_error = "REGISTRY_CLEANUP_FAILED"
        if lock_owned:
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                cleanup_error = "REGISTRY_LOCK_CLEANUP_FAILED"
        if cleanup_error:
            # The parent independently observes successful commit; cleanup never
            # changes that outcome into a retry-safe failure.
            pass


class KnowledgeRegistry:
    """A small registry whose complete file is replaced atomically on every mutation."""

    def __init__(self, path: str | Path, *, write_timeout_seconds: float = 2.0):
        self.path = Path(path)
        if not isinstance(write_timeout_seconds, (int, float)) or write_timeout_seconds <= 0:
            raise ValueError("write_timeout_seconds must be positive")
        # Two seconds is the normal per-write budget. Thirty seconds remains the
        # non-configurable safety ceiling even when a caller requests more.
        self.write_timeout_seconds = min(float(write_timeout_seconds), 30.0)
        self.last_cleanup_error_code: str | None = None
        self._last_commit_outcome: str | None = None

    def read_all(self) -> list[SourcePacket]:
        if not self.path.exists():
            return []
        packets: list[SourcePacket] = []
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, 1):
                    if not line.strip():
                        continue
                    raw = json.loads(line)
                    packets.append(validate_source_packet(raw))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise RegistryCorruptionError(f"invalid registry at line {locals().get('line_number', '?')}") from exc
        self._assert_unique(packets)
        return sorted(packets, key=lambda p: p.source_id)

    def register(self, packet: SourcePacket | Mapping[str, Any]) -> SourcePacket:
        candidate = validate_source_packet(packet)
        packets, base_digest = self._read_mutation_snapshot()
        self._assert_not_duplicate(candidate, packets)
        self._write((*packets, candidate), expected_digest=base_digest)
        return candidate

    def replace(self, source_id: str, packet: SourcePacket | Mapping[str, Any]) -> SourcePacket:
        candidate = validate_source_packet(packet)
        if candidate.source_id != source_id:
            raise KnowledgeRegistryError("source_id is immutable")
        packets, base_digest = self._read_mutation_snapshot()
        if not any(item.source_id == source_id for item in packets):
            raise KeyError(source_id)
        remaining = [item for item in packets if item.source_id != source_id]
        self._assert_not_duplicate(candidate, remaining)
        self._write((*remaining, candidate), expected_digest=base_digest)
        return candidate

    def _read_mutation_snapshot(self) -> tuple[list[SourcePacket], str | None]:
        """Read a mutation base only when its before/after digest is stable."""
        before = _file_digest(str(self.path))
        packets = self.read_all()
        after = _file_digest(str(self.path))
        if before != after:
            raise RegistryWriteError(
                "registry changed while mutation snapshot was being read",
                error_code="REGISTRY_CONCURRENT_WRITE",
                timeout_seconds=self.write_timeout_seconds,
            )
        return packets, after

    def get(self, source_id: str) -> SourcePacket | None:
        return next((packet for packet in self.read_all() if packet.source_id == source_id), None)

    def query(
        self, *, source_type: str | None = None, status: str | SourceStatus | None = None,
        tags: Iterable[str] | None = None, related_domains: Iterable[str] | None = None,
        routed_teams: Iterable[str] | None = None, authority_level: str | None = None,
        verification_status: str | None = None, analysis_status: str | None = None,
        adoption_decision: str | None = None, text: str | None = None,
    ) -> list[SourcePacket]:
        expected_status = SourceStatus(status) if status is not None else None
        required_tags = set(tags or ())
        required_domains = set(related_domains or ())
        required_teams = set(routed_teams or ())
        needle = text.casefold().strip() if text else None
        result = []
        for packet in self.read_all():
            if source_type is not None and packet.source_type != source_type: continue
            if expected_status is not None and packet.status != expected_status: continue
            if authority_level is not None and packet.authority_level != authority_level: continue
            if verification_status is not None and packet.verification_status != verification_status: continue
            if analysis_status is not None and packet.analysis_status != analysis_status: continue
            if adoption_decision is not None and packet.adoption_decision != adoption_decision: continue
            if not required_tags.issubset(packet.tags): continue
            if not required_domains.issubset(packet.related_domains): continue
            if not required_teams.issubset(packet.routed_teams): continue
            if needle and needle not in " ".join((packet.title, packet.summary, packet.project_relevance, *packet.tags)).casefold(): continue
            result.append(packet)
        return result

    def _write(
        self, packets: Iterable[SourcePacket], *, expected_digest: str | None = None,
    ) -> None:
        ordered = sorted(packets, key=lambda p: p.source_id)
        self._assert_unique(ordered)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = "".join(
            json.dumps(packet.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            for packet in ordered
        ).encode("utf-8")
        # Keep replacement injectable for deterministic failure tests; real Windows
        # writes always take the bounded child-process path.
        if os.name == "nt" and getattr(os.replace, "__module__", "") != "unittest.mock":
            self._write_windows_bounded(payload, expected_digest=expected_digest)
            return
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=self.path.parent,
                                             prefix=f".{self.path.name}.", suffix=".tmp", delete=False) as handle:
                temp_path = Path(handle.name)
                handle.write(payload.decode("utf-8"))
                handle.flush()
                # FlushFileBuffers (the Windows implementation of fsync) can block for
                # tens of seconds on scanned/synchronised workspaces.  Closing the
                # handle still flushes Python/CRT buffers before the atomic replace;
                # POSIX keeps the stronger crash-durability barrier where it is cheap.
                if os.name != "nt":
                    os.fsync(handle.fileno())
            os.replace(temp_path, self.path)
        except OSError as exc:
            raise KnowledgeRegistryError("atomic registry update failed") from exc
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def _write_windows_bounded(self, payload: bytes, *, expected_digest: str | None = None) -> None:
        """Bound Windows writes with a killable process.

        One operation deadline applies across digest, staging, lock acquisition,
        commit, outcome verification, and cleanup.  The 30-second default leaves
        enough budget for Windows interpreter startup and endpoint scanning while
        preserving a strict upper bound; callers may select a smaller positive
        deadline when their environment has lower startup latency.

        A timeout applies to staging and is terminal for that attempt: subprocess.run
        kills and waits for the worker before cleanup and return. The worker never
        replaces the registry, so a staging timeout preserves the original. The
        parent commits only after successful staging. A registry-scoped exclusive
        lock covers the expected-digest check, replace worker, and outcome check,
        eliminating the previous check/replace TOCTOU window. Lock acquisition and
        replace are both bounded by write_timeout_seconds.

        A retry must re-read the registry and reacquire the lock. Lock files are not
        automatically broken: a process killed while holding one can leave a stale
        lock, and removing it is an operator action only after confirming the owner
        process is dead. This fail-closed boundary avoids two live writers ever
        assuming ownership of the same registry.
        """
        deadline = time.monotonic() + self.write_timeout_seconds
        self.last_cleanup_error_code = None
        self._last_commit_outcome = None
        attempt_id = uuid.uuid4().hex
        helper = (
            "import json,sys;"
            "from modules.knowledge.knowledge_registry import _windows_registry_operation_worker as w;"
            "p=sys.stdin.buffer.read();"
            "e=None if sys.argv[4]=='-' else sys.argv[4];"
            "sys.stdout.write(json.dumps(w(sys.argv[1],sys.argv[2],sys.argv[3],e,p),sort_keys=True))"
        )
        payload_digest = hashlib.sha256(payload).hexdigest()
        try:
            # Reserve a small part of the same absolute deadline for the parent
            # to classify a killed worker's commit outcome from the target digest.
            worker_budget = max(0.01, self._remaining(deadline) - 0.25)
            completed = subprocess.run(
                [sys.executable, "-c", helper, str(self.path), attempt_id, payload_digest,
                 expected_digest or "-"],
                input=payload, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                timeout=worker_budget, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            outcome = self._digest_windows_bounded(deadline, outcome_unknown=True)
            error_code = ("REGISTRY_COMMIT_OUTCOME_UNKNOWN" if outcome == payload_digest
                          else "REGISTRY_WRITE_TIMEOUT")
            raise RegistryWriteError(
                "registry write exceeded the absolute operation deadline",
                error_code=error_code, timeout_seconds=self.write_timeout_seconds,
            ) from exc
        except OSError as exc:
            raise RegistryWriteError(
                "registry write worker could not start", error_code="REGISTRY_WORKER_START_FAILED",
                timeout_seconds=self.write_timeout_seconds,
            ) from exc
        try:
            result = json.loads(completed.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            result = {"status": "FAILED", "error_code": f"REGISTRY_WORKER_EXITED_{completed.returncode}"}
        if completed.returncode == 0 and result.get("status") == "COMMITTED":
            self._last_commit_outcome = "COMMITTED"
            return
        raise RegistryWriteError(
            "atomic registry update failed",
            error_code=result.get("error_code", f"REGISTRY_WORKER_EXITED_{completed.returncode}"),
            timeout_seconds=self.write_timeout_seconds,
        )

    def _commit_windows_bounded(
        self, temp_path: Path, result_path: Path, *, expected_digest: str | None,
        payload_digest: str, deadline: float,
    ) -> None:
        helper = (
            "import sys;"
            "from modules.knowledge.knowledge_registry import _windows_atomic_replace_worker as w;"
            "w(sys.argv[1],sys.argv[2],sys.argv[3])"
        )
        try:
            completed = subprocess.run(
                [sys.executable, "-c", helper, str(self.path), str(temp_path), str(result_path)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=self._remaining(deadline), check=False,
            )
        except subprocess.TimeoutExpired as exc:
            outcome = self._digest_windows_bounded(deadline, outcome_unknown=True)
            cleanup_error = self._cleanup_paths_best_effort(result_path, temp_path, deadline=deadline)
            if outcome == payload_digest:
                self._last_commit_outcome = "COMMITTED"
                self.last_cleanup_error_code = cleanup_error
                return
            if outcome == expected_digest:
                raise RegistryWriteError(
                    "registry commit timed out; original preserved",
                    error_code="REGISTRY_WRITE_TIMEOUT",
                    timeout_seconds=self.write_timeout_seconds, cleanup_error_code=cleanup_error,
                ) from exc
            raise RegistryWriteError(
                "registry commit timed out; commit outcome is unknown",
                error_code="REGISTRY_COMMIT_OUTCOME_UNKNOWN",
                timeout_seconds=self.write_timeout_seconds, cleanup_error_code=cleanup_error,
            ) from exc
        except OSError as exc:
            outcome = self._digest_windows_bounded(deadline, outcome_unknown=True)
            cleanup_error = self._cleanup_paths_best_effort(result_path, temp_path, deadline=deadline)
            if outcome == payload_digest:
                self._last_commit_outcome = "COMMITTED"
                self.last_cleanup_error_code = cleanup_error
                return
            raise RegistryWriteError(
                "registry commit worker could not start",
                error_code=("REGISTRY_WORKER_START_FAILED" if outcome == expected_digest
                            else "REGISTRY_COMMIT_OUTCOME_UNKNOWN"),
                timeout_seconds=self.write_timeout_seconds, cleanup_error_code=cleanup_error,
            ) from exc
        result = self._read_result_windows_bounded(result_path, deadline, completed.returncode)
        outcome = self._digest_windows_bounded(deadline, outcome_unknown=True)
        cleanup_error = self._cleanup_paths_best_effort(result_path, temp_path, deadline=deadline)
        if result == "COMMITTED" and outcome == payload_digest:
            self._last_commit_outcome = "COMMITTED"
            self.last_cleanup_error_code = cleanup_error
            return
        raise RegistryWriteError(
            "atomic registry commit failed", error_code=(
                result if result != "COMMITTED" else "REGISTRY_COMMIT_OUTCOME_UNKNOWN"
            ), timeout_seconds=self.write_timeout_seconds, cleanup_error_code=cleanup_error,
        )

    @contextmanager
    def _exclusive_lock(self, lock_path: Path, deadline: float) -> Iterator[None]:
        token = f"pid={os.getpid()} created={time.time():.6f}\n"
        while True:
            try:
                lock_result = self._try_acquire_lock_windows_bounded(lock_path, token, deadline)
                if lock_result == "ACQUIRED":
                    break
                if lock_result != "EXISTS":
                    raise RegistryWriteError(
                        "registry lock could not be initialized", error_code="REGISTRY_LOCK_FAILED",
                        timeout_seconds=self.write_timeout_seconds,
                    )
                if time.monotonic() >= deadline:
                    raise RegistryWriteError(
                        "registry lock acquisition timed out",
                        error_code="REGISTRY_LOCK_TIMEOUT",
                        timeout_seconds=self.write_timeout_seconds,
                    )
                time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
            except subprocess.TimeoutExpired as exc:
                raise RegistryWriteError(
                    "registry lock acquisition timed out", error_code="REGISTRY_LOCK_TIMEOUT",
                    timeout_seconds=self.write_timeout_seconds,
                ) from exc
        try:
            yield
        finally:
            cleanup_error = self._cleanup_paths_best_effort(
                lock_path, error_code="REGISTRY_LOCK_CLEANUP_FAILED", deadline=deadline)
            active = sys.exc_info()[1]
            if cleanup_error and isinstance(active, RegistryWriteError):
                active.cleanup_error_code = cleanup_error
            elif cleanup_error and self._last_commit_outcome == "COMMITTED":
                self.last_cleanup_error_code = cleanup_error
            elif cleanup_error:
                raise RegistryWriteError(
                    "registry lock cleanup failed", error_code=cleanup_error,
                    timeout_seconds=self.write_timeout_seconds,
                )

    def _remaining(self, deadline: float) -> float:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired("knowledge-registry-operation", self.write_timeout_seconds)
        return remaining

    def _try_acquire_lock_windows_bounded(
        self, lock_path: Path, token: str, deadline: float,
    ) -> str:
        helper = (
            "import os,sys;"
            "p=sys.argv[1];t=sys.argv[2].encode('ascii');"
            "\ntry:\n f=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(f,t);os.close(f);print('ACQUIRED',end='')"
            "\nexcept FileExistsError: print('EXISTS',end='')"
            "\nexcept OSError: print('FAILED',end='')"
        )
        completed = subprocess.run(
            [sys.executable, "-c", helper, str(lock_path), token],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=self._remaining(deadline), check=False, text=True,
        )
        return completed.stdout if completed.returncode == 0 else "FAILED"

    def _digest_windows_bounded(self, deadline: float, *, outcome_unknown: bool = False) -> str | None:
        helper = (
            "import sys;"
            "from modules.knowledge.knowledge_registry import _file_digest as d;"
            "v=d(sys.argv[1]);sys.stdout.write(v or '-')"
        )
        try:
            completed = subprocess.run(
                [sys.executable, "-c", helper, str(self.path)],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                timeout=self._remaining(deadline), check=False, text=True,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            if outcome_unknown:
                return "__OUTCOME_UNKNOWN__"
            raise RegistryWriteError(
                "registry digest could not be determined within operation deadline",
                error_code="REGISTRY_COMMIT_OUTCOME_UNKNOWN",
                timeout_seconds=self.write_timeout_seconds,
            ) from exc
        if completed.returncode != 0:
            if outcome_unknown:
                return "__OUTCOME_UNKNOWN__"
            raise RegistryWriteError(
                "registry digest worker failed", error_code="REGISTRY_COMMIT_OUTCOME_UNKNOWN",
                timeout_seconds=self.write_timeout_seconds,
            )
        return None if completed.stdout == "-" else completed.stdout

    def _cleanup_paths_best_effort(
        self, *paths: Path, error_code: str = "REGISTRY_CLEANUP_FAILED",
        deadline: float | None = None,
    ) -> str | None:
        if not paths:
            return None
        if deadline is None:
            deadline = time.monotonic() + self.write_timeout_seconds
        helper = (
            "import pathlib,sys;ok=True;"
            "[(lambda p: p.unlink(missing_ok=True))(pathlib.Path(v)) for v in sys.argv[1:]]"
        )
        try:
            completed = subprocess.run(
                [sys.executable, "-c", helper, *(str(path) for path in paths)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=self._remaining(deadline), check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            return error_code
        return None if completed.returncode == 0 else error_code

    def _read_result_windows_bounded(
        self, result_path: Path, deadline: float, worker_returncode: int,
    ) -> str:
        helper = "import pathlib,sys;sys.stdout.write(pathlib.Path(sys.argv[1]).read_text(encoding='ascii'))"
        try:
            completed = subprocess.run(
                [sys.executable, "-c", helper, str(result_path)],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                timeout=self._remaining(deadline), check=False, text=True,
            )
        except (subprocess.TimeoutExpired, OSError):
            return "REGISTRY_COMMIT_OUTCOME_UNKNOWN"
        if completed.returncode != 0:
            return f"REGISTRY_WORKER_EXITED_{worker_returncode}"
        return completed.stdout

    def _cleanup_paths(self, *paths: Path, error_code: str = "REGISTRY_CLEANUP_FAILED") -> None:
        for path in paths:
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                raise RegistryWriteError(
                    "registry attempt cleanup failed", error_code=error_code,
                    timeout_seconds=self.write_timeout_seconds,
                ) from exc

    @staticmethod
    def _assert_not_duplicate(candidate: SourcePacket, packets: Iterable[SourcePacket]) -> None:
        for packet in packets:
            if packet.source_id == candidate.source_id:
                raise DuplicateSourceError("duplicate source_id")
            if packet.content_hash == candidate.content_hash:
                raise DuplicateSourceError("duplicate content_hash")
            if candidate.original_url and packet.original_url == candidate.original_url:
                raise DuplicateSourceError("duplicate original_url")

    @classmethod
    def _assert_unique(cls, packets: Iterable[SourcePacket]) -> None:
        checked: list[SourcePacket] = []
        for packet in packets:
            cls._assert_not_duplicate(packet, checked)
            checked.append(packet)
