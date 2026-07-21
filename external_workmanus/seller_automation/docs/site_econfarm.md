# 이컨팜(에코앤팜) / 어드민플러스 기반 크롤링 분석

## 사이트 유형
- 플랫폼: **ADMINPLUS (adminplus.co.kr)** — 다수 도매처가 공용으로 사용하는 B2B 발주 솔루션
- 서버 렌더링 + **세션 쿠키 인증** (JWT 아님)
- 도메인: `https://econfarm.adminplus.co.kr`
- => 동일 플랫폼이면 다른 도매처도 같은 크롤러 재사용 가능 (서브도메인만 교체)

## 로그인
- 로그인 페이지: `/partner/login.html`
- 폼: `memid`(아이디), `admpwd`(비밀번호) → POST (login.html 처리)
- 성공 시 `/partner/?mod=product&actpage=prt.list` 로 이동, 세션 쿠키 발급
- requests.Session으로 쿠키 유지 필요

## 상품 목록
- URL: `/partner/?mod=product&actpage=prt.list`
- 전체 상품수 표기, 카테고리(전체/과일/선물세트/김치/채소/견과·건과류/수산물/육류·가공식품)
- 각 상품 항목 onclick: `prtView("{pcode}","{grp}","{delflag}")`
  - 예: `prtView("10004810","2","1")`
  - pcode = 상품코드(10004810 형식)

## 상품 상세 (팝업 HTML)
- grp=="2" && delflag=="1": `/partner/?mod=product&actpage=prt.grp.detail.pop&pcode={pcode}`  (그룹/옵션형)
- 그 외: `/partner/?mod=product&actpage=prt.detail.pop&pcode={pcode}`
- 상세 HTML 내 옵션 테이블: 제품명/재고/공급가/판매가/과세여부/배송비 (class=list_table)
- 상품 이미지 CDN: `https://cdn.yourlove.co.kr/econfarm/img/prtimg/...`

## 수집 전략 (HTML 파싱)
1. login (memid/admpwd) → 세션 쿠키
2. prt.list 페이지 GET → BeautifulSoup으로 `prtView(...)` onclick에서 (pcode,grp,delflag) + 상품명/공급가 추출
3. 각 pcode별 상세 팝업 GET → 옵션 테이블 파싱(제품명/공급가/판매가/배송비), 상세 이미지 추출
4. 카테고리별 필터는 list 페이지 파라미터로 처리

## 비고
- "전체제품 엑셀 다운로드", "상세페이지 & 썸네일 다운로드" 버튼 존재 → 대량 수집 시 활용 가능
