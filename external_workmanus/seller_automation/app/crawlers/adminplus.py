"""
어드민플러스(ADMINPLUS) 기반 도매처 크롤러 (예: 이컨팜)
- 서버 렌더링 + 세션 쿠키 인증
- 로그인: /partner/login.html (memid, admpwd)
- 목록: /partner/?mod=product&actpage=prt.list  (onclick="prtView(pcode,grp,delflag)")
- 상세: prt.grp.detail.pop / prt.detail.pop  (옵션 테이블 파싱)
* 서브도메인만 바꾸면 동일 플랫폼의 다른 도매처도 재사용 가능
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
import re
import time
from bs4 import BeautifulSoup

from .base import BaseCrawler, NormalizedProduct, ProductOption, CrawlerError

PRTVIEW_RE = re.compile(r'prtView\(["\'](\d+)["\']\s*,\s*["\'](\d+)["\']\s*,\s*["\'](\d+)["\']\)')
PRICE_RE = re.compile(r'[\d,]+')


class AdminplusCrawler(BaseCrawler):
    site_key = "adminplus"
    display_name = "어드민플러스"

    def __init__(self, username: str, password: str, base_url: str, timeout: int = 20):
        super().__init__(username, password, timeout)
        self.base_url = base_url.rstrip("/")
        # HTML 응답 받으므로 Accept 조정
        self.session.headers["Accept"] = "text/html,application/xhtml+xml,*/*"

    def login(self) -> None:
        # 로그인 페이지 먼저 방문 (세션 쿠키 발급 + 리퍼러 확보)
        self.session.get(
            f"{self.base_url}/partner/login.html?rtnurl=%2Fpartner%2F",
            timeout=self.timeout,
        )
        # 실제 로그인 처리 엔드포인트: login.chk.php
        #  폼 id=signup을 jQuery serialize 후 POST. 아이디 input은 id=memid이지만
        #  실제 name 속성은 'admid' (주의!). 성공 시 응답 본문은 'ok'.
        try:
            resp = self.session.post(
                f"{self.base_url}/partner/login.chk.php",
                data={"rejoin": "", "admid": self.username,
                      "admpwd": self.password, "saveid": "1"},
                headers={"Referer": f"{self.base_url}/partner/login.html",
                         "X-Requested-With": "XMLHttpRequest"},
                timeout=self.timeout,
                allow_redirects=True,
            )
            if resp.text.strip() != "ok":
                raise CrawlerError(
                    f"로그인 거부: {resp.text.strip()[:50]}")
        except CrawlerError:
            raise
        except Exception as e:
            raise CrawlerError(f"로그인 요청 실패: {e}")
        # 로그인 성공 여부: 상품 목록 접근으로 검증
        chk = self.session.get(
            f"{self.base_url}/partner/?mod=product&actpage=prt.list",
            timeout=self.timeout,
        )
        if "prtView(" in chk.text or "전체상품수" in chk.text or "로그아웃" in chk.text:
            return
        raise CrawlerError("어드민플러스 로그인 실패 (계정/엔드포인트 확인 필요)")

    def fetch_product_list(self, max_items: Optional[int] = None) -> List[Dict[str, Any]]:
        """상품 목록은 prt.list.proc (XML) 엔드포인트에서 페이지네이션으로 수집.
        응답 XML: <result><total_cnt>..</total_cnt><data>(상품 HTML 조각)</data>...
        각 data 조각 안에 onclick="prtView(pcode, grp, delflag)" 가 존재."""
        summaries: List[Dict[str, Any]] = []
        seen = set()
        page = 1
        while True:
            r = self.session.get(
                f"{self.base_url}/partner/?mod=product/json&actpage=prt.list.proc",
                params={"page": str(page), "order": "", "by": "",
                        "searchval": "", "prt_cate_1": "", "prt_cate_2": "",
                        "prt_cate_3": "", "prt_cate_4": ""},
                headers={"X-Requested-With": "XMLHttpRequest",
                         "Referer": f"{self.base_url}/partner/?mod=product&actpage=prt.list"},
                timeout=self.timeout,
            )
            if r.status_code != 200:
                raise CrawlerError(f"목록 조회 실패: HTTP {r.status_code}")
            # XML 파싱: <data> 안에 상품 HTML 조각이 들어있음 (CDATA/이스케이프)
            xml = BeautifulSoup(r.text, "xml")
            data_nodes = xml.find_all("data")
            if not data_nodes:
                break
            page_added = 0
            for node in data_nodes:
                frag_html = node.get_text()  # 상품 HTML 조각
                frag = BeautifulSoup(frag_html, "html.parser")
                for el in frag.find_all(attrs={"onclick": PRTVIEW_RE}):
                    m = PRTVIEW_RE.search(el.get("onclick"))
                    if not m:
                        continue
                    pcode, grp, delflag = m.group(1), m.group(2), m.group(3)
                    if pcode in seen:
                        continue
                    seen.add(pcode)
                    title = frag.get_text(" ", strip=True)[:80]
                    summaries.append({"id": pcode, "grp": grp,
                                      "delflag": delflag, "title": title})
                    page_added += 1
                    if max_items and len(summaries) >= max_items:
                        return summaries
            if page_added == 0:
                break
            page += 1
            time.sleep(0.2)
        return summaries

    def fetch_detail(self, summary: Dict[str, Any]) -> NormalizedProduct:
        pcode = summary["id"]
        grp = summary.get("grp", "0")
        delflag = summary.get("delflag", "0")
        if grp == "2" and delflag == "1":
            actpage = "prt.grp.detail.pop"
        else:
            actpage = "prt.detail.pop"
        url = f"{self.base_url}/partner/?mod=product&actpage={actpage}&pcode={pcode}"
        r = self.session.get(url, timeout=self.timeout)
        soup = BeautifulSoup(r.text, "html.parser")

        # 순수 상품명/원산지/상세설명은 write_table의 행에서 추출
        title = ""
        origin = ""
        detail_desc = ""
        wt = soup.find("table", class_="write_table")
        if wt:
            for tr in wt.find_all("tr"):
                cells = tr.find_all(["th", "td"])
                if len(cells) < 2:
                    continue
                label = cells[0].get_text(" ", strip=True)
                value = cells[1].get_text(" ", strip=True)
                if label == "제품명" and not title:
                    title = value
                elif label == "제품설명":
                    detail_desc = value
                    om = re.search(r"원산지\s*[:：]\s*([\w가-힣]+)", value)
                    if om:
                        origin = om.group(1)
        if not title:
            title = summary.get("title", "")
        options: List[ProductOption] = []
        # 옵션 테이블: 제품명/재고/공급가/판매가/과세여부/배송비
        for table in soup.find_all("table", class_="list_table"):
            rows = table.find_all("tr")
            for tr in rows:
                tds = tr.find_all("td")
                if len(tds) >= 3:
                    name = tds[0].get_text(" ", strip=True)
                    price_text = tds[2].get_text(strip=True)
                    pm = PRICE_RE.search(price_text)
                    price = int(pm.group(0).replace(",", "")) if pm else 0
                    if name and price:
                        options.append(ProductOption(name=name, price=price))
                        if not title:
                            title = name
        # 상세 이미지
        images = []
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src and "cdn" in src and "noimage" not in src:
                images.append(src)

        prices = [o.price for o in options if o.price]
        return NormalizedProduct(
            source_site=self.site_key,
            source_product_id=str(pcode),
            title=title or f"상품 {pcode}",
            min_price=min(prices) if prices else 0,
            max_price=max(prices) if prices else 0,
            thumbnail_url=images[0] if images else "",
            options=options,
            images=images,
            origin=origin,
            detail_html=detail_desc or str(soup.find(id="addproductInfo") or ""),
            raw={"summary": summary, "detail_desc": detail_desc},
        )


class EconfarmCrawler(AdminplusCrawler):
    site_key = "econfarm"
    display_name = "이컨팜(에코앤팜)"

    def __init__(self, username: str, password: str, timeout: int = 20):
        super().__init__(username, password,
                         base_url="https://econfarm.adminplus.co.kr", timeout=timeout)
