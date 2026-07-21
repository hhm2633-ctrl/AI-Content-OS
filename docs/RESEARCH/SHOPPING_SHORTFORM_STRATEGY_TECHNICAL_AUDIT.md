# 2026 쇼핑몰 숏폼 전략 리포트 기술 감사

Date: 2026-07-14

Source: `2026 쇼핑몰 숏폼 전략 리포트_homepage.pdf` (43 pages, Catenoid/Charlla)

Status: **RESEARCH ONLY - 외부 서비스 도입, 광고 집행, 게시, 계정 연결, 코드 구현 승인 아님**

## CTO 판정

이 PDF의 높은 가치는 "숏폼을 많이 만들라"는 조언이 아니라 **구매 직전의 질문을 업종별
결정적 장면으로 변환하는 분류체계**다. 현재 `ShortsModule`의 일반적인
`hook -> problem -> solution -> cta`를 대체하지 않고, Commerce 상품의 실제 질문과 근거를
`ConversionQuestion -> DecisiveSceneSpec -> PlacementManifest -> MeasurementReceipt`으로 연결하는
standalone 전환 콘텐츠 계약에 활용할 가치가 있다.

반면 이 문서는 독립 학술·시장 조사라기보다 Charlla 제품 도입을 유도하는 vendor report다.
수치에는 출처 기관명만 있고 보고서 제목·발행일·URL·표본·측정 기간·산식이 없으며, 고객 사례도
대조군과 attribution 정의가 없다. PDF에는 실제 embed snippet, SDK, API, event schema, dashboard
metric definition, player configuration 또는 라이선스가 없다. 따라서:

- **ADOPT:** 업종별 27개 촬영 유형, 구매 질문 중심 기획, placement와 creative를 분리하는 구조
- **BUILD CLEAN-ROOM:** 프로젝트 소유의 scene/placement/experiment/measurement 계약
- **BUY/INTEGRATE LATER:** Charlla 또는 대체 video-commerce player는 vendor due diligence 뒤
- **REJECT:** 브랜드 screenshot·QR·카피 복제, vendor 통계를 성과 보장으로 사용, 조회와 구매 인과 혼동

## 감사 방법과 증거 상태

- `pypdf`로 43쪽 전체 텍스트를 추출했다. 43쪽은 추출 텍스트가 없는 빈 페이지다.
- 표지, 전략 논리, 체크리스트, 업종별 도입 페이지, 패션 예시, 최종 embed/measurement 표와 CTA를
  포함한 14쪽(1, 3-7, 11, 16, 21, 26, 31, 36, 40, 42)을 110 DPI로 렌더링했다.
- 4쪽 체크리스트, 7쪽 widget 사례, 40쪽 기능 비교표는 원본 크기로 추가 확인했다.
- 아래 라벨로 사실의 종류를 구분한다.

| 라벨 | 의미 |
|---|---|
| `PDF-FACT` | PDF에 실제로 적혀 있거나 화면으로 확인한 내용 |
| `AUTHOR-ADVICE` | 저자가 권하는 전략. 성과가 검증됐다는 뜻은 아님 |
| `VENDOR-CLAIM` | Charlla 기능·성과·고객사에 관한 판매자 주장 |
| `INFERENCE` | 현재 repository와 기술 계약에 매핑한 CTO 판단 |
| `REUSABLE-CONTRACT` | 원문 표현·media를 복사하지 않고 clean-room으로 구현 가능한 구조 |

## 문서가 실제로 제안하는 시스템

`PDF-FACT` 3-5쪽은 SNS와 자사몰의 역할을 분리한다. SNS 숏폼은 인지·유입을 만들지만, 상품
페이지의 숏폼은 구매 전 불확실성을 해소하는 "전환 콘텐츠"여야 한다. 4쪽 체크리스트는 다음
실패 패턴을 제시한다.

- 유행 때문에 영상을 만들고 역할을 정의하지 않음
- SNS에서 반응한 영상을 자사몰에 그대로 재사용
- 고객 문의·리뷰의 반복 질문을 영상으로 옮기지 않음
- 상품 설명은 텍스트에 맡기고 영상은 장식으로 사용
- 구매 직전 궁금한 장면을 보여주지 못함
- 상품 설명보다 브랜드 이미지 영상이 많음

`AUTHOR-ADVICE` 이 진단은 타당한 문제 정의지만, "4개 이상이면 전략 재검토"라는 기준은 검증된
scoring model이 아니다. 체크리스트를 품질 진단의 질문으로는 사용할 수 있지만 점수·합격선은
프로젝트가 실제 데이터로 보정해야 한다.

문서의 핵심 흐름은 다음으로 정규화할 수 있다.

```text
구매 직전 질문
  -> 업종별 결정적 장면
  -> 소유·허가된 실제 제품 영상
  -> 상세페이지/메인/썸네일/배너 placement
  -> 노출·재생·CTA·장바구니·구매 event
  -> 실험 단위의 효과 판정
```

마지막 두 단계는 PDF가 필요성만 주장할 뿐 구현 계약을 제공하지 않는다.

## 업종별 27개 재사용 가능한 촬영 템플릿

아래는 제목을 분류용 taxonomy로 요약한 것이다. 원문 screenshot, video, QR, 설명문은 Catenoid의
`ALL RIGHTS RESERVED` 자료이며 production asset으로 재사용하지 않는다.

| 업종 | PDF 페이지 | 결정적 장면 taxonomy | 답하는 구매 질문 | 주요 claim 위험 |
|---|---:|---|---|---|
| 패션 | 7 | `multi_angle_360` | 앞·뒤·옆 핏과 숨은 detail은? | model/body representation |
| 패션 | 8 | `detail_closeup` | 봉제·단추·질감의 완성도는? | 내구성·품질 과장 |
| 패션 | 9 | `material_behavior` | 탄성·복원·광택·흐름은? | 시험 조건 누락 |
| 패션 | 10 | `seasonal_lookbook` | 함께 입었을 때 mood는? | conversion보다 brand 목적 |
| 뷰티 | 12 | `application_texture_test` | 제형·발림·밀착·발색은? | 보정·피부 tone 차이 |
| 뷰티 | 13 | `before_after` | 사용 전후 무엇이 달라지는가? | 화장품 효능·표시광고 고위험 |
| 뷰티 | 14 | `mechanism_3d_explainer` | 성분이 어떻게 작용하는가? | 실제 작용을 animation으로 오인 |
| 뷰티 | 15 | `customer_review` | 실제 사용자는 무엇을 경험했나? | 후기 진위·대가·동의·likeness |
| 푸드 | 17 | `quick_recipe` | 얼마나 쉽게 조리하는가? | 조리시간·결과 재현성 |
| 푸드 | 18 | `origin_trace` | 어디서 누가 생산했는가? | 원산지·생산자 증빙 |
| 푸드 | 19 | `pairing_recipe` | 어떻게 활용하면 좋은가? | 알레르기·영양·음주 표현 |
| 푸드 | 20 | `hygiene_process` | 제조·포장이 위생적인가? | 인증·공정 대표성 |
| 홈앤리빙 | 22 | `in_room_scale` | 내 공간에 맞고 어울리는가? | scale·lens 왜곡 |
| 홈앤리빙 | 23 | `real_use_result` | 사용하면 무엇이 달라지는가? | "3초 제거" 같은 정량 claim |
| 홈앤리빙 | 24 | `stress_test` | 오염·충격·압력에 견디는가? | test protocol·범위 |
| 홈앤리빙 | 25 | `brand_mood` | 이 brand가 내 취향과 맞는가? | direct conversion 근거 약함 |
| 스포츠 | 27 | `dynamic_motion` | 실제 운동 중 어떻게 움직이는가? | 연출을 성능으로 오인 |
| 스포츠 | 28 | `functional_test` | 방수·통기·보온 차이는? | 시험 표준·대조군·조건 |
| 스포츠 | 29 | `field_use` | 실제 환경에서 안정적인가? | 대표성·안전 주장 |
| 스포츠 | 30 | `active_fit` | 움직일 때 fit·신축성은? | model/body variation |
| 소형가전 | 32 | `performance_demo` | 핵심 성능이 눈에 보이는가? | 측정 단위·안전·과장 |
| 소형가전 | 33 | `competitor_comparison` | 유사 상품보다 무엇이 낫나? | 비교 기준·상표·공정성 고위험 |
| 소형가전 | 34 | `expert_review` | 안전하고 믿을 만한가? | 전문가 자격·대가·endorsement |
| 소형가전 | 35 | `ten_second_howto` | 작동·세척·분리가 쉬운가? | 안전 경고 생략 |
| 반려동물 | 37 | `authentic_pet_reaction` | 내 반려동물도 좋아할까? | 개별 반응을 일반화 |
| 반려동물 | 38 | `fit_safety_demo` | 착용·설치·작동이 안전한가? | 안전 인증·사용 조건 |
| 반려동물 | 39 | `behavior_change` | 문제 행동이 해결되는가? | 치료·행동 개선 인과 고위험 |

이 taxonomy는 `pattern_type`이 아니라 `decision_scene_type`이다. SNS hook이나 편집 style과 섞지
않아야 같은 제품 영상도 owned-store, affiliate, brand campaign, retargeting ad 목적에 맞게 다른
opening/CTA/disclosure를 붙일 수 있다.

## 통계·사례의 데이터 품질 감사

| 페이지 | PDF 주장 | 증거 품질 | 사용 규칙 |
|---:|---|---|---|
| 6 | W컨셉 숏폼 상품 전환율 6.2%, 일반 상품 대비 약 4배; 구매 건수 182%, 매출 98% 증가; 60세 이상 59% 시청 경험 | 한국경제신문·한국방송통신전파진흥원 이름만 있음. 기간, 모집단, 분모, URL 없음 | 외부 원문 재검증 전 KPI baseline이나 영업 claim으로 사용 금지 |
| 11 | 뷰티 소비자 71%가 구매 전 숏폼 시연 시청 | 오픈서베이 이름만 있음. 질문 문구·표본·시점 없음 | 방향성 hypothesis로만 사용 |
| 16 | 식품 구매자 64%가 recipe 영상 후 구매 경험; Instagram 21.6%, YouTube 9.0% 직접 구매 경험 | DMC Media·오픈서베이 이름만 있고 조사 간 정의가 다를 수 있음 | 서로 비교하거나 attribution 비율로 사용 금지 |
| 16 | 고객사 전환율이 3%대까지 증가 | `VENDOR-CLAIM`; baseline, test design, 기간, traffic mix 없음 | 인과 또는 기대 uplift로 사용 금지 |
| 21 | 2019 대비 2024 가구 online 판매액 60%+ 증가 | "온라인 쇼핑동향조사"만 표기 | 원자료 확인 전 market sizing 금지 |
| 26 | 스포츠 구매자 72%가 기능 시연 영상 선호; 2035 시장 509조 원 | WGSN·Market.US 이름만 있음. 환율·시장 범위·forecast model 없음 | TAM/ROI 계산에 사용 금지 |
| 31 | 가전 구매 시 영상 review 참고 81%, 1분 이내 unboxing/guide가 가장 영향력 | Nasmedia report 이름만 있고 문항·표본 없음 | creative brief 가설로만 사용 |
| 31 | 상세페이지 평균 10개+ 영상, loading 0.9초 | 고객사 testimonial; 측정 도구, network/device, LCP/load 정의 없음 | 성능 SLA로 사용 금지 |
| 36 | 반려동물 월 비용 13만-16만원, offline 구매 36% | 오픈서베이 이름만 있음 | Commerce audience fact로 승격 금지 |
| 40 | 고화질, 수십 개도 지연 없음, page/video별 구매 전환 dashboard | 제품 기능 주장. event·attribution·data export 계약 없음 | vendor demo와 metric dictionary 검증 필요 |

PDF의 수치와 고객사는 `source_type: vendor_report`, `evidence_grade: unverified_secondary`로만
저장할 수 있다. 실제 콘텐츠 claim이나 투자 판단에 사용하려면 원문 URL, 제목, 발행일, 표본, 기간,
metric definition과 재현 가능한 산식을 별도로 확보해야 한다.

## PDF에 있는 도구·코드·설정 자산

### 확인된 도구·placement

- `PDF-FACT` 7쪽: 페이지 측면 고정 `floating widget`
- `PDF-FACT` 15쪽: 여러 영상을 넘기는 `slide widget`
- `PDF-FACT` 30쪽: main page용 `thumbnail player`
- `PDF-FACT` 40쪽: detail page, thumbnail, banner 등 여러 위치에 한 줄 code로 삽입한다고 주장
- `PDF-FACT` 40쪽: 원본 고화질, 다수 영상 경량화, conversion dashboard를 주장

### 직접 재사용 가능한 코드 여부

**없다.** PDF에는 다음이 전혀 없다.

- 실제 `<script>`/`iframe`/custom element embed code
- player SDK·API·webhook·package·repository·license
- CMS/Cafe24/SmartStore 연동 contract
- video encoding ladder, codec, CDN/cache, poster/lazy-load configuration
- consent/cookie/PII/data processor 설명
- analytics event name, session/user identity, attribution window, purchase join rule
- experiment assignment, holdout, bot/internal traffic exclusion, refund/cancel handling
- accessibility caption, keyboard, screen reader, reduced-motion 정책

QR과 branded screenshots는 reference media이지 코드가 아니다. QR destination을 자동 방문하거나
추적 parameter를 분석하지 않았다. Charlla private player를 reverse engineer하지 않는다.

## 프로젝트가 소유해야 할 clean-room 계약

### 1. `ConversionQuestionBrief`

```json
{
  "brief_id": "deterministic-hash",
  "product_ref": "internal-product-ref",
  "category": "fashion",
  "funnel_stage": "product_decision",
  "question_source": "verified_support_log | verified_review | owner_brief",
  "question_evidence_refs": [],
  "purchase_question": "What does the fit look like from every angle?",
  "allowed_claim_refs": [],
  "blocked_claims": [],
  "requires_disclosure": false,
  "status": "draft"
}
```

고객 문의·review를 사용한다면 실제 승인된 source와 PII 제거가 필수다. PDF가 예시한 질문을 실제
customer voice로 오인하지 않는다.

### 2. `DecisiveSceneSpec`

```json
{
  "scene_id": "scene-001",
  "brief_id": "deterministic-hash",
  "decision_scene_type": "multi_angle_360",
  "decision_question": "...",
  "shot_list": [],
  "required_evidence_refs": [],
  "test_protocol_ref": null,
  "comparison_target_authorized": false,
  "claim_risk": "medium",
  "asset_rights_required": true,
  "acceptance_checks": ["product_identity", "claim_match", "rights_ready"],
  "approval_status": "draft"
}
```

`ShortsModule.shorts_scene_plan_result`의 scene과 연결하되 기존 script/caption/audio/render contract를
변경하지 않는다. `decision_scene_type`은 additive metadata다.

### 3. `VideoPlacementManifest`

```json
{
  "placement_id": "deterministic-hash",
  "content_id": "sha256:...",
  "product_ref": "internal-product-ref",
  "surface": "owned_product_page | owned_home | social | ad | brand_campaign",
  "placement_type": "inline | floating | slider | thumbnail | banner",
  "page_context": "product_detail",
  "position_ref": "after-benefit-section",
  "autoplay": false,
  "muted": true,
  "plays_inline": true,
  "preload": "metadata",
  "poster_asset_ref": "...",
  "caption_track_ref": "...",
  "cta": {"type": "product_purchase", "destination_ref": "internal-product-ref"},
  "experiment_id": null,
  "publish_approved": false
}
```

PDF가 `floating/slider/thumbnail`을 보여주지만 어느 placement가 더 낫다는 비교 증거는 없다. placement는
creative와 별도 version/hash로 관리해야 한다.

### 4. `CommerceVideoClaimReceipt`

```json
{
  "receipt_id": "deterministic-hash",
  "content_id": "sha256:...",
  "product_ref": "internal-product-ref",
  "claim_refs": [],
  "volatile_fact_checked_at": null,
  "test_protocol_ref": null,
  "before_after_review": "not_applicable",
  "comparison_review": "not_applicable",
  "expert_endorsement_review": "not_applicable",
  "rights_receipt_refs": [],
  "human_approval": false,
  "render_allowed": false
}
```

이 receipt는 `CommerceModule`의 source/freshness/permission gate를 강화하는 downstream artifact다.
영상 자체가 price, stock, review, 효능, 안전, 구매 경험의 증거가 되지 않는다.

### 5. `VideoCommerceEvent`와 `ExperimentReceipt`

```json
{
  "event_schema_version": "1.0",
  "event_id": "opaque-id",
  "occurred_at": "timezone-aware timestamp",
  "anonymous_subject_id": "rotating-pseudonymous-id",
  "session_id": "opaque-session-id",
  "content_id": "sha256:...",
  "placement_id": "deterministic-hash",
  "product_ref": "internal-product-ref",
  "experiment_id": "exp-id",
  "variant_id": "control | treatment",
  "event_type": "eligible_impression | player_visible | play_start | progress_25 | progress_50 | progress_75 | complete | cta_click | add_to_cart | checkout_start | purchase | refund | cancel",
  "source": "first_party_approved",
  "is_measured": true
}
```

`ExperimentReceipt`는 assignment unit, eligibility, exposure definition, start/end, control/treatment,
sample counts, exclusions, metric version, analysis timestamp와 refund/cancel window를 보존해야 한다.
단순 video viewer와 purchaser를 비교하면 selection bias가 생기므로 uplift라고 부르지 않는다.

## Owned-site player의 최소 기술 요구사항

다음은 PDF의 코드가 아니라 `INFERENCE`인 provider-neutral acceptance criteria다.

```html
<video controls playsinline muted preload="metadata" poster="/owned/poster.webp"
       data-content-id="sha256-..." data-placement-id="placement-...">
  <source src="/owned/product-demo.mp4" type="video/mp4">
  <track kind="captions" srclang="ko" src="/owned/product-demo.ko.vtt" default>
</video>
```

- below-the-fold player는 poster 우선, viewport 근접 시에만 source attach/load
- autoplay는 platform/browser 정책과 접근성을 고려해 muted·playsinline 조건에서도 실험 변수로 관리
- width/height 또는 aspect-ratio를 미리 확보해 CLS 방지
- LCP/INP/CLS, player JS bytes, media bytes, request count, long task를 placement별 수집
- caption/VTT, keyboard controls, focus, reduced motion, audio 설명 필요 여부를 QA
- first-party consent 상태 전에는 marketing identity/event 전송 차단
- raw product URL, affiliate tracking secret, PII를 event payload에 넣지 않음
- third-party script 장애가 product page와 checkout을 막지 않도록 async/fallback/remove switch 제공
- player unavailable이면 poster와 핵심 text facts를 유지하며 구매 flow는 정상 동작

"영상 10개인데 0.9초"라는 PDF 사례를 재현 목표로 삼지 않는다. 실제 target은 현재 site baseline과
mobile network/device 분포를 측정한 뒤 budget으로 정한다.

## 수익화 채널 매핑

| 영역 | 이 자료가 주는 입력 | 기존 계약과 연결 | 반드시 막아야 할 오해 |
|---|---|---|---|
| Shorts/Reels | 결정적 장면·shot taxonomy | `modules/shorts/shorts_module.py` scene metadata, `shorts_exporter.py` rights-validated assets | 자사몰 전환 장면이 SNS hook으로 자동 성공하지 않음 |
| Commerce | product-use/demo/compare/guide brief | `modules/commerce/commerce_module.py` fact/freshness, Phase 2 dry-run/approval | generated/demo video가 상품 사실 증거가 아님 |
| Affiliate | 제품 질문에 맞는 scene와 CTA 후보 | `modules/affiliate/`의 verified program/offer/disclosure/human approval 뒤 | owned-store purchase CTA와 affiliate tracking link를 혼합하지 않음 |
| Naver BrandConnect | seller/creator deliverable의 shot list·rights checklist | `BRANDCONNECT_PHASE_1_CONTRACT`의 campaign/link/disclosure receipt | vendor 사례를 brand campaign 성과 증거로 제출하지 않음 |
| Paid Ads | conversion question별 retargeting creative variant | 향후 approved ad account adapter 앞의 offline creative manifest | PDF는 Meta/Google ads 성과·정책·집행법을 제공하지 않음 |
| Measurement | content+placement+product event taxonomy | 실제 first-party analytics가 승인될 때 별도 external-data adapter | play/view와 incremental purchase를 동일시하지 않음 |
| Brand/AdSense | product page engagement와 reusable footage | brand mood asset은 p25 유형, site performance guardrail 필요 | AdSense 수익 최적화 자료가 아니며 player가 광고 수익을 보장하지 않음 |

Affiliate/BrandConnect에서는 경제적 이해관계 공개를 영상·caption·landing context에 맞게 검토한다.
실제 link, commission, purchase, settlement는 각각 승인된 외부 source receipt가 없으면 null이다.

## 촬영·제작 workflow

문서의 27개 유형을 실제 생산에 쓰려면 다음 순서를 권장한다.

```text
verified product facts + approved customer questions
  -> ConversionQuestionBrief
  -> one decision_scene_type
  -> claim/test/rights risk review
  -> ShotSpec + acceptance checks
  -> owner-shot or licensed asset capture
  -> ShortsEditingPackage / captions / local QA
  -> channel-specific opening, CTA and disclosure variants
  -> PlacementManifest
  -> human approval
  -> manual publish or approved adapter
  -> measured event/experiment receipts
```

특히 `before_after`, `functional_test`, `competitor_comparison`, `expert_review`,
`behavior_change`는 촬영 전 Compliance gate가 필요하다. 3D sequence는 approved mechanism을 설명하는
illustration으로 표시하고 실제 microscopic footage처럼 제시하지 않는다.

## Charlla 또는 대체 SaaS 도입 전 질문

40쪽의 one-line embed와 dashboard 주장을 평가하려면 vendor가 아래를 서면으로 제공해야 한다.

1. 실제 embed/API/SDK/export 문서, supported commerce platforms와 version policy
2. CSP/SRI, script domain, iframe isolation, dependency/permission, kill switch와 rollback
3. encoding profiles, codec fallback, CDN region/cache, signed URL expiry, asset export/exit
4. player JS/media performance benchmark의 device/network/tool/metric definition
5. caption, keyboard, screen reader, autoplay, reduced-motion 지원
6. cookie/identifier/PII, controller/processor 역할, subprocessors, retention/deletion, overseas transfer
7. impression/view/play/progress/click/conversion의 정확한 정의와 deduplication
8. attribution model/window, order join, cancel/refund, bot/internal traffic exclusion
9. raw event export/API/webhook, schema version, historical backfill과 ownership
10. pricing unit(traffic/storage/encoding/player view), overage, SLA, incident response, termination/export

이 자료만으로 Charlla를 선택할 수 없다. 기능 demo와 실제 계약·data export·performance test를 통과하면
**BUY**, export/API가 없거나 data lock-in이 크면 수동 external operator 또는 **REJECT**다.

## 가장 작은 가역적 파일럿

### Pilot 0 - 즉시 가능한 offline contract pilot

- 소유자 승인 상품 1개와 이미 repository에 있는 검증된 product facts만 사용
- 실제 고객 데이터 대신 owner가 명시한 구매 질문 3개 사용; customer voice라고 표시하지 않음
- `ConversionQuestionBrief` 3개와 서로 다른 `DecisiveSceneSpec` 3개 생성
- 영상·API·SaaS 없이 claim/rights/test/disclosure blocker가 올바르게 fail closed 되는지 검토
- 성공 기준: 모든 scene이 source claim과 연결되고 고위험 유형은 approval 전 `render_allowed=false`

### Pilot 1 - local owned-asset prototype

- owner-shot 5-10초 product clip 1개, poster 1개, VTT caption 1개
- local static product page에서 `inline` 한 placement만 구현
- network/account/publish 없이 browser에서 lazy load, keyboard, caption, fallback, CLS를 확인
- vendor script와 third-party tracking은 사용하지 않음
- 성공 기준은 baseline 대비 측정 가능한 page-performance 차이와 QA pass이며 구매 성과를 만들지 않음

### Pilot 2 - 승인 후 controlled live experiment

- product 1개, placement 1개, control/no-video와 treatment/video만 비교
- 사전 고정한 eligibility, random assignment, exposure, primary metric, guardrail, duration 사용
- purchase와 refund/cancel은 approved first-party order receipt로만 join
- 시작 전 privacy/consent, site owner, product/claim/rights, analytics, deployment/rollback 승인
- sample-size나 uplift target은 baseline 없이 만들지 않음

### 채널 파생 pilot

- BrandConnect: 동일 ShotSpec으로 offline deliverable package만 생성; 신청·message·link·게시 없음
- Affiliate: `SceneProductMatchCandidate`까지만 생성; 실제 link/commission/settlement 없음
- Ads: hook/CTA만 바꾼 `CreativeVariantManifest` 작성; ad account 연결·spend·upload 없음

## 구현 우선순위

1. **ADOPT now as research vocabulary:** 27개 `decision_scene_type`와 5개 공통 계약
2. **NARROW BUILD:** Offline `ConversionQuestionBrief`/`DecisiveSceneSpec` fixture pilot
3. **MANUAL PRODUCTION:** 기존 Shorts editing package로 owner-shot asset 검증
4. **MEASUREMENT GATE:** first-party event/experiment contract와 privacy 승인
5. **BUY/INTEGRATE decision:** Charlla와 대체 player를 동일 acceptance criteria로 비교
6. **CHANNEL EXTENSION:** Affiliate, BrandConnect, Ads는 각 기존 approval gate 뒤에서만 파생

`WorkflowEngine`, CardNews protected core, live Commerce upload, affiliate link generation, BrandConnect
UI, ad accounts 또는 publishing에는 연결하지 않는다.

## 저작권·플랫폼 정책·데이터 정직성

- PDF 표지와 마지막 페이지는 `© CATENOID INC. ALL RIGHTS RESERVED`라고 표시한다.
- example brand screenshot, video still, QR, logo, 카피는 분석용 `competitor_reference`이며
  `render_allowed=false`다. 해당 브랜드가 Catenoid에 제공한 권리가 우리에게 이전되지 않는다.
- 고객 review·전문가·model·생산자·작업자·반려동물 owner의 likeness/voice와 광고 대가를 확인한다.
- 비교·before/after·기능 시험은 조건, 횟수, 대조군, 편집 여부와 한계를 보존한다.
- 구매 전환율, revenue, view, play, engagement는 실제 source와 metric version 없이는 생성하지 않는다.
- platform별 synthetic media, endorsement, branded content, affiliate disclosure와 광고 심사 정책은
  파일럿 시점에 공식 문서로 재검증한다.
- video를 여러 채널에 재사용할 때 license의 channel, territory, duration, paid media permission을
  별도 확인한다.

## 확인되지 않은 항목

- PDF 통계의 원문 보고서와 정확한 조사 설계
- Charlla embed code, API/SDK, supported platforms, data schema와 commercial terms
- dashboard의 conversion 산식, attribution window와 order/refund 처리
- 0.9초 사례의 측정 방법과 환경
- 각 example brand video의 제작 조건, 비용, 매출 인과와 media rights
- QR destination의 현재 상태와 tracking behavior(의도적으로 접근하지 않음)

## 구현 상태

Research only. 원본 PDF는 수정하지 않았다. 외부 website, QR, account, ad platform, API, upload,
publish, paid service 또는 proprietary code에 접근하지 않았다. 문서와 전용 임시 PDF artifacts 외
repository code/tests/storage/shared status documents는 변경하지 않았다.
