# REBORN Automation Kit 공개 기술 재사용 감사

- 조사일: 2026-07-14 (Asia/Seoul)
- 조사 대상: [AI Hub](https://rebornlabs.kr/ai-hub.html), [Automation Kit](https://rebornlabs.kr/kit.html), [개인정보처리방침](https://rebornlabs.kr/privacy.html), [카드결제 상품](https://ctee.kr/item/store/99077), [공개 PDF manifest](https://rtozdreykeuqlwntulkc.supabase.co/storage/v1/object/public/podcast/ai_insta/pdfs/index.json)
- 상태: 공개 증거 기반 기술 연구만 완료. 구매·폼 제출·API mutation·계정 연결·패키지 설치·실행·vendor code 복제는 하지 않았다.

## CTO 판정

| 분류 | 판정 |
|---|---|
| `DIRECT-CODE` | **없음** — 공개 repository/source archive와 재사용 가능한 코드 라이선스를 확인하지 못함 |
| `SERVICE-ADAPTER` | **없음** — 공개 developer API/SDK/CLI/OpenAPI/export contract를 확인하지 못함 |
| `CONFIG-AS-CODE` | **없음** — 구매 전 공개된 module manifest/config schema/license가 없음 |
| `CLEAN-ROOM-PATTERN` | **조건부 채택** — preflight, `.env`, config, dry-run, approval, schedule, control-room 패턴 |
| `BUY` | **현재 NO-GO** — 모듈/업데이트/개인정보/라이선스 범위 불일치 해소와 샘플 코드 검증 전 구매하지 않음 |
| `BUILD` | 전체 kit 복제는 `REJECT`; 기존 프로젝트에 없는 작은 계약만 clean-room으로 추가 |
| `BENCHMARK` | **GO** — 판매 funnel, module catalogue, operator onboarding, revenue attribution의 장단점 참고 |

이 제품은 AI-Content-OS가 이미 보유한 CardNews, Shorts, Commerce, Affiliate, Knowledge, Analytics, 승인 게이트와 상당히 중복된다. 공개 상태에서 바로 가져올 수 있는 코드는 없으며, 가격이 싸다는 이유만으로 38개 모듈을 import하는 것은 개발 가속이 아니라 공급망·라이선스·중복 위험을 한꺼번에 들이는 선택이다.

## 증거 등급

- `VERIFIED PUBLIC FACT`: 인증 없이 공개 페이지/정적 클라이언트/공개 manifest에서 직접 확인.
- `MARKETING CLAIM`: vendor가 공개 페이지에서 주장하지만 실제 구매 산출물이나 실행으로 검증하지 못함.
- `OBSERVABLE INTERFACE`: 브라우저 코드에 endpoint·payload 경계가 보이지만 공개 API 계약은 아님.
- `INFERENCE`: 공개 동작에서 도출한 독립 구현 제안. vendor 내부 구현 사실로 주장하지 않음.

접근 가능한 JavaScript가 곧 오픈소스는 아니다. 공개 페이지의 inline script는 동작 확인에만 사용했으며 저장소로 복사하지 않았다.

---

## 1. 공개 표면에서 확인된 구조

### 1.1 AI Hub

`VERIFIED PUBLIC FACT`:

- Hub는 무료 PDF, ₩99,000 무통장 kit, ₩117,000 CTEE 카드결제, 월 ₩149,000 운영대행, ₩69,000 landing guide를 연결한다.
- Supabase public bucket의 `pdfs/index.json`을 읽어 동적 PDF 목록을 만든다.
- PDF/kit/guide/대행/카드결제 클릭을 `hub-event`로 기록하고, `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, referrer를 전송한다.
- kit/guide/대행 링크에 UTM을 전파한다.

`OBSERVABLE INTERFACE`:

```text
POST https://mobility.rebornlabs.kr/api/hub-event
body: kind, label, utm_source, utm_medium, utm_campaign, utm_content, referrer
transport: sendBeacon or fetch keepalive
```

이는 공개 developer API가 아니다. endpoint의 인증, 스키마 버전, retention, idempotency, rate limit, 오류 계약은 공개되지 않았다. 호출기나 adapter를 만들지 않는다.

### 1.2 Supabase PDF manifest

2026-07-14 GET 결과:

- public read, `Content-Type: application/json`, CORS `*`, cache `public, max-age=60`.
- 최상위 필드는 `updated`, `count`, `items`이며 당시 `updated: 20260714`, `count: 25`였다.
- 각 item은 `title`, `tool`, `tagline`, `date`, `url`, `source`를 포함했다.
- item `url`은 같은 public Supabase bucket PDF를, `source`는 외부 기사/GitHub 원자료를 가리켰다.

이 JSON은 좋은 **source-linked content manifest 패턴**이지만 재사용 라이선스, schema version, content hash, rights status, source retrieval time, supersedes 관계가 없다. JSON과 PDF가 공개 다운로드 가능하다는 사실만으로 상업적 복제·학습·재배포 권리가 생기지 않는다. 우리 프로젝트는 데이터를 가져오지 않고 아래 clean-room 보완 필드만 참고한다.

```json
{
  "schema_version": "research_asset_manifest.v1",
  "asset_id": "deterministic-id",
  "title": "...",
  "source_url": "https://...",
  "source_retrieved_at": "timezone-aware ISO-8601",
  "asset_url": "https://...",
  "asset_sha256": "...",
  "rights_status": "reference_only|licensed|owned|unknown",
  "render_allowed": false,
  "supersedes": null
}
```

### 1.3 Kit landing과 module catalogue

`VERIFIED PUBLIC FACT`인 것은 **페이지에 아래 문구가 존재한다는 사실**뿐이다.

- Module catalogue는 콘텐츠 20, 영업·비서 5, 문서·서류 7, 운영·관측 4, 소상공인 백오피스 2로 합계 38개를 열거한다.
- 공개된 이름에는 `coupang-picks`, `affiliate-short`, `short-video`, `cardnews`, `threads-publisher`, `naver-blog-lite`, `web-scraper`, `gmail-secretary`, `cold-outreach`, `doc-parse`, `knowledge-chat`, `control-room`, `llm-gateway`, `analytics` 등이 포함된다.
- 설치 흐름은 zip 해제 -> Claude Code -> `node tools/preflight.mjs` -> `.env` -> config -> dry-run -> 사람 승인 -> schedule이라고 설명한다.
- 1인/1사, 재판매·재배포 금지를 footer에 표시한다.

다음은 구매 산출물을 보지 못했으므로 `MARKETING CLAIM`이다.

- 실제로 38개 모듈이 모두 포함되고 실행 가능하다.
- 8개 채널, 매일 70+ 자동 작업이 안정적으로 무인 실행된다.
- 모든 것이 로컬로 실행되고 데이터가 구매자 소유다.
- secret이 항상 `.env`에만 있고 code/log/prompt/child process에 노출되지 않는다.
- 모든 발행·발송이 dry-run과 승인 뒤에만 실행된다.
- `preflight.mjs`가 Node/Python/version/tool/provider를 충분히 검증한다.
- 표시광고법 문구 자동 삽입만으로 규정 위험이 없어진다.
- 블로그 자동 타이핑이 복붙 감지나 어뷰징을 안전하게 피한다.
- 평생 자동 업데이트가 지속된다.

공개 source tree, dependency lockfile, module fixture, test report, sample manifest, SBOM, security policy, changelog가 없으므로 위 주장을 코드 품질 증거로 사용할 수 없다.

---

## 2. 공개 endpoint와 funnel 계약

아래는 landing inline script에서 관찰한 인터페이스다. **호출하거나 mutation하지 않았다.**

### 2.1 `kit-track`

```text
POST https://mobility.rebornlabs.kr/api/kit-track
events: pageview, cta_click, order_open, order_submit
body: visitor_id, event, UTM 5종, referrer, path+query
```

- `kv`: random visitor ID, 365일 cookie.
- `ka`: 최초 UTM object, 365일 cookie.
- `SameSite=Lax`, `path=/`; 공개 script상 `Secure`, `HttpOnly`는 설정되지 않는다. JavaScript cookie이므로 `HttpOnly`는 적용할 수 없다.
- 최초 UTM cookie는 이후 직접유입이 덮지 않게 설계됐다.

`INFERENCE`: first-touch attribution pattern은 Revenue Analytics에 유용하지만, consent/retention/deletion/source receipt 없이 그대로 채택하면 안 된다.

### 2.2 `kit-lead`

```text
POST https://mobility.rebornlabs.kr/api/kit-lead
body: email, source, utm_source, utm_medium, utm_campaign
```

- 공개 form은 무료 cold-email PDF 전송용 이메일을 받는다.
- client validation 뒤 JSON POST한다.
- `fetch().catch(...).then(success UI)` 구조여서 네트워크/API 실패여도 완료 UI가 표시될 수 있다. 실제 전달 receipt가 없다.

### 2.3 `kit-order`

```text
POST https://mobility.rebornlabs.kr/api/kit-order
body: name, phone, email, depositor, honeypot, idempotency-like UUID,
      product, current full URL, visitor_id, first-touch UTM fields
```

- 무통장 주문 form은 이름·전화·이메일·입금자명을 수집한다.
- modal을 열 때 UUID를 만들어 `idem`으로 보내는 것은 idempotency 의도를 보여준다. 서버 강제 여부는 UNKNOWN이다.
- 현재 전체 URL을 `referrer` 필드로 보내고 attribution cookie를 결합한다.
- lead와 동일하게 request failure를 삼킨 뒤 성공 UI를 표시할 수 있어 `order_submit` tracking과 실제 주문 저장이 불일치할 수 있다.
- response status/body/order ID/readback receipt를 확인하지 않는다.

### 2.4 공개 interface에서 배울 것과 버릴 것

| 패턴 | 판정 |
|---|---|
| first-touch UTM + stable visitor correlation | consent·TTL·deletion을 갖춘 clean-room schema로 제한 채택 |
| idempotency key | 서버 receipt와 request hash를 더해 채택 |
| funnel event vocabulary | `pageview -> cta -> order_open -> order_accepted -> payment_confirmed -> fulfilled`로 확장 |
| `catch` 후 무조건 성공 UI | **Reject** — false success |
| full path/query/referrer 전송 | **Reject by default** — token/PII query redaction 필요 |
| endpoint URL을 public API처럼 재사용 | **Reject** — private implementation surface |

우리 프로젝트에서 필요한 clean-room receipt:

```json
{
  "schema_version": "revenue_funnel_event.v1",
  "event_id": "uuid",
  "event_type": "lead_accepted|order_accepted|payment_confirmed|fulfilled",
  "occurred_at": "timezone-aware ISO-8601",
  "subject_id": "irreversible-opaque-id",
  "campaign": {
    "source": "...",
    "medium": "...",
    "campaign": "...",
    "content": "...",
    "term": "..."
  },
  "consent_receipt_id": "...",
  "request_hash": "sha256",
  "external_receipt_id": null,
  "is_measured": true,
  "revenue_amount": null,
  "settlement_verified": false
}
```

---

## 3. 개인정보·결제·라이선스 정합성 감사

### 3.1 개인정보와 cookie 불일치

[공개 개인정보처리방침](https://rebornlabs.kr/privacy.html)은 시행일 2026-07-04이며 Instagram Graph API를 통한 username/ID/comment/DM 처리와 PDF DM 전송을 주로 설명한다. “웹사이트 쿠키를 통한 별도의 개인 추적을 수행하지 않는다”고 명시한다.

그러나 Hub/Kit 공개 script는 다음을 실제로 한다.

- 365일 visitor/first-touch UTM cookie 생성.
- pageview/CTA/order event와 visitor ID, UTM, referrer, path/query 전송.
- lead 이메일 수집.
- 주문 이름, 전화, 이메일, 입금자명, full URL, visitor attribution 수집.

공개 방침은 이 web funnel의 수집 항목, 처리 목적, 보유기간, 위탁/수탁자, Supabase/Vercel/mobility host, lead/order 삭제 절차, cookie 거부 방법을 설명하지 않는다. Kit와 Hub footer에서도 조사 시점에 해당 방침 link를 확인하지 못했다. 구매 전에 개정 방침과 동의/고지 화면을 요구해야 한다.

### 3.2 가격·수량·업데이트 불일치

| 표면 | 공개 문구 |
|---|---|
| Hub 무통장 | ₩99,000, 평생 사용 |
| Kit hero/catalogue | 38개 모듈, 6개 영역(20+5+7+4+2 + bootstrap) |
| Kit pricing card | 26개 모듈, 4개 영역, 평생 자동 업데이트 |
| Kit 하단 CTA | 평생 사용, **1년 업데이트** |
| CTEE title/OG | ₩117,000, 평생 자동업데이트, **26모듈** |

판매 채널별 가격 차이는 결제수단 수수료 정책일 수 있으나 설명이 필요하다. 더 중요한 것은 동일 상품의 module count와 update term이 일치하지 않는다는 점이다. 주문 시점의 exact SKU, version, module manifest, update 기간과 channel별 권리를 계약서/영수증에 고정해야 한다.

### 3.3 공개 라이선스 범위

확인된 공개 문구는 다음뿐이다.

- 1인/1사 라이선스.
- 재판매·재배포 금지.
- 규제·저작권·플랫폼 약관·산출물 책임은 사용자에게 있음.

확인하지 못한 항목:

- 수정·파생물·내부 repository 반입·AI agent를 통한 수정 허용 범위.
- 회사 내 사용자/기기/worker/process 수.
- 외주 개발자, Git host, CI, backup 접근 허용.
- bundled third-party code/model/font/media별 license와 NOTICE.
- 상업적 산출물 소유권과 voice clone/stock/model output 권리.
- update 종료, vendor 폐업, download 재발급, 취약점 패치 의무.
- 환불·하자·지원 SLA와 버전 rollback.

Landing의 “데이터 내 소유”나 “평생 사용”은 source license가 아니다. 서면 전문을 보기 전에는 우리 repository에 어떤 파일도 반입하지 않는다.

---

## 4. 공개 코드·SDK·API·설정 재사용 감사

| 자산 | 공개 증거 | 법적/기술 판정 |
|---|---|---|
| Kit source repository | 확인 못함 | 재사용 불가 |
| Source zip/sample module | 구매 전 공개본 없음 | 품질·라이선스 검증 불가 |
| GitHub organization/core repo | 제품 소유로 확인되는 공개 repo 없음 | 재사용 불가 |
| npm/PyPI package | 제품 소유로 확인되는 package 없음 | 재사용 불가 |
| SDK/CLI/OpenAPI | 없음 확인 | service adapter 불가 |
| `preflight.mjs` | 파일명/실행 명령만 marketing page에 공개 | 코드 재사용 불가 |
| `.env`/config schema | 동작 주장만 공개; schema/example 없음 | config-as-code 불가 |
| 38-module manifest | HTML catalogue뿐; machine-readable versioned manifest 없음 | benchmark only |
| Supabase PDF `index.json` | public data manifest | schema pattern만 참고; 내용 복제 금지 |
| Hub/Kit inline scripts | 브라우저에서 접근 가능하나 라이선스 없음 | 관찰만; 복제 금지 |
| `hub-event`, `kit-lead/order/track` | client endpoint 이름/payload가 보임 | private interface; 호출/의존 금지 |

**정확히 재사용 가능한 vendor public asset: 0개.**

공개 PDF 중 일부가 MIT 등 공개 repository를 원자료로 가리켜도, Reborn이 만든 PDF 전체가 그 원 repository와 같은 라이선스를 가진다는 뜻은 아니다. 필요하면 원 repository를 별도로 공식 출처에서 감사해야 한다.

---

## 5. Clean-room 패턴과 AI-Content-OS 매핑

| Reborn에서 관찰한 패턴 | 기존 프로젝트 소비자 | 결정 |
|---|---|---|
| bootstrap interview -> module recommendation | Sprint Manager / 향후 operator setup | 설정 wizard 패턴만 benchmark; runtime Planner와 혼합 금지 |
| preflight -> `.env` -> config | QA, retry audit, provider adapter | provider/version/secret readiness receipt로 독립 구현 가능 |
| dry-run -> approval -> schedule | `modules/commerce` dry-run/approval, BrandConnect, Publishing | 이미 더 강한 fail-closed 계약이 있으므로 기존 코드 재사용 |
| module catalogue | External Engine Portfolio / Roadmap | versioned capability manifest 아이디어만 참고 |
| `coupang-picks` / `affiliate-short` | `modules/commerce`, `modules/affiliate`, `modules/shorts` | 실상품·offer·disclosure 근거 없이는 자동 실행 금지 |
| control-room | Analytics/Dashboard | 실제 run receipt와 fallback 상태만 표시; “무인 성공” 추정 금지 |
| knowledge vault | Knowledge Engine | 두 번째 knowledge store 금지 |
| PDF source manifest | Research/Knowledge provenance | rights/hash/version 필드를 보강한 독립 schema |
| first-touch funnel tracking | Revenue Analytics | consent + redaction + measured receipt가 갖춰진 후 Roadmap |
| lead/cold outreach | BrandConnect/향후 CRM | PII·수신동의·발송승인·unsubscribe 없이는 NO-GO |

### 우리가 직접 보유할 최소 계약

```text
CapabilityManifest
├─ capability_id / version / owner
├─ inputs / outputs / external_dependencies
├─ dry_run_supported / approval_required
├─ secrets / data classes / rights
├─ health_check / rollback / fallback
└─ evidence_receipts / implementation_status
```

이것은 vendor module을 베끼는 것이 아니라 현재 standalone 모듈의 상태와 승인 경계를 한 형식으로 보여주는 clean-room registry다. 구현은 별도 Sprint 승인 사항이다.

### 수익 경로별 판단

- **쿠팡/제휴**: `coupang-picks`, `affiliate-short` 이름은 방향성 증거일 뿐이다. 상품 source, 가격/재고 freshness, 프로그램 enrollment, official link, disclosure receipt가 공개되지 않아 기존 Affiliate Router보다 안전하거나 빠르다는 증거가 없다.
- **네이버/브랜드**: `naver-blog-lite`, outreach는 콘텐츠·영업 보조 후보지만 Naver BrandConnect/Shopping Connect 공식 link·campaign·성과 API를 해결하지 않는다.
- **Google/광고**: 공개 funnel은 UTM attribution의 최소 예시다. 실제 AdSense/Google Ads revenue import, spend, conversion, settlement 계약은 없다.
- **콘텐츠**: CardNews/Shorts/Knowledge는 현재 프로젝트와 직접 중복된다. 구매 이유는 결과 품질이 fixture benchmark에서 우월할 때뿐이다.

---

## 6. 구매 전 Due Diligence 체크리스트

다음 항목을 **결제 전에 서면으로** 받고, 답이 없으면 NO-GO를 유지한다.

### 상품·업데이트

- [ ] 현재 SKU/version과 machine-readable module manifest 제공.
- [ ] 38 vs 26, 6영역 vs 4영역의 정확한 차이와 판매 채널별 구성 확인.
- [ ] “평생 업데이트” vs “1년 업데이트” 중 계약상 우선하는 조건 확인.
- [ ] ₩99,000 무통장과 ₩117,000 카드 상품의 구성·권리·지원 차이 확인.
- [ ] update 전달 방식, 서명/hash, changelog, rollback, vendor 종료 시 최종본 보장 확인.

### 코드 품질·보안

- [ ] 결제 전 redacted source tree, module 1개 전문, `preflight.mjs`, `.env.example`, config schema, lockfile 제공.
- [ ] 지원 OS, Node/Python 최소/최대 version, Docker/ffmpeg/browser 의존성 확인.
- [ ] SBOM, dependency license, malware/secret scan, network endpoint inventory 제공.
- [ ] dry-run이 모든 publish/send/order 모듈에서 기술적으로 강제되는지 test 증거 확인.
- [ ] approval receipt, idempotency, audit log, retry/backoff, rate limit, rollback, crash recovery 확인.
- [ ] secret이 prompt/log/subprocess/error/report에 노출되지 않는 test 확인.
- [ ] auto-update package 서명, 공급망 검증, 임의 remote code execution 방지 확인.

### 데이터·플랫폼·수익 정직성

- [ ] Coupang/Naver/Meta/Google/YouTube별 공식 API, account scope, 정책 근거와 freshness SLA 확인.
- [ ] 상품 선정·commission·판매량·광고 성과가 추정인지 실제 source receipt인지 확인.
- [ ] 표시광고 문구 template만으로 legal approval을 주장하지 않는지 확인.
- [ ] blog human-typing/anti-detection 기능이 플랫폼 우회·bot evasion인지 확인; 해당 기능은 사용하지 않음.
- [ ] voice clone, generated media, screenshots, fonts, stock/music, third-party content 권리 확인.

### 개인정보·결제

- [ ] web lead/order/tracking/cookie를 포함하도록 개인정보처리방침 개정 및 링크 제공.
- [ ] 처리자/수탁자, 저장 region, retention, 삭제 SLA, breach response 확인.
- [ ] 365일 cookie의 consent/opt-out/delete와 full URL/query redaction 확인.
- [ ] order/lead endpoint의 success receipt, server validation, idempotency, abuse protection 확인.
- [ ] 카드/무통장 환불, 전자상거래 고지, 다운로드 미수신/하자 처리 절차 확인.

### 라이선스

- [ ] 1인/1사의 사용자·기기·worker·법인·외주자 범위 확인.
- [ ] source 수정, 내부 Git/backup/CI, AI coding agent 사용 허용 확인.
- [ ] 상업적 산출물 소유권과 고객 데이터/모델 output 권리 확인.
- [ ] bundled OSS/model의 license/NOTICE와 copyleft/noncommercial 제약 제공.
- [ ] 재배포 금지와 내부 배포/배포 artifact/container의 경계 확인.

### 제한된 평가 조건

위 문서 검토가 통과해도 즉시 active repository에 넣지 않는다.

1. 격리된 VM 또는 별도 test workspace에서 hash를 기록한다.
2. 네트워크 차단 상태로 source/dependency/secret/license scan을 먼저 한다.
3. 외부 계정·키 없이 sample fixture 한 개로 preflight/dry-run만 실행한다.
4. 우리 CardNews/Shorts/Affiliate fixture와 결과 품질·시간·fallback·정직성을 비교한다.
5. 우월한 bounded module만 별도 clean-room adapter 또는 라이선스가 허용하는 dependency로 제안한다.
6. Protected Core, active storage, 실계정, 자동 publish/send/order에는 연결하지 않는다.

## 최종 권고

- 지금 얻은 가장 가치 있는 자산은 vendor code가 아니라 **불일치와 위험을 포함한 제품 설계 증거**다.
- onboarding/preflight/dry-run/approval/control-room은 좋은 패턴이지만 프로젝트에 이미 상당 부분 구현되어 있다.
- 수익화 관점의 실질적 미충족 영역은 live product/offer/campaign/ad revenue evidence import인데, 공개 Reborn kit는 이 공식 데이터 계약을 입증하지 못한다.
- 따라서 현재는 `BENCHMARK`, 구매는 due diligence 완료 후 `CONDITIONAL`, repository import와 endpoint integration은 `NO-GO`다.

## Implementation Status

- Research document only.
- Public fact, marketing claim, observable interface, inference를 분리했다.
- 외부 package/source/API/account/credential를 추가하거나 실행하지 않았다.
- Vendor public code/config의 직접 재사용 승인: **없음**.
