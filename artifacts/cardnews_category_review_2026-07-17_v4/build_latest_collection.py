from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parents[1]
sys.path.insert(0, str(REPOSITORY))

from modules.trend_collector.naver_api_hub_client import NaverApiHubClient


SHALLOW = REPOSITORY / "storage/source_intake/2026-07-17/daily_shallow_collection.json"
OUTPUT = ROOT / "collection.json"
KST = timezone(timedelta(hours=9))

NEWS_SOURCES = {
    "daum_news", "hankyung_economy", "mk_economy", "moneytoday", "edaily",
    "yonhap", "newsis", "news1",
}
ECONOMY_SOURCES = {"hankyung_economy", "mk_economy", "moneytoday", "edaily"}
COMMUNITY_SOURCES = {"nate_pann", "fmkorea", "bobaedream"}
FASHION_BEAUTY_SOURCES = {
    "fashionn", "fashionbiz", "apparelnews", "allure_beauty", "vogue_beauty",
    "wkorea_beauty", "gq_grooming",
}
NAVER_QUERIES = (
    ("A", "사회·사건", "사건 사고"),
    ("A", "사회·이슈", "사회 이슈"),
    ("B", "연예·도파민", "연예 뉴스"),
    ("B", "연애·관계", "연애 결혼"),
    ("C", "패션", "패션 신제품"),
    ("C", "뷰티·메이크업", "메이크업 신제품"),
    ("C", "뷰티·향수", "향수 신제품"),
)


def clean(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("새 창 열림", "")
    return re.sub(r"\s+", " ", text).strip()


def readable_korean(text: str) -> bool:
    if not text:
        return False
    visible = [char for char in text if not char.isspace()]
    if not visible:
        return False
    valid = sum(char.isalnum() or "가" <= char <= "힣" or char in ".,!?·'\"()[]-_:…%" for char in visible)
    return valid / len(visible) >= 0.82


def canonical_title(title: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", title.lower())


def item_url(item: dict[str, Any]) -> str:
    return clean(item.get("link") or item.get("url"))


def b_category(item: dict[str, Any]) -> str:
    text = f"{clean(item.get('title'))} {clean(item.get('summary'))}"
    if re.search(r"남편|아내|결혼|이혼|연애|남친|여친|썸|소개팅|시댁|처가|재혼|바람|데이트", text):
        return "연애·관계"
    if re.search(r"직장|회사|가족|부모|자녀|친구|상사|동료", text):
        return "현실썰"
    return "연예·도파민"


def c_category(item: dict[str, Any]) -> str:
    vertical = clean(item.get("account_c_vertical")).lower()
    raw = clean(item.get("category") or item.get("section_category")).lower()
    title = clean(item.get("title")).lower()
    if vertical == "fashion" or item.get("source_id") in {"fashionn", "fashionbiz", "apparelnews"}:
        return "패션"
    if "hair" in raw or "헤어" in title or "머리" in title:
        return "뷰티·헤어"
    if "makeup" in raw or "메이크업" in title:
        return "뷰티·메이크업"
    if "fragrance" in raw or "향수" in title or "향기" in title:
        return "뷰티·향수"
    if "skincare" in raw or "스킨" in title or "피부" in title:
        return "뷰티·스킨케어"
    return "뷰티"


def a_category(item: dict[str, Any]) -> str:
    raw = clean(item.get("category") or item.get("board_or_category")).lower()
    title = clean(item.get("title"))
    if "world" in raw:
        return "세계뉴스"
    if "politic" in raw:
        return "국내정치"
    if "society" in raw:
        return "사회·사건"
    if re.search(r"축구|야구|농구|배구|올림픽|월드컵|선수|경기", title):
        return "생활·스포츠"
    if re.search(r"대통령|국회|여당|야당|민주당|국민의힘|후보|장관|정치", title):
        return "국내정치"
    if item.get("source_id") in ECONOMY_SOURCES:
        return "경제·생활"
    return "국내외 뉴스"


def context_for(item: dict[str, Any]) -> str:
    summary = clean(item.get("summary") or item.get("snippet"))
    if summary:
        return summary[:240]
    publisher = clean(item.get("publisher") or item.get("source_name") or item.get("source_id"))
    rank = item.get("rank_position") or item.get("rank")
    return f"{publisher} 공개 목록{f' {rank}위' if rank else ''}. 원문을 열어 세부 내용을 확인할 후보입니다."


def public_reaction(item: dict[str, Any]) -> int | None:
    values = []
    for key in ("comments", "comment_count", "likes", "recommend_count"):
        value = item.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values.append(max(0, int(value)))
    return sum(values) if values else None


def media_count(item: dict[str, Any]) -> int | None:
    flags = item.get("media_flags") if isinstance(item.get("media_flags"), dict) else {}
    count = flags.get("image_count")
    if isinstance(count, int) and not isinstance(count, bool):
        return max(0, count)
    if item.get("has_images") is True or flags.get("has_image") is True or item.get("thumbnail_url"):
        return 1
    return None


def stable_id(account: str, title: str) -> str:
    digest = hashlib.sha1(f"{account}|{canonical_title(title)}".encode("utf-8")).hexdigest()[:12]
    return f"20260717-2003-{account}-{digest}"


def candidate_from_item(item: dict[str, Any], account: str, category: str) -> dict[str, Any]:
    title = clean(item.get("title") or item.get("keyword"))
    published = clean(item.get("published_at") or item.get("published_date") or item.get("visible_date"))
    result = {
        "account": account,
        "category": category,
        "raw_category": clean(item.get("category") or item.get("board_or_category")) or category,
        "id": stable_id(account, title),
        "title": title,
        "context": context_for(item),
        "published_at": published,
        "collected_at": clean(item.get("collected_at")),
        "urls": [item_url(item)],
        "source_ids": [clean(item.get("source_id"))],
        "source_count": 1,
        "rank_position": item.get("rank_position") or item.get("rank"),
        "reaction_count": public_reaction(item),
        "media_count": media_count(item),
        "status": "OWNER_UNLABELED",
        "selection_stage": "bounded_source_window",
    }
    return result


def naver_candidates(exclusions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    client = NaverApiHubClient(timeout=8)
    results: list[dict[str, Any]] = []
    for account, category, query in NAVER_QUERIES:
        response = client.search_news(query=query, display=5, sort="date")
        if response.get("status") != "ok":
            exclusions.append({
                "source_id": "naver_api_hub",
                "query": query,
                "reason": response.get("error_type") or "naver_query_failed",
                "safe_message": response.get("safe_message") or "",
            })
            continue
        for rank, raw in enumerate(response.get("items", []), 1):
            item = {
                "source_id": "naver_api_hub",
                "source_name": "네이버 뉴스 검색",
                "title": raw.get("title"),
                "summary": raw.get("description"),
                "link": raw.get("link"),
                "published_at": raw.get("pubDate"),
                "collected_at": datetime.now(KST).isoformat(),
                "rank_position": rank,
            }
            candidate = candidate_from_item(item, account, category)
            candidate["query"] = query
            candidate["selection_stage"] = "naver_latest_supplement"
            results.append(candidate)
    return results


def merge_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for candidate in candidates:
        key = (candidate["account"], canonical_title(candidate["title"]))
        if key not in merged:
            merged[key] = candidate
            continue
        current = merged[key]
        current["urls"] = list(dict.fromkeys(current["urls"] + candidate["urls"]))
        current["source_ids"] = list(dict.fromkeys(current["source_ids"] + candidate["source_ids"]))
        current["source_count"] = len(current["source_ids"])
        current["duplicate_group"] = f"exact:{current['id']}"
        if candidate.get("reaction_count") is not None:
            current["reaction_count"] = max(current.get("reaction_count") or 0, candidate["reaction_count"])
        if candidate.get("media_count") is not None:
            current["media_count"] = max(current.get("media_count") or 0, candidate["media_count"])
    return list(merged.values())


def main() -> None:
    payload = json.loads(SHALLOW.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    candidates: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    per_source_seen: Counter[str] = Counter()

    for item in items:
        source_id = clean(item.get("source_id"))
        title = clean(item.get("title") or item.get("keyword"))
        url = item_url(item)
        reason = ""
        if not title or not url:
            reason = "missing_title_or_url"
        elif item.get("is_fallback") is True:
            reason = "cached_or_fallback_not_current"
        elif not readable_korean(title):
            reason = "unreadable_text_encoding"
        elif source_id == "naver_news":
            reason = "default_ai_automation_query_replaced_by_cardnews_queries"
        elif source_id in NEWS_SOURCES:
            if per_source_seen[source_id] >= 4:
                reason = "outside_news_source_top4_review_window"
            else:
                per_source_seen[source_id] += 1
                account = "B" if clean(item.get("category")).lower() in {"culture", "entertainment"} else "A"
                category = b_category(item) if account == "B" else a_category(item)
                candidates.append(candidate_from_item(item, account, category))
        elif source_id in COMMUNITY_SOURCES:
            if per_source_seen[source_id] >= 10:
                reason = "outside_community_source_top10_review_window"
            else:
                per_source_seen[source_id] += 1
                candidates.append(candidate_from_item(item, "B", b_category(item)))
        elif source_id in FASHION_BEAUTY_SOURCES:
            if per_source_seen[source_id] >= 5:
                reason = "outside_fashion_beauty_source_top5_review_window"
            else:
                per_source_seen[source_id] += 1
                candidates.append(candidate_from_item(item, "C", c_category(item)))
        else:
            reason = "source_not_in_current_account_portfolios"

        if reason:
            exclusions.append({
                "source_id": source_id,
                "title": title,
                "url": url,
                "reason": reason,
            })

    candidates.extend(naver_candidates(exclusions))
    candidates = merge_candidates(candidates)
    candidates.sort(key=lambda item: (item["account"], item["category"], item.get("rank_position") or 999, item["title"]))
    source_counts = Counter(source for item in candidates for source in item.get("source_ids", []))
    account_counts = Counter(item["account"] for item in candidates)
    output = {
        "schema_version": "owner_cardnews_latest_collection_v1",
        "as_of": datetime.now(KST).isoformat(),
        "raw_collection_file": str(SHALLOW.relative_to(REPOSITORY)).replace("\\", "/"),
        "raw_item_count": len(items),
        "candidate_count": len(candidates),
        "account_counts": dict(account_counts),
        "candidates": candidates,
        "exclusion_ledger": exclusions,
        "exclusion_count": len(exclusions),
        "source_counts": dict(source_counts),
        "coverage_note": (
            "원수집 전체를 보존하고 뉴스 소스당 상위 4건, 커뮤니티 소스당 상위 10건, "
            "패션·뷰티 소스당 상위 5건과 계정별 네이버 최신 검색을 소유자 검토창에 노출. "
            "캐시·깨진 문자열·기본 AI 검색 결과·창 밖 항목은 exclusion_ledger에 사유와 함께 보존."
        ),
        "owner_labels_applied": False,
        "publishing_executed": False,
    }
    ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT),
        "raw_item_count": len(items),
        "candidate_count": len(candidates),
        "account_counts": dict(account_counts),
        "exclusion_count": len(exclusions),
        "source_counts": dict(source_counts),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
