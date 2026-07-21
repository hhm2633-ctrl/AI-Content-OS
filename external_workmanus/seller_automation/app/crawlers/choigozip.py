"""
최고집 홀세일 (partner.choigozip.co.kr) 크롤러
- React SPA + REST API (Spring Page)
- 공개 API(/api/public/products)로 로그인 없이 수집 가능
- 로그인 자격증명이 있으면 보조로 토큰을 받아 비공개 가격에 대비
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
import re
import time

from .base import BaseCrawler, NormalizedProduct, ProductOption, CrawlerError

BASE = "https://partner.choigozip.co.kr"
IMG_TAG_RE = re.compile(r'<img[^>]+src=["\']?([^"\'>\s]+)', re.I)


class ChoigozipCrawler(BaseCrawler):
    site_key = "choigozip"
    display_name = "최고집 홀세일"

    def login(self) -> None:
        """공개 API만으로 수집 가능하므로 로그인은 선택 사항.
        자격증명이 주어지면 토큰 발급을 시도하되 실패해도 진행한다."""
        if not self.username or not self.password:
            return
        for path in ("/api/auth/login", "/api/login", "/api/public/auth/login"):
            try:
                r = self.session.post(
                    BASE + path,
                    json={"username": self.username, "password": self.password},
                    timeout=self.timeout,
                )
                if r.status_code == 200:
                    data = r.json()
                    tok = data.get("accessToken") or data.get("token") or data.get("access_token")
                    if tok:
                        self.token = tok
                        self.session.headers["Authorization"] = f"Bearer {tok}"
                        break
            except Exception:
                continue

    def fetch_product_list(self, max_items: Optional[int] = None) -> List[Dict[str, Any]]:
        summaries: List[Dict[str, Any]] = []
        page = 0
        size = 40
        while True:
            r = self.session.get(
                f"{BASE}/api/public/products",
                params={"page": page, "size": size},
                timeout=self.timeout,
            )
            if r.status_code != 200:
                raise CrawlerError(f"목록 조회 실패: HTTP {r.status_code}")
            data = r.json()
            content = data.get("content", [])
            for item in content:
                summaries.append(item)
                if max_items and len(summaries) >= max_items:
                    return summaries
            if data.get("last", True) or not content:
                break
            page += 1
            time.sleep(0.2)
        return summaries

    def fetch_detail(self, summary: Dict[str, Any]) -> NormalizedProduct:
        pid = summary.get("id")
        detail = summary
        # 옵션/상세설명은 상세 API에 있다
        try:
            r = self.session.get(f"{BASE}/api/public/products/{pid}", timeout=self.timeout)
            if r.status_code == 200:
                detail = r.json()
        except Exception:
            pass

        options: List[ProductOption] = []
        for o in (detail.get("options") or []):
            options.append(ProductOption(
                name=o.get("optionName", ""),
                price=int(o.get("supplyPrice") or 0),
                source_option_id=str(o.get("id", "")),
            ))

        prices = [op.price for op in options if op.price] or [int(detail.get("supplyPrice") or 0)]
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0

        # 상세 설명 HTML 안의 이미지 추출
        desc = detail.get("description") or ""
        images = IMG_TAG_RE.findall(desc)
        if detail.get("imageUrl"):
            images = [detail["imageUrl"]] + images

        return NormalizedProduct(
            source_site=self.site_key,
            source_product_id=str(pid),
            title=detail.get("name", ""),
            min_price=min_price,
            max_price=max_price,
            origin=detail.get("categoryName", ""),
            thumbnail_url=detail.get("imageUrl") or detail.get("thumbnailUrl") or "",
            options=options,
            images=images,
            detail_html=desc,
            raw=detail,
        )
