import ipaddress
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from PIL import Image, UnidentifiedImageError


class EvidenceInputValidator:
    """Offline structural validator for user-supplied CardNews evidence manifests."""

    RENDER_ALLOWED_COPYRIGHT_STATUSES = {
        "owned",
        "licensed",
        "public_domain",
        "official_reuse_allowed",
        "user_supplied_with_permission",
        "permission_granted",
    }
    PERMISSION_EVIDENCE_TYPES = {
        "license_url",
        "written_permission",
        "ownership_record",
        "public_domain_record",
        "official_reuse_policy",
    }
    PERMISSION_REVIEW_STATUS = "approved"
    COPYRIGHT_PERMISSION_TYPE_MAP = {
        "owned": {"ownership_record"},
        "licensed": {"license_url"},
        "public_domain": {"public_domain_record"},
        "official_reuse_allowed": {"official_reuse_policy"},
        "user_supplied_with_permission": {"written_permission"},
        "permission_granted": {"written_permission"},
    }
    TOPIC_REVIEW_STATUS = "confirmed"
    ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
    RELEVANCE_THRESHOLD = 0.34
    MIN_MATCHED_TERMS = 2
    DEFAULT_MAX_AGE_DAYS = 30

    def __init__(self, repository_root: Path = Path("."), max_age_days: int = DEFAULT_MAX_AGE_DAYS):
        self.repository_root = Path(repository_root).resolve()
        self.max_age_days = max(0, int(max_age_days))

    def validate(self, manifest: Any, reference_time: Optional[datetime] = None) -> Dict[str, Any]:
        now = self._normalize_reference_time(reference_time)
        issues: List[Dict[str, Any]] = []

        if not isinstance(manifest, dict):
            issues.append(self._issue("manifest_invalid", "Manifest root must be an object."))
            return self._result([], issues)

        requested_topic_terms = self._normalize_terms(manifest.get("topic_terms"))
        if len(requested_topic_terms) < self.MIN_MATCHED_TERMS:
            issues.append(self._issue(
                "topic_terms_missing",
                "Manifest must provide at least two meaningful topic terms.",
            ))

        assets = manifest.get("assets")
        if not isinstance(assets, list) or not assets:
            issues.append(self._issue("assets_missing", "Manifest must contain at least one image asset."))
            return self._result([], issues)

        validated_assets = [
            self._validate_asset(index, asset, requested_topic_terms, now, issues)
            for index, asset in enumerate(assets)
        ]
        return self._result(validated_assets, issues)

    def _validate_asset(
        self,
        index: int,
        asset: Any,
        requested_topic_terms: Set[str],
        now: datetime,
        issues: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prefix = f"assets[{index}]"
        if not isinstance(asset, dict):
            issues.append(self._issue("asset_invalid", "Asset must be an object.", prefix))
            return {"index": index, "valid": False, "asset_path": None}

        issue_count_before = len(issues)
        source_url = str(asset.get("source_url", "")).strip()
        source_url_valid, source_url_risk = self._assess_public_url(source_url)
        if not source_url_valid:
            issues.append(self._issue(
                "source_url_invalid",
                "source_url must be a credential-free public HTTP(S) URL.",
                f"{prefix}.source_url",
            ))

        source_name = str(asset.get("source_name", "")).strip()
        if not source_name:
            issues.append(self._issue(
                "source_name_missing", "source_name is required.", f"{prefix}.source_name"
            ))

        captured_at, captured_at_text = self._parse_datetime(asset.get("captured_at"))
        if captured_at is None:
            issues.append(self._issue(
                "captured_at_invalid",
                "captured_at must be an ISO-8601 datetime with an explicit timezone.",
                f"{prefix}.captured_at",
            ))
        else:
            age_days = (now - captured_at).total_seconds() / 86400
            if age_days < 0:
                issues.append(self._issue(
                    "captured_at_future", "captured_at cannot be in the future.", f"{prefix}.captured_at"
                ))
            elif age_days > self.max_age_days:
                issues.append(self._issue(
                    "evidence_stale",
                    f"Evidence is older than the allowed {self.max_age_days} days.",
                    f"{prefix}.captured_at",
                ))

        relative_path, resolved_path = self._validate_asset_path(asset.get("asset_path"), prefix, issues)

        copyright_status = str(asset.get("copyright_status", "")).strip()
        if copyright_status not in self.RENDER_ALLOWED_COPYRIGHT_STATUSES:
            issues.append(self._issue(
                "rights_not_renderable",
                "copyright_status is missing or not approved for rendering.",
                f"{prefix}.copyright_status",
            ))

        permission_evidence = self._validate_permission_evidence(
            asset.get("permission_evidence"), copyright_status, relative_path, now, prefix, issues
        )

        asset_role = str(asset.get("asset_role", "")).strip()
        if asset_role != "topic_evidence":
            issues.append(self._issue(
                "asset_role_invalid",
                "Only asset_role=topic_evidence can pass this input contract.",
                f"{prefix}.asset_role",
            ))

        asset_terms = self._normalize_terms(asset.get("topic_terms"))
        relevance = self._score_relevance(asset_terms, requested_topic_terms)
        if not relevance["topic_match_candidate"]:
            issues.append(self._issue(
                "topic_mismatch",
                (
                    f"Topic matching requires at least {self.MIN_MATCHED_TERMS} terms "
                    f"and score >= {self.RELEVANCE_THRESHOLD}."
                ),
                f"{prefix}.topic_terms",
            ))

        topic_relevance_note = str(asset.get("topic_relevance_note", "")).strip()
        if not topic_relevance_note:
            issues.append(self._issue(
                "topic_relevance_note_missing",
                "A human-readable topic relevance note is required.",
                f"{prefix}.topic_relevance_note",
            ))

        topic_review = self._validate_topic_review(asset.get("topic_relevance_review"), now, prefix, issues)

        attribution_value = asset.get("attribution_required")
        attribution_required = attribution_value if isinstance(attribution_value, bool) else None
        if attribution_required is None:
            issues.append(self._issue(
                "attribution_required_invalid",
                "attribution_required must be an explicit boolean.",
                f"{prefix}.attribution_required",
            ))
        attribution_text = str(asset.get("attribution_text", "")).strip()
        if attribution_required is True and not attribution_text:
            issues.append(self._issue(
                "attribution_missing",
                "attribution_text is required when attribution_required=true.",
                f"{prefix}.attribution_text",
            ))

        return {
            "index": index,
            "valid": len(issues) == issue_count_before,
            "asset_path": relative_path,
            "asset_decoded": resolved_path is not None and self._image_decodes(resolved_path),
            # Invalid URLs are omitted so credentials or internal endpoints never
            # survive in downstream diagnostics/provenance output.
            "source_url": source_url if source_url_valid else "",
            "source_url_risk": source_url_risk,
            "source_name": source_name,
            "captured_at": captured_at_text,
            "copyright_status": copyright_status,
            "permission_evidence": permission_evidence,
            "asset_role": asset_role,
            "topic_terms": sorted(asset_terms),
            "topic_relevance_note": topic_relevance_note,
            "topic_match_candidate": relevance["topic_match_candidate"],
            "topic_relevance_score": relevance["score"],
            "matched_topic_terms": relevance["matched_terms"],
            "topic_relevance_review": topic_review,
            "topic_relevance_manually_confirmed": topic_review.get("status") == self.TOPIC_REVIEW_STATUS,
            "attribution_required": attribution_required,
            "attribution_text": attribution_text,
        }

    def _validate_asset_path(
        self, path_value: Any, prefix: str, issues: List[Dict[str, Any]]
    ) -> Tuple[Optional[str], Optional[Path]]:
        if not isinstance(path_value, str) or not path_value.strip():
            issues.append(self._issue("asset_path_missing", "asset_path is required.", f"{prefix}.asset_path"))
            return None, None

        candidate = Path(path_value.strip())
        if not candidate.is_absolute():
            candidate = self.repository_root / candidate
        try:
            resolved = candidate.resolve(strict=False)
            relative = resolved.relative_to(self.repository_root)
        except (OSError, ValueError):
            issues.append(self._issue(
                "asset_path_outside_repository",
                "asset_path must stay inside the repository root.",
                f"{prefix}.asset_path",
            ))
            return None, None

        relative_text = relative.as_posix()
        if resolved.suffix.lower() not in self.ALLOWED_IMAGE_EXTENSIONS:
            issues.append(self._issue(
                "asset_extension_not_allowed",
                "asset_path must use an allowed image extension.",
                f"{prefix}.asset_path",
            ))
            return relative_text, None
        if not resolved.is_file():
            issues.append(self._issue(
                "asset_file_missing",
                "The local asset does not exist or is not a file.",
                f"{prefix}.asset_path",
            ))
            return relative_text, None
        if not self._image_decodes(resolved):
            issues.append(self._issue(
                "asset_image_invalid",
                "The local asset is not a decodable, non-corrupt image.",
                f"{prefix}.asset_path",
            ))
            return relative_text, None
        return relative_text, resolved

    def _validate_permission_evidence(
        self,
        value: Any,
        copyright_status: str,
        asset_path: Optional[str],
        now: datetime,
        prefix: str,
        issues: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        if not isinstance(value, dict):
            issues.append(self._issue(
                "permission_evidence_invalid",
                "permission_evidence must be a structured object.",
                f"{prefix}.permission_evidence",
            ))
            return {}

        evidence_type = str(value.get("type", "")).strip()
        reference = str(value.get("reference", "")).strip()
        reference_valid = False
        review_status = str(value.get("review_status", "")).strip()
        reviewed_at, reviewed_at_text = self._parse_datetime(value.get("reviewed_at"))
        linked_asset = str(value.get("asset_path", "")).strip().replace("\\", "/")

        if evidence_type not in self.PERMISSION_EVIDENCE_TYPES:
            issues.append(self._issue(
                "permission_type_invalid",
                "permission evidence type is not supported.",
                f"{prefix}.permission_evidence.type",
            ))
        allowed_types = self.COPYRIGHT_PERMISSION_TYPE_MAP.get(copyright_status, set())
        if evidence_type not in allowed_types:
            issues.append(self._issue(
                "permission_type_mismatch",
                (
                    f"permission evidence type '{evidence_type}' is not valid for "
                    f"copyright_status '{copyright_status}'."
                ),
                f"{prefix}.permission_evidence.type",
            ))
        if not reference:
            issues.append(self._issue(
                "permission_reference_missing",
                "permission evidence reference is required.",
                f"{prefix}.permission_evidence.reference",
            ))
        elif evidence_type in {"license_url", "public_domain_record", "official_reuse_policy"}:
            reference_valid = self._valid_public_url(reference)
            if not reference_valid:
                issues.append(self._issue(
                    "permission_reference_invalid",
                    "URL-based permission references must be public, credential-free HTTP(S) URLs.",
                    f"{prefix}.permission_evidence.reference",
                ))
        elif evidence_type in {"written_permission", "ownership_record"}:
            reference_valid = self._valid_local_permission_reference(reference)
            if not reference_valid:
                issues.append(self._issue(
                    "permission_reference_invalid",
                    "Local permission references must identify an existing file inside the repository.",
                    f"{prefix}.permission_evidence.reference",
                ))
        if review_status != self.PERMISSION_REVIEW_STATUS:
            issues.append(self._issue(
                "permission_review_not_approved",
                "permission evidence must have review_status=approved.",
                f"{prefix}.permission_evidence.review_status",
            ))
        if reviewed_at is None:
            issues.append(self._issue(
                "permission_reviewed_at_invalid",
                "permission evidence reviewed_at requires an ISO-8601 datetime with timezone.",
                f"{prefix}.permission_evidence.reviewed_at",
            ))
        elif reviewed_at > now:
            issues.append(self._issue(
                "permission_reviewed_at_future",
                "permission evidence reviewed_at cannot be in the future.",
                f"{prefix}.permission_evidence.reviewed_at",
            ))
        if not asset_path or linked_asset != asset_path:
            issues.append(self._issue(
                "permission_asset_mismatch",
                "permission evidence must reference the same repository-relative asset_path.",
                f"{prefix}.permission_evidence.asset_path",
            ))

        return {
            "type": evidence_type,
            # Invalid references are omitted rather than echoed. This is
            # especially important for credential-bearing URLs.
            "reference": reference if reference_valid else "",
            "review_status": review_status,
            "reviewed_at": reviewed_at_text,
            "asset_path": linked_asset,
        }

    def _valid_local_permission_reference(self, value: str) -> bool:
        if not value:
            return False
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = self.repository_root / candidate
        try:
            resolved = candidate.resolve(strict=False)
            resolved.relative_to(self.repository_root)
        except (OSError, ValueError):
            return False
        return resolved.is_file()

    def _validate_topic_review(
        self, value: Any, now: datetime, prefix: str, issues: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        if not isinstance(value, dict):
            issues.append(self._issue(
                "topic_review_missing",
                "topic_relevance_review must be a structured manual review record.",
                f"{prefix}.topic_relevance_review",
            ))
            return {}
        status = str(value.get("status", "")).strip()
        reviewed_by = str(value.get("reviewed_by", "")).strip()
        reviewed_at, reviewed_at_text = self._parse_datetime(value.get("reviewed_at"))
        if status != self.TOPIC_REVIEW_STATUS:
            issues.append(self._issue(
                "topic_review_not_confirmed",
                "topic relevance requires status=confirmed manual review.",
                f"{prefix}.topic_relevance_review.status",
            ))
        if not reviewed_by:
            issues.append(self._issue(
                "topic_reviewer_missing",
                "topic relevance review must identify the reviewer.",
                f"{prefix}.topic_relevance_review.reviewed_by",
            ))
        if reviewed_at is None:
            issues.append(self._issue(
                "topic_reviewed_at_invalid",
                "topic relevance reviewed_at requires an ISO-8601 datetime with timezone.",
                f"{prefix}.topic_relevance_review.reviewed_at",
            ))
        elif reviewed_at > now:
            issues.append(self._issue(
                "topic_reviewed_at_future",
                "topic relevance reviewed_at cannot be in the future.",
                f"{prefix}.topic_relevance_review.reviewed_at",
            ))
        return {"status": status, "reviewed_by": reviewed_by, "reviewed_at": reviewed_at_text}

    def _score_relevance(self, asset_terms: Set[str], topic_terms: Set[str]) -> Dict[str, Any]:
        if not asset_terms or not topic_terms:
            return {"score": 0.0, "matched_terms": [], "topic_match_candidate": False}
        matched_terms = sorted(asset_terms & topic_terms)
        score = round(len(matched_terms) / max(1, min(len(asset_terms), len(topic_terms))), 4)
        return {
            "score": min(1.0, score),
            "matched_terms": matched_terms,
            "topic_match_candidate": (
                len(matched_terms) >= self.MIN_MATCHED_TERMS and score >= self.RELEVANCE_THRESHOLD
            ),
        }

    def _result(self, assets: List[Dict[str, Any]], issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        input_valid = bool(assets) and not issues and all(asset.get("valid") for asset in assets)
        return {
            "status": "evidence_input_structurally_valid" if input_valid else "manual_review_required",
            "input_valid": input_valid,
            "eligible_for_manual_integration": input_valid,
            "validated_asset_count": sum(1 for asset in assets if asset.get("valid")),
            "assets": assets,
            "issues": issues,
            "manual_image_required": True,
            "publishing_ready": False,
            "real_image_gate": {
                "satisfied": False,
                "required_action": (
                    "Render an approved local asset into CardNews, then verify "
                    "real_image_used_count > 0 in the normal workflow."
                ),
            },
            "network_used": False,
            "hostname_risk_policy": {
                "dns_resolution_performed": False,
                "hostname_status_without_dns": "UNKNOWN",
                "blocked_literal_ip_ranges": [
                    "private", "loopback", "link_local", "reserved", "unspecified"
                ],
                "note": (
                    "Domain hostnames are not resolved offline; their network destination remains UNKNOWN "
                    "until manual source verification."
                ),
            },
            "source_verification_pending": True,
            "manual_approval_required": True,
            "manual_approval_checklist": [
                "Open each public source URL and compare it with the submitted provenance.",
                "Confirm rights evidence and its link to the exact local asset.",
                "Confirm topic relevance from the source content, not submitted keywords alone.",
                "Inspect the decoded image and required attribution before rendering.",
                "After rendering, verify real_image_used_count > 0 and rerun normal QA.",
            ],
        }

    @staticmethod
    def _image_decodes(path: Path) -> bool:
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                image.load()
            return True
        except (OSError, ValueError, UnidentifiedImageError):
            return False

    @staticmethod
    def _assess_public_url(value: str) -> Tuple[bool, Dict[str, str]]:
        try:
            parsed = urlparse(value)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                return False, {"status": "BLOCKED", "reason": "invalid_scheme_or_hostname"}
            if parsed.username is not None or parsed.password is not None:
                return False, {"status": "BLOCKED", "reason": "credentials_present"}
            hostname = parsed.hostname.rstrip(".").lower()
            if hostname == "localhost" or hostname.endswith(".localhost"):
                return False, {"status": "BLOCKED", "reason": "localhost"}
            try:
                address = ipaddress.ip_address(hostname)
            except ValueError:
                return True, {
                    "status": "UNKNOWN",
                    "reason": "dns_not_resolved_offline",
                    "hostname": hostname,
                }
            blocked = (
                address.is_private
                or address.is_loopback
                or address.is_link_local
                or address.is_reserved
                or address.is_unspecified
            )
            return (
                not blocked,
                {
                    "status": "BLOCKED" if blocked else "PUBLIC_IP",
                    "reason": "non_public_ip_literal" if blocked else "public_ip_literal",
                    "hostname": hostname,
                },
            )
        except (ValueError, UnicodeError):
            return False, {"status": "BLOCKED", "reason": "url_parse_error"}

    @classmethod
    def _valid_public_url(cls, value: str) -> bool:
        valid, _risk = cls._assess_public_url(value)
        return valid

    @staticmethod
    def _parse_datetime(value: Any) -> Tuple[Optional[datetime], str]:
        if not isinstance(value, str) or not value.strip():
            return None, ""
        original = value.strip()
        normalized = original.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None, original
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None, original
        return parsed.astimezone(timezone.utc), original

    @staticmethod
    def _normalize_reference_time(value: Optional[datetime]) -> datetime:
        reference = value or datetime.now(timezone.utc)
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)
        return reference.astimezone(timezone.utc)

    @staticmethod
    def _normalize_terms(value: Any) -> Set[str]:
        values = value if isinstance(value, list) else []
        terms: Set[str] = set()
        for item in values:
            if not isinstance(item, str):
                continue
            cleaned = re.sub(r"[#\.\,\!\?\"'\(\)\[\]:;]", " ", item.lower())
            terms.update(token for token in cleaned.split() if len(token) >= 2)
        return terms

    @staticmethod
    def _issue(code: str, message: str, field: str = "") -> Dict[str, str]:
        return {"code": code, "message": message, "field": field}
