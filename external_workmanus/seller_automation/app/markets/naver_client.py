"""
네이버 커머스 API 클라이언트.
- 카테고리 조회, 이미지 업로드, 상품 등록
- dry_run=True 이면 실제 전송하지 않고 요청(payload/headers/url)만 반환 → 샌드박스 검증용
- 실제 전송은 사용자 PC에서 dry_run=False 로 동작
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
import json
import requests

from .naver_auth import NaverAuth, API_BASE
from .naver_payload import NaverProductInput, build_product_payload


class NaverClient:
    def __init__(self, client_id: str, client_secret: str,
                 dry_run: bool = True, timeout: int = 30):
        self.auth = NaverAuth(client_id, client_secret)
        self.dry_run = dry_run
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        token = self.auth.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # --- 카테고리 검색 ---
    def search_category(self, keyword: str) -> List[Dict[str, Any]]:
        url = f"{API_BASE}/v1/categories"
        if self.dry_run:
            return [{"_dry_run": True, "url": url, "keyword": keyword}]
        resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        kw = (keyword or "").strip()
        return [c for c in data if kw in c.get("name", "")] if kw else data

    # --- 이미지 업로드 ---
    def upload_image(self, image_path_or_url: str) -> str:
        """이미지를 네이버에 업로드하고 업로드된 URL 반환."""
        url = f"{API_BASE}/v1/product-images/upload"
        if self.dry_run:
            # dry-run: 원본 URL을 그대로 반환(검증용)
            return image_path_or_url
        # 실제: 파일 바이트를 multipart 업로드
        if image_path_or_url.startswith("http"):
            img = requests.get(image_path_or_url, timeout=self.timeout).content
        else:
            with open(image_path_or_url, "rb") as f:
                img = f.read()
        files = {"imageFiles": ("image.jpg", img, "image/jpeg")}
        token = self.auth.get_token()
        resp = requests.post(url, headers={"Authorization": f"Bearer {token}"},
                             files=files, timeout=self.timeout)
        resp.raise_for_status()
        images = resp.json().get("images", [])
        return images[0]["url"] if images else ""

    # --- 상품 등록 ---
    def create_product(self, ni: NaverProductInput) -> Dict[str, Any]:
        url = f"{API_BASE}/v2/products"
        payload = build_product_payload(ni)
        if self.dry_run:
            return {
                "_dry_run": True,
                "method": "POST",
                "url": url,
                "headers": {"Authorization": "Bearer <TOKEN>",
                            "Content-Type": "application/json"},
                "payload": payload,
            }
        resp = requests.post(url, headers=self._headers(),
                             data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                             timeout=self.timeout)
        result: Dict[str, Any] = {"status_code": resp.status_code}
        try:
            result["body"] = resp.json()
        except Exception:
            result["body"] = resp.text
        return result
