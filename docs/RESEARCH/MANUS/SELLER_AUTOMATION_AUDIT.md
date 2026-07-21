# Manus Seller Automation Audit

Audit date: 2026-07-11

Target source: `external_workmanus/seller_automation`

Scope rule: read-only audit. The original Manus folder, runtime database, secret file, logs, cache,
existing AI-Content-OS code/tests/shared documents/site/storage, and Git state were not modified.
The target application was not executed.

Legend:

- `CONFIRMED`: directly observed in repository files during this audit.
- `INFERRED`: derived from observed code structure or naming, but not runtime-verified.
- `UNKNOWN`: not verified in this audit, usually because it requires credentials, external network,
  database inspection, platform policy confirmation, or original runtime execution.

## 1. Excluded And Bounded Analysis Scope

`CONFIRMED`: The target folder has these top-level entries:

- `app/` - application code and templates, about 0.21 MB.
- `docs/` - source-site and market notes, about 0.01 MB.
- `data/` - runtime data, about 127.87 MB.
- `logs/` - log directory, about 0.00 MB.
- `venv/` - Python virtual environment, about 69.95 MB.
- `README.md`, `requirements.txt`, `run_server.bat`.

`CONFIRMED`: `data/seller.db` exists and is about 134,078,464 bytes. It was not opened or queried.
It may contain credentials, product data, account metadata, logs, or personal data.

`CONFIRMED`: `data/secret.key` exists and has a file length of 64 characters. The value was not
read or recorded. Only existence was noted.

`CONFIRMED`: `venv/`, `logs/`, bytecode, generated data, and runtime database contents were not
deep-read. They were classified by structure and size only.

## 2. Architecture And Execution Model

`CONFIRMED`: The application is a Windows-oriented local web server. `README.md` describes it as a
"나만의 셀러 자동화 시스템 (Windows 11 전용)" and instructs users to run `run_server.bat`.

`CONFIRMED`: `requirements.txt` declares a FastAPI stack:

- `fastapi`, `uvicorn`, `jinja2`
- `sqlalchemy`
- `itsdangerous`, `cryptography`, `bcrypt`
- `requests`, `beautifulsoup4`, `lxml`
- `python-multipart`

`CONFIRMED`: `run_server.bat` creates or reuses `venv/`, installs requirements if FastAPI is
missing, prints the default admin password, and starts:

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Evidence: `external_workmanus/seller_automation/run_server.bat`.

`CONFIRMED`: `app/main.py` creates a FastAPI app with web pages and JSON endpoints for dashboard,
settings, product listing, device approval, collection jobs, Naver listing jobs, job status, and
health checks.

Key observed endpoints:

- `/`, `/pending`, `/login`, `/logout`
- `/dashboard`, `/products`, `/settings`
- `/settings/site`, `/settings/market`, `/settings/profile`
- `/api/collect`, `/api/list-naver`, `/api/jobs/{job_id}`, `/api/stats`
- `/devices/{device_id}/approve`, `/devices/{device_id}/block`,
  `/devices/{device_id}/label`, `/devices/{device_id}/delete`
- `/change-password`, `/health`

`CONFIRMED`: Runtime storage is SQLite under `data/seller.db`.
Evidence: `app/config.py`, `app/database.py`.

`CONFIRMED`: Credential-like values are encrypted with Fernet using a key derived from
`data/secret.key`.
Evidence: `app/crypto.py`.

`CONFIRMED`: Jobs are in-memory background threads.
Evidence: `app/jobs.py`.

`INFERRED`: The application is not production-server hardened. It is designed as a local/LAN
operator tool with local state and browser-based administration, not as a multi-user hosted SaaS.

## 3. Why This Upload Approach Was Used

This section records only what the Manus code and local Manus documents show. It does not decide
current official platform policy. Current SmartStore/Coupang policy verification remains a separate
Claude/Independent QA workstream.

### 3.1 Actual Implementation Path

`CONFIRMED`: The observed implementation does not use Selenium, Playwright, Chrome extension,
WebDriver, Puppeteer, or browser DOM automation for marketplace upload.

Evidence:

- `requirements.txt` contains FastAPI/server/scraping libraries, but no Selenium, Playwright,
  Puppeteer, browser extension, or WebDriver package.
- `app/markets/naver_client.py` implements Naver Commerce API calls for category lookup, image
  upload, and product creation.
- `app/markets/naver_auth.py` implements a Naver Commerce API token/signature flow.
- `app/jobs.py` calls `NaverClient.upload_image()` and `NaverClient.create_product()`.
- Template JavaScript uses DOM selectors only for local UI checkbox/form handling and sends
  `fetch('/api/list-naver')`; it is not automating an external seller portal DOM.

`CONFIRMED`: Source-site collection uses direct HTTP/API/HTML calls through `requests`, not browser
automation.

Evidence:

- `app/crawlers/luckyfresh.py` documents an internal API direct-call approach.
- `app/crawlers/choigozip.py` documents public API direct collection.
- `app/crawlers/adminplus.py` uses session/HTML-oriented requests.

`UNKNOWN`: No Chrome extension or desktop browser-automation artifact was found in the target
folder. If a separate FarmersGo/extension artifact exists, it is outside this folder and outside
this specific audit's confirmed evidence.

### 3.2 Was There A Recorded Reason For Not Using APIs?

`CONFIRMED`: For Naver SmartStore, the local Manus materials show the opposite of API avoidance:
the system was designed around Naver Commerce API usage.

Evidence:

- `README.md` says products are registered through the Naver SmartStore Commerce API.
- `README.md` has a "네이버 API 키 등록" section.
- `README.md` says real registration requires the PC public IP to match the allowed IP registered
  in the Naver Commerce API Center.
- `docs/market_naver.md` describes Naver Commerce API auth, product registration, image upload,
  and implementation steps.

`CONFIRMED`: For Coupang, the code and UI show "not implemented yet", not a confirmed platform ban.

Evidence:

- `services.py` includes `coupang` in `SUPPORTED_MARKETS`.
- `settings.html` disables non-Naver market credential fields and labels them as planned later.
- `README.md` says the first version is complete through Naver SmartStore and Coupang will be added
  later in the same plugin-like structure.
- No `coupang_client.py` or Coupang upload job equivalent was found.

`UNKNOWN`: No local Manus file found in this audit states that SmartStore or Coupang fully forbid
API upload.

`UNKNOWN`: No local Manus file found in this audit proves that Coupang's API was unusable at the
time. The local evidence only confirms that Coupang was deferred.

`CONFIRMED`: Manus local docs contain Naver-specific uncertainty markers, such as
`docs/market_naver.md` calling the product endpoint "추정/표준" and source-site docs using phrases
like "추정" or "추가 확인 필요".

`INFERRED`: Manus likely encoded the author's then-current practical understanding of Naver API
use, including IP allowlisting and CAMPA/OSSA-derived signature details, but the local files are not
sufficient to treat those as current official facts.

### 3.3 Platform Restriction Categories

| Claim category | SmartStore in Manus evidence | Coupang in Manus evidence |
|---|---|---|
| Platform fully bans API upload | `UNKNOWN`; not stated in local files | `UNKNOWN`; not stated in local files |
| Seller/app approval required | `CONFIRMED` only as local Manus claim: Naver API key and allowed IP are required | `UNKNOWN`; no Coupang implementation docs found |
| Product registration API limited | `UNKNOWN`; product create path exists, but exact current official limits not verified here | `UNKNOWN`; no implementation |
| Official API exists but access conditions may block practical use | `CONFIRMED` as local Manus claim for Naver allowed-IP mismatch blocking real registration | `UNKNOWN` from this folder |
| Manus assumption/reverse-engineered claim | `CONFIRMED`: `naver_auth.py` references CAMPA/OSSA analysis; `market_naver.md` uses "추정/표준" | `UNKNOWN`; no comparable Coupang note found |

### 3.4 API Capability Scope Shown By Manus Files

This table is not a current official policy statement. It is only what the Manus folder implements
or documents.

| Platform | New product registration | Product modification | Price | Stock | Order/shipping |
|---|---|---|---|---|---|
| SmartStore | `CONFIRMED code path`: `NaverClient.create_product()` posts a product payload | `UNKNOWN`: no explicit update/modify job found | `CONFIRMED included in create payload`; separate price update API `UNKNOWN` | `CONFIRMED included in create payload`; separate stock update API `UNKNOWN` | `UNKNOWN`: no order/shipping API implementation found |
| Coupang | `CONFIRMED not implemented in this folder` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |

### 3.5 Browser Automation Risk If Considered Later

`CONFIRMED`: Browser automation is not the observed marketplace upload implementation in this
folder.

`INFERRED`: If future work uses Selenium/Playwright/Chrome extension/DOM auto-input as a fallback,
it should be treated as high risk because it can introduce:

- platform terms and account suspension risk,
- selector/UI breakage,
- CAPTCHA and bot-detection failure,
- accidental live listing or price/stock mutation,
- session cookie and personal-data exposure,
- weak auditability compared with explicit payload artifacts.

`INFERRED`: Browser automation should be blocked by default until policy approval, account-risk
approval, and a human-supervised dry-run plan exist.

### 3.6 Safe Target For AI-Content-OS

`INFERRED`: The safe target should not be "automatic upload" as the default. The safer Commerce
target is:

1. verified product facts,
2. platform-shaped payload artifacts,
3. freshness/source/rights gates,
4. user review and approval,
5. only then an allowed transmission method.

`CONFIRMED`: This aligns with existing AI-Content-OS Commerce Phase 1, which is manual-only, and
Commerce Phase 2 research, which gates dry-run payload generation and any real upload behind CTO
approval.

### 3.7 Alternative Priority If Official API Use Is Not Available

`INFERRED`: If official API use is unavailable or not approved, the preferred fallback order should
be:

1. Platform official bulk-registration file, if available and policy-compliant.
2. Semi-automatic input only after user approval, with no hidden side effects.
3. Official partner/solution workflow.
4. Browser automation only as the last resort, blocked until explicit policy/account-risk approval.

`INFERRED`: Under this hierarchy, Manus's existing Naver API client should be treated as a research
artifact, not as an approved AI-Content-OS upload adapter.

## 4. Implemented, Partial, Stub, And Unconnected Capabilities

### 4.1 Core UI And Local Administration

`CONFIRMED`: Implemented or substantially implemented:

- Login page and signed session cookie.
- Device cookie, device approval, block, label, and delete flows.
- Dashboard with collection controls, job polling, stats, device list, and password change.
- Settings UI for source credentials, Naver market credentials, and processing profile.
- Product table with filters and Naver listing controls.

Evidence: `app/main.py`, `app/templates/dashboard.html`, `app/templates/settings.html`,
`app/templates/products.html`.

`UNKNOWN`: Runtime UX correctness was not verified because the application was not executed.

### 4.2 Product Collection

`CONFIRMED`: Three source collectors are present and wired in `app/collector.py`:

- `luckyfresh`
- `econfarm`
- `choigozip`

`CONFIRMED`: Source-specific crawler files exist:

- `app/crawlers/luckyfresh.py`
- `app/crawlers/adminplus.py`
- `app/crawlers/choigozip.py`

`CONFIRMED`: Collection persists product fields including source IDs, price-like data, thumbnail
URLs, detail HTML, options, and metadata through SQLAlchemy models.
Evidence: `app/models.py`, `app/collector.py`.

`UNKNOWN`: Actual live collection success is not verified. It requires source-site credentials,
network access, and current source-site structure.

### 4.3 Naver SmartStore

`CONFIRMED`: Naver SmartStore listing code exists:

- `app/markets/naver_auth.py` - token/signature flow.
- `app/markets/naver_client.py` - category search, image upload, product create.
- `app/markets/naver_payload.py` - payload builder.
- `app/jobs.py` - starts Naver listing jobs from selected product IDs.

`CONFIRMED`: Dry-run is supported. `products.html` defaults the checkbox to dry-run, and asks for
confirmation when dry-run is disabled.

`CONFIRMED`: Non-dry-run can call external Naver API paths and can change product listing state.
Evidence: `app/markets/naver_client.py`, `app/jobs.py`.

`UNKNOWN`: Naver auth, payload schema, image upload method, category metadata, notice information,
and seller eligibility were not confirmed against official current documentation in this audit.

### 4.4 Coupang, Gmarket, Toss

`CONFIRMED`: The service layer lists `SUPPORTED_MARKETS = ["naver", "coupang", "gmarket", "toss"]`.

`CONFIRMED`: The settings template disables non-Naver market inputs and labels them as
`준비중`.

`CONFIRMED`: No Coupang/Gmarket/Toss client implementation equivalent to `markets/naver_client.py`
was found.

Assessment:

- Coupang: `stub/placeholder`.
- Gmarket: `stub/placeholder`.
- Toss: `stub/placeholder`.

### 4.5 Detail Page Generation

`CONFIRMED`: Product detail content is primarily carried forward from collected source detail HTML
and converted into Naver payload fields. A separate AI/content detail-page generator was not found.

`CONFIRMED`: `app/processing.py` implements simple product-name and price transformations.

`INFERRED`: Detail-page generation is partial. It packages existing source detail content and
basic processing, but does not implement AI-Content-OS style truth-gated detail-page sections,
rights checks, or freshness gates.

### 4.6 Text Attachment / Copy Controls

`CONFIRMED`: Processing profile fields exist for price margin, shipping fee, name prefix/suffix,
banned words, and A/S phone/default origin-like values.

`UNKNOWN`: A dedicated "text attachment" feature beyond naming/profile fields and source detail
HTML was not identified.

### 4.7 Automatic Upload

`CONFIRMED`: Automatic listing exists for Naver when `dry_run=False`, assuming valid credentials
and successful API calls.

`CONFIRMED`: Automatic upload does not exist for Coupang/Gmarket/Toss.

`UNKNOWN`: Real Naver upload correctness and platform compliance were not verified.

## 5. Function Status Matrix

| Function | Status | Evidence |
|---|---|---|
| Local FastAPI dashboard | `CONFIRMED implemented, runtime unverified` | `app/main.py`, templates |
| Device approval | `CONFIRMED implemented, runtime unverified` | `app/security.py`, `app/main.py` |
| Local encrypted credential storage | `CONFIRMED implemented, key co-located` | `app/crypto.py`, `data/secret.key` |
| Luckyfresh collection | `CONFIRMED code present, live result UNKNOWN` | `app/crawlers/luckyfresh.py`, `app/collector.py` |
| Econfarm/Adminplus collection | `CONFIRMED code present, live result UNKNOWN` | `app/crawlers/adminplus.py`, `app/collector.py` |
| Choigozip collection | `CONFIRMED code present, live result UNKNOWN` | `app/crawlers/choigozip.py`, `app/collector.py` |
| SmartStore dry-run payload | `CONFIRMED code present, schema correctness UNKNOWN` | `app/markets/naver_client.py`, `app/markets/naver_payload.py` |
| SmartStore real upload | `CONFIRMED code path present, unsafe to run without gate` | `app/jobs.py`, `app/markets/naver_client.py` |
| Coupang upload | `CONFIRMED not implemented` | disabled UI, no client |
| Detail-page generator | `INFERRED partial` | `app/processing.py`, `app/markets/naver_payload.py` |
| Tests | `UNKNOWN/likely absent in target` | no target `tests/` found in bounded file list |

## 6. Security And Compliance Risks

### Critical

1. `CONFIRMED`: Documented default admin password and LAN binding coexist.
   - Evidence: `README.md`, `run_server.bat`, `app/config.py`.
   - `run_server.bat` starts on `0.0.0.0:8000`.
   - A default admin password is documented unless overridden by `SA_ADMIN_PW`.
   - Risk: if run on a shared network before password hardening, unauthorized LAN access is
     plausible despite device approval.

2. `CONFIRMED`: Runtime database and decryption key are co-located.
   - Evidence: `data/seller.db`, `data/secret.key`, `app/crypto.py`.
   - Secret value was not read.
   - Risk: copying the `data/` folder may be enough to decrypt stored source credentials and
     market API keys.

3. `CONFIRMED`: Real Naver product creation can be triggered by the app when dry-run is disabled.
   - Evidence: `products.html`, `app/jobs.py`, `app/markets/naver_client.py`.
   - Risk: live marketplace side effects, wrong price/stock/detail content, policy violation, or
     account impact.

### High

1. `CONFIRMED`: Arbitrary remote image URLs from product data can be fetched and uploaded during
   real Naver listing.
   - Evidence: `app/jobs.py` calls `client.upload_image(p.thumbnail_url)`;
     `app/markets/naver_client.py` fetches HTTP URLs.
   - Risk: SSRF-like internal URL access, unexpected file/content upload, tracking, or policy
     breach if product data is polluted.

2. `CONFIRMED`: No CSRF token mechanism was observed for state-changing POST routes.
   - Evidence: form and fetch POST routes in `app/main.py` and templates.
   - Risk: an approved/logged-in browser could be induced to trigger device, collection, settings,
     or listing actions.

3. `CONFIRMED`: Cookies are signed/HTTP-only but not marked secure in observed code.
   - Evidence: `app/security.py`.
   - Risk: session/device cookies are exposed over plain HTTP on LAN.

4. `CONFIRMED`: Hardcoded external source URLs and scraping/API assumptions exist.
   - Evidence: crawler files under `app/crawlers/`.
   - Risk: source-site terms, login flow, bot blocking, IP blocking, and structure drift can break
     collection or create account risk.

5. `CONFIRMED`: Source HTML/detail content is reused in downstream listing payloads.
   - Evidence: `app/models.py`, `app/markets/naver_payload.py`.
   - Risk: unreviewed HTML, tracking tags, prohibited claims, third-party copyrighted content, or
     marketplace-incompatible markup can be pushed forward.

6. `CONFIRMED`: In-memory background jobs are not durable.
   - Evidence: `app/jobs.py`.
   - Risk: server restart loses job state; partial uploads and local records may diverge.

7. `UNKNOWN`: Contents of `seller.db` may include PII, account identifiers, wholesale credentials,
   product data, listing logs, or market API keys. The database was not opened.

8. `UNKNOWN`: Current official Naver Commerce API requirements and source-site permissions were
   not independently verified during this audit.

## 7. Prompt Injection, External Fetch, And Browser Automation Notes

`CONFIRMED`: No LLM prompt pipeline was found in the target application.

`CONFIRMED`: External fetches are present through source crawlers and Naver image upload path.

`CONFIRMED`: Browser automation was not found. The app uses `requests`/HTML parsing/API calls, not
Playwright/Selenium.

`INFERRED`: Prompt injection is not the main immediate risk in this codebase. The closer risks are
HTML/content injection into marketplace detail pages, unsafe remote URL fetches, source-site terms
violations, and live API side effects.

## 8. FarmersGo Desktop/Extension Reuse And Integration Contract

`UNKNOWN`: No direct FarmersGo desktop or browser-extension implementation was found in
`external_workmanus/seller_automation`.

`CONFIRMED`: Existing AI-Content-OS Commerce Phase 1 is intentionally offline and manual-only.
Evidence: `docs/COMMERCE_PHASE_1_CONTRACT.md` states Phase 1 does not log in, crawl a marketplace,
call a marketplace API, use OAuth, automate a browser, or upload/update a listing. It produces
manual-upload packages and keeps `upload_mode: "manual_only"` and `auto_upload_performed: false`.

`CONFIRMED`: Existing AI-Content-OS Commerce Phase 2 research proposes adapter-based uploads only
behind CTO gates. Evidence: `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` proposes
`SmartStoreAdapter` and `CoupangAdapter`, strict preflight checks, dry-run payload generation, and
explicit CTO approval before any real upload.

Reusable contracts from the Manus app:

- `INFERRED`: Local operator dashboard pattern can inform future Commerce admin UX, but should not
  be copied as-is.
- `INFERRED`: Source credential grouping by site and market is reusable conceptually, but storage
  must be redesigned to avoid key/database co-location.
- `INFERRED`: Job lifecycle shape (`queued/running/done/failed`, progress, logs) can inform a safe
  Commerce operation queue.
- `INFERRED`: Product collection output fields can help design an import schema, but every
  product fact must be passed through AI-Content-OS Commerce Phase 1 truth/source/freshness gates.
- `INFERRED`: Naver payload field mapping can be used only as a research hint. It is not a trusted
  implementation contract until confirmed against official platform documentation.

Non-reusable or blocked contracts:

- `CONFIRMED`: Direct real upload code is incompatible with current Phase 1 manual-only contract.
- `CONFIRMED`: Source crawling and marketplace API calls are outside Phase 1.
- `INFERRED`: Any FarmersGo-style extension/desktop automation should be treated as a separate
  Phase 2 or later operator tool, not merged into WorkflowEngine or Commerce Phase 1.

## 9. AI-Content-OS Commerce Phase 1/2 Overlap, Conflict, And Reuse

### Overlap

`CONFIRMED`: Both systems target SmartStore-ready product content and platform package preparation.

`CONFIRMED`: Manus contains Naver-specific payload and upload code. AI-Content-OS has Commerce
Phase 1 contracts and Phase 2 upload architecture documents.

### Conflict

`CONFIRMED`: Manus can crawl, store credentials, call marketplace APIs, upload images, and create
Naver listings. AI-Content-OS Commerce Phase 1 forbids those actions.

`CONFIRMED`: Manus product facts are collected/scraped and transformed without the AI-Content-OS
truth/source/freshness/rights gate model.

`CONFIRMED`: Manus stores runtime data under its own `data/` layout, while AI-Content-OS Commerce
Phase 1 writes controlled package artifacts under `storage/commerce/<request_id>/`.

### Reuse

`INFERRED`: Safe reuse should be limited to:

- audit references,
- schema comparison,
- UX/job-flow ideas,
- Naver field-mapping hints,
- future isolated importer design.

`INFERRED`: Direct code reuse should be blocked until security, legal, source-rights, official API,
and credential-storage questions are resolved.

## 10. Execution Decision

`CONFIRMED`: The target should not be run as-is from AI-Content-OS during normal development.

Reasons:

- It can bind to all network interfaces.
- It has a default admin password unless environment configuration overrides it.
- It can store and use real credentials.
- It can perform real Naver product creation when dry-run is disabled.
- It may fetch arbitrary product image URLs.
- It contains a large existing runtime database whose contents were not inspected.

Safe isolated execution conditions, if a future owner explicitly approves runtime testing:

1. Use a disposable machine or VM with no personal browser session, no production credentials, and
   no shared LAN exposure.
2. Bind to `127.0.0.1` only.
3. Override the default admin password before first boot.
4. Start with a copied, empty database and a newly generated secret key, never the existing
   `data/` folder.
5. Block external network by default; allowlist only documented targets for a specific test.
6. Keep Naver listing in dry-run only unless a CTO-approved sandbox/test-account plan exists.
7. Log and inspect every outbound request.
8. Do not connect AI-Content-OS storage, `.env`, or Commerce outputs to this app during isolation
   testing.

## 11. Recommended Non-Overlapping Work Lanes

1. Lane A - Security Containment Audit
   - Owns: a new risk register and isolated-run checklist.
   - Excludes: product import, platform adapter code, WorkflowEngine.
   - Goal: decide whether the Manus app may ever be executed in a sandbox.

2. Lane B - Schema Mapping Research
   - Owns: mapping document from Manus `Product`/`ProcessingProfile`/Naver payload fields to
     AI-Content-OS Commerce Phase 1 input contract.
   - Excludes: code reuse and runtime database reads.
   - Goal: identify which fields can be imported only after source/freshness/rights verification.

3. Lane C - Official Platform Verification
   - Owns: official Naver SmartStore and Coupang API evidence review.
   - Excludes: implementation.
   - Goal: close `UNKNOWN` gaps around auth, image upload, notice fields, sandbox/test accounts,
     and rate limits.

4. Lane D - Isolated Importer Prototype Design
   - Owns: a proposal for reading a sanitized export, not the live Manus database.
   - Excludes: direct `seller.db` access, credential import, source crawling, marketplace upload.
   - Goal: convert safe product facts into Commerce Phase 1 request objects.

5. Lane E - Future Operator UI Pattern
   - Owns: UI/job-flow pattern analysis only.
   - Excludes: authentication reuse, credentials, live upload, source scraping.
   - Goal: reuse dashboard ergonomics without copying insecure runtime assumptions.

6. Lane F - Platform Upload Adapter Phase 2A
   - Owns: dry-run-only payload generation from already `ready_for_manual_upload` Commerce Phase 1
     packages.
   - Excludes: credentials, real API calls, browser automation, automatic upload.
   - Goal: align with `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`.

## 12. Final Integration Judgment

`CONFIRMED`: Manus Seller Automation is a separate, incomplete but functional-looking local seller
automation prototype. It is not a drop-in module for AI-Content-OS.

`INFERRED`: Its most valuable near-term use is reference material for Commerce schema mapping and
operator UX, not implementation reuse.

`CONFIRMED`: Direct integration would violate current AI-Content-OS Commerce Phase 1 boundaries.

`INFERRED`: Future reuse is possible only after a security containment pass, official platform
verification, sanitized export design, and CTO-approved Phase 2 adapter work.

## 13. Evidence Index

Key target files read:

- `external_workmanus/seller_automation/README.md`
- `external_workmanus/seller_automation/requirements.txt`
- `external_workmanus/seller_automation/run_server.bat`
- `external_workmanus/seller_automation/app/main.py`
- `external_workmanus/seller_automation/app/config.py`
- `external_workmanus/seller_automation/app/database.py`
- `external_workmanus/seller_automation/app/models.py`
- `external_workmanus/seller_automation/app/security.py`
- `external_workmanus/seller_automation/app/crypto.py`
- `external_workmanus/seller_automation/app/passwords.py`
- `external_workmanus/seller_automation/app/services.py`
- `external_workmanus/seller_automation/app/processing.py`
- `external_workmanus/seller_automation/app/collector.py`
- `external_workmanus/seller_automation/app/jobs.py`
- `external_workmanus/seller_automation/app/crawlers/base.py`
- `external_workmanus/seller_automation/app/crawlers/luckyfresh.py`
- `external_workmanus/seller_automation/app/crawlers/adminplus.py`
- `external_workmanus/seller_automation/app/crawlers/choigozip.py`
- `external_workmanus/seller_automation/app/markets/naver_auth.py`
- `external_workmanus/seller_automation/app/markets/naver_client.py`
- `external_workmanus/seller_automation/app/markets/naver_payload.py`
- `external_workmanus/seller_automation/app/templates/dashboard.html`
- `external_workmanus/seller_automation/app/templates/products.html`
- `external_workmanus/seller_automation/app/templates/settings.html`
- `external_workmanus/seller_automation/docs/market_naver.md`
- `external_workmanus/seller_automation/docs/site_choigozip.md`
- `external_workmanus/seller_automation/docs/site_econfarm.md`
- `external_workmanus/seller_automation/docs/site_luckyfresh.md`
- `docs/COMMERCE_PHASE_1_CONTRACT.md`
- `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md`
- `modules/commerce/commerce_module.py`
- `modules/commerce/commerce_storage.py`

Files intentionally not read deeply:

- `external_workmanus/seller_automation/data/seller.db`
- `external_workmanus/seller_automation/data/secret.key`
- `external_workmanus/seller_automation/venv/**`
- `external_workmanus/seller_automation/logs/**`
- bytecode/cache/generated runtime files

Secret handling:

- `CONFIRMED`: secret-like files and credential storage paths exist.
- `CONFIRMED`: no secret value, cookie value, API key, account password, or database record content
  is recorded in this audit.
