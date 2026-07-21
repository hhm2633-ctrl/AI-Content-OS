---
name: publishing-engine
description: Publishing Engine 전용 Domain Skill. Caption, Hashtag, Publishing Queue, Publish Result를 다룬다.
---

# Publishing Engine Skill

## 대상 모듈

`modules/publishing/publishing_module.py` (`PublishingModule`) — WorkflowEngine의 마지막 단계. `card_news_result`를 받아 발행 준비물을 만든다. 실제 업로드는 하지 않는다 (`upload_mode: "manual"`이 기본값).

## Caption

- `_create_caption(title)`이 고정 템플릿 문장(제목 + 안내 문구)으로 캡션 본문을 만든다.
- `_create_full_caption(caption, hashtags)`이 캡션 + 해시태그를 합쳐 최종 텍스트를 만든다.

## Hashtag

- `config/publishing.json`의 `hashtags` 배열을 읽는다 (파일 없으면 하드코딩 fallback 목록 사용).
- `_create_hashtags()`가 `#` 접두사를 정규화하고 최대 20개로 제한한다.

## Publishing Queue

- `_create_publish_queue()`가 `config/publishing.json`의 `platform`/`upload_mode`/`accounts`/`schedule`을 읽어 큐 아이템 하나를 만든다.
- `storage/publishing/publish_queue.json`에 저장된다 (`queue_id`, `platform`, `account_id`, `card_paths`, `full_caption`, `scheduled_time`, `status: "ready_for_manual_upload"`, `next_action`).

## Publish Result

- `storage/publishing/publishing_result.json` — 모듈 전체 결과 (title, card_count, card_paths, caption, hashtags, full_caption, next_action).
- `storage/publishing/caption.txt`, `storage/publishing/hashtags.txt` — 사람이 바로 복사해 쓸 수 있는 텍스트 파일.

## 절대 원칙

- 이 모듈은 실제 Instagram API 호출이나 자동 업로드를 수행하지 않는다 — "사람이 확인 후 수동 업로드"가 현재 설계다. 자동 업로드 기능을 추가하는 것은 이 프로젝트의 현재 우선순위(카드뉴스 MVP)를 벗어나는 확장이므로 `planning.md`의 ROI 평가를 먼저 거친다.
- `config/publishing.json`이 없거나 손상돼도 하드코딩된 fallback 설정으로 동작해야 한다.
- 이 단계가 실패해도 이전 단계(`card_news_result`)는 이미 완성되어 있으므로, 실패를 최대한 fallback 값(`caption`/`hashtags` 기본값)으로 흡수하고 `workflow_failed`로 이어지지 않게 한다.
