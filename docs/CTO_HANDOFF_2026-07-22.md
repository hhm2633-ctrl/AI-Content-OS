# AI-Content-OS CTO 압축 인계서

기록 시각: 2026-07-22 Asia/Seoul

이 문서는 새 채팅에서 과거 대화 전체를 다시 읽지 않고 AI-Content-OS CTO 역할을 이어가기 위한
경량 체크포인트다. 저장소 실제 상태가 이 문서보다 우선한다.

## 새 채팅 시작 지시

다음 문장을 새 채팅의 첫 메시지로 사용한다.

> 이 채팅에 AI-Content-OS 프로젝트의 CTO 역할을 위임한다. 먼저 저장소 `AGENTS.md`,
> `PROJECT_OPERATING_SYSTEM.md`, 그리고 `docs/CTO_HANDOFF_2026-07-22.md`를 읽고 현재 작업을
> 이어가라. 과거 전체 대화, 이미지, 영상은 다시 불러오지 말고 필요한 사실만 저장소에서 제한적으로
> 확인하라. 운영 연결은 실제 import/call chain으로 증명하고, 테스트 통과와 운영 연결을 같은 것으로
> 간주하지 마라. Git, 실제 게시, 자동화 재개, 외부 API write는 별도 승인 없이는 하지 마라.

## CTO 운영 권한과 경계

- 역할: 범위 통제, 아키텍처 판단, 작업 분할, 운영 호출 경로 검증, 최종 QA와 인계.
- 최우선: CardNews 다계정 수집, 선정, 제작. Commerce/Shorts 임의 확장 금지.
- Protected Core와 `workflow_completed` 보존.
- 실행 명령은 `py -m src.main`; 기본 compile은 `py -m compileall src modules scripts`.
- 테스트가 통과해도 실제 스크립트/WorkflowEngine/호출 함수가 없으면 운영 연결 완료로 보고하지 않는다.
- 저장소는 다수의 기존 변경이 있는 dirty worktree다. 관련 없는 변경을 되돌리거나 Git 작업하지 않는다.
- Claude는 동시 한 세션만 허용한다. Spark는 `model_reasoning_summary="none"` 전용 경로만 사용한다.
- 실제 SNS 게시, 제휴 링크 발급, 배포, 자동화 재개, 외부 API write는 명시적 승인 전 금지다.

## 현재 최우선 미완료 작업

작업명: `naver_news_collector.py` 내장 파싱을 `NaverNewsParserV2`로 교체.

현재 코드 상태:

- `modules/trend_collector/naver_news_collector.py`가 `NaverNewsParserV2`를 import하고 인스턴스화한다.
- RSS 경로는 `NaverNewsParserV2.parse_query()`를 호출한다.
- HTML 검색 경로는 `NaverNewsParserV2.parse_search_payload()`를 호출한다.
- 기존 namespace/case/malformed RSS 및 구형 HTML 호환을 위한 정규화 shim과 lenient fallback은 남아 있다.
- ranking/section 파싱은 건드리지 않았다.
- 이번 작업에서 수정한 소스 파일은 위 collector 한 개뿐이다.

현재 검증 결과:

| 검증 | 결과 |
|---|---:|
| `tests.test_naver_news_parser_v2` | 4/4 통과 |
| `tests.test_naver_news_collector` | 16/16 통과 |
| `tests.test_source_intake_naver_news_fallback_diagnostic` | 3/3 통과 |
| `tests.test_naver_news_parser_recovery` | 16/16 통과 |
| 실제 `collect(["AI"], source)` 관찰 | 5건 반환, HTML 경로 사용, 캐시/API Hub 미사용 |

잔존 실패:

1. `test_api_hub_success_runs_only_after_free_paths_are_empty`: free RSS/HTML fetch 2회 기대인데 0회로 관찰됨.
2. `test_free_rss_success_skips_api_hub`: API Hub 미시도 상태의 `error_type`은 빈 문자열이어야 하나
   `missing_credentials`가 남음.

따라서 이 작업은 아직 완료가 아니다. 새 CTO의 첫 구현 작업은 collector의 API Hub 실행 순서와
`last_status["api_hub"]` 초기화 의미를 기존 외부 계약에 맞추는 것이다. 다른 collector와
ranking/section 기능은 건드리지 않는다. 수정 후 관련 네이버 뉴스 테스트 전체와 실제 검색 1회를
다시 실행하고, 사용자가 지정한 고정 완료 형식으로 보고한다.

## 최근 누적 구현 상태

### Owner feedback 및 design learning

- `scripts/import_design_candidates_to_owner_feedback.py`가 운영 시작점으로 존재한다.
- 실제 호출 체인은 `main()` -> `build_design_candidates()` ->
  `candidate_to_owner_review_payload()` -> `append_owner_review_feedback()` -> 기존 normalize/append 경로다.
- `knowledge/owner_feedback/cardnews_owner_feedback.jsonl`은 현재 105줄이다.
- 최초 확인된 71줄에서 design candidate 34줄이 추가된 상태로 해석된다. 마지막 34개 이벤트는
  `review_kind="candidate_evaluation"`, `owner_rule_activation="NONE"`이며 자동 승인 규칙이 아니다.
- candidate의 `candidate_type`은 category로, `observed_pattern`은 owner decision/title로,
  `recommended_usage`는 owner reason으로 변환된다.

### Local image intake

- `scripts/run_local_image_intake.py`가 `--source-dir`, `--output-dir` 필수 인자를 받고
  `run_local_image_intake()`를 실제 호출한다.
- 결과 콘솔에는 discovered/supported/unique/exact-duplicate count와 manifest/contact-sheet 존재 여부를
  출력하도록 구현돼 있다.
- 이번 제한 확인에서는 `F:/AI-Content-OS-Data/design_learning` 아래 batch_001 시범 manifest와
  contact sheet를 찾지 못했다. 이전 실행 산출물 위치를 현재 증거만으로 확정하지 말고, 필요 시
  batch_001 하나만 다시 실행하라는 owner 승인을 받은 뒤 확인한다.

### Visual QA hard fields

- `visual_qa_gate.py`의 현재 필수 finding에는 `copy_density_ok`, `feed_caption_present`,
  `image_is_primary`가 포함돼 있고 각각 reason code가 연결돼 있다.
- `generate_visual_qa_receipt_from_media.py`의 copy density 기준은 OCR 260자 이하 AND 12줄 이하다.
- PaddleOCR box 기반 `text_area_ratio`를 사용하며 `image_is_primary` 기준은 15% 미만 pass다.
- 테스트 helper에는 세 finding의 기본 pass가 반영돼 있다.
- 이전 라운드에서 CardNews 관련 4개 테스트 파일 31개 통과가 보고됐지만, 이 인계 작성 시점에
  재실행하지 않았으므로 현재 전체 회귀 통과를 새로 주장하지 않는다.
- 나머지 미구현/보류 규칙은 AI 모델 정체성 2개, 유명인 권리, 미디어 출처 진위다. 새 자산 추적과
  출처 확인 인프라가 필요한 별도 라운드이며 임의 구현하지 않는다.

### Brand Connect 의미 매칭

- `brandconnect_candidate_matcher.py`에 기존 키워드 신호를 보존한 채
  `semantic_similarity:점수`를 match basis에 추가하는 코드가 있다.
- 의미 점수 계산 전 기존 candidate/situation family 기준으로 product subset을 좁히는 코드가 있다.
- product family 경계를 의미 유사도로 우회하면 안 된다.
- `sentence_transformers_runtime.py`의 한글 subprocess 인코딩 수정과 matcher의 custom env 제거가
  반영된 것으로 이전 작업에서 다뤄졌다.
- 전체 96후보 파이프라인 재실행은 중단 지시가 있었고, 이후 범위는 후보 1개 직접 호출로 제한됐다.
  이 인계 작성 시점에는 최종 전체 before/after commerce count를 검증된 완료값으로 남기지 않는다.

## 확인만 했고 연결하지 않은 영역

- `owner_feedback_bridge.py`의 실제 owner grade 호출 여부 조사는 연결 작업이 아니었다.
- `agent_console/executor.py`의 주기 실행/dispatch 여부 조사는 연결 작업이 아니었다.
- `modules/knowledge`와 `modules/knowledge_engine` 관계 조사는 구조 확인 작업이었다.
- `daily_collection_executor`와 `multi_account_card_news_discovery_pipeline`은 기존 반자동 운영 경로와의
  관계를 조사했지만 WorkflowEngine에 연결하지 않았다.
- Soul Character `account_c_fixed_model_01`은 계획만 수립 대상이었고 크레딧 충전 전 실행 금지다.

## 유지해야 할 제품 결정

- CardNews는 고정 4장이 아니라 주제별 가변 슬라이드와 mixed media 구조다.
- 슬라이드 문안은 짧게 유지하고 별도 자연스러운 feed caption을 제공한다.
- Account A/B/C 포트폴리오를 하나의 보편 규칙으로 합치지 않는다.
- 세월호 사건은 hook/example/논란/engagement topic으로 사용하지 않는 hard exclusion이다.
- 실제 인물과 무관한 유명인 이미지를 쓰지 않는다. 중립 인물은 명확한 생성형 가상 모델을 사용한다.
- Account C runway/beauty는 실제 이미지 우선이며 순수 runway 정보에 commerce를 강제하지 않는다.
- owner feedback은 학습 신호이지 모든 후보를 영구 제거하는 보편 ranking rule이 아니다.

## 새 CTO의 즉시 실행 순서

1. `AGENTS.md`, `PROJECT_OPERATING_SYSTEM.md`, 이 인계서만 우선 읽는다.
2. 현재 owner 요청이 없으면 구현을 확대하지 않는다.
3. 네이버 뉴스 recovery 테스트와 실제 검색 확인은 완료됐다.
4. 추가 변경이 생길 때만 관련 테스트와 실제 네이버 검색을 마지막에 다시 실행한다.
5. 운영 호출 chain, 반환 계약 유지, 테스트 개수, 실제 실행 결과를 분리해 보고한다.
6. Git/게시/자동화/외부 write는 별도 승인 전 실행하지 않는다.

## 현재 완료 판정

- CTO 인계 문서 생성: 완료.
- 네이버 파서 교체 작업: 완료(recovery 16/16 통과, 실제 검색 5건 반환).
- 전체 프로젝트/CardNews 운영 완성: 완료로 주장할 수 없음.

## 2026-07-22 최신 통합 상태 (이전 우선순위보다 우선)

- 기존 코드 조각을 5단계 로컬 호출선으로 연결했다: daily collection file -> multi-account discovery -> owner report -> owner-selected deep discovery -> final 1-20 plan -> approval package -> Controller/render -> automatic evidence QA -> owner visual approval.
- Controller는 `production_package_ready`와 유효한 package approval을 초기화 시점에 강제한다.
- 자동 OCR/OpenCLIP receipt는 evidence-only이며 owner 시각 승인으로 사용할 수 없다.
- 71개 focused test와 compile이 통과했다. 실제 후보 network deep fetch, 렌더, 게시, 외부 write, 자동화, Git은 실행하지 않았다.

- 네이버 파서 recovery는 16/16 통과했고 실제 검색은 HTML 경로로 5건을 반환했다.
- 2026-07-22 뉴스 후보는 174개이며 174/174 category 정규화가 완료됐다. owner 검토 파일은 `F:\AI-Content-OS-Data\source_intake\2026-07-22\owner_review_all_news_candidates.md`다.
- 기본 Workflow의 무승인 이미지 API/렌더/게시 준비 경로를 차단했다. orchestration은 blocked production 결과와 함께 `workflow_completed`를 유지할 수 있다.
- production package는 명시적 owner-bound approval receipt가 없으면 pending/blocked이며, build/quality 스크립트가 승인을 합성하거나 ready로 승격할 수 없다.
- 승인 제작 경로는 approved package -> controller -> Satori/resvg -> OCR/OpenCLIP 자동 증거 QA -> owner 시각 승인 순서다. 자동 QA는 owner 승인이나 publish-ready를 만들지 않는다.
- CardNews는 고정 4장이 아니라 승인된 계획의 가변 slide 수를 사용한다.
- Sentence Transformers는 same-event clustering에 연결됐다. Intel XPU는 probe-only이며 SeaweedFS/Mixpost/TryPost는 critical path 밖이다.
- 최종 안전 QA는 compile 통과, focused test 67개 통과다. 변경 후 외부 호출 가능 전체 Workflow와 실제 승인 렌더는 실행하지 않았다.
- 다음 owner gate는 174개 후보 검토/선택이다. 그다음 실제 대표 후보 렌더에는 별도 명시적 승인이 필요하다.
- Git, 실제 게시, 자동화 재개, 외부 API write는 수행하지 않았다.
