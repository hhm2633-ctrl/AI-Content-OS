"""
크롤러 공통 베이스.
- 각 도매 사이트별 크롤러는 BaseCrawler를 상속해 login() / fetch_products() / fetch_detail() 구현
- 표준화된 상품 dict를 반환하여 상위 계층(DB 저장/가공)에서 동일하게 처리
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import requests


@dataclass
class ProductOption:
    name: str
    price: int
    prefix_name: str = ""
    shipping_fee: int = 0
    status: str = ""
    source_option_id: str = ""


@dataclass
class NormalizedProduct:
    """모든 사이트에서 동일한 형태로 맞추는 표준 상품 구조."""
    source_site: str
    source_product_id: str
    title: str
    prefix_name: str = ""
    min_price: int = 0
    max_price: int = 0
    origin: str = ""
    thumbnail_url: str = ""
    options: List[ProductOption] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    detail_html: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_db_dict(self) -> Dict[str, Any]:
        import json
        price = self.min_price or (self.options[0].price if self.options else 0)
        return {
            "source_site": self.source_site,
            "source_product_id": str(self.source_product_id),
            "title": self.title,
            "prefix_name": self.prefix_name,
            "price": price,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "origin": self.origin,
            "thumbnail_url": self.thumbnail_url,
            "options_json": json.dumps([asdict(o) for o in self.options], ensure_ascii=False),
            "images_json": json.dumps(self.images, ensure_ascii=False),
            "detail_html": self.detail_html,
            "raw_json": json.dumps(self.raw, ensure_ascii=False)[:200000],
            "status": "collected",
        }


class CrawlerError(Exception):
    pass


class BaseCrawler:
    site_key: str = "base"
    display_name: str = "Base"

    def __init__(self, username: str, password: str, timeout: int = 20):
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0 Safari/537.36"),
            "Accept": "application/json, text/plain, */*",
        })
        self.token: Optional[str] = None

    # 하위 클래스에서 구현
    def login(self) -> None:
        raise NotImplementedError

    def fetch_product_list(self, max_items: Optional[int] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def fetch_detail(self, summary: Dict[str, Any]) -> NormalizedProduct:
        raise NotImplementedError

    def collect(self, max_items: Optional[int] = None) -> List[NormalizedProduct]:
        """전체 수집 파이프라인: 로그인 → 목록 → 상세."""
        self.login()
        summaries = self.fetch_product_list(max_items=max_items)
        results: List[NormalizedProduct] = []
        for s in summaries:
            try:
                results.append(self.fetch_detail(s))
            except Exception as e:  # 개별 상품 실패는 건너뜀
                print(f"  [warn] detail 실패 ({s.get('id')}): {e}")
        return results
