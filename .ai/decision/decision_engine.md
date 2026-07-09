# Decision Engine

작업이 들어왔을 때 "지금 할지/미룰지"와 "누가 할지"를 판단하는 기준이다.
ChatGPT CTO가 Sprint를 설계할 때, 그리고 Claude/Codex가 애매한 요청을 받았을 때 이 기준으로 판단한다.

## 1. ROI 평가

```text
카드뉴스 MVP(Trend→Topic→Pattern→Research→Content→Image→CardNews→Publishing)에
직접 기여하는가?
        ↓ 예                              ↓ 아니오
     지금 진행                      ROADMAP.md로 이동 (M5/M6/Later Roadmap)
```

- "직접 기여"의 기준: 이 파이프라인의 안정성, 품질(가독성/강조/CTA/QA), 실패율(fallback 빈도), 실행 속도 중
  하나 이상을 개선하는가.
- Shorts/Blog/SmartStore/대시보드/영상 렌더러 등은 이미 `ROADMAP.md`에 M5~M6, Later Roadmap으로 분류되어
  있다 — 명시적 승인 없이는 지금 만들지 않는다.

## 2. 파일 수 기준 (담당 AI 1차 판단)

| 조건 | 담당 |
|---|---|
| 8개 이상 파일 수정/생성, 새 모듈(엔진) 추가, 복잡한 리팩토링 | Claude |
| 그 미만의 국소 수정 (설정값 조정, 문구 수정, 작은 버그 수정) | Codex 직접 처리 가능 |

## 3. 위험도 기준

| 위험 신호 | 처리 |
|---|---|
| `src/workflow_engine.py` 구조 변경이 필요해 보임 | 반드시 사용자 명시적 승인 필요 — 기본값은 "하지 않는다" |
| `storage/**` 스키마를 바꿔야 할 것 같음 | 하위 호환(기존 필드 유지 + 새 필드 추가)으로 우회 가능한지 먼저 검토 |
| 기존 모듈/클래스/함수 이름 변경이 필요해 보임 | `.claude/skills/refactoring.md` 기준 최소화, 승인 필요 |
| 되돌리기 어려운 작업(파일 삭제, git 강제 명령, storage 대량 정리) | Claude가 직접 실행하지 않고 가이드만 제시, 실행은 Codex/사용자 |
| API Key/네트워크/외부 서비스 관련 | `.ai/rules/project_rules.md`의 보안/Fallback 우선 원칙 적용 |

## 4. Claude vs Codex 선택 기준 (종합)

Claude가 담당해야 하는 신호 (하나라도 해당하면 Claude):

- 8개 이상 파일
- 새 모듈/엔진 디렉터리 생성
- 여러 파일에 걸친 리팩토링
- "전체 파일을 새로 작성해야 하는" 성격의 작업
- 설계 판단(어떤 구조로 만들지)이 필요한 작업

Codex가 담당해야 하는 신호:

- Repository 상태 확인/정리, 커밋
- Compile/Workflow 실행 및 결과 확인
- 이미 설계가 끝난 작은 수정의 적용
- 문서 자동 생성 스크립트 실행 및 최종 반영

## 5. Roadmap 판단 기준

- `ROADMAP.md`의 M1(Trend Engine)~M4(Publishing/Scheduler)는 카드뉴스 MVP 범위 — 우선순위 높음.
- M5(Dashboard/Analytics), M6(Shorts/Blog/Store 확장), Later Roadmap(Timeline/Animation/Video/PDF)은
  후순위 — 명시적 요청이 없으면 Sprint화하지 않는다.
- 후순위 항목에 대한 아이디어/요청이 들어오면, 구현하지 않고 `ROADMAP.md`에 항목으로 추가하는 것까지만 한다
  (문서 수정이 이번 Sprint에서 허용된 경우에 한함).

## 사용 예

> "카드뉴스 레이아웃에 새 스타일을 추가해줘" → ROI: MVP 직접 기여(예) → 파일 수: 기존 파일 확장이면 소규모,
> 새 클래스 여러 개면 Claude → 위험도: 새 Layout 타입 생성은 `cardnews.md`가 금지 → 먼저 기존 10종으로
> 해결 가능한지 확인 후 진행.
