"""Import verified Instagram card-news learning candidates into the existing
Pattern Registry (modules/knowledge/pattern_registry.py).

This script does NOT create a new registry or a new data model. It builds
``Pattern`` records using the existing, unmodified contract
(``modules/knowledge/pattern_contract.py``) and registers them through the
existing ``PatternRegistry`` (``modules/knowledge/pattern_registry.py``) —
the same store read by ``scripts/knowledge_query.py`` and
``scripts/knowledge_validate.py``.

Source of truth (read-only, never modified by this script):
  external_workclaude/instagram_broad_learning_v1/RAW_OBSERVATIONS.json
  external_workclaude/instagram_broad_learning_v1/LEARNING_CANDIDATES.json

Design notes (why fields map the way they do):
  - The Pattern contract is strict: ``Pattern.from_dict`` rejects any record
    whose keys are not exactly the 15 declared dataclass fields. Adding new
    fields (evidence_urls, observation_count, dataset_hash, ...) directly to
    the dataclass would make every existing JSONL line in the registry fail
    to load (missing the new keys) and would break
    ``tests/test_pattern_registry.py``. So this script does NOT touch the
    contract or the registry class. Instead it maps the Instagram-learning
    data onto the existing fields:
      * evidence_urls              -> source_claim_ids (raw post URLs; valid
                                       for CANDIDATE status, which is all this
                                       script ever writes — the PROMOTED-only
                                       "resolves to a real source_id" check in
                                       scripts/knowledge_validate.py never
                                       fires for CANDIDATE records)
      * evidence_status (the two   -> a `evidence_status=...` marker inside
        allowed values)               `preconditions`, plus it drives the
                                       ``confidence`` float via a fixed,
                                       documented mapping (never "validated"/
                                       "proven")
      * observation_count/account_count/category_count/dataset_hash/
        import_version              -> `key=value` markers inside
                                       `preconditions` (all non-empty
                                       strings, contract-legal), parseable via
                                       `parse_preconditions()` below
      * DM-keyword-CTA candidate    -> filed under domain="engagement_mechanic"
                                       (never "content_pattern"), with
                                       `prohibited_actions` explicitly barring
                                       default/primary CTA use and a
                                       `risk_flags=manipulation_risk,funnel_risk`
                                       marker — see ENGAGEMENT_MECHANIC_MARKERS
  - Every imported pattern is written with status=CANDIDATE only. The
    registry's own ALLOWED_TRANSITIONS forbids CANDIDATE->CANDIDATE, so a
    pattern_id can only ever be registered once as CANDIDATE — re-running this
    script is naturally idempotent (already-present pattern_ids are skipped,
    never re-registered, never promoted).
  - Nothing here writes original Instagram caption text or images. The
    ``candidate`` strings in LEARNING_CANDIDATES.json are already this
    project's own structural-analysis sentences (verified during the prior
    audit passes), not verbatim post captions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from modules.knowledge.pattern_contract import Pattern, PatternStatus  # noqa: E402
from modules.knowledge.pattern_registry import PatternRegistry, PatternRegistryError  # noqa: E402

SOURCE_DIR = REPOSITORY_ROOT / "external_workclaude" / "instagram_broad_learning_v1"
RAW_OBSERVATIONS_PATH = SOURCE_DIR / "RAW_OBSERVATIONS.json"
LEARNING_CANDIDATES_PATH = SOURCE_DIR / "LEARNING_CANDIDATES.json"
DEFAULT_REGISTRY_PATH = REPOSITORY_ROOT / "knowledge" / "patterns" / "pattern_registry.jsonl"

IMPORT_VERSION = "instagram_broad_learning_v1.v1"
OWNER_SKILL = "ai-content-os-knowledge-intelligence"
PATTERN_ID_PREFIX = "pattern.instagram_learning"

# The only two evidence classes this import will ever write. Anything else
# (validated/proven/etc.) is rejected before a Pattern object is built.
ALLOWED_EVIDENCE_STATUSES = {"benchmark_observed", "hypothesis_only"}
CONFIDENCE_BY_EVIDENCE_STATUS = {"benchmark_observed": 0.5, "hypothesis_only": 0.25}
DISALLOWED_PROMOTION_WORDS = {"validated", "proven", "confirmed", "verified fact"}

# Stable (marker substring -> slug, is_engagement_mechanic) map. Matching by a
# distinctive substring of the candidate sentence keeps pattern_id generation
# deterministic across reruns even if the candidates list is reordered.
CANDIDATE_SLUG_MAP: Tuple[Tuple[str, str, bool], ...] = (
    ("댓글에 특정 키워드를 남기면 DM으로", "dm_keyword_cta", True),
    ("지역/기관 공지형 카드뉴스", "regional_institution_notice_style", False),
    ("인용·반전형 헤드라인", "quote_reversal_hook", False),
    ("번호형 큐레이션 리스트 구조", "numbered_curation_list_structure", False),
    ("병원/공공기관 계정은 캐릭터 의인화", "healthcare_public_character_illustration", False),
    ("게시 직후(수 시간 내) 관찰", "immediate_post_zero_engagement", False),
)


def compute_dataset_hash(path: Path) -> str:
    """Content-addressed hash of the canonical RAW dataset (never re-derived)."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def load_raw_urls(path: Path) -> Set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["url"] for item in data["observations"]}


def load_candidates(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["candidates"]


def _slug_for(candidate_text: str) -> Tuple[str, bool]:
    for marker, slug, is_mechanic in CANDIDATE_SLUG_MAP:
        if marker in candidate_text:
            return slug, is_mechanic
    # Fail-safe fallback for any future, unmapped candidate: deterministic,
    # content-addressed, never colliding with the explicit slugs above.
    fallback = "auto_" + hashlib.sha1(candidate_text.encode("utf-8")).hexdigest()[:10]
    return fallback, False


def parse_preconditions(preconditions: List[str]) -> Dict[str, str]:
    """Read back the key=value markers this script writes into preconditions."""
    parsed: Dict[str, str] = {}
    for item in preconditions:
        if "=" in item:
            key, _, value = item.partition("=")
            parsed[key] = value
    return parsed


@dataclass
class RejectedItem:
    candidate: str
    reason: str


@dataclass
class ImportReport:
    attempted: int = 0
    imported: int = 0
    skipped_duplicate: int = 0
    rejected: int = 0
    rejected_items: List[RejectedItem] = field(default_factory=list)
    registry_status_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attempted": self.attempted,
            "imported": self.imported,
            "skipped_duplicate": self.skipped_duplicate,
            "rejected": self.rejected,
            "rejected_items": [
                {"candidate": item.candidate, "reason": item.reason} for item in self.rejected_items
            ],
            "registry_status_counts": self.registry_status_counts,
        }


class ImportValidationError(ValueError):
    """Raised for a candidate that must be rejected before touching the registry."""


def build_pattern(candidate: Dict[str, Any], *, dataset_hash: str, raw_urls: Set[str]) -> Pattern:
    text = candidate.get("candidate")
    if not isinstance(text, str) or not text.strip():
        raise ImportValidationError("candidate text is missing or empty")

    evidence_status = candidate.get("confidence")
    if evidence_status not in ALLOWED_EVIDENCE_STATUSES:
        raise ImportValidationError(
            f"disallowed evidence status {evidence_status!r} — only "
            f"{sorted(ALLOWED_EVIDENCE_STATUSES)} are accepted (no validated/proven promotion)"
        )
    lowered = text.casefold()
    for banned in DISALLOWED_PROMOTION_WORDS:
        if banned in lowered:
            raise ImportValidationError(f"candidate text contains a promotion-style claim word: {banned!r}")

    evidence_urls = candidate.get("evidence_urls")
    if not isinstance(evidence_urls, list) or not evidence_urls:
        raise ImportValidationError("evidence_urls missing or empty")
    unresolvable = [url for url in evidence_urls if url not in raw_urls]
    if unresolvable:
        raise ImportValidationError(f"evidence_urls not found in RAW_OBSERVATIONS.json: {unresolvable}")

    for count_field in ("observation_count", "account_count", "category_count"):
        value = candidate.get(count_field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ImportValidationError(f"{count_field} must be a positive integer, got {value!r}")

    slug, is_mechanic = _slug_for(text)
    domain = "engagement_mechanic" if is_mechanic else "content_pattern"
    pattern_id = f"{PATTERN_ID_PREFIX}.{domain}.{slug}"

    preconditions = [
        f"evidence_status={evidence_status}",
        f"observation_count={candidate['observation_count']}",
        f"account_count={candidate['account_count']}",
        f"category_count={candidate['category_count']}",
        f"dataset_hash={dataset_hash}",
        f"import_version={IMPORT_VERSION}",
        "source_dataset=external_workclaude/instagram_broad_learning_v1/RAW_OBSERVATIONS.json",
    ]

    prohibited_actions = [
        "Treating this pattern as validated or proven — only benchmark_observed/hypothesis_only evidence "
        "classes are recognized for this import",
        "Promoting this pattern to VERIFIED/PROMOTED without independent human review per "
        "knowledge/patterns/promotion_policy.md",
        "Reproducing the original Instagram post images or full captions — only the source URL and the "
        "structural claim above may be referenced",
    ]
    failure_signals = [
        "Causal claim not verified — evidence is correlational only",
        f"Sample size n={candidate['observation_count']} across {candidate['account_count']} accounts — "
        "not statistically robust",
    ]
    success_metrics = [
        candidate.get("note") or "Structural repetition observed across the listed evidence_urls",
    ]

    if is_mechanic:
        preconditions.append("risk_flags=manipulation_risk,funnel_risk")
        prohibited_actions.extend(
            [
                "Using this engagement mechanic as the default or primary recommended CTA in generated "
                "content",
                "Presenting this comment-keyword/DM-funnel mechanic as a general best practice without "
                "disclosing manipulation and funnel risk",
            ]
        )
        failure_signals.append(
            "Mechanic may read as comment-farming and could violate platform manipulation/spam policies "
            "if used without disclosure"
        )
        recommended_action = (
            f"[ENGAGEMENT MECHANIC — reference only, do not default-recommend; evidence={evidence_status}] "
            f"{text}"
        )
    else:
        recommended_action = f"[REFERENCE PATTERN — evidence={evidence_status}] {text}"

    return Pattern(
        pattern_id=pattern_id,
        name=text[:200],
        domain=domain,
        source_claim_ids=list(evidence_urls),
        preconditions=preconditions,
        recommended_action=recommended_action,
        prohibited_actions=prohibited_actions,
        success_metrics=success_metrics,
        failure_signals=failure_signals,
        confidence=CONFIDENCE_BY_EVIDENCE_STATUS[evidence_status],
        status=PatternStatus.CANDIDATE,
        version="1.0.0",
        reviewed_at=None,
        owner_skill=OWNER_SKILL,
        supersedes=None,
        expires_at=None,
    )


def run_import(
    registry: PatternRegistry,
    candidates: List[Dict[str, Any]],
    *,
    dataset_hash: str,
    raw_urls: Set[str],
    dry_run: bool = False,
) -> ImportReport:
    report = ImportReport()
    for candidate in candidates:
        report.attempted += 1
        text = candidate.get("candidate", "<missing candidate text>")
        try:
            pattern = build_pattern(candidate, dataset_hash=dataset_hash, raw_urls=raw_urls)
        except ImportValidationError as exc:
            report.rejected += 1
            report.rejected_items.append(RejectedItem(candidate=text[:120], reason=str(exc)))
            continue

        existing = registry.get(pattern.pattern_id)
        if existing is None:
            if dry_run:
                report.imported += 1
                continue
            try:
                registry.register(pattern)
                report.imported += 1
            except PatternRegistryError as exc:
                report.rejected += 1
                report.rejected_items.append(RejectedItem(candidate=text[:120], reason=str(exc)))
            continue

        existing_markers = parse_preconditions(existing.preconditions)
        new_markers = parse_preconditions(pattern.preconditions)
        if existing_markers.get("dataset_hash") == new_markers.get("dataset_hash"):
            # Same pattern, same evidence snapshot already imported: idempotent no-op.
            report.skipped_duplicate += 1
        else:
            # Registry forbids CANDIDATE -> CANDIDATE re-registration, so a changed
            # source snapshot for an already-imported pattern_id must be rejected
            # (never silently overwritten) and flagged for manual VERIFIED/REJECTED
            # review instead.
            report.rejected += 1
            report.rejected_items.append(
                RejectedItem(
                    candidate=text[:120],
                    reason=(
                        f"pattern_id {pattern.pattern_id} already registered with a different dataset_hash "
                        f"({existing_markers.get('dataset_hash')} != {new_markers.get('dataset_hash')}); "
                        "CANDIDATE->CANDIDATE re-registration is not an allowed transition — manual "
                        "VERIFIED/REJECTED review required, registry left untouched"
                    ),
                )
            )

    current = registry.current()
    status_counts: Dict[str, int] = {}
    for pattern in current.values():
        status_counts[pattern.status.value] = status_counts.get(pattern.status.value, 0) + 1
    report.registry_status_counts = status_counts
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Import verified Instagram broad-learning candidates into the existing Pattern Registry."
        )
    )
    parser.add_argument(
        "--registry-path",
        type=Path,
        default=DEFAULT_REGISTRY_PATH,
        help=f"pattern registry JSONL path (default: {DEFAULT_REGISTRY_PATH})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="compute the import plan and print the report without writing to the registry",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    dataset_hash = compute_dataset_hash(RAW_OBSERVATIONS_PATH)
    raw_urls = load_raw_urls(RAW_OBSERVATIONS_PATH)
    candidates = load_candidates(LEARNING_CANDIDATES_PATH)

    registry = PatternRegistry(args.registry_path)
    report = run_import(
        registry,
        candidates,
        dataset_hash=dataset_hash,
        raw_urls=raw_urls,
        dry_run=args.dry_run,
    )

    output = report.to_dict()
    output["dataset_hash"] = dataset_hash
    output["import_version"] = IMPORT_VERSION
    output["dry_run"] = args.dry_run
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
