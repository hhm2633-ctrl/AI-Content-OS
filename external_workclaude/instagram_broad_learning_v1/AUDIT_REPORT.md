# AUDIT_REPORT
판정: LEARNING_IMPORT_NO_GO

## 1) RAW 기준 핵심 정합성
- RAW_OBSERVATIONS 개수: 39
- meta.total_observations: 39
- URL 중복: 0
- 1년 필터(2025-07-14 기준) 통과율: 39 / 39, 초과기준 초과: 0
- 최소/최대 post_date: 2025-07-19 / 2026-07-14
- 카테고리 수: 10
- 단일 계정 최대 비중: 2건 (sellwell_labbs, 5.1%)
- 계정 수(요청사항 기대값 35): 관측 기준 37로 확인(기대 35 미달)

## 2) 공개 지표/파싱
- public_likes/public_comments/public_reposts 정수 파싱 실패: 0
- public_views/public_saves/public_reach 비널 건수: 0 (모두 null)
- 팔로워 미확인 계정(유니크 계정 기준): 33 (명시적 공개 계정: 2개)
- 팔로워 기반 engagement-rate 직접 산출 흔적: 없음(용어 및 실제 산식 언급만 존재)

## 3) URL 결속 결함
- `CTA_AND_EVIDENCE_PATTERNS.json`: `https://www.instagram.com/p/DJFV4zTPA2n/` (RAW 미수록)
- `ENGAGEMENT_BENCHMARKS.json`: `https://www.instagram.com/p/DZrRPtkGJN2_유사/`
- `VISUAL_LAYOUT_LIBRARY.json`: `https://www.instagram.com/p/CVcqKC1vceM/`
- `STORY_STRUCTURE_LIBRARY.json`: `https://www.instagram.com/p/C9_QVFFPrKf_유사`
- 위 4건: 총 4건 URL 바인딩 불일치

## 4) DM CTA 11건 비율 재계산
| url | likes | comments | comments/likes |
|---|---:|---:|---:|
| https://www.instagram.com/p/DaCzy3oD-RH/ | 15 | 10 | 0.6667 |
| https://www.instagram.com/p/DYUI6eKk80S/ | 2200 | 3400 | 1.5455 |
| https://www.instagram.com/p/DZnQtl3Eq-_/ | 126 | 511 | 4.0556 |
| https://www.instagram.com/p/DZwFmVzgT-c/ | 140 | 232 | 1.6571 |
| https://www.instagram.com/p/DZ-P1r_k_ox/ | 176 | 280 | 1.5909 |
| https://www.instagram.com/p/DZaM-F2EhBr/ | 271 | 1100 | 4.0590 |
| https://www.instagram.com/p/DY_j-R4kUw1/ | 281 | 1100 | 3.9146 |
| https://www.instagram.com/p/DZsBFesH6EI/ | 177 | 1100 | 6.2147 |
| https://www.instagram.com/p/DaNEjI7ieUa/ | 1400 | 339 | 0.2421 |
| https://www.instagram.com/p/DZupSq1ICoT/ | 151 | 49 | 0.3245 |
| https://www.instagram.com/p/DadGwa9GhH3/ | 34 | 270 | 7.9412 |

- 범위 요약(재계산): 24.21% ~ 794.12%, 미계산/누락 0건

## 5) causality 혼동/benchmark 분리
- 인과성 혼동 문구 자체는 다수 존재하나 대부분 `hypothesis_only` caveat/한정으로 마감됨.
- 단, `LEARNING_CANDIDATES` 등에서 `confidence`가 `benchmark_observed(구조 반복)`로 표기되어 상태 표준값(benchmark_observed/hypothesis_only) 외 케이스가 존재.

## 6) 최종 차단 항목
1. 계정 수 기대값(35)와 관측 산출(37) 불일치
2. URL 결속 실패 4건
3. 상태 표기 통일성 위반 가능성(`benchmark_observed(구조 반복)`)

결론: `LEARNING_IMPORT_NO_GO`
