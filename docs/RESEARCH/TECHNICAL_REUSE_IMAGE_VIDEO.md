# Halfdone 이미지·영상 자료 기술 재사용 감사

Date: 2026-07-14  
Status: **RESEARCH ONLY — 코드·계정·API·크레딧·미디어 생성 승인 아님**

## 감사 목적과 판정 기준

이 문서는 Halfdone 자료 4건을 단순 제품 추천이 아니라 **개발 가속을 위한 공개 구현 자산 감사**로
다시 분석한다. 타사 비공개 코드나 Halfdone의 프롬프트·강의 흐름은 복제하지 않았다. 공식 문서와
공식·공개 GitHub 저장소에서 확인한 SDK, CLI, API 계약, 샘플, 라이선스만 재사용 후보로 인정한다.

- `VERIFIED`: 공식 문서 또는 공식 조직의 공개 저장소에서 확인한 사실
- `INFERENCE`: 확인된 사실을 현재 저장소 구조에 매핑한 설계 판단
- `REUSE NOW`: 라이선스와 형식상 코드·도구를 즉시 평가할 수 있음. 설치·실행 승인을 뜻하지 않음
- `BLOCKED`: 라이선스·계정·비용·권리 또는 공개 코드 부재 때문에 코드 재사용 불가

## 결론 먼저

| Halfdone 자료 | 실제 재사용 결론 | 판정 |
|---|---|---|
| [AI로 카드뉴스 만드는 법](https://halfdoneclub.co/community/image-video-ai/6aea8176-eb26-44d1-aa4a-fabc84a8c82e) | Figma 공식 MIT 플러그인 샘플은 재사용 가능하지만 `html.to.design` 구현은 공개되지 않았다. 우리 Pillow Renderer를 버리지 말고, 필요할 때 CardNews JSON→Figma Node 플러그인만 별도 구축한다. | **BUILD + BENCHMARK** |
| [Higgsfield AI Influencer/Motion Control 자료](https://halfdoneclub.co/community/image-video-ai/72dac4af-e7c1-4a0a-a470-f46e3ba62f0b) | 공식 CLI, Python SDK, 에이전트 스킬이 공개되어 있다. 네 자료 중 **가장 즉시 재사용성이 높다**. 향후 standalone provider adapter는 CLI JSON 경계가 가장 짧다. | **INTEGRATE later / REUSE NOW candidate** |
| [DomoAI Talking Avatar/Video-to-Video 자료](https://halfdoneclub.co/community/image-video-ai/739fd40b-0f43-494f-99cd-9ad23a002d5c) | 공식 REST 요청·콜백 스키마는 명확하지만 공식 SDK/공개 저장소는 확인하지 못했다. 코드 복사가 아니라 API 계약만 채택하고 얇은 자체 adapter를 작성해야 한다. | **INTEGRATE later** |
| [Freepik Spaces→Kling 캠페인 자료](https://halfdoneclub.co/community/image-video-ai/3b568990-d524-4d9f-89eb-d7cc94ebe6df) | typed node DAG와 asset handoff 구조는 채택 가치가 크다. Freepik MCP와 Kling ComfyUI 노드는 공개됐지만 명시적 라이선스가 없어 코드 복사는 차단한다. | **BENCHMARK + BUY/manual** |

현재 바로 프로젝트에 복사할 타사 완제품 모듈은 없다. 그러나 Higgsfield CLI/SDK와 Figma 샘플은
승인 후 adapter 시간을 크게 줄이고, LivePortrait는 미래 로컬 아바타 대안이 된다. 나머지는 코드보다
**비동기 작업 계약, typed workflow graph, provenance manifest**를 가져오는 것이 더 빠르고 안전하다.

## 1. 카드뉴스 HTML → Figma 워크플로

### 자료에서 확인한 워크플로

`VERIFIED` Halfdone 공개 페이지는 Gemini/Claude로 4:5 HTML 카드 템플릿을 만들고,
`html.to.design` Chrome 확장으로 `.h2d`를 만든 뒤 Figma 플러그인에서 레이어로 가져오는 순서를
설명한다. 이 HTML·프롬프트는 교육 예시이며 우리 저장소의 재사용 코드가 아니다.

### 공개 코드·SDK 감사

| 자산 | 라이선스·유지 상태 | 즉시 재사용 판단 |
|---|---|---|
| [figma/plugin-samples](https://github.com/figma/plugin-samples) | Figma 공식, MIT, TypeScript/HTML 샘플, 236 commits | **가능**. `post-message`, `svg-inserter`, `text-review`, `variables-import-export` 구조를 독립 Figma exporter의 scaffold로 사용할 수 있다. |
| [figma/rest-api-spec](https://github.com/figma/rest-api-spec) / `@figma/rest-api-spec` | Figma 공식 OpenAPI 3.1 + TypeScript types, MIT, 공식 설명상 beta | **가능**. 서버 측 Figma REST 읽기/내보내기 타입이 필요할 때 사용한다. 현재 Python CardNews Renderer에는 불필요하다. |
| [Figma Plugin API](https://developers.figma.com/docs/plugins/) | 공식 API. 플러그인은 JavaScript/HTML이며 document node를 읽고 쓸 수 있음 | **계약 재사용 가능**. 실행은 Figma 편집기와 별도 TypeScript plugin project가 필요하다. |
| `html.to.design` | 공개 소스·SDK·`.h2d` 파일 명세·재사용 라이선스를 확인하지 못함 | **BLOCKED**. `.h2d`를 역공학하거나 구현을 복사하지 않는다. 수동 SaaS로만 평가한다. |

### 우리 코드에 바로 매핑되는 부분

`INFERENCE` 현재 `modules/card_news/card_news_module.py`의 Pillow 렌더링, 기존 4장 구조,
`layout_rule_engine.py`, `typography_rules.py`, `card_news_quality_checker.py`가 이미 결정적 생산 경로다.
HTML 생성으로 교체하면 모바일 QA와 `workflow_completed` 보호 계약을 다시 만들어야 하므로 손해다.

가장 작은 확장은 미래 standalone `EditableCardDocument`다.

```json
{
  "schema_version": "1.0",
  "canvas": {"width": 1080, "height": 1350},
  "cards": [{
    "card_index": 1,
    "role": "hook",
    "layers": [
      {"type": "text", "role": "headline", "text": "...", "style_token": "headline"},
      {"type": "image", "asset_ref": null, "render_allowed": false}
    ]
  }],
  "source_manifest_ref": "card_news_result_manifest.json",
  "editable_export_status": "not_exported"
}
```

이 JSON을 Figma Plugin API로 Rectangle/Text/Image node로 변환하면 된다. Figma 공식 MIT 샘플의
manifest, message passing, node creation scaffold는 재사용할 수 있지만, 기존 Renderer나 품질 검사를
대체하지 않는다. `html.to.design`은 **BUY/manual**, 자체 JSON→Figma plugin은 실제 편집 수요가
확인될 때만 **BUILD**다.

## 2. Higgsfield AI Influencer / Motion Control

### 공개 코드·SDK 감사

| 자산 | 확인된 기능 | 라이선스·유지 상태 | 판단 |
|---|---|---|---|
| [higgsfield-ai/cli](https://github.com/higgsfield-ai/cli) | Windows 포함 설치, `model list`, `generate create/cost/get/wait`, upload, Soul ID, Marketing Studio, Product Photoshoot, `--json`, timeout/poll interval | 공식 MIT. 59 releases, `v1.1.13`이 2026-07-11 공개 | **가장 우선적인 REUSE NOW 후보**. subprocess JSON adapter로 감싸면 자체 HTTP/auth/poll 구현을 피할 수 있다. |
| [higgsfield-ai/higgsfield-client](https://github.com/higgsfield-ai/higgsfield-client) / `higgsfield-client` | Python sync/async submit, polling status classes, webhook, 파일/PIL upload | 공식 Apache-2.0. 공개 저장소는 2 commits, GitHub release 없음 | **코드 재사용 가능하나 유지보수 신호가 약함**. CLI보다 후순위다. |
| [higgsfield-ai/skills](https://github.com/higgsfield-ai/skills) | generate, Soul ID, product photoshoot, marketplace cards용 에이전트 스킬; CLI를 auth/retry/poll/schema 경계로 사용 | 공식 MIT, repo version 0.3.0; 2026-05 업데이트 확인 | **워크플로 구조 재사용 가능**. 프로젝트 스킬로 설치하려면 별도 보안·비용·행동 범위 검토가 필요하다. |
| [higgsfield-ai/higgsfield](https://github.com/higgsfield-ai/higgsfield) | 대규모 GPU 학습 orchestration framework | Apache-2.0, 마지막 release 계열은 2024 | 이름은 같지만 콘텐츠 생성 SDK가 아니다. **REJECT**. |

Halfdone 자료가 다룬 AI Influencer 화면만 보고 “API 없음”으로 결론 내리면 틀린다. 현재 공식 CLI는
Kling 3, Soul character, branded marketing, product photoshoot까지 다루고 machine-readable JSON을
제공한다. 다만 이는 계정·업로드·크레딧을 사용하는 외부 실행기이므로 현재 실행 승인은 아니다.

### 가장 빠른 통합 방식

`INFERENCE` Python SDK를 애플리케이션 내부에 바로 import하기보다, 별도 프로세스에서 버전을
고정한 CLI를 `--json`으로 호출하는 방식이 현재 저장소에 더 잘 맞는다.

```text
ShortsEditingPackage / approved commerce brief
  -> ExternalAssetJob JSON
  -> higgsfield CLI adapter (future standalone process)
  -> job JSON + downloaded local asset + actual credits
  -> modules/shorts/shorts_exporter.py user_assets gate
  -> local QA and manual publish preparation
```

CLI가 auth, upload, schema 조회, polling을 담당하므로 직접 구현 범위는 명령 생성, JSON 정규화,
timeout/fallback, 비용 상한, provenance receipt에 한정된다. `modules/shorts/shorts_module.py`의
`renderer: not_selected`와 `modules/shorts/shorts_exporter.py`의 `render_allowed`/license hash를
그대로 보존한다. 상품 이미지 후보는 `modules/commerce/commerce_module.py`의 검증된 product facts와
`contract_loader.py`의 이미지 계약을 통과해야 하며, 생성 이미지가 상품 사실의 증거가 되어서는
안 된다.

### 직접 복사할 것과 복사하지 않을 것

- 재사용 가능: CLI executable, 공개 MIT skill 구조, Apache-2.0 SDK의 client/poll/upload 코드
- 그대로 복사 금지: Halfdone prompt, 타사 캠페인 prompt, 실존 인물 reference, provider UI 흐름
- 주의: CLI 결과의 virality score는 실제 조회·유지율이 아니며 내부 예측값으로만 저장한다.
- 계정 credential은 소스/결과에 넣지 않고, 결제와 credit 소비는 owner approval 뒤에만 허용한다.

## 3. DomoAI Talking Avatar / Video-to-Video

### 공식 API 계약

`VERIFIED` [Talking Avatar API](https://docs.domoai.app/api-reference/ai-video/talking-avatar)는
`POST /v1/video/talking-avatar`에 image 또는 video, audio, prompt, seconds(1~60), optional
callback URL, aspect ratio와 model을 받으며 task UUID를 반환한다. 공식
[Callback Protocol](https://docs.domoai.app/api-reference/callback/callback-protocol)은
`PENDING | QUEUING | PROCESSING | SUCCESS | FAILED | CANCELED`, category, output video URL,
actual credits와 timestamps를 정의한다. 별도 `GET Get Task` 경로도 문서 목차에 존재한다.

### 코드 재사용 판단

- 공식 문서에는 Python `requests`, JavaScript `fetch`, curl 예시가 있다.
- 공식 DomoAI SDK, 공개 GitHub client, OpenAPI 파일 또는 예시 코드의 별도 소프트웨어 라이선스는
  이번 감사에서 확인하지 못했다.
- 따라서 예시를 복사해 들여오는 것은 **BLOCKED**다. endpoint와 JSON 계약만 사용해 자체 thin
  adapter를 작성한다.
- 현재 `requirements.txt`에는 `requests/httpx`가 없으므로 연구 단계에서 dependency를 추가하지 않는다.

`INFERENCE` 미래 adapter는 아래 상태만 표준화하면 된다. DomoAI만을 위한 새로운 Shorts schema는
만들지 않는다.

```json
{
  "provider": "domoai",
  "operation": "talking_avatar",
  "provider_task_id": "uuid",
  "status": "queued | processing | succeeded | failed | canceled",
  "input_asset_refs": [],
  "requested_seconds": 5,
  "requested_aspect_ratio": "9:16",
  "actual_credits": null,
  "output_assets": [],
  "rights_review": "not_completed",
  "render_allowed": false
}
```

`modules/shorts/shorts_exporter.py`가 이미 asset 존재성, magic signature, rights, license evidence와
SHA-256을 검증하므로 Domo output은 그 입력 경계에만 전달한다. 성공 callback은 권리 승인이나
`render_allowed=true`를 의미하지 않는다. 판정은 **INTEGRATE later**, 즉 공개 코드는 없지만 API
계약 때문에 자체 모델 구현보다 훨씬 빠른 공급자 후보라는 뜻이다.

## 4. Freepik Spaces → Kling 캠페인

### Freepik 공개 자산

`VERIFIED` [Freepik Spaces 문서](https://www.freepik.com/ai/docs/introduction-to-spaces)는 Text,
Image, Video, Audio 등 typed port를 가진 node와 connector, Run Node/Workflow/Downstream, 실행 상태와
history를 설명한다. 이는 코드보다 유용한 workflow contract다.

[freepik-company/freepik-mcp](https://github.com/freepik-company/freepik-mcp)는 공식 공개 Python
MCP로 icon search/download, resource management, image classification, Mystic image generation을
구현한다. 그러나 감사 시점에:

- 저장소에 `LICENSE` 파일이 없고 `pyproject.toml`에도 license 선언이 없다.
- Python 3.12+, FastMCP/httpx 등 현재 프로젝트에 없는 dependency를 요구한다.
- README는 Windows에서 WSL을 요구하며 GitHub release/package가 없다.
- 공개 저장소는 14 commits 수준이고, README 범위에는 Spaces/Kling video pipeline이 없다.

따라서 코드를 복사하거나 dependency로 편입하는 것은 **BLOCKED**다. API 호출 패턴과 MCP tool
경계만 **BENCHMARK**한다. 라이선스가 공식 확인된 뒤에도 `WorkflowEngine`이 아니라 별도 provider
service 후보로만 검토한다.

### Kling 공개 자산

| 자산 | 라이선스·유지 상태 | 재사용 판단 |
|---|---|---|
| [KlingAIResearch/ComfyUI-KLingAI-API](https://github.com/KlingAIResearch/ComfyUI-KLingAI-API) | 공식 조직, Python ComfyUI nodes, 10 commits, release 없음, LICENSE 파일 없음 | 실행 참고는 가능하지만 **코드 복사 BLOCKED**. API key와 ComfyUI가 필요하다. |
| [KlingAIResearch/kling-skills](https://github.com/KlingAIResearch/kling-skills) | 공식 조직, 1 commit, release·LICENSE 없음 | **BENCHMARK only**. prompt/skill 코드 복사 금지. |
| [KlingAIResearch/LivePortrait](https://github.com/KlingAIResearch/LivePortrait) | 공식 연구 구현, MIT, 활발한 사용자 기반 | **직접 재사용 가능한 로컬 portrait-animation 코드**. 단, bundled InsightFace detection model은 non-commercial research only이며 상업용은 교체해야 한다고 LICENSE가 명시한다. |

LivePortrait는 Kling 3 cloud renderer 코드가 아니며 audio-driven talking avatar 전체를 대체하지도
않는다. 그러나 소유·동의된 portrait와 driving video를 로컬에서 애니메이션하는 미래 대안이다.
GPU, 모델 용량, 모델별 라이선스, 얼굴 개인정보 때문에 현재 프로젝트 dependency로 넣지 않는다.

Kling cloud를 먼저 시험해야 한다면 공개 라이선스가 불명확한 ComfyUI node 코드를 복사하는 것보다,
앞 절의 유지되는 Higgsfield MIT CLI가 제공하는 `kling3_0` job을 provider-neutral 경계에서 평가하는
편이 짧다. 이는 **INFERENCE**이며 비용·약관·출력 권리를 승인한 뒤의 선택이다.

### 채택할 workflow/data 구조

Freepik Spaces의 제품 UI를 복제하지 않고 다음 작은 typed DAG만 채택한다.

```json
{
  "creative_graph_version": "1.0",
  "nodes": [
    {"id": "brief", "kind": "text", "output_type": "text", "status": "ready"},
    {"id": "image", "kind": "asset_request", "input_types": ["text"], "output_type": "image", "status": "planned"},
    {"id": "video", "kind": "asset_request", "input_types": ["image", "text"], "output_type": "video", "status": "planned"}
  ],
  "edges": [
    {"from": "brief", "to": "image", "data_type": "text"},
    {"from": "image", "to": "video", "data_type": "image"}
  ],
  "external_execution_approved": false
}
```

이를 기존 `CampaignBrief -> Storyboard -> ShotSpec[] -> AssetManifest`에 덧붙이면 Freepik, Kling,
Higgsfield, DomoAI를 같은 graph로 표현할 수 있다. node failure는 downstream을 `blocked_manual`로
표시하되 CardNews/Shorts planning 결과를 실패시키지 않는다.

## 공통으로 직접 구축할 최소 계약

외부 공급자별 adapter를 만들기 전에 아래 `ExternalAssetJob` 하나만 프로젝트가 소유해야 한다.

```json
{
  "job_schema_version": "1.0",
  "job_id": "deterministic-hash",
  "provider": "not_selected",
  "provider_adapter_version": null,
  "operation": "image | video | talking_avatar | motion_transfer",
  "source_scene_ids": [],
  "input_assets": [{
    "sha256": null,
    "rights_status": "unverified",
    "consent_ref": null,
    "uploaded": false
  }],
  "request": {"model": null, "parameters": {}, "max_cost": null},
  "provider_job": {"id": null, "status": "not_submitted"},
  "cost": {"estimated": null, "actual": null, "unit": "provider_credit"},
  "outputs": [],
  "terms_snapshot_ref": null,
  "render_allowed": false,
  "fallback_used": true,
  "reason": "External execution not approved"
}
```

`job_id`에는 승인된 input hash, model/version, generation parameters, scene mapping을 넣고 credential,
절대경로, callback secret은 넣지 않는다. provider success와 `render_allowed`는 분리한다. 이 계약은
`modules/shorts/shorts_exporter.py`의 asset validation 및 `modules/card_news/evidence_input_validator.py`의
provenance gate와 중복되지 않고, 그 앞의 비동기 작업 receipt 역할만 한다.

## 가장 작은 오프라인 파일럿

외부 호출 없이도 adapter 구조의 대부분을 검증할 수 있다.

1. 공식 문서의 field 이름만 이용해 Higgsfield CLI JSON, Domo callback, generic failed job의 작은
   로컬 fixture를 독립적으로 작성한다. 문서 예제 payload를 복사하지 않는다.
2. 세 fixture를 동일 `ExternalAssetJob`으로 정규화한다.
3. 성공 fixture도 실제 로컬 asset과 권리 증빙이 없으면 `render_allowed=false`인지 확인한다.
4. 소유한 1x1 test PNG와 자체 license fixture만 `ShortsExporter.user_assets` 경계에 넣어 기존
   hash/magic/path/rights validation을 통과시키고, 외부 호출 없이 package가 재현되는지 확인한다.
5. CardNews 결과 한 세트를 `EditableCardDocument` JSON으로 변환하되 Figma 계정이나 plugin은
   사용하지 않는다.
6. typed DAG의 cycle, incompatible port, failed node downstream 차단을 순수 단위 테스트로 확인한다.

이 파일럿은 API key, 계정 로그인, upload, credit, 모델 다운로드, 미디어 생성, Figma/Kling/Freepik
실행이 전혀 없다. 통과 후에도 provider별 실제 파일럿은 별도 CTO·권리·비용 승인이 필요하다.

## 우선순위와 구현 절감 효과

1. **BUILD now only when approved:** `ExternalAssetJob` + fixture normalizer. 공급자 네 곳의 상태·비용·
   provenance를 한 번에 수용해 중복 adapter 코드를 막는다.
2. **REUSE first:** Higgsfield CLI의 auth/upload/schema/poll/JSON. 같은 범위를 자체 HTTP client로
   다시 만들 필요가 없다.
3. **BUILD on proven need:** CardNews JSON→Figma plugin. Figma MIT sample scaffold를 쓰고 `.h2d`는
   다루지 않는다.
4. **INTEGRATE later:** DomoAI thin REST adapter. SDK가 없으므로 공통 job contract가 먼저다.
5. **BENCHMARK:** Freepik Spaces typed DAG. Freepik MCP는 라이선스 확인 전 코드 사용 금지다.
6. **OPTIONAL local R&D:** LivePortrait. 상업 배포 전 InsightFace detector 교체와 모든 model license를
   다시 감사한다.
7. **REJECT:** 타사 prompt/creative 복사, `.h2d` 역공학, 라이선스 없는 Kling/Freepik repo 코드 복사,
   provider를 `WorkflowEngine` 필수 단계로 연결, 가상 인물의 허위 후기·상품 사용 주장.

정량적 개발시간 절감치는 실제 구현 전에는 근거가 없으므로 만들지 않는다. 확인 가능한 절감은
Higgsfield CLI가 이미 auth, upload, model schema, cost query, polling, JSON output을 제공하고,
Figma 샘플이 plugin manifest와 message/node scaffold를 제공한다는 범위까지다.

## 권리·개인정보·비용·벤더 위험

- 얼굴, 음성, motion reference는 생체·likeness 데이터다. 문서화된 목적별 동의 없이는 업로드 금지.
- 상품 생성 이미지는 실제 상품 형태·사용 경험·성능의 증거가 아니다. Commerce의 source/freshness
  gate와 Affiliate의 disclosure/human approval을 우회하지 않는다.
- 공개 소스 코드 라이선스와 생성 output 상업 라이선스는 서로 별개다.
- MIT/Apache 코드도 model weight, detector, font, reference media, provider terms의 권리를 보장하지 않는다.
- provider credit estimate와 actual consumption을 분리하고 retry마다 실제 비용을 기록한다.
- callback URL은 서명/secret 검증, replay 방지, allowlist가 확인되기 전 운영에 열지 않는다.
- vendor outage, moderation, credit exhaustion, auth expiry는 구조화된 fallback이며
  `workflow_completed`를 실패로 바꾸지 않는다.
- 유지보수 상태와 약관은 변한다. 실제 파일럿 때 pinned version, commit/release, LICENSE, dependency
  lock, pricing, retention/deletion, training use, commercial/client-work rights를 다시 캡처한다.

## 구현 상태

**Research only.** 이번 감사에서 코드, dependency, test, storage output, plugin/skill, API key,
계정, 외부 호출, upload, credit purchase, model download, media generation, publish, `WorkflowEngine`는
변경하지 않았다. 다음 구현은 명시적 Sprint 승인과 독점 파일 소유권이 있는 별도 work order가
필요하다.

