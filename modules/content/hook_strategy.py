import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class HookStrategy:
    """
    Hook Engine v2 (Content Intelligence Sprint 2).

    Hook Library(benchmark/HOOK_LIBRARY.md) 기반으로 pattern_type/topic_intelligence/
    brand_profile에 가장 적합한 hook_type을 선택하고, 실제 훅 문장(hook_line)과
    Hook Score(hook_score, 0.0~1.0)까지 만든다. Pattern Engine의 hook_type(5종)보다
    넓은 7종 팔레트를 사용해 Content Engine 단계에서 한 번 더 다듬는다.

    Sprint 2 개선:
    - hook_type별 템플릿을 2개 -> 4개로 늘려 다양성을 높였다.
    - storage/content/content_history.json(ContentDuplicateDetector가 이미 기록하는
      기존 파일)의 최근 hook_text를 "읽기 전용"으로 참고해, 최근 기록과 문장이 너무
      비슷하면 다른 템플릿으로 회피한다 (새 storage 파일/스키마를 만들지 않는다).
    - Hook Score에 다양성 가점/감점을 추가했다.

    select()는 하위 호환을 유지한다: pattern_plan만 넘겨도 동작하며, topic_intelligence/
    brand_profile/keyword는 선택 인자다. 실패해도 예외를 던지지 않고 안전한 기본값을
    반환한다 (fallback-first 계약 유지). storage 파일을 쓰지 않는다(읽기 전용).
    """

    HOOK_TYPES = [
        "attention",
        "saveable_tip",
        "authority",
        "contrarian",
        "pain_point",
        "beginner",
        "result_proof",
    ]

    # pattern_type 기준 Content Engine 전용 세분화 매핑.
    # tutorial/story는 Pattern Engine에 없는 beginner/result_proof로 세분화한다.
    PATTERN_HOOK_MAP = {
        "warning": "attention",
        "tutorial": "beginner",
        "comparison": "contrarian",
        "story": "result_proof",
        "number_list": "saveable_tip",
        "resource": "saveable_tip",
    }

    DEFAULT_HOOK_TYPE = "pain_point"
    DEFAULT_HOOK_LINE = "지금 이것부터 시작해보세요."

    # benchmark/HOOK_LIBRARY.md의 패턴을 참고한 hook_type별 문장 템플릿 (다양성 확대: 4개/타입).
    # "___"는 generate 시 keyword로 치환된다.
    HOOK_TEMPLATES: Dict[str, List[str]] = {
        "attention": [
            "___ 이제 막 시작했다면, 이건 꼭 보세요.",
            "___ 하기 전에 이것부터 확인하세요.",
            "아무도 말해주지 않는 ___의 진실.",
            "___ 이거 하나로 끝납니다.",
        ],
        "saveable_tip": [
            "___ 시간을 절반으로 줄이는 법.",
            "___ 할 때 90%가 놓치는 것 하나.",
            "___ 콘텐츠 일주일치를 1시간에 짜는 법.",
            "초보도 매일 쓰는 ___ 방법 3가지.",
        ],
        "beginner": [
            "막막함 없이 ___ 시작하는 법.",
            "___ 처음 시작할 때 알았으면 했던 것.",
            "경험이 0이어도 ___ 시작하는 법.",
            "___ 기초, 이것 하나로 끝냅니다.",
        ],
        "authority": [
            "___ 제대로 해보고 내린 결론.",
            "___ 현업에서만 아는 것.",
            "수백 번 해보고 알게 된 ___의 공식.",
            "___ 잘하는 사람은 이 습관이 있어요.",
        ],
        "contrarian": [
            "다들 아는 ___ 조언, 사실 틀렸어요.",
            "___ 열심히 하지 마세요. 이유가 있어요.",
            "인기 많은 그 ___ 방법, 저는 반대합니다.",
            "___ 트렌드, 그냥 따라가지 마세요.",
        ],
        "pain_point": [
            "___ 하는 사람만 아는 고충.",
            "저도 ___ 이거 때문에 매번 막혔어요.",
            "___, 사실 시작이 제일 어렵죠.",
            "___ 자꾸 미루게 되는 진짜 이유.",
        ],
        "result_proof": [
            "___ 30일 하고 달라진 점.",
            "___ 방법 바꾸고 나서 생긴 변화.",
            "___ 전 vs 후, 이만큼 바뀌었어요.",
            "조회수 0에서 여기까지, ___ 기록.",
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
        hook_type_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            return self._select(
                pattern_plan or {},
                topic_intelligence or {},
                brand_profile or {},
                str(keyword or ""),
                hook_type_override,
            )
        except Exception:
            return {
                "hook_type": self.DEFAULT_HOOK_TYPE,
                "reason": "Hook 선택 계산 실패로 기본 훅으로 대체함.",
                "hook_line": self.DEFAULT_HOOK_LINE,
                "hook_score": 0.0,
                "hook_score_reason": "Hook 선택 실패로 0.0 처리함.",
            }

    def _select(
        self,
        pattern_plan: Dict[str, Any],
        topic_intelligence: Dict[str, Any],
        brand_profile: Dict[str, Any],
        keyword: str,
        hook_type_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        pattern_type = str(pattern_plan.get("pattern_type", ""))
        upstream_hook = str(pattern_plan.get("hook_type", ""))

        # AI Planner Consumer Adapter 실제 연결(Sprint 15-3): hook_type_override는
        # ContentPromptBuilder가 PlannerConsumerAdapter.resolve_hook()으로 이미
        # "적용해도 안전하다"고 판정한 값만 넘긴다 - 이 클래스는 그 판단을 하지
        # 않고, 넘어온 값이 실제로 이 클래스가 아는 hook_type인지만 다시 확인한다
        # (이중 방어). override가 없거나 알 수 없는 값이면 기존 로직을 그대로 쓴다.
        if hook_type_override and hook_type_override in self.HOOK_TYPES:
            hook_type = hook_type_override
            reason = f"AI Planner Hint에 따라 '{hook_type}' 훅으로 재지정함."
        elif pattern_type in self.PATTERN_HOOK_MAP:
            hook_type = self.PATTERN_HOOK_MAP[pattern_type]
            reason = (
                f"pattern_type '{pattern_type}' 콘텐츠 목적에 맞춰 Content Engine이 "
                f"'{hook_type}' 훅으로 세분화함."
            )
        elif upstream_hook in self.HOOK_TYPES:
            hook_type = upstream_hook
            reason = f"Content Engine 매핑에 없어 Pattern Engine의 '{hook_type}' 훅을 사용함."
        else:
            hook_type = self.DEFAULT_HOOK_TYPE
            reason = "pattern_type/hook_type 정보가 부족해 기본 훅으로 대체함."

        recent_hook_lines = self._load_recent_texts("hook_text")
        hook_line, is_diverse = self._generate_hook_line(hook_type, keyword, recent_hook_lines)

        score_result = self._score_hook(
            hook_type=hook_type,
            pattern_type=pattern_type,
            pattern_plan=pattern_plan,
            topic_intelligence=topic_intelligence,
            brand_profile=brand_profile,
            hook_line=hook_line,
            is_diverse=is_diverse,
        )

        return {
            "hook_type": hook_type,
            "reason": reason,
            "hook_line": hook_line,
            "hook_score": score_result["hook_score"],
            "hook_score_reason": score_result["hook_score_reason"],
        }

    def _generate_hook_line(
        self,
        hook_type: str,
        keyword: str,
        recent_lines: List[str],
    ) -> Tuple[str, bool]:
        templates = self.HOOK_TEMPLATES.get(hook_type)

        if not templates:
            return self.DEFAULT_HOOK_LINE, True

        keyword = keyword.strip()
        display_keyword = keyword if keyword else "이것"

        # 키워드 문자 합으로 시작 템플릿을 결정론적으로 고른다 (같은 입력이면 같은 결과).
        base_index = (sum(ord(char) for char in keyword) % len(templates)) if keyword else 0

        # 최근 이력과 너무 비슷하면 다음 템플릿으로 순환하며 회피한다 (Hook 다양성 향상 +
        # 최근 Hook 중복 방지). 전부 비슷하면 어쩔 수 없이 기본 후보를 그대로 사용한다
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

    def _score_hook(
        self,
        hook_type: str,
        pattern_type: str,
        pattern_plan: Dict[str, Any],
        topic_intelligence: Dict[str, Any],
        brand_profile: Dict[str, Any],
        hook_line: str,
        is_diverse: bool,
    ) -> Dict[str, Any]:
        reasons: List[str] = []
        score = 0.5

        ideal_hook = self.PATTERN_HOOK_MAP.get(pattern_type)

        if ideal_hook and hook_type == ideal_hook:
            score += 0.25
            reasons.append("pattern_type에 가장 적합한 훅 타입 사용(+0.25)")
        elif ideal_hook:
            score -= 0.1
            reasons.append("pattern_type의 이상적인 훅 타입과 다름(-0.1)")

        confidence_score = topic_intelligence.get("confidence_score")
        if isinstance(confidence_score, (int, float)):
            adjustment = round((float(confidence_score) - 0.5) * 0.3, 4)
            score += adjustment
            reasons.append(f"topic confidence_score({confidence_score}) 반영({adjustment:+.4f})")

        if pattern_plan.get("fallback_used"):
            score -= 0.15
            reasons.append("pattern_plan.fallback_used로 감점(-0.15)")

        if is_diverse:
            score += 0.05
            reasons.append("최근 이력과 겹치지 않는 다양한 훅(+0.05)")
        else:
            score -= 0.1
            reasons.append("최근 이력과 유사한 훅이 감지됨(-0.1)")

        banned_words = brand_profile.get("banned_words") if isinstance(brand_profile, dict) else None
        if isinstance(banned_words, list):
            for word in banned_words:
                word_text = str(word or "").strip()
                if word_text and word_text in hook_line:
                    score -= 0.2
                    reasons.append(f"hook_line에 브랜드 금지어 '{word_text}' 포함(-0.2)")
                    break

        score = round(max(0.0, min(1.0, score)), 4)

        return {
            "hook_score": score,
            "hook_score_reason": ("; ".join(reasons) + ".") if reasons else "기본 점수.",
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
