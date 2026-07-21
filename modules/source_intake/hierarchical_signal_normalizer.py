"""Deterministic Stage-1 normalization for shallow source-intake candidates.

The normalizer compares only observed visible signals.  It deliberately keeps
missing values as missing so sources whose pages do not expose engagement
metrics (notably many news sources) are not assigned fabricated zeroes.
"""

from __future__ import annotations

from copy import deepcopy
import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


HIERARCHICAL_SIGNAL_NORMALIZER_VERSION = "hierarchical_signal_normalizer_v1"
STAGE1_NORMALIZED_SIGNALS_FIELD = "stage1_normalized_signals"

SIGNAL_NAMES: Tuple[str, ...] = (
    "rank_position",
    "views",
    "comments",
    "likes",
    "dislikes",
)

# A one-item narrow cohort carries no comparative information.  In that case
# we continue down the hierarchy; the batch cohort remains the final fallback
# even when the whole batch contains one observed value.
MIN_NARROW_COHORT_SIZE = 2

_BASIS_CONFIDENCE = {
    "source_topic": 1.0,
    "source": 0.9,
    "source_type": 0.75,
    "batch": 0.6,
}


def _closed(reason_code: str, reason: str) -> Dict[str, Any]:
    return {
        "schema_version": HIERARCHICAL_SIGNAL_NORMALIZER_VERSION,
        "status": "closed",
        "reason_code": reason_code,
        "reason": reason,
        "item_count": 0,
        "items": [],
    }


def _text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _topic_key(candidate: Mapping[str, Any]) -> Optional[str]:
    """Return the first available topic-like cohort discriminator."""
    for field in ("source_lane_id", "board_or_category", "category"):
        value = _text(candidate.get(field))
        if value is not None:
            return f"{field}:{value}"
    return None


def _cohort_keys(candidate: Mapping[str, Any]) -> Dict[str, Optional[Tuple[str, ...]]]:
    source_id = _text(candidate.get("source_id"))
    source_type = _text(candidate.get("source_type"))
    topic = _topic_key(candidate)

    return {
        "source_topic": (source_id, topic) if source_id and topic else None,
        "source": (source_id,) if source_id else None,
        "source_type": (source_type,) if source_type else None,
        "batch": ("all",),
    }


def _is_observed_number(value: Any, signal: str) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if not math.isfinite(float(value)):
        return False
    if signal == "rank_position":
        return float(value) > 0.0
    return float(value) >= 0.0


def _extract_signal(candidate: Mapping[str, Any], signal: str) -> Tuple[Any, str, str]:
    """Return raw value, status, and origin without coercing missing to zero."""
    if signal == "rank_position":
        if signal not in candidate or candidate.get(signal) is None:
            return None, "missing", "top_level"
        raw = candidate.get(signal)
        return (
            (raw, "observed", "top_level")
            if _is_observed_number(raw, signal)
            else (raw, "invalid", "top_level")
        )

    visible_metrics = candidate.get("visible_metrics")
    if isinstance(visible_metrics, Mapping) and signal in visible_metrics:
        raw = visible_metrics.get(signal)
        if raw is None:
            return None, "missing", "visible_metrics"
        return (
            (raw, "observed", "visible_metrics")
            if _is_observed_number(raw, signal)
            else (raw, "invalid", "visible_metrics")
        )

    if signal not in candidate or candidate.get(signal) is None:
        return None, "missing", "flat"
    raw = candidate.get(signal)
    return (
        (raw, "observed", "flat")
        if _is_observed_number(raw, signal)
        else (raw, "invalid", "flat")
    )


def _build_cohorts(
    candidates: Sequence[Mapping[str, Any]],
    observations: Sequence[Mapping[str, Tuple[Any, str, str]]],
) -> Dict[str, Dict[str, Dict[Tuple[str, ...], List[float]]]]:
    cohorts: Dict[str, Dict[str, Dict[Tuple[str, ...], List[float]]]] = {
        signal: {basis: {} for basis in _BASIS_CONFIDENCE}
        for signal in SIGNAL_NAMES
    }

    for index, candidate in enumerate(candidates):
        keys = _cohort_keys(candidate)
        for signal in SIGNAL_NAMES:
            raw, status, _origin = observations[index][signal]
            if status != "observed":
                continue
            value = float(raw)
            for basis, key in keys.items():
                if key is not None:
                    cohorts[signal][basis].setdefault(key, []).append(value)

    return cohorts


def _select_cohort(
    signal: str,
    candidate: Mapping[str, Any],
    cohorts: Mapping[str, Mapping[str, Mapping[Tuple[str, ...], List[float]]]],
) -> Tuple[str, List[float]]:
    keys = _cohort_keys(candidate)

    for basis in ("source_topic", "source", "source_type"):
        key = keys[basis]
        values = cohorts[signal][basis].get(key, []) if key is not None else []
        if len(values) >= MIN_NARROW_COHORT_SIZE:
            return basis, values

    return "batch", cohorts[signal]["batch"].get(("all",), [])


def _empirical_midrank(value: float, values: Sequence[float], invert: bool) -> float:
    """Map an observed value to a deterministic 0..1 empirical midrank."""
    if invert:
        better = sum(candidate_value > value for candidate_value in values)
    else:
        better = sum(candidate_value < value for candidate_value in values)
    equal = sum(candidate_value == value for candidate_value in values)
    normalized = (better + (0.5 * equal)) / len(values)
    return round(min(max(normalized, 0.0), 1.0), 6)


def _confidence(basis: str, sample_size: int) -> float:
    # Five observations are enough for full V1 sample confidence.  Specificity
    # remains separate through the basis multiplier.
    sample_confidence = min(sample_size / 5.0, 1.0)
    return round(_BASIS_CONFIDENCE[basis] * sample_confidence, 6)


def run_hierarchical_signal_normalizer(candidates: Any) -> Dict[str, Any]:
    """Normalize observed Stage-1 signals without mutating ``candidates``.

    ``candidates`` must be a list of mappings.  Candidate fields are preserved
    in each output item so the result can be passed directly to Stage 2.
    Malformed top-level batches fail closed and never return partial output.
    """
    if not isinstance(candidates, list):
        return _closed("malformed_candidates", "candidates must be a list")

    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, Mapping):
            return _closed(
                "malformed_candidate",
                f"candidates[{index}] must be an object",
            )

    observations: List[Dict[str, Tuple[Any, str, str]]] = [
        {signal: _extract_signal(candidate, signal) for signal in SIGNAL_NAMES}
        for candidate in candidates
    ]
    cohorts = _build_cohorts(candidates, observations)

    output_items: List[Dict[str, Any]] = []
    observed_counts = {signal: 0 for signal in SIGNAL_NAMES}
    missing_counts = {signal: 0 for signal in SIGNAL_NAMES}
    invalid_counts = {signal: 0 for signal in SIGNAL_NAMES}

    for index, candidate in enumerate(candidates):
        normalized_candidate = deepcopy(dict(candidate))
        signal_results: Dict[str, Dict[str, Any]] = {}

        for signal in SIGNAL_NAMES:
            raw, status, origin = observations[index][signal]
            if status != "observed":
                signal_results[signal] = {
                    "raw_value": raw,
                    "normalized_value": None,
                    "status": status,
                    "basis": None,
                    "sample_size": 0,
                    "confidence": 0.0,
                    "value_origin": origin,
                }
                if status == "missing":
                    missing_counts[signal] += 1
                else:
                    invalid_counts[signal] += 1
                continue

            basis, cohort_values = _select_cohort(signal, candidate, cohorts)
            sample_size = len(cohort_values)
            # An observed value always belongs to the batch cohort, so an
            # empty cohort here would indicate an internal contract violation.
            normalized_value = (
                _empirical_midrank(
                    float(raw),
                    cohort_values,
                    invert=(signal == "rank_position"),
                )
                if sample_size
                else None
            )
            signal_results[signal] = {
                "raw_value": raw,
                "normalized_value": normalized_value,
                "status": "observed",
                "basis": basis,
                "sample_size": sample_size,
                "confidence": _confidence(basis, sample_size) if sample_size else 0.0,
                "value_origin": origin,
            }
            observed_counts[signal] += 1

        normalized_candidate[STAGE1_NORMALIZED_SIGNALS_FIELD] = signal_results
        output_items.append(normalized_candidate)

    return {
        "schema_version": HIERARCHICAL_SIGNAL_NORMALIZER_VERSION,
        "status": "ok",
        "item_count": len(output_items),
        "items": output_items,
        "diagnostics": {
            "hierarchy": ["source_topic", "source", "source_type", "batch"],
            "minimum_narrow_cohort_size": MIN_NARROW_COHORT_SIZE,
            "observed_counts": observed_counts,
            "missing_counts": missing_counts,
            "invalid_counts": invalid_counts,
        },
    }


__all__ = [
    "run_hierarchical_signal_normalizer",
    "HIERARCHICAL_SIGNAL_NORMALIZER_VERSION",
    "STAGE1_NORMALIZED_SIGNALS_FIELD",
    "SIGNAL_NAMES",
    "MIN_NARROW_COHORT_SIZE",
]
