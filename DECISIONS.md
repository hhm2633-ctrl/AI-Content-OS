# DECISIONS.md

# AI-Content-OS

프로젝트에서 내려진 모든 중요한 의사결정을 기록한다.

---

# Decision History

## 2026-07-07

### 프로젝트 방향

결정

AI 자동화 프로젝트가 아니라

AI Content Operating System을 구축한다.

이유

장기적으로 다양한 플랫폼과 사업으로 확장하기 위함.

---

### 개발 방식

결정

Documentation First

문서를 먼저 작성한다.

이유

프로젝트 규모가 커질수록 유지보수가 쉬워진다.

---

### 프로젝트 관리

결정

GitHub를 Single Source of Truth로 사용한다.

이유

모든 AI와 개발 환경에서 동일한 기준을 유지하기 위함.

---

### Legacy 정책

결정

기존 자료는 바로 사용하지 않는다.

반드시

분석

↓

분류

↓

리팩토링

↓

편입

절차를 따른다.

---

### Architecture

결정

모놀리식 구조가 아니라

모듈형 구조를 채택한다.

이유

필요한 기능만 교체 가능하도록 하기 위함.

---

### AI 사용 정책

결정

AI마다 역할을 분리한다.

ChatGPT

- CTO
- Architecture
- Documentation
- Project Management

Claude

- Code
- Refactoring

Gemini

- Vision
- OCR
- Google Ecosystem

필요시 다른 AI 추가 가능

---

### 현재 사업 전략

결정

첫 번째 목표는

Instagram 카드뉴스 자동화

이유

가장 빠르게 수익 검증이 가능하기 때문.

---

### 장기 전략

Instagram

↓

YouTube Shorts

↓

Affiliate

↓

Smart Store

↓

Coupang

↓

AI Content Company

---

### 개발 원칙

결정

기능 추가보다

프로젝트 구조를 우선한다.

---

### 문서 정책

결정

모든 중요한 변경은

먼저 문서를 수정한다.

그 이후 코드를 수정한다.

---

### 답변 정책

결정

AI는

부분 최적화가 아니라

프로젝트 전체를 고려하여 답변한다.

---

# Future Decisions

앞으로 중요한 기술적 결정은

날짜와 함께 계속 추가한다.

절대로 삭제하지 않는다.