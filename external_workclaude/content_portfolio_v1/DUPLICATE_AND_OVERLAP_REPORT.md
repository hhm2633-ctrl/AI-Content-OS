# Duplicate and Overlap Report

Total title pairs inspected: 7140. Similarity = character-bigram Jaccard on `working_title` (threshold >= 0.30 shown).

- CANDIDATE_TRUE_DUPLICATE (same channel, sim >= 0.55): **0**
- IN_CHANNEL_STRUCTURAL_SIMILARITY (same channel, 0.35 <= sim < 0.55): **4**
- CROSS_CHANNEL_CLUSTER_MEMBER (different channel, same theme_tag -- already formalized as a cluster): **1**
- CROSS_CHANNEL_OVERLAP_CANDIDATE (different channel, sim >= 0.30, no shared theme_tag yet): **1**

## Verdict

**0 same-channel true duplicates found.** No brief was removed because none met the true-duplicate bar (same content_type + near-identical title). Every 25 CardNews / 20 Shorts / 20 Instagram / 20 Commerce topics is a distinct core subject; where two briefs share a domain (e.g. winter vs. summer energy saving), they are an intentional seasonal or catalog pair, not redundant copies.

The one pattern the CTO's instruction specifically anticipated -- "채널 이름만 바꾼 실질적 중복" -- was investigated directly: CN-016 ("여행 전 짐싸기 체크리스트", CardNews) and SH-018 ("캐리어 짐싸기 순서", Shorts) share the same real-world topic (packing before a trip). They were **not deleted**, because the underlying deliverable genuinely differs (a static 4-slide checklist vs. a 45-second filmed demonstration) -- consumption mode, not just channel label, differs. Instead this pair was formalized as `CLUSTER-CAMPING_TRAVEL_PACK` in `CROSS_CHANNEL_CLUSTERS.json` so the two briefs explicitly share research/sourcing while staying differentiated in format.

## In-channel structural similarity (same channel, related but distinct topics)

| similarity | a | b |
|---|---|---|
| 0.429 | BC-008 브랜드 앰버서더 소개 콘텐츠 | BC-014 브랜드 굿즈 소개 콘텐츠 |
| 0.385 | CM-004 캠핑 초보 텐트 고르는 기준 | CM-016 전기포트 고르는 기준 |
| 0.385 | CM-019 주방 칼 세트 비교 가이드 | CM-020 데스크 매트 비교 가이드 |
| 0.364 | CM-013 러닝화 고르는 기준 | CM-016 전기포트 고르는 기준 |

## Cross-channel overlaps (formalized as clusters -- see CROSS_CHANNEL_CLUSTERS.json)

1 pairs share both a title-similarity signal and a `theme_tag` -- these are the pairs that became cluster members rather than duplicate-removal candidates.

## Template / structural repetition (the real quality issue, distinct from topic duplication)

Topic duplication is not the backlog's actual repetition problem -- shared boilerplate **field text** within a content_type is. This is quantified below (fraction of briefs in that content_type sharing byte-identical text for the given field):

### cardnews

| field | identical_rate | n |
|---|---|---|
| hook 슬라이드 body_intent | 1.0 | 25 |
| mobile_readability_risk | 1.0 | 25 |
| forbidden_claims 목록 | 0.88 | 25 |
| cta 문구 | 1.0 | 25 |

### shorts

| field | identical_rate | n |
|---|---|---|
| narration_intent | 1.0 | 20 |
| subtitle_intent | 1.0 | 20 |
| unsupported_automation_boundary | 1.0 | 20 |
| forbidden_claims 목록 | 0.85 | 20 |

### instagram_feed

| field | identical_rate | n |
|---|---|---|
| forbidden_claims 목록 | 1.0 | 20 |
| cta 문구 | 1.0 | 20 |

### brandconnect

| field | identical_rate | n |
|---|---|---|
| hook (브랜드 미확정으로 전원 동일 placeholder) | 1.0 | 15 |
| forbidden_claims 목록 | 1.0 | 15 |
| sponsorship_disclosure 문구 | 1.0 | 15 |

### commerce_guide

| field | identical_rate | n |
|---|---|---|
| forbidden_claims 목록 | 1.0 | 20 |
| purchase_cta_approval_gate 문구 | 1.0 | 20 |

### knowledge_evergreen

| field | identical_rate | n |
|---|---|---|
| forbidden_claims 목록 | 1.0 | 20 |
| cta 문구 | 1.0 | 20 |

`forbidden_claims` and `cta` boilerplate repetition across most content types is an intentional shared safety contract (the same prohibited-claim list should apply to every brief in a category) and is not a quality defect. `brandconnect.hook` at 100% identical is a deliberate placeholder (`가상 브랜드 사실 생성 금지` -- no real brand exists to write a real hook against) and is resolved by `PRODUCTION_BRIEFS_V1_1.json`'s scaffolding for the top 3 BrandConnect items, not by inventing brand copy. The 18 items in `PRODUCTION_BRIEFS_V1_1.json` have hand-authored, non-templated hook options and slide direction as a concrete demonstration that de-templatization is possible; de-templatizing all 120 briefs at this level of detail was out of scope for this audit pass and is flagged as a follow-on recommendation in `CONTENT_QUALITY_AUDIT_V1_1.md`.