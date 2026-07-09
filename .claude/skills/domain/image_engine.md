---
name: image-engine
description: Image Engine 전용 Domain Skill. Image Prompt, Image Generation, Fallback, Retry, Cache, Prompt Optimization을 다룬다.
---

# Image Engine Skill

## 대상 모듈

- `modules/image_prompt/image_prompt_module.py` (`ImagePromptModule`) — `content_result`를 받아 슬라이드별 이미지 생성 프롬프트 4개를 LLM으로 만든다.
- `modules/image_generation/image_generation_module.py` (`ImageGenerationModule`) — 프롬프트를 받아 OpenAI `gpt-image-1`로 실제 PNG를 생성한다 (`storage/generated_images/`).

## Image Prompt

- `ImagePromptModule`은 `src/llm_client.py::LLMClient`를 통해 LLM을 호출하고, `_safe_json_parse` + `_fallback_prompts` 패턴으로 응답을 검증한다.
- 프롬프트 조건: 글자 없음, 로고 없음, 워터마크 없음, 사람 얼굴 없음, 1:1 정사각형, 슬라이드 role별 톤 통일(hook=시선끌기, problem=문제상황, solution=해결구조, cta=정리/행동유도).
- LLM 실패 시 `_fallback_prompts`가 role 기반 하드코딩 프롬프트로 대체한다 — 절대 예외를 던지지 않는다.

## Image Generation

- `ImageGenerationModule._generate_image()`가 `client.images.generate(model="gpt-image-1", size="1024x1024", n=1)`을 호출하고 base64 응답을 디코드해 PNG로 저장한다.
- **Retry**: Network Stability Patch 이후, 이미지 1장당 최대 3회 재시도(2초/5초/10초 backoff)를 수행한다. 재시도 가능 여부는 `_is_retryable_error_type()`이 `connection_refused`/`timeout`/`unknown_error`일 때만 허용한다 — 인증/rate limit 오류는 재시도해도 소용없으므로 즉시 실패 처리한다.
- 재시도가 모두 소진되면 `ImageGenerationRetryError`(커스텀 예외, `final_error_type`/`retry_count`/`original_error` 보유)를 던지고, `run()`의 상위 try/except가 이를 잡아 `status: "failed"`로 기록한다 — 이 예외는 `ImageGenerationModule` 내부에서만 순환하며 WorkflowEngine까지 전파되지 않는다.

## Fallback

- 이미지 4장 중 일부만 실패해도 나머지는 정상 생성되고, 실패한 이미지는 `{"status": "failed", "image_path": None, "error": final_error_type, "retry_count": N}`으로 기록된다.
- `result.fallback_used`가 하나라도 실패 시 `true`가 되고, `result.service_diagnostic`(`modules/common/service_diagnostic.py`)이 `error_type`/`safe_message`/`api_key_present`를 기록한다 (`debug.md` 참고).
- `CardNewsModule`은 이미지가 없는 슬라이드에 solid color 배경을 대신 사용하므로, 이미지 생성이 전부 실패해도 카드뉴스 자체는 계속 만들어진다.

## Cache

- 현재 Image Engine에는 **생성된 이미지에 대한 캐시가 없다** — 매 실행마다 새로 생성을 시도한다. Trend Engine의 `storage/cache/*.json` 같은 캐시 계층은 아직 없음 (알려진 gap, 향후 Sprint 후보).

## Prompt Optimization

- CardNews Engine의 `CardNewsTextOptimizer` 같은 **이미지 프롬프트 전용 최적화기는 아직 없다** — `ImagePromptModule`이 만든 프롬프트를 그대로 사용한다. 프롬프트 길이/중복 최적화가 필요하면 `CardNewsTextOptimizer`와 동일한 패턴(규칙 기반, LLM 호출 없음, 실패 시 원본 반환)으로 새 헬퍼를 추가하는 것을 검토할 수 있다 (신규 모듈 생성이므로 `large_implementation.md` 기준 적용, 사용자 승인 필요).

## 절대 원칙

- 이미지 API 실패는 절대 `workflow_failed`로 이어지지 않는다 — 개별 이미지 실패만 기록하고 계속 진행한다.
- API Key는 `os.getenv("OPENAI_API_KEY")`로만 읽고, 값 자체를 로그/출력하지 않는다.
