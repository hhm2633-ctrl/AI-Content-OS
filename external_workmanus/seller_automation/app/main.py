"""
셀러 자동화 시스템 - 메인 FastAPI 애플리케이션

기능:
- 승인 기기 인증 + 로그인 (security)
- 대시보드(통계/기기관리/비번변경)
- 상품 목록(/products) : 수집된 상품 조회·선택·네이버 등록
- 설정(/settings)      : 도매 계정 / 마켓 API 키 / 가공 설정 저장
- 작업 API(/api/*)     : 수집·등록 실행 + 진행률 폴링

실행: (프로젝트 루트에서)
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
또는 동봉된 run_server 스크립트 사용.
"""
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Request, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from . import config, security, services, jobs
from .database import init_db, get_db, verify_admin_password, set_admin_password
from .models import Device, Product, Listing

BASE = Path(__file__).resolve().parent
app = FastAPI(title="나만의 셀러 자동화 시스템")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE / "templates"))


@app.on_event("startup")
def _startup():
    init_db()


def _guard(request: Request, db: Session) -> Optional[RedirectResponse]:
    """로그인 가드. 통과하면 None, 아니면 리다이렉트 응답 반환."""
    if not security.is_logged_in(request, db):
        return RedirectResponse("/login", status_code=302)
    return None


def _guard_api(request: Request, db: Session) -> bool:
    return security.is_logged_in(request, db)


# ---------- 진입점: 기기 식별 후 라우팅 ----------
@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    resp = RedirectResponse("/login")
    device = security.get_or_create_device(request, resp, db)
    if not security.is_device_approved(device):
        return RedirectResponse("/pending", status_code=302)
    if security.is_logged_in(request, db):
        return RedirectResponse("/dashboard", status_code=302)
    return resp


# ---------- 미승인 기기 대기 화면 ----------
@app.get("/pending", response_class=HTMLResponse)
def pending(request: Request, db: Session = Depends(get_db)):
    resp_holder = HTMLResponse("")
    device = security.get_or_create_device(request, resp_holder, db)
    html = templates.TemplateResponse(request, "pending.html", {"device": device})
    for k, v in resp_holder.raw_headers:
        if k.decode().lower() == "set-cookie":
            html.raw_headers.append((k, v))
    return html


# ---------- 로그인 ----------
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    resp_holder = HTMLResponse("")
    device = security.get_or_create_device(request, resp_holder, db)
    if not security.is_device_approved(device):
        return RedirectResponse("/pending", status_code=302)
    html = templates.TemplateResponse(request, "login.html", {"error": None})
    for k, v in resp_holder.raw_headers:
        if k.decode().lower() == "set-cookie":
            html.raw_headers.append((k, v))
    return html


@app.post("/login")
def login_submit(request: Request, password: str = Form(...), db: Session = Depends(get_db)):
    resp = RedirectResponse("/dashboard", status_code=302)
    device = security.get_or_create_device(request, resp, db)
    if not security.is_device_approved(device):
        return RedirectResponse("/pending", status_code=302)
    if not verify_admin_password(db, password):
        return templates.TemplateResponse(
            request, "login.html", {"error": "비밀번호가 올바르지 않습니다."}
        )
    security.create_session_cookie(resp, device.device_token)
    return resp


@app.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=302)
    security.clear_session_cookie(resp)
    return resp


# ---------- 대시보드 ----------
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    g = _guard(request, db)
    if g:
        return g
    devices = db.query(Device).order_by(Device.created_at.desc()).all()
    current = security.read_session(request)
    current_token = current.get("device") if current else None
    stats = services.dashboard_stats(db)
    return templates.TemplateResponse(
        request, "dashboard.html",
        {"devices": devices, "current_token": current_token, "stats": stats,
         "site_labels": services.SITE_LABELS},
    )


# ---------- 상품 목록 ----------
@app.get("/products", response_class=HTMLResponse)
def products_page(request: Request, db: Session = Depends(get_db),
                  site: str = Query(""), q: str = Query(""),
                  page: int = Query(1)):
    g = _guard(request, db)
    if g:
        return g
    page = max(1, page)
    per = 50
    query = db.query(Product)
    if site:
        query = query.filter(Product.source_site == site)
    if q:
        query = query.filter(Product.title.like(f"%{q}%"))
    total = query.count()
    items = (query.order_by(Product.updated_at.desc())
             .offset((page - 1) * per).limit(per).all())
    pages = max(1, (total + per - 1) // per)
    return templates.TemplateResponse(
        request, "products.html",
        {"items": items, "total": total, "page": page, "pages": pages,
         "site": site, "q": q, "site_labels": services.SITE_LABELS},
    )


# ---------- 설정 ----------
@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    g = _guard(request, db)
    if g:
        return g
    sites = []
    for s in services.SUPPORTED_SITES:
        rec = services.get_site_credential(db, s)
        sites.append({
            "key": s, "label": services.SITE_LABELS[s],
            "username": rec.username if rec else "",
            "has_pw": bool(rec and rec.password_enc),
            "enabled": rec.enabled if rec else True,
        })
    markets = []
    for m in services.SUPPORTED_MARKETS:
        rec = services.get_market_credential(db, m)
        markets.append({
            "key": m, "label": services.MARKET_LABELS[m],
            "client_id": rec.client_id if rec else "",
            "has_secret": bool(rec and rec.client_secret_enc),
            "enabled": rec.enabled if rec else True,
        })
    profile = services.get_default_profile(db)
    return templates.TemplateResponse(
        request, "settings.html",
        {"sites": sites, "markets": markets, "profile": profile},
    )


@app.post("/settings/site")
def save_site(request: Request, site: str = Form(...), username: str = Form(""),
              password: str = Form(""), enabled: str = Form(""),
              db: Session = Depends(get_db)):
    g = _guard(request, db)
    if g:
        return g
    services.save_site_credential(db, site, username, password, enabled == "on")
    return RedirectResponse("/settings", status_code=302)


@app.post("/settings/market")
def save_market(request: Request, market: str = Form(...), client_id: str = Form(""),
                client_secret: str = Form(""), enabled: str = Form(""),
                db: Session = Depends(get_db)):
    g = _guard(request, db)
    if g:
        return g
    services.save_market_credential(db, market, client_id, client_secret,
                                    enabled=(enabled == "on"))
    return RedirectResponse("/settings", status_code=302)


@app.post("/settings/profile")
def save_profile(request: Request,
                 margin_rate: int = Form(30), payment_fee_rate: int = Form(4),
                 round_unit: int = Form(100), min_price: int = Form(0),
                 prefix: str = Form(""), suffix: str = Form(""),
                 banned_words: str = Form(""), default_stock: int = Form(200),
                 db: Session = Depends(get_db)):
    g = _guard(request, db)
    if g:
        return g
    services.save_default_profile(
        db, margin_rate=margin_rate, payment_fee_rate=payment_fee_rate,
        round_unit=round_unit, min_price=min_price, prefix=prefix, suffix=suffix,
        banned_words=banned_words, default_stock=default_stock,
    )
    return RedirectResponse("/settings", status_code=302)


# ---------- 작업 API ----------
@app.post("/api/collect")
async def api_collect(request: Request, db: Session = Depends(get_db)):
    if not _guard_api(request, db):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    body = await request.json()
    sites = body.get("sites") or services.SUPPORTED_SITES
    max_items = body.get("max_items")
    sites = [s for s in sites if s in services.SUPPORTED_SITES]
    job_id = jobs.start_collect(sites, max_items)
    return {"job_id": job_id}


@app.post("/api/list-naver")
async def api_list_naver(request: Request, db: Session = Depends(get_db)):
    if not _guard_api(request, db):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    body = await request.json()
    product_ids = [int(x) for x in body.get("product_ids", [])]
    leaf_category_id = str(body.get("leaf_category_id", "")).strip()
    dry_run = bool(body.get("dry_run", True))
    if not product_ids:
        return JSONResponse({"error": "선택된 상품이 없습니다."}, status_code=400)
    if not leaf_category_id:
        return JSONResponse({"error": "카테고리 ID(leafCategoryId)를 입력하세요."}, status_code=400)
    job_id = jobs.start_naver_listing(product_ids, leaf_category_id, dry_run)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def api_job(job_id: str, request: Request, db: Session = Depends(get_db)):
    if not _guard_api(request, db):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    j = jobs.get_job(job_id)
    if not j:
        return JSONResponse({"error": "not found"}, status_code=404)
    return j


@app.get("/api/stats")
def api_stats(request: Request, db: Session = Depends(get_db)):
    if not _guard_api(request, db):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return services.dashboard_stats(db)


# ---------- 기기 관리 (승인/차단/삭제) ----------
@app.post("/devices/{device_id}/approve")
def approve_device(device_id: int, request: Request, db: Session = Depends(get_db)):
    g = _guard(request, db)
    if g:
        return g
    d = db.get(Device, device_id)
    if d:
        d.approved = True
        db.commit()
    return RedirectResponse("/dashboard", status_code=302)


@app.post("/devices/{device_id}/block")
def block_device(device_id: int, request: Request, db: Session = Depends(get_db)):
    g = _guard(request, db)
    if g:
        return g
    d = db.get(Device, device_id)
    if d:
        d.approved = False
        db.commit()
    return RedirectResponse("/dashboard", status_code=302)


@app.post("/devices/{device_id}/label")
def label_device(device_id: int, request: Request, label: str = Form(""),
                 db: Session = Depends(get_db)):
    g = _guard(request, db)
    if g:
        return g
    d = db.get(Device, device_id)
    if d:
        d.label = label[:120]
        db.commit()
    return RedirectResponse("/dashboard", status_code=302)


@app.post("/devices/{device_id}/delete")
def delete_device(device_id: int, request: Request, db: Session = Depends(get_db)):
    g = _guard(request, db)
    if g:
        return g
    d = db.get(Device, device_id)
    if d:
        db.delete(d)
        db.commit()
    return RedirectResponse("/dashboard", status_code=302)


# ---------- 비밀번호 변경 ----------
@app.post("/change-password")
def change_password(request: Request, new_password: str = Form(...),
                    db: Session = Depends(get_db)):
    g = _guard(request, db)
    if g:
        return g
    if len(new_password) >= 4:
        set_admin_password(db, new_password)
    return RedirectResponse("/dashboard", status_code=302)


# ---------- 헬스 체크 ----------
@app.get("/health")
def health():
    return {"status": "ok"}
