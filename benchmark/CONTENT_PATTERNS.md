# Content Patterns

Last Updated: 2026-07-08

## Purpose

AI-Content-OS가 생성할 콘텐츠의 반복 가능한 구조를 정의한다.
성공 계정들은 매번 새로 창작하지 않고, 검증된 Pattern을 반복한다.

## Core Content Patterns

### 1. Number List Pattern

Example Titles:

- ___ 필수 도구 7가지
- ___ 실수 5가지
- ___ 아껴주는 10가지 방법
- ___ 초보가 봐야 할 사이트 20개

Structure:

```text
Slide 1: 숫자형 Hook
Slide 2: 왜 중요한지
Slide 3~N: 항목 나열
Last: 저장/팔로우 CTA
```

Best For:

- AI 툴
- 프롬프트
- 무료 리소스
- 사이트 추천

---

### 2. Warning Pattern

Example Titles:

- ___ 이렇게 하면 계정 망합니다
- ___ 전에 꼭 보세요
- ___ 모르면 손해입니다
- ___ 절대 하지 마세요

Structure:

```text
Slide 1: 경고형 Hook
Slide 2: 흔한 실수
Slide 3: 왜 위험한지
Slide 4: 해결 방법
Last: 저장 CTA
```

Best For:

- 인스타 성장
- AI툴 사용법
- 프롬프트 실수
- 계정 운영

---

### 3. Comparison Pattern

Example Titles:

- Claude vs ChatGPT
- 예전 인스타그램 vs 지금 인스타그램
- 무료툴 vs 유료툴
- 초보 vs 고수

Structure:

```text
Slide 1: 비교 Hook
Slide 2: 기준 설명
Slide 3: A 장점
Slide 4: B 장점
Slide 5: 상황별 추천
Last: 댓글 CTA
```

Best For:

- AI 모델 비교
- 플랫폼 비교
- 도구 비교

---

### 4. Before / After Pattern

Example Titles:

- ___ 전 vs 후
- 이 방법 쓰고 달라진 점
- 30일 동안 ___ 한 결과

Structure:

```text
Slide 1: 결과 Hook
Slide 2: Before 상황
Slide 3: 변경한 방법
Slide 4: After 결과
Slide 5: 따라 하는 방법
Last: DM/저장 CTA
```

Best For:

- 성장 사례
- 수익화 사례
- 업무 자동화

---

### 5. Tutorial Pattern

Example Titles:

- ___ 하는 법
- 초보도 따라 하는 ___ 세팅
- 10분 만에 ___ 만드는 법

Structure:

```text
Slide 1: How-to Hook
Slide 2: 준비물
Slide 3~N: 단계별 설명
Last: 체크리스트/프로필 CTA
```

Best For:

- Claude Code
- Codex
- MCP
- Canva
- Edits
- AI 영상툴

---

### 6. Resource Curation Pattern

Example Titles:

- 무료 AI 사이트 20개
- 저장 필수 프롬프트 모음
- 이번 주 AI툴 TOP 5

Structure:

```text
Slide 1: 저장 유도 Hook
Slide 2: 선정 기준
Slide 3~N: 리소스 목록
Last: 댓글 키워드 CTA
```

Best For:

- 무료 자료
- 프롬프트
- 사이트
- 앱
- AI툴

---

### 7. Story Pattern

Example Titles:

- 저는 ___로 1년을 날렸습니다
- 처음엔 아무것도 몰랐어요
- 포기하려던 날 바뀐 것

Structure:

```text
Slide 1: 개인 이야기 Hook
Slide 2: 문제 상황
Slide 3: 실패/고민
Slide 4: 전환점
Slide 5: 교훈
Last: 공감 댓글 CTA
```

Best For:

- 퍼스널 브랜딩
- 계정 성장기
- 사업 성장기

---

### 8. Funnel Pattern

Purpose: 콘텐츠에서 판매/상담/자료신청으로 연결한다.

Structure:

```text
Free Value
↓
Trust
↓
Problem Awareness
↓
CTA
↓
DM/Profile/Link
```

Best For:

- 강의
- 컨설팅
- 템플릿 판매
- PDF 배포
- 스마트스토어/쿠팡 확장

## Visual Layout Patterns

### Notebook Layout

- 손글씨 느낌
- 노트 배경
- 빨간색/파란색 강조
- platformtree 스타일

### Dark Editorial Layout

- 어두운 배경
- 고급 이미지
- 흰색 제목
- adu.aihub 스타일

### Bold AI Tool Layout

- 흰색 굵은 제목
- AI 이미지/툴 아이콘
- 노란색 강조
- biggie_ai / woojooboss 스타일

### Character Diary Layout

- 고정 캐릭터
- 일기형 문장
- 부드러운 색감
- moongi_adventures 스타일

### Personal Talking Head Layout

- 인물 얼굴 중심
- 큰 자막
- 마이크/책상/화이트보드
- blabla_lizzypark / nookitokki 스타일

## Engine Rule

Content Engine은 바로 글을 만들지 않는다.
먼저 Pattern Engine이 아래를 선택해야 한다.

```json
{
  "pattern_type": "number_list | warning | comparison | tutorial | story | resource | funnel",
  "hook_type": "attention | saveable_tip | authority | contrarian | pain_point",
  "layout_type": "notebook | dark_editorial | bold_ai | character_diary | talking_head",
  "cta_type": "save | comment | dm | profile | follow"
}
```
