# 2026-07-19 Capacity And Recovery Notes

## Dirty Claude worktrees (18)

- `worktree-cardnews-topic-intelligence-v1` — CardNews 주제 지능·Instagram 학습 패턴·제작 실험 자료 (138 changes).
- `worktree-claude-hook-guard-review` — Claude hook guard와 Agent Console 카테고리 프롬프트 연결 (5 changes).
- `worktree-community-metrics-parser-v1` — 커뮤니티 수집기·지표 파서·source intake 설정 (20 changes).
- `worktree-elegant-sauteeing-sonnet` — EDaily 수집기 recon·fixture 계약 (2 changes).
- `worktree-hankyung-economy-recon` — 한국경제 수집기 recon·fixture 계약 (2 changes).
- `worktree-ig-feed-native-scan-v1` — Instagram 피드 네이티브 디자인 스캔 보고서 (4 changes).
- `worktree-lovely-soaring-patterson` — DCInside 수집기 recon·fixture 계약 (2 changes).
- `worktree-mk-economy-recon` — 매일경제 수집기 recon·fixture 계약 (2 changes).
- `worktree-moneytoday-recon` — 머니투데이 수집기 recon·fixture 계약 (2 changes).
- `worktree-nate-news-rank-recon` — Nate 뉴스 랭킹 수집기 recon·fixture 계약 (2 changes).
- `worktree-naver-news-parser-recovery` — Naver 뉴스 파서 복구·API hub·회귀 테스트 (4 changes).
- `worktree-news-category-profiles-v1` — 뉴스 카테고리 프로필·수집기·source intake 연결 (17 changes).
- `worktree-news1-recon-outputs` — News1 수집기 recon·fixture 계약 (2 changes).
- `worktree-newsis-recon` — Newsis 수집기 recon·fixture 계약 (2 changes).
- `worktree-ruliweb-dogdrip-collectors` — Ruliweb·Dogdrip 수집기와 테스트 (5 changes).
- `worktree-source-intake-v1` — source intake schema·capability map·metrics와 수집기 연결 (12 changes).
- `worktree-tender-soaring-seahorse` — Daum 뉴스 수집기 recon·fixture 계약 (2 changes).
- `worktree-virtual-crafting-sunset` — Instagram 피드 네이티브 디자인 스캔 보고서 (4 changes).

Clean worktrees: `worktree-design-learning-import-v1`, `worktree-proud-singing-muffin`. `worktree-design-learning-import-v1` is one commit ahead of `main`; do not remove before recovery review.

## Verified storage notes

- F: redirect policy: keep repository code/lightweight manifests on C:, and route large collected/generated media, catalogs, caches, review artifacts, and external tool runtimes to `F:\AI-Content-OS-Data` to prevent C: repository growth.
- `external_workmanus/seller_automation/data/seller.db` remains in place; verified backup copy is `F:\AI-Content-OS-Data\archives\seller_20260719.db` (134,078,464 bytes, SHA-256 matched).
- Do not run `git gc`, prune, or history rewriting until Manus work resumes and finishes. `.git` is 462.07 MiB; 419.33 MiB is unreachable loose objects, led by an unreachable blob matching `seller.db`.
- `site/` is a nested Next.js source repository plus generated output, not a disposable build-only folder. Its 628.21 MiB is mostly `node_modules` (451.98 MiB) and `.next` (170.90 MiB); the root repository tracks no `site/` files.
- `artifacts/` (221.54 MiB) is mixed: regenerable render/review output plus non-guaranteed original, selection, learning, relation, and evidence data. Never delete wholesale.
- `tools/` (151.89 MiB) is mostly regenerable `cardnews-renderer/node_modules`; preserve its four source/lock/runner files.
- `graphify-out/` (90.85 MiB) is regenerable graph output plus time/token-saving cache and dated snapshots.
- `.claude/worktrees/` (57.43 MiB) contains 18 dirty worktrees; recover or review each before removal.
- Test temp cleanup now retries explicitly and logs/raises persistent deletion failures. The five focused modules ran 68 tests: all passed, zero cleanup retries/final failures, zero remaining `.tmp_test_workspace/tmp*` directories.
