---
name: performance
description: 성능 최적화 원칙. 불필요한 API/LLM 호출을 제거하고, 캐시를 우선하며, Retry를 최소화한다.
---

# Performance Skill

## Purpose

AI-Content-OS는 외부 API(OpenAI LLM/Image, Naver, Nate)에 의존하는 파이프라인이다.
성능 문제는 대부분 "코드가 느려서"가 아니라 "불필요하게 외부 호출을 반복해서" 발생한다.

## 불필요한 API 제거

- 새 기능을 추가할 때, 이미 같은 실행(run) 안에서 얻은 데이터를 다시 API로 조회하지 않는다 (예: 이미 `research_result.json`에 있는 `topic_intelligence`를 다시 계산하지 않고 파일에서 읽는 기존 패턴을 따른다 — `CardNewsModule._load_topic_intelligence()` 참고).
- 한 슬라이드/한 항목마다 별도 API 호출을 만들지 않는다 — 가능하면 배치로 묶는다.

## 불필요한 LLM 호출 제거

- LLM 호출은 `ContentModule`(문안), `ImagePromptModule`(이미지 프롬프트) 두 곳으로 고정되어 있다. 새 기능이 "LLM으로 한 번 더 다듬기"를 원한다면, 정말 LLM이 필요한지 먼저 검토한다 — CardNews Engine의 `CardNewsTextOptimizer`처럼 **규칙 기반으로 해결 가능한 것은 LLM을 쓰지 않는다** (비용 없음, 지연 없음, fallback 불필요).
- 이미 실패한 LLM 응답을 다시 파싱하려고 재호출하지 않는다 — `_safe_json_parse` + `_fallback_*` 패턴(파싱 실패 시 안전한 기본값)을 따른다.

## 캐시 우선

- Trend Engine은 이미 `storage/cache/*.json` 캐시 계층이 있다 (`trend_engine.md` 참고) — 실시간 수집이 실패하면 캐시를 최우선으로 사용한다.
- Image Engine에는 아직 캐시가 없다 (`image_engine.md`의 gap) — 동일 프롬프트를 반복 생성하는 상황이 발견되면 캐시 추가를 검토할 수 있다 (신규 모듈이므로 사용자 승인 필요).
- 새로운 외부 호출을 추가할 때는 "캐시가 있다면 캐시부터" 순서를 기본값으로 설계한다.

## Retry 최소화

- Network Stability Patch(재시도 3회 × 2/5/10초 backoff)가 LLM/Image/Trend 4개 서비스에 모두 적용된 이후, 실제 관측된 전체 워크플로 실행 시간이 **357.66초**까지 늘어난 사례가 있다 (`CHANGELOG.md` 2026-07-09 Network Stability Patch 항목).
- 재시도는 **일시적 오류에만** 의미가 있다. `connection_refused`/`timeout`/`unknown_error`처럼 재시도해 볼 가치가 있는 오류와, `auth_failed`/`rate_limited`처럼 재시도해도 소용없는 오류를 구분한다 (`ImageGenerationModule._is_retryable_error_type()` 패턴 참고).
- 재시도 횟수/backoff를 늘리기 전에 "정말 이 재시도가 성공률을 올리는가, 아니면 실패 시간만 늘리는가"를 먼저 판단한다. 근본 원인이 네트워크 자체라면 재시도 튜닝보다 `debug.md`의 원인 분석이 우선이다.

## 절대 원칙

- 성능 최적화를 이유로 fallback-first 계약(외부 실패는 예외가 아니라 안전한 기본값)을 약화시키지 않는다. 빠르게 실패하는 것과 안전하게 실패하는 것은 별개다 — 항상 후자를 유지한 채로 속도를 개선한다.
