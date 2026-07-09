# Prompt Library

## Prompt 관리 원칙

- **중복 프롬프트를 만들지 않는다** (`AI_CONTEXT.md`의 "Reusable" 원칙). 비슷한 목적의 프롬프트가 이미 있다면
  새로 만들지 않고 기존 것을 파라미터화/확장한다.
- 프롬프트는 코드가 아니라 **데이터**로 취급한다 — LLM에게 보낼 지시문은 가능하면 `.md` 파일이나 설정에
  분리해 두고, Python 코드에는 그 파일을 읽어 조합하는 로직만 둔다 (`ContentPromptBuilder`/`PatternPromptRouter` 패턴).
- 최종적으로 LLM에게 요구하는 **출력 JSON 스키마**는 프롬프트 문구를 바꾸더라도 유지한다 — 스키마가 바뀌면
  응답을 파싱하는 코드(`_safe_json_parse` 등)까지 함께 바꿔야 한다.
- 프롬프트 실패(LLM이 이상한 응답을 줌)는 항상 fallback 콘텐츠로 흡수한다 — 프롬프트를 더 길게/엄격하게 만드는 것으로
  실패를 "방지"하려 하지 않는다 (`.claude/skills/domain/performance.md`의 "불필요한 LLM 호출 제거" 참고).

## Prompt Library 구조

```text
prompts/
├── README.md
├── research_prompt.md          Research 단계 참고 프롬프트
├── content_prompt.md           Content 단계 참고 프롬프트 (레거시, 대부분 코드 내 인라인으로 실제 구현됨)
├── image_prompt.md             Image Prompt 단계 참고 프롬프트
└── patterns/                   pattern_type별 Content Prompt 가이드 (PatternPromptRouter가 로드)
    ├── warning_prompt.md
    ├── tutorial_prompt.md
    ├── comparison_prompt.md
    ├── story_prompt.md
    ├── number_list_prompt.md
    └── resource_prompt.md
```

- `prompts/patterns/*.md`는 실제 코드(`modules/content/pattern_prompt_router.py::PatternPromptRouter`)가
  런타임에 읽는 파일이다 — 이 파일들을 수정하면 실제 LLM 프롬프트 내용이 바로 바뀐다.
- `prompts/research_prompt.md`, `content_prompt.md`, `image_prompt.md`는 현재 대부분 참고용 문서이며,
  실제 프롬프트 문자열은 각 모듈(`ContentModule._legacy_*_prompt`, `ImagePromptModule.run` 등) 안에
  하드코딩되어 있다 — 새 프롬프트 작업을 할 때는 반드시 **실제로 코드가 어디서 프롬프트를 읽는지** 먼저
  확인하고, 참고 문서만 고쳐서 아무 효과가 없는 상황을 피한다.

## 새 프롬프트 추가 시 체크리스트

1. 비슷한 프롬프트가 이미 있는가? (`Grep`으로 `prompts/`, `modules/*/`, benchmark 참고 확인)
2. 이 프롬프트가 실제로 코드에서 로드되는가, 아니면 참고 문서로만 남는가?
3. 출력 스키마가 하위 파싱 로직과 일치하는가?
4. LLM 실패 시 어떤 fallback 콘텐츠로 대체되는가?
