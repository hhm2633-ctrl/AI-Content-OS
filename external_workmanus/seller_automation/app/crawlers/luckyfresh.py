"""
럭키프레시(행운프레시) 크롤러 — 내부 API 직접 호출 방식.

분석 결과:
- 로그인:  POST https://api.luckyfresh.co.kr/api/auth/login  {username, password} -> data.token (JWT)
- 목록:    GET  /api/products?page=&limit=  -> data.data[], data.pagination
- 상세:    GET  /api/products/{id}  -> data.product, data.options[]
"""
from __future__ import annotations
import re
from typing import List, Dict, Any, Optional
from .base import BaseCrawler, NormalizedProduct, ProductOption, CrawlerError

API = "https://api.luckyfresh.co.kr"
IMG_RE = re.compile(r'<img[^>]+src=\\?"?([^"\\>\s]+)', re.IGNORECASE)


class LuckyfreshCrawler(BaseCrawler):
    site_key = "luckyfresh"
    display_name = "럭키프레시(행운프레시)"

    def login(self) -> None:
        r = self.session.post(
            f"{API}/api/auth/login",
            json={"username": self.username, "password": self.password},
            timeout=self.timeout,
        )
        data = r.json()
        if r.status_code != 200 or not data.get("success"):
            raise CrawlerError(f"로그인 실패: {data.get('message', r.status_code)}")
        self.token = data["data"]["token"]
        self.session.headers["Authorization"] = f"Bearer {self.token}"

    def fetch_product_list(self, max_items: Optional[int] = None) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        page, limit = 1, 50
        while True:
            r = self.session.get(
                f"{API}/api/products", params={"page": page, "limit": limit},
                timeout=self.timeout)
            j = r.json()
            if not j.get("success"):
                raise CrawlerError(f"목록 조회 실패: {j.get('message')}")
            block = j["data"]
            batch = block["data"]
            items.extend(batch)
            total_pages = block["pagination"]["totalPages"]
            if max_items and len(items) >= max_items:
                return items[:max_items]
            if page >= total_pages or not batch:
                break
            page += 1
        return items

    def fetch_detail(self, summary: Dict[str, Any]) -> NormalizedProduct:
        pid = summary["id"]
        r = self.session.get(f"{API}/api/products/{pid}", timeout=self.timeout)
        j = r.json()
        if not j.get("success"):
            raise CrawlerError(f"상세 조회 실패: {j.get('message')}")
        p = j["data"]["product"]
        opts_raw = j["data"].get("options", [])
        options = [
            ProductOption(
                name=o.get("name", ""),
                price=int(o.get("price", 0) or 0),
                prefix_name=o.get("prefixName", "") or "",
                shipping_fee=int(o.get("shippingFee", 0) or 0),
                status=o.get("status", ""),
                source_option_id=str(o.get("id", "")),
            )
            for o in opts_raw
        ]
        prices = [o.price for o in options if o.price] or [
            summary.get("minPrice", 0), summary.get("maxPrice", 0)]
        # 상세 HTML 내 이미지 + 썸네일 수집
        detail_html = p.get("contentHtml", "") or ""
        images = []
        if p.get("thumbnailUrl"):
            images.append(p["thumbnailUrl"])
        for m in IMG_RE.findall(detail_html):
            url = m.replace("\\", "")
            if url not in images:
                images.append(url)
        return NormalizedProduct(
            source_site=self.site_key,
            source_product_id=str(pid),
            title=p.get("name", summary.get("name", "")),
            prefix_name=p.get("prefixName", summary.get("prefixName", "")) or "",
            min_price=min(prices) if prices else 0,
            max_price=max(prices) if prices else 0,
            origin=p.get("origin", "") or "",
            thumbnail_url=p.get("thumbnailUrl", "") or "",
            options=options,
            images=images,
            detail_html=detail_html,
            raw={"summary": summary, "product": p, "options": opts_raw},
        )
