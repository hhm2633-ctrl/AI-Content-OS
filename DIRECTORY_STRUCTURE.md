# DIRECTORY_STRUCTURE.md

# AI-Content-OS
Directory Structure

Version: 1.0

---

# Purpose

본 문서는 AI-Content-OS 프로젝트의 디렉터리 구조와 각 폴더의 역할을 정의한다.

모든 개발자는 이 구조를 기준으로 파일을 생성한다.

---

# Root Structure

```
AI-Content-OS/

│
├── README.md
├── ROADMAP.md
├── AI_CONTEXT.md
├── PROJECT_BIBLE.md
├── PROJECT_STATE.md
├── CURRENT_TASK.md
├── DECISIONS.md
├── CHANGELOG.md
├── SYSTEM_ARCHITECTURE.md
├── MODULE_SPEC.md
├── WORKFLOW_SPEC.md
├── DIRECTORY_STRUCTURE.md
│
├── docs/
├── src/
├── modules/
├── workflows/
├── prompts/
├── templates/
├── storage/
├── config/
├── scripts/
├── tests/
├── logs/
├── assets/
└── archive/
```

---

# Root Documents

README.md

프로젝트 소개

---

ROADMAP.md

개발 로드맵

---

PROJECT_BIBLE.md

프로젝트 철학 및 핵심 원칙

---

AI_CONTEXT.md

AI가 프로젝트를 이해하기 위한 문서

---

PROJECT_STATE.md

현재 개발 상태

---

CURRENT_TASK.md

현재 진행 중인 작업

---

DECISIONS.md

중요 의사결정 기록

---

CHANGELOG.md

변경 이력

---

SYSTEM_ARCHITECTURE.md

전체 시스템 설계

---

MODULE_SPEC.md

모듈 명세

---

WORKFLOW_SPEC.md

워크플로우 명세

---

DIRECTORY_STRUCTURE.md

폴더 구조 정의

---

# docs/

프로젝트 문서 저장

예시

```
docs/

DeveloperGuide.md

Installation.md

Deployment.md

API_Document.md

Troubleshooting.md
```

---

# src/

실제 실행 코드

```
src/

main.py

app.py

core/

utils/

services/
```

---

# modules/

AI 모듈

```
modules/

research/

keyword/

content/

image/

thumbnail/

seo/

qa/

publishing/

analytics/

memory/

scheduler/
```

---

# workflows/

워크플로우 정의

```
workflows/

content.yaml

thumbnail.yaml

publishing.yaml

analytics.yaml
```

---

# prompts/

프롬프트 관리

```
prompts/

content/

seo/

thumbnail/

system/

shared/
```

---

# templates/

템플릿 저장

```
templates/

blog/

youtube/

instagram/

smartstore/

coupang/
```

---

# storage/

데이터 저장

```
storage/

cache/

history/

memory/

projects/

outputs/
```

---

# config/

환경설정

```
config/

settings.json

model.json

workflow.json

api.json
```

---

# scripts/

자동화 스크립트

```
scripts/

setup.py

build.py

deploy.py

backup.py
```

---

# tests/

테스트

```
tests/

unit/

integration/

performance/
```

---

# logs/

로그

```
logs/

workflow/

system/

error/

ai/
```

---

# assets/

이미지 및 리소스

```
assets/

images/

icons/

fonts/

branding/
```

---

# archive/

오래된 파일 보관

```
archive/

deprecated/

backup/

old_versions/
```

---

# Naming Convention

파일명

- 대문자 문서 : PROJECT_STATE.md
- 코드 : snake_case
- 폴더 : lowercase

예시

content_generator.py

workflow_engine.py

thumbnail_module.py

---

# Directory Rules

- 각 폴더는 하나의 역할만 가진다.
- 코드와 문서는 분리한다.
- 로그는 logs 폴더만 사용한다.
- Prompt는 prompts 폴더만 사용한다.
- Template은 templates 폴더만 사용한다.
- Config는 config 폴더만 사용한다.
- 임시 파일은 프로젝트 루트에 저장하지 않는다.

---

# Future Expansion

향후 추가 가능

```
plugins/

docker/

kubernetes/

mobile/

desktop/

web/

api/

monitoring/

ai_models/
```

---

# End