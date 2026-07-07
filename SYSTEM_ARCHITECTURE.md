# SYSTEM_ARCHITECTURE.md

# AI-Content-OS
System Architecture

Version: 1.0

---

# 1. Goal

AI-Content-OS는
콘텐츠를 자동 생성하고
자동 검수하고
자동 업로드하는
모듈형 콘텐츠 생산 운영체제이다.

모든 기능은 독립적인 모듈로 구성하며
각 모듈은 다른 모듈과 최소한으로만 연결된다.

---

# 2. Architecture Philosophy

원칙

- Single Responsibility
- Modular Design
- Replaceable Components
- AI First
- Human Approval Optional
- No Vendor Lock-in

---

# 3. High Level Architecture

User

↓

Master AI

↓

Task Manager

↓

Workflow Engine

↓

Modules

- Research
- Content
- Image
- Thumbnail
- SEO
- QA
- Publishing
- Analytics

↓

Storage

↓

External APIs

---

# 4. Core Components

## Master AI

역할

- 프로젝트 이해
- 작업 계획
- 모듈 호출
- 결과 평가

절대 직접 작업하지 않는다.

항상 적절한 모듈에게 위임한다.

---

## Task Manager

역할

- 작업 생성
- 작업 우선순위
- 작업 상태 관리
- 재시도 관리

상태

TODO

RUNNING

WAITING

DONE

FAILED

---

## Workflow Engine

역할

각 Task를

순서대로 실행한다.

예)

Research

↓

Keyword

↓

Outline

↓

Article

↓

Thumbnail

↓

SEO

↓

QA

↓

Publish

---

## Storage Layer

저장

Project

Content

Images

Prompt

Logs

Templates

Cache

History

Memory

---

# 5. Module Design

모든 모듈은 동일한 인터페이스를 사용한다.

Input

↓

Process

↓

Output

↓

Validation

↓

Save

---

예시

Content Module

Input

Keyword

↓

Generate Draft

↓

Quality Check

↓

Save

---

# 6. Communication Rules

모든 모듈은

JSON만 주고받는다.

예시

{
  task_id,

  module,

  input,

  output,

  status,

  timestamp
}

---

# 7. Error Handling

실패 시

Retry

↓

Fallback

↓

Human Review

↓

Abort

---

# 8. Logging

모든 작업은 기록한다.

Task Log

AI Decision

API Call

Error

Execution Time

Token Usage

Version

---

# 9. Future Expansion

새로운 모듈은

Module Interface만 구현하면
즉시 연결 가능하다.

예)

Instagram

Threads

TikTok

Pinterest

Coupang

SmartStore

YouTube

Blog

---

# 10. Directory Mapping

/docs

/modules

/workflows

/prompts

/templates

/storage

/logs

/scripts

/config

/tests

---

# End