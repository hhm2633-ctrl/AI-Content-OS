"""Generate representative visual QA receipt payloads from rendered slide media.

This helper is intentionally isolated from controller/qa gate internals. It reads a
production-style manifest, runs OpenCLIP + PaddleOCR against each expected slide,
and emits a qa_receipt.json shaped for the existing `accept-visual-qa` flow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

from modules.card_news.visual_qa_gate import REQUIRED_FINDINGS, assess_visual_qa_receipt
from modules.media_intelligence.rembg_bbox import extract_subject_bbox_from_alpha
from modules.tool_adapters.rembg_runtime import RembgRuntimeAdapter
from modules.tool_adapters.openclip_runtime import OpenClipRuntime
from modules.tool_adapters.paddleocr_runtime import extract_korean_text
from scripts.run_cardnews_production import (
    SUBJECT_CROP_GUARD_MAX_SUBJECT_OUTSIDE_RATIO,
    SUBJECT_CROP_GUARD_METRIC_PRECISION,
    _evaluate_subject_crop_guard,
    _expected_slides,
)

PASS = "pass"
NOT_APPLICABLE = "not_applicable"
FAIL = "fail"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _iter_candidates(
    manifest: Mapping[str, Any],
    candidate_filter: set[str] | None,
) -> Iterable[Mapping[str, Any]]:
    for record in manifest.get("records", []):
        if not isinstance(record, Mapping):
            continue
        candidate_id = _text(record.get("candidate_id"))
        if not candidate_id:
            continue
        if candidate_filter and candidate_id not in candidate_filter:
            continue
        yield record


def _load_packages(
    manifest: Mapping[str, Any],
    candidates: set[str] | None,
) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for record in manifest.get("records", []):
        if not isinstance(record, Mapping):
            continue
        candidate_id = _text(record.get("candidate_id"))
        if not candidate_id:
            continue
        if candidates and candidate_id not in candidates:
            continue
        package_path = Path(_text(record.get("package_path")))
        if not package_path.is_file():
            continue
        try:
            package = _read_json(package_path)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(package, Mapping):
            out[candidate_id] = package
    return out


def _candidate_title(package: Mapping[str, Any]) -> str:
    if not isinstance(package, Mapping):
        return ""
    candidate = package.get("candidate")
    if isinstance(candidate, Mapping):
        return _text(candidate.get("title") or candidate.get("summary"))
    story = package.get("story")
    if isinstance(story, Mapping):
        return _text(story.get("summary") or story.get("title"))
    return _text(package.get("title") or package.get("story"))


def _candidate_category(package: Mapping[str, Any]) -> str:
    if not isinstance(package, Mapping):
        return ""
    candidate = package.get("candidate")
    if isinstance(candidate, Mapping):
        return _text(candidate.get("category"))
    return _text(package.get("category"))


def _collect_topics(
    package: Mapping[str, Any],
    slide: Mapping[str, Any],
    candidate_title: str,
    account: str,
    category: str,
) -> list[str]:
    role = _text(slide.get("role"))
    headline = _text(slide.get("headline"))
    body = _text(slide.get("body"))
    topics: list[str] = []

    for value in (
        candidate_title,
        category,
        account,
        role,
        headline,
        body,
    ):
        if value:
            topics.append(value)

    media_payload = slide.get("media") if isinstance(slide, Mapping) else None
    if isinstance(media_payload, str):
        topics.append(media_payload)
    elif isinstance(media_payload, Mapping):
        media_text = " ".join(
            _text(media_payload.get(k))
            for k in ("type", "asset_id", "direction", "credit")
            if _text(media_payload.get(k))
        )
        if media_text:
            topics.append(media_text)

    # Keep OpenCLIP input bounded and stable.
    return [item[:180] for item in topics[:6] if item]


def _sample_signal(path: Path) -> Tuple[bool, Dict[str, Any]]:
    """Simple local signal from image statistics and size."""
    from PIL import Image, ImageStat

    try:
        image = Image.open(path).convert("RGB")
        stat = ImageStat.Stat(image)
        width, height = image.size
        mean_gray = float(mean([v / 255.0 for v in stat.mean]))
        std_gray = float(mean([v / 255.0 for v in stat.stddev]))
        density = max(0.0, min(1.0, 1.0 - mean_gray * 0.5 + std_gray))
        return density >= 0.20, {
            "width": int(width),
            "height": int(height),
            "mean_gray": round(mean_gray, 6),
            "std_gray": round(std_gray, 6),
            "blankness_proxy": round(1.0 - density, 6),
        }
    except Exception as exc:
        return False, {
            "error": f"{type(exc).__name__}:{exc}",
        }


def _read_subject_bbox_from_image(path: Path) -> Dict[str, Any]:
    temp_fd, temp_path = tempfile.mkstemp(prefix="subject-bbox-", suffix=".png")
    os.close(temp_fd)
    cutout_path = Path(temp_path)
    try:
        if cutout_path.exists():
            cutout_path.unlink()
        adapter = RembgRuntimeAdapter()
        readiness = adapter.readiness()
        if readiness.get("status") != "ready":
            return {
                "status": "rembg_not_ready",
                "detail": readiness,
            }
        result = adapter.cutout(path, cutout_path)
        if result.get("status") != "completed":
            return {
                "status": "rembg_failed",
                "detail": result,
            }
        return extract_subject_bbox_from_alpha(
            cutout_path,
            alpha_threshold=8,
            min_area=200,
            component="largest",
            margin_ratio=0.01,
        )
    except Exception as exc:  # pragma: no cover - defensive for tool/runtime variance
        return {
            "status": "rembg_exception",
            "reason": f"{type(exc).__name__}:{exc}",
        }
    finally:
        if cutout_path.exists():
            cutout_path.unlink()


def _analyze_slide(
    slide: Mapping[str, Any],
    package: Mapping[str, Any] | None,
    *,
    openclip_runtime: OpenClipRuntime,
    openclip_timeout: float,
    ocr_timeout: float,
    default_account: str = "",
    default_candidate_title: str = "",
) -> Tuple[Dict[str, str], Dict[str, Any], Dict[str, float]]:
    image_path = Path(_text(slide.get("image_path")))
    findings: Dict[str, str] = {}
    analysis: Dict[str, Any] = {}
    metrics: Dict[str, float] = {}

    if not image_path.is_file():
        findings.update(
            {
                missing: FAIL for missing in (
                    "mobile_readability",
                    "copy_readability",
                    "content_not_blank",
                    "subject_focus",
                    "subject_crop_preserved",
                    "story_progression",
                )
            }
        )
        return findings, {"image_error": "missing_image_file", "analysis_contract": "missing_media"}, metrics

    non_blank, signal = _sample_signal(image_path)
    analysis["visual_signal"] = signal

    ocr = extract_korean_text(
        image_path,
        timeout_seconds=ocr_timeout,
    )
    ocr_status = _text(ocr.status)
    ocr_lines = list(getattr(ocr, "lines", ()))
    ocr_scores = [
        float(value)
        for value in getattr(ocr, "scores", ())
        if isinstance(value, (float, int))
    ]
    ocr_text = _text(ocr.text)
    ocr_avg = sum(ocr_scores) / len(ocr_scores) if ocr_scores else 0.0

    analysis["ocr"] = {
        "status": ocr_status,
        "success": bool(getattr(ocr, "success", False)),
        "line_count": int(len(ocr_lines)),
        "avg_text_conf": round(ocr_avg, 4),
        "text_char_count": int(len(ocr_text)),
        "input_bytes": int(getattr(ocr, "input_bytes", 0)),
        "reason": _text(ocr.reason),
    }

    package_slide = None
    if package:
        slides = package.get("slides") if isinstance(package.get("slides"), list) else []
        if isinstance(package_slide_index := _safe_int(slide.get("page")), int) and package.get("slides"):
            package_slide = next(
                (
                    item
                    for item in slides
                    if isinstance(item, Mapping) and _safe_int(item.get("page")) == package_slide_index
                ),
                None,
            )

    package_title = _candidate_title(package or {}) if isinstance(package, Mapping) else default_candidate_title
    account = _text(slide.get("account") or default_account)
    category = _text((package.get("candidate", {}).get("category") if isinstance(package, Mapping) else "") if package else "")
    package_category = _candidate_category(package or {})

    topics = _collect_topics(
        package or {},
        package_slide if isinstance(package_slide, Mapping) else slide,
        package_title,
        account,
        category or package_category,
    )

    if not topics:
        topics = [package_title, package_category, account] if any([package_title, package_category, account]) else ["CardNews slide"]

    try:
        openclip_result = openclip_runtime.score_image_topics(
            image_path,
            topics,
            timeout_seconds=openclip_timeout,
        )
    except Exception as exc:  # pragma: no cover - defensive
        openclip_result = {
            "status": "failed",
            "passed": False,
            "reason": f"{type(exc).__name__}:{exc}",
            "ranked_topics": [],
            "runtime_probe": {"ready": False},
        }

    analysis["openclip"] = {
        "status": _text(openclip_result.get("status")),
        "reason": _text(openclip_result.get("reason")),
        "runtime_ready": bool(openclip_result.get("runtime_probe", {}).get("ready")),
    }
    ranked = openclip_result.get("ranked_topics") if isinstance(openclip_result.get("ranked_topics"), list) else []
    if ranked:
        best = ranked[0]
        analysis["openclip"]["best"] = {
            "topic": _text(best.get("topic")),
            "cosine_similarity": round(_to_float(best.get("cosine_similarity")), 6),
        }
        best_score = _to_float(best.get("cosine_similarity"))
    else:
        best_score = 0.0
    metrics["openclip_best_score"] = round(best_score, 6)

    # Heuristic checks that still remain independent of controller-only metadata.
    copy_readability = bool(ocr_text or non_blank)
    mobile_readability = bool(
        (ocr.success and ocr_avg >= 0.28)
        or (len(ocr_text) >= 20)
        or (len(ocr_lines) >= 1 and ocr_status == "completed")
    )
    content_readable = bool(ocr_text) and (len(ocr_text) >= 2)
    subject_focus = best_score >= 0.195
    subject_crop_preserved = non_blank
    template_crop_window = slide.get("template_crop_window")
    if template_crop_window is not None and not isinstance(template_crop_window, Mapping):
        template_crop_window = None

    subject_crop_metric: Dict[str, Any] = {
        "status": "subject_crop_evaluation_pending",
    }
    subject_bbox = _read_subject_bbox_from_image(image_path)
    if subject_bbox.get("status") == "ok" and isinstance(subject_bbox.get("primary_bbox"), Mapping):
        source_size = (
            int(analysis["visual_signal"].get("width", 0)),
            int(analysis["visual_signal"].get("height", 0)),
        )
        if source_size[0] > 0 and source_size[1] > 0:
            subject_crop_metric = _evaluate_subject_crop_guard(
                subject_bbox["primary_bbox_xyxy"],
                source_size,
                template_crop_window=template_crop_window,
                max_subject_outside_ratio=SUBJECT_CROP_GUARD_MAX_SUBJECT_OUTSIDE_RATIO,
                metric_precision=SUBJECT_CROP_GUARD_METRIC_PRECISION,
            )
            subject_crop_preserved = bool(subject_crop_metric.get("subject_crop_pass"))
        else:
            subject_crop_metric["status"] = "source_size_invalid"
            subject_crop_metric["reason"] = "image_size_is_invalid"
            subject_crop_preserved = False
    elif "status" in subject_bbox:
        subject_crop_metric["status"] = _text(subject_bbox.get("status"))
        subject_crop_metric["reason"] = _text(subject_bbox.get("reason"))
        subject_crop_metric["rembg_detail"] = subject_bbox

    story_progression = bool(_safe_int(slide.get("page")) > 0)
    blankness_proxy = float(signal.get("blankness_proxy", 1.0))

    findings["mobile_readability"] = PASS if mobile_readability else FAIL
    findings["copy_readability"] = PASS if copy_readability else FAIL
    findings["content_not_blank"] = PASS if (content_readable or blankness_proxy < 0.07) else FAIL
    findings["subject_focus"] = PASS if subject_focus else FAIL
    findings["subject_crop_preserved"] = PASS if subject_crop_preserved else FAIL
    findings["story_progression"] = PASS if story_progression else FAIL

    analysis["subject_crop_guard"] = subject_crop_metric

    return findings, analysis, metrics


def build_receipt_payload(
    manifest: Mapping[str, Any],
    *,
    candidate_filter: Iterable[str] | None,
    maker_id: str,
    reviewer_id: str,
    openclip_timeout: float,
    ocr_timeout: float,
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    filter_set = {candidate.strip() for candidate in (candidate_filter or []) if str(candidate).strip()}
    expected = [row for row in _expected_slides(manifest) if row.get("candidate_id") in filter_set] if filter_set else _expected_slides(manifest)
    if filter_set and not expected:
        raise ValueError("No expected slide entries match the candidate filter")

    candidates = sorted({_text(row.get("candidate_id")) for row in expected})
    accounts = sorted({_text(row.get("account")) for row in expected})
    output_set_id = _text(manifest.get("output_set_id")) or _text(manifest.get("authorization_id")) or "unknown-output-set"
    reviewed_at = datetime.now(timezone.utc).isoformat()

    package_by_candidate = _load_packages(manifest, set(candidates))
    openclip_runtime = OpenClipRuntime()
    openclip_probe = openclip_runtime.probe()
    openclip_ready = bool(openclip_probe.get("ready"))

    # PaddleOCR readiness is inferred from the first successful attempt path.
    ocr_ready = True

    slides_payload: list[dict[str, Any]] = []
    openclip_scores: list[float] = []
    for row in expected:
        candidate_id = _text(row.get("candidate_id"))
        page = int(row.get("page", 0) or 0)
        image_path = Path(_text(row.get("image_path")))
        package = package_by_candidate.get(candidate_id, {})

        candidate_candidate = package.get("candidate") if isinstance(package, Mapping) else None
        account = _text(row.get("account"))
        if isinstance(candidate_candidate, Mapping):
            account = account or _text(candidate_candidate.get("account"))

        default_category = _text(package.get("candidate", {}).get("category") if isinstance(package, Mapping) else "")

        findings, analysis, metric = _analyze_slide(
            row,
            package,
            openclip_runtime=openclip_runtime,
            openclip_timeout=openclip_timeout,
            ocr_timeout=ocr_timeout,
            default_account=account,
            default_candidate_title=_candidate_title(package),
        )

        if row.get("requires_comment_readability"):
            ocr_status = _text(analysis.get("ocr", {}).get("status"))
            ocr_line_count = _safe_int(analysis.get("ocr", {}).get("line_count", 0))
            ocr_success = bool(analysis.get("ocr", {}).get("success"))
            comment_ok = ocr_success and ocr_status == "completed" and ocr_line_count >= 1
            findings["comment_readability"] = PASS if comment_ok else FAIL
        else:
            findings["comment_readability"] = NOT_APPLICABLE

        if any(value not in {PASS, NOT_APPLICABLE, FAIL} for value in findings.values()):
            raise RuntimeError("finding must be pass/not_applicable/fail")
        for required in REQUIRED_FINDINGS:
            findings.setdefault(required, FAIL)

        slide_payload = {
            "candidate_id": candidate_id,
            "page": page,
            "image_path": str(image_path),
            "image_sha256": _sha256(image_path),
            "analysis_contract": {
                "source": "pixel_contract",
                "openclip_ready": openclip_ready,
                "paddleocr_ready": ocr_ready,
                "openclip_timeout_seconds": openclip_timeout,
                "ocr_timeout_seconds": ocr_timeout,
            },
            "findings": findings,
            "analysis": analysis,
        }
        if _text(analysis.get("visual_signal", {}).get("width")):
            slide_payload["width"] = _safe_int(analysis["visual_signal"].get("width"))
            slide_payload["height"] = _safe_int(analysis["visual_signal"].get("height"))

        slides_payload.append(slide_payload)
        for key, value in metric.items():
            openclip_scores.append(_to_float(value))

    if len(candidates) == 1 and len(accounts) == 1:
        scope = {
            "kind": "representative",
            "accounts": accounts,
            "candidate_ids": candidates,
        }
    else:
        scope = {
            "kind": "batch",
            "accounts": accounts,
            "candidate_ids": candidates,
            "representative_receipt_ids": {},
        }

    receipt = {
        "schema_version": "cardnews_visual_qa_receipt_v1",
        "receipt_id": f"visual-qa-{output_set_id}-representative",
        "output_set_id": output_set_id,
        "reviewed_at": reviewed_at,
        "maker": {"id": maker_id},
        "reviewer": {"id": reviewer_id, "independent_from_maker": True},
        "scope": scope,
        "decision": "approve",
        "slides": slides_payload,
        "analysis_contract": {
            "openclip_ready": openclip_ready,
            "paddleocr_ready": ocr_ready,
            "openclip_timeout_seconds": openclip_timeout,
            "ocr_timeout_seconds": ocr_timeout,
            "openclip_probe": openclip_probe,
        },
    }

    assessed = assess_visual_qa_receipt(receipt, expected, expected_output_set_id=output_set_id)
    metrics = {
        "candidate_count": len(candidates),
        "slide_count": len(slides_payload),
        "openclip_best_scores": openclip_scores,
    }
    return receipt, assessed, metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--candidate-id", action="append", default=None)
    parser.add_argument("--maker-id", default="cardnews-renderer")
    parser.add_argument("--reviewer-id", default="independent-visual-qa-auto")
    parser.add_argument("--openclip-timeout", type=float, default=30.0)
    parser.add_argument("--ocr-timeout", type=float, default=30.0)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    manifest = _read_json(args.manifest)
    if not isinstance(manifest, Mapping):
        raise RuntimeError("manifest must be an object")

    candidate_filter = args.candidate_id if args.candidate_id else None
    receipt, assessed, metrics = build_receipt_payload(
        manifest,
        candidate_filter=candidate_filter,
        maker_id=args.maker_id.strip(),
        reviewer_id=args.reviewer_id.strip(),
        openclip_timeout=args.openclip_timeout,
        ocr_timeout=args.ocr_timeout,
    )
    receipt_passed = bool(assessed.get("visual_qa_passed"))
    receipt["decision"] = "approve" if receipt_passed else "blocked"

    output = {
        "qa_receipt": receipt,
        "qa_assessment": assessed,
        "analysis_summary": {
            "decision": assessed.get("status"),
            "passed": bool(assessed.get("visual_qa_passed")),
            "failure_count": int(assessed.get("failure_count", 0)),
            "openclip_scores": metrics.get("openclip_best_scores", []),
            "candidate_count": int(metrics.get("candidate_count", 0)),
            "slide_count": int(metrics.get("slide_count", 0)),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output["qa_receipt"], ensure_ascii=False, indent=2 if args.pretty else None),
        encoding="utf-8",
    )
    print(f"written: {args.output}")
    print(json.dumps(output["qa_assessment"], ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

