# AEDI-V / Snipit 기술 재사용 감사

- 조사일: 2026-07-14 (Asia/Seoul)
- 대상: [AEDI-V](https://aisum.com/ko/aediv), [AEDI-V Chrome Web Store](https://chromewebstore.google.com/detail/aedi-v-ai-product-matchin/bgfclceipgllbohhclicafhdcipbeogd?hl=ko), [Snipit](https://snipit.im/)
- 목적: 제품 소개가 아니라 **공개 코드·계약·구현 패턴을 재사용해 AI-Content-OS의 수익화 개발을 단축할 수 있는지** 판정한다.
- 경계: 계정 생성, 확장 설치, YouTube/Meta 연결, 인증 후 수집, 비공개 코드 복제는 하지 않았다.

## 결론

| 제품 | 바로 복사해 쓸 공개 코드 | 공식 공개 API/SDK/CLI | 허용된 export/webhook | 지금 판정 |
|---|---|---|---|---|
| AEDI-V | **없음 확인** | **없음 확인** | **없음 확인** | `BENCHMARK + CONDITIONAL BUY`; 직접 통합 `NO-GO` |
| Snipit | **없음 확인** | **없음 확인** | 사용자용 다운로드/import 흔적은 관찰되지만 외부 개발자 계약은 **없음 확인** | `BENCHMARK`; 상업 사용·export 서면 허가 후 `CONDITIONAL BUY` |

두 제품의 공개 배포물을 우리 저장소로 가져올 수는 없다. 대신 바로 쓸 수 있는 것은 다음 세 가지다.

1. 기존 `modules/affiliate`, `modules/brandconnect`, `modules/commerce`, `modules/shorts`, `modules/competitor_learning`에 맞춘 **정규화 스키마와 수동 import 경계**
2. AEDI-V의 `장면/음성/맥락 -> 상품 후보 -> 사람 선택 -> 태그 작업` 패턴
3. Snipit의 `다중 소스 광고 -> 공통 CreativeReference -> 검색/필터 -> 보드/모니터링 -> 패턴 학습` 패턴

공개 번들에서 관찰된 URL이나 브라우저 확장 코드는 **문서화된 제3자 API가 아니다**. 호출·복제·의존하지 않고 인터페이스 설계 증거로만 사용한다.

## 조사 방법과 증거 등급

- `VERIFIED`: 공식 사이트, 공식 Web Store, 공개 배포 manifest, 공식 약관/개인정보 문서에서 확인.
- `OBSERVED`: 인증 없이 공개된 웹/PWA 클라이언트의 manifest·정적 번들에서 이름이나 경계를 관찰. 지원 계약이나 재사용 허가는 아님.
- `INFERRED`: 기능 동작을 설명하는 가장 작은 합리적 아키텍처. 벤더 구현 사실로 주장하지 않음.
- GitHub, npm, PyPI에서 제품명·회사명·도메인을 검색했으나 2026-07-14 기준 벤더 소유로 확인되는 공개 저장소/패키지를 찾지 못했다. 동명의 PyPI/GitHub 프로젝트는 관련 없는 프로젝트이므로 채택하지 않는다.

---

## 1. AEDI-V

### 1.1 확인된 제품 및 배포 계약

`VERIFIED`:

- Chrome 확장 프로그램이며 YouTube Studio 편집 페이지에서 영상 장면·대화·맥락을 분석해 상품과 타임스탬프를 추천하고 선택된 태그를 등록한다. 파트너 상품 목록에 없는 상품은 추천되지 않을 수 있고, 무분별한 등록은 YouTube Shopping 제한 위험이 있다고 벤더가 직접 경고한다. [공식 Web Store 설명](https://chromewebstore.google.com/detail/aedi-v-ai-product-matchin/bgfclceipgllbohhclicafhdcipbeogd?hl=en)
- 공식 소개는 영상·음성·상황의 세 매칭 신호, 품절/판매 중단 모니터링과 대체 상품 제안을 설명한다. [AEDI-V 소개](https://aisum.com/ko/aediv)
- Web Store 공개 정보상 2026-07-02 버전은 `1.2.76`, Manifest V3 배포물이다. 개발자는 개인 식별 정보, 금융·결제 정보, 웹사이트 콘텐츠 처리를 신고했다.
- 공식 Google 배포 CRX에서 **manifest만 메모리로 읽고 즉시 폐기**해 확인한 권한은 `scripting`, `identity`, `activeTab`, `tabs`, `storage`, `cookies`, host permission `<all_urls>`이다. content script는 `studio.youtube.com/*`와 `<all_urls>` 범위를 포함하고, background service worker를 사용한다. 이는 설치 전 보안심사가 필요한 넓은 권한이다. 확장 코드는 복사·저장·분석하지 않았다.
- AISUM의 공개 개인정보 문서는 서비스 이용기록, IP, 쿠키, 결제정보와 생성정보 수집 도구를 명시하지만 AEDI-V/YouTube 영상 데이터의 필드별 보존기간·삭제 SLA·모델 학습 여부는 명확히 분리해 설명하지 않는다. [AISUM 개인정보 처리방침](https://aisum.com/ko/policy)
- AISUM 약관은 회사가 제공하지 않는 방식의 접속, 로봇/스크립트 접근, 보고서 내용의 무단 영리 이용·제공·변조를 금지한다. [AISUM 이용약관](https://aisum.com/ko/terms_of_use)

### 1.2 공개 코드·API·export 감사

| 항목 | 결과 | 재사용 판정 |
|---|---|---|
| 공개 GitHub repository | 확인 못함 | 없음 |
| 공개 소스 라이선스 | 확인 못함 | 없음 |
| npm/PyPI package | 벤더 소유 확인 못함 | 없음 |
| 공식 REST/GraphQL API 문서 | 확인 못함 | 통합 금지 |
| SDK/CLI | 확인 못함 | 없음 |
| CSV/JSON export schema | 확인 못함 | 수동 export를 가정하지 말 것 |
| webhook | 확인 못함 | 없음 |
| Chrome manifest | 공식 배포물에서 확인 | 권한/보안 경계 참고만 가능 |
| CRX JavaScript | 공개 배포지만 라이선스 없음 | 복제·vendor code import 금지 |

따라서 **바로 쓸 수 있는 벤더 코드는 0개**다. 확장 내부 요청이나 DOM 조작을 흉내 내는 것도 공식 API가 아니며 약관·계정 위험 때문에 금지한다.

### 1.3 관찰과 추정을 분리한 아키텍처

`VERIFIED/OBSERVED` 흐름:

```text
YouTube Studio 편집 화면
-> 확장 프로그램 UI
-> 영상/음성/맥락 분석 요청
-> 파트너 상품 후보와 타임스탬프
-> 사용자 선택
-> Studio 태그 등록
```

`INFERRED` 구현 패턴:

```text
video identity + revision fingerprint
-> scene segmentation / sampled frames
-> speech transcript or dialogue signal
-> visual, speech, context 후보 검색
-> 상품 카탈로그 후보 합집합
-> relevance/risk/availability/commission ranking
-> human approval
-> idempotent tag command + readback receipt
```

프레임 샘플링 방식, 모델, 임베딩, 랭커, 프롬프트, 정확도 계산, 카탈로그 API는 공개 근거가 없으므로 벤더 구현으로 간주하지 않는다.

### 1.4 우리 코드에 필요한 최소 계약

새 엔진을 바로 만들지 말고 기존 standalone 모듈 사이에 아래 vendor-neutral 계약을 둔다.

```json
{
  "schema_version": "scene_product_match_candidate.v1",
  "candidate_id": "opaque-deterministic-id",
  "content_ref": {
    "platform": "youtube",
    "video_id": "opaque",
    "revision_fingerprint": "sha256",
    "source_rights": "owner_confirmed"
  },
  "scene": {
    "scene_id": 3,
    "start_ms": 12400,
    "end_ms": 16800,
    "evidence_types": ["visual", "speech", "context"]
  },
  "product_candidate": {
    "network_id": "coupang_or_other_confirmed_network",
    "merchant_id": null,
    "product_id": null,
    "title": "operator-supplied",
    "canonical_url": null
  },
  "scores": {
    "match_score": null,
    "score_source": "vendor_or_internal",
    "is_measured": false
  },
  "commercial_observation": {
    "commission_estimate": null,
    "currency": null,
    "source_url": null,
    "source_timestamp": null,
    "settlement_verified": false
  },
  "human_review": {
    "status": "pending",
    "reviewer": null,
    "reviewed_at": null,
    "false_endorsement_checked": false
  }
}
```

권장 내부 인터페이스:

```python
class SceneProductCandidateImporter:
    def import_manual_receipt(self, receipt: dict) -> dict: ...

class SceneProductMatchGate:
    def evaluate(self, candidate: dict, current_time) -> dict: ...

class AffiliateCandidateAdapter:
    def to_routing_inputs(self, approved_candidate: dict) -> dict: ...
```

구현 원칙:

- `AffiliateCandidateAdapter`는 `MerchantOffer`를 만들어도 프로그램/오퍼/merchant exact back-reference와 출처·freshness를 채우지 못하면 `manual_review`로 남긴다.
- AEDI-V의 예상 커미션은 `commission_estimate`, `is_measured: false`, `settlement_verified: false`이며 실제 `revenue_ledger`에 쓰지 않는다.
- 태그 등록은 `TrackingLinkRequest`나 `TaggingActionRequest`까지만 만들고 실제 링크/태그는 Phase 2 승인 전 수행하지 않는다.
- 영상 수정 후 이전 후보가 남는 위험을 `revision_fingerprint` 불일치로 차단한다.

### 1.5 현재 모듈 매핑

| 프로젝트 계층 | 재사용 방식 |
|---|---|
| `modules/shorts` | `shorts_scene_plan_result.scenes[]`를 상품 후보의 scene 경계로 사용; renderer/publisher와 분리 |
| `modules/affiliate` | 승인 후보를 기존 `AffiliateRevenueRouter` 입력으로 변환; 실제 링크 생성 금지 유지 |
| `modules/commerce` | 상품 identity/fact/source/freshness를 재검증; AEDI-V 추천만으로 상품 사실을 만들지 않음 |
| `modules/brandconnect` | Naver Shopping Connect 링크/캠페인과 혼합하지 않고 별도 수익선으로 기록 |
| Competitor/Learning | 상품이 연결되는 장면·hook·CTA 패턴 통계만 익명화해 학습 |
| Analytics | 추천 수, 승인률, false-positive율, 작업시간만 측정; 매출은 승인된 정산 소스만 사용 |

### 1.6 판정과 최소 파일럿

- `BUY`: YouTube Shopping 운영이 실제 시작된 뒤 수동 생산성 도구로 조건부.
- `INTEGRATE`: 공식 API/export/schema와 계약이 없으므로 현재 `NO-GO`.
- `BENCHMARK`: 지금 채택. 특히 multimodal candidate + human gate + stale replacement 패턴.
- `BUILD`: vendor-neutral 후보 계약, revision gate, Affiliate adapter만 향후 작은 Sprint로 보유.

가장 작은 가역 파일럿:

1. 설치 전에 AISUM에 정확한 host 권한 필요성, YouTube 콘텐츠 보존/삭제, 모델 학습, 제3자 제공, export/API, 태그 write/readback 범위를 서면 질의한다.
2. 통과 시 소유자 승인 격리 브라우저 프로필과 비운영 영상 1개만 사용한다.
3. 자동 등록 전에 후보 10개를 사람이 검수하고 `precision`, timestamp 오차, 승인률, 1영상 작업시간을 기록한다.
4. 실제 매출 효과를 주장하지 않고, 종료 후 확장 제거·세션/권한 철회 여부를 확인한다.

---

## 2. Snipit

### 2.1 확인된 제품 및 공개 클라이언트 계약

`VERIFIED`:

- Instagram/Meta 광고 등 레퍼런스를 검색하고 브랜드 아카이브·보드·필터·인플루언서 추천으로 정리한다. [Snipit 공식 소개](https://snipit.im/)
- 플랜은 검색, 보드, 브랜드 모니터링, 플랫폼 범위를 차등 제공하며 Enterprise는 Google Display/YouTube Ads 등을 명시한다. [플랜 안내](https://snipit.im/pricing)
- 공식 약관은 서비스에서 얻은 정보를 사전 승낙 없이 복제·유통·상업적으로 이용하는 행위와 회사 동의 없는 영리 목적 사용을 금지한다. 따라서 광고 원본이나 서비스 결과를 우리 데이터셋/상품에 넣기 전에 **서면 라이선스 확인이 필수**다. [Snipit 이용약관 제12조](https://snipit.im/terms-of-service)
- 개인정보 방침은 방문기록 보존과 Google Workspace/Photos API 데이터의 일반 모델 학습 제한을 설명하지만, 모든 광고·Meta 연결 데이터에 동일 제한이 적용된다고 확대 해석할 수 없다. [Snipit 개인정보 처리방침](https://snipit.im/privacy-policy)

`OBSERVED` — 인증 없이 공개된 PWA 정적 자산에서 확인한 경계:

- `manifest.json`: PWA 이름은 “스니핏 | 콘텐츠 레퍼런스 보드”.
- 프런트 번들 분리는 `vendor-tanstack`, `vendor-mantine`, `vendor-charts`, `vendor-analytics`, `main`으로 노출된다. 이는 TanStack 계열 상태/데이터 패턴, Mantine UI, 차트/분석 계층을 사용한다는 기술 단서이지 소스 라이선스가 아니다.
- 공개 client bundle에는 `/api/v1` base와 search, boards, archive, monitoring, analytics, agent, canvas, script project/run, media download, Instagram-saved import, Meta connection 경로 이름이 보인다.
- 사용자 기능으로 PNG/PDF/chart download, media ZIP, board export, Instagram saved import 관련 문자열이 보인다.

이 경로들은 인증·권한·rate limit·스키마·안정성·상업 사용 약정이 없는 **내부 API**다. 호출하거나 우리 adapter 대상으로 고정하지 않는다. webhook은 공개 client와 공식 문서에서 확인하지 못했다.

### 2.2 공개 코드·API·export 감사

| 항목 | 결과 | 재사용 판정 |
|---|---|---|
| 공개 GitHub repository | 벤더 소유 확인 못함 | 없음 |
| 공개 소스 라이선스 | 확인 못함 | 없음 |
| npm/PyPI package | 벤더 소유 확인 못함 | 없음 |
| 공식 developer API/OpenAPI | 확인 못함 | 내부 `/api/v1` 직접 호출 금지 |
| SDK/CLI | 확인 못함 | 없음 |
| 사용자 다운로드/import | client에 기능 흔적 있음 | 계정/플랜별 실제 형식과 재사용 권리는 UNKNOWN |
| webhook | 확인 못함 | 없음 |
| PWA/JS bundle | 공개 정적 배포물 | 구조 관찰만; 코드 복제 금지 |

따라서 Snipit에서도 **바로 복사해 쓸 벤더 코드는 0개**다. React/TanStack/Mantine 같은 일반 라이브러리는 각 원 라이선스에 따라 독립적으로 선택할 수 있지만, Snipit 번들에서 코드를 추출해서 쓰는 것은 허용되지 않는다.

### 2.3 관찰과 추정을 분리한 아키텍처

`VERIFIED/OBSERVED` 기능 경계:

```text
platform content/ad sources
-> normalized searchable references
-> text/image/filter search
-> boards/archive
-> brand monitoring and analytics
-> canvas/script/agent workflows
-> user download/import surfaces
```

`INFERRED` 구현 패턴:

```text
source adapters
-> immutable CreativeReference + provenance
-> text/image embedding indexes + metadata index
-> brand/time/platform aggregates
-> pattern extraction (hook/problem/proof/offer/CTA/format)
-> approved internal knowledge
-> content/brand/affiliate plan
```

수집기, Meta API 계약, 임베딩 모델, 랭킹식, agent prompt, 데이터베이스는 공개 근거가 없어 벤더 구현으로 주장하지 않는다.

### 2.4 우리 코드에 필요한 최소 계약

```json
{
  "schema_version": "creative_reference.v1",
  "reference_id": "opaque-deterministic-id",
  "platform": "instagram|meta_ads|youtube_ads|google_display|tiktok",
  "source": {
    "canonical_url": "https://...",
    "retrieved_at": "timezone-aware ISO-8601",
    "collection_method": "manual_vendor_export|official_api|manual_url",
    "rights_status": "reference_only",
    "render_allowed": false
  },
  "publisher": {
    "brand_id": "normalized-local-id",
    "display_name": "..."
  },
  "creative": {
    "published_at": null,
    "media_type": "image|carousel|video|unknown",
    "caption_summary": "operator-authored summary",
    "asset_locator": null
  },
  "observed_signals": {
    "active_duration_days": null,
    "engagement": null,
    "performance_source": "vendor_observation",
    "is_revenue": false
  },
  "pattern": {
    "hook_type": null,
    "problem_frame": null,
    "proof_type": null,
    "offer_type": null,
    "cta_type": null,
    "confidence": null,
    "human_verified": false
  }
}
```

권장 내부 인터페이스:

```python
class CreativeReferenceImporter:
    def import_authorized_export(self, payload: bytes, receipt: dict) -> list[dict]: ...

class CreativeRightsGate:
    def evaluate(self, reference: dict) -> dict: ...

class CreativePatternExtractor:
    def extract(self, reference_summary: dict) -> list[dict]: ...
```

필수 불변식:

- 기본값은 `rights_status: reference_only`, `render_allowed: false`.
- 원본 이미지·영상·카피를 CardNews/Shorts에 복제하지 않고, 사람이 확인한 추상 패턴만 Knowledge로 승격한다.
- 광고 게재 기간, engagement, vendor filter는 매출/ROAS 증거가 아니다.
- import는 벤더가 허용한 export 파일과 권리 receipt가 있을 때만 수행한다. 내부 API endpoint 호출기는 만들지 않는다.

### 2.5 현재 모듈 매핑

| 프로젝트 계층 | 재사용 방식 |
|---|---|
| `modules/competitor_learning` | `CreativeReference`를 읽고 hook/CTA/format 통계와 knowledge candidate 생성 |
| Competitor Engine | 브랜드·플랫폼·기간별 profile/monitoring snapshot; 원본 asset은 reference-only |
| Analytics Engine | 출처별 coverage, 최신성, 중복률, pattern confidence; 실제 광고 성과와 분리 |
| `modules/brandconnect` | 브랜드 campaign brief와 competitor pattern을 연결하되 보상/commission 사실은 별도 증거 필요 |
| `modules/affiliate` | 상품군별 검증된 pattern을 콘텐츠 전략에만 사용; offer/commission/link 근거로 사용 금지 |
| `modules/commerce` | 상품 상세 카피 구조 참고만; 제품 사실·가격·재고·리뷰를 광고에서 추출하지 않음 |
| `modules/shorts` | hook/problem/proof/offer/CTA를 script/scene hint로 적용; 광고 원본 asset 재사용 금지 |

### 2.6 판정과 최소 파일럿

- `BUY`: 먼저 Snipit에 상업적 레퍼런스 활용, 내부 분석 저장, export, API/Enterprise 권리 범위를 서면 확인한 뒤 조건부.
- `INTEGRATE`: 공식 developer API/export schema가 없어 현재 `NO-GO`.
- `BENCHMARK`: 지금 채택. 공통 CreativeReference, 보드, monitoring, 검색, pattern promotion 구조.
- `BUILD`: 현재 Competitor Learning 위에 vendor-neutral reference registry와 rights gate만 직접 보유.

가장 작은 가역 파일럿:

1. 약관의 영리 이용 금지와 실제 마케팅팀 사용 허용 범위를 벤더에게 서면 확인한다.
2. 허가 후 Free/체험 계정에서 브랜드 2개, reference 20개만 사람이 검토한다.
3. 원본 파일은 저장하지 않고 URL, 날짜, 플랫폼, 사람이 요약한 hook/CTA 패턴만 기록한다.
4. 조사시간 절감률, 중복률, 패턴 채택률을 측정한다. 실제 CTR/매출 개선은 발행 후 승인된 성과 소스가 생길 때까지 주장하지 않는다.
5. export/API가 계약되지 않으면 자동 integration을 종료하고 수동 research 도구로만 남긴다.

---

## 3. 구현 우선순위와 개발 단축 효과

### 바로 재사용할 것

벤더 코드가 아니라 기존 프로젝트 코드를 재사용한다.

1. AEDI-V 패턴은 `Shorts scene contract -> SceneProductMatchCandidate -> AffiliateRevenueRouter` 어댑터 설계로 연결한다.
2. Snipit 패턴은 기존 `CompetitorLearningExtractor/Statistics/Storage/Interface` 위에 `CreativeReference` 입력 계약과 rights gate만 추가하는 방향으로 연결한다.
3. 기존 Affiliate의 exact back-reference, enrollment, freshness, disclosure, human approval 게이트와 Commerce의 source/freshness/rights gate를 그대로 사용한다.
4. 두 외부 서비스 모두 Protected Core나 `WorkflowEngine`에 연결하지 않는다.

### 만들지 않을 것

- AEDI-V clone, YouTube Studio DOM 자동화, 비공개 tag API 호출
- Snipit clone, 내부 `/api/v1` 호출기, 광고 플랫폼 무단 수집기
- 경쟁 광고 원본 미디어/카피 데이터셋
- 예상 커미션·광고 지속기간을 실제 수익/ROAS로 변환하는 코드
- 계정 cookie/session을 모델·로그·repository에 전달하는 코드

### 다음 승인 Sprint의 가장 작은 단위

외부 서비스 도입보다 먼저 구현할 가치가 있는 공통 부분은 한 개다.

```text
Revenue Evidence Intake Contract
├─ SceneProductMatchCandidate
├─ CreativeReference
├─ Source/Rights/Freshness Receipt
├─ Human Review Receipt
└─ existing Affiliate/Commerce/BrandConnect/Competitor adapters
```

이 계약은 외부 API 없이 fixture로 검증할 수 있고 vendor 교체가 가능하다. 다만 현재 문서는 Research이며 구현 승인을 의미하지 않는다.

## 4. 미확인 사항 및 승인 게이트

### AEDI-V에 질의할 사항

- 공식 API, bulk export, candidate JSON/CSV, webhook, Enterprise data-processing 계약 존재 여부
- 영상·자막·프레임·채널 식별자·YouTube page content의 저장 위치, 보존기간, 삭제 SLA, 모델 학습 여부
- `<all_urls>`, `cookies`, `tabs`, `identity` 권한 각각의 필요성과 제한 가능성
- 쿠팡/브랜드 상품 목록의 제공 주체, freshness, 수수료 계산식, 품절 갱신 SLA
- 태그 등록의 idempotency, rollback, readback receipt, 변경된 영상 revision 감지

### Snipit에 질의할 사항

- 상업적 내부 분석이 약관상 허용되는 플랜과 서면 라이선스
- 공식 API/OpenAPI/SDK, service account, rate limit, webhook, export schema와 데이터 권리
- board/creative/chart/media export별 원본 권리와 재가공·보존·팀 공유 범위
- Meta/Instagram/Google/TikTok 데이터의 수집 근거, freshness, 삭제/정정, 계정 연결 scope
- Enterprise에서 raw reference가 아닌 aggregate/pattern export만 제공 가능한지

## Implementation Status

- 상태: `RESEARCH COMPLETE / IMPLEMENTATION NOT APPROVED`
- 벤더 코드 추가: 없음
- 외부 dependency 추가: 없음
- 계정/API/확장 연결: 없음
- 권고: 두 서비스는 각각 `benchmark`로 지식화하고, vendor-neutral intake contract가 승인될 때만 standalone Sprint로 구현한다.
