# 럭키프레시(행운프레시) 크롤링 분석

## 사이트 유형
- React SPA + 별도 API 서버 (`api.luckyfresh.co.kr`)
- 인증: 로그인 성공 시 JWT 발급, **localStorage `token`** 에 저장
- API 호출 시 헤더 `Authorization: Bearer <token>` 필요

## 로그인
- 로그인 페이지: `https://luckyfresh.co.kr/login`
- 추정 로그인 API: `POST https://api.luckyfresh.co.kr/api/auth/login` (body: 아이디/비번) → 추가 확인 필요
- 화면 폼: 아이디 input(text) / 비번 input(password) / 로그인 버튼

## 핵심 API
### 1) 상품 목록
`GET https://api.luckyfresh.co.kr/api/products?page=1&limit=20`
응답:
```
data.data[] = { id, name, prefixName, thumbnailUrl, minPrice, maxPrice, orderCutoffTime }
data.pagination = { total, page, limit, totalPages }
```

### 2) 상품 상세
`GET https://api.luckyfresh.co.kr/api/products/{id}`
응답:
```
data.product = {
  id, name, prefixName, thumbnailUrl,
  contentHtml,   // 상세설명 HTML (이미지 포함)
  origin,        // 원산지
  driveLink,     // 구글드라이브(상세이미지 원본)
  orderCutoffTime, status, isReservation ...
}
data.options[] = { id, name, prefixName, price, shippingFee, status }
```

### 3) 카테고리
`GET https://api.luckyfresh.co.kr/api/categories/active`

## 수집 전략
- 로그인 → 토큰 확보 → `/api/products` 페이지네이션 순회 → 각 상품 `/api/products/{id}` 상세 수집
- 옵션(가격/배송비), 상세 HTML, 원산지, 썸네일까지 완전 수집 가능
- 이미지: thumbnailUrl + contentHtml 내 <img> S3 URL 추출
