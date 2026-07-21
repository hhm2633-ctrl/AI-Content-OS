"""Deterministic comparison-metric calculator for the Source Intake layer.

All derived metrics are computed from visible page metrics with hard null/zero
safety: a missing input never raises and never produces a fabricated number —
it produces None (or the documented neutral fallback for velocity).

No AI/token usage here by design; this is the cheap wide-scan scoring that
decides which topics are even worth spending tokens on later.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from modules.source_intake.source_intake_schema import (
    CHANNEL_CANDIDATES,
    VISIBLE_METRIC_KEYS,
)

# Neutral velocity when published_at is missing/unparsable: the item is neither
# boosted nor buried for lacking a timestamp.
NEUTRAL_VELOCITY_SCORE = 0.5

# Normalization caps so heterogeneous metrics land on a comparable 0..1 scale.
COMMENT_DENSITY_CAP = 0.05      # 5 comments per 100 views is already very hot
LIKE_RATE_CAP = 0.02            # 2 likes per 100 views is very hot
CONTROVERSY_CAP = 5.0           # 5+ comments per like = full controversy signal
VELOCITY_CAP = 200.0            # 200+ reactions/hour = full velocity signal
MIN_ELAPSED_HOURS = 0.1

DEFAULT_DEEP_DIVE_THRESHOLD = 0.35

# Per-channel weighting of the normalized derived metrics. V1 scoring input/
# output structure only — no account operation or publishing happens here.
CHANNEL_WEIGHT_PROFILES: Dict[str, Dict[str, float]] = {
    "issue_daily": {
        "velocity_score": 0.40,
        "comment_density": 0.30,
        "controversy_score": 0.20,
        "like_rate": 0.10,
    },
    "love_signal": {
        "comment_density": 0.40,
        "like_rate": 0.30,
        "velocity_score": 0.20,
        "controversy_score": 0.10,
    },
    "dopamine_issue": {
        "controversy_score": 0.40,
        "velocity_score": 0.30,
        "comment_density": 0.20,
        "like_rate": 0.10,
    },
    "style_weather": {
        "like_rate": 0.40,
        "velocity_score": 0.30,
        "comment_density": 0.20,
        "controversy_score": 0.10,
    },
    "commerce_signal": {
        "like_rate": 0.35,
        "comment_density": 0.35,
        "velocity_score": 0.20,
        "controversy_score": 0.10,
    },
}


def _safe_int(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value if value >= 0 else None

    if isinstance(value, float):
        return int(value) if value >= 0 else None

    return None


def _safe_ratio(numerator: Optional[int], denominator: Optional[int]) -> Optional[float]:
    if numerator is None or denominator is None or denominator <= 0:
        return None

    return round(numerator / denominator, 6)


def compute_comment_density(metrics: Dict[str, Any]) -> Optional[float]:
    return _safe_ratio(_safe_int(metrics.get("comments")), _safe_int(metrics.get("views")))


def compute_like_rate(metrics: Dict[str, Any]) -> Optional[float]:
    return _safe_ratio(_safe_int(metrics.get("likes")), _safe_int(metrics.get("views")))


def compute_controversy_score(metrics: Dict[str, Any]) -> Optional[float]:
    comments = _safe_int(metrics.get("comments"))

    if comments is None:
        return None

    likes = _safe_int(metrics.get("likes")) or 0
    base = comments / max(likes, 1)

    dislikes = _safe_int(metrics.get("dislikes"))
    if dislikes is not None and dislikes > 0:
        base = base * (1.0 + dislikes / max(likes, 1))

    return round(base, 6)


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def compute_velocity_score(
    metrics: Dict[str, Any],
    published_at: Optional[str],
    collected_at: Optional[str],
) -> Dict[str, Any]:
    """reactions per elapsed hour; neutral fallback when published_at is unusable."""
    reaction_parts = [
        _safe_int(metrics.get(key))
        for key in ("comments", "likes", "scraps", "shares")
    ]
    known_parts = [part for part in reaction_parts if part is not None]

    published = _parse_timestamp(published_at)
    collected = _parse_timestamp(collected_at)

    if published is None or collected is None or not known_parts:
        return {
            "velocity_score": NEUTRAL_VELOCITY_SCORE,
            "velocity_fallback": True,
            "velocity_reason": "missing_published_at" if published is None else "missing_reactions",
        }

    if published.tzinfo != collected.tzinfo:
        # Mixed aware/naive timestamps can't be compared safely — stay neutral.
        if (published.tzinfo is None) != (collected.tzinfo is None):
            return {
                "velocity_score": NEUTRAL_VELOCITY_SCORE,
                "velocity_fallback": True,
                "velocity_reason": "timestamp_mismatch",
            }

    elapsed_hours = (collected - published).total_seconds() / 3600.0
    elapsed_hours = max(elapsed_hours, MIN_ELAPSED_HOURS)

    reaction_count = sum(known_parts)

    return {
        "velocity_score": round(reaction_count / elapsed_hours, 6),
        "velocity_fallback": False,
        "velocity_reason": "computed",
    }


def compute_derived_metrics(
    visible_metrics: Optional[Dict[str, Any]],
    published_at: Optional[str] = None,
    collected_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute all derived comparison metrics. Deterministic and null-safe."""
    metrics = visible_metrics if isinstance(visible_metrics, dict) else {}

    velocity = compute_velocity_score(metrics, published_at, collected_at)

    return {
        "comment_density": compute_comment_density(metrics),
        "like_rate": compute_like_rate(metrics),
        "controversy_score": compute_controversy_score(metrics),
        "velocity_score": velocity["velocity_score"],
        "velocity_fallback": velocity["velocity_fallback"],
        "velocity_reason": velocity["velocity_reason"],
    }


def _normalize(value: Optional[float], cap: float) -> float:
    """Clamp a raw derived metric into 0..1; None contributes zero signal."""
    if value is None or cap <= 0:
        return 0.0

    return min(max(value / cap, 0.0), 1.0)


def normalized_signal_vector(derived: Dict[str, Any]) -> Dict[str, float]:
    velocity = derived.get("velocity_score")

    if derived.get("velocity_fallback"):
        velocity_signal = NEUTRAL_VELOCITY_SCORE
    else:
        velocity_signal = _normalize(velocity, VELOCITY_CAP)

    return {
        "comment_density": _normalize(derived.get("comment_density"), COMMENT_DENSITY_CAP),
        "like_rate": _normalize(derived.get("like_rate"), LIKE_RATE_CAP),
        "controversy_score": _normalize(derived.get("controversy_score"), CONTROVERSY_CAP),
        "velocity_score": velocity_signal,
    }


def compute_channel_scores(derived: Dict[str, Any]) -> Dict[str, float]:
    """Weighted sum per channel candidate over the normalized signal vector."""
    signals = normalized_signal_vector(derived if isinstance(derived, dict) else {})
    scores = {}

    for channel in CHANNEL_CANDIDATES:
        weights = CHANNEL_WEIGHT_PROFILES.get(channel, {})
        score = sum(
            weights.get(metric, 0.0) * signals.get(metric, 0.0)
            for metric in signals
        )
        scores[channel] = round(score, 6)

    return scores


def compute_deep_dive_priority(
    derived: Dict[str, Any],
    channel_candidates: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Deep-dive priority = best channel score among the item's candidates.

    Returns the full per-channel breakdown so downstream routing can reuse it.
    """
    all_scores = compute_channel_scores(derived)
    candidates = [
        channel for channel in (channel_candidates or CHANNEL_CANDIDATES)
        if channel in CHANNEL_CANDIDATES
    ] or CHANNEL_CANDIDATES

    candidate_scores = {channel: all_scores[channel] for channel in candidates}
    best_channel = max(candidate_scores, key=lambda ch: candidate_scores[ch])

    return {
        "deep_dive_priority": candidate_scores[best_channel],
        "best_channel": best_channel,
        "channel_scores": candidate_scores,
    }


def select_deep_dive_candidates(
    items: List[Dict[str, Any]],
    threshold: float = DEFAULT_DEEP_DIVE_THRESHOLD,
    max_count: int = 5,
) -> List[Dict[str, Any]]:
    """Only items above threshold become deep-dive targets, capped at max_count.

    This is the cost gate: everything below threshold stays shallow forever.
    """
    eligible = [
        item for item in (items or [])
        if isinstance(item, dict)
        and isinstance(item.get("deep_dive_priority"), (int, float))
        and not isinstance(item.get("deep_dive_priority"), bool)
        and item["deep_dive_priority"] >= threshold
    ]

    eligible.sort(key=lambda item: item["deep_dive_priority"], reverse=True)

    return eligible[:max_count]
