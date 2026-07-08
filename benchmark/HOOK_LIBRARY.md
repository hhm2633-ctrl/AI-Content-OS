# Hook Library

Last Updated: 2026-07-08

## Purpose

릴스, 카드뉴스, 쇼츠, 블로그 제목에 사용할 Hook Pattern Library이다.
출처 자료: Reels Hook 200 PDF, Instagram benchmark accounts.

주의: 원문 문장을 그대로 무한 복사하는 것이 목적이 아니다.
목적은 패턴을 추출하여 AI-Content-OS가 주제별로 새로운 훅을 생성하게 만드는 것이다.

## Hook Types

### 1. First 2 Seconds / 시선강탈형

Purpose: 스크롤을 멈추게 한다.

Patterns:

- 다들 안 될 거라 했어요. 근데 됐습니다.
- ___ 이제 막 시작했다면, 이건 꼭 보세요.
- 아무도 말해주지 않는 ___의 진실.
- 저는 몇 달 동안 이 실수를 했어요. 따라 하지 마세요.
- 이 작은 변화 하나가 결과를 완전히 바꿨어요.
- 지금 ___ 이렇게 하고 있다면, 손해 보고 있는 거예요.
- ___가 안 되는 진짜 이유.
- 3초만 보세요. ___ 이거 하나로 끝납니다.
- 이 영상 저장 안 하면 나중에 후회해요.
- ___ 하기 전에 이 영상부터 보세요.

AI-Content-OS Usage:

```json
{
  "type": "attention",
  "best_for": ["reels", "shorts", "carousel_first_slide"],
  "emotion": ["curiosity", "fear", "urgency"],
  "cta_fit": ["save", "watch_more"]
}
```

---

### 2. Tips / Tools / 저장 유발형

Purpose: 저장과 공유를 유도한다.

Patterns:

- ___를 한 번에 끌어올린 작은 습관 5가지.
- ___ 시간을 절반으로 줄이는 법.
- 초보도 매일 쓰는 ___ 툴 3가지.
- 매번 ___ 전에 확인하는 체크리스트.
- 무료인데 유료급인 ___ 툴 3가지.
- ___ 콘텐츠 일주일치를 1시간에 짜는 법.
- ___ 할 때 90%가 놓치는 세팅 하나.
- 저장해두고 ___ 할 때마다 꺼내 쓰는 템플릿.

AI-Content-OS Usage:

```json
{
  "type": "saveable_tip",
  "best_for": ["carousel", "reels", "blog"],
  "emotion": ["utility", "efficiency"],
  "cta_fit": ["save", "share"]
}
```

---

### 3. Beginner How-to / 초보 하우투형

Purpose: 초보자가 바로 따라 하게 만든다.

Patterns:

- 막막함 없이 ___ 시작하는 법.
- ___ 처음 시작할 때 알았으면 했던 가이드.
- ___를 단순하게 만드는 3단계 방법.
- 그대로 따라 해도 되는 저의 ___ 작업 흐름.
- 초보가 ___에서 꼭 하는 실수 하나.
- 경험이 0이어도 ___ 시작하는 법.
- ___ 첫 주에 뭘 해야 하는지 알려드릴게요.
- ___ 기초, 이 영상 하나로 끝냅니다.

AI-Content-OS Usage:

```json
{
  "type": "beginner_howto",
  "best_for": ["tutorial", "carousel", "youtube_shorts"],
  "emotion": ["relief", "clarity"],
  "cta_fit": ["follow", "save"]
}
```

---

### 4. Storytelling / Mindset / 연결형

Purpose: 팬과 신뢰를 만든다.

Patterns:

- ___ 처음엔 뭘 하는지도 몰랐어요.
- 이 실패가 어떤 성공보다 많은 걸 가르쳐줬어요.
- ___를 30일 동안 매일 하며 배운 것.
- ___를 그만두려던 그날, 그만두지 않았습니다.
- 완벽을 좇는 걸 멈춘 이유.
- 1년 전의 저에게 해주고 싶은 말.
- 조회수가 안 나와도 계속했던 이유.
- 그때 포기했다면 지금의 저는 없었어요.

AI-Content-OS Usage:

```json
{
  "type": "story_mindset",
  "best_for": ["personal_brand", "reels", "newsletter"],
  "emotion": ["empathy", "trust"],
  "cta_fit": ["comment", "follow"]
}
```

---

### 5. Authority / Trust / 권위형

Purpose: 전문가로 보이게 만든다.

Patterns:

- ___ 3년 해보고 내린 결론.
- ___ 전문가들이 절대 안 하는 것.
- ___로 먹고사는 사람의 하루 루틴.
- 수백 번 해보고 알게 된 ___의 공식.
- ___ 현업에서만 아는 꿀팁.
- ___, 이론 말고 실전은 이렇습니다.
- ___ 10년 차가 신입 때로 돌아간다면.
- ___ 잘하는 사람은 이 습관이 있어요.

AI-Content-OS Usage:

```json
{
  "type": "authority",
  "best_for": ["expert_account", "consulting", "course_funnel"],
  "emotion": ["trust", "respect"],
  "cta_fit": ["dm", "profile"]
}
```

---

### 6. Contrarian / Debate / 반전·논쟁형

Purpose: 댓글과 참여를 만든다.

Patterns:

- ___ 열심히 하지 마세요. 이유가 있어요.
- 다들 아는 ___ 조언, 사실 틀렸어요.
- ___에 돈 쓰지 마세요. 이걸로 충분해요.
- 인기 많은 그 ___ 방법, 저는 반대합니다.
- ___ 매일 하라고요? 그거 함정이에요.
- "___ 이렇게 해야 한다"는 거짓말.
- 남들과 반대로 했더니 ___가 됐어요.
- ___ 트렌드, 그냥 따라가지 마세요.

AI-Content-OS Usage:

```json
{
  "type": "contrarian",
  "best_for": ["reels", "threads", "shorts"],
  "emotion": ["surprise", "debate"],
  "cta_fit": ["comment"]
}
```

---

### 7. List / Curation / 리스트형

Purpose: 정보 밀도를 높여 저장을 유도한다.

Patterns:

- ___ 필수 도구 7가지.
- ___ 할 때 쓰는 앱 TOP 5.
- 저장 필수, ___ 무료 리소스 10개.
- ___ 초보가 봐야 할 계정 5개.
- ___ 관련 인생 책 3권.
- ___ 자동화 툴 베스트 5.
- ___ 템플릿 무료로 주는 곳 3군데.
- 요즘 뜨는 ___ 트렌드 5가지.

AI-Content-OS Usage:

```json
{
  "type": "list_curation",
  "best_for": ["carousel", "blog", "newsletter"],
  "emotion": ["utility", "collection"],
  "cta_fit": ["save", "share"]
}
```

---

### 8. Before/After / Result / 증거형

Purpose: 결과와 증거로 설득한다.

Patterns:

- ___ 30일 하고 달라진 점.
- ___ 전 vs 후, 이만큼 바뀌었어요.
- ___로 첫 수익 낸 과정 전부 공개.
- 100일 동안 ___ 한 결과.
- ___ 방법 바꾸고 나서 생긴 변화.
- 조회수 0에서 여기까지, ___ 기록.
- 실험: ___ 이 방법, 진짜 될까?
- ___ 처음과 지금, 솔직 비교.

AI-Content-OS Usage:

```json
{
  "type": "result_proof",
  "best_for": ["case_study", "reels", "carousel"],
  "emotion": ["proof", "credibility"],
  "cta_fit": ["dm", "profile", "save"]
}
```

---

### 9. Pain Point / 공감형

Purpose: 사용자가 “내 얘기다”라고 느끼게 한다.

Patterns:

- ___ 하는 사람만 아는 고충.
- "나만 이런가?" 싶은 ___의 순간.
- ___ 하다 보면 꼭 겪는 슬럼프.
- ___, 사실 시작이 제일 어렵죠.
- ___ 자꾸 미루게 되는 진짜 이유.
- 저도 ___ 이거 때문에 매번 막혔어요.
- ___, 이거 공감되면 저장하세요.
- 남들은 쉬워 보이는데 나만 ___ 어렵죠.

AI-Content-OS Usage:

```json
{
  "type": "pain_point",
  "best_for": ["reels", "shorts", "personal_brand"],
  "emotion": ["empathy", "relief"],
  "cta_fit": ["comment", "save"]
}
```

---

### 10. CTA / Sales / 전환형

Purpose: 시청자를 행동으로 바꾼다.

Patterns:

- 댓글에 '___' 남기면 무료로 보내드려요.
- 이거 필요한 분? 댓글 남겨주세요.
- ___ 자료, 선착순으로 DM 드립니다.
- 저장하고 ___ 할 때 꺼내 보세요.
- 팔로우하면 ___ 꿀팁 매일 올라와요.
- ___ 정리본 원하는 분, '신청'이라고 남겨주세요.
- 이 ___ 템플릿, 프로필 링크에 있어요.
- 댓글 하나면 ___ 전체 리스트 보내드려요.
- ___ 고민 있으면 DM 주세요.
- 이 시리즈 놓치기 싫으면 팔로우.

AI-Content-OS Usage:

```json
{
  "type": "conversion_cta",
  "best_for": ["final_slide", "reels_end", "caption"],
  "emotion": ["action", "urgency"],
  "cta_fit": ["comment", "dm", "profile"]
}
```

## Implementation Note

Hook Engine은 아래 값을 기준으로 훅을 선택해야 한다.

- topic
- platform
- content_type
- brand_profile
- target_audience
- desired_action
- recent_used_hooks
- performance_history
