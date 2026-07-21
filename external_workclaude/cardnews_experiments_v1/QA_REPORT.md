# QA Report — CardNews Experiment V1

## 입력 확인

- `knowledge/patterns/pattern_registry.jsonl`에서 이번 태스크 직전에 추가된 Instagram 후보 6건(라인 10~15, `pattern.instagram_learning.*`)을 읽음.
- `engagement_mechanic` 도메인 패턴 1건(`pattern.instagram_learning.engagement_mechanic.dm_keyword_cta`)은 실험 설계에서 완전히 제외함(어떤 브리프의 `pattern_id_applied`에도 등장하지 않음 — `EXPERIMENT_MATRIX.json` 전수 확인).
- 남은 5건 중 3건(`quote_reversal_hook`, `numbered_curation_list_structure`, `healthcare_public_character_illustration`)을 표지 훅·스토리 구조·비주얼 레이아웃 실험에 각 1건씩 배정. 나머지 2건(`regional_institution_notice_style`, `immediate_post_zero_engagement`)은 이번 3쌍에 사용하지 않음(사용 의무 없음, 3개 변수에 맞춰 가장 적합한 3건만 선정).

## 계약 준수 체크리스트

| 항목 | 결과 |
|---|---|
| 각 쌍 동일 topic·evidence·CTA | 충족 — EXP-2 양 arm은 동일 `content_evidence_basis=evidence_not_required`, 동일 CTA 및 동일 세 정보 단위를 사용 |
| 쌍당 변수 1개만 변경 | 충족 — EXP-2는 2·3장의 순차 안내 대 번호형 목록이라는 `slide_structure`만 변경 |
| 비교 변수는 표지 훅/스토리 구조/비주얼 레이아웃 중 하나 | 충족 — 3쌍이 각각 서로 다른 변수 1개씩 담당, 중복 없음 |
| EXP-2 양측 슬라이드 수 동일 | 충족 — CONTROL 4장, VARIANT 4장으로 고정 |
| EXP-2 불변 필드 동일 | 충족 — `cover_hook`, `content_evidence_basis`, `cta`, `visual_tone`, `copy_length_rule`을 `EXPERIMENT_MATRIX.json` 양 arm에 동일 문자열로 명시 |
| 서로 다른 3개 분야 사용 | 충족 — 건강·피트니스(EXP-1) / 생활정보(EXP-2) / 지식·자기계발(EXP-3), 3개 전부 다름 |
| 패턴 ID·evidence URL 결속 | 충족 — `PATTERN_BINDINGS.json`의 pattern_id 3건이 `knowledge/patterns/pattern_registry.jsonl`에 각 정확히 1회씩 존재함을 grep으로 재확인(count=3). evidence_urls도 레지스트리 레코드의 `source_claim_ids`를 그대로 복사(누락·추가 없음) |
| EXP-2 pattern provenance 분리 | 충족 — `pattern_provenance_role`로 pattern_id/evidence_urls를 실험 구조 출처로 한정하고 콘텐츠 사실 근거 및 성과 증명에서 제외 |
| 예상 성과 hypothesis_only 유지 | 충족 — `EXPERIMENT_MATRIX.json`의 모든 `expected_outcome_status` 필드가 `"hypothesis_only"`. 원 패턴이 `benchmark_observed`인 경우(EXP-2, EXP-3)에도 "우리 프로덕션에서의 성과"는 별개의 미검증 주장으로 분리 기재 |
| CN-006 미수정 | 충족 — `external_workclaude/content_portfolio_v1/**`에 대해 이번 세션에서 Read/Grep만 수행, Edit/Write 없음. `git status --porcelain`으로 해당 경로에 이번 태스크로 인한 변경 없음을 확인(사전부터 존재하던 미추적 상태 그대로) |
| DM 댓글 유도 금지 | 충족 — 6개 브리프의 CTA 전부 저장 유도형("저장해두고 ...")이며 "댓글", "DM" 요청 문구 없음(정규식 검색으로 재확인, 프로그램상 부정문 외 매치 0건) |
| 과장 훅 금지 | 충족 — 훅 예시 문구에 구체적 미검증 수치·성과 단정 없음 |
| EXP-2 콘텐츠 주장 경계 | 충족 — 용기 선택·장소 선택·개봉 날짜 기록이라는 절차만 사용하며 결과·기간·성능을 약속하는 문장을 사용하지 않음. pattern evidence URL은 구조 provenance로만 분리 |
| 렌더링·게시 미수행 | 충족 — 이번 산출물은 전부 기획 문서(JSON/MD)이며 `modules/card_news/**`, `modules/publishing/**`, `storage/**`를 호출·수정하지 않음 |

## 위반 검색 (정규식 재확인)

`댓글.*남기|DM으로|검증된|효과가 입증|% 향상|승격|validated|proven` 패턴으로 `external_workclaude/cardnews_experiments_v1/**` 전수 검색 결과, 매치 2건은 모두 금지 규칙을 서술하는 부정문(METRIC_AND_DECISION_PLAN.md의 승격 절차 설명, SIX_PRODUCTION_BRIEFS.md의 "금지 사항" 예시)이며 실제 위반 사용은 0건.

## 성과 판정 기준 반영

`METRIC_AND_DECISION_PLAN.md`에 도달 대비 저장율/공유율/댓글율/프로필 방문율을 24시간/72시간/7일 시점으로 비교하는 계획을 수립함. 판정 규칙은 방향 일관성(2개 이상 시점)과 최소 도달 기준을 요구하며, 규칙을 통과해도 `PatternRegistry`의 `VERIFIED`/`PROMOTED` 승격은 자동으로 이루어지지 않고 `promotion_policy.md`의 별도 인간 승인 절차가 필요함을 명시함.

EXP-2 실행 순서는 `Block 1 A→B`, `Block 2 B→A`로 사전 고정했으며 각 게시물의 7일 측정창 뒤 7일 washout을 둔다. 표본 단위는 게시물 1개이고 arm별 `n=2`다. 실제 게시에는 account/arm/schedule/최종 카드 SHA-256과 결속된 별도 서명 `actual_publish=true` 승인이 필요하며 현재 승인은 없다.

## 제작 우선순위 추천

`METRIC_AND_DECISION_PLAN.md` 하단에 **EXP-2(스토리 구조 · CN-017 커피 원두 보관법)** 1쌍만 추천함. 근거 재현성(3개 분야 반복 관측)·실행 리스크(구조 재배열만 필요)·주제 안전성(효능 리스크 낮은 생활정보 주제, 이미 offline_ready)·분야 적합성(원 근거 분야와 적용 분야 일치)을 기준으로 삼았으며, 이는 제작 우선순위 판단일 뿐 성과 우열의 예단이 아님을 명시함.

## 결론

`LEARNING_IMPORT_GO` 이후 단계로서, 이번 산출물은 렌더링·게시 이전의 순수 기획 문서 5종이며 계약 11개 항목 전부 충족을 확인함.
