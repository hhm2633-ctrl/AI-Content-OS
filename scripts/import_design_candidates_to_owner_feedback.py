"""Import cardnews design-learning candidates into owner feedback history."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from modules.design_learning.card_news_design_learning import build_design_candidates
from modules.agent_console.owner_feedback_learning import append_owner_review_feedback


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def candidate_to_owner_review_payload(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Convert one design-learning candidate into owner_review_learning payload."""

    candidate_type = _text(candidate.get("candidate_type")) or "card_news_design_learning"
    observed_pattern = _text(candidate.get("observed_pattern")) or candidate_type
    recommended_usage = _text(candidate.get("recommended_usage")) or observed_pattern
    candidate_id = _text(candidate.get("candidate_id"))

    return {
        "review_kind": "candidate_evaluation",
        "category": candidate_type,
        "title": observed_pattern[:300],
        "candidate_id": candidate_id or f"design-{observed_pattern[:40]}",
        "owner_decision": observed_pattern[:2000],
        "owner_reason": recommended_usage[:2000],
        "applies_to": [candidate_type, "card_news_design_learning", "design_candidate"],
        "source": "human_owner_review_workspace",
    }


def _feedback_line_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in path.open(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--feedback-path",
        type=Path,
        default=REPOSITORY_ROOT / "knowledge" / "owner_feedback" / "cardnews_owner_feedback.jsonl",
    )
    parser.add_argument(
        "--index-path",
        type=Path,
        default=REPOSITORY_ROOT / "knowledge" / "owner_feedback" / "cardnews_owner_learning_index.json",
    )
    parser.add_argument("--candidate-limit", type=int, default=None)
    args = parser.parse_args()

    feedback_path = args.feedback_path
    index_path = args.index_path

    payload = build_design_candidates()
    candidates = payload.get("candidates", [])
    if args.candidate_limit is not None and args.candidate_limit >= 0:
        candidates = candidates[:args.candidate_limit]

    before = _feedback_line_count(feedback_path)
    appended = 0
    skipped_duplicate = 0
    failed = 0
    first_error = None

    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            failed += 1
            continue
        try:
            event_payload = candidate_to_owner_review_payload(candidate)
            append_owner_review_feedback(
                event_payload,
                feedback_path=feedback_path,
                index_path=index_path,
            )
            appended += 1
        except ValueError as error:
            message = str(error)
            if "duplicate owner feedback event_id" in message:
                skipped_duplicate += 1
            else:
                failed += 1
                if first_error is None:
                    first_error = message

    after = _feedback_line_count(feedback_path)
    result = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "feedback_path": str(feedback_path),
        "index_path": str(index_path),
        "candidate_count": len(candidates),
        "appended": appended,
        "skipped_duplicate": skipped_duplicate,
        "failed": failed,
        "line_count_before": before,
        "line_count_after": after,
        "line_count_delta": max(after - before, 0),
        "first_error": first_error,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
