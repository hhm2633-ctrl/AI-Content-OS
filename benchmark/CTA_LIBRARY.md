# CTA Library

Last Updated: 2026-07-08

## Purpose

AI-Content-OS가 카드뉴스, 릴스, 쇼츠, 블로그, 캡션에서 사용할 CTA 패턴을 정리한다.
CTA는 조회수를 행동으로 바꾸는 장치이다.

## CTA Types

### 1. Save CTA

Purpose: 저장 수 증가

Examples:

- 저장해두고 필요할 때 꺼내 보세요.
- 나중에 다시 볼 수 있게 저장하세요.
- 이 체크리스트는 저장 필수입니다.
- 다음에 ___ 할 때 보려면 저장하세요.

Best For:

- 카드뉴스
- 체크리스트
- 도구 모음
- 프롬프트 모음

---

### 2. Comment CTA

Purpose: 댓글 증가, 알고리즘 참여율 증가

Examples:

- 댓글에 '자료' 남기면 보내드릴게요.
- 궁금하면 '궁금'이라고 댓글 남겨주세요.
- 필요한 분은 댓글로 알려주세요.
- 여러분은 어떻게 생각하세요?

Best For:

- 릴스
- 논쟁형 콘텐츠
- 무료 자료 제공
- 강의/컨설팅 퍼널

---

### 3. DM CTA

Purpose: 1:1 상담, 리드 수집

Examples:

- 자세한 내용은 DM 주세요.
- 고민 있으면 DM 주세요. 답해드릴게요.
- 신청 원하면 DM으로 알려주세요.
- 무료 자료는 DM으로 보내드립니다.

Best For:

- 컨설팅
- 강의
- 서비스 판매
- 고가 상품

---

### 4. Profile CTA

Purpose: 프로필 방문 유도

Examples:

- 더 많은 자료는 프로필 링크에 있습니다.
- 무료 가이드는 프로필에서 받아가세요.
- 관련 자료는 프로필 링크에 올려뒀습니다.
- 다음 단계가 궁금하면 프로필을 확인하세요.

Best For:

- 링크 모음
- XLink
- Linktree
- PDF 다운로드
- 강의 신청

---

### 5. Follow CTA

Purpose: 팔로우 전환

Examples:

- 이 시리즈 놓치기 싫으면 팔로우하세요.
- 매일 AI 자동화 팁을 올립니다.
- 다음 편에서 이어서 풀게요. 팔로우하세요.
- 비슷한 자료 계속 받고 싶으면 팔로우하세요.

Best For:

- 시리즈 콘텐츠
- 교육 계정
- AI툴 큐레이션

---

### 6. Share CTA

Purpose: 공유 유도

Examples:

- 이거 필요한 친구에게 공유하세요.
- 같이 시작할 사람 태그하세요.
- 주변에 ___ 하는 사람 있다면 보내주세요.

Best For:

- 실용 팁
- 무료 리소스
- 체크리스트

---

### 7. Edits Link CTA

Purpose: 릴스 안에서 클릭 유도

Examples:

- 바로 갈 수 있게 링크 걸어둘게요.
- 이 릴스 끝나면 다음 영상도 눌러보세요.
- 관련 영상은 화면 링크에서 확인하세요.
- 프로필로 바로 이동할 수 있게 연결해둘게요.

Best For:

- Reels
- Shorts Funnel
- Related Reels
- Profile Link

## CTA Engine Rules

CTA Engine은 아래 값을 기준으로 CTA를 선택한다.

```json
{
  "goal": "save | comment | dm | profile | follow | share | link_click",
  "content_type": "carousel | reels | shorts | blog",
  "topic": "AI tools | Instagram growth | side hustle | smartstore",
  "funnel_stage": "awareness | trust | lead | sale",
  "brand_profile": "account_specific"
}
```

## Recommended CTA by Content Goal

| Goal | Recommended CTA |
|---|---|
| 도달 증가 | 저장, 공유 |
| 댓글 증가 | 질문, 의견 요청 |
| 팔로워 증가 | 시리즈 예고 |
| 리드 수집 | 댓글 키워드, DM |
| 상품 판매 | 프로필 링크, 상담 DM |
| 영상 회전율 증가 | Edits 릴스 링크 |

## AI-Content-OS Integration

CTA Engine은 Publishing 직전에 실행한다.

```text
Content Engine
↓
CTA Engine
↓
Caption Generator
↓
Publishing Engine
```

릴스/쇼츠에서는 Video Engine 이후 Edits Link Plan과 함께 실행한다.

```text
Video Engine
↓
CTA Engine
↓
Edits Link Plan
↓
Publishing Checklist
```
