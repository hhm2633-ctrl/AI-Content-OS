import json
import os
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image

from modules.base_module import BaseModule
from modules.card_news.canvas_contract import (
    is_allowed_card_canvas_size,
    is_allowed_card_slide_count,
)


def _valid_card_png_set(paths: List[str], reject_run_paths: bool = False) -> bool:
    if not is_allowed_card_slide_count(len(paths)) or len(set(paths)) != len(paths):
        return False
    for value in paths:
        path = Path(value)
        if (
            not value
            or (reject_run_paths and any(part.lower() == ".runs" for part in path.parts))
            or not path.is_file()
        ):
            return False
        try:
            if path.stat().st_size <= 0 or path.suffix.lower() != ".png":
                return False
            with Image.open(path) as image:
                if not is_allowed_card_canvas_size(image.size) or image.format != "PNG":
                    return False
                image.verify()
        except (OSError, ValueError):
            return False
    return True


def rebind_committed_paths(
    publishing_result: Dict[str, Any],
    committed_card_paths: List[str],
    output_set_id: str,
    publish_queue_target: Any = None,
) -> Dict[str, Any]:
    """Return a copy rebound to durable card paths; never mutate the input.

    This small public adapter is intended for the atomic promote boundary.  A
    failed validation returns a safely blocked copy and never exposes the
    proposed paths as upload-ready.
    """
    rebound = deepcopy(publishing_result) if isinstance(publishing_result, dict) else {}
    paths = [str(path).strip() for path in committed_card_paths] if isinstance(committed_card_paths, list) else []
    normalized_id = str(output_set_id).strip() if output_set_id is not None else ""
    existing_id = str(rebound.get("output_set_id", "")).strip()
    blockers = list(rebound.get("blocker_codes", [])) if isinstance(rebound.get("blocker_codes"), list) else []
    readiness_checks = rebound.get("readiness_checks", {}) if isinstance(rebound.get("readiness_checks"), dict) else {}
    required_readiness_checks = (
        "attestation_schema_valid",
        "card_count_within_allowed_range",
        "exactly_four_cards",
        "card_files_exist",
        "manifest_paths_match",
        "output_set_match",
        "rights_passed",
        "evidence_passed",
        "compliance_passed",
        "qa_passed",
        "manual_image_clear",
        "upload_mode_manual",
    )
    attestation_invalid = any(
        readiness_checks.get(key) is not True
        for key in required_readiness_checks
    )

    invalid_paths = not _valid_card_png_set(paths, reject_run_paths=True)
    identity_invalid = not normalized_id or (bool(existing_id) and existing_id != normalized_id)
    if invalid_paths:
        blockers.append("PUBLISH_COMMITTED_PATHS_INVALID")
    if identity_invalid:
        blockers.append("PUBLISH_COMMITTED_OUTPUT_SET_MISMATCH")
    if attestation_invalid:
        blockers.append("PUBLISH_COMMITTED_ATTESTATION_INVALID")
    blockers = list(dict.fromkeys(blockers))

    committed_parents = (
        {Path(value).resolve().parent for value in paths}
        if not invalid_paths else set()
    )
    committed_parent = next(iter(committed_parents)) if len(committed_parents) == 1 else None
    target = (
        Path(publish_queue_target)
        if publish_queue_target is not None
        else committed_parent / "09_publish_queue.json"
        if committed_parent is not None
        else None
    )
    target_resolved = target.resolve(strict=False) if target is not None else None
    target_invalid = (
        target is None
        or committed_parent is None
        or target_resolved.parent != committed_parent
        or any(part.lower() == ".runs" for part in target_resolved.parts)
        or target_resolved.name.lower() not in ("publish_queue.json", "09_publish_queue.json")
        or (target.exists() and target.is_symlink())
    )
    if target_invalid:
        blockers.append("PUBLISH_COMMITTED_QUEUE_TARGET_INVALID")
        blockers = list(dict.fromkeys(blockers))

    rebound["actual_publish"] = False
    if invalid_paths or identity_invalid or attestation_invalid or target_invalid:
        rebound["package_ready"] = False
        rebound["publishing_ready"] = False
        rebound["status"] = "publishing_blocked"
        rebound["blocker_codes"] = blockers
        package = rebound.get("operator_upload_package")
        if isinstance(package, dict):
            package["status"] = "blocked"
            package["actual_publish"] = False
            package["blocker_codes"] = blockers
            package.pop("publish_queue_path", None)
        rebound.pop("publish_queue_path", None)
        queue = rebound.get("publish_queue")
        if isinstance(queue, dict):
            queue["status"] = "queue_blocked"
            queue["actual_publish"] = False
            queue["blocker_codes"] = blockers
            for item in queue.get("items", []):
                if isinstance(item, dict):
                    item["status"] = "blocked_rebind_failed"
                    item["actual_publish"] = False
                    item["blocker_codes"] = blockers
        return rebound

    rebound["output_set_id"] = normalized_id
    rebound["card_paths"] = paths
    package = rebound.get("operator_upload_package")
    if isinstance(package, dict):
        package["output_set_id"] = normalized_id
        package["ordered_card_paths"] = paths
        package["actual_publish"] = False
    queue = rebound.get("publish_queue")
    if isinstance(queue, dict):
        queue["output_set_id"] = normalized_id
        queue["actual_publish"] = False
        for item in queue.get("items", []):
            if isinstance(item, dict):
                item["card_paths"] = paths
                item["output_set_id"] = normalized_id
                item["actual_publish"] = False
        if blockers or rebound.get("package_ready") is not True:
            queue["status"] = "queue_blocked"
            queue["blocker_codes"] = blockers
            for item in queue.get("items", []):
                if isinstance(item, dict):
                    item["status"] = "blocked_rebind_failed"
                    item["blocker_codes"] = blockers

        queue_binding_valid = (
            queue.get("output_set_id") == normalized_id
            and queue.get("actual_publish") is False
            and isinstance(queue.get("items"), list)
            and bool(queue["items"])
            and all(
                isinstance(item, dict)
                and item.get("output_set_id") == normalized_id
                and item.get("actual_publish") is False
                and item.get("card_paths") == paths
                for item in queue["items"]
            )
        )
        if not queue_binding_valid:
            blockers.append("PUBLISH_COMMITTED_QUEUE_BINDING_INVALID")
            blockers = list(dict.fromkeys(blockers))
            rebound["package_ready"] = False
            rebound["publishing_ready"] = False
            rebound["status"] = "publishing_blocked"
            rebound["blocker_codes"] = blockers
            queue["status"] = "queue_blocked"
            queue["blocker_codes"] = blockers
            if isinstance(package, dict):
                package["status"] = "blocked"
                package["blocker_codes"] = blockers

        if target is not None and queue_binding_valid:
            temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(temporary, "w", encoding="utf-8") as file:
                    json.dump(queue, file, ensure_ascii=False, indent=2)
                    file.flush()
                    os.fsync(file.fileno())
                os.replace(temporary, target)
            except OSError:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
                blockers.append("PUBLISH_COMMITTED_QUEUE_PERSIST_FAILED")
                blockers = list(dict.fromkeys(blockers))
                rebound["package_ready"] = False
                rebound["publishing_ready"] = False
                rebound["status"] = "publishing_blocked"
                rebound["blocker_codes"] = blockers
                queue["status"] = "queue_blocked"
                queue["blocker_codes"] = blockers
                if isinstance(package, dict):
                    package["status"] = "blocked"
                    package["blocker_codes"] = blockers
                    package.pop("publish_queue_path", None)
                rebound.pop("publish_queue_path", None)
            else:
                rebound["publish_queue_path"] = str(target_resolved)
                if isinstance(package, dict):
                    package["publish_queue_path"] = str(target_resolved)
    else:
        blockers.append("PUBLISH_COMMITTED_QUEUE_BINDING_INVALID")
        blockers = list(dict.fromkeys(blockers))
        rebound["package_ready"] = False
        rebound["publishing_ready"] = False
        rebound["status"] = "publishing_blocked"
        rebound["blocker_codes"] = blockers
        if isinstance(package, dict):
            package["status"] = "blocked"
            package["blocker_codes"] = blockers
    return rebound


class PublishingModule(BaseModule):
    rebind_committed_paths = staticmethod(rebind_committed_paths)
    def __init__(self, config=None):
        super().__init__(config)

        self.config = config or {}
        self.publishing_dir = Path("storage/publishing")
        self.publishing_dir.mkdir(parents=True, exist_ok=True)

        self.publishing_config = self._load_publishing_config()

    def _load_publishing_config(self) -> Dict[str, Any]:
        config_path = Path("config/publishing.json")

        if not config_path.exists():
            return self._fallback_publishing_config()

        try:
            with open(config_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return self._fallback_publishing_config()

    def _fallback_publishing_config(self) -> Dict[str, Any]:
        return {
            "platform": "instagram",
            "upload_mode": "manual",
            "default_account": "account_01",
            "accounts": [
                {
                    "account_id": "account_01",
                    "account_name": "AI 카드뉴스 계정",
                    "enabled": True
                }
            ],
            "schedule": {
                "enabled": False,
                "default_time": "09:00"
            },
            "hashtags": [
                "#AI",
                "#자동화",
                "#콘텐츠자동화",
                "#카드뉴스",
                "#인스타그램",
                "#부업",
                "#수익화"
            ]
        }

    def _extract_card_paths(self, card_news_result: Dict[str, Any]) -> List[str]:
        card_paths = []

        if isinstance(card_news_result, dict):
            cards = card_news_result.get("cards", [])

            if isinstance(cards, list):
                for item in cards:
                    if isinstance(item, dict):
                        card_path = item.get("card_path")

                        if card_path:
                            card_paths.append(card_path)

        return card_paths

    def _extract_title(self, card_news_result: Dict[str, Any]) -> str:
        if isinstance(card_news_result, dict):
            title = card_news_result.get("title")

            if title:
                return str(title)

        return "오늘의 AI 카드뉴스"

    def _create_caption(self, title: str) -> str:
        caption = (
            f"{title}\n\n"
            "AI-Content-OS가 자동으로 생성한 카드뉴스입니다.\n\n"
            "저장해두고 하나씩 따라가면 콘텐츠 자동화 흐름을 이해할 수 있습니다.\n\n"
            "더 좋은 자동화 구조를 계속 테스트하고 개선합니다."
        )

        return caption

    def _create_hashtags(self) -> List[str]:
        hashtags = self.publishing_config.get("hashtags", [])

        if not hashtags:
            hashtags = [
                "#AI",
                "#자동화",
                "#콘텐츠자동화",
                "#카드뉴스",
                "#인스타그램",
                "#부업",
                "#수익화"
            ]

        clean_hashtags = []

        for tag in hashtags:
            tag = str(tag).strip()

            if not tag:
                continue

            if not tag.startswith("#"):
                tag = "#" + tag

            clean_hashtags.append(tag)

        return clean_hashtags[:20]

    def _create_full_caption(self, caption: str, hashtags: List[str]) -> str:
        return caption + "\n\n" + " ".join(hashtags)

    def _normalize_output_set_id(self, value: Any) -> str:
        return str(value).strip() if value is not None else ""

    def _resolve_release_manifest(self, card_news_result: Dict[str, Any]) -> Dict[str, Any]:
        """Return an explicitly supplied CardNews release manifest, if present.

        The normal WorkflowEngine call predates the release-manifest handoff, so that
        path remains supported.  A post-QA handoff can attach the manifest under any
        of the documented adapter keys without changing the common engine.
        """
        if not isinstance(card_news_result, dict):
            return {}
        for key in ("pre_publish_attestation", "result_manifest", "manifest", "card_news_manifest"):
            value = card_news_result.get(key)
            if isinstance(value, dict):
                return value
        return {}

    def _resolve_package_readiness(
        self,
        card_news_result: Dict[str, Any],
        card_paths: List[str],
        operations: Dict[str, Any],
    ) -> Dict[str, Any]:
        manifest = self._resolve_release_manifest(card_news_result)
        output_set_id = self._normalize_output_set_id(card_news_result.get("output_set_id"))
        manifest_cards = manifest.get("cards") if isinstance(manifest.get("cards"), list) else []
        manifest_paths = [
            str(item.get("path") or item.get("card_path") or "").strip()
            for item in manifest_cards if isinstance(item, dict)
        ]
        is_gate_attestation = manifest.get("schema_version") == "pre_publish_attestation.v1"
        is_canonical_attestation = (
            manifest.get("contract") == "card_news_pre_publish_attestation_v1"
            and manifest.get("schema_version") == 1
        )
        attestation_schema_valid = is_gate_attestation or is_canonical_attestation
        if is_gate_attestation and not manifest_paths:
            # Paths are bound by the CardNews result/output_set; the compliance
            # attestation independently binds the approved asset identities.
            manifest_paths = list(card_paths)
        identity = manifest.get("output_set_identity", {}) if manifest else {}
        attestation_output_set_id = self._normalize_output_set_id(manifest.get("output_set_id"))
        if not attestation_output_set_id:
            legacy_ids = identity.get("ids", {}) if isinstance(identity.get("ids"), dict) else {}
            # Publishing's own result identity is deliberately excluded: it does
            # not exist until this module finishes.
            upstream_ids = [
                self._normalize_output_set_id(legacy_ids.get(key))
                for key in ("card_news_result", "quality")
            ]
            upstream_ids = [value for value in upstream_ids if value]
            if upstream_ids and len(set(upstream_ids)) == 1:
                attestation_output_set_id = upstream_ids[0]
        card_count_within_allowed_range = is_allowed_card_slide_count(len(card_paths))
        card_files_exist = _valid_card_png_set(card_paths)
        manifest_paths_match = len(manifest_paths) == len(card_paths) and card_paths == manifest_paths
        output_set_present = bool(output_set_id) and bool(attestation_output_set_id)
        output_set_match = output_set_present and output_set_id == attestation_output_set_id
        approved_assets = manifest.get("assets", []) if is_gate_attestation and isinstance(manifest.get("assets"), list) else []
        rendered_scope_declared = "rendered_asset_ids" in manifest if manifest else False
        rendered_asset_ids = {
            str(value).strip()
            for value in manifest.get("rendered_asset_ids", manifest.get("asset_ids", []))
            if str(value).strip()
        } if manifest else set()
        render_allowed_asset_ids = {
            str(value).strip()
            for value in manifest.get("render_allowed_asset_ids", [])
            if str(value).strip()
        } if manifest else set()
        rendered_asset_rights_match = (
            not rendered_scope_declared
            or (
                bool(rendered_asset_ids)
                and rendered_asset_ids.issubset(render_allowed_asset_ids)
            )
        )
        rights = manifest.get("rights", {}) if manifest else {}
        rights_passed = (
            bool(approved_assets)
            and all(item.get("render_allowed") is True and item.get("rights_status") not in ("", "blocked") for item in approved_assets)
        ) if is_gate_attestation else (
            rights.get("ready") is True
            and rights.get("status") == "pass"
            and rendered_asset_rights_match
        )
        evidence_status = manifest.get("evidence", {}).get("status") if manifest else None
        evidence_passed = (
            bool(approved_assets) and all(item.get("evidence_status") == "valid" for item in approved_assets)
        ) if is_gate_attestation else evidence_status in ("applied", "unavailable")
        quality_source = card_news_result.get("quality", {}) if isinstance(card_news_result.get("quality"), dict) else {}
        quality = quality_source or (manifest.get("quality") if isinstance(manifest.get("quality"), dict) else manifest.get("qa", {}))
        qa_passed = quality.get("passed") is True if manifest else False
        release_guard = manifest.get("release_guard", {}) if manifest else {}
        compliance = manifest.get("compliance_result", {}) if manifest else {}
        issue_codes = release_guard.get("issue_codes", []) if isinstance(release_guard.get("issue_codes"), list) else []
        technical_fixture_blocked = (
            manifest.get("technical_fixture_not_publish_approved") is True
            or
            compliance.get("status") == "technical_fixture_not_publish_approved"
            or "technical_fixture_not_publish_approved" in compliance.get("blocking_reasons", [])
            or "technical_fixture_not_publish_approved" in issue_codes
        )
        canonical_compliance_blocked = is_canonical_attestation and (
            compliance.get("status") != "valid"
            or compliance.get("publish_ready") is not True
            or bool(compliance.get("blocking_reasons"))
            or release_guard.get("ready") is not True
            or not rendered_asset_rights_match
        )
        if canonical_compliance_blocked:
            # The canonical compliance decision is authoritative.  Optimistic
            # outer rights/evidence fields must never reopen a blocked gate.
            rights_passed = False
            evidence_passed = False
        compliance_passed = (
            is_gate_attestation
            and manifest.get("publish_ready") is True
            and manifest.get("blockers") == []
            and bool(manifest.get("asset_ids"))
            and set(manifest.get("asset_ids", [])) == set(manifest.get("render_allowed_asset_ids", []))
            and all(item.get("classification") != "technical_fixture" for item in approved_assets)
        ) or (
            compliance.get("schema_version") == "card_news_compliance.v1"
            and bool(str(compliance.get("package_id", "")).strip())
            and compliance.get("status") == "valid"
            and compliance.get("publish_ready") is True
            and compliance.get("blocking_reasons") == []
            and release_guard.get("ready") is True
            and not technical_fixture_blocked
        )
        compliance_provenance_present = is_gate_attestation or (
            compliance.get("schema_version") == "card_news_compliance.v1"
            and bool(str(compliance.get("package_id", "")).strip())
        )
        manual_image_clear = not operations["publishing_blocked"] if manifest else False
        upload_mode_manual = self.publishing_config.get("upload_mode", "manual") == "manual"
        checks = {
            "attestation_schema_valid": attestation_schema_valid,
            "exactly_four_cards": card_count_within_allowed_range,
            "card_count_within_allowed_range": card_count_within_allowed_range,
            "card_files_exist": card_files_exist,
            "manifest_paths_match": manifest_paths_match,
            "output_set_match": output_set_match,
            "rights_passed": rights_passed,
            "rendered_asset_rights_match": rendered_asset_rights_match,
            "evidence_passed": evidence_passed,
            "compliance_passed": compliance_passed,
            "qa_passed": qa_passed,
            "manual_image_clear": manual_image_clear,
            "upload_mode_manual": upload_mode_manual,
        }
        blocking_reasons = []
        if not manifest: blocking_reasons.append("PUBLISH_ATTESTATION_MISSING")
        elif not attestation_schema_valid: blocking_reasons.append("PUBLISH_ATTESTATION_SCHEMA_INVALID")
        if not card_count_within_allowed_range: blocking_reasons.append("PUBLISH_CARD_COUNT_INVALID")
        if not card_files_exist: blocking_reasons.append("PUBLISH_CARD_FILE_MISSING")
        if not manifest_paths_match: blocking_reasons.append("PUBLISH_MANIFEST_PATH_MISMATCH")
        if not output_set_present: blocking_reasons.append("PUBLISH_OUTPUT_SET_MISSING")
        elif not output_set_match: blocking_reasons.append("PUBLISH_OUTPUT_SET_MISMATCH")
        if not rights_passed: blocking_reasons.append("PUBLISH_RIGHTS_BLOCKED")
        if not evidence_passed: blocking_reasons.append("PUBLISH_EVIDENCE_BLOCKED")
        if not compliance_provenance_present:
            blocking_reasons.append("PUBLISH_COMPLIANCE_PROVENANCE_MISSING")
        if not compliance_passed: blocking_reasons.append("PUBLISH_COMPLIANCE_BLOCKED")
        if not qa_passed: blocking_reasons.append("PUBLISH_QA_BLOCKED")
        if not manual_image_clear: blocking_reasons.append("PUBLISH_MANUAL_IMAGE_REQUIRED")
        if not upload_mode_manual: blocking_reasons.append("PUBLISH_UPLOAD_MODE_UNSAFE")
        return {
            "ready": not blocking_reasons,
            "contract": "card_news_pre_publish_attestation_v1",
            "output_set_id": output_set_id,
            "checks": checks,
            "blocking_reasons": blocking_reasons,
        }

    def _create_manual_upload_checklist(self, readiness: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"step": 1, "action": "4개 이미지 파일을 manifest 순서대로 선택", "required": True},
            {"step": 2, "action": "caption과 hashtag를 플랫폼 본문에 붙여넣기", "required": True},
            {"step": 3, "action": "권리·표시 문구와 미리보기를 운영자가 최종 확인", "required": True},
            {
                "step": 4,
                "action": "운영자가 플랫폼에서 직접 업로드",
                "required": True,
                "allowed_now": bool(readiness["ready"]),
            },
        ]

    def _get_default_account(self) -> Dict[str, Any]:
        accounts = self.publishing_config.get("accounts", [])

        if isinstance(accounts, list):
            for account in accounts:
                if account.get("enabled", True):
                    return account

        return {
            "account_id": "account_01",
            "account_name": "AI 카드뉴스 계정",
            "enabled": True
        }

    def _resolve_planner_strategy(self, card_news_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        AI Planner Consumer Adapter 실제 연결(Sprint 15-3): PublishingModule은
        실제 게시 동작(캡션/해시태그/큐 생성 로직)을 전혀 바꾸지 않는다 - 상위
        단계(CardNewsModule)가 이미 요약해 둔 `planner_influence`를 그대로
        복사해 메타데이터로만 기록한다.
        """
        influence = card_news_result.get("planner_influence") if isinstance(card_news_result, dict) else None

        if isinstance(influence, dict) and influence:
            return influence

        return {
            "any_hint_applied": False,
            "content": {},
            "image_strategy": {},
            "reason": "card_news_result에 planner_influence가 없어 기본값을 사용함.",
        }

    def _resolve_image_sourcing_status(self, card_news_result: Dict[str, Any]) -> Dict[str, Any]:
        status = card_news_result.get("image_sourcing_status") if isinstance(card_news_result, dict) else None

        if isinstance(status, dict) and status:
            return status

        return {
            "manual_image_required": False,
            "recommended_source": "",
            "real_image_used_count": 0,
            "checklist": [],
            "reason": "card_news_result에 image_sourcing_status가 없어 수동 이미지 체크리스트를 생략함.",
        }

    def _resolve_publishing_gate(self, image_sourcing_status: Dict[str, Any]) -> Dict[str, Any]:
        manual_image_required = bool(image_sourcing_status.get("manual_image_required", False))

        try:
            real_image_used_count = int(image_sourcing_status.get("real_image_used_count", 0) or 0)
        except (TypeError, ValueError):
            real_image_used_count = 0

        blocking_reasons = []
        if manual_image_required:
            blocking_reasons.append("manual_image_required")
        if real_image_used_count <= 0:
            blocking_reasons.append("real_image_used_count_zero")

        return {
            "publishing_blocked": bool(blocking_reasons),
            "blocking_reasons": blocking_reasons,
            "real_image_used_count": real_image_used_count,
            "required_action": (
                "실제 이미지를 카드뉴스에 반영하고 이미지 체크리스트를 완료하세요."
                if blocking_reasons
                else "카드뉴스 이미지와 캡션을 최종 확인하세요."
            ),
        }

    def _create_publish_queue(
        self,
        title: str,
        card_paths: List[str],
        caption: str,
        hashtags: List[str],
        image_sourcing_status: Dict[str, Any],
        operations: Dict[str, Any],
    ) -> Dict[str, Any]:
        account = self._get_default_account()
        schedule = self.publishing_config.get("schedule", {})
        manual_image_required = bool(image_sourcing_status.get("manual_image_required", False))

        next_action = "카드뉴스 이미지와 캡션을 확인한 뒤 인스타그램에 수동 업로드"
        if operations["publishing_blocked"]:
            next_action = (
                "실제 이미지를 반영하고 image_checklist를 완료한 뒤 발행 준비 상태를 다시 확인"
            )

        queue_item = {
            "queue_id": f"publish_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "platform": self.publishing_config.get("platform", "instagram"),
            "upload_mode": self.publishing_config.get("upload_mode", "manual"),
            "account_id": account.get("account_id", "account_01"),
            "account_name": account.get("account_name", "AI 카드뉴스 계정"),
            "title": title,
            "card_paths": card_paths,
            "caption": caption,
            "hashtags": hashtags,
            "full_caption": self._create_full_caption(caption, hashtags),
            "schedule_enabled": schedule.get("enabled", False),
            "scheduled_time": schedule.get("default_time", "09:00"),
            "status": (
                "blocked_pending_image_sourcing"
                if operations["publishing_blocked"]
                else "ready_for_manual_upload"
            ),
            "manual_image_required": manual_image_required,
            "image_checklist": image_sourcing_status.get("checklist", []),
            "created_at": datetime.now().isoformat(),
            "next_action": next_action,
            "operations": operations,
        }

        return {
            "status": "queue_blocked" if operations["publishing_blocked"] else "queue_ready",
            "output_set_id": "",
            "actual_publish": False,
            "count": 1,
            "items": [queue_item]
        }

    def _save_json(self, path: Path, data: Dict[str, Any]):
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def _save_text(self, path: Path, text: str):
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)

    def run(self, card_news_result: Dict[str, Any]) -> Dict[str, Any]:
        print("Publishing Module Started")

        title = self._extract_title(card_news_result)
        card_paths = self._extract_card_paths(card_news_result)
        caption = self._create_caption(title)
        hashtags = self._create_hashtags()
        full_caption = self._create_full_caption(caption, hashtags)
        image_sourcing_status = self._resolve_image_sourcing_status(card_news_result)
        operations = self._resolve_publishing_gate(image_sourcing_status)
        readiness = self._resolve_package_readiness(card_news_result, card_paths, operations)
        queue_operations = dict(operations)
        queue_operations["publishing_blocked"] = not readiness["ready"]
        queue_operations["blocking_reasons"] = readiness["blocking_reasons"]
        queue_operations["package_ready"] = readiness["ready"]

        publish_queue = self._create_publish_queue(
            title=title,
            card_paths=card_paths,
            caption=caption,
            hashtags=hashtags,
            image_sourcing_status=image_sourcing_status,
            operations=queue_operations,
        )
        publish_queue["output_set_id"] = readiness["output_set_id"]
        for item in publish_queue.get("items", []):
            if isinstance(item, dict):
                item["output_set_id"] = readiness["output_set_id"]
                item["actual_publish"] = False

        manual_image_required = bool(image_sourcing_status.get("manual_image_required", False))
        next_action = "카드뉴스 이미지와 캡션을 확인한 뒤 인스타그램에 수동 업로드"
        if not readiness["ready"]:
            next_action = (
                "실제 이미지를 반영하고 이미지 체크리스트를 완료한 뒤 발행 준비 상태를 다시 확인"
            )

        account = self._get_default_account()
        schedule = self.publishing_config.get("schedule", {})
        operator_upload_package = {
            "status": "ready_for_manual_upload" if readiness["ready"] else "blocked",
            "platform": self.publishing_config.get("platform", "instagram"),
            "upload_mode": "manual",
            "actual_publish": False,
            "output_set_id": readiness["output_set_id"],
            "ordered_card_paths": card_paths,
            "caption": caption,
            "hashtags": hashtags,
            "full_caption": full_caption,
            "manual_upload_checklist": self._create_manual_upload_checklist(readiness),
            "schedule": {
                "enabled": bool(schedule.get("enabled", False)),
                "scheduled_time": schedule.get("default_time", "09:00"),
            },
            "account": {
                "account_id": account.get("account_id", "account_01"),
                "account_name": account.get("account_name", "AI 카드뉴스 계정"),
            },
            "blocker_codes": readiness["blocking_reasons"],
        }

        result = {
            "module": "PublishingModule",
            "status": (
                "publishing_blocked"
                if not readiness["ready"]
                else "publishing_ready"
            ),
            "platform": self.publishing_config.get("platform", "instagram"),
            "upload_mode": self.publishing_config.get("upload_mode", "manual"),
            "actual_publish": False,
            "output_set_id": readiness["output_set_id"],
            "package_ready": readiness["ready"],
            "publishing_ready": readiness["ready"],
            "readiness_checks": readiness["checks"],
            "blocker_codes": readiness["blocking_reasons"],
            "operator_upload_package": operator_upload_package,
            "card_count": len(card_paths),
            "card_paths": card_paths,
            "caption": caption,
            "hashtags": hashtags,
            "full_caption": full_caption,
            "publish_queue_path": "storage/publishing/publish_queue.json",
            "publish_queue": publish_queue,
            "image_sourcing_status": image_sourcing_status,
            "manual_image_required": manual_image_required,
            "operations": operations,
            "next_action": next_action,
            "planner_strategy": self._resolve_planner_strategy(card_news_result),
            "created_at": datetime.now().isoformat()
        }

        self._save_json(self.publishing_dir / "publishing_result.json", result)
        self._save_json(self.publishing_dir / "publish_queue.json", publish_queue)
        self._save_text(self.publishing_dir / "caption.txt", full_caption)
        self._save_text(self.publishing_dir / "hashtags.txt", " ".join(hashtags))

        print(f"Publishing Result Saved: {self.publishing_dir / 'publishing_result.json'}")
        print(f"Publish Queue Saved: {self.publishing_dir / 'publish_queue.json'}")
        print(f"Caption Saved: {self.publishing_dir / 'caption.txt'}")
        print(f"Hashtags Saved: {self.publishing_dir / 'hashtags.txt'}")
        print("Publishing Module Finished")

        return result
