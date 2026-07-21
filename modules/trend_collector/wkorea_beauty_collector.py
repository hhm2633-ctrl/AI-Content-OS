"""Bounded public-list collector for W Korea Beauty."""

from modules.trend_collector.allure_beauty_collector import (
    PublicBeautyEditorialCollector,
)


class WKoreaBeautyCollector(PublicBeautyEditorialCollector):
    SOURCE_ID = "wkorea_beauty"
    SOURCE_NAME = "W Korea"
    DEFAULT_URL = "https://www.wkorea.com/category/beauty/"
    ALLOWED_HOSTS = frozenset({"wkorea.com", "www.wkorea.com"})
    CACHE_FILENAME = "wkorea_beauty_editorial_cache.json"
    COLLECTION_METHOD = "wkorea_beauty_public_list"
    CACHE_METHOD = "wkorea_beauty_cache"
    NO_DATA_METHOD = "wkorea_beauty_no_data"
    ATTRIBUTION = "W Korea Beauty public list"
