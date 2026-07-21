"""Bounded public-list collector for Vogue Korea Beauty."""

from modules.trend_collector.allure_beauty_collector import (
    PublicBeautyEditorialCollector,
)


class VogueBeautyCollector(PublicBeautyEditorialCollector):
    SOURCE_ID = "vogue_beauty"
    SOURCE_NAME = "Vogue Korea"
    DEFAULT_URL = "https://www.vogue.co.kr/category/beauty/"
    ALLOWED_HOSTS = frozenset({"vogue.co.kr", "www.vogue.co.kr"})
    CACHE_FILENAME = "vogue_beauty_editorial_cache.json"
    COLLECTION_METHOD = "vogue_beauty_public_list"
    CACHE_METHOD = "vogue_beauty_cache"
    NO_DATA_METHOD = "vogue_beauty_no_data"
    ATTRIBUTION = "Vogue Korea Beauty public list"
