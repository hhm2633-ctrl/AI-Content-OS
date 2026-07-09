import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class CTAStrategy:
    """
    CTA Engine v2 (Content Intelligence Sprint 2).

    CTA Library(benchmark/CTA_LIBRARY.md) 기반으로 pattern_type/topic_intelligence/
    brand_profile/platform에 가장 적합한 cta_type을 선택하고, 실제 CTA 문장(cta_line)과
    CTA Score(cta_score, 0.0~1.0)까지 만든다. Pattern Engine의 cta_type(5종)보다 넓은
    7종 팔레트를 사용해 Content Engine 단계에서 한 번 더 다듬는다.

    플랫폼별 선택은 config/publishing.json의 platform 값을 읽어 PLATFORM_CTA_OVERRIDES에
    정의된 경우에만 pattern 기반 매핑을 덮어쓴다. 현재는 instagram만 운영 중이라
    override가 비어 있고, pattern 기반 매핑이 그대로 적용된다 — 새 플랫폼이 추가되면
    이 표에 항목을 채우는 것으로 확장한다.

    Sprint 2 개선:
    - cta_type별 템플릿을 2개 -> 4개로 늘려 다양성을 높였다.
    - storage/content/content_history.json(ContentDuplicateDetector가 이미 기록하는
      기존 파일)의 최근 cta_text를 "읽기 전용"으로 참고해, 최근 기록과 문장이 너무
      비슷하면 다른 템플릿으로 회피한다 (새 storage 파일/스키마를 만들지 않는다).
    - pattern_plan.layout_type(CardNews Layout Intelligence와 동일한 값)과 cta_type의
      궁합을 CTA Score에 반영해 "플랫폼별 CTA 선택 정확도"를 실질적으로 높였다.
      실제 플랫폼이 instagram 하나뿐이라 플랫폼 분기 로직을 허위로 늘리는 대신,
      이미 존재하는 layout 신호로 정확도를 개선하는 방식을 선택했다. 기존
      PLATFORM_CTA_OVERRIDES 메커니즘은 그대로 유지한다.

    select()는 하위 호환을 유지한다: pattern_plan만 넘겨도 동작하며, topic_intelligence/
    brand_profile/keyword는 선택 인자다. 실패해도 예외를 던지지 않고 안전한 기본값을
    반환한다 (fallback-first 계약 유지). storage 파일을 쓰지 않는다(읽기 전용).
    """

    CTA_TYPES = [
        "save",
        "comment",
        "follow",
        "profile",
        "dm",
        "share",
        "link_click",
    ]

    PATTERN_CTA_MAP = {
        "warning": "save",
        "tutorial": "follow",
        "comparison": "comment",
        "story": "dm",
        "number_list": "share",
        "resource": "profile",
    }

    # layout_type(CardNews Layout Intelligence와 동일한 값)과 궁합이 좋은 cta_type.
    # 선택 자체를 덮어쓰지는 않고 CTA Score 보너스로만 반영한다.
    LAYOUT_CTA_HINTS = {
        "talking_head": "dm",
        "character_diary": "comment",
        "bold_ai": "share",
        "dark_editorial": "profile",
        "notebook": "save",
    }

    # platform -> pattern_type -> cta_type. 정의된 조합만 PATTERN_CTA_MAP을 덮어쓴다.
    # 신규 플랫폼(예: youtube_shorts, threads)이 생기면 여기에 항목을 추가한다.
    PLATFORM_CTA_OVERRIDES: Dict[str, Dict[str, str]] = {
        "instagram": {},
    }

    DEFAULT_CTA_TYPE = "save"
    DEFAULT_PLATFORM = "instagram"
    DEFAULT_CTA_LINE = "저장해두고 필요할 때 꺼내 보세요."

    # benchmark/CTA_LIBRARY.md의 패턴을 참고한 cta_type별 문장 템플릿 (다양성 확대: 4개/타입).
    # "___"는 generate 시 keyword로 치환된다.
    CTA_TEMPLATES: Dict[str, List[str]] = {
        "save": [
            "저장해두고 ___ 할 때 꺼내 보세요.",
            "이 ___ 정리본은 저장 필수입니다.",
            "나중에 다시 보려면 지금 저장하세요.",
            "___ 필요할 때 바로 찾도록 저장해두세요.",
        ],
        "comment": [
            "___ 어떻게 생각하세요? 댓글로 알려주세요.",
            "___ 궁금하면 댓글 남겨주세요.",
            "___ 관련 경험 있다면 댓글로 공유해주세요.",
            "더 알고 싶은 ___ 이야기 댓글로 남겨주세요.",
        ],
        "follow": [
            "___ 시리즈 놓치기 싫으면 팔로우하세요.",
            "매일 ___ 팁을 올립니다. 팔로우하세요.",
            "다음 ___ 편도 보려면 팔로우해두세요.",
            "___ 소식 계속 받아보려면 팔로우하세요.",
        ],
        "profile": [
            "더 많은 ___ 자료는 프로필 링크에 있습니다.",
            "___ 관련 자료는 프로필에서 확인하세요.",
            "___ 다른 글도 프로필에서 확인해보세요.",
            "프로필 방문하고 ___ 이전 글도 살펴보세요.",
        ],
        "dm": [
            "___ 고민 있으면 DM 주세요.",
            "___ 자세한 내용은 DM으로 안내드립니다.",
            "1:1로 ___ 궁금한 점은 DM 주세요.",
            "___ 직접 물어보고 싶다면 DM 보내주세요.",
        ],
        "share": [
            "___ 필요한 친구에게 공유하세요.",
            "주변에 ___ 하는 사람 있다면 보내주세요.",
            "혼자 보기 아깝다면 ___ 공유해보세요.",
            "___ 함께 보면 좋은 사람에게 공유하세요.",
        ],
        "link_click": [
            "___ 관련 영상은 화면 링크에서 확인하세요.",
            "다음 ___ 편으로 바로 이동할 수 있게 연결해둘게요.",
            "___ 전체 자료는 링크에서 확인하세요.",
            "지금 링크 눌러서 ___ 더 확인해보세요.",
        ],
    }

    HISTORY_PATH = Path("storage/content/content_history.json")
    RECENT_HISTORY_LIMIT = 10
    SIMILARITY_THRESHOLD = 0.72

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def select(
        self,
        pattern_plan: Optional[Dict[str, Any]],
        topic_intelligence: Optional[Dict[str, Any]] = None,
        brand_profile: Optional[Dict[str, Any]] = None,
        keyword: str = "",
    ) -> Dict[str, Any]:
        try:
            return self._select(
                pattern_plan or {},
                topic_intelligence or {},
                brand_profile or {},
                str(keyword or ""),
            )
        except Exception:
            return {
                "cta_type": self.DEFAULT_CTA_TYPE,
                "reason": "CTA 선택 계산 실패로 기본 CTA로 대체함.",
                "cta_line": self.DEFAULT_CTA_LINE,
                "cta_score": 0.0,
                "cta_score_reason": "CTA 선택 실패로 0.0 처리함.",
                "platform": self.DEFAULT_PLATFORM,
            }

    def _select(
        self,
        pattern_plan: Dict[str, Any],
        topic_intelligence: Dict[str, Any],
        brand_profile: Dict[str, Any],
        keyword: str,
    ) -> Dict[str, Any]:
        pattern_type = str(pattern_plan.get("pattern_type", ""))
        upstream_cta = str(pattern_plan.get("cta_type", ""))
        layout_type = str(pattern_plan.get("layout_type", ""))
        platform = self._load_platform()

        if pattern_type in self.PATTERN_CTA_MAP:
            cta_type = self.PATTERN_CTA_MAP[pattern_type]
            reason = (
                f"pattern_type '{pattern_type}' 콘텐츠 목적에 맞춰 Content Engine이 "
                f"'{cta_type}' CTA로 세분화함."
            )
        elif upstream_cta in self.CTA_TYPES:
            cta_type = upstream_cta
            reason = f"Content Engine 매핑에 없어 Pattern Engine의 '{cta_type}' CTA를 사용함."
        else:
            cta_type = self.DEFAULT_CTA_TYPE
            reason = "pattern_type/cta_type 정보가 부족해 기본 CTA로 대체함."

        platform_overrides = self.PLATFORM_CTA_OVERRIDES.get(platform, {})
        if pattern_type in platform_overrides:
            overridden_cta = platform_overrides[pattern_type]
            if overridden_cta != cta_type:
                cta_type = overridden_cta
                reason = f"platform '{platform}' 전용 매핑으로 '{cta_type}' CTA를 사용함."

        recent_cta_lines = self._load_recent_texts("cta_text")
        cta_line, is_diverse = self._generate_cta_line(cta_type, keyword, recent_cta_lines)

        score_result = self._score_cta(
            cta_type=cta_type,
            pattern_type=pattern_type,
            layout_type=layout_type,
            pattern_plan=pattern_plan,
            topic_intelligence=topic_intelligence,
            brand_profile=brand_profile,
            cta_line=cta_line,
            is_diverse=is_diverse,
        )

        return {
            "cta_type": cta_type,
            "reason": reason,
            "cta_line": cta_line,
            "cta_score": score_result["cta_score"],
            "cta_score_reason": score_result["cta_score_reason"],
            "platform": platform,
        }

    def _generate_cta_line(
        self,
        cta_type: str,
        keyword: str,
        recent_lines: List[str],
    ) -> Tuple[str, bool]:
        templates = self.CTA_TEMPLATES.get(cta_type)

        if not templates:
            return self.DEFAULT_CTA_LINE, True

        keyword = keyword.strip()
        display_keyword = keyword if keyword else "필요할 때"

        # 키워드 문자 합으로 시작 템플릿을 결정론적으로 고른다 (같은 입력이면 같은 결과).
        base_index = (sum(ord(char) for char in keyword) % len(templates)) if keyword else 0

        # 최근 이력과 너무 비슷하면 다음 템플릿으로 순환하며 회피한다 (CTA 다양성 추가 +
        # 최근 CTA 중복 방지). 전부 비슷하면 어쩔 수 없이 기본 후보를 그대로 사용한다
        # (fallback-first: 항상 값은 반환해야 한다).
        for offset in range(len(templates)):
            index = (base_index + offset) % len(templates)
            candidate = templates[index].replace("___", display_keyword)

            if not self._is_similar_to_recent(candidate, recent_lines):
                return candidate, True

        return templates[base_index].replace("___", display_keyword), False

    def _is_similar_to_recent(self, candidate: str, recent_lines: List[str]) -> bool:
        try:
            candidate_lower = candidate.strip().lower()

            for line in recent_lines:
                line_lower = str(line or "").strip().lower()

                if not line_lower:
                    continue

                if SequenceMatcher(None, candidate_lower, line_lower).ratio() >= self.SIMILARITY_THRESHOLD:
                    return True

            return False
        except Exception:
            return False

    def _score_cta(
        self,
        cta_type: str,
        pattern_type: str,
        layout_type: str,
        pattern_plan: Dict[str, Any],
        topic_intelligence: Dict[str, Any],
        brand_profile: Dict[str, Any],
        cta_line: str,
        is_diverse: bool,
    ) -> Dict[str, Any]:
        reasons: List[str] = []
        score = 0.5

        ideal_cta = self.PATTERN_CTA_MAP.get(pattern_type)

        if ideal_cta and cta_type == ideal_cta:
            score += 0.25
            reasons.append("pattern_type에 가장 적합한 CTA 타입 사용(+0.25)")
        elif ideal_cta:
            score -= 0.1
            reasons.append("pattern_type의 이상적인 CTA 타입과 다름(-0.1)")

        layout_ideal_cta = self.LAYOUT_CTA_HINTS.get(layout_type)
        if layout_ideal_cta:
            if cta_type == layout_ideal_cta:
                score += 0.1
                reasons.append(f"layout_type '{layout_type}'과 궁합이 좋은 CTA 사용(+0.1)")
            else:
                score -= 0.05
                reasons.append(f"layout_type '{layout_type}'과 궁합이 아쉬운 CTA(-0.05)")

        confidence_score = topic_intelligence.get("confidence_score")
        if isinstance(confidence_score, (int, float)):
            adjustment = round((float(confidence_score) - 0.5) * 0.2, 4)
            score += adjustment
            reasons.append(f"topic confidence_score({confidence_score}) 반영({adjustment:+.4f})")

        if pattern_plan.get("fallback_used"):
            score -= 0.15
            reasons.append("pattern_plan.fallback_used로 감점(-0.15)")

        if is_diverse:
            score += 0.05
            reasons.append("최근 이력과 겹치지 않는 다양한 CTA(+0.05)")
        else:
            score -= 0.1
            reasons.append("최근 이력과 유사한 CTA가 감지됨(-0.1)")

        banned_words = brand_profile.get("banned_words") if isinstance(brand_profile, dict) else None
        if isinstance(banned_words, list):
            for word in banned_words:
                word_text = str(word or "").strip()
                if word_text and word_text in cta_line:
                    score -= 0.2
                    reasons.append(f"cta_line에 브랜드 금지어 '{word_text}' 포함(-0.2)")
                    break

        score = round(max(0.0, min(1.0, score)), 4)

        return {
            "cta_score": score,
            "cta_score_reason": ("; ".join(reasons) + ".") if reasons else "기본 점수.",
        }

    def _load_recent_texts(self, field_name: str) -> List[str]:
        """
        storage/content/content_history.json을 읽기 전용으로 참고한다 (쓰지 않는다).
        이 파일은 ContentDuplicateDetector가 이미 기록하고 있는 기존 파일이며, 이
        메서드는 새 storage 스키마를 추가하지 않고 기존 필드(hook_text/cta_text)만
        재사용한다. 파일이 없거나 손상돼도 빈 리스트를 반환한다.
        """
        try:
            if not self.HISTORY_PATH.exists():
                return []

            with open(self.HISTORY_PATH, "r", encoding="utf-8") as file:
                data = json.load(file)

            if not isinstance(data, dict):
                return []

            records = data.get("records", [])
            if not isinstance(records, list):
                return []

            recent_records = records[-self.RECENT_HISTORY_LIMIT:]
            texts = []

            for record in recent_records:
                if isinstance(record, dict):
                    text = str(record.get(field_name, "")).strip()
                    if text:
                        texts.append(text)

            return texts
        except Exception:
            return []

    def _load_platform(self) -> str:
        config_path = Path("config/publishing.json")

        if not config_path.exists():
            return self.DEFAULT_PLATFORM

        try:
            with open(config_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                platform = str(data.get("platform", self.DEFAULT_PLATFORM)).strip()
                return platform or self.DEFAULT_PLATFORM
        except Exception:
            pass

        return self.DEFAULT_PLATFORM
