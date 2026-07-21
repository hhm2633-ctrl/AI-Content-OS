# 최고집 홀세일 (choigozip) 크롤링 분석

## 사이트 유형
- React SPA + REST API (독자 구축, Spring 추정)
- 도메인: `https://partner.choigozip.co.kr`
- 이미지 CDN: `https://d2gs9jf7txm97a.cloudfront.net/products/...`

## 핵심: 공개(public) API로 인증 없이 상품 수집 가능
- 상품 목록: `GET /api/public/products?page={0부터}&size={n}`
  - 응답: Spring Page 객체 (content[], totalElements, totalPages, number, last 등)
  - 현재 총 222개 상품 (size=40이면 약 6페이지)
- 상품 상세: `GET /api/public/products/{id}` → options 배열 포함 (optionName, supplyPrice)
- 카테고리: `GET /api/public/categories`
- 공지/배너: `/api/public/notices/popup`, `/api/public/banners`
- (참고) `/api/products` 등 비공개 API는 401 "인증이 필요합니다" → 로그인 토큰 필요하지만, public API로 충분

## 상품 데이터 필드
- id, name, categoryName, imageUrl, thumbnailUrl, images, description(HTML)
- taxType(TAX_FREE 등), supplyPrice(공급가), priceType, hasOptions
- shippingPolicy{type, jejuExtra, isolatedExtra}, supplyMethod(CONSIGNMENT=위탁)
- stockType(UNLIMITED 등), availableStock, isNew
- options[]: {id, optionName, supplyPrice}

## 수집 전략 (API 직접 호출 - 가장 견고)
1. (로그인 불필요) `/api/public/products?page=N&size=40` 순회하여 전체 목록 수집
2. hasOptions=true면 `/api/public/products/{id}` 호출하여 옵션/상세설명 수집
3. 이미지: imageUrl + description 내 <img> 태그에서 상세이미지 추출
4. 로그인이 필요한 경우(가격 차등 등)에 대비해 로그인 토큰 획득 로직도 보조로 준비

## 비고
- 럭키프레시와 동일한 "API 직접 호출" 방식 → base.py의 API 크롤러 패턴 재사용
- 로그인 없이도 공급가/옵션까지 노출되어 수집 난이도 가장 낮음
