# AI-Content-OS 로컬 도구체인 CTO 인계서

- 기준일: 2026-07-22 (Asia/Seoul)
- 범위: CardNews 다계정 수집·선정·제작 보조 도구
- 판정 기준: `설치`, `저장소 어댑터`, `제작 전처리 호출`, `실제 로컬 smoke`를 서로 다른 상태로 구분
- 금지 상태: 실제 SNS 게시, 외부 API write, 자동화 재개, Git 작업은 수행하지 않음

## 1. CTO 결론

현재 가장 실효성이 높은 묶음은 `Sentence Transformers + OpenCLIP + PaddleOCR + rembg + Real-ESRGAN`이다. 주제 중복 제거와 이미지 선택, 한글 스크린샷 판독, 제품·뷰티 이미지 분리, 저해상도 파생 이미지 보정을 모두 로컬에서 수행할 수 있다. `PySceneDetect`는 영상 입력이 생길 때 즉시 쓸 수 있다.

`Satori + resvg + Fabric.js + Motion Canvas`는 설치와 어댑터 검증까지 끝났지만 기존 CardNews 렌더 경로를 대체하지 않았다. 새 렌더러를 한꺼번에 운영 기본값으로 바꾸면 레이아웃 회귀 위험이 있으므로, 계정별 템플릿 1종을 병렬 실험한 뒤 승격해야 한다.

`SeaweedFS`, `Intel XPU`, `Mixpost/TryPost`, `Qwen Image/FLUX`는 지금 운영 투입 대상이 아니다. 특히 Qwen Image/FLUX 모델 가중치는 이 노트북의 8GB GPU·15.5GB RAM 대비 부담이 커 설치하지 않았다.

## 2. 현재 장비·저장 위치

- 장비: Core Ultra 5 225H, RAM 15.5GB, Intel Arc 130T 8GB
- 대용량 런타임·모델 기본 위치: `F:\AI-Content-OS-Data\external_tools`
- 일부 기존 도구 위치: `F:\AI-Content-OS-Data\tools`
- 저장소 연결 위치: `modules/tool_adapters`, `modules/media_intelligence`, `scripts`, `config/external_tools`

## 3. 설치·연결·문제 현황

| 항목 | 라이선스 | 설치 상태 | 현재 연결/검증 | 문제·보류 사유 | 프로젝트 효과 | CTO 판정 |
|---|---|---|---|---|---|---|
| Sentence Transformers 5.6.0 + multilingual MiniLM | Apache-2.0 | F: 런타임·약 476MB 모델 설치 | 로컬 한글 임베딩 성공, 384차원; 유사 문장 0.9461/무관 문장 0.1879 실측 | 다계정 실운영 중복제거·클러스터링 호출은 추가 연결 필요 | 같은 사건의 제목 변형을 묶고 계정 간 중복 주제를 줄임 | **우선 적용** |
| OpenCLIP 3.3.0 + RN50-quickgelu | 코드·가중치 MIT, pinned revision | F: 런타임·모델 설치 | `score_image_topics()` 및 오프라인 이미지-주제 점수 smoke 성공 | 점수는 내부 관련성 proxy일 뿐 사실·출처·권리 증거가 아님 | 후보 이미지 중 제목·주제에 가까운 컷을 자동 우선순위화 | **우선 적용** |
| PaddleOCR 3.7.0 + PaddlePaddle CPU 3.2.0 | Apache-2.0 | F: 런타임·한글 det/rec 모델 설치 | `extract_korean_text()`로 `한글 OCR 테스트 2026` 정확 추출, confidence 0.9607 | 사용하지 않는 server det 모델 약 88MB가 남아 있음; 실물 스크린샷 품질 benchmark 필요 | 뉴스·댓글·패션 이미지의 한글 텍스트 추출, 글자 과밀·가독성 검사 | **우선 적용** |
| rembg 2.0.76 + u2netp | 코드 MIT, U-2-Net 근거 Apache-2.0 | F: CPU 런타임·모델 설치 | 96×96 RGB→RGBA 배경제거 smoke 성공 | 실제 상품·헤어 사진 품질 미검증; 원본 근거 이미지 배경제거는 정책상 차단 | Account C 제품·뷰티 컷을 카드 레이아웃용 투명 PNG로 만듦 | **보조 적용** |
| Real-ESRGAN ncnn Vulkan | BSD-3-Clause | F: v0.2.5.0 런타임 설치 | Intel Arc Vulkan에서 96×96→192×192 업스케일 성공 | 오래된 upstream 배포물에 publisher digest가 없어 로컬 SHA256만 고정; 원본 증거 대체 금지 | 작은 상품·에디토리얼 컷의 카드용 파생 이미지 선명도 개선 | **보조 적용** |
| PySceneDetect 0.7 + FFmpeg | BSD-3-Clause | F: 런타임 설치 | 2초 합성 영상에서 0–1초/1–2초 장면 정확 분리 | 정적 CardNews만 만들 때 직접 효용이 작음 | 캠페인·런웨이·여행 영상에서 대표 장면 후보를 빠르게 추출 | **영상 입력 시 적용** |
| Satori 0.28.0 | MPL-2.0 | `tools/cardnews-renderer` 설치 | 패키지·버전 probe와 어댑터 테스트 통과 | 기존 Pillow 운영 렌더에 미연결; 수정한 MPL 파일 배포 시 파일 단위 의무 검토 | HTML/CSS식 타이포·레이아웃으로 트렌디한 카드 시안 제작 | **템플릿 1종 실험** |
| resvg-js 2.6.2 | MPL-2.0 | 같은 Node 도구 폴더에 설치 | 패키지·버전 probe와 어댑터 테스트 통과 | Satori 결과의 운영 PNG 렌더 경로 미연결 | SVG를 선명한 고정 크기 PNG로 변환 | **Satori와 묶어 실험** |
| Fabric.js 7.4.0 | MIT | 같은 Node 도구 폴더에 설치 | 패키지·버전 probe와 어댑터 테스트 통과 | 자동 템플릿 엔진에 아직 미연결 | 이미지 크롭·마스킹·스티커·레이어 정밀 편집 | **선택 편집층** |
| Motion Canvas 3.17.2 | MIT | 같은 Node 도구 폴더에 설치 | core/2d 패키지·버전 probe와 어댑터 테스트 통과 | 영상 export·CardNews 운영 호출 없음 | 캐러셀을 Reels/모션 프리뷰로 재사용할 기반 | **정적 품질 안정 후** |
| Playwright 1.61.0 | Apache-2.0 | F: Chromium 브라우저 설치 | 브라우저 실행 파일 탐색과 정적 readiness 테스트 통과 | 이번 최종 검증은 실제 사이트 로그인·탐색을 하지 않음 | 네이버·Instagram 공개 페이지의 반복 캡처·입력 보조 기반 | **수집 어댑터부터 제한 연결** |
| SeleniumBase 4.51.2 | MIT | F: 런타임·pinned ChromeDriver 설치 | 정적 readiness와 페이지 어댑터 테스트 통과 | Playwright와 기능 중복; 실제 사이트 smoke 미실행 | Playwright 실패 사이트용 fallback 및 브라우저 진단 | **fallback 전용** |
| Local media pipeline | 저장소 자체 코드 | 저장소 연결 완료 | OCR, 이미지-주제 점수, 장면 분리, 업스케일, 배경제거를 명시적 요청으로 호출 가능; 현재 단위·통합 테스트 통과 | 기본값 `validate_only`; 기존 CardNews production controller의 자동 호출로 승격하지 않음 | 도구별 호출을 하나의 fail-closed receipt로 묶어 원본 훼손·무단 실행 방지 | **현재 안전 진입점** |
| SeaweedFS 4.39 | upstream Apache-2.0 | F: `weed.exe` 존재 | 실행 파일 readiness만 확인 | 로컬 인접 LICENSE 증빙 없음; 서비스·볼륨·백업 운영 미설정 | 대량 원본·파생 이미지 저장을 단일 로컬 object/file 계층으로 통합 | **규모 증가 전 보류** |
| Intel XPU 런타임 | 구성요소별 라이선스 | F: 격리 환경 약 5GB 설치 | Arc 130T FP32/FP16/BF16 행렬연산 및 Qwen/FLUX pipeline import 성공 | 모델 load·생성은 미검증; 설치 자체가 이미지 생성 능력을 뜻하지 않음 | Intel GPU 호환성 확인과 향후 경량 모델 실행 기반 | **probe 전용** |
| Qwen Image / FLUX pipeline 코드 | 대상 후보 Apache-2.0 | import 코드만 존재, 가중치 없음 | pipeline class import만 성공 | Qwen 약 57.7GB, FLUX.2-klein-4B 약 23.7GB; 8GB VRAM/15.5GB RAM에서 실용성 낮음 | 설치해도 현 장비에서는 제작시간 단축보다 swap·실패 위험이 큼 | **가중치 설치 제외** |
| Mixpost 참고 소스 | MIT | F: 소스 존재 | 게시 reference adapter 테스트 통과 | 버전 provenance 미고정, 서버·DB·worker 미설치 | 게시 큐·계정 연결·상태 추적 구조를 설계할 때 참고 | **참고 전용** |
| TryPost 참고 소스 | AGPL-3.0-only | F: 소스 존재 | 게시 reference adapter 테스트 통과 | 버전 provenance 미고정; AGPL 네트워크 제공 의무 검토 필요; 실행 금지 | 다계정 게시 흐름과 실패 처리 아이디어 참고 | **코드 복사 금지, 참고 전용** |

## 4. 실제 저장소 연결점

- 통합 진입점: `modules/media_intelligence/local_media_pipeline.py`
- 이미지 파생 작업 정책: `modules/media_intelligence/image_operations.py`
- 수동 실행 CLI: `scripts/prepare_cardnews_local_media.py`
- 안전 설정: `config/external_tools/local_media_pipeline.json`
- 개별 런타임: `modules/tool_adapters/*_runtime.py`
- 렌더러 런타임: `modules/tool_adapters/cardnews_renderer_runtime.py`

통합 파이프라인은 다음 경계를 강제한다.

1. 작업명 없는 자동 실행을 거부한다.
2. 원본 파일 덮어쓰기와 F: 출력 루트 밖 기록을 거부한다.
3. rembg·Real-ESRGAN 결과는 파생/보조 자산으로만 기록한다.
4. OpenCLIP 점수를 사실 근거나 권리 증거로 승격하지 않는다.
5. 렌더·게시·업로드·백그라운드 서비스는 기본 설정에서 비활성화한다.

## 5. 오늘 테스트 CardNews에 적용하는 예

### Account A — 뉴스·시사

- Sentence Transformers가 `호우 피해`, `주택 침수`, `대피`처럼 같은 사건을 다른 문장으로 쓴 후보를 묶어 중복 선정을 줄인다.
- PaddleOCR가 기사 캡처의 한글 제목·수치·자막을 추출해 카드 문안 대조와 글자 과밀 검사를 돕는다.
- OpenCLIP은 산사태·호우 같은 주제와 실제 이미지 후보의 시각적 관련성을 보조 점수로 정렬한다. 출처·사실 검증은 별도다.
- Real-ESRGAN은 사용 허가된 저해상도 파생 컷만 보정하며 원본 근거를 대체하지 않는다.

### Account B — 커뮤니티·관계형 이야기

- Sentence Transformers가 `같은 곡이 또 나왔다`, `신혼인데 전우 같다` 같은 서로 다른 서사와 유사 재탕 소재를 구분한다.
- PaddleOCR은 커뮤니티 캡처의 본문과 댓글을 추출해 근거 문장·익명화 대상·카드 글자량을 점검한다.
- Satori/Fabric.js 실험 템플릿은 대화형 말풍선, 리듬감 있는 제목 배치, 정밀 마스킹을 구현하는 데 적합하다.

### Account C — 패션·뷰티

- OpenCLIP이 `하트 레이어스 커트`, `여행 룩`, `레페토 X 버켄스탁`과 이미지 후보의 주제 적합도를 정렬한다.
- rembg는 출처 근거가 아닌 사용 허가된 제품 컷을 분리해 잡지형 레이아웃에 배치한다.
- Real-ESRGAN은 작은 제품·룩북 파생 컷을 카드 크기에 맞춰 보정한다.
- PySceneDetect는 런웨이·캠페인 영상에서 룩 변화 구간을 나눠 대표 프레임 후보를 만든다.

## 6. 검증 결과와 해석

- 2026-07-22 현재 관련 어댑터·통합 파이프라인 단위 테스트: **107개 통과** (`1.687s`)
- F:의 MiniLM, SeaweedFS 실행 파일, Intel XPU 환경, Real-ESRGAN, rembg, PaddleOCR, OpenCLIP, PySceneDetect, publishing reference 소스 경로 존재를 재확인함
- 위 107개 통과는 계약·경로·fail-closed 동작 검증이다. 모든 외부 도구의 실제 품질과 사이트 자동화를 다시 실행했다는 뜻은 아니다.
- 실제 로컬 smoke 성공 기록은 MiniLM 임베딩, Intel XPU 행렬연산, Real-ESRGAN 업스케일, rembg 배경제거, PaddleOCR 한글 추출, OpenCLIP 주제 점수, PySceneDetect 장면 분리에 한정한다.
- 전체 `py -m src.main` 및 `workflow_completed`는 이 문서 작성 작업에서 재실행하지 않았다.

## 7. 남은 문제와 CTO 실행 순서

1. **Local media를 CardNews 1개 패키지에 수동 연결**: 오늘 생성물 하나를 골라 OCR→OpenCLIP→필요 시 rembg/업스케일 receipt를 만들고 원본 불변·F: 출력·시각 품질을 확인한다.
2. **현 렌더러와 Satori 실험 A/B**: 기존 Pillow 결과를 보존하고 Account B 또는 C 템플릿 1종만 Satori+resvg로 병렬 렌더한다. Fabric.js는 필요한 마스킹에만 사용한다.
3. **자동 승격 전 시간 계측**: 수집, 선정, 이미지 준비, 렌더 구간을 각각 재서 30분 지연의 실제 병목을 확정한다. 설치 수만으로 시간 절감을 약속하지 않는다.
4. **Playwright 제한 smoke**: 로그인·게시 없이 공개 페이지 1개 캡처와 종료만 검증한다. SeleniumBase는 Playwright 실패가 확인될 때만 사용한다.
5. **라이선스 정리**: SeaweedFS 공식 LICENSE/NOTICE와 설치 출처·SHA256을 로컬 provenance에 고정한다. Mixpost/TryPost는 tag/commit이 고정될 때까지 참고 전용을 유지한다.
6. **보류 유지**: Qwen/FLUX 가중치, SeaweedFS 서비스, Mixpost/TryPost 서버, Motion Canvas 영상 export는 현재 CardNews 병목이 입증하기 전 설치·운영하지 않는다.

## 8. 완료 판정

- 설치 완료: Satori, resvg, Fabric.js, Motion Canvas, Playwright, SeleniumBase, Sentence Transformers+MiniLM, SeaweedFS 실행 파일, Intel XPU probe 환경, Real-ESRGAN, rembg, PaddleOCR, OpenCLIP, PySceneDetect, Mixpost/TryPost 참고 소스
- 저장소 어댑터 완료: 위 항목 전체
- 안전 통합 완료: Real-ESRGAN, rembg, PaddleOCR, OpenCLIP, PySceneDetect를 `LocalMediaPipeline`과 CLI에서 명시적으로 호출 가능
- 부분 연결: Sentence Transformers, Satori/resvg/Fabric/Motion, Playwright/SeleniumBase
- 참고 전용/운영 금지: Mixpost, TryPost
- 보류: SeaweedFS 서비스화, Motion Canvas 영상 export, Qwen Image/FLUX 모델 가중치와 실제 생성
- 전체 CardNews 운영 자동화 완료 여부: **아님**. 운영 production controller 자동 호출, 실제 품질 A/B, 실행시간 benchmark가 남아 있음
## 9. 2026-07-22 CTO continuation verification

- Local media technical fixture completed real PaddleOCR and OpenCLIP execution with the source SHA256 unchanged.
- Sentence Transformers is already connected through the same-event clusterer after deterministic eligibility gates; a real Korean runtime smoke completed.
- The production controller CLI direct-entry import failure was fixed.
- A Windows default-code-page mismatch corrupted Korean JSON sent to Node and caused `controller_state_hash_invalid`; the renderer subprocess is now explicitly UTF-8.
- One Satori/resvg representative technical render completed at `F:\AI-Content-OS-Data\card_news\renderer_ab\satori-ab-20260722-121758`. It is not publish-approved, remains pending independent visual QA, and does not replace Pillow.
- Intel XPU recheck passed: FP32/FP16/BF16 execution and Qwen/FLUX pipeline class imports succeeded. Model weights, model load, and generation were not attempted.
- SeaweedFS remains executable-only with no adjacent license file. Mixpost and TryPost remain source-version-unpinned and reference-only.
- Final focused QA passed 25 tests; compile passed; the full workflow promoted output set `6023ee0d327a439eacea6cce17072f03` and ended with `workflow_completed`.
## 10. Approved provenance and browser verification

- SeaweedFS `4.39` reported commit `db42bb49757b459551607939807017d7a9d5a94a`. The official `windows_amd64.zip` SHA256 `55d0fcddcea510f6e02575211931f76a20e2adf8d933c336bc679d26b8cf158a` matched the download, and the extracted and installed `weed.exe` SHA256 both matched `751975fa1c5f26cc7ba529fbfc1b7e7b471caabdb80225e1747a6b199ed1bd18`.
- The official SeaweedFS Apache-2.0 `LICENSE` and a local install provenance manifest were stored next to the F: executable. No SeaweedFS service or volume was started.
- Mixpost source was pinned to commit `df57648b866310446703f5294350552b62735df5`; all official archive files matched except the locally changed `package-lock.json`.
- TryPost source was pinned to commit `5f0346951dfc03ed46e958ed820146b8e1dc76ef`; source code matched with disclosed exceptions for two missing README files and locally changed Composer/NPM lockfiles.
- The repository adapter now accepts a source commit only when the provenance schema, source slug, 40-character commit, archive SHA256, tracked-file verification, exception list, and reference-only boundary all validate.
- Playwright GET/HEAD-only smoke loaded `https://www.naver.com/` and `https://www.instagram.com/` with HTTP 200. No login, click, form submission, posting, or data write was attempted; an Instagram background POST was blocked.
