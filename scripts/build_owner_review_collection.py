"""Merge deterministic account fragments into the local owner-review collection."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping


CATEGORY_NAMES = {
    "domestic_news": "국내뉴스",
    "world_news": "세계뉴스",
    "incident_society": "사건·사회",
    "economy": "경제·생활",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _first_text(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            text = _text(item)
            if text:
                return text
        return ""
    return _text(value)


def _urls(value: Mapping[str, Any]) -> list[str]:
    raw = value.get("urls")
    if not isinstance(raw, list):
        raw = [value.get("url") or value.get("link")]
    return list(dict.fromkeys(_text(item) for item in raw if _text(item)))


def _fragment_rows(fragment: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    rows = fragment.get("candidates")
    if not isinstance(rows, list):
        rows = fragment.get("items")
    return (item for item in rows or [] if isinstance(item, Mapping))


def _raw_url_index(raw: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    result: Dict[str, Mapping[str, Any]] = {}
    for item in raw.get("items", []):
        if not isinstance(item, Mapping):
            continue
        url = _text(item.get("url") or item.get("link"))
        if url:
            result[url] = item
    return result


def _observation(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    for field in ("observations", "observed"):
        rows = candidate.get(field)
        if isinstance(rows, list) and rows and isinstance(rows[0], Mapping):
            return rows[0]
    return {}


def _normalize(candidate: Mapping[str, Any], raw_by_url: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    urls = _urls(candidate)
    raw = next((raw_by_url[url] for url in urls if url in raw_by_url), {})
    observation = _observation(candidate)
    dates = observation.get("dates") if isinstance(observation.get("dates"), Mapping) else {}
    context = _first_text(candidate.get("context")) or _text(candidate.get("summary"))
    context = context or _text(raw.get("summary") or raw.get("snippet"))
    source_ids = candidate.get("source_ids") if isinstance(candidate.get("source_ids"), list) else []
    source_ids = list(dict.fromkeys(_text(item) for item in source_ids if _text(item)))
    if not source_ids and _text(raw.get("source_id")):
        source_ids = [_text(raw.get("source_id"))]
    visible_metrics = raw.get("visible_metrics") if isinstance(raw.get("visible_metrics"), Mapping) else {}
    reaction_values = []
    for field in ("comments", "likes"):
        value = raw.get(field)
        if value is None:
            value = visible_metrics.get(field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            reaction_values.append(max(0, int(value)))
    media_flags = raw.get("media_flags") if isinstance(raw.get("media_flags"), Mapping) else {}
    media_count = media_flags.get("image_count")
    if not isinstance(media_count, int):
        media_count = 1 if raw.get("thumbnail_url") or raw.get("has_images") is True else None
    candidate_id = _text(candidate.get("id") or candidate.get("candidate_id"))
    account = _text(candidate.get("account")).upper()
    category = CATEGORY_NAMES.get(_text(candidate.get("category")), _text(candidate.get("category")) or "미분류")
    return {
        "account": account,
        "category": category,
        "raw_category": _text(candidate.get("category")) or category,
        "id": candidate_id,
        "title": _text(candidate.get("title")),
        "context": context[:500],
        "published_at": (
            _first_text(candidate.get("published_at"))
            or _text(dates.get("published_at_iso") or dates.get("published_at"))
            or _text(observation.get("published_at"))
            or _text(raw.get("published_at") or raw.get("visible_date"))
        ),
        "collected_at": (
            _first_text(candidate.get("collected_at"))
            or _text(dates.get("collected_at"))
            or _text(observation.get("collected_at"))
            or _text(raw.get("collected_at"))
        ),
        "urls": urls,
        "source_ids": source_ids,
        "source_count": len(source_ids),
        "rank_position": candidate.get("rank_position") or raw.get("rank_position") or raw.get("rank"),
        "reaction_count": sum(reaction_values) if reaction_values else None,
        "media_count": media_count,
        "status": "OWNER_UNLABELED",
        "selection_stage": "daily_shallow_all_visible",
    }


def _reason_index(fragments: Iterable[Mapping[str, Any]]) -> Dict[str, list[str]]:
    result: Dict[str, list[str]] = defaultdict(list)
    for fragment in fragments:
        ledgers = []
        for field in ("exclusions", "exclusion_ledger", "reject_ledger"):
            if isinstance(fragment.get(field), list):
                ledgers.extend(fragment[field])
        for entry in ledgers:
            if not isinstance(entry, Mapping):
                continue
            reason = _text(entry.get("reason") or entry.get("reason_code")) or "outside_account_portfolio"
            refs = entry.get("item_refs") if isinstance(entry.get("item_refs"), list) else [entry]
            for ref in refs:
                if not isinstance(ref, Mapping):
                    continue
                url = _text(ref.get("url") or ref.get("link"))
                if url and reason not in result[url]:
                    result[url].append(reason)
    return result


def build_collection(raw_path: Path, fragment_root: Path, output_path: Path) -> Dict[str, Any]:
    raw = _load(raw_path)
    fragments = [_load(fragment_root / f"fragment_{account}.json") for account in "ABC"]
    raw_by_url = _raw_url_index(raw)
    normalized = [
        _normalize(candidate, raw_by_url)
        for fragment in fragments
        for candidate in _fragment_rows(fragment)
    ]
    candidates = []
    seen = set()
    for candidate in normalized:
        key = candidate["id"] or (candidate["account"], candidate["title"])
        if key in seen:
            continue
        seen.add(key)
        candidates.append(candidate)
    candidates.sort(key=lambda item: (item["account"], item["category"], item["published_at"] or "", item["title"]), reverse=False)

    represented_urls = {url for candidate in candidates for url in candidate["urls"]}
    reasons = _reason_index(fragments)
    unassigned = []
    for url, item in raw_by_url.items():
        if url in represented_urls:
            continue
        unassigned.append({
            "source_id": _text(item.get("source_id")),
            "title": _text(item.get("title")),
            "url": url,
            "reasons": reasons.get(url, ["not_routed_to_current_account_portfolios"]),
            "is_fallback": item.get("is_fallback") is True,
        })
    source_counts = Counter(source for item in candidates for source in item["source_ids"])
    account_counts = Counter(item["account"] for item in candidates)
    category_counts = Counter(f"{item['account']}:{item['category']}" for item in candidates)
    output = {
        "schema_version": "owner_cardnews_latest_collection_v1",
        "as_of": datetime.now().astimezone().isoformat(),
        "raw_collection_file": str(raw_path).replace("\\", "/"),
        "raw_item_count": len(raw.get("items", [])),
        "candidate_count": len(candidates),
        "account_counts": dict(account_counts),
        "category_counts": dict(category_counts),
        "candidates": candidates,
        "unassigned_items": unassigned,
        "unassigned_count": len(unassigned),
        "source_counts": dict(source_counts),
        "coverage_note": "All deterministic A/B/C portfolio candidates are visible; unrouted raw items remain in unassigned_items with reasons.",
        "owner_labels_applied": False,
        "deep_research_executed": False,
        "render_executed": False,
        "publishing_executed": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--fragment-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_collection(args.raw, args.fragment_root, args.output)
    print(json.dumps({
        "output": str(args.output),
        "candidate_count": result["candidate_count"],
        "account_counts": result["account_counts"],
        "category_counts": result["category_counts"],
        "unassigned_count": result["unassigned_count"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
