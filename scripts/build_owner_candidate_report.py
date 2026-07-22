"""Build a lossless owner-review Markdown report from collection artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple


CATEGORY_VALUE_ALIASES = {
    "\uacbd\uc81c": "economy",
}

UNUSABLE_CATEGORY_VALUES = {
    "uncategorized",
    "unknown",
    "\ubbf8\ubd84\ub958",
}

GENERIC_NEWS_SOURCE_IDS = {
    "naver_news",
    "daum_news",
    "nate_news_rank",
    "news1",
    "newsis",
    "yonhap",
}

ECONOMY_SOURCE_IDS = {
    "edaily",
    "hankyung_economy",
    "mk_economy",
    "moneytoday",
}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _first(*values: Any) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _category_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        values = [entry.strip() for entry in value if isinstance(entry, str) and entry.strip()]
        return values[-1] if values else ""
    return ""


def _report_category(item: Mapping[str, Any], match: Mapping[str, Any]) -> str:
    category = _first(
        match.get("primary_category"),
        match.get("category"),
        match.get("raw_category"),
        item.get("primary_category"),
        item.get("category"),
        item.get("board_or_category"),
        item.get("category_slug"),
    )
    if category.casefold() in UNUSABLE_CATEGORY_VALUES:
        category = ""
    if not category:
        category = _first(
            item.get("primary_category"),
            item.get("category"),
            item.get("board_or_category"),
            item.get("category_slug"),
        )
    if category.casefold() in UNUSABLE_CATEGORY_VALUES:
        category = ""
    if not category:
        category = _category_text(item.get("category_path"))
    if not category and item.get("source_type") == "news_economy":
        category = "economy"
    if not category and item.get("source_id") in ECONOMY_SOURCE_IDS:
        category = "economy"
    if not category and item.get("source_id") in GENERIC_NEWS_SOURCE_IDS:
        category = "news"
    return CATEGORY_VALUE_ALIASES.get(category, category) or "uncategorized"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _pipeline_title_objects(value: Any) -> Iterable[Tuple[Mapping[str, Any], Tuple[str, ...]]]:
    stack: list[Tuple[Any, Tuple[str, ...]]] = [(value, ())]
    while stack:
        current, trail = stack.pop()
        if isinstance(current, Mapping):
            if _text(current.get("title")):
                yield current, trail
            stack.extend((child, trail + (str(key),)) for key, child in current.items())
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            stack.extend((child, trail + (str(index),)) for index, child in enumerate(current))


def _accounting_ledger(pipeline: Any) -> Dict[int, Mapping[str, Any]]:
    if not isinstance(pipeline, Mapping):
        return {}
    preservation = pipeline.get("candidate_preservation")
    if not isinstance(preservation, Mapping):
        return {}
    ledger = preservation.get("ledger")
    if not isinstance(ledger, list):
        return {}
    return {
        entry["input_index"]: entry
        for entry in ledger
        if isinstance(entry, Mapping)
        and isinstance(entry.get("input_index"), int)
        and not isinstance(entry.get("input_index"), bool)
    }


def _best_pipeline_match(
    matches: Sequence[Tuple[Mapping[str, Any], Tuple[str, ...]]],
) -> Tuple[Mapping[str, Any], Tuple[str, ...]]:
    if not matches:
        return {}, ()
    return max(
        matches,
        key=lambda entry: (
            bool(_text(entry[0].get("account_id") or entry[0].get("account"))),
            "account_routing" in entry[1],
            "top_selection" in entry[1],
        ),
    )


def build_report(raw_path: Path, pipeline_path: Path, output_path: Path) -> Dict[str, Any]:
    raw = _load(raw_path)
    pipeline = _load(pipeline_path)
    accounting = _accounting_ledger(pipeline)
    classified = list(_pipeline_title_objects(pipeline))
    by_url: Dict[str, list[Tuple[Mapping[str, Any], Tuple[str, ...]]]] = defaultdict(list)
    by_title: Dict[str, list[Tuple[Mapping[str, Any], Tuple[str, ...]]]] = defaultdict(list)

    for candidate, trail in classified:
        urls = list(candidate.get("urls")) if isinstance(candidate.get("urls"), list) else []
        urls.extend(candidate.get(key) for key in ("url", "link"))
        for url in urls:
            text = _text(url)
            if text:
                by_url[text].append((candidate, trail))
        by_title[_text(candidate.get("title"))].append((candidate, trail))

    groups: Dict[str, list[Tuple[int, str, str, str, str, str, str, str]]] = defaultdict(list)
    uncategorized_sources: Counter[str] = Counter()
    items = raw.get("items") if isinstance(raw, Mapping) else []
    if not isinstance(items, list):
        raise ValueError("raw collection items must be a list")

    for index, item in enumerate(items, start=1):
        if not isinstance(item, Mapping):
            groups["malformed"].append((
                index, "(non-object item)", "", "unknown", "unassigned",
                "raw malformed", "excluded", "candidate_must_be_object",
            ))
            continue
        title = _first(item.get("title"), item.get("keyword"), item.get("headline")) or "(untitled)"
        url = _first(item.get("url"), item.get("link"))
        matches = by_url.get(url, []) or by_title.get(title, [])
        match, trail = _best_pipeline_match(matches)
        category = _report_category(item, match)
        account = _first(match.get("account_id"), match.get("account"), item.get("account_portfolio")) or "unassigned"
        stage = "/".join(trail[-4:]) if trail else "no_pipeline_match"
        source = _first(item.get("source_id")) or "unknown"
        ledger_entry = accounting.get(index - 1, {})
        disposition = _first(ledger_entry.get("disposition")) or "held"
        reason_code = _first(ledger_entry.get("reason_code")) or "stage1_accounting_not_observed"
        groups[category].append((
            index, title, url, source, account, stage, disposition, reason_code,
        ))
        if category == "uncategorized":
            uncategorized_sources[source] += 1

    reported_count = sum(len(rows) for rows in groups.values())
    if reported_count != len(items):
        raise RuntimeError(f"lossless report invariant failed: raw={len(items)} reported={reported_count}")

    lines = [
        "# 2026-07-22 News and Economy Owner Review",
        "",
        f"- Raw file: `{raw_path}`",
        f"- Routing file: `{pipeline_path}`",
        f"- Raw item count: **{len(items)}**",
        f"- Reported item count: **{reported_count}**",
        "- Deduplication: not applied",
        "- Candidate visibility: all raw rows are shown, including excluded and held rows",
        "- Deep research, selection, rendering, publishing: not executed",
        "",
    ]
    for category in sorted(groups):
        rows = groups[category]
        lines.extend((f"## {category} ({len(rows)})", ""))
        for index, title, url, source, account, stage, disposition, reason_code in rows:
            lines.append(f"{index}. **{title}**")
            lines.append(f"   - Source: `{source}` / Account: `{account}` / Route: `{stage}`")
            lines.append(f"   - State: `{disposition}` / Reason: `{reason_code}`")
            lines.append(f"   - URL: {url or 'not_observed'}")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "output": str(output_path),
        "raw_item_count": len(items),
        "reported_item_count": reported_count,
        "category_counts": {category: len(groups[category]) for category in sorted(groups)},
        "uncategorized_sources": dict(sorted(uncategorized_sources.items())),
        "pipeline_title_objects_seen": len(classified),
        "candidate_state_counts": dict(sorted(Counter(
            row[6] for rows in groups.values() for row in rows
        ).items())),
        "stage1_accounting_rows_seen": len(accounting),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--pipeline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_report(args.raw, args.pipeline, args.output)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
