# AI-Content-OS 현재 개발 상태

## 실행 명령어

Windows PowerShell에서는 항상 아래 명령어를 사용한다.

```powershell
py -m src.main
```

`python -m src.main` 사용 금지.
현재 PC에서는 `python` 명령어가 인식되지 않는다.

---

## 현재 완료된 것

* GitHub 저장소 생성 완료
* GitHub Desktop 연동 완료
* VS Code 개발환경 구축 완료
* Python 3.13 설치 완료
* `.env` 생성 완료
* `requirements.txt` 생성 완료
* `config/settings.json` 생성 완료
* 전체 기본 폴더 구조 생성 완료

---

## 현재 폴더 구조

```text
config/
  settings.json

modules/
  base_module.py
  research/
    research_module.py
  content/
    content_module.py
  image_prompt/
    image_prompt_module.py
  image_generation/
    image_generation_module.py
  card_news/
    card_news_module.py
  publishing/
    publishing_module.py

src/
  main.py
  workflow_engine.py
  llm_client.py

storage/
  outputs/
  images/
  card_news/
```

---

## 현재 Workflow

```text
Research
↓
Content
↓
Image Prompt
↓
Image Generation
↓
Card News
↓
Publishing
```

---

## 현재 정상 생성되는 결과물

```text
storage/outputs/research_result.json
storage/outputs/content_result.json
storage/outputs/image_prompt_result.json
storage/outputs/image_generation_result.json
storage/outputs/card_news_result.json
storage/outputs/publishing_result.json

storage/images/card_slide_1.png
storage/images/card_slide_2.png
storage/images/card_slide_3.png
storage/images/card_slide_4.png

storage/card_news/card_news_1.png
storage/card_news/card_news_2.png
storage/card_news/card_news_3.png
storage/card_news/card_news_4.png
```

---

## 완료된 리팩토링

* `BaseModule`에서 `self.config = config` 저장 완료
* 모든 모듈이 `BaseModule(config)` 구조를 사용하도록 통일 완료
* `ResearchModule` LLMClient 연결 완료
* `ContentModule` LLMClient 연결 완료
* `ImagePromptModule` LLMClient 연결 완료
* `ImageGenerationModule` config 기반 구조 정리 완료
* `CardNewsModule` config 기반 구조 정리 완료
* `PublishingModule` config 기반 구조 정리 완료
* `WorkflowEngine` 전체 흐름 정리 완료
* `main.py` config 로딩 구조 정리 완료
* `settings.json`에 `llm`, `storage`, `research`, `content`, `image_prompt`, `image_generation`, `card_news`, `publishing` 설정 구역 생성 완료

---

## 현재 중요한 상태

현재 `LLMClient`는 아직 실제 OpenAI API를 호출하지 않는다.

현재 상태는:

```text
llm.enabled = false
```

이므로 fake response를 반환하는 테스트 구조다.

---

## 다음 작업

다음 작업은 반드시 여기서부터 시작한다.

```text
src/llm_client.py
```

를 실제 OpenAI API 연결 구조로 교체한다.

목표:

```text
ResearchModule
ContentModule
ImagePromptModule
```

이 실제 GPT 응답을 사용하게 만든다.

---

## 앞으로의 개발 원칙

* 컴퓨터 초보 기준으로 한 단계씩 진행
* 항상 전체 수정본 제공
* 기존 파일 수정 시 반드시 전체 코드 제공
* 임시 코드, 연습용 코드 작성 금지
* 최종 AI-Content-OS에서 사용할 구조만 개발
* 아키텍처를 먼저 생각하고 기능을 추가
* 기존 구조를 자주 뒤엎지 않음
* Windows 실행 명령어는 항상 `py` 사용

---

## 다음 채팅 시작 문장

AI-Content-OS 개발 계속.

현재 `PROJECT_STATE.md` 기준으로 이어서 진행한다.

중요:
Windows PowerShell에서는 항상 `py -m src.main` 명령어를 사용한다.
`python -m src.main` 사용 금지.

현재 완료:
BaseModule 구조 통일 완료.
WorkflowEngine 정리 완료.
main.py 정리 완료.
settings.json config 구조 완료.
ResearchModule, ContentModule, ImagePromptModule은 LLMClient에 연결 완료.
ImageGenerationModule, CardNewsModule, PublishingModule은 config 기반 구조로 정리 완료.
.env와 requirements.txt는 이미 생성 완료.

현재 다음 작업:
`src/llm_client.py`를 실제 OpenAI API 연결 구조로 전체 교체한다.

항상 전체 수정본으로 제공해줘.
