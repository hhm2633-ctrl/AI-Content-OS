"""
백그라운드 작업 관리자.
- 수집(collect)과 등록(list_to_naver) 작업을 별도 스레드로 실행
- 진행상황을 메모리에 보관하여 /api/jobs/{id} 로 폴링 가능
- SQLite는 스레드별로 별도 세션을 열어 사용
"""
from __future__ import annotations
import threading
import traceback
import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from .database import SessionLocal
from . import services, collector
from .models import Product, Listing
from .processing import (
    PricingConfig, NamingConfig, calc_sale_price, process_name,
)
from .markets.naver_client import NaverClient
from .markets.naver_payload import NaverProductInput

# 작업 상태 저장소 (메모리)
JOBS: Dict[str, Dict[str, Any]] = {}
_LOCK = threading.Lock()


def _new_job(kind: str) -> str:
    job_id = uuid.uuid4().hex[:12]
    with _LOCK:
        JOBS[job_id] = {
            "id": job_id, "kind": kind, "status": "running",
            "progress": 0, "total": 0, "done": 0,
            "message": "시작 중...", "logs": [], "result": None,
            "started_at": datetime.now().strftime("%H:%M:%S"),
        }
    return job_id


def _log(job_id: str, text: str):
    with _LOCK:
        j = JOBS.get(job_id)
        if j:
            j["logs"].append(text)
            j["logs"] = j["logs"][-200:]
            j["message"] = text


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        j = JOBS.get(job_id)
        return dict(j) if j else None


# ---------------- 수집 작업 ----------------
def start_collect(sites: List[str], max_items: Optional[int]) -> str:
    job_id = _new_job("collect")

    def run():
        db = SessionLocal()
        try:
            totals = {"new": 0, "updated": 0, "failed": 0, "listed": 0}
            with _LOCK:
                JOBS[job_id]["total"] = len(sites)
            for idx, site in enumerate(sites, 1):
                login = services.get_site_login(db, site)
                _log(job_id, f"[{services.SITE_LABELS.get(site, site)}] 수집 시작...")

                def progress(s, i, n, title):
                    with _LOCK:
                        JOBS[job_id]["message"] = f"[{services.SITE_LABELS.get(s, s)}] {i}/{n} {title[:30]}"

                try:
                    stats = collector.collect_site(
                        db, site,
                        username=login["username"], password=login["password"],
                        max_items=max_items, progress=progress,
                    )
                    for k in ("new", "updated", "failed", "listed"):
                        totals[k] += stats.get(k, 0)
                    _log(job_id, f"[{services.SITE_LABELS.get(site, site)}] 완료: "
                                 f"신규 {stats['new']} / 갱신 {stats['updated']} / 실패 {stats['failed']}")
                except Exception as e:
                    _log(job_id, f"[{services.SITE_LABELS.get(site, site)}] 오류: {e}")
                with _LOCK:
                    JOBS[job_id]["done"] = idx
                    JOBS[job_id]["progress"] = int(idx / max(1, len(sites)) * 100)
            with _LOCK:
                JOBS[job_id]["status"] = "done"
                JOBS[job_id]["result"] = totals
                JOBS[job_id]["message"] = (
                    f"수집 완료 · 신규 {totals['new']} / 갱신 {totals['updated']} / 실패 {totals['failed']}")
        except Exception as e:
            with _LOCK:
                JOBS[job_id]["status"] = "error"
                JOBS[job_id]["message"] = f"오류: {e}"
            _log(job_id, traceback.format_exc()[-500:])
        finally:
            db.close()

    threading.Thread(target=run, daemon=True).start()
    return job_id


# ---------------- 네이버 등록 작업 ----------------
def _build_naver_input(p: Product, profile, leaf_category_id: str,
                       rep_image_url: str) -> NaverProductInput:
    pricing = PricingConfig(
        margin_rate=profile.margin_rate / 100.0,
        payment_fee_rate=profile.payment_fee_rate / 100.0,
        round_unit=profile.round_unit,
        min_price=profile.min_price,
    )
    naming = NamingConfig(
        prefix=profile.prefix, suffix=profile.suffix,
        banned_words=[w.strip() for w in (profile.banned_words or "").split(",") if w.strip()],
    )
    sale_price = calc_sale_price(p.min_price or p.price, pricing)
    name = process_name(p.title, naming)

    # 옵션 변환 (조합형)
    option_combinations = []
    try:
        opts = json.loads(p.options_json) if p.options_json else []
        for o in opts[:50]:
            oname = o.get("name") or o.get("title") or "옵션"
            oprice = int(o.get("price", 0) or 0)
            add = calc_sale_price(oprice, pricing) - sale_price if oprice else 0
            option_combinations.append({
                "optionName1": str(oname)[:25],
                "stockQuantity": profile.default_stock,
                "price": int(add),
                "usable": True,
            })
    except Exception:
        pass

    return NaverProductInput(
        name=name,
        leaf_category_id=leaf_category_id,
        sale_price=sale_price,
        stock_quantity=profile.default_stock,
        representative_image_url=rep_image_url,
        detail_content_html=p.detail_html or f"<div>{name}</div>",
        origin=p.origin,
        seller_product_code=f"{p.source_site}-{p.source_product_id}",
        option_combinations=option_combinations,
    )


def start_naver_listing(product_ids: List[int], leaf_category_id: str,
                        dry_run: bool = True) -> str:
    job_id = _new_job("naver_listing")

    def run():
        db = SessionLocal()
        try:
            keys = services.get_market_keys(db, "naver")
            if not keys["client_id"] or not keys["client_secret"]:
                with _LOCK:
                    JOBS[job_id]["status"] = "error"
                    JOBS[job_id]["message"] = "네이버 API 키가 등록되지 않았습니다. 설정에서 먼저 등록하세요."
                return

            client = NaverClient(keys["client_id"], keys["client_secret"], dry_run=dry_run)
            profile = services.get_default_profile(db)
            products = db.query(Product).filter(Product.id.in_(product_ids)).all()

            with _LOCK:
                JOBS[job_id]["total"] = len(products)
            ok, fail = 0, 0
            for idx, p in enumerate(products, 1):
                try:
                    rep_url = client.upload_image(p.thumbnail_url) if p.thumbnail_url else ""
                    ni = _build_naver_input(p, profile, leaf_category_id, rep_url)
                    res = client.create_product(ni)

                    if dry_run:
                        status = "dryrun"
                        msg = "dry-run payload 생성 완료"
                    else:
                        sc = res.get("status_code")
                        if sc and 200 <= sc < 300:
                            status, msg = "success", f"등록 성공: {res.get('body')}"
                            ok += 1
                        else:
                            status, msg = "failed", f"HTTP {sc}: {str(res.get('body'))[:300]}"
                            fail += 1
                    db.add(Listing(
                        product_id=p.id, market="naver",
                        sale_price=ni.sale_price, status=status, message=msg,
                        payload_json=json.dumps(res, ensure_ascii=False)[:50000],
                    ))
                    if status != "failed":
                        p.status = "listed" if not dry_run else p.status
                    db.commit()
                    _log(job_id, f"[{idx}/{len(products)}] {ni.name[:25]} · {ni.sale_price:,}원 · {status}")
                except Exception as e:
                    fail += 1
                    _log(job_id, f"[{idx}] 오류: {e}")
                with _LOCK:
                    JOBS[job_id]["done"] = idx
                    JOBS[job_id]["progress"] = int(idx / max(1, len(products)) * 100)
            with _LOCK:
                JOBS[job_id]["status"] = "done"
                JOBS[job_id]["result"] = {"ok": ok, "fail": fail, "dry_run": dry_run}
                JOBS[job_id]["message"] = (
                    "dry-run 완료 (실제 전송 안 함)" if dry_run
                    else f"등록 완료 · 성공 {ok} / 실패 {fail}")
        except Exception as e:
            with _LOCK:
                JOBS[job_id]["status"] = "error"
                JOBS[job_id]["message"] = f"오류: {e}"
            _log(job_id, traceback.format_exc()[-500:])
        finally:
            db.close()

    threading.Thread(target=run, daemon=True).start()
    return job_id
