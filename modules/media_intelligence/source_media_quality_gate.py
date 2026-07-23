"""Fail-closed media relevance and duplicate gate for pre-render selection.

OpenCLIP and OCR outputs are internal quality proxies only.  They do not prove
facts, source support, rights, licensing, performance, or publishing approval.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import math
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence

from PIL import Image

from modules.tool_adapters.openclip_runtime import OpenClipRuntime
from modules.tool_adapters.paddleocr_runtime import extract_korean_text


SCHEMA_VERSION = "source_media_quality_gate.v1"
DEFAULT_DISTRACTOR_LABELS = (
    "unrelated generic stock photo",
    "cute animal or pet",
    "generic abstract background",
    "blank template or empty box",
)
PROXY_BOUNDARY = {
    "classification": "internal_quality_proxy",
    "factual_accuracy_evidence": False,
    "source_support_evidence": False,
    "rights_or_license_evidence": False,
    "publishing_approval": False,
    "automatic_production_approval": False,
}
_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]{2,}")


def _receipt(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        value = value.to_dict()
    elif is_dataclass(value):
        value = asdict(value)
    return dict(value) if isinstance(value, Mapping) else {}


def _tokens(value: Any) -> set[str]:
    return {item.casefold() for item in _TOKEN_RE.findall(str(value or ""))}


def _dhash(path: Path) -> int:
    with Image.open(path) as image:
        pixels = list(
            image.convert("L").resize((9, 8), Image.Resampling.LANCZOS).getdata()
        )
    bits = 0
    for row in range(8):
        offset = row * 9
        for column in range(8):
            bits = (bits << 1) | (
                pixels[offset + column] > pixels[offset + column + 1]
            )
    return bits


def _hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def _labels(
    headline: str,
    body: str,
    bilingual_visual_labels: Mapping[str, Sequence[str]] | Sequence[str] | None,
) -> tuple[list[str], list[str]]:
    relevant: list[str] = []
    distractors = list(DEFAULT_DISTRACTOR_LABELS)
    if isinstance(bilingual_visual_labels, Mapping):
        relevant.extend(
            str(item).strip()
            for item in bilingual_visual_labels.get("relevant", ())
            if str(item).strip()
        )
        supplied_distractors = [
            str(item).strip()
            for item in bilingual_visual_labels.get("distractors", ())
            if str(item).strip()
        ]
        if supplied_distractors:
            distractors = supplied_distractors
    elif isinstance(bilingual_visual_labels, Sequence) and not isinstance(
        bilingual_visual_labels, (str, bytes)
    ):
        relevant.extend(
            str(item).strip() for item in bilingual_visual_labels if str(item).strip()
        )
    if not relevant:
        context = " ".join(part.strip() for part in (headline, body) if part.strip())
        if context:
            relevant.append(context[:300])
    return relevant[:8], distractors[:8]


class SourceMediaQualityGate:
    """Return only candidates with complete tool receipts and relevance support."""

    def __init__(
        self,
        *,
        ocr_extractor: Callable[..., Any] = extract_korean_text,
        openclip: Any | None = None,
        ocr_timeout_seconds: float = 30.0,
        openclip_timeout_seconds: float = 30.0,
        minimum_relevant_score: float = 0.18,
        distractor_margin: float = 0.02,
        duplicate_hamming_threshold: int = 6,
    ) -> None:
        self.ocr_extractor = ocr_extractor
        self.openclip = openclip if openclip is not None else OpenClipRuntime()
        self.ocr_timeout_seconds = ocr_timeout_seconds
        self.openclip_timeout_seconds = openclip_timeout_seconds
        self.minimum_relevant_score = minimum_relevant_score
        self.distractor_margin = distractor_margin
        self.duplicate_hamming_threshold = duplicate_hamming_threshold

    @staticmethod
    def _tool_failure(tool: str, receipt: Mapping[str, Any]) -> str | None:
        status = str(receipt.get("status") or "").casefold()
        reason = str(receipt.get("reason") or "").casefold()
        if "timeout" in status or "timeout" in reason:
            return f"{tool}_timeout"
        if status in {"blocked", "unavailable"} or "not_ready" in reason:
            return f"{tool}_unavailable"
        if tool == "ocr":
            complete = (
                receipt.get("success") is True
                and status == "completed"
                and receipt.get("input_unchanged", True) is True
            )
        else:
            complete = receipt.get("passed") is True and status == "passed"
        return None if complete else f"{tool}_failed"

    @staticmethod
    def _ocr_required(candidate: Mapping[str, Any]) -> bool:
        media_type = str(
            candidate.get("media_type")
            or candidate.get("type")
            or candidate.get("asset_class")
            or ""
        ).casefold()
        role = str(
            candidate.get("role_hint")
            or candidate.get("narrative_role")
            or ""
        ).casefold()
        return any(
            token in f"{media_type} {role}"
            for token in (
                "comment",
                "document",
                "letter",
                "screenshot",
                "text_capture",
                "댓글",
                "문서",
                "편지",
                "캡처",
            )
        )

    def _evaluate_candidate(
        self,
        candidate: Mapping[str, Any],
        *,
        relevant_labels: Sequence[str],
        distractor_labels: Sequence[str],
        context_tokens: set[str],
    ) -> tuple[dict[str, Any], int | None]:
        record = dict(candidate)
        raw_path = str(record.get("local_path") or "").strip()
        path = Path(raw_path).expanduser()
        if not raw_path or not path.is_absolute() or not path.is_file():
            return {
                **record,
                "quality_gate": {
                    "passed": False,
                    "reason_code": "local_image_unavailable",
                    "proxy_boundary": dict(PROXY_BOUNDARY),
                },
            }, None
        try:
            perceptual_hash = _dhash(path)
        except (OSError, ValueError, Image.UnidentifiedImageError):
            return {
                **record,
                "quality_gate": {
                    "passed": False,
                    "reason_code": "local_image_invalid",
                    "proxy_boundary": dict(PROXY_BOUNDARY),
                },
            }, None

        try:
            ocr = _receipt(
                self.ocr_extractor(path, timeout_seconds=self.ocr_timeout_seconds)
            )
        except TimeoutError:
            ocr = {"status": "timed_out", "success": False, "reason": "ocr_timeout"}
        except Exception as exc:
            ocr = {
                "status": "failed",
                "success": False,
                "reason": f"dependency_exception:{type(exc).__name__}",
            }
        ocr_required = self._ocr_required(record)
        ocr_failure = self._tool_failure("ocr", ocr)
        if ocr_failure and ocr_required:
            return {
                **record,
                "quality_gate": {
                    "passed": False,
                    "reason_code": ocr_failure,
                    "ocr_required": True,
                    "ocr": ocr,
                    "proxy_boundary": dict(PROXY_BOUNDARY),
                },
            }, perceptual_hash

        topics = list(relevant_labels) + list(distractor_labels)
        try:
            clip = _receipt(
                self.openclip.score_image_topics(
                    path,
                    topics,
                    timeout_seconds=self.openclip_timeout_seconds,
                )
            )
        except TimeoutError:
            clip = {"status": "timeout", "passed": False, "reason": "score_timeout"}
        except Exception as exc:
            clip = {
                "status": "failed",
                "passed": False,
                "reason": f"dependency_exception:{type(exc).__name__}",
            }
        clip_failure = self._tool_failure("openclip", clip)
        if clip_failure:
            return {
                **record,
                "quality_gate": {
                    "passed": False,
                    "reason_code": clip_failure,
                    "ocr": ocr,
                    "openclip": clip,
                    "proxy_boundary": dict(PROXY_BOUNDARY),
                },
            }, perceptual_hash

        ranked = clip.get("ranked_topics")
        score_by_topic: dict[str, float] = {}
        if isinstance(ranked, Sequence) and not isinstance(ranked, (str, bytes)):
            for item in ranked:
                if not isinstance(item, Mapping):
                    continue
                score = item.get("cosine_similarity")
                if isinstance(score, (int, float)) and math.isfinite(float(score)):
                    score_by_topic[str(item.get("topic") or "")] = float(score)
        relevant_score = max(
            (score_by_topic.get(label, -1.0) for label in relevant_labels), default=-1.0
        )
        distractor_score = max(
            (score_by_topic.get(label, -1.0) for label in distractor_labels), default=-1.0
        )
        if relevant_score < self.minimum_relevant_score:
            reason = "insufficient_visual_relevance"
        elif distractor_score >= relevant_score - self.distractor_margin:
            reason = "distractor_dominant"
        else:
            reason = ""

        ocr_text = str(ocr.get("text") or " ".join(ocr.get("lines") or ())).strip()
        ocr_tokens = _tokens(ocr_text)
        ocr_overlap = sorted(context_tokens & ocr_tokens)
        if (
            not reason
            and ocr_required
            and len("".join(ocr_tokens)) >= 4
            and not ocr_overlap
        ):
            reason = "ocr_context_mismatch"

        return {
            **record,
            "quality_gate": {
                "passed": not reason,
                "reason_code": reason or None,
                "ocr_required": ocr_required,
                "ocr_diagnostic_only": not ocr_required,
                "ocr_failure_ignored": bool(ocr_failure and not ocr_required),
                "perceptual_hash": f"{perceptual_hash:016x}",
                "ocr_context_overlap": ocr_overlap,
                "relevant_score": relevant_score,
                "distractor_score": distractor_score,
                "ocr": ocr,
                "openclip": clip,
                "proxy_boundary": dict(PROXY_BOUNDARY),
            },
        }, perceptual_hash

    def evaluate(
        self,
        candidates: Sequence[Mapping[str, Any]],
        *,
        headline: str,
        body: str,
        bilingual_visual_labels: Mapping[str, Sequence[str]] | Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Evaluate candidates and expose only verified, non-duplicate candidates."""

        if (
            isinstance(candidates, (str, bytes))
            or not isinstance(candidates, Sequence)
            or not str(headline or body).strip()
        ):
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "blocked",
                "reason_code": "quality_gate_input_invalid",
                "passed_candidates": [],
                "rejected_candidates": [],
                "render_allowed": False,
                "proxy_boundary": dict(PROXY_BOUNDARY),
            }
        relevant, distractors = _labels(
            str(headline or ""), str(body or ""), bilingual_visual_labels
        )
        if not relevant:
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "blocked",
                "reason_code": "visual_labels_unavailable",
                "passed_candidates": [],
                "rejected_candidates": [],
                "render_allowed": False,
                "proxy_boundary": dict(PROXY_BOUNDARY),
            }

        context_tokens = _tokens(f"{headline} {body} {' '.join(relevant)}")
        passed: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        accepted_hashes: list[tuple[int, str]] = []
        for index, candidate in enumerate(candidates):
            if not isinstance(candidate, Mapping):
                rejected.append(
                    {
                        "candidate_index": index,
                        "quality_gate": {
                            "passed": False,
                            "reason_code": "candidate_malformed",
                            "proxy_boundary": dict(PROXY_BOUNDARY),
                        },
                    }
                )
                continue
            evaluated, perceptual_hash = self._evaluate_candidate(
                candidate,
                relevant_labels=relevant,
                distractor_labels=distractors,
                context_tokens=context_tokens,
            )
            gate = evaluated["quality_gate"]
            if gate["passed"] and perceptual_hash is not None:
                duplicate = next(
                    (
                        candidate_id
                        for existing, candidate_id in accepted_hashes
                        if _hamming(existing, perceptual_hash)
                        <= self.duplicate_hamming_threshold
                    ),
                    None,
                )
                if duplicate is not None:
                    gate["passed"] = False
                    gate["reason_code"] = "perceptual_duplicate"
                    gate["duplicate_of"] = duplicate
            if gate["passed"]:
                candidate_id = str(
                    evaluated.get("candidate_id")
                    or evaluated.get("asset_id")
                    or f"candidate-{index + 1}"
                )
                accepted_hashes.append((perceptual_hash, candidate_id))
                passed.append(evaluated)
            else:
                rejected.append(evaluated)

        render_allowed = bool(passed)
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "passed" if render_allowed else "blocked",
            "reason_code": None if render_allowed else "no_candidate_passed_quality_gate",
            "passed_candidates": passed,
            "rejected_candidates": rejected,
            "render_allowed": render_allowed,
            "tool_execution_required": True,
            "relevant_visual_labels": relevant,
            "distractor_visual_labels": distractors,
            "proxy_boundary": dict(PROXY_BOUNDARY),
        }


def evaluate_source_media_candidates(
    candidates: Sequence[Mapping[str, Any]],
    *,
    headline: str,
    body: str,
    bilingual_visual_labels: Mapping[str, Sequence[str]] | Sequence[str] | None = None,
    ocr_extractor: Callable[..., Any] = extract_korean_text,
    openclip: Any | None = None,
) -> dict[str, Any]:
    """Functional dependency-injection entry point for production integration."""

    return SourceMediaQualityGate(
        ocr_extractor=ocr_extractor,
        openclip=openclip,
    ).evaluate(
        candidates,
        headline=headline,
        body=body,
        bilingual_visual_labels=bilingual_visual_labels,
    )


__all__ = [
    "DEFAULT_DISTRACTOR_LABELS",
    "PROXY_BOUNDARY",
    "SCHEMA_VERSION",
    "SourceMediaQualityGate",
    "evaluate_source_media_candidates",
]
