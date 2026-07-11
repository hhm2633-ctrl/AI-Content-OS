from typing import Any, Dict, List, Optional, Sequence


def _avg(values: Sequence[Any]) -> Optional[float]:
    numeric = [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
    if not numeric:
        return None
    return round(sum(numeric) / len(numeric), 2)


def _dominant(counts: Dict[str, int]) -> str:
    if not counts:
        return ""
    return max(counts.items(), key=lambda pair: pair[1])[0]


class CompetitorLearningStatistics:
    """
    Competitor Learning Engine - Statistics (Sprint 18).

    Pure computation over CompetitorLearningExtractor's observation list. No
    I/O, no network, no LLM. Never raises: empty/None/malformed input always
    yields safe zeroed structures instead of an exception.
    """

    def compute(self, observations: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        observations = [obs for obs in (observations or []) if isinstance(obs, dict)]

        return {
            "sample_size": len(observations),
            "hook_statistics": self._type_stats(observations, "hook_type", "hook_confidence"),
            "cta_statistics": self._type_stats(observations, "cta_type", "cta_confidence"),
            "pattern_statistics": self._type_stats(observations, "pattern_type", "pattern_confidence"),
            "layout_statistics": self._layout_stats(observations),
            "competitor_statistics": self._competitor_stats(observations),
            "caption_summary": self._caption_summary(observations),
        }

    def _type_stats(
        self,
        observations: List[Dict[str, Any]],
        type_field: str,
        confidence_field: str,
    ) -> Dict[str, Any]:
        distribution: Dict[str, int] = {}
        buckets: Dict[str, Dict[str, List[Any]]] = {}
        unknown_count = 0

        for obs in observations:
            value = obs.get(type_field) or "unknown"
            distribution[value] = distribution.get(value, 0) + 1

            if value == "unknown":
                unknown_count += 1

            bucket = buckets.setdefault(value, {"likes": [], "comments": [], "confidences": []})

            if obs.get("like_count") is not None:
                bucket["likes"].append(obs["like_count"])
            if obs.get("comment_count") is not None:
                bucket["comments"].append(obs["comment_count"])

            confidence = obs.get(confidence_field)
            if isinstance(confidence, (int, float)) and not isinstance(confidence, bool):
                bucket["confidences"].append(confidence)

        top = []
        for value, count in sorted(distribution.items(), key=lambda pair: pair[1], reverse=True):
            bucket = buckets.get(value, {"likes": [], "comments": [], "confidences": []})
            top.append({
                "value": value,
                "count": count,
                "avg_likes": _avg(bucket["likes"]),
                "avg_comments": _avg(bucket["comments"]),
                "avg_confidence": _avg(bucket["confidences"]),
            })

        return {
            "distribution": distribution,
            "top": top,
            "sample_size": len(observations),
            "unknown_count": unknown_count,
        }

    def _layout_stats(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        distribution: Dict[str, int] = {}
        slide_counts: List[Any] = []
        image_counts: List[Any] = []
        buckets: Dict[str, Dict[str, List[Any]]] = {}

        for obs in observations:
            value = obs.get("post_type") or "unknown"
            distribution[value] = distribution.get(value, 0) + 1

            if isinstance(obs.get("slide_count"), (int, float)) and not isinstance(obs.get("slide_count"), bool):
                slide_counts.append(obs["slide_count"])
            if isinstance(obs.get("image_count"), (int, float)) and not isinstance(obs.get("image_count"), bool):
                image_counts.append(obs["image_count"])

            bucket = buckets.setdefault(value, {"likes": [], "comments": []})
            if obs.get("like_count") is not None:
                bucket["likes"].append(obs["like_count"])
            if obs.get("comment_count") is not None:
                bucket["comments"].append(obs["comment_count"])

        top_layouts = []
        for value, count in sorted(distribution.items(), key=lambda pair: pair[1], reverse=True):
            bucket = buckets.get(value, {"likes": [], "comments": []})
            top_layouts.append({
                "value": value,
                "count": count,
                "avg_likes": _avg(bucket["likes"]),
                "avg_comments": _avg(bucket["comments"]),
            })

        return {
            "post_type_distribution": distribution,
            "top_layouts": top_layouts,
            "avg_slide_count": _avg(slide_counts),
            "avg_image_count": _avg(image_counts),
            "sample_size": len(observations),
            "vocabulary_note": (
                "이 값은 Instagram 게시물 형식(carousel/reel/single_image) 분포이며, "
                "CardNews Pattern Engine의 LayoutSelector 어휘(bold_ai/notebook/"
                "dark_editorial/character_diary/talking_head)와는 다른 체계다 - "
                "서로 매핑/치환하지 않는다 (존재하지 않는 대응 관계를 꾸며내지 않기 위함)."
            ),
        }

    def _competitor_stats(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        accounts: Dict[str, Dict[str, Any]] = {}

        for obs in observations:
            handle = obs.get("account_handle") or "unknown"
            account = accounts.setdefault(handle, {
                "post_count": 0,
                "hook_counts": {},
                "cta_counts": {},
                "pattern_counts": {},
                "post_type_counts": {},
                "caption_lengths": [],
                "hashtag_counts": [],
                "likes": [],
                "comments": [],
                "hashtags": {},
            })

            account["post_count"] += 1

            for field, counts_key in (
                ("hook_type", "hook_counts"),
                ("cta_type", "cta_counts"),
                ("pattern_type", "pattern_counts"),
                ("post_type", "post_type_counts"),
            ):
                value = obs.get(field) or "unknown"
                account[counts_key][value] = account[counts_key].get(value, 0) + 1

            if isinstance(obs.get("caption_length"), (int, float)) and not isinstance(obs.get("caption_length"), bool):
                account["caption_lengths"].append(obs["caption_length"])
            if isinstance(obs.get("hashtag_count"), (int, float)) and not isinstance(obs.get("hashtag_count"), bool):
                account["hashtag_counts"].append(obs["hashtag_count"])
            if obs.get("like_count") is not None:
                account["likes"].append(obs["like_count"])
            if obs.get("comment_count") is not None:
                account["comments"].append(obs["comment_count"])

            for tag in obs.get("hashtags") or []:
                if isinstance(tag, str) and tag:
                    account["hashtags"][tag] = account["hashtags"].get(tag, 0) + 1

        profiles = {}
        for handle, account in accounts.items():
            profiles[handle] = {
                "post_count": account["post_count"],
                "dominant_hook_type": _dominant(account["hook_counts"]),
                "dominant_cta_type": _dominant(account["cta_counts"]),
                "dominant_pattern_type": _dominant(account["pattern_counts"]),
                "dominant_post_type": _dominant(account["post_type_counts"]),
                "avg_caption_length": _avg(account["caption_lengths"]),
                "avg_hashtag_count": _avg(account["hashtag_counts"]),
                "avg_likes": _avg(account["likes"]),
                "avg_comments": _avg(account["comments"]),
                "top_hashtags": [
                    tag for tag, _ in sorted(
                        account["hashtags"].items(), key=lambda pair: pair[1], reverse=True
                    )[:5]
                ],
            }

        return {
            "accounts": profiles,
            "account_count": len(profiles),
            "sample_size": len(observations),
        }

    def _caption_summary(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        caption_lengths = [
            obs["caption_length"] for obs in observations
            if isinstance(obs.get("caption_length"), (int, float)) and not isinstance(obs.get("caption_length"), bool)
        ]
        hashtag_counts = [
            obs["hashtag_count"] for obs in observations
            if isinstance(obs.get("hashtag_count"), (int, float)) and not isinstance(obs.get("hashtag_count"), bool)
        ]

        hashtag_totals: Dict[str, int] = {}
        for obs in observations:
            for tag in obs.get("hashtags") or []:
                if isinstance(tag, str) and tag:
                    hashtag_totals[tag] = hashtag_totals.get(tag, 0) + 1

        top_hashtags = [
            {"hashtag": tag, "count": count}
            for tag, count in sorted(hashtag_totals.items(), key=lambda pair: pair[1], reverse=True)[:10]
        ]

        return {
            "avg_caption_length": _avg(caption_lengths),
            "avg_hashtag_count": _avg(hashtag_counts),
            "top_hashtags": top_hashtags,
        }
