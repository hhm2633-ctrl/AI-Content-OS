# AI-Content-OS Content Strategy

Last Updated: 2026-07-08

## Purpose

이 문서는 AI-Content-OS의 콘텐츠 운영 전략 문서이다.
목표는 카드뉴스 자동화가 아니라, Instagram/Reels/Shorts/Blog/Publishing/Analytics까지 확장 가능한 AI 콘텐츠 운영체제를 만드는 것이다.

## Core Discovery

최근 벤치마킹한 AI/인스타/릴스 계정들의 공통점은 단순히 글을 잘 쓰는 것이 아니다.
성공 계정들은 대부분 아래 구조를 반복한다.

```text
Topic
↓
Hook
↓
Pattern
↓
Layout
↓
CTA
↓
Funnel
```

따라서 AI-Content-OS는 단순 Content Generator가 아니라 Pattern 기반 Content Operating System이어야 한다.

## Target Workflow Upgrade

현재 기본 구조:

```text
Trend Engine
↓
Research Engine
↓
Content Engine
↓
Image Prompt Engine
↓
Image Generation Engine
↓
Card News Engine
↓
Publishing Engine
```

향후 목표 구조:

```text
Trend Engine
↓
Pattern Engine
↓
Hook Engine
↓
Research Engine
↓
Content Engine
↓
Layout Engine
↓
Image/Video Engine
↓
CTA Engine
↓
Publishing Engine
↓
Analytics Engine
↓
Learning Engine
```

## Strategic Direction

### 1. Pattern First

콘텐츠를 바로 생성하지 않는다.
먼저 어떤 패턴으로 만들지 결정한다.

예시:

- 숫자형
- 경고형
- 실수형
- 비교형
- 반전형
- 결과형
- 체크리스트형
- 스토리형
- 저장 유도형
- DM 유도형

### 2. Hook First

첫 문장은 조회수를 결정한다.
Content Engine은 본문보다 Hook Engine을 먼저 호출해야 한다.

### 3. CTA First

콘텐츠의 목적은 조회수가 아니라 다음 행동이다.

주요 CTA:

- 저장
- 댓글
- DM
- 팔로우
- 프로필 클릭
- PDF 신청
- 무료 자료 신청
- 다음 릴스 시청
- 상품/강의/컨설팅 연결

### 4. Brand Profile

각 계정은 독립된 브랜드 규칙을 가져야 한다.

Brand Profile 예시:

```json
{
  "brand_name": "AI 자동화 계정",
  "tone": "쉽고 실전적인 설명",
  "visual_style": "강한 제목 + 명확한 대비",
  "hook_priority": ["warning", "number", "mistake", "comparison"],
  "cta_priority": ["save", "comment", "dm"],
  "forbidden": ["과장된 수익 보장", "검증 안 된 주장"]
}
```

## Engine Roadmap

### Pattern Engine

- Hook 유형 선택
- 콘텐츠 패턴 선택
- 슬라이드 구조 선택
- 릴스 구조 선택
- CTA 목적 선택

### Hook Engine

- 주제별 훅 생성
- 계정별 훅 톤 조절
- 반복 훅 방지
- 성과 기반 훅 점수화

### CTA Engine

- 저장 유도
- 댓글 유도
- DM 유도
- 프로필 유도
- 링크 유도
- Edits 링크 삽입 계획

### Competitor Engine

- 벤치마크 계정 목록 관리
- 조회수/댓글/좋아요 기준 상위 콘텐츠 분석
- 대본 추출
- Hook/CTA/Pattern 분류

### Learning Engine

- 성과 좋은 훅 저장
- 성과 좋은 CTA 저장
- 반복 주제 감점
- 계정별 성공 패턴 학습

## Important References

- Reels Hook 200 PDF
- Edits Reels Link PDF
- Bla View Guide PDF
- Instagram benchmark screenshots
- FikaClip / Brivvy / PlatformTree / Biggie / Woojooboss / Moongi / Jwon / 3dragon / ReelTrigger examples

## Sprint Implication

Sprint 2 이후부터는 단순 Topic Intelligence만 개발하지 말고 Pattern Intelligence를 함께 고려한다.

추천 Sprint 순서:

1. Sprint 2: Topic Intelligence + Pattern Engine Skeleton
2. Sprint 3: Hook Engine + CTA Engine
3. Sprint 4: Content Pattern Library + Brand Profile
4. Sprint 5: CardNews Layout Engine
5. Sprint 6: Reels/Shorts Planning Engine
6. Sprint 7: Competitor Engine
7. Sprint 8: Analytics/Learning Engine
