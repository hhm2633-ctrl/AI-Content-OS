"""
통합 수집기 (Collector)
- 등록된 도매 사이트 크롤러들을 실행해 상품을 수집하고 로컬 DB에 저장(upsert)한다.
- (source_site, source_product_id) 기준으로 이미 있으면 갱신, 없으면 신규 삽입.
"""
from __future__ import annotations
import json
from datetime import datetime
from typing import Dict, List, Optional, Type

from sqlalchemy.orm import Session

from .models import Product
from .crawlers.base import BaseCrawler, NormalizedProduct
from .crawlers.luckyfresh import LuckyfreshCrawler
from .crawlers.choigozip import ChoigozipCrawler
from .crawlers.adminplus import EconfarmCrawler

# 사이트 키 -> 크롤러 클래스 매핑
CRAWLER_REGISTRY: Dict[str, Type[BaseCrawler]] = {
    "luckyfresh": LuckyfreshCrawler,
    "choigozip": ChoigozipCrawler,
    "econfarm": EconfarmCrawler,
}

# 로그인 필요 여부 (최고집은 public API라 불필요)
NEEDS_LOGIN = {"luckyfresh": True, "econfarm": True, "choigozip": False}


def _upsert_product(db: Session, np: NormalizedProduct) -> bool:
    """정규화 상품을 DB에 upsert. 신규면 True, 갱신이면 False 반환."""
    existing = (
        db.query(Product)
        .filter(Product.source_site == np.source_site,
                Product.source_product_id == str(np.source_product_id))
        .first()
    )
    options_json = json.dumps([o.__dict__ for o in np.options], ensure_ascii=False)
    images_json = json.dumps(np.images, ensure_ascii=False)
    raw_json = json.dumps(np.raw, ensure_ascii=False)[:50000]

    if existing:
        existing.title = np.title
        existing.price = np.min_price
        existing.min_price = np.min_price
        existing.max_price = np.max_price
        existing.origin = np.origin
        existing.thumbnail_url = np.thumbnail_url
        existing.options_json = options_json
        existing.images_json = images_json
        existing.detail_html = np.detail_html
        existing.raw_json = raw_json
        existing.updated_at = datetime.utcnow()
        return False
    else:
        db.add(Product(
            source_site=np.source_site,
            source_product_id=str(np.source_product_id),
            title=np.title,
            price=np.min_price,
            min_price=np.min_price,
            max_price=np.max_price,
            origin=np.origin,
            thumbnail_url=np.thumbnail_url,
            options_json=options_json,
            images_json=images_json,
            detail_html=np.detail_html,
            raw_json=raw_json,
            status="collected",
        ))
        return True


def collect_site(
    db: Session,
    site_key: str,
    username: str = "",
    password: str = "",
    max_items: Optional[int] = None,
    progress=None,
) -> Dict[str, int]:
    """단일 사이트 수집 후 DB 저장. 통계 dict 반환."""
    if site_key not in CRAWLER_REGISTRY:
        raise ValueError(f"알 수 없는 사이트: {site_key}")
    crawler_cls = CRAWLER_REGISTRY[site_key]
    crawler = crawler_cls(username=username, password=password)

    if NEEDS_LOGIN.get(site_key, False):
        crawler.login()

    summaries = crawler.fetch_product_list(max_items=max_items)
    stats = {"site": site_key, "listed": len(summaries), "new": 0, "updated": 0, "failed": 0}

    for i, summary in enumerate(summaries, 1):
        try:
            np = crawler.fetch_detail(summary)
            is_new = _upsert_product(db, np)
            stats["new" if is_new else "updated"] += 1
            if i % 10 == 0:
                db.commit()
            if progress:
                progress(site_key, i, len(summaries), np.title)
        except Exception as e:
            stats["failed"] += 1
            if progress:
                progress(site_key, i, len(summaries), f"[실패] {e}")
    db.commit()
    return stats
