"""Compile existing owner-learning records into deterministic production profiles.

This module does not inspect or reinterpret source images. It consumes only the
structured JSON already stored under ``knowledge/owner_feedback`` and preserves
the source identifiers behind every emitted production instruction.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "production_profile_compiler_v1"
MAX_REFERENCE_CANDIDATES = 40
ROLE_PROFILE_TOP_K = 5
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FEEDBACK_ROOT = REPOSITORY_ROOT / "knowledge" / "owner_feedback"
DEFAULT_TAXONOMY_PATH = DEFAULT_FEEDBACK_ROOT / "owner_learning_taxonomy_v1.json"
DEFAULT_INDEX_PATH = DEFAULT_FEEDBACK_ROOT / "cardnews_owner_learning_index.json"

PROFILE_FIELDS = (
    "account",
    "topic",
    "season",
    "emotion",
    "issue_intensity",
    "first_screen",
    "layout",
    "palette",
    "typography",
    "image_grammar",
    "body_density",
    "carousel_reels",
    "commerce",
    "ai_presenter",
)

ROLE_PROFILE_FIELDS = {
    "hook": ("first_screen", "layout", "palette", "typography", "image_grammar"),
    "evidence": ("layout", "typography", "image_grammar", "body_density"),
    "transition": ("layout", "palette", "image_grammar", "emotion"),
    "conclusion": ("layout", "palette", "typography", "body_density"),
}

_DIRECT_ALIASES = {
    "account": ("account", "account_id", "accounts", "category", "categories"),
    "topic": ("topic", "topics", "subject", "theme", "title"),
    "season": ("season", "seasonality", "month", "season_context"),
    "emotion": ("emotion", "emotions", "mood", "emotional_arc", "tone"),
    "issue_intensity": (
        "issue_intensity",
        "intensity",
        "urgency",
        "severity",
        "issue_strength",
    ),
    "first_screen": (
        "first_screen",
        "first_frame",
        "cover",
        "cover_rule",
        "hook",
        "thumbnail",
    ),
    "layout": ("layout", "layouts", "composition", "visual_structure"),
    "palette": ("palette", "color", "colors", "color_matching", "visual_tone"),
    "typography": ("typography", "font", "fonts", "caption_style", "subtitle_style"),
    "image_grammar": (
        "image_grammar",
        "image_media",
        "media_grammar",
        "visual_grammar",
        "visual_direction",
        "image_strategy",
    ),
    "body_density": (
        "body_density",
        "text_density",
        "copy_density",
        "caption_density",
        "content_density",
    ),
    "carousel_reels": (
        "carousel_reels",
        "format_strategy",
        "carousel",
        "reels",
        "shorts",
        "motion",
    ),
    "commerce": (
        "commerce",
        "product",
        "products",
        "product_connection",
        "monetization",
        "affiliate",
    ),
    "ai_presenter": (
        "ai_presenter",
        "presenter",
        "ai_model",
        "character_identity",
        "host_identity",
    ),
}

_LAYER_ROUTES = {
    "topic": ("topic",),
    "hook": ("first_screen",),
    "story_structure": ("layout",),
    "layout": ("layout",),
    "color": ("palette",),
    "typography": ("typography",),
    "image_media": ("image_grammar",),
    "commerce": ("commerce",),
}

_TEXT_ROUTES = {
    "season": ("계절", "시즌", "봄", "여름", "가을", "겨울", "장마", "season"),
    "emotion": (
        "감정",
        "감성",
        "분노",
        "긴장",
        "반전",
        "슬픔",
        "기쁨",
        "emotion",
        "mood",
    ),
    "issue_intensity": (
        "이슈 강도",
        "긴급",
        "경고",
        "충격",
        "민감",
        "위기",
        "urgency",
        "severity",
        "intensity",
    ),
    "body_density": (
        "본문 밀도",
        "텍스트 밀도",
        "글자 수",
        "짧은 문장",
        "한 문장",
        "두 문장",
        "copy density",
        "text density",
    ),
    "carousel_reels": (
        "캐러셀",
        "릴스",
        "쇼츠",
        "동영상",
        "프레임",
        "carousel",
        "reels",
        "shorts",
    ),
    "ai_presenter": (
        "ai 진행자",
        "ai 모델",
        "가상 진행자",
        "동일한 ai",
        "fictional ai presenter",
        "character identity",
    ),
}

_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣_]+")
_GENERIC_TOKENS = {
    "account",
    "cardnews",
    "content",
    "owner",
    "rule",
    "story",
    "topic",
    "공통",
    "규칙",
    "내용",
    "자료",
    "카드뉴스",
}


def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    return ""


def _as_strings(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [text for item in value if (text := _as_text(item))]
    text = _as_text(value)
    return [text] if text else []


def _as_field_values(value: Any) -> list[Any]:
    if isinstance(value, Mapping):
        return [copy.deepcopy(dict(value))] if value else []
    if isinstance(value, (list, tuple, set)):
        values: list[Any] = []
        for item in value:
            values.extend(_as_field_values(item))
        return values
    text = _as_text(value)
    return [text] if text else []


def _tokens(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        text = " ".join(_as_text(item) for item in value.values())
    elif isinstance(value, (list, tuple, set)):
        text = " ".join(_as_text(item) for item in value)
    else:
        text = _as_text(value)
    return {
        token.lower()
        for token in _TOKEN_RE.findall(text)
        if len(token) > 1 and token.lower() not in _GENERIC_TOKENS
    }


def _read_json(path: Path) -> Mapping[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, Mapping) else {}


def _stable_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _stable_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple, set)):
        normalized = [_stable_value(item) for item in value]
        return sorted(normalized, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True))
    return value


def _source_id(record: Mapping[str, Any], source_file: str, ordinal: int) -> str:
    for key in (
        "learning_id",
        "source_id",
        "event_id",
        "pattern_id",
        "rule_id",
        "record_id",
        "item_id",
        "id",
    ):
        if text := _as_text(record.get(key)):
            return text
    digest = hashlib.sha256(
        json.dumps(_stable_value(record), ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return f"{Path(source_file).stem}:{ordinal}:{digest}"


def _walk_records(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            if isinstance(child, (Mapping, list)):
                yield from _walk_records(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_records(child)


def _record_text(record: Mapping[str, Any]) -> str:
    preferred = (
        "rule",
        "owner_decision",
        "owner_reason",
        "recommended_action",
        "summary",
        "description",
        "title",
        "name",
    )
    values: list[str] = []
    for key in preferred:
        values.extend(_as_strings(record.get(key)))
    return " | ".join(dict.fromkeys(values))


def _field_values(record: Mapping[str, Any], field: str) -> list[Any]:
    values: list[Any] = []
    for alias in _DIRECT_ALIASES[field]:
        values.extend(_as_field_values(record.get(alias)))

    layers = set(_as_strings(record.get("learning_layers")))
    text = _record_text(record)
    for layer, destinations in _LAYER_ROUTES.items():
        if field in destinations and layer in layers and text:
            values.append(text)

    lowered = text.lower()
    if text and any(marker in lowered for marker in _TEXT_ROUTES.get(field, ())):
        values.append(text)

    formats = _as_strings(record.get("formats"))
    if field == "carousel_reels" and formats:
        values.extend(formats)
    if field == "account":
        values.extend(_as_strings(record.get("applies_to")))

    unique: dict[str, Any] = {}
    for value in values:
        key = json.dumps(
            _stable_value(value),
            ensure_ascii=False,
            sort_keys=True,
        )
        unique[key] = value
    return list(unique.values())


def _is_usable(record: Mapping[str, Any], source_kind: str) -> bool:
    if source_kind == "index":
        return record.get("active") is True
    if record.get("owner_confirmed") is False:
        return False
    if _as_text(record.get("status")).upper() in {"REJECTED", "DEPRECATED", "DISABLED"}:
        return False
    return True


def _is_reference_only(record: Mapping[str, Any]) -> bool:
    value = record.get("reference_only")
    if isinstance(value, bool):
        return value
    return _as_text(value).casefold() in {"1", "true", "yes", "y", "reference_only"}


def _owner_approval(record: Mapping[str, Any], source_kind: str) -> tuple[bool, str]:
    for key in ("owner_approved", "owner_confirmed", "approved"):
        if record.get(key) is True:
            return True, key
    if source_kind == "index" and record.get("active") is True:
        return True, "active_index"
    return False, "missing_explicit_owner_approval"


def _record_scope(record: Mapping[str, Any]) -> dict[str, list[str]]:
    accounts = sorted(
        {
            item
            for key in ("accounts", "categories", "applies_to", "account", "account_id")
            for item in _as_strings(record.get(key))
        }
    )
    formats = sorted(
        {
            item
            for key in ("formats", "format")
            for item in _as_strings(record.get(key))
        }
    )
    roles = sorted(
        {
            item
            for key in ("learning_layers", "roles", "role", "slide_role", "content_role")
            for item in _as_strings(record.get(key))
        }
    )
    return {"accounts": accounts, "formats": formats, "roles": roles}


def _normalized_render_value(field: str, value: Any) -> Any:
    if isinstance(value, Mapping):
        if field != "palette":
            return copy.deepcopy(dict(value))
        direct = {
            key: _as_text(value.get(key))
            for key in ("background", "ink", "accent", "muted", "panel")
            if _as_text(value.get(key))
        }
        role_map = {
            "primary": "accent",
            "support": "ink",
            "base": "background",
        }
        for source_role, target_role in role_map.items():
            nested = value.get(source_role)
            if isinstance(nested, Mapping):
                color = _as_text(nested.get("hex") or nested.get("color"))
                if color:
                    direct.setdefault(target_role, color)
        return direct or None
    values = value if isinstance(value, list) else [value]
    text = " ".join(_as_text(item) for item in values).casefold()
    if not text:
        return None

    if field == "layout":
        if any(token in text for token in ("분할", "좌우", "비대칭", "split")):
            return "editorial_split"
        if any(token in text for token in ("중앙", "센터", "center")):
            return "centered_panel"
        if any(token in text for token in ("전면", "풀블리드", "full bleed", "full_bleed")):
            return "full_bleed"
        return None
    if field == "typography":
        typography: dict[str, str] = {}
        if any(token in text for token in ("굵", "강한 제목", "bold", "condensed")):
            typography["headline"] = "bold_condensed"
        if any(
            token in text
            for token in ("짧은 본문", "짧은 문장", "한두 문장", "한글", "korean")
        ):
            typography["body"] = "short_korean"
        return typography or None
    if field == "body_density":
        if any(
            token in text
            for token in ("짧", "한두 문장", "한 문장", "두 문장", "low", "적게")
        ):
            return "low"
        if any(token in text for token in ("촘촘", "정보량", "상세", "high", "많이")):
            return "high"
        if "medium" in text or "보통" in text:
            return "medium"
        return None
    if field == "emotion":
        if any(token in text for token in ("경고", "경각심", "위기", "위험")):
            return "warning"
        if any(token in text for token in ("긴장", "충격", "급박")):
            return "urgent_warm"
        if any(token in text for token in ("밝", "유쾌", "기쁨")):
            return "bright"
        if any(token in text for token in ("연애", "로맨", "설렘")):
            return "romantic"
        if any(token in text for token in ("차분", "안정", "calm")):
            return "calm"
        return None
    if field == "image_grammar":
        grammar: list[str] = []
        if any(
            token in text
            for token in ("실제 보도", "보도 이미지", "문서 캡처", "출처 이미지")
        ):
            grammar.append("source_editorial")
        if any(token in text for token in ("전면", "풀블리드", "full bleed")):
            grammar.append("full_bleed")
        if any(token in text for token in ("전체가 보이", "잘리지", "contain")):
            grammar.append("contain")
        return grammar or None
    if field == "first_screen":
        if any(token in text for token in ("분할", "좌우", "split")):
            return "split"
        if any(token in text for token in ("중앙", "center")):
            return "center"
        if any(token in text for token in ("오른쪽", "right")):
            return "right"
        if any(token in text for token in ("왼쪽", "left")):
            return "left"
        if any(token in text for token in ("전면", "풀블리드", "full bleed")):
            return "full"
        return None
    if field == "palette":
        return None
    if field == "ai_presenter":
        return value
    return value


class ProductionProfileCompiler:
    """Build auditable topic production profiles from existing structured learning."""

    def __init__(
        self,
        *,
        feedback_root: str | Path = DEFAULT_FEEDBACK_ROOT,
        taxonomy_path: str | Path = DEFAULT_TAXONOMY_PATH,
        index_path: str | Path = DEFAULT_INDEX_PATH,
    ) -> None:
        self.feedback_root = Path(feedback_root)
        self.taxonomy_path = Path(taxonomy_path)
        self.index_path = Path(index_path)
        self._record_cache: list[dict[str, Any]] | None = None

    def _load_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        reserved = {self.taxonomy_path.resolve(), self.index_path.resolve()}

        sources: list[tuple[str, Path, Mapping[str, Any]]] = []
        if self.taxonomy_path.is_file():
            sources.append(("taxonomy", self.taxonomy_path, _read_json(self.taxonomy_path)))
        if self.index_path.is_file():
            sources.append(("index", self.index_path, _read_json(self.index_path)))
        if self.feedback_root.is_dir():
            for path in sorted(self.feedback_root.glob("*.json"), key=lambda item: item.name):
                if path.resolve() not in reserved:
                    sources.append(("analysis", path, _read_json(path)))

        for source_kind, path, payload in sources:
            candidates: Sequence[Mapping[str, Any]]
            if source_kind in {"taxonomy", "index"}:
                raw_records = payload.get("records", [])
                candidates = [item for item in raw_records if isinstance(item, Mapping)]
                if source_kind == "taxonomy":
                    candidates = [
                        *candidates,
                        *[
                            item
                            for key in ("candidate_patterns", "owner_rule_payloads")
                            for item in payload.get(key, [])
                            if isinstance(item, Mapping)
                        ],
                    ]
            else:
                candidates = list(_walk_records(payload))

            for ordinal, record in enumerate(candidates):
                if not _is_usable(record, source_kind):
                    continue
                source_file = str(path.as_posix())
                records.append(
                    {
                        "record": record,
                        "source_kind": source_kind,
                        "source_file": source_file,
                        "source_id": _source_id(record, source_file, ordinal),
                    }
                )
        return records

    def _records(self) -> list[dict[str, Any]]:
        if self._record_cache is None:
            self._record_cache = self._load_records()
        return self._record_cache

    def _reference_candidates(
        self,
        context: Mapping[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        source_records = self._records()
        ranked: list[dict[str, Any]] = []
        scoped_count = 0
        approved_count = 0
        reference_only_excluded_count = 0

        for item in source_records:
            record = item["record"]
            relevance = self._relevance(record, context)
            has_scope = bool(context["account"] or context["topic"] or context["formats"])
            scope = _record_scope(record)
            record_scoped = bool(scope["accounts"] or scope["formats"])
            if has_scope and record_scoped and not any(relevance):
                continue
            scoped_count += 1

            owner_approved, approval_basis = _owner_approval(
                record,
                item["source_kind"],
            )
            if not owner_approved:
                continue
            approved_count += 1
            if _is_reference_only(record):
                reference_only_excluded_count += 1
                continue

            instruction_fields = {
                field: _field_values(record, field)
                for field in PROFILE_FIELDS
                if _field_values(record, field)
            }
            if not instruction_fields:
                continue

            render_profile: dict[str, Any] = {}
            render_field_map = {
                "first_screen": "first_screen",
                "layout": "layout_family",
                "palette": "palette",
                "typography": "typography",
                "image_grammar": "image_grammar",
                "body_density": "text_density",
                "emotion": "emotional_tone",
                "ai_presenter": "account_identity",
            }
            for source_field, render_field in render_field_map.items():
                for value in instruction_fields.get(source_field, []):
                    normalized = _normalized_render_value(source_field, value)
                    if normalized not in (None, "", [], {}):
                        render_profile[render_field] = normalized
                        break

            record_hash = hashlib.sha256(
                json.dumps(
                    _stable_value(record),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            ranked.append(
                {
                    "reference_id": f"{item['source_id']}:{record_hash[:12]}",
                    "source": {
                        "source_id": item["source_id"],
                        "source_file": item["source_file"],
                        "source_kind": item["source_kind"],
                        "record_hash": record_hash,
                    },
                    "approval": {
                        "owner_approved": True,
                        "basis": approval_basis,
                    },
                    "reference_only": False,
                    "scope": scope,
                    "relevance": {
                        "account_match": relevance[0],
                        "format_match": relevance[1],
                        "topic_token_overlap": relevance[2],
                    },
                    "instruction_fields": instruction_fields,
                    "render_profile": render_profile,
                    "approval_status": "owner_approved",
                    "owner_approval_receipt_id": _as_text(
                        record.get("owner_approval_receipt_id")
                        or record.get("approval_receipt_id")
                    ),
                    "reference_only": False,
                    "blueprint_id": _as_text(record.get("blueprint_id")),
                }
            )

        ranked.sort(
            key=lambda candidate: (
                -candidate["relevance"]["topic_token_overlap"],
                -candidate["relevance"]["account_match"],
                -candidate["relevance"]["format_match"],
                candidate["reference_id"],
            )
        )
        unique: dict[str, dict[str, Any]] = {}
        for candidate in ranked:
            unique.setdefault(candidate["reference_id"], candidate)
        production_selectable = list(unique.values())
        emitted = production_selectable[:MAX_REFERENCE_CANDIDATES]
        receipt = {
            "selection_mode": (
                "bounded_ranked_reference_candidates_with_legacy_first_value_profile"
            ),
            "legacy_profile_selection_mode": "first_normalizable_value_per_render_field",
            "max_candidates": MAX_REFERENCE_CANDIDATES,
            "counts": {
                "source_records": len(source_records),
                "scope_matched_records": scoped_count,
                "owner_approved_records": approved_count,
                "reference_only_excluded": reference_only_excluded_count,
                "production_selectable": len(production_selectable),
                "emitted": len(emitted),
                "truncated": max(0, len(production_selectable) - len(emitted)),
            },
        }
        return emitted, receipt

    @staticmethod
    def _context(topic_context: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "account": _as_text(
                topic_context.get("account") or topic_context.get("account_id")
            ),
            "topic": _as_text(
                topic_context.get("topic")
                or topic_context.get("title")
                or topic_context.get("subject")
            ),
            "season": _as_text(topic_context.get("season")),
            "emotion": _as_text(topic_context.get("emotion")),
            "issue_intensity": _as_text(topic_context.get("issue_intensity")),
            "formats": sorted(
                set(
                    _as_strings(
                        topic_context.get("formats")
                        or topic_context.get("format")
                        or topic_context.get("target_formats")
                    )
                )
            ),
            "keywords": sorted(set(_as_strings(topic_context.get("keywords")))),
        }

    @staticmethod
    def _relevance(record: Mapping[str, Any], context: Mapping[str, Any]) -> tuple[int, int, int]:
        account = _as_text(context.get("account")).lower()
        formats = {item.lower() for item in _as_strings(context.get("formats"))}
        topic_tokens = _tokens(
            [
                context.get("topic"),
                context.get("season"),
                context.get("emotion"),
                context.get("issue_intensity"),
                *context.get("keywords", []),
            ]
        )
        record_accounts = {
            item.lower()
            for key in ("accounts", "categories", "applies_to", "account", "account_id")
            for item in _as_strings(record.get(key))
        }
        record_formats = {
            item.lower()
            for key in ("formats", "format")
            for item in _as_strings(record.get(key))
        }
        account_match = int(bool(account and account in record_accounts))
        format_match = int(bool(formats & record_formats))
        topic_overlap = len(topic_tokens & _tokens([_record_text(record), *record_accounts]))
        return account_match, format_match, topic_overlap

    def compile(self, topic_context: Mapping[str, Any]) -> dict[str, Any]:
        context = self._context(topic_context)
        reference_candidates, reference_candidate_receipt = (
            self._reference_candidates(context)
        )
        buckets: dict[str, list[dict[str, Any]]] = {field: [] for field in PROFILE_FIELDS}

        for item in self._records():
            record = item["record"]
            relevance = self._relevance(record, context)
            has_scope = bool(context["account"] or context["topic"] or context["formats"])
            record_scoped = any(
                _as_strings(record.get(key))
                for key in ("accounts", "categories", "applies_to", "formats", "format")
            )
            if has_scope and record_scoped and not any(relevance):
                continue

            for field in PROFILE_FIELDS:
                for value in _field_values(record, field):
                    buckets[field].append(
                        {
                            "value": value,
                            "source_id": item["source_id"],
                            "source_file": item["source_file"],
                            "source_kind": item["source_kind"],
                            "relevance": {
                                "account_match": relevance[0],
                                "format_match": relevance[1],
                                "topic_token_overlap": relevance[2],
                            },
                        }
                    )

        explicit_context = {
            field: context[field]
            for field in ("account", "topic", "season", "emotion", "issue_intensity")
            if context[field]
        }
        for field, value in explicit_context.items():
            buckets[field].append(
                {
                    "value": value,
                    "source_id": "runtime-topic-context",
                    "source_file": "",
                    "source_kind": "runtime_context",
                    "relevance": {
                        "account_match": int(field == "account"),
                        "format_match": 0,
                        "topic_token_overlap": int(field == "topic"),
                    },
                }
            )

        fields: dict[str, dict[str, Any]] = {}
        all_source_ids: set[str] = set()
        all_source_files: set[str] = set()
        for field in PROFILE_FIELDS:
            unique: dict[tuple[str, str], dict[str, Any]] = {}
            for evidence in buckets[field]:
                key = (
                    json.dumps(
                        _stable_value(evidence["value"]),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    evidence["source_id"],
                )
                unique[key] = evidence
            ordered = sorted(
                unique.values(),
                key=lambda item: (
                    -item["relevance"]["topic_token_overlap"],
                    -item["relevance"]["account_match"],
                    -item["relevance"]["format_match"],
                    item["source_id"],
                    json.dumps(
                        _stable_value(item["value"]),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                ),
            )
            source_ids = sorted({item["source_id"] for item in ordered})
            source_files = sorted(
                {item["source_file"] for item in ordered if item["source_file"]}
            )
            all_source_ids.update(source_ids)
            all_source_files.update(source_files)
            fields[field] = {
                "status": "compiled" if ordered else "missing",
                "values": [item["value"] for item in ordered],
                "selected": copy.deepcopy(ordered[0]["value"]) if ordered else None,
                "evidence": ordered,
                "provenance_source_ids": source_ids,
            }

        role_top_k: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for role, role_fields in ROLE_PROFILE_FIELDS.items():
            role_top_k[role] = {}
            for field in role_fields:
                role_top_k[role][field] = [
                    {
                        "value": copy.deepcopy(item["value"]),
                        "source_id": item["source_id"],
                        "relevance": copy.deepcopy(item["relevance"]),
                    }
                    for item in fields[field]["evidence"][:ROLE_PROFILE_TOP_K]
                ]

        approved_reference_specimen_candidates = [
            copy.deepcopy(candidate)
            for candidate in reference_candidates
            if candidate.get("approval_status") == "owner_approved"
            and candidate.get("reference_only") is False
        ]
        reference_v2_selectable_candidates = [
            copy.deepcopy(candidate)
            for candidate in approved_reference_specimen_candidates
            if _as_text(candidate.get("blueprint_id"))
            and _as_text(candidate.get("owner_approval_receipt_id"))
        ]

        render_field_map = {
            "first_screen": "first_screen",
            "layout": "layout_family",
            "palette": "palette",
            "typography": "typography",
            "image_grammar": "image_grammar",
            "body_density": "text_density",
            "emotion": "emotional_tone",
            "ai_presenter": "account_identity",
        }
        production_profile: dict[str, Any] = {}
        production_profile_provenance: dict[str, list[str]] = {}
        for source_field, render_field in render_field_map.items():
            for evidence in fields[source_field]["evidence"]:
                normalized = _normalized_render_value(
                    source_field,
                    evidence["value"],
                )
                if normalized in (None, "", [], {}):
                    continue
                production_profile[render_field] = normalized
                production_profile_provenance[render_field] = [
                    evidence["source_id"]
                ]
                break
        if context["account"]:
            production_profile["account_identity"] = context["account"]
            production_profile_provenance["account_identity"] = [
                "runtime-topic-context"
            ]
        selected_layout = fields["layout"]["selected"]
        if isinstance(selected_layout, Mapping):
            composition = selected_layout.get("composition")
            if composition not in (None, "", [], {}):
                production_profile["composition"] = copy.deepcopy(composition)
                production_profile_provenance["composition"] = copy.deepcopy(
                    fields["layout"]["provenance_source_ids"][:1]
                )

        fingerprint_payload = {
            "schema_version": SCHEMA_VERSION,
            "context": context,
            "fields": fields,
            "production_profile": production_profile,
            "role_top_k": role_top_k,
            "approved_reference_specimen_candidates": approved_reference_specimen_candidates,
            "reference_v2_selectable_candidates": reference_v2_selectable_candidates,
            "production_profile_normalization": {
                "mode": "deterministic_existing_text_mapping",
                "source_reanalysis": False,
            },
            "reference_candidates": reference_candidates,
            "reference_candidate_receipt": reference_candidate_receipt,
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                _stable_value(fingerprint_payload),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        return {
            "schema_version": SCHEMA_VERSION,
            "profile_id": f"production-profile:{fingerprint[:20]}",
            "status": "compiled" if all_source_ids else "no_learning_evidence",
            "context": context,
            "fields": fields,
            "production_profile": production_profile,
            "role_top_k": role_top_k,
            "production_profile_normalization": {
                "mode": "deterministic_existing_text_mapping",
                "source_reanalysis": False,
            },
            "production_profile_provenance": production_profile_provenance,
            "reference_candidates": reference_candidates,
            "approved_reference_specimen_candidates": approved_reference_specimen_candidates,
            "reference_v2_selectable_candidates": reference_v2_selectable_candidates,
            "reference_candidate_receipt": reference_candidate_receipt,
            "missing_fields": [
                field for field in PROFILE_FIELDS if fields[field]["status"] == "missing"
            ],
            "provenance": {
                "source_ids": sorted(all_source_ids),
                "source_files": sorted(all_source_files),
                "source_count": len(all_source_ids),
            },
            "deterministic_fingerprint": fingerprint,
            "inference_used": False,
        }

    def compile_many(
        self, topic_contexts: Iterable[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        return [
            self.compile(context)
            for context in sorted(
                topic_contexts,
                key=lambda item: json.dumps(
                    _stable_value(dict(item)),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            )
        ]


__all__ = [
    "DEFAULT_FEEDBACK_ROOT",
    "DEFAULT_INDEX_PATH",
    "DEFAULT_TAXONOMY_PATH",
    "MAX_REFERENCE_CANDIDATES",
    "PROFILE_FIELDS",
    "ProductionProfileCompiler",
    "SCHEMA_VERSION",
]
