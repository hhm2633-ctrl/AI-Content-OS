"""Rebuild CardNews owner learning and optionally compile the analyzed corpus."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from modules.agent_console.owner_feedback_learning import (
    append_owner_review_feedback,
    ensure_owner_learning_index,
)
from modules.design_learning.owner_feedback_corpus import (
    DEFAULT_FEEDBACK_ROOT,
    DEFAULT_OUTPUT_PATH,
    compile_owner_feedback_corpus,
    register_candidate_patterns,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compile-corpus", action="store_true")
    parser.add_argument("--append-owner-rules", action="store_true")
    parser.add_argument("--register-patterns", action="store_true")
    parser.add_argument("--feedback-root", type=Path, default=DEFAULT_FEEDBACK_ROOT)
    parser.add_argument("--taxonomy-output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--pattern-registry",
        type=Path,
        default=REPOSITORY_ROOT / "knowledge" / "patterns" / "pattern_registry.jsonl",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = ensure_owner_learning_index()
    corpus = None
    appended = 0
    skipped_duplicate = 0
    append_errors = []
    registration = None
    if args.compile_corpus or args.append_owner_rules or args.register_patterns:
        corpus = compile_owner_feedback_corpus(
            args.feedback_root,
            output_path=args.taxonomy_output,
        )
    if args.append_owner_rules and corpus is not None:
        for payload in corpus.get("owner_rule_payloads", []):
            try:
                append_owner_review_feedback(payload)
                appended += 1
            except ValueError as error:
                if "duplicate owner feedback event_id" in str(error):
                    skipped_duplicate += 1
                else:
                    append_errors.append(str(error))
        result = ensure_owner_learning_index()
    if args.register_patterns and corpus is not None:
        registration = register_candidate_patterns(
            corpus.get("candidate_patterns", []),
            registry_path=args.pattern_registry,
        )
    report = {
        "schema_version": result.get("schema_version"),
        "stats": result.get("stats", {}),
        "errors": result.get("errors", []),
        "feedback_log_reloaded": result.get("feedback_log_reloaded", False),
        "corpus": {
            "compiled": corpus is not None,
            "output": str(args.taxonomy_output) if corpus is not None else None,
            "stats": corpus.get("stats", {}) if corpus is not None else {},
            "errors": corpus.get("errors", []) if corpus is not None else [],
        },
        "owner_rules": {
            "appended": appended,
            "skipped_duplicate": skipped_duplicate,
            "errors": append_errors,
        },
        "pattern_registration": registration,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    has_errors = bool(
        result.get("errors")
        or append_errors
        or (corpus and corpus.get("errors"))
        or (registration and registration.get("rejected"))
    )
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
