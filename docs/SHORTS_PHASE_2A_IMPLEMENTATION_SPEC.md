# Shorts Phase 2A — 편집 패키지 내보내기 구현 명세

Status: **IMPLEMENTATION SPEC ONLY — CTO APPROVAL REQUIRED BEFORE CODE**

## 1. 목표

Phase 1의 오프라인 Shorts 결과를 사람이 편집 도구로 옮길 수 있는 독립적인 export
폴더로 변환한다. Phase 2A는 실제 영상을 만들거나 게시하지 않는다. 결과물은 JSON,
SRT, 1080x1920 timeline manifest와 사용자 제공 asset 검증 보고서다.

핵심 사용자 결과:

- 한 Shorts 기획 결과당 하나의 재현 가능한 편집 패키지
- 편집자가 장면 순서, 시간, 자막, asset 경로와 권리 상태를 한 폴더에서 확인
- 누락되거나 미승인된 asset이 있어도 안전한 패키지와 수동 작업 목록 생성
- 실제 render 또는 publish 완료로 오인할 수 없는 명시적인 상태값

## 2. 승인 범위와 금지 범위

### 승인 요청 범위

- Phase 1의 9개 결과 계약을 읽는 standalone exporter
- JSON 편집 패키지, SRT 자막, 1080x1920 timeline manifest 생성
- 사용자가 로컬에서 제공한 asset의 존재성, 형식, 장면 연결, 출처 상태 검증
- export 폴더 생성과 파일 쓰기 fallback
- 독립 단위·통합 테스트

### 금지 범위

- 외부 API, 네트워크 요청 또는 API key
- TTS, 전사, 번역 또는 음성 합성
- 영상 인코딩, 합성, animation 또는 renderer
- CapCut/Edits 프로젝트 파일의 비공개 형식 역공학
- Instagram/Meta/YouTube 자동 게시 또는 계정 자동화
- `src/workflow_engine.py` 연결 또는 변경
- CardNews, AI Planner, `site/` 변경
- 실제 transcript, render, publish, 조회·유지율·engagement 생성 주장

## 3. 입력 계약

### 3.1 필수 입력

Exporter는 Phase 1 `shorts_result.json`과 동일한 dict를 입력으로 받는다. 다음 9개
계약 키가 대상이다.

1. `shorts_brief_result`
2. `shorts_script_result`
3. `shorts_scene_plan_result`
4. `shorts_asset_plan_result`
5. `shorts_caption_result`
6. `shorts_audio_plan_result`
7. `shorts_render_plan_result`
8. `shorts_qa_result`
9. `shorts_publish_prep_result`

Exporter는 각 계약의 `status`, `fallback_used`, `reason`을 보존한다. 알 수 없는 추가
필드는 삭제하지 않고 `source_contracts.json`에 그대로 보존하되, timeline 계산에는
명시적으로 지원하는 필드만 사용한다.

### 3.2 사용자 제공 asset 입력

선택 입력 `user_assets`는 list이며 각 항목은 다음 계약을 따른다.

```json
{
  "scene_id": 1,
  "file_path": "user-assets/scene-01.mp4",
  "asset_type": "background_video",
  "topic_relevant": true,
  "copyright_status": "licensed",
  "license_reference": "licenses/stock-provider-receipt.pdf",
  "provided_by": "user"
}
```

Phase 2A는 파일을 자동 탐색하거나 인터넷에서 보충하지 않는다. `file_path`와 license
증빙은 exporter의 명시적 `asset_root` 내부 일반 파일만 허용한다. `..`, root 이탈,
export root 재참조, symlink/reparse 경로, directory·device 등 비정규 파일은 content
hash·size·magic read 전에 차단한다. 결과에는 절대경로 대신 `asset_root` 기준 상대 reference만
남긴다.

허용 `copyright_status`:

- `owned`
- `licensed`
- `public_domain`
- `official_reuse_allowed`
- `user_supplied_with_permission`

`unknown`, `restricted`, `third_party_unlicensed_reference` 또는 미지원 값은 차단한다.

## 4. 출력 계약

### 4.1 최상위 export 결과

```json
{
  "module": "ShortsEditingPackageExporter",
  "status": "shorts_editing_package_created",
  "package_version": "2a.1",
  "export_root": "storage/shorts/exports/<package_id>",
  "files": {
    "source_contracts": "source_contracts.json",
    "editing_package": "editing_package.json",
    "timeline_manifest": "timeline_manifest.json",
    "captions_srt": "captions.srt",
    "asset_validation": "asset_validation.json",
    "manual_checklist": "manual_checklist.json"
  },
  "rendered_video_path": null,
  "external_calls_attempted": false,
  "manual_action_required": true,
  "fallback_used": false,
  "reason": ""
}
```

`status` 허용값:

- `shorts_editing_package_created`: 필수 파일을 모두 기록함
- `shorts_editing_package_partial`: 일부 비필수 산출물이 fallback으로 기록됨
- `shorts_editing_package_fallback`: 필수 입력 또는 파일 쓰기 문제로 정상 export 불가

어떤 상태에서도 `rendered_video_path`는 `null`이며 `manual_action_required`는 `true`다.

### 4.2 `editing_package.json`

사람과 편집 도구 adapter가 사용할 정규화된 요약이다.

```json
{
  "package_version": "2a.1",
  "package_id": "deterministic-title-caption-hash",
  "title": "...",
  "target": {"width": 1080, "height": 1920, "orientation": "vertical"},
  "duration_seconds": 25.0,
  "scene_count": 4,
  "caption_format": "srt",
  "timeline_manifest": "timeline_manifest.json",
  "asset_validation": "asset_validation.json",
  "production_mode": "manual_editing_required",
  "rendered": false,
  "published": false
}
```

`package_id`는 scene content/order/timing, 정규화된 caption 계약, 사용자 asset의 실제
content hash·크기·확장자·scene 연결·권리 상태·`provided_by`, license 증빙 hash를 canonical
JSON으로 직렬화한 뒤 SHA-256으로 결정한다. asset/license 원본 경로와 user asset/caption
입력 배열 순서는 ID에 영향을 주지 않는다. timestamp 또는 random 값을 쓰지 않으며 동일
의미 입력은 동일 ID를 만든다. 기존 폴더를 덮어쓸지는 명시적 `overwrite=True`일 때만 허용한다.

### 4.3 `captions.srt`

- caption 순서는 `start_seconds`, `scene_id` 순으로 고정한다.
- SRT 번호는 1부터 연속 증가한다.
- 시간 형식은 `HH:MM:SS,mmm --> HH:MM:SS,mmm`이다.
- 시작은 0 이상, 종료는 시작보다 커야 한다.
- 다음 caption 시작은 이전 종료보다 빠를 수 없다.
- 최종 종료 시간은 script/timeline duration을 초과할 수 없다.
- 텍스트의 SRT 구분 충돌을 막기 위해 개행을 정규화한다. 빈 텍스트는 항목을 만들지
  않고 validation warning으로 기록한다.
- 자막은 Phase 1 script 기반 추정치이며 transcript가 아님을 manifest에 명시한다.

### 4.4 `timeline_manifest.json`

```json
{
  "schema_version": "2a.1",
  "canvas": {
    "width": 1080,
    "height": 1920,
    "pixel_aspect_ratio": "1:1",
    "orientation": "vertical"
  },
  "timebase": {"unit": "seconds", "fps": null},
  "duration_seconds": 25.0,
  "rendering_supported": false,
  "caption_source": "script_text_only",
  "transcription_used": false,
  "scenes": [
    {
      "scene_id": 1,
      "order": 1,
      "start_seconds": 0.0,
      "end_seconds": 3.0,
      "duration_seconds": 3.0,
      "script_line_ids": [1],
      "visual_type": "text_over_background",
      "transition": "cut",
      "asset": {
        "package_path": null,
        "validation_status": "manual_asset_required",
        "render_allowed": false
      },
      "caption_ids": [1]
    }
  ],
  "warnings": []
}
```

Phase 2A는 frame-accurate 편집을 주장하지 않으므로 `fps`는 `null`이다. scene 시작 시간은
이전 scene 종료 시간에서 누적 계산한다. scene duration 합계, script duration, caption
최종 시간이 불일치하면 자동 보정하지 않고 warning과 partial 상태를 기록한다.

### 4.5 `asset_validation.json`

각 scene마다 정확히 하나의 검증 결과를 만든다.

```json
{
  "status": "asset_validation_completed",
  "all_assets_ready": false,
  "manual_asset_required_count": 1,
  "items": [
    {
      "scene_id": 1,
      "source_path": "...",
      "package_path": null,
      "exists": false,
      "is_file": false,
      "supported_extension": false,
      "topic_relevant": null,
      "copyright_status": "unknown",
      "license_reference_present": false,
      "render_allowed": false,
      "validation_status": "manual_asset_required",
      "warnings": ["No user-provided asset"]
    }
  ],
  "fallback_used": true,
  "reason": "One or more scenes require a validated user asset."
}
```

`render_allowed=true` 조건은 모두 충족해야 한다.

1. scene이 실제 존재한다.
2. 경로가 존재하는 일반 파일이다.
3. 확장자가 승인 목록에 있다.
4. `topic_relevant is true`다.
5. `copyright_status`가 허용 목록에 있다.
6. `provided_by`가 정확히 `user`다.
7. `licensed`일 때 `license_reference`가 path로 가리키는 실제 증빙 파일이 존재한다.
8. 확장자와 최소 file magic signature가 일치한다.

초기 승인 확장자 제안:

- video: `.mp4`, `.mov`, `.webm`
- image: `.png`, `.jpg`, `.jpeg`, `.webp`
- audio는 Phase 2A asset copy 대상에서 제외한다.

Phase 2A는 PNG/JPEG/WebP 및 MP4/MOV/WebM의 최소 magic/container signature만 검증한다.
이는 콘텐츠 안전성이나 실제 영상 codec 재생 가능성을 보증하지 않는다. 실제 decode 및
video codec 검증은 명시적인 **Phase 2B CTO gate**이며 manifest와 asset validation에
`codec_validation: "not_performed_phase_2b_gate"`로 기록한다.

## 5. export 폴더 구조

```text
storage/shorts/exports/<package_id>/
  source_contracts.json
  editing_package.json
  timeline_manifest.json
  captions.srt
  asset_validation.json
  manual_checklist.json
  assets/
    scene-001.<ext>       # 검증 통과 후 복사가 승인된 사용자 파일만
  licenses/
    README.json           # 원본 license reference와 package asset 연결 정보
```

구현 시 기본 export root는 생성자 또는 명시적 인자로 교체할 수 있어야 한다. 테스트는
임시 디렉터리를 사용한다. 원본 asset은 이동·삭제하지 않고 복사만 한다. package 안의
파일명은 사용자 경로를 그대로 사용하지 않고 `scene-NNN` 규칙으로 정규화해 path traversal,
충돌과 개인정보 노출을 줄인다.

Asset 복사 실패는 전체 계약을 없애지 않는다. 해당 scene을
`asset_copy_failed`/`render_allowed=false`로 내리고 manual checklist에 추가한다.
부분 copy 파일은 즉시 제거하며 staging 검증은 `asset_validation.json`의 package path 집합과
실제 `assets/` 일반 파일 집합이 정확히 일치할 때만 통과한다.

모든 JSON/SRT/asset/license 산출물은 final package의 sibling staging directory에서 먼저
완성하고 parse/필수 파일 검증을 통과해야 한다. 신규 package는 검증된 staging directory를
final path로 rename한다. `overwrite=True`는 기존 final을 sibling backup으로 rename한 뒤 새
staging을 final로 교체하며, 교체 실패 시 기존 package를 복구한다. 따라서 어느 쓰기·복사·
검증 단계가 실패해도 불완전 final package를 노출하지 않고 stale asset/marker를 남기지 않는다.

## 6. 수동 체크리스트

`manual_checklist.json`은 최소 다음 항목과 완료 여부를 포함한다.

1. 모든 scene의 asset 존재·주제 관련성·권리 확인
2. voice 녹음 또는 승인
3. 사용 허가된 music 선택
4. 실제 편집 결과 기준 caption timing 재검수
5. 1080x1920 최종 영상 전체 시청
6. likeness, 저작권, AI disclosure 확인
7. 대상 계정과 caption/hashtag 확인 후 수동 업로드

Phase 2A는 체크리스트 항목을 자동 완료 처리하지 않는다. export 직후
`completed=false`, `manual_action_required=true`가 정상이다.

## 7. fallback 및 실패 처리

| 실패 조건 | 결과 | 전체 상태 |
|---|---|---|
| 입력이 dict가 아니거나 9개 계약 전체가 없음 | 빈 안전 계약과 진단만 반환, 파일 생성 시도 안 함 | `fallback` |
| 일부 계약 누락·형식 오류 | 가능한 장면과 자막만 export, 누락 필드 warning | `partial` |
| scene 없음 | 빈 timeline/SRT와 수동 재작성 체크리스트 | `partial` |
| duration 불일치 | 원값 보존, 자동 stretch 금지, warning | `partial` |
| caption 시간 역전·중첩 | 잘못된 항목 SRT 제외, JSON에 진단 보존 | `partial` |
| asset 없음 | scene placeholder metadata만 생성 | `created` 또는 `partial` |
| 미승인 권리·주제 불일치 | 복사 금지, `render_allowed=false` | `created` 또는 `partial` |
| asset 복사 실패 | 다른 산출물 유지, scene별 오류 기록 | `partial` |
| export 폴더/필수 JSON 쓰기 실패 | 예외를 외부로 내보내지 않고 reason 반환 | `fallback` |
| SRT 쓰기 실패 | staging 정리, final package 미생성·기존 final 유지 | `fallback` |
| duplicate scene ID | staging 생성 전 차단 | `fallback` |
| package path file/symlink collision | 기존 경로를 수정하지 않고 차단 | `fallback` |
| staging 쓰기·검증 실패 | staging 정리, 기존 final 유지 | `fallback` |
| overwrite 교체 실패 | 기존 package 원자 복구 | `fallback` |

모든 fallback 결과에 `external_calls_attempted=false`, `rendered=false`,
`published=false`를 기록한다. 로그나 결과에 사용자 원본 파일의 binary 또는 credential을
포함하지 않는다. source contract의 credential-like key는 `[REDACTED]`로 저장하고, raw
exception·절대경로는 외부 결과에 노출하지 않는다. 실패는 `blockers[]`의 안정적인
`code`/`stage`/`retryable` 값으로 전달한다.

## 8. 제안 구현 파일과 소유권

Phase 2A 구현 Sprint 승인 후 한 writer가 다음 파일을 독점 소유한다.

```text
modules/shorts/shorts_exporter.py                 # exporter/SRT/timeline/asset validator 통합
tests/test_shorts_phase_2a_exporter.py             # 위험 기반 standalone 테스트
```

조건부 소유:

- `modules/shorts/__init__.py`: 공개 import가 필요하다고 CTO가 승인할 때만
- 기존 `modules/shorts/shorts_module.py`: Phase 2A exporter를 호출하지 않는다. 변경이
  필요한 경우 별도 integration 승인 필요

보호 파일:

- `src/workflow_engine.py`
- `modules/card_news/**`
- `modules/ai_planner/**`
- `site/**`
- 기존 Phase 1 테스트
- `CURRENT_TASK.md`, `ROADMAP.md`, `MODULE_STATUS.md`, `DECISIONS.md`, `CHANGELOG.md`,
  `PROJECT_SNAPSHOT.md`, `docs/ACTIVE_PARALLEL_WORK_ORDERS.md`
- Git stage/commit/push는 CTO integration lane 전용

## 9. 위험 기반 테스트 명세

### 계약과 정상 export

- 실제 Phase 1 Content 기반 결과로 6개 필수 파일과 `assets/` 구조 생성
- 동일 입력은 동일 `package_id`, scene order, SRT를 생성
- 모든 JSON이 UTF-8이며 다시 parse 가능
- timeline canvas가 정확히 1080x1920이고 `rendering_supported=false`

### SRT와 duration

- 0초, 밀리초 반올림, 1시간 미만의 일반 시간 변환
- caption 번호 연속성, 시간 단조 증가, 중첩 차단
- 최종 caption 종료와 timeline duration 일치
- duration 불일치 시 자동 왜곡 없이 partial + warning
- 빈 자막, 개행, 특수문자와 한국어 보존

### asset provenance

- 허용 권리 + 주제 관련 + 실제 파일만 복사 허용
- `licensed`인데 실제 license 증빙 파일이 없으면 차단
- `provided_by != "user"` 차단
- 확장자 위장 파일을 magic signature로 차단
- `unknown`, `restricted`, 미지원 확장자, directory 경로 차단
- 존재하지 않는 파일, 중복 scene, 알 수 없는 scene ID 차단
- `../` 경로가 package 경계를 벗어나지 못함
- 원본 파일은 수정·이동·삭제되지 않음

### fallback과 파일 I/O

- `None`, 문자열, 비어 있는 dict, 부분 계약에서 예외가 밖으로 나오지 않음
- JSON, SRT, asset copy 각각의 쓰기 실패가 지정된 partial/fallback으로 변환
- asset 하나 실패해도 나머지 scene과 manifest 유지
- 기존 package 폴더는 `overwrite=False`에서 변경되지 않음
- 중간 쓰기 실패 시 불완전 final/staging이 남지 않음
- overwrite 실패 시 기존 완전 package가 byte-for-byte 유지됨
- overwrite 성공 시 stale asset/marker가 제거됨
- scene/caption/asset/provenance 변화가 package ID를 변경함
- manifest caption ID와 SRT cue ID가 동일함
- duplicate scene ID와 package path collision 공격 차단
- asset/license path containment와 symlink/비정규 파일 선차단
- hash/size/magic read가 path 승인 전에 호출되지 않음
- raw exception, credential, 절대경로가 package/fallback에 남지 않음
- copy 실패 orphan과 manifest 불일치가 final package로 승격되지 않음
- backup cleanup 실패 시 기존 package 복구, 복구 실패 시 구조화 blocker 반환
- 경로와 입력 배열 순서가 달라도 동일 의미 입력은 동일 package ID
- 실패 결과도 외부 호출·render·publish가 없음을 명시

### 경계 보호

- exporter source에 network/TTS/transcription/renderer/publish import가 없음
- `src/workflow_engine.py`에 `modules.shorts` 연결이 없음
- CardNews와 AI Planner import가 없음

## 10. 완료 기준

Phase 2A 구현 완료 판정에는 다음이 모두 필요하다.

- 명세된 JSON/SRT/timeline/asset-validation/checklist 파일 생성
- 실제 Phase 1 결과 기반 standalone export 성공
- 위험 기반 테스트 전체 통과
- `py -m compileall src modules scripts` 통과
- 기존 Phase 1 Shorts 테스트 전부 통과
- 외부 호출, render file, publish 동작이 없음을 결과와 테스트로 확인
- 누락 asset이 있는 패키지를 성공적인 제작 완료로 표시하지 않음
- CTO integration lane의 diff 검토와 문서/Git 후속 처리

## 11. CTO 승인 게이트

구현 전 필요한 승인:

1. Phase 2A를 Phase 1과 분리된 standalone exporter로 구현할지 승인
2. 제안된 5개 구현·테스트 파일의 단일 writer 소유권 승인
3. 사용자 asset을 export 폴더로 복사할지, 참조 manifest만 만들지 결정
4. 허용 asset 확장자 목록 승인
5. `licensed` asset의 `license_reference` 필수 정책 승인
6. 기본 export root와 기존 package overwrite 정책 승인

Phase 2A 이후에도 별도 승인 없이는 금지되는 항목:

- TTS/STT/번역 provider와 credential
- 실제 video renderer 또는 편집 도구 자동화
- 음원/stock asset 외부 공급자 연결
- 플랫폼 자동 게시와 OAuth
- AI Planner 또는 WorkflowEngine 연결
