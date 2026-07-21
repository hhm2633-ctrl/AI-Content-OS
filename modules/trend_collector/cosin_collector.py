"""Fallback-first shallow collector for Cosin Korea public editorial lists."""

import re

from modules.trend_collector.beautynury_collector import BeautynuryCollector


class CosinCollector(BeautynuryCollector):
    """Collect only metadata visible on a Cosin Korea public list page.

    The shared implementation is intentionally limited to one public list request,
    deterministic list-card parsing, and a read-only fresh-cache fallback.  It does
    not visit article details or infer product efficacy and engagement.
    """

    DEFAULT_URL = "https://www.cosinkorea.com/news/article_list_all.html"
    DEFAULT_CACHE_PATH = BeautynuryCollector.DEFAULT_CACHE_PATH.with_name(
        "cosin_editorial_cache.json"
    )
    SOURCE_ID = "cosin"
    SOURCE_NAME = "Cosin Korea"
    ATTRIBUTION = "Cosin Korea public editorial list"
    LIVE_METHOD = "cosin_public_editorial_list"
    CACHE_METHOD = "cosin_editorial_cache"
    NO_DATA_METHOD = "cosin_no_data"
    ALLOWED_HOSTS = {"cosinkorea.com", "www.cosinkorea.com"}
    ARTICLE_PATH_PATTERN = re.compile(
        r"^/news/article\.html$", re.IGNORECASE
    )

    def _is_article_link(self, link: str) -> bool:
        """Accept only real Cosin article URLs with a numeric article number."""
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(link)
        if not self.ARTICLE_PATH_PATTERN.fullmatch(parsed.path):
            return False
        values = parse_qs(parsed.query).get("no", [])
        return len(values) == 1 and values[0].isdigit()


__all__ = ["CosinCollector"]
