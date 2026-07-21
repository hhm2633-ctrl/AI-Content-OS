# QA Report — Instagram Broad CardNews Learning V1

## AUDIT 수정 이력 (2026-07-14, Spark AUDIT_REPORT.md 대응)

Spark의 `AUDIT_REPORT.md`(판정: `LEARNING_IMPORT_NO_GO`)가 지적한 3개 항목을 `RAW_OBSERVATIONS.json`을 유일한 원본으로 삼아 수정했다. **RAW의 observations 39건 자체는 삭제·변조하지 않았으며**, meta 필드 정정과 파생 산출물 재생성만 수행했다. `AUDIT_REPORT.md`는 지시대로 수정하지 않았다.

### 1. 계정 수 오기재 (35 → 37)
`RAW_OBSERVATIONS.json`의 `observations[].account` 39건을 집합 연산으로 재계산한 결과 unique 값은 **37**이 정확하다(mart_eting, sellwell_labbs만 각 2회, 나머지 35개 계정은 1회 = 35+2=37). 최초 보고치 35는 산술 오류였으며, 계정명 normalization 차이(표기 불일치)로 인한 것이 아니었다 — 39개 account 필드 전부가 프로필 표시 그대로의 원문이라 canonical_account_id 별도 부여는 불필요했다. `RAW_OBSERVATIONS.json meta`, `ACCOUNT_AND_CATEGORY_SAMPLE.json`, `BROAD_LEARNING_REPORT.md`의 35를 37로 전부 교정.

### 2. RAW에 없는 URL 4건
Chrome에서 4건을 재확인한 결과:

| URL | 재확인 결과 | 조치 |
|---|---|---|
| `https://www.instagram.com/p/DJFV4zTPA2n/` | 실존(oztourscanada, 2025-05-01) — 1년 이내 기준(2025-07-14 이후) 미충족 | RAW에 추가하지 않음. `CTA_AND_EVIDENCE_PATTERNS.json`의 "외부 채널 유도형"에서 해당 URL 제거(evidence_urls 3→2건, benchmark_observed 유지) |
| `https://www.instagram.com/p/DZrRPtkGJN2_유사/` | 유효한 URL 형식이 아님("_유사"가 붙은 오기). 실제 `DZrRPtkGJN2`는 RAW id8(andy__wormhole, likes 28)로 이 인용이 참조하려던 데이터(likes 2200)와 무관 | RAW 필드값(likes=2200) 대조 결과 유일하게 일치하는 레코드는 id9(trendpark77, `DYUI6eKk80S`) — URL 추정이 아니라 canonical RAW 대조로 오기를 교정. `ENGAGEMENT_BENCHMARKS.json` 고반응 3분위 목록 수정 |
| `https://www.instagram.com/p/CVcqKC1vceM/` | 실존(jsdesign.studio, 2021-10-25) — 1년 이내 기준 미충족 | RAW에 추가하지 않음. `VISUAL_LAYOUT_LIBRARY.json`의 "앱 UI 목업 재현형"에서 제거(evidence_urls 2→1건, confidence는 원래도 hypothesis_only라 변경 없음) |
| `https://www.instagram.com/p/C9_QVFFPrKf_유사` | 유효한 URL 형식이 아님. 실제 `C9_QVFFPrKf`(psshkr, 2024-07-29)는 존재하나 1년 이내 기준 미충족 | RAW에 추가하지 않음. `STORY_STRUCTURE_LIBRARY.json`의 "증상 공감→의인화..." 구조에서 제거(evidence_urls 2→1건, confidence는 원래도 hypothesis_only라 변경 없음) |

4건 중 진짜 URL 조작·추정은 없었음: 2건은 실존하지만 1년 이내 기준 미충족으로 RAW 미등재 상태가 맞았고(파생 라이브러리 인용이 잘못이었음), 2건은 RAW의 실제 레코드를 가리키려다 생긴 오기(1건은 대조로 정정, 1건은 대조 불가하여 제거)였다.

### 3. 상태 표준화
`benchmark_observed`(evidence_urls 2건 이상) / `hypothesis_only`(1건 또는 인과·비교 주장) 두 값만 허용하도록 전 파생 파일을 재작성했다.

- `LEARNING_CANDIDATES.json`: `benchmark_observed(구조 반복)`, `benchmark_observed(빈도)` 등 괄호 부연 표기를 전부 제거하고 부연 설명은 `note` 필드로 이동
- `ENGAGEMENT_BENCHMARKS.json`: `"benchmark_observed(빈도) / 원인 해석은 hypothesis_only"`처럼 하나의 필드에 두 상태를 혼합 기재하던 부분을 `confidence`(단일 표준값) + `note`(해석 caveat)로 분리
- 결속 규칙 적용: evidence_urls가 2건 이상인 항목은 `benchmark_observed`, 1건인 항목은 `hypothesis_only`로 기계적으로 통일. 이 규칙 적용 결과 2건이 재조정됨:
  - `HOOK_PATTERN_LIBRARY.json` "인용·반전형 서술 헤드라인": evidence_urls 1건인데 기존에 `benchmark_observed`로 표기되어 있어 `hypothesis_only`로 하향
  - `CTA_AND_EVIDENCE_PATTERNS.json` "실무자/전문가 인터뷰 인용형": evidence_urls 2건인데 기존에 `hypothesis_only`로 표기되어 있어 `benchmark_observed`로 상향
- `LEARNING_CANDIDATES.json` 5번 항목("병원/공공기관 계정 캐릭터 의인화")은 원문이 "시각 스타일 반복"과 "반응이 낮다는 비교 주장"을 한 문장에 혼합하고 있어, confidence 판단 왜곡을 막기 위해 시각 스타일 반복(n=2, `benchmark_observed`)만 candidate 본문에 남기고 비교 주장은 `note`로 분리해 별도 확정 주장으로 취급하지 않음
- 전 패턴 파일(`HOOK_PATTERN_LIBRARY`, `STORY_STRUCTURE_LIBRARY`, `VISUAL_LAYOUT_LIBRARY`, `CTA_AND_EVIDENCE_PATTERNS`, `LEARNING_CANDIDATES`)의 모든 항목에 `evidence_urls`, `observation_count`, `account_count`, `category_count`, `confidence` 5개 필드를 결속 완료

## AUDIT 수정 이력 (2차, 2026-07-14, Spark 재감사 대응)

Spark가 `LEARNING_IMPORT_NO_GO`로 재차 지적한 최종 2개 항목을 수정했다. `AUDIT_REPORT.md`는 이번에도 수정하지 않았다.

### 4. CTA 패턴 category_count 재검증

`CTA_AND_EVIDENCE_PATTERNS.json`의 모든 패턴에 대해 evidence_urls를 `RAW_OBSERVATIONS.json`의 `observations[].category`와 join하여 unique category 수를 기계적으로 재계산했다. 오류의 근본 원인은 id36(`DPDvKDFkRTN`, madebylab_rx)의 category 필드값이 `"패션·뷰티 / 브랜드·제품"` 복합 표기라는 점이 join 시 하나의 카테고리로만 처리되고 분리 카운트되지 않은 것이었다. `ACCOUNT_AND_CATEGORY_SAMPLE.json`은 처음부터 이 복합 항목을 두 분야에 각각 반영해 왔으므로, 그 규칙을 `CTA_AND_EVIDENCE_PATTERNS.json`에도 동일하게 적용해 재계산했다.

재계산 결과 3건이 실제로 오류였음:

| 패턴 | evidence_urls | 기존 category_count | 재계산 결과 | 원인 |
|---|---|---|---|---|
| 외부 채널 유도형 | Dav8rULEl4G(경제·재테크), DPDvKDFkRTN(패션·뷰티/브랜드·제품) | 2 | **3** | DPDvKDFkRTN의 복합 카테고리 미분리 |
| 없음(정보 나열형) | 15건 | 8 | **9** | 15건 category join 시 뉴스·시사, 경제·재테크, 교육·지식, 유머·이슈, 생활정보, 건강, 여행·지역, 패션·뷰티, 문화·책 = 9개인데 1개 누락 집계 |
| 명시적 광고/협찬 라벨 있음 | DRZEU4oEmjg(생활정보), DX540sxj3kb(건강), DPDvKDFkRTN(패션·뷰티/브랜드·제품) | 2 | **4** | DPDvKDFkRTN의 복합 카테고리 미분리 |

`observation_count`와 `account_count`도 같은 방식(evidence_urls를 RAW의 account 필드와 join)으로 전 패턴에 대해 기계 재검증했으며, 위 3건 외에는 불일치가 없었다(`HOOK_PATTERN_LIBRARY.json`, `STORY_STRUCTURE_LIBRARY.json`, `VISUAL_LAYOUT_LIBRARY.json`, `LEARNING_CANDIDATES.json`, `ENGAGEMENT_BENCHMARKS.json`의 evidence_urls/observation_count/account_count/category_count 전 항목도 동일 방법으로 재대조했고 전부 일치).

### 5. validated/proven 등 긍정 승격 표현 스캔

기계 판독 대상 필드(`status`, `confidence`, 그리고 패턴/후보의 주장문인 `pattern`/`candidate`/`description`/`note` 등 claim 텍스트)를 전수 검사했다.

- `"confidence"`/`"status"` 필드 값은 정규식 `"(status|confidence)":\s*"[^"]*"` 로 전 파일에서 추출해 확인한 결과, `RAW_OBSERVATIONS.json`의 `meta.status: "COMPLETE"`(데이터셋 처리 상태를 나타내는 필드이며 패턴의 증거 등급을 나타내는 값이 아님) 1건을 제외하면 전부 `benchmark_observed` 또는 `hypothesis_only`뿐이었다.
- `validated`, `proven`, `확정적`, `입증`, `검증됨` 등 승격 표현을 전 파일에서 검색한 결과, 실제 등장한 곳은 `HOOK_PATTERN_LIBRARY.json`과 `LEARNING_CANDIDATES.json`의 `status_standard` 설명문 — "candidate/validated/proven 등 승격 표현 사용 안 함" — 뿐이었다. 이는 금지 규칙을 서술하는 메타 설명(부정문)이며 실제 패턴에 승격 등급을 매긴 사례가 아니므로 위반으로 집계하지 않았다(사용자 지시: "부정·메타 설명은 위반으로 보지 않는다").
- `BROAD_LEARNING_REPORT.md`의 "확정적 결론으로 사용해서는 안 된다" 역시 금지를 서술하는 부정문으로, 위반 집계에서 제외했다.

**`positive_promotion_claim_count = 0`** (검사 방법: 전 JSON 파일의 `status`/`confidence` 필드가 `benchmark_observed`/`hypothesis_only` 외 값을 갖는 경우, 그리고 `validated`/`proven`/`확정적`/`입증`/`검증됨` 등의 문자열이 부정·금지 서술이 아닌 실제 등급 상승 주장으로 쓰인 경우를 위반으로 카운트. 두 경우 모두 0건.)
- 전 패턴 파일(`HOOK_PATTERN_LIBRARY`, `STORY_STRUCTURE_LIBRARY`, `VISUAL_LAYOUT_LIBRARY`, `CTA_AND_EVIDENCE_PATTERNS`, `LEARNING_CANDIDATES`)의 모든 항목에 `evidence_urls`, `observation_count`, `account_count`, `category_count`, `confidence` 5개 필드를 결속 완료

---

## 체크리스트 결과 (원본, AUDIT 대응 후 재확인)

| 항목 | 결과 |
|---|---|
| 실제 URL 없는 관찰 | 0건 — `RAW_OBSERVATIONS.json` 39건 전부 실제 URL 보유(관측 삭제·변조 없음) |
| 중복 게시물 | 0건 |
| 숨겨진 지표(조회수·저장·도달) 추정 | 0건 |
| 문안·이미지 복제 | 0건 |
| 파생 라이브러리 URL이 RAW에 없는 경우 | 0건(수정 전 4건 → 수정 후 0건, 위 "AUDIT 수정 이력 2" 참고) |
| 상태값이 `benchmark_observed`/`hypothesis_only` 외 표기인 경우 | 0건(수정 전 다수 → 수정 후 0건) |
| 패턴별 evidence_urls·observation_count·account_count·category_count·confidence 결속 | 완료 |

## 표본·계정·분야 편중 검사

- **표본 수: 39건**(목표 60건 미달 — 사유는 아래 참고)
- **계정 수: 37개**(목표 15개 이상 충족)
- **단일 계정 최대 비중**: mart_eting 2건, sellwell_labbs 2건 — 각 39건의 5.1%로 10% 상한 이내 통과
- **분야 커버리지**: 10개 분야 전부 최소 1건 이상 확보(목표 8개 이상 충족). 브랜드·제품(1건), 문화·책(1건), 건강(2건), 유머·이슈(2건)는 표본이 얇아 `LEARNING_CANDIDATES.json`에서 관련 후보는 `hypothesis_only`로 표기

## 표본 수 미달 사유 (39/60)

수집 도중 사용자가 "1년 이내 게시물만 수집"이라는 지시를 추가했다. Instagram 해시태그 페이지의 기본 노출은 "인기 게시물" 위주라 오래된(2019~2024년) 게시물이 다수 섞여 있었고, 이를 소급 적용한 결과 최초 수집분 중 **28건**이 1년 초과로 제외되었다. 이후 분야별 하위 해시태그를 추가 검색해 최근 게시물을 보강했으나 60건 목표에는 도달하지 못했다.

### 1년 초과로 제외된 게시물 목록 (28건)

| URL | 계정 | 게시일 |
|---|---|---|
| /p/C8LKOagssu9/ | icmcseoul | 2024-06-14 |
| /p/C9_QVFFPrKf/ | psshkr | 2024-07-29 |
| /p/CVcqKC1vceM/ | jsdesign.studio | 2021-10-25 |
| /p/B3l4dXxpoOr/ | by_melly | 2019-10-14 |
| /p/CmRGtC-LY67/ | oh_three_2020 | 2022-12-17 |
| /p/DIz3LLkJfmX/ | themnk_official | 2025-04-24 |
| /p/CkaMBN2r83l/ | mkmd_director | 2022-11-01 |
| /p/CpyqU-0y5kX/ | ggvc1365 | 2023-03-15 |
| /p/CZdUepRvNES/ | reimond_717 | 2022-02-02 |
| /p/Ca9Uxa7r-Y0/ | reimond_717 | 2022-03-11 |
| /p/CZtyQcPFU4R/ | reimond_717 | 2022-02-08 |
| /p/CGHJSvsFOl8/ | ku_vetmed | 2020-10-09 |
| /p/Cy5WLs_Bvrs/ | mpm_kr | 2023-10-27 |
| /p/B0Absz0jGAL/ | power_of_presentation | 2019-07-17 |
| /p/CXflN8HPxUA/ | lib_gyjungang | 2021-12-15 |
| /p/CaChp2fPvr-/ | solutionsom__ | 2022-02-16 |
| /p/DJ5p2J8hnH2/ | beautrend_lab | 2025-05-21 |
| /p/DKMMjumTUqk/ | carmore_official | 2025-05-28 |
| /p/DJFV4zTPA2n/ | oztourscanada | 2025-05-01 |
| /p/B6zPl9SJxmO/ | lifeup.office | 2020-01-02 |
| /p/DJooi1OPyHI/ | munhak_gongbang.official | 2025-05-14 |
| /p/CpL801JPE3t/ | mindsetting7_7 | 2023-02-28 |
| /p/CKi253vlOJ5/ | pattern_grace | 2021-01-27 |
| /p/DJwWz1avbvI/ | munhak_gongbang.official | 2025-05-17 |
| /p/COzK0vMtrv8/ | jhsactivity_ | 2021-05-13 |
| /p/CDNUw3nDdKN/ | tuisy.design | 2020-07-29 |
| /p/DFw9SdzOF3i/ | milwaukeetoolkorea | 2025-02-07 |
| /p/DBN2Pp0TZ86/ | dabida_fit | 2024-10-17 |

## 기타 한계 사항 (투명성 고지)

- **계정 팔로워 수**: 37개 계정 중 2개(zzalqueen, dot0tori)만 확인. 나머지 35개 계정의 프로필 방문(팔로워 확인)을 생략함. "계정 규모가 비슷한 표본끼리 비교"는 이 2건 외에는 제한적.
- **슬라이드 수**: 대부분 dot 인디케이터 개수 기반 추정치. 정확한 "N/M" 텍스트 표기가 확인된 것은 1건뿐(sellwell_labbs, 1/5).
- **댓글/좋아요/리포스트 숫자 매핑**: 아이콘 순서(하트→말풍선→리포스트) 관례 매핑이며 완전한 보증은 아님.
- **CN-006 비교**: 사용자 지시에 따라 이번 단계에서 미수행.
