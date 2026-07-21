"""Content Portfolio V1.4.1 -- Release Boundary correction.

Stdlib only. Corrects a real overclaim from the V1.4 handoff summary: "9 of 12 pieces need no
photo, no source, no approval from the user at all" conflated two genuinely different readiness
states -- (1) copy drafting needing no further evidence, and (2) actual production/publish
readiness, which every single item still lacks regardless of how evidence-clean its copy is.

This script reads WORK_ORDERS_V1_4.json (69 work orders from V1.4) and adds a three-tier release
boundary to every one of them:

- copy_draft_ready: true for all 12 content_ids -- copy drafting itself needs no further
  external evidence (this was already true and is not being walked back).
- production_asset_ready: false for every work order right now -- no real photo, video, audio,
  or rights record has actually been captured for anything in this batch yet.
- publish_review_ready: false for every work order right now -- no per-channel asset, no
  attribution decision, no operator approval, and (for CardNews) no technical release gate has
  been resolved.

Also adds asset_provenance_required, operator_approval_required, technical_release_gate, and
release_blockers per content-type rules the CTO specified: CardNews fallback images are
dev-safe-validation-only and never a publish-approval substitute; Shorts needs real footage +
separate music/voice rights; Instagram needs final graphic provenance; Knowledge needs a
separate image/attribution judgment if published standalone.

Never reads/writes outside external_workclaude/content_portfolio_v1/, no network call, no Git
operation, no real publish/purchase/account action, no code change to modules/tests/docs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
WORKORDERS_JSON = BASE / "WORK_ORDERS_V1_4.json"

OUT_WORKORDERS_JSON = BASE / "WORK_ORDERS_V1_4_1.json"
OUT_USERINPUT_MD = BASE / "USER_INPUT_REQUEST_V1_4_1.md"
OUT_MATRIX_MD = BASE / "RELEASE_BOUNDARY_MATRIX_V1_4_1.md"
OUT_QA_MD = BASE / "QA_REPORT_V1_4_1.md"

CARDNEWS_RECEIPT_BLOCKER = "CARDNEWS_RECEIPT_FALSE_READY_UNRESOLVED"
EVIDENCE_REVIEW_BLOCKER = "EVIDENCE_REVIEW_PENDING"

BANNED_OVERCLAIM_PATTERNS = [
    re.compile(r"사진.{0,3}출처.{0,3}승인.{0,5}필요\s*없"),
    re.compile(r"필요.{0,3}없.{0,5}(사진|출처|승인)"),
]

CARDNEWS_IDS = {"CN-013", "CN-014", "CN-016", "CN-017"}
SHORTS_IDS = {"SH-017", "SH-006", "SH-018"}
INSTAGRAM_IDS = {"IG-007", "IG-009", "IG-013"}
KNOWLEDGE_IDS = {"KN-007", "KN-008"}


def content_type_of(content_id):
    if content_id in CARDNEWS_IDS:
        return "cardnews"
    if content_id in SHORTS_IDS:
        return "shorts"
    if content_id in INSTAGRAM_IDS:
        return "instagram_feed"
    if content_id in KNOWLEDGE_IDS:
        return "knowledge_evergreen"
    raise ValueError(f"unknown content_id {content_id}")


def release_fields_for(content_id, existing_blocker_codes):
    ct = content_type_of(content_id)

    release_blockers = ["NO_REAL_ASSET_CAPTURED", "NO_OPERATOR_APPROVAL_RECORDED", "ASSET_PROVENANCE_UNCONFIRMED"]
    if CARDNEWS_RECEIPT_BLOCKER in existing_blocker_codes:
        release_blockers.append(CARDNEWS_RECEIPT_BLOCKER)
    if EVIDENCE_REVIEW_BLOCKER in existing_blocker_codes:
        release_blockers.append(EVIDENCE_REVIEW_BLOCKER)

    if ct == "cardnews":
        asset_provenance = {
            "required": True,
            "description": (
                "실제 게시에는 권리 승인된 이미지 또는 승인된 생성 이미지 기록이 필요함. "
                "CardNewsModule fallback 배경(단색/그라디언트)은 dev-safe 검증(레이아웃/타이포 확인) "
                "전용이며, 게시 승인 이미지로 취급하지 않음."
            ),
        }
        technical_release_gate = (
            f"07/08 workflow_results receipt false-ready 이슈({CARDNEWS_RECEIPT_BLOCKER})가 "
            "해결되기 전까지 package/publish review 진행 금지 -- Common Engine/CardNews 담당 팀 "
            "확인 필요 (이 패키지는 수정하지 않음)"
        )
    elif ct == "shorts":
        asset_provenance = {
            "required": True,
            "description": (
                "실제 촬영 영상과 촬영자 소유권/동의 확인이 반드시 필요함. 음악·음성(TTS)·배경 "
                "자산을 사용할 경우 각각 별도의 라이선스 확인이 필요하며, 촬영 영상의 존재가 "
                "음악/음성 자산의 권리까지 자동으로 충족시키지 않음."
            ),
        }
        technical_release_gate = (
            "자동 렌더링/TTS/음악 삽입 파이프라인 없음 -- 전 과정 수동 촬영·편집 후 운영자 검수 필요, "
            "이 패키지 범위에서 자동화되는 기술적 게이트는 없음"
        )
    elif ct == "instagram_feed":
        asset_provenance = {
            "required": True,
            "description": "최종 게시 이미지/그래픽의 출처(자체 제작/자체 촬영/라이선스)가 확인되어야 함.",
        }
        technical_release_gate = (
            "N/A -- CardNewsModule 렌더 파이프라인에 의존하지 않는 단순 카드/이미지 포맷, "
            "별도 기술적 게이트 없음 (운영자 검수는 별도로 필요)"
        )
    else:  # knowledge_evergreen
        asset_provenance = {
            "required": "conditional",
            "description": (
                "독립 게시물로 발행할 경우 최종 이미지 사용 여부와 attribution 필요 여부를 별도로 "
                "판단해야 함. 현재는 자체 제작 인포그래픽 우선 방침이며, 이미지를 사용하지 않으면 "
                "provenance 이슈가 발생하지 않지만 이 판단 자체는 아직 내려지지 않았음."
            ),
        }
        technical_release_gate = "N/A -- 문서형 콘텐츠, 별도 기술적 게이트 없음 (운영자 검수는 별도로 필요)"
        release_blockers[0] = "NO_REAL_ASSET_CAPTURED_IF_IMAGE_USED"

    return {
        "copy_draft_ready": True,
        "production_asset_ready": False,
        "publish_review_ready": False,
        "asset_provenance_required": asset_provenance,
        "operator_approval_required": True,
        "technical_release_gate": technical_release_gate,
        "release_blockers": release_blockers,
    }


def flatten_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from flatten_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from flatten_strings(v)


def run_qa(work_orders, rendered_text_blobs, by_content=None):
    lines = []
    ok = True

    misrepresented = [
        wo["work_order_id"] for wo in work_orders
        if wo["copy_draft_ready"] and wo["publish_review_ready"] and not (wo["production_asset_ready"])
    ]
    # the above can never trigger since publish_review_ready is always False right now; the real
    # check is the inverse invariant: publish_review_ready implies production_asset_ready implies
    # nothing is silently skipped.
    inconsistent = [
        wo["work_order_id"] for wo in work_orders
        if wo["publish_review_ready"] and not wo["production_asset_ready"]
    ]
    lines.append(f"[copy readiness를 publish readiness로 오인하는 항목] {'PASS' if not inconsistent else 'FAIL'} -- violations={inconsistent}")
    ok &= not inconsistent

    no_asset_but_ready = [wo["work_order_id"] for wo in work_orders if wo["production_asset_ready"] is not False]
    lines.append(f"[자산 없이 production_asset_ready=true인 항목] {'PASS' if not no_asset_but_ready else 'FAIL'} -- violations={no_asset_but_ready}")
    ok &= not no_asset_but_ready

    no_approval_but_ready = [wo["work_order_id"] for wo in work_orders if wo["publish_review_ready"] is not False]
    lines.append(f"[operator 승인 없이 publish_review_ready=true인 항목] {'PASS' if not no_approval_but_ready else 'FAIL'} -- violations={no_approval_but_ready}")
    ok &= not no_approval_but_ready

    cn_render_stages = {"RENDER_OUTPUT", "PACKAGING_PUBLISH_HANDOFF", "INDEPENDENT_QA_FINAL"}
    cn_bypass = [
        wo["work_order_id"] for wo in work_orders
        if wo["content_id"] in CARDNEWS_IDS and wo["stage"] in cn_render_stages
        and CARDNEWS_RECEIPT_BLOCKER not in wo["release_blockers"]
    ]
    lines.append(f"[CardNews receipt blocker 우회 0] {'PASS' if not cn_bypass else 'FAIL'} -- bypassed={cn_bypass}")
    ok &= not cn_bypass

    fallback_as_approved = [
        wo["work_order_id"] for wo in work_orders
        if wo["content_id"] in CARDNEWS_IDS and wo["publish_review_ready"] is True
    ]
    lines.append(f"[fallback을 게시 승인 이미지로 취급한 항목] {'PASS' if not fallback_as_approved else 'FAIL'} -- violations={fallback_as_approved}")
    ok &= not fallback_as_approved

    not_false = [wo["work_order_id"] for wo in work_orders if wo["publish_ready"] is not False or wo["actual_publish"] is not False]
    lines.append(f"[모든 publish_ready/actual_publish=false] {'PASS' if not not_false else 'FAIL'} -- violations={not_false}")
    ok &= not not_false

    overclaim_hits = []
    for label, text in rendered_text_blobs.items():
        for rx in BANNED_OVERCLAIM_PATTERNS:
            if rx.search(text):
                overclaim_hits.append((label, rx.pattern))
    lines.append(f"[금지 표현('사진·출처·승인이 필요 없다') 재출현 0] {'PASS' if not overclaim_hits else 'FAIL'} -- hits={overclaim_hits}")
    ok &= not overclaim_hits

    required_fields = ["copy_draft_ready", "production_asset_ready", "publish_review_ready",
                       "asset_provenance_required", "operator_approval_required",
                       "technical_release_gate", "release_blockers"]
    missing = [(wo["work_order_id"], f) for wo in work_orders for f in required_fields if f not in wo]
    lines.append(f"[7개 신규 필드 전체 존재] {'PASS' if not missing else 'FAIL'} -- missing={missing}")
    ok &= not missing

    lines.append(f"[work order 총 개수 유지] {'PASS' if len(work_orders) == 69 else 'FAIL'} -- count={len(work_orders)}")
    ok &= len(work_orders) == 69

    if by_content is not None:
        # Regression guard for the content-level aggregation bug found and fixed during this
        # pass: a first-wins pick of one work order per content_id silently dropped the CardNews
        # receipt blocker (only present on later stages, not the copy-finalize stage) from the
        # matrix. Confirm the aggregated view still surfaces it for every CardNews content_id,
        # and the evidence-review blocker for KN-008.
        cn_missing_in_matrix = [
            cid for cid in CARDNEWS_IDS
            if CARDNEWS_RECEIPT_BLOCKER not in by_content[cid]["release_blockers"]
        ]
        lines.append(f"[매트릭스 집계에 CardNews receipt blocker 누락 0 (회귀 방지)] {'PASS' if not cn_missing_in_matrix else 'FAIL'} -- missing={cn_missing_in_matrix}")
        ok &= not cn_missing_in_matrix

        kn008_missing = EVIDENCE_REVIEW_BLOCKER not in by_content["KN-008"]["release_blockers"]
        lines.append(f"[매트릭스 집계에 KN-008 evidence-review blocker 누락 0 (회귀 방지)] {'PASS' if not kn008_missing else 'FAIL'}")
        ok &= not kn008_missing

    return ok, lines


def aggregate_by_content(work_orders):
    """One row per content_id for the matrix -- but the union of release_blockers/gate info
    across ALL of that content_id's stages, not just whichever stage happens to be first. A
    first-wins pick (e.g. always showing the COPY_STORY_FINALIZE stage) would silently hide that
    CN-013's later render/QA/packaging stages carry the CardNews receipt blocker while its copy
    stage does not -- exactly the kind of misleading partial view this correction pass exists to
    prevent."""
    by_content = {}
    for wo in work_orders:
        cid = wo["content_id"]
        if cid not in by_content:
            by_content[cid] = {
                "copy_draft_ready": wo["copy_draft_ready"],
                "production_asset_ready": wo["production_asset_ready"],
                "publish_review_ready": wo["publish_review_ready"],
                "asset_provenance_required": wo["asset_provenance_required"],
                "operator_approval_required": wo["operator_approval_required"],
                "technical_release_gate": wo["technical_release_gate"],
                "release_blockers": set(),
            }
        by_content[cid]["release_blockers"].update(wo["release_blockers"])
        # publish_review_ready/production_asset_ready are false everywhere today, but if any
        # stage ever disagreed, the content-level view must reflect the least-ready stage, not
        # the most-ready one.
        by_content[cid]["copy_draft_ready"] = by_content[cid]["copy_draft_ready"] and wo["copy_draft_ready"]
        by_content[cid]["production_asset_ready"] = by_content[cid]["production_asset_ready"] and wo["production_asset_ready"]
        by_content[cid]["publish_review_ready"] = by_content[cid]["publish_review_ready"] and wo["publish_review_ready"]
    for cid, rec in by_content.items():
        rec["release_blockers"] = sorted(rec["release_blockers"])
    return by_content


def render_matrix_md(by_content):
    lines = ["# Release Boundary Matrix V1.4.1", "",
             "Per content_id, the three-tier readiness state as of right now. `copy_draft_ready` "
             "being true does **not** imply `production_asset_ready` or `publish_review_ready` -- "
             "these are three separate gates, and today every item in this batch sits at the same "
             "point: copy is done, nothing else is.", "",
             "| content_id | copy_draft_ready | production_asset_ready | publish_review_ready | "
             "asset_provenance_required | operator_approval_required | technical_release_gate |",
             "|---|---|---|---|---|---|---|"]
    for cid, wo in by_content.items():
        ap = wo["asset_provenance_required"]
        lines.append(
            f"| {cid} | {wo['copy_draft_ready']} | {wo['production_asset_ready']} | "
            f"{wo['publish_review_ready']} | {ap['required']} | {wo['operator_approval_required']} | "
            f"{wo['technical_release_gate'][:60]}... |"
        )
    lines.append("")
    lines.append("## Full detail per content_id")
    lines.append("")
    for cid, wo in by_content.items():
        lines.append(f"### {cid}")
        lines.append(f"- copy_draft_ready: {wo['copy_draft_ready']}")
        lines.append(f"- production_asset_ready: {wo['production_asset_ready']}")
        lines.append(f"- publish_review_ready: {wo['publish_review_ready']}")
        lines.append(f"- asset_provenance_required: {wo['asset_provenance_required']}")
        lines.append(f"- operator_approval_required: {wo['operator_approval_required']}")
        lines.append(f"- technical_release_gate: {wo['technical_release_gate']}")
        lines.append(f"- release_blockers: {wo['release_blockers']}")
        lines.append("")
    return "\n".join(lines)


def render_user_input_md():
    return "\n".join([
        "# User Input Request V1.4.1 -- corrected", "",
        "## Correction from V1.4", "",
        "V1.4's summary said '9 of 12 pieces need no photo, no source, no approval from the user "
        "at all.' That sentence is deleted -- it conflated two different things. The corrected "
        "statement is:", "",
        "> 9개 콘텐츠는 문안 초안 작성에 추가 사용자 입력이 필요하지 않다. 실제 제작·게시에는 "
        "채널별 자산 권리와 운영자 승인이 별도로 필요하다.", "",
        "In plain English: the **writing** for 9 of these 12 pieces is finished and needed nothing "
        "further from you to get there. Actually **producing and publishing** any of the 12 -- "
        "including those 9 -- still requires real images/assets, rights confirmation, and an "
        "operator's sign-off, none of which exist yet for any item in this batch.", "",
        "## What you need to prepare NOW (to keep things moving)", "",
        "- **Three short self-filmed videos** (the only items that require your own footage): "
        "pet-walk gear (SH-017), coffee brewing (SH-006), suitcase packing (SH-018). Filming takes "
        "real time, so starting now is the one thing that actually speeds up the batch.",
        "- For each video, a one-line confirmation that it's your own pet/gear/suitcase (and, only "
        "if another person appears on camera, that they're okay with it being used).",
        "- Nothing else is needed right now. The other 9 items' copy is finished and doesn't need "
        "anything from you at this stage.", "",
        "## What still needs to happen LATER, right before publish (not your job to prepare now, "
        "just so you know it's coming)", "",
        "- **CardNews (4 items)**: someone has to decide whether each of the 4 will use a real, "
        "rights-cleared photo or the plain fallback background -- the fallback is only good enough "
        "for checking the layout, not for an actual post. Whichever is chosen, it needs a rights "
        "record before publish. Separately, an existing, unrelated technical issue in the "
        "CardNews rendering pipeline needs to be fixed by another team before these 4 can even be "
        "rendered -- that's not something you or this package can resolve.",
        "- **Shorts (3 items)**: once filmed, if any background music or voiceover is added, that "
        "needs its own license check -- owning the video footage doesn't automatically cover music "
        "rights.",
        "- **Instagram (3 items)**: whatever final image or graphic gets used needs its origin "
        "confirmed (made in-house, photographed by you, or properly licensed) right before it goes "
        "out.",
        "- **Knowledge (2 items)**: if these end up posted with an image at all, someone needs to "
        "decide that and confirm the image's rights/attribution at that time -- not decided yet.",
        "- **Every item, no exceptions**: a person (the operator) has to actually look at the "
        "finished piece and approve it before it's real -- nothing in this batch publishes itself.",
        "",
        "## Bottom line", "",
        "Right now: only the 3 videos need your action. Everything else is a later step that "
        "involves rights confirmation and a human sign-off, not something that's already done just "
        "because the writing is finished.",
    ])


def main():
    doc = json.loads(WORKORDERS_JSON.read_text(encoding="utf-8"))
    work_orders = doc["work_orders"]

    for wo in work_orders:
        fields = release_fields_for(wo["content_id"], wo["blocker_codes"])
        wo.update(fields)

    by_content = aggregate_by_content(work_orders)

    matrix_text = render_matrix_md(by_content)
    userinput_text = render_user_input_md()

    ok, qa_lines = run_qa(work_orders, {"matrix": matrix_text, "user_input": userinput_text}, by_content=by_content)

    OUT_WORKORDERS_JSON.write_text(
        json.dumps({"version": "content_portfolio_v1.4.1", "count": len(work_orders), "work_orders": work_orders}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    OUT_MATRIX_MD.write_text(matrix_text, encoding="utf-8")
    OUT_USERINPUT_MD.write_text(userinput_text, encoding="utf-8")
    OUT_QA_MD.write_text(
        "\n".join(["# QA Report V1.4.1 -- Release Boundary Correction", "", f"Overall: {'PASS' if ok else 'FAIL'}", ""] + [f"- {l}" for l in qa_lines]),
        encoding="utf-8",
    )

    print("QA_V1_4_1_OK:", ok)
    for l in qa_lines:
        print(l)


if __name__ == "__main__":
    main()
