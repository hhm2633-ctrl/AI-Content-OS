from typing import Any, Dict, List, Optional

from modules.instagram_research.instagram_classifier import classify_post
from modules.instagram_research.instagram_normalizer import parse_visible_count_text
from modules.instagram_research.instagram_research_interface import InstagramResearchInterface


class CompetitorLearningExtractor:
    """
    Competitor Learning Engine - Extractor (Sprint 18).

    Reads modules/instagram_research/'s already-saved, manually-observed posts
    through its public, read-only InstagramResearchInterface, and classifies
    each post's hook/cta/pattern using instagram_research's own
    classify_post() function. This class never imports Playwright/browser
    automation, never writes back into modules/instagram_research/'s storage,
    and never modifies that module - it is a read-only consumer, exactly like
    KnowledgeInterface is for the other Engines in this codebase.

    extract() never raises: any failure (no research data yet, corrupted
    records, classification errors on a single post) degrades to skipping
    that item, never to an exception reaching the caller.
    """

    def __init__(self, interface: Optional[InstagramResearchInterface] = None):
        self.interface = interface or InstagramResearchInterface()

    def extract(self) -> List[Dict[str, Any]]:
        try:
            posts = self.interface.get_posts()
        except Exception as error:
            print(f"Competitor Learning Extractor Failed To Read Posts: {error}")
            return []

        if not isinstance(posts, list):
            return []

        observations = []
        for post in posts:
            observation = self._build_observation(post)
            if observation is not None:
                observations.append(observation)

        return observations

    def _build_observation(self, post: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(post, dict):
            return None

        try:
            classification = classify_post(post)
        except Exception as error:
            print(f"Competitor Learning Extractor Classification Failed: {error}")
            classification = {}

        if not isinstance(classification, dict):
            classification = {}

        hook = classification.get("hook") or {}
        cta = classification.get("cta") or {}
        pattern = classification.get("pattern") or {}

        try:
            like_count = parse_visible_count_text(post.get("visible_like_text"))
        except Exception:
            like_count = None

        try:
            comment_count = parse_visible_count_text(post.get("visible_comment_text"))
        except Exception:
            comment_count = None

        hashtags = post.get("hashtags")
        if not isinstance(hashtags, list):
            hashtags = []

        return {
            "account_handle": post.get("account_handle"),
            "post_shortcode": post.get("post_shortcode"),
            "post_type": post.get("post_type") or "unknown",
            "slide_count": post.get("slide_count"),
            "image_count": post.get("image_count"),
            "caption_length": post.get("caption_length"),
            "hashtag_count": post.get("hashtag_count"),
            "hashtags": hashtags,
            "like_count": like_count,
            "comment_count": comment_count,
            "hook_type": hook.get("value") or "unknown",
            "hook_confidence": hook.get("confidence") if isinstance(hook.get("confidence"), (int, float)) else 0.0,
            "cta_type": cta.get("value") or "unknown",
            "cta_confidence": cta.get("confidence") if isinstance(cta.get("confidence"), (int, float)) else 0.0,
            "pattern_type": pattern.get("value") or "unknown",
            "pattern_confidence": pattern.get("confidence") if isinstance(pattern.get("confidence"), (int, float)) else 0.0,
        }
