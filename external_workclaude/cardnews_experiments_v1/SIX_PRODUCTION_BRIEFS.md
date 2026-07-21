# Six Production Briefs — CardNews A/B Experiment V1

**상태: 기획 단계. 렌더링·게시 미수행.** 모든 "예상 효과"는 `hypothesis_only`이며 사실로 단정하지 않는다. DM 댓글 유도, 과장 훅, 근거 없는 효능 주장은 전 브리프에서 금지한다.

각 쌍은 `topic_content_id`, 근거(evidence), CTA가 동일하며 표에 명시된 변수 1개만 다르다. control 브리프는 `PATTERN_BINDINGS.json`의 `control_baseline_reference`(CN-006 기존 관행, 미수정·참고만)를 따른다.

---

## 실험 쌍 1 (EXP-1) — 변수: 표지 훅 · 분야: 건강·피트니스 · 주제: CN-010 초보자를 위한 홈트레이닝 루틴

### 공통 사항 (control/experiment 동일)
- **근거(evidence)**: 무리한 고강도 운동보다 저강도로 시작해 점진적으로 강도를 올리는 방식이 부상 위험을 낮춘다는 것은 일반적인 운동 상식으로 통용됨(구체적 수치·의학적 효능 주장 없음). 준비운동(warm-up)의 부상 예방 목적도 일반 상식 수준에서만 언급.
- **CTA**: "저장해두고 다음 운동할 때 다시 확인하세요" (저장 유도형, 댓글/DM 요청 없음)
- **슬라이드 수**: 4장 (CN-006 baseline 구조 준수 — hook / problem·context / evidence-backed solution / cta·source)
- **금지 사항**: "3일 만에 효과", "전문가가 검증한" 등 근거 없는 효능·권위 주장 금지. 인물 얼굴 클로즈업 지양(CN-006 규칙 준수).

### EXP1-CONTROL (통제군)
- **표지 훅(고정값)**: "초보자를 위한 홈트레이닝 루틴" — CN-006식 평서형 정보 타이틀. 수사적 반전·인용 장치 없음.
- **표지 이미지**: 운동 매트/실내 공간 등 상황·사물 이미지(인물 클로즈업 없음)
- **슬라이드 구성**: ① 훅(위 타이틀) → ② 문제(운동 초보자가 겪는 흔한 어려움: 시간 부족, 장비 없음) → ③ 해결(저강도 루틴 예시 3~4개, 각 동작 설명) → ④ CTA(저장 유도)
- **예상 결과 (hypothesis_only)**: 이 브리프는 비교 기준점 역할. 우열을 예단하지 않음.

### EXP1-VARIANT (실험군)
- **표지 훅(변경값)**: 인용·반전형 헤드라인 구조 적용 — 예시 톤: "'헬스장 안 다니면 소용없다'던 통념, 홈트레이닝으로 뒤집은 사람들의 근황" (실제 카피는 제작 단계에서 확정하되, 구체적 인물·통계를 지어내지 않고 통념→반전 구조만 유지)
- **표지 이미지**: EXP1-CONTROL과 동일(인물 클로즈업 없음, 상황/사물 이미지만) — 훅 "문구" 구조만 변경, 비주얼은 통제 유지
- **슬라이드 구성**: 훅 문구만 교체, ②~④는 EXP1-CONTROL과 동일
- **적용 패턴**: `pattern.instagram_learning.content_pattern.quote_reversal_hook` (evidence: https://www.instagram.com/p/DaNcegIkmEy/)
- **예상 결과 (hypothesis_only)**: 표지 클릭률·완독률이 control 대비 개선될 수 있다는 가설. 근거는 n=1·뉴스·시사 분야 관측이며 건강·피트니스로의 전이 효과는 검증되지 않음.

---

## 실험 쌍 2 (EXP-2) — 변수: 스토리 구조 · 분야: 생활정보 · 주제: CN-017 커피 원두 보관법

### 공통 사항 (control/experiment 동일)
- **content_evidence_basis**: `evidence_not_required` — 결과를 약속하지 않는 절차형 체크리스트만 사용한다. 공통 정보 단위는 `용기 선택`, `장소 선택`, `개봉 날짜 기록` 세 가지다.
- **CTA**: "저장해두고 원두 살 때마다 확인하세요" (저장 유도형)
- **슬라이드 수**: **항상 4장 고정**
- **cover_hook**: "원두 보관 체크리스트" — 철자·띄어쓰기까지 양 arm에서 동일한 문자열을 사용한다.
- **copy_length_rule**: 각 슬라이드 headline 1개와 body 1~2개 짧은 절차 문장.
- **visual_tone**: 사물·주방 환경 중심의 낮은 자극도 정보형 톤.
- **불변 계약**: topic, 세 정보 단위, CTA, 4장 수, cover_hook, visual_tone, copy_length_rule은 동일하다. 변경 허용 범위는 2·3장의 순차 안내와 번호형 목록 표현 차이뿐이다.

### EXP2-CONTROL (통제군)
- **스토리 구조(고정값)**: ① 동일 표지 → ② 순차 안내(용기를 고르세요. 보관 장소를 정하세요.) → ③ 순차 안내(개봉 날짜를 적으세요.) → ④ 동일 CTA.
- **주제 고정**: CN-017 커피 원두 보관법
- **훅 문구**: "원두 보관 체크리스트"
- **예상 결과 (hypothesis_only)**: 비교 기준점. 우열 예단 없음.

### EXP2-VARIANT (실험군)
- **스토리 구조(변경값)**: ① 동일 표지 → ② 번호형 목록(1. 용기 고르기 / 2. 보관 장소 정하기) → ③ 번호형 목록(3. 개봉 날짜 기록하기) → ④ 동일 CTA.
- **슬라이드 구성**: 정확히 4장. 번호 표기와 목록 배열만 적용하고 정보 단위는 통제군과 동일하게 유지한다.
- **주제 고정**: CN-017 커피 원두 보관법
- **훅 문구**: "원두 보관 체크리스트"
- **적용 패턴 출처**: `pattern.instagram_learning.content_pattern.numbered_curation_list_structure` (https://www.instagram.com/p/DZZko8HESg3/, https://www.instagram.com/p/DMR7KeXyMRs/, https://www.instagram.com/p/DZ1m16hEoJS/). 이 출처는 실험 구조의 provenance이며 콘텐츠 사실 근거가 아니다.
- **예상 결과 (hypothesis_only)**: 저장 지표가 달라질 수 있다는 가설이며 방향을 예단하지 않는다.

---

## 실험 쌍 3 (EXP-3) — 변수: 비주얼 레이아웃 · 분야: 지식·자기계발 · 주제: KN-008 시간관리 매트릭스 활용법

### 공통 사항 (control/experiment 동일)
- **근거(evidence)**: 중요도·긴급도 2축으로 할 일을 4분면에 분류하는 시간관리 매트릭스는 널리 알려진 자기관리 프레임워크(특정 저자·서적의 저작물 표현을 복제하지 않고 개념만 설명, 원저작자 표기는 통용 개념이므로 불요 — CN-006 attribution 규칙과 동일 기준 적용).
- **CTA**: "저장해두고 이번 주 할 일 정리할 때 활용하세요" (저장 유도형)
- **슬라이드 수**: 4장 (CN-006 baseline 구조 준수)
- **금지 사항**: "이 매트릭스로 생산성 200% 향상" 등 근거 없는 수치·효능 단정 금지.

### EXP3-CONTROL (통제군)
- **비주얼 레이아웃(고정값)**: CN-006 baseline — 자체 제작 인포그래픽(4분면 다이어그램은 도형/타이포로만 표현), 캐릭터 일러스트 없음, 실사 미사용, 인물 클로즈업 없음
- **슬라이드 구성**: ① 훅(매트릭스 주제 제시, 평서형 타이틀) → ② 문제(할 일이 뒤섞여 우선순위를 못 정하는 상황을 도형으로 표현) → ③ 해결(4분면 매트릭스 다이어그램 + 각 분면 설명) → ④ CTA
- **예상 결과 (hypothesis_only)**: 비교 기준점. 우열 예단 없음.

### EXP3-VARIANT (실험군)
- **비주얼 레이아웃(변경값)**: 캐릭터 의인화 일러스트 + 파스텔톤 배경 적용 — 4분면 다이어그램을 딱딱한 도형 대신 귀여운 캐릭터가 각 분면(예: "지금 당장!"에는 다급한 표정 캐릭터, "나중에"에는 여유로운 캐릭터)을 통해 설명하는 일러스트 스타일. 파스텔 블루/민트 배경(원 패턴 관측과 동일 색조 계열).
- **슬라이드 구성**: ①~④ 구성은 EXP3-CONTROL과 동일, 시각 스타일(일러스트+파스텔톤)만 교체
- **적용 패턴**: `pattern.instagram_learning.content_pattern.healthcare_public_character_illustration` (evidence: https://www.instagram.com/p/DX540sxj3kb/, https://www.instagram.com/p/DMumn3wvugh/)
- **예상 결과 (hypothesis_only)**: 체류시간·완독이 개선될 수 있다는 가설이나, 원 근거가 n=2·건강 분야 관측(계정 2개뿐)이라 지식 콘텐츠로의 전이 효과는 세 실험 중 가장 근거가 얇음.

---

## 공통 준수 사항 체크리스트 (전 6개 브리프)

- [x] 각 쌍 동일 topic_content_id·evidence·CTA, 변수 1개만 변경
- [x] pattern_id + evidence_url 결속 (`PATTERN_BINDINGS.json` 참고)
- [x] 모든 예상 효과 `hypothesis_only` 표기, 사실 단정 없음
- [x] CN-006 미수정 — baseline 관행만 참고
- [x] DM 댓글 유도 CTA 없음 (`engagement_mechanic.dm_keyword_cta` 미사용)
- [x] 과장 훅 없음 (수치·효능 단정형 훅 미사용)
- [x] 근거 없는 효능 주장 없음 (일반 상식 수준 근거만 사용, 구체적 미검증 수치 없음)
- [x] 렌더링·게시 미수행
