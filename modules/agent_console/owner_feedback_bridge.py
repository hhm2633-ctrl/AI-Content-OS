"""Record one owner-review UI decision with an optional Agent Console trace."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from modules.agent_console.owner_feedback_learning import append_owner_review_feedback


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def _job_trace(state: Mapping[str, Any], candidate_id: str) -> dict[str, Any]:
    jobs = state.get("jobs", []) if isinstance(state, Mapping) else []
    matches = [
        job for job in jobs
        if isinstance(job, Mapping) and str(job.get("candidate_id") or "") == candidate_id
    ]
    if not matches:
        return {}
    job = matches[-1]
    dispatch = job.get("dispatch") if isinstance(job.get("dispatch"), Mapping) else {}
    education = dispatch.get("education_receipt") if isinstance(dispatch.get("education_receipt"), Mapping) else {}
    return {
        "job_id": job.get("job_id"),
        "result_status": job.get("status"),
        "handoff_path": job.get("handoff_path"),
        "education_receipt": education,
    }


def record_owner_grade(
    *,
    candidate_id: str,
    grade: str,
    category: str,
    title: str,
    account: str,
    feedback_path: Path,
    index_path: Path,
    console_state_path: Path,
) -> dict[str, Any]:
    clean_grade = str(grade).strip()
    if clean_grade not in {"1", "2", "3", "exclude"}:
        raise ValueError("grade must be 1, 2, 3, or exclude")
    state = _read_json(console_state_path, {})
    recorded_at = datetime.now(timezone.utc).isoformat()
    event_digest = hashlib.sha256(
        f"{candidate_id}|{clean_grade}|{recorded_at}".encode("utf-8")
    ).hexdigest()[:20]
    result = append_owner_review_feedback(
        {
            "event_id": f"owner-review-{event_digest}",
            "recorded_at": recorded_at,
            "review_kind": "candidate_evaluation",
            "source": "human_owner_review_workspace",
            "candidate_id": str(candidate_id).strip(),
            "category": str(category).strip(),
            "title": str(title).strip(),
            "owner_decision": f"GRADE_{clean_grade.upper()}",
            "owner_reason": (
                f"Owner assigned grade {clean_grade} as optional CardNews quality feedback. "
                "This grade is not selection approval, production approval, or upload approval."
            ),
            "applies_to": [
                str(account).strip(),
                "candidate_selection",
                "owner_grading",
                "optional_reference_signal",
                "not_selection_gate",
                "not_production_gate",
                "pre_upload_approval_only",
            ],
        },
        execution_context=_job_trace(state, str(candidate_id).strip()),
        feedback_path=feedback_path,
        index_path=index_path,
    )
    result["signal_contract"] = {
        "role": "optional_reference_signal",
        "selection_gate": False,
        "production_gate": False,
        "upload_approval": False,
        "approval_gate_stage": "pre_upload_manual_upload_ready",
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--grade", required=True)
    parser.add_argument("--category", default="")
    parser.add_argument("--title", default="")
    parser.add_argument("--account", default="")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    result = record_owner_grade(
        candidate_id=args.candidate_id,
        grade=args.grade,
        category=args.category,
        title=args.title,
        account=args.account,
        feedback_path=root / "knowledge" / "owner_feedback" / "cardnews_owner_feedback.jsonl",
        index_path=root / "knowledge" / "owner_feedback" / "cardnews_owner_learning_index.json",
        console_state_path=root / "artifacts" / "agent_console_v1" / "state.json",
    )
    print(json.dumps({
        "status": "recorded",
        "event_id": result["event"]["event_id"],
        "learning_stage": (result.get("learning_record") or {}).get("stage"),
        "execution_trace": result["event"].get("execution_trace", {}),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["record_owner_grade"]
