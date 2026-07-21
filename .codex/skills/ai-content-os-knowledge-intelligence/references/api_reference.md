# Pattern Contract Reference

필수 필드는 `pattern_id`, `name`, `domain`, `source_claim_ids`, `preconditions`, `recommended_action`, `prohibited_actions`, `success_metrics`, `failure_signals`, `confidence`, `status`, `version`, `reviewed_at`, `owner_skill`, `supersedes`, `expires_at`이다. 추가·누락 필드는 허용하지 않는다.

상태 흐름은 `CANDIDATE → VERIFIED → PROMOTED → DEPRECATED`이다. `CANDIDATE`와 `VERIFIED`는 `REJECTED`로 종료할 수 있다. 종료 상태에서 되돌리지 않는다.

`PROMOTED`는 source claim, 성공 지표, 검토 시각, runtime의 `performance_met=True`, `human_approved=True`가 모두 필요하다. 일반 `register()`로 우회하지 않는다.

버전은 점으로 구분한 숫자 문자열이며 후행 0은 동등하다. 활성 패턴의 domain/name/action/preconditions 정규화 fingerprint가 같으면 의미 중복으로 거부한다.

Related project contracts:
- product-management/references/communication.md - Comprehensive guide for status updates
- product-management/references/context_building.md - Deep-dive on gathering context
- bigquery/references/ - API references and query examples

## Validation Rules

- exact schema validation
- status transition validation
- canonical version progression
- semantic duplicate rejection
- acyclic supersedes validation
- source-free promotion rejection
- Comprehensive API documentation
- Detailed workflow guides
- Complex multi-step processes
- Information too lengthy for main SKILL.md
- Content that's only needed for specific use cases

## Structure Suggestions

### API Reference Example
- Overview
- Authentication
- Endpoints with examples
- Error codes
- Rate limits

### Workflow Guide Example
- Prerequisites
- Step-by-step instructions
- Common patterns
- Troubleshooting
- Best practices
