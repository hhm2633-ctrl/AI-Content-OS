"""Select bounded per-account finalists from the owner-ranked review queue.

This is a data-only bridge. It preserves every reviewed candidate, reuses the
conservative same-event clusterer, and treats Brand Connect as an optional
positive tie-break for account C. Missing signals are recorded, never invented.
"""

from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Mapping, Sequence

from modules.source_intake.same_event_topic_clusterer import run_same_event_topic_clustering


SCHEMA_VERSION = "cardnews_final_selection_v1"
ACCOUNTS = ("A", "B", "C")
GRADES = {"1": 0, "2": 1, "3": 2}
TOPIC_STOPWORDS = {
    "출시", "예고", "개최", "공개", "근황", "최신", "직접", "이유", "이렇게", "요즘",
    "담은", "선보였다", "나왔다", "없었다", "있었다", "관련", "소식", "포토",
    "리뷰", "2027", "남성복", "컬렉션", "이탈리아", "럭셔리", "주제로",
}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _commerce_score(annotation: Mapping[str, Any]) -> float:
    if _text(annotation.get("commerce_status")) != "matched":
        return 0.0
    value = annotation.get("commerce_fit")
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return max(0.0, float(value))
    return 1.0


def _rank_key(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        GRADES[_text(candidate.get("grade"))],
        -float(candidate.get("commerce_tie_break") or 0.0),
        -int(candidate.get("observed_source_count") or 0),
        int(candidate.get("owner_queue_index") or 0),
        _text(candidate.get("candidate_id")),
    )


def _category_bucket(account: str, category: str) -> str:
    lowered = category.lower()
    if account == "C":
        return "fashion" if "패션" in category else "beauty"
    if account == "B":
        return "entertainment" if any(token in category for token in ("연예", "도파민")) else "relationship_story"
    if any(token in category for token in ("사회", "사건", "사고", "국내", "국제")):
        return "news_incident"
    return lowered or "unknown"


def _topic_terms(title: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[0-9A-Za-z가-힣]+", title)
        if len(token) >= 2 and token.lower() not in TOPIC_STOPWORDS
    }


def _supplemental_same_topic(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    """Catch obvious same-product/event headlines missed by the conservative clusterer."""

    a = _topic_terms(_text(left.get("title")))
    b = _topic_terms(_text(right.get("title")))
    common = a & b
    if len(common) < 3:
        return False
    union = a | b
    return bool(union) and len(common) / len(union) >= 0.25


def _closed(reason_code: str, reason: str) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "closed",
        "reason_code": reason_code,
        "reason": reason,
        "accounts": {account: {"selected": [], "not_selected": []} for account in ACCOUNTS},
        "selected_count": 0,
        "candidate_count": 0,
        "execution_enabled": False,
        "network_executed": False,
        "link_issuance": False,
        "publishing": False,
    }


def select_owner_ranked_final_candidates(
    owner_queue: Any,
    brandconnect_stage: Any,
    *,
    per_account_limit: int = 4,
    category_soft_limit: int = 2,
) -> Dict[str, Any]:
    """Return per-account finalists without starting discovery or publishing."""

    if not isinstance(owner_queue, Mapping) or owner_queue.get("schema_version") != "owner_ranked_deep_dive_queue_v1":
        return _closed("invalid_owner_queue", "owner-ranked queue schema is required")
    requests = owner_queue.get("requests")
    if not isinstance(requests, list):
        return _closed("invalid_owner_requests", "owner-ranked requests must be a list")
    if not isinstance(per_account_limit, int) or per_account_limit < 1:
        return _closed("invalid_limit", "per_account_limit must be a positive integer")

    annotations = {}
    if isinstance(brandconnect_stage, Mapping):
        for value in brandconnect_stage.get("annotations", []):
            if isinstance(value, Mapping) and _text(value.get("candidate_id")):
                annotations[_text(value.get("candidate_id"))] = copy.deepcopy(dict(value))

    prepared: Dict[str, List[Dict[str, Any]]] = {account: [] for account in ACCOUNTS}
    excluded: List[Dict[str, Any]] = []
    for index, raw in enumerate(requests):
        if not isinstance(raw, Mapping):
            excluded.append({"owner_queue_index": index, "reason_code": "candidate_must_be_object"})
            continue
        candidate_id = _text(raw.get("candidate_id"))
        account = _text(raw.get("account")).upper()
        grade = _text(raw.get("grade"))
        title = _text(raw.get("title"))
        if not candidate_id or account not in ACCOUNTS or grade not in GRADES or not title:
            excluded.append(
                {
                    "candidate_id": candidate_id or None,
                    "account": account or None,
                    "grade": grade or None,
                    "owner_queue_index": index,
                    "reason_code": "invalid_or_excluded_owner_label",
                }
            )
            continue
        annotation = annotations.get(candidate_id, {})
        source_urls = [
            _text(url) for url in raw.get("source_urls", []) if isinstance(url, str) and _text(url)
        ]
        commerce_tie_break = _commerce_score(annotation) if account == "C" else 0.0
        prepared[account].append(
            {
                "request_id": _text(raw.get("request_id")),
                "candidate_id": candidate_id,
                "account": account,
                "category": _text(raw.get("category")) or "unknown",
                "title": title,
                "grade": grade,
                "source_urls": source_urls,
                "requested_media": copy.deepcopy(raw.get("requested_media", [])) if isinstance(raw.get("requested_media"), list) else [],
                "owner_queue_index": index,
                "observed_source_count": len(source_urls),
                "commerce": annotation,
                "commerce_tie_break": commerce_tie_break,
                "category_bucket": _category_bucket(account, _text(raw.get("category")) or "unknown"),
            }
        )

    accounts: Dict[str, Dict[str, Any]] = {}
    total_selected = 0
    duplicate_count = 0
    for account in ACCOUNTS:
        candidates = prepared[account]
        cluster_input = [
            {
                "candidate_id": item["candidate_id"],
                "title": item["title"],
                "category": item["category"],
                "link": item["source_urls"][0] if item["source_urls"] else "",
            }
            for item in candidates
        ]
        cluster_result = run_same_event_topic_clustering(cluster_input)
        cluster_by_id: Dict[str, str] = {}
        cluster_members: Dict[str, List[str]] = {}
        if cluster_result.get("status") == "ok":
            for cluster in cluster_result.get("clusters", []):
                cluster_id = f"{account}:{_text(cluster.get('cluster_id'))}"
                ids = [_text(value) for value in cluster.get("candidate_ids", []) if _text(value)]
                cluster_members[cluster_id] = ids
                for candidate_id in ids:
                    cluster_by_id[candidate_id] = cluster_id

        # Merge conservative clusterer output with an explicit high-overlap
        # headline guard for obvious repeat coverage of the same event/product.
        parents = list(range(len(candidates)))

        def find(position: int) -> int:
            while parents[position] != position:
                parents[position] = parents[parents[position]]
                position = parents[position]
            return position

        def union(left: int, right: int) -> None:
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                parents[right_root] = left_root

        supplemental_edges = 0
        for left in range(len(candidates)):
            for right in range(left + 1, len(candidates)):
                left_id = candidates[left]["candidate_id"]
                right_id = candidates[right]["candidate_id"]
                same_existing_cluster = (
                    left_id in cluster_by_id
                    and right_id in cluster_by_id
                    and cluster_by_id[left_id] == cluster_by_id[right_id]
                )
                supplemental = _supplemental_same_topic(candidates[left], candidates[right])
                if same_existing_cluster or supplemental:
                    union(left, right)
                    if supplemental and not same_existing_cluster:
                        supplemental_edges += 1
        group_ids: Dict[int, str] = {}
        for index, item in enumerate(candidates):
            root = find(index)
            group_ids.setdefault(root, f"{account}:cluster:{len(group_ids):04d}")
            item["cluster_id"] = group_ids[root]

        representatives: List[Dict[str, Any]] = []
        not_selected: List[Dict[str, Any]] = []
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for item in candidates:
            grouped.setdefault(item["cluster_id"], []).append(item)
        for cluster_id, members in grouped.items():
            ranked_members = sorted(members, key=_rank_key)
            representatives.append(ranked_members[0])
            for duplicate in ranked_members[1:]:
                duplicate_count += 1
                not_selected.append(
                    {
                        **copy.deepcopy(duplicate),
                        "selection_status": "not_selected",
                        "reason_code": "same_event_or_topic_duplicate",
                        "kept_candidate_id": ranked_members[0]["candidate_id"],
                    }
                )

        ranked = sorted(representatives, key=_rank_key)
        selected: List[Dict[str, Any]] = []
        deferred: List[Dict[str, Any]] = []
        category_counts: Dict[str, int] = {}
        # A soft diversity rule may reorder candidates inside the same owner
        # grade, but it must never promote a lower grade ahead of an available
        # higher-grade candidate.
        for grade in ("1", "2", "3"):
            grade_items = [item for item in ranked if item["grade"] == grade]
            grade_deferred: List[Dict[str, Any]] = []
            for item in grade_items:
                bucket = item["category_bucket"]
                category_full = category_counts.get(bucket, 0) >= category_soft_limit
                if len(selected) < per_account_limit and not category_full:
                    selected.append(item)
                    category_counts[bucket] = category_counts.get(bucket, 0) + 1
                else:
                    grade_deferred.append(item)
            if len(selected) < per_account_limit:
                # Fill from the same grade before considering the next grade.
                for item in grade_deferred:
                    if len(selected) >= per_account_limit:
                        break
                    selected.append(item)
                    bucket = item["category_bucket"]
                    category_counts[bucket] = category_counts.get(bucket, 0) + 1
            deferred.extend(item for item in grade_deferred if item not in selected)
            if len(selected) >= per_account_limit:
                deferred.extend(item for item in ranked if GRADES[item["grade"]] > GRADES[grade])
                break
        if len(selected) < per_account_limit:
            fill = [item for item in deferred if item not in selected][: per_account_limit - len(selected)]
            selected.extend(fill)
            deferred = [item for item in deferred if item not in fill]

        selected_entries: List[Dict[str, Any]] = []
        for rank, item in enumerate(selected, 1):
            reasons = ["owner_grade_priority", "same_event_deduplicated", "account_category_balance"]
            if account == "C" and item["commerce_tie_break"] > 0:
                reasons.append("natural_brandconnect_match_used_as_same_grade_tiebreak")
            selected_entries.append(
                {
                    **copy.deepcopy(item),
                    "rank": rank,
                    "selection_status": "selected",
                    "selection_reasons": reasons,
                }
            )
        for item in deferred:
            not_selected.append(
                {
                    **copy.deepcopy(item),
                    "selection_status": "not_selected",
                    "reason_code": "per_account_limit_reached",
                }
            )
        not_selected.sort(key=lambda item: int(item.get("owner_queue_index") or 0))
        total_selected += len(selected_entries)
        accounts[account] = {
            "candidate_count": len(candidates),
            "selected_count": len(selected_entries),
            "not_selected_count": len(not_selected),
            "selected": selected_entries,
            "not_selected": not_selected,
            "cluster_summary": {
                **copy.deepcopy(cluster_result.get("summary", {})),
                "supplemental_high_overlap_edge_count": supplemental_edges,
                "final_cluster_count": len(group_ids),
            },
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "selected" if total_selected else "closed",
        "reason_code": "ok" if total_selected else "no_candidates_selected",
        "source_schema_version": owner_queue.get("schema_version"),
        "brandconnect_schema_version": brandconnect_stage.get("schema_version") if isinstance(brandconnect_stage, Mapping) else None,
        "selection_policy": {
            "per_account_limit": per_account_limit,
            "limit_status": "owner_operating_hypothesis_not_permanent_rule",
            "category_soft_limit": category_soft_limit,
            "commerce_scope": "account_C_same_grade_positive_tiebreak_only",
            "matched_product_use_is_optional_not_forced": True,
            "unmatched_or_editorial_bypass_penalty": False,
            "cross_account_entertainment_overlap_allowed": True,
        },
        "missing_signals_not_imputed": [
            "freshness_or_event_time",
            "public_reaction_metrics",
            "verified_media_availability",
            "previous_published_topic_history",
        ],
        "requested_media_is_plan_not_verified_availability": True,
        "candidate_count": sum(len(values) for values in prepared.values()),
        "selected_count": total_selected,
        "not_selected_count": sum(bucket["not_selected_count"] for bucket in accounts.values()),
        "duplicate_suppressed_count": duplicate_count,
        "excluded_invalid_or_ungraded": excluded,
        "accounts": accounts,
        "execution_enabled": False,
        "network_executed": False,
        "link_issuance": False,
        "publishing": False,
    }


__all__ = ["SCHEMA_VERSION", "select_owner_ranked_final_candidates"]
