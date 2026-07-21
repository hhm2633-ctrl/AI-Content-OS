from copy import deepcopy
from datetime import datetime, timedelta, timezone
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional

from modules.brand_dna_engine.brand_dna_interface import BrandDNAInterface
from modules.knowledge_engine.knowledge_interface import KnowledgeInterface
from modules.commerce.commerce_storage import CommerceStorage, CommerceStorageError


class CommerceModule:
    """Offline, truth-gated Commerce Phase 1 package generator."""

    VERSION = "commerce_phase_1.1"
    METHODS = {"document", "merchant_input", "manufacturer_source", "marketplace_export", "physical_inspection"}
    SENSITIVE = {"price", "discount", "stock", "shipping", "benefit", "benefits", "efficacy", "effect",
                 "certification", "review", "reviews", "rating", "sales", "sales_count", "ranking", "rank"}
    ALWAYS_VOLATILE = {"price", "discount", "stock", "shipping", "benefit", "benefits", "rating",
                       "sales", "sales_count", "ranking", "rank", "review_count"}
    RIGHTS_FIELDS = {"claim", "claims", "efficacy", "effect", "certification", "review", "reviews", "image", "images"}
    PLATFORM_NOTICE = {
        "smartstore": ("manufacturer", "country_of_origin"),
        "coupang": ("manufacturer", "country_of_origin", "model_name"),
    }
    SUPPORTED_PLATFORMS = ("smartstore", "coupang")
    MAX_FRESHNESS_SECONDS = 31_536_000
    AUTHORITATIVE_METHODS = {"document", "manufacturer_source"}
    AUTHORITATIVE_SOURCE_TYPES = {"document", "official_document", "manufacturer_source", "manufacturer_document", "regulator_document"}
    PROHIBITED_KEYWORD_CLAIMS = (
        "1위", "일위", "베스트셀러", "판매량", "판매수", "누적판매", "랭킹", "순위", "최저가",
        "할인", "세일", "특가", "재고", "품절임박", "효능", "효과", "치료", "예방", "완치",
        "인증", "승인", "certified", "approved", "efficacy", "cure", "treat", "ranking",
        "discount",
        "매출", "구매", "주문폭주", "완판", "품귀", "한정수량", "임상", "검증완료",
        "보장", "개선", "회복", "면역", "항암", "식약처", "fda", "ce인증",
        "bestseller", "판매일등", "가장많이팔린",
    )

    def __init__(self, storage: Optional[CommerceStorage] = None,
                 knowledge_interface: Optional[KnowledgeInterface] = None,
                 brand_dna_interface: Optional[BrandDNAInterface] = None):
        self.storage = storage or CommerceStorage()
        self.knowledge_interface = knowledge_interface or KnowledgeInterface()
        self.brand_dna_interface = brand_dna_interface or BrandDNAInterface()

    def run(self, product_facts: Optional[Dict[str, Any]], content_patterns: Optional[Dict[str, Any]] = None,
            learned_context: Optional[Dict[str, Any]] = None, persist: bool = True) -> Dict[str, Any]:
        raw = deepcopy(product_facts) if isinstance(product_facts, dict) else {}
        request_id = self.storage.normalize_request_id(raw.get("request_id"))
        raw["request_id"] = request_id
        now = datetime.now(timezone.utc)
        requested, platform_issues = self._requested_platforms(raw)
        issue_platforms = requested or list(self.SUPPORTED_PLATFORMS)
        sources, source_issues = self._sources(raw.get("sources"), now, issue_platforms)
        accepted: Dict[str, List[Dict[str, Any]]] = {}
        missing: List[Dict[str, Any]] = []
        blocked: List[Dict[str, Any]] = list(platform_issues) + list(source_issues)
        fact_items = list(self._fact_items(raw))
        conflicts = self._duplicate_conflicts(fact_items)
        for field, item in fact_items:
            display_field = str(item.get("field_id") or field)
            if display_field in conflicts:
                issue = self._reason("conflicting_sources", display_field, item.get("platforms", ["smartstore", "coupang"]),
                                     "error", "Duplicate field_id has conflicting values.", "Select and re-verify one authoritative value.")
                value = None
            else:
                value, issue = self._validate_item(field, item, sources, raw.get("freshness_policy", {}), now)
            if issue:
                blocked.append(issue)
                missing.append(self._missing(field, issue["platforms"], issue["message"], issue["required_action"],
                                             required=field in self.SENSITIVE))
            elif value is not None:
                accepted.setdefault(field, []).append(value)

        required_identity = {
            "brand": "Verified brand is required.",
            "product_name": "Verified product name is required.",
            "seller": "Verified seller is required.",
        }
        for field, message in required_identity.items():
            applicable = {
                platform for entry in accepted.get(field, [])
                for platform in requested
                if platform in entry.get("platforms", ["smartstore", "coupang"])
            }
            missing_platforms = [platform for platform in requested if platform not in applicable]
            if missing_platforms:
                label = f"product.{field}"
                reason = self._reason("missing_required_field", label, missing_platforms, "error", message,
                                      f"Provide {field} as a non-blank, source-backed fact.")
                blocked.append(reason)
                missing.append(self._missing(label, missing_platforms, reason["message"], reason["required_action"]))

        learning = self._load_learning(raw.get("learned_data", {}), learned_context, content_patterns)
        detail = self._detail(raw, accepted)
        packages = {p: self._package(p, raw, accepted, detail, missing, blocked) for p in requested}
        all_missing = self._dedupe(missing + [x for p in packages.values() for x in p["missing_fields"]])
        all_blocked = self._dedupe(blocked + [x for p in packages.values() for x in p["blocked_reasons"]])
        statuses = [p["status"] for p in packages.values()]
        status = "blocked" if not requested or platform_issues or "blocked" in statuses else ("partial" if all_missing else "ready_for_manual_upload")
        result: Dict[str, Any] = {
            "module": "CommerceModule", "version": self.VERSION, "phase": "commerce_phase_1",
            "request_id": request_id, "generated_at": now.isoformat(),
            "status": status, "upload_mode": "manual_only", "auto_upload_performed": False,
            "source_summary": {"provided": len(sources), "valid_source_ids": sorted(sources)},
            "freshness_summary": {"generation_time": now.isoformat(), "policy": deepcopy(raw.get("freshness_policy", {}))},
            "learned_data_metadata": learning, "detail_page": detail, "platform_packages": packages,
            "manual_upload_checklist": self._checklist(requested), "missing_fields": all_missing,
            "blocked_reasons": all_blocked, "output_paths": [],
            "phase_2_gate": {"required": True, "status": "not_approved", "owner": "CTO"},
        }
        if persist:
            try:
                result["output_paths"] = list(self.storage.save(result).values())
            except Exception as error:
                result["status"] = "blocked"
                result["output_paths"] = []
                storage_code = error.code if isinstance(error, CommerceStorageError) else "storage_operation_failed"
                blocker_code = "storage_cleanup_failed" if storage_code == "temporary_cleanup_failed" else "storage_write_failed"
                result["blocked_reasons"].append(self._reason(blocker_code, "storage", requested,
                    "critical", "Commerce artifacts could not be saved atomically.", "Resolve the storage failure and regenerate."))
                result["storage_error"] = {"code": storage_code, "message": "Commerce storage operation failed safely."}
        return result

    def _requested_platforms(self, raw):
        if "target_platforms" not in raw:
            return list(self.SUPPORTED_PLATFORMS), []
        value = raw.get("target_platforms")
        if not isinstance(value, list) or not value or any(not isinstance(p, str) for p in value):
            return [], [self._reason("invalid_target_platforms", "target_platforms", list(self.SUPPORTED_PLATFORMS), "error",
                "Requested platforms must be a non-empty list of supported platform identifiers.", "Request smartstore and/or coupang explicitly.")]
        normalized = list(dict.fromkeys(p.strip().lower() for p in value))
        unsupported = [p for p in normalized if p not in self.SUPPORTED_PLATFORMS]
        if unsupported:
            return [], [self._reason("unsupported_platform", "target_platforms", list(self.SUPPORTED_PLATFORMS), "error",
                "One or more requested platforms are unsupported.", "Request smartstore and/or coupang explicitly.")]
        return normalized, []

    def _sources(self, value: Any, now, issue_platforms):
        valid, issues = {}, []
        seen = set()
        for source in value if isinstance(value, list) else []:
            if not isinstance(source, dict) or not source.get("source_id"):
                continue
            source_id = str(source["source_id"])
            if self._secret_like(source_id):
                issues.append(self._reason("unsafe_source_id", "sources", issue_platforms, "error",
                    "A source identifier contains forbidden secret-like material.", "Replace it with a stable non-secret identifier."))
                continue
            if source_id in seen:
                valid.pop(source_id, None)
                issues.append(self._reason("duplicate_source_id", "sources", issue_platforms, "error",
                    "Duplicate source identifiers are not accepted.", "Provide one unique record per source identifier."))
                continue
            seen.add(source_id)
            required = ("source_type", "source_name", "source_locator", "retrieved_at")
            retrieved = self._parse_time(source.get("retrieved_at"))
            if retrieved is not None and retrieved > now:
                issues.append(self._reason("future_verification_time", "sources.retrieved_at", issue_platforms, "error",
                    "A source retrieval time cannot be in the future.", "Provide the actual completed retrieval time."))
                continue
            if any(self._empty(source.get(k)) for k in required) or retrieved is None:
                issues.append(self._reason("missing_source", "sources", issue_platforms, "error",
                    "A source record is incomplete or has an invalid retrieval time.", "Provide complete source metadata and a non-future timezone timestamp."))
                continue
            if self._empty(source.get("rights_or_permission")) or not self._rights_ok(source.get("rights_or_permission")):
                issues.append(self._reason("missing_source_rights", "sources", issue_platforms, "error",
                    "A source record has no accepted use permission.", "Provide an allowed rights_or_permission value."))
                continue
            valid[source_id] = deepcopy(source)
        return valid, issues

    def _fact_items(self, raw: Dict[str, Any]):
        product = raw.get("product", {}) if isinstance(raw.get("product"), dict) else {}
        for key in ("brand", "manufacturer", "model_name", "category", "product_name", "seller", "country_of_origin"):
            if isinstance(product.get(key), dict): yield key, product[key]
        for key in ("facts", "options", "specifications", "usage", "cautions", "faq"):
            for item in product.get(key, []) if isinstance(product.get(key), list) else []:
                yield key.rstrip("s"), item if isinstance(item, dict) else {"field_id": key, "_malformed": True}
        for key, item in (product.get("notice_information", {}) if isinstance(product.get("notice_information"), dict) else {}).items():
            if isinstance(item, dict): yield f"notice.{key}", item
        for key, item in (raw.get("commercial_facts", {}) or {}).items():
            for entry in item if isinstance(item, list) else [item]:
                if isinstance(entry, dict): yield key, entry
        for key in ("claims", "reviews", "sales_metrics"):
            for item in raw.get(key, []) if isinstance(raw.get(key), list) else []:
                semantic = str(item.get("claim_type") or item.get("metric_type") or key.rstrip("s")) if isinstance(item, dict) else key.rstrip("s")
                yield semantic, item if isinstance(item, dict) else {"field_id": key, "_malformed": True}
        # Backward-compatible fact map, but still requires source_ids and registered sources.
        for key, item in (raw.get("facts", {}) if isinstance(raw.get("facts"), dict) else {}).items():
            if isinstance(item, dict): yield key, item

    def _validate_item(self, field, item, sources, policy, now):
        raw_platforms = item.get("platforms", list(self.SUPPORTED_PLATFORMS))
        if (item.get("_malformed") or not isinstance(raw_platforms, list) or not raw_platforms
                or any(not isinstance(p, str) or p not in self.SUPPORTED_PLATFORMS for p in raw_platforms)):
            return None, self._reason("malformed_input", str(item.get("field_id") or field), list(self.SUPPORTED_PLATFORMS), "error",
                "Fact structure or platform scope is malformed.", "Provide a fact object with a non-empty supported platforms list.")
        platforms = list(dict.fromkeys(raw_platforms))
        output_field = str(item.get("field_id") or field)
        value = item.get("value")
        if self._empty(value): return None, self._reason("missing_required_field", output_field, platforms, "error", "Value is unavailable.", "Supply a verified value.")
        ids = item.get("source_ids") if isinstance(item.get("source_ids"), list) else []
        if not ids or any(str(i) not in sources for i in ids):
            return None, self._reason("missing_source", output_field, platforms, "error", "Fact is not linked to valid source records.", "Provide valid source_ids.")
        method = str(item.get("verification_method") or "")
        if method not in self.METHODS:
            return None, self._reason("missing_verification_method", output_field, platforms, "error", "Verification method is absent or inferred.", "Use an explicit allowed verification_method.")
        verified = self._parse_time(item.get("verified_at"))
        if not verified:
            return None, self._reason("missing_verification_time", output_field, platforms, "error", "Timezone-aware verified_at is required.", "Re-verify and provide timestamp with timezone.")
        if verified > now:
            return None, self._reason("future_verification_time", output_field, platforms, "error", "verified_at cannot be in the future.", "Provide the actual completed verification time.")
        volatile = bool(item.get("volatile")) or field in self.ALWAYS_VOLATILE
        expires = self._parse_time(item.get("expires_at"))
        max_age = self._max_age(field, policy)
        if expires and (expires <= verified or expires <= now):
            return None, self._reason("stale_volatile_fact", output_field, platforms, "error", "Fact expiry is invalid or already elapsed.", "Re-verify and provide a valid expiry after verification.")
        if volatile and not expires and max_age is None:
            return None, self._reason("stale_volatile_fact", output_field, platforms, "error", "Volatile fact has no deterministic lifetime.", "Provide expires_at or freshness_policy max_age.")
        if max_age is not None and max_age > self.MAX_FRESHNESS_SECONDS:
            return None, self._reason("invalid_freshness_policy", output_field, platforms, "error", "Freshness lifetime exceeds the safe maximum.", "Use a maximum age of one year or less.")
        if max_age is not None and verified + timedelta(seconds=max_age) <= now:
            return None, self._reason("stale_volatile_fact", output_field, platforms, "error", "Volatile fact is stale.", "Re-verify immediately before generation.")
        observed = item.get("source_values")
        if item.get("conflict_detected") is True or (isinstance(observed, dict) and len({self._freeze(v) for v in observed.values()}) > 1):
            return None, self._reason("conflicting_sources", output_field, platforms, "error", "Source values conflict.", "Select and re-verify an authoritative source.")
        semantic_field = f"{field}.{output_field}".lower()
        is_review = "review" in semantic_field
        rights_sensitive = field in self.RIGHTS_FIELDS or any(token in semantic_field for token in ("certification", "efficacy", "effect", "claim", "review", "image"))
        if rights_sensitive:
            if any(not self._rights_ok(sources[str(i)].get("rights_or_permission")) for i in ids):
                code = "review_rights_unconfirmed" if is_review else "unsupported_claim"
                return None, self._reason(code, output_field, platforms, "error", "Use permission is not documented.", "Document permission and attribution/disclosure.")
        customer_claim = self._contains_prohibited_customer_claim(value)
        authoritative_claim = any(token in semantic_field for token in ("certification", "efficacy", "effect", "claim"))
        if customer_claim:
            source_types = {str(sources[str(i)].get("source_type", "")).strip().lower() for i in ids}
            if not (authoritative_claim and method in self.AUTHORITATIVE_METHODS
                    and source_types and source_types <= self.AUTHORITATIVE_SOURCE_TYPES):
                return None, self._reason("unsupported_claim", output_field, platforms, "error",
                    "Customer-facing text contains a claim without authoritative verification.", "Remove the claim or verify it with an authoritative document/manufacturer source.")
        if is_review and not (item.get("authenticity_confirmed") is True
                              and (item.get("pii_removed") is True or item.get("contains_pii") is False)
                              and (item.get("attribution_confirmed") is True or bool(item.get("attribution")))):
            return None, self._reason("review_rights_unconfirmed", output_field, platforms, "error", "Review authenticity, PII, or attribution is unconfirmed.", "Confirm authenticity, remove PII, and document attribution.")
        return {"field_id": item.get("field_id"), "value": deepcopy(value), "source_ids": [str(i) for i in ids],
                "verified_at": item.get("verified_at"), "platforms": list(platforms)}, None

    def _detail(self, raw, accepted):
        def vals(key): return [x["value"] for x in accepted.get(key, [])]
        def section(text=None, items=None, ids=None, required=False):
            content = items if items is not None else text
            status = "ready" if not self._empty(content) else ("blocked" if required else "partial")
            result = {"status": status, "source_ids": sorted(set(ids or []))}
            result["items" if items is not None else "text"] = content if not self._empty(content) else ([] if items is not None else "")
            return result
        ids = lambda k: [sid for x in accepted.get(k, []) for sid in x["source_ids"]]
        name = (vals("product_name") or vals("name") or [""])[0]
        facts, claims = vals("fact") + vals("feature"), vals("claim") + vals("benefit")
        specs, usage, cautions = vals("specification"), vals("usage"), vals("caution")
        faq = vals("faq")
        return {
            "headline": section(f"{name} — 확인된 상품 정보를 살펴보세요." if name else "", ids=ids("product_name") + ids("name"), required=True),
            "problem": section("구매 전 용도와 사양을 확인하세요.", ids=[]),
            "benefits": section(items=claims, ids=ids("claim")), "features": section(items=facts, ids=ids("fact") + ids("feature"), required=True),
            "specifications": section(items=specs, ids=ids("specification"), required=True),
            "usage": section(items=usage, ids=ids("usage"), required=True), "cautions": section(items=cautions, ids=ids("caution"), required=True),
            "faq": section(items=faq or [{"question": "확인이 필요한 정보가 있나요?", "answer": "누락 항목은 판매자에게 확인하세요."}], ids=ids("faq")),
            "cta": section("옵션과 고시정보를 확인한 뒤 구매를 결정하세요.", ids=[]),
        }

    def _package(self, platform, raw, accepted, detail, common_missing, common_blocked):
        product = raw.get("product", {}) if isinstance(raw.get("product"), dict) else {}
        def platform_values(key):
            return [entry for entry in accepted.get(key, []) if platform in entry.get("platforms", ["smartstore", "coupang"])]
        get = lambda k: platform_values(k)[0].get("value", "") if platform_values(k) else ""
        notice = {}
        missing, blocked = [], []
        for field in ("category", "option"):
            value = get(field) if field == "category" else platform_values("option")
            if self._empty(value):
                label = "product.category" if field == "category" else "product.options"
                missing.append(self._missing(label, [platform], "Required platform field is absent.", "Provide a verified value."))
                blocked.append(self._reason("missing_required_field", label, [platform], "error",
                    "Required platform field is absent.", "Provide a verified value."))
        for field in self.PLATFORM_NOTICE[platform]:
            value = get(f"notice.{field}") or get(field)
            if self._empty(value):
                missing.append(self._missing(f"notice_information.{field}", [platform], "Required platform notice is absent.", "Provide verified notice text."))
                blocked.append(self._reason("notice_information_incomplete", f"notice_information.{field}", [platform], "error", "Required platform notice is absent.", "Provide verified notice text."))
            else: notice[field] = value
        relevant = [x for x in common_blocked if platform in x["platforms"] and x["severity"] in {"error", "critical"}]
        relevant_missing = [x for x in common_missing if platform in x.get("platforms", [])]
        name_parts = [str(get(k)) for k in ("brand", "model_name", "product_name", "category") if get(k)]
        seeds = []
        for candidate in raw.get("search_seed_keywords", []) if isinstance(raw.get("search_seed_keywords"), list) else []:
            if not isinstance(candidate, (str, int, float)):
                continue
            seed = str(candidate).strip()
            if not seed:
                continue
            if self._keyword_has_prohibited_claim(seed):
                missing.append(self._missing("search_seed_keywords", [platform], "Keyword contains an unverified customer-facing claim.", "Remove the claim or supply it through the verified fact contract.", required=False))
                blocked.append(self._reason("unsupported_claim", "search_seed_keywords", [platform], "error",
                    "Keyword contains an unverified customer-facing claim.", "Remove the claim or supply it through the verified fact contract."))
                continue
            seeds.append(seed)
        keywords = list(dict.fromkeys(name_parts + seeds))
        description = self._render_detail(detail, platform)
        status = "blocked" if blocked or relevant or any(s["status"] == "blocked" for s in detail.values()) else ("partial" if relevant_missing else "ready_for_manual_upload")
        return {"platform": platform, "status": status,
                "missing_fields": self._dedupe(relevant_missing + missing),
                "blocked_reasons": self._dedupe(relevant + blocked),
                "product_name": " ".join(dict.fromkeys(name_parts)),
                "search_keywords": (keywords[:10] if platform == "smartstore" else ",".join(keywords[:20])),
                "options": [x["value"] for x in platform_values("option")], "detail_description": description,
                "notice_information": notice, "manual_upload_text_path": f"storage/commerce/{raw.get('request_id', 'commerce_request')}/{platform}_package.txt"}

    @classmethod
    def _keyword_has_prohibited_claim(cls, value):
        folded = unicodedata.normalize("NFKC", str(value)).casefold()
        # Format characters are discarded so zero-width insertion cannot split a claim.
        visible = "".join(ch for ch in folded if unicodedata.category(ch) != "Cf")
        words = re.findall(r"[a-z]+|\d+|[가-힣]+", visible)
        compact = "".join(words)

        def compact_form(text):
            normalized = unicodedata.normalize("NFKC", str(text)).casefold()
            return "".join(re.findall(r"[a-z]+|\d+|[가-힣]+", normalized))

        if any(compact_form(token) in compact for token in cls.PROHIBITED_KEYWORD_CLAIMS):
            return True

        word_set = set(words)
        english = [word for word in words if word.isascii()]
        joined_english = "".join(english)

        # Sales/ranking/endorsement claims use combinations instead of ambiguous bare
        # words. This keeps descriptions such as "seller information", "rated voltage",
        # and "top-loading bottle" available while rejecting marketing superlatives.
        if re.search(r"best(?:sell(?:er|ing)?|selling)", joined_english):
            return True
        if re.search(r"top(?:rated|seller|pick)", joined_english):
            return True
        if re.search(r"(?:number|no)(?:one|1)$", joined_english):
            return True
        if re.search(r"(?:number|no)(?:one|1)(?:product|seller|pick|choice)", joined_english):
            return True
        if re.search(r"(?:rank|ranking)(?:one|1|first|top)", joined_english):
            return True
        if word_set & {"sold", "sales", "rank", "ranking", "stock"}:
            return True
        if "sale" in word_set and (len(words) == 1 or bool(word_set & {"flash", "big", "special", "on"})):
            return True

        # Numeric and number-word percentage discounts are explicit claims only when
        # paired with both the percentage unit and OFF.
        number_words = {
            "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
            "ten", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
            "hundred",
        }
        if "off" in word_set and ("percent" in word_set or "%" in visible):
            if any(word.isdigit() for word in words) or bool(word_set & number_words):
                return True
        if re.search(r"\d+percentoff", compact):
            return True

        # Korean inflection-aware sales-volume claims. The combination is deliberately
        # narrow: 많이 + 팔리/팔렸 with a superlative cue, or the established compact
        # phrase, rather than either everyday word on its own.
        if re.search(r"(?:가장|제일)많이팔(?:리|렸|린|리는|림)", compact):
            return True
        if re.search(r"판매(?:일등|1위|최고|상위)", compact):
            return True
        return False

    @classmethod
    def _contains_prohibited_customer_claim(cls, value):
        if isinstance(value, dict):
            return any(cls._contains_prohibited_customer_claim(item) for item in value.values())
        if isinstance(value, (list, tuple, set)):
            return any(cls._contains_prohibited_customer_claim(item) for item in value)
        if not isinstance(value, str):
            return False
        # Ordinary provenance/support phrases are not purchase-volume claims.
        screened = re.sub(r"구매\s*처", "판매처", value)
        return cls._keyword_has_prohibited_claim(screened)

    @staticmethod
    def _secret_like(value):
        text = unicodedata.normalize("NFKC", str(value)).strip()
        lowered = text.casefold()
        if re.search(r"(?:bearer|api[_-]?key|access[_-]?token|secret|password|credential)(?:\s+|\s*[:=_-])", lowered):
            return True
        if lowered.startswith(("sk-", "sk_", "ghp_", "github_pat_", "xoxb-", "xoxp-")):
            return True
        # JWTs and long opaque credential-shaped identifiers are not valid source IDs.
        if re.fullmatch(r"eyj[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}", lowered):
            return True
        return len(text) >= 48 and bool(re.fullmatch(r"[A-Za-z0-9_+/=.-]+", text))

    @staticmethod
    def _render_detail(detail, platform):
        order = ("headline", "features", "benefits", "specifications", "usage", "cautions", "faq", "cta") if platform == "smartstore" else ("headline", "benefits", "features", "usage", "specifications", "cautions", "faq", "cta")
        parts = []
        for key in order:
            section = detail[key]
            if section["status"] == "blocked": continue
            body = section.get("text") or section.get("items")
            parts.append(f"[{key.upper()}]\n{body}")
        return "\n\n".join(parts)

    def _load_learning(self, requested, supplied, patterns):
        enabled = requested if isinstance(requested, dict) else {}
        data = deepcopy(supplied) if isinstance(supplied, dict) else {}
        def meta(key, interface, content, applied_key):
            on = bool(enabled.get(f"{key}_enabled", True)); available = bool(content)
            return {"enabled": on, "available": available, "source_path_or_interface": interface,
                    "snapshot_updated_at": None, applied_key: [],
                    "fallback_used": bool(on and not available),
                    "reason": ("available but not applied to generated copy" if on and available
                               else "learned data unavailable; safe defaults used" if on else "disabled by request")}
        knowledge, brand = data.get("knowledge", {}), data.get("brand_dna", {})
        if bool(enabled.get("knowledge_enabled", True)) and not knowledge:
            try:
                knowledge = {"hooks": self.knowledge_interface.get_top_hooks(limit=3),
                             "ctas": self.knowledge_interface.get_top_ctas(limit=3),
                             "patterns": self.knowledge_interface.get_pattern_knowledge(limit=3)}
            except Exception:
                knowledge = {}
        if bool(enabled.get("brand_dna_enabled", True)) and not brand:
            try:
                brand = self.brand_dna_interface.get_dominant_preferences() or {}
            except Exception:
                brand = {}
        return {"application_mode": "read_only",
                "knowledge": {**meta("knowledge", "KnowledgeInterface", knowledge, "applied_record_ids"), "record_ids": list(knowledge) if isinstance(knowledge, dict) else []},
                "brand_dna": meta("brand_dna", "BrandDNAInterface/brand_profile", brand, "applied_preferences"),
                "content_patterns": meta("content_patterns", "existing Content contracts", patterns or {}, "applied_patterns"),
                "writes_performed": False}

    @classmethod
    def _duplicate_conflicts(cls, fact_items):
        values = {}
        for field, item in fact_items:
            field_id = str(item.get("field_id") or field)
            values.setdefault(field_id, set()).add(cls._freeze(item.get("value")))
        return {field_id for field_id, observed in values.items() if len(observed) > 1}

    @staticmethod
    def _checklist(platforms):
        labels = ("Verify identity, seller, model, category, and options", "Re-verify volatile commercial facts", "Confirm claims, certifications, cautions, and notices", "Confirm review authenticity, rights, attribution, and no PII", "Confirm product and image rights", "Review names and keywords", "Preview platform layout", "Record human reviewer and time", "Upload manually and record listing ID")
        return [{"check_id": f"{p}_{i+1}", "platform": p, "label": label, "required": True, "completed": False, "instructions": label} for p in platforms for i, label in enumerate(labels)]

    @staticmethod
    def _reason(code, field, platforms, severity, message, action):
        return {"code": code, "field": field, "platforms": list(platforms), "severity": severity, "message": message, "required_action": action}
    @staticmethod
    def _missing(field, platforms, reason, action, required=True):
        return {"field": field, "platforms": list(platforms), "required": required, "reason": reason, "required_action": action}
    @staticmethod
    def _parse_time(value):
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00")); return dt.astimezone(timezone.utc) if dt.tzinfo else None
        except (ValueError, TypeError): return None
    @staticmethod
    def _max_age(field, policy):
        if not isinstance(policy, dict): return None
        value = policy.get(field)
        if value is None and field in CommerceModule.ALWAYS_VOLATILE:
            value = policy.get("volatile_max_age_seconds")
        if value is None:
            value = policy.get("default_max_age_seconds")
        if isinstance(value, dict): value = value.get("max_age_seconds")
        try: return float(value) if float(value) > 0 else None
        except (TypeError, ValueError): return None
    @staticmethod
    def _rights_ok(value):
        if isinstance(value, dict):
            return value.get("confirmed") is True or str(value.get("status", "")).lower() in {"granted", "owned", "licensed", "permitted", "merchant_owned", "merchant_authorized", "permission_confirmed"}
        return str(value or "").strip().lower() in {"granted", "owned", "licensed", "permitted", "merchant_owned", "merchant_authorized", "permission_confirmed"}
    @staticmethod
    def _freeze(value):
        import json
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    @staticmethod
    def _empty(value): return value is None or (isinstance(value, str) and not value.strip()) or value == [] or value == {}
    @classmethod
    def _dedupe(cls, entries):
        seen, result = set(), []
        for entry in entries:
            key = cls._freeze(entry)
            if key not in seen: seen.add(key); result.append(entry)
        return result
