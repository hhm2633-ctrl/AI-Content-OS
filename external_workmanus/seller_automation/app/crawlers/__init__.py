from .base import BaseCrawler, NormalizedProduct, ProductOption, CrawlerError
from .luckyfresh import LuckyfreshCrawler

# 사이트 키 -> 크롤러 클래스 매핑
CRAWLERS = {
    LuckyfreshCrawler.site_key: LuckyfreshCrawler,
}


def get_crawler(site_key: str, username: str, password: str) -> BaseCrawler:
    cls = CRAWLERS.get(site_key)
    if not cls:
        raise CrawlerError(f"지원하지 않는 사이트: {site_key}")
    return cls(username, password)
