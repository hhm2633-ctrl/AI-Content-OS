from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence


def _bump(counter: Dict[str, int], key: Any) -> None:
    key = key if isinstance(key, str) and key else "unknown"
    counter[key] = counter.get(key, 0) + 1


def compute_statistics(posts: Sequence[Dict[str, Any]], classifications: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    posts = list(posts or [])
    classifications = list(classifications or [])

    post_type_distribution: Dict[str, int] = {}
    caption_lengths: List[int] = []
    hashtag_counts: List[int] = []
    accounts = set()

    for post in posts:
        if not isinstance(post, dict):
            continue
        _bump(post_type_distribution, post.get("post_type"))
        if post.get("account_handle"):
            accounts.add(post["account_handle"])
        if post.get("caption_text") is not None:
            caption_lengths.append(post.get("caption_length") or 0)
        if isinstance(post.get("hashtag_count"), int):
            hashtag_counts.append(post["hashtag_count"])

    hook_distribution: Dict[str, int] = {}
    cta_distribution: Dict[str, int] = {}
    pattern_distribution: Dict[str, int] = {}
    unknown_counts = {"hook": 0, "cta": 0, "pattern": 0}

    for item in classifications:
        if not isinstance(item, dict):
            continue
        hook = (item.get("hook") or {}).get("value")
        cta = (item.get("cta") or {}).get("value")
        pattern = (item.get("pattern") or {}).get("value")
        _bump(hook_distribution, hook)
        _bump(cta_distribution, cta)
        _bump(pattern_distribution, pattern)
        if hook == "unknown":
            unknown_counts["hook"] += 1
        if cta == "unknown":
            unknown_counts["cta"] += 1
        if pattern == "unknown":
            unknown_counts["pattern"] += 1

    def _avg(values: List[int]) -> float:
        return round(sum(values) / len(values), 2) if values else 0.0

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_posts": len(posts),
        "total_accounts": len(accounts),
        "post_type_distribution": post_type_distribution,
        "hook_distribution": hook_distribution,
        "cta_distribution": cta_distribution,
        "pattern_distribution": pattern_distribution,
        "unknown_counts": unknown_counts,
        "caption_length_avg": _avg(caption_lengths),
        "caption_length_observed_count": len(caption_lengths),
        "hashtag_count_avg": _avg(hashtag_counts),
    }
