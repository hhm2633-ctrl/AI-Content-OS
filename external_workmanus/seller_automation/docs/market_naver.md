# 네이버 스마트스토어(커머스 API) 등록 스펙 — 캄파(OSSA) 분석 기반

## 1. 인증 (토큰 발급)
- 엔드포인트: `POST https://api.commerce.naver.com/external/v1/oauth2/token`
- 전자서명: `bcrypt.hashpw(f"{client_id}_{timestamp}", salt=client_secret)` → base64
- 파라미터: client_id, timestamp(ms, -1분 보정), client_secret_sign, grant_type=client_credentials, type=SELF
- 토큰 캐시: 만료 전 재사용 (캄파는 120초 여유로 재사용)

## 2. 상품 등록 (ProdCreate)
- 엔드포인트(추정/표준): `POST https://api.commerce.naver.com/external/v2/products`
- Content-Type: application/json, Authorization: Bearer {token}

### Payload 최상위 구조
```json
{
  "originProduct": {
    "statusType": "SALE",
    "leafCategoryId": "<네이버 리프 카테고리ID>",
    "name": "<상품명>",
    "images": {
      "representativeImage": { "url": "<대표이미지 URL>" },
      "optionalImages": [ { "url": "..." }, ... ]
    },
    "detailContent": "<상세 HTML>",
    "salePrice": <판매가 정수>,
    "stockQuantity": <재고 정수>,
    "deliveryInfo": { ... 배송정보 ... },
    "customerBenefit": { ... 혜택(선택) ... },
    "detailAttribute": {
      "naverShoppingSearchInfo": { ... 브랜드/제조사 ... },
      "productInfoProvidedNotice": { ... 상품정보제공고시 ... },
      "originAreaInfo": { ... 원산지 ... },
      "optionInfo": { ... 옵션(색상/사이즈) ... },
      "seoInfo": { ... 태그/SEO ... },
      "minorPurchasable": true
    }
  },
  "smartstoreChannelProduct": {
    "naverShoppingRegistration": true,
    "channelProductDisplayStatusType": "ON"
  }
}
```

### 핵심 필드 소스 매핑 (우리 시스템 기준)
| 네이버 필드 | 의미 | 우리 데이터 소스 |
|---|---|---|
| originProduct.name | 상품명 | Product.title (+ 말머리/가공) |
| leafCategoryId | 네이버 카테고리 | 카테고리 매핑 테이블 (수동/자동) |
| salePrice | 판매가 | 도매가 × (1+마진율) + 배송비 등 (가격계산 모듈) |
| stockQuantity | 재고 | 기본값(예: 200) 또는 옵션재고 |
| representativeImage.url | 대표이미지 | Product.thumbnail_url (네이버 이미지 업로드 후 URL) |
| optionalImages | 추가이미지 | Product.images |
| detailContent | 상세설명 HTML | Product.detail_html (+ 템플릿) |
| originAreaInfo | 원산지 | Product.origin |
| productInfoProvidedNotice | 상품정보제공고시 | 카테고리별 템플릿 (식품 필수) |
| optionInfo | 옵션 | Product.options (사이즈/색상 → 조합형) |

### 주의/특이점 (캄파 코드에서 확인)
1. 이미지는 외부 URL을 바로 쓰기보다 **네이버 이미지 업로드 API로 먼저 올린 뒤 그 URL**을 사용(대표이미지). → 우리도 동일 처리 필요.
2. `productInfoProvidedNotice`(상품정보제공고시)는 **식품 카테고리에서 필수**. 도매 상품이 농수산식품이므로 반드시 채워야 함.
3. `originAreaInfo`(원산지)도 식품 필수. Product.origin 활용.
4. 옵션은 색상/사이즈 조합형. 우리 도매 상품은 "용량/중량" 단일 옵션이 많으므로 단순옵션(optionCombinations) 형태로 구성.
5. 가격은 정수(원), salePrice 단위.

## 3. 구현 계획 (우리 시스템)
- `markets/naver_auth.py` : 토큰 (완료)
- `markets/naver_payload.py` : Product → 네이버 originProduct payload 빌더 (가공/마진/고시 포함)
- `markets/naver_client.py` : 이미지 업로드 + 카테고리 조회 + 상품등록 호출 (dry-run 지원)
- 샌드박스에서는 dry-run으로 payload 생성/검증까지, 실제 전송은 사용자 PC에서 키 입력 후.
