"""CardNews Topic Intelligence Engine V1.

카드뉴스 4장 제작이 아니라 "카드뉴스를 만들 주제를 고르는" 엔진.

세 구성요소로 이루어진다:

1. CommunityIssueRadar
   TrendCollector 결과 items(네이트판/FM코리아/보배드림/네이버 등)를
   제목/키워드 기반으로 유사 이슈 클러스터로 묶고, 클러스터 단위로
   freshness / source_repeat / community_reaction / explainability /
   evidence_feasibility / image_feasibility / risk를 점수화한다.
   제목 길이는 점수 항목에 포함하지 않는다.

2. InstagramLearningSelector
   knowledge/patterns/pattern_registry.jsonl에서 domain이
   content_pattern / engagement_mechanic인 패턴을 읽어 각 topic 후보에
   대해 hook_fit / story_structure_fit / visual_layout_fit / cta_fit /
   manipulation_risk를 산출한다. status=CANDIDATE 패턴은 낮은 가중치의
   "참고 신호(미검증)"로만 쓰고, PROMOTED/VERIFIED가 아니면 확정 법칙
   표현을 절대 쓰지 않는다. DM CTA 계열 mechanic은 기본 추천하지 않고
   risk flag로만 기록한다 (promotion_policy.md의 Release Selection 절 준수).

3. CardNewsTopicSelector
   위 두 점수를 합쳐 카드뉴스 후보 TOP 5를 만들고, 각 후보에
   recommended_angle / hook_candidates / story_structure /
   cta_recommendation / visual_direction / risk_flags / evidence_needs /
   go_no_go / selection_reason을 붙인다.

fallback-first 계약: 이 엔진의 어떤 실패도 workflow를 죽이지 않는다.
모든 예외는 fallback result(dict)로 흡수된다.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

KNOWN_COMMUNITY_SOURCES = {"nate_pann", "fmkorea", "bobaedream"}
KNOWN_NEWS_SOURCES = {"naver_news"}
KNOWN_SOURCES = KNOWN_COMMUNITY_SOURCES | KNOWN_NEWS_SOURCES

# CANDIDATE는 미검증 가설이므로 참고 신호로만 반영한다(promotion_policy.md).
STATUS_WEIGHTS = {
    "PROMOTED": 1.0,
    "VERIFIED": 0.7,
    "CANDIDATE": 0.2,
}

CANDIDATE_REFERENCE_LABEL = "[참고 신호·미검증 CANDIDATE]"

EXPLAINABILITY_SIGNALS = [
    "이유", "방법", "정리", "총정리", "비교", "변화", "원인", "결과",
    "논란", "후기", "기준", "혜택", "지원", "꿀팁", "순위", "리스트",
    "가지", "체크", "주의", "차이",
]

IMAGE_SENSITIVE_SIGNALS = [
    "사망", "시신", "자살", "유혈", "참사", "학대", "폭행 영상", "성폭",
]

RISK_SIGNALS = {
    "rumor_risk": ["루머", "카더라", "찌라시", "의혹", "추측", "지라시"],
    "defamation_risk": ["명예훼손", "폭로", "저격", "불륜", "사생활"],
    "medical_high_risk": ["질병", "치료", "백신", "부작용", "진단", "암 투병", "다이어트약"],
    "legal_high_risk": ["소송", "판결", "법원", "구속", "기소", "형량"],
    "political_high_risk": ["대통령", "국회", "선거", "정당", "여당", "야당", "탄핵"],
}

CRITICAL_RISK_FLAGS = {"rumor_risk", "defamation_risk"}
HIGH_RISK_FLAGS = {"medical_high_risk", "legal_high_risk", "political_high_risk"}


def _normalize_text(text: str) -> str:
    normalized = str(text or "").lower()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[^0-9a-z가-힣 ]+", "", normalized)
    return normalized.strip()


# 커뮤니티 글 제목에 흔한 범용 토큰. 이런 단어 1개 겹침만으로
# 무관한 글이 같은 이슈로 묶이는 오탐을 막기 위해 클러스터링에서 제외한다.
CLUSTER_STOPWORDS = {
    "진짜", "정말", "오늘", "근데", "그냥", "너무", "완전", "약간",
    "그리고", "요즘", "지금", "이거", "저거", "다들", "제발",
}


def _tokens(text: str) -> set:
    return {
        token
        for token in _normalize_text(text).split()
        if token not in CLUSTER_STOPWORDS
    }


class CommunityIssueRadar:
    """TrendCollector items를 유사 이슈 클러스터로 묶고 점수화한다."""

    SIMILARITY_THRESHOLD = 0.5

    def __init__(self, config: Optional[Dict[str, Any]] = None, now: Optional[datetime] = None):
        self.config = config or {}
        self.now = now or datetime.now()

    def build_clusters(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        clusters: List[Dict[str, Any]] = []

        for item in items or []:
            if not isinstance(item, dict):
                continue

            title = str(item.get("keyword", "")).strip()
            if not title:
                continue

            item_tokens = _tokens(title)
            target = None

            for cluster in clusters:
                if self._is_similar(item_tokens, cluster["tokens"]):
                    target = cluster
                    break

            if target is None:
                target = {
                    "cluster_id": f"issue_cluster_{len(clusters) + 1}",
                    "tokens": set(item_tokens),
                    "items": [],
                }
                clusters.append(target)

            target["tokens"] |= item_tokens
            target["items"].append(item)

        scored = []
        for cluster in clusters:
            scored.append(self._score_cluster(cluster))
        return scored

    def _is_similar(self, tokens_a: set, tokens_b: set) -> bool:
        if not tokens_a or not tokens_b:
            return False

        overlap = len(tokens_a & tokens_b)
        smaller = min(len(tokens_a), len(tokens_b))
        if smaller == 0:
            return False

        ratio = overlap / smaller

        # 범용 단어 1개 겹침만으로 묶이는 오탐 방지: 비율 조건에 더해
        # 의미 토큰 2개 이상 겹침을 요구한다. (한쪽 제목이 통째로
        # 포함되는 완전 일치 수준일 때만 예외)
        if overlap >= 2 and ratio >= self.SIMILARITY_THRESHOLD:
            return True

        return ratio >= 1.0

    def _score_cluster(self, cluster: Dict[str, Any]) -> Dict[str, Any]:
        items = cluster["items"]
        representative = max(
            items,
            key=lambda item: (
                int(item.get("quality_score", 0) or 0),
                int(item.get("score", 0) or 0),
            ),
        )
        title = str(representative.get("keyword", "")).strip()
        combined_text = " ".join(
            str(item.get("keyword", "")) + " " + str(item.get("summary", ""))
            for item in items
        )

        sources = sorted({str(item.get("source", "unknown")) for item in items})
        community_sources = sorted(set(sources) & KNOWN_COMMUNITY_SOURCES)

        risk_flags = self._detect_risk_flags(combined_text)
        risk_penalty = self._risk_penalty(risk_flags)

        scores = {
            "freshness_score": self._freshness_score(items),
            "source_repeat_score": self._source_repeat_score(sources),
            "community_reaction_score": self._community_reaction_score(community_sources, items),
            "card_news_explainability_score": self._explainability_score(combined_text, items),
            "evidence_feasibility_score": self._evidence_feasibility_score(items),
            "image_feasibility_score": self._image_feasibility_score(combined_text),
            "risk_penalty": risk_penalty,
        }

        community_total = (
            0.15 * scores["freshness_score"]
            + 0.20 * scores["source_repeat_score"]
            + 0.20 * scores["community_reaction_score"]
            + 0.20 * scores["card_news_explainability_score"]
            + 0.15 * scores["evidence_feasibility_score"]
            + 0.10 * scores["image_feasibility_score"]
            - risk_penalty
        )
        community_total = round(max(0.0, min(100.0, community_total)), 2)

        return {
            "cluster_id": cluster["cluster_id"],
            "topic_title": title,
            "sources": sources,
            "community_sources": community_sources,
            "items": items,
            "scores": scores,
            "community_total_score": community_total,
            "risk_flags": risk_flags,
            "has_source_binding": self._has_source_binding(items),
        }

    def _freshness_score(self, items: List[Dict[str, Any]]) -> int:
        best = 0
        parsed_any = False

        for item in items:
            raw = item.get("published_at") or item.get("collected_at") or ""
            moment = self._parse_datetime(str(raw))
            if moment is None:
                continue

            parsed_any = True
            age_hours = max(0.0, (self.now - moment).total_seconds() / 3600.0)

            if age_hours <= 6:
                score = 100
            elif age_hours <= 24:
                score = 85
            elif age_hours <= 72:
                score = 65
            elif age_hours <= 168:
                score = 45
            else:
                score = 30

            best = max(best, score)

        return best if parsed_any else 50

    def _parse_datetime(self, raw: str) -> Optional[datetime]:
        raw = raw.strip()
        if not raw:
            return None
        try:
            moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return moment.replace(tzinfo=None)
        except ValueError:
            return None

    def _source_repeat_score(self, sources: List[str]) -> int:
        known = [source for source in sources if source in KNOWN_SOURCES]
        count = len(set(known))
        if count >= 4:
            return 100
        if count == 3:
            return 85
        if count == 2:
            return 60
        if count == 1:
            return 20
        return 0

    def _community_reaction_score(
        self,
        community_sources: List[str],
        items: List[Dict[str, Any]],
    ) -> int:
        count = len(community_sources)
        if count >= 3:
            base = 100
        elif count == 2:
            base = 80
        elif count == 1:
            base = 55
        else:
            base = 20

        # 커뮤니티 수집 항목에 reaction 지표가 붙어 있으면 소폭 가산.
        for item in items:
            for field in ("comment_count", "view_count", "reaction_count"):
                try:
                    if int(item.get(field, 0) or 0) > 0:
                        return min(100, base + 10)
                except (TypeError, ValueError):
                    continue

        return base

    def _explainability_score(self, combined_text: str, items: List[Dict[str, Any]]) -> int:
        # 제목 길이는 의도적으로 점수 항목에서 제외한다.
        score = 25

        if any(str(item.get("summary", "")).strip() for item in items):
            score += 20

        normalized = _normalize_text(combined_text)
        matched = sum(1 for signal in EXPLAINABILITY_SIGNALS if signal in normalized)
        score += min(45, matched * 15)

        if re.search(r"\d", normalized):
            score += 10

        return min(100, score)

    def _evidence_feasibility_score(self, items: List[Dict[str, Any]]) -> int:
        score = 0

        if any(str(item.get("link", "")).strip() for item in items):
            score += 40
        if any(str(item.get("publisher", "")).strip() for item in items):
            score += 20
        if any(str(item.get("summary", "")).strip() for item in items):
            score += 20
        if any(not bool(item.get("is_fallback", False)) for item in items):
            score += 20

        return min(100, score)

    def _image_feasibility_score(self, combined_text: str) -> int:
        score = 75
        normalized = _normalize_text(combined_text)

        for signal in IMAGE_SENSITIVE_SIGNALS:
            if _normalize_text(signal) in normalized:
                score -= 25
                break

        return max(10, min(100, score))

    def _detect_risk_flags(self, combined_text: str) -> List[str]:
        normalized = _normalize_text(combined_text)
        flags = []

        for flag, signals in RISK_SIGNALS.items():
            if any(_normalize_text(signal) in normalized for signal in signals):
                flags.append(flag)

        return flags

    def _risk_penalty(self, risk_flags: List[str]) -> int:
        penalty = 0
        for flag in risk_flags:
            penalty += 25 if flag in CRITICAL_RISK_FLAGS else 15
        return penalty

    def _has_source_binding(self, items: List[Dict[str, Any]]) -> bool:
        for item in items:
            source = str(item.get("source", ""))
            method = str(item.get("collection_method", ""))
            has_link = bool(str(item.get("link", "")).strip())
            is_placeholder = method == "placeholder_fallback" or source == "placeholder"

            if is_placeholder:
                continue
            if has_link or source in KNOWN_SOURCES:
                return True

        return False


class InstagramLearningSelector:
    """pattern_registry.jsonl의 Instagram 학습 패턴을 참고 신호로만 소비한다."""

    RELEVANT_DOMAINS = {"content_pattern", "engagement_mechanic"}

    def __init__(
        self,
        registry_path: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.config = config or {}
        self.registry_path = Path(
            registry_path or "knowledge/patterns/pattern_registry.jsonl"
        )
        self.patterns = self._load_patterns()

    def _load_patterns(self) -> List[Dict[str, Any]]:
        if not self.registry_path.exists():
            return []

        latest: Dict[str, Dict[str, Any]] = {}
        try:
            with open(self.registry_path, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(record, dict):
                        continue
                    if record.get("domain") not in self.RELEVANT_DOMAINS:
                        continue
                    pattern_id = str(record.get("pattern_id", ""))
                    if not pattern_id:
                        continue
                    latest[pattern_id] = record
        except OSError:
            return []

        return list(latest.values())

    def is_available(self) -> bool:
        return bool(self.patterns)

    def _pattern_weight(self, pattern: Dict[str, Any]) -> float:
        status = str(pattern.get("status", "")).upper()
        return STATUS_WEIGHTS.get(status, 0.0)

    def _pattern_note(self, pattern: Dict[str, Any]) -> str:
        status = str(pattern.get("status", "")).upper()
        name = str(pattern.get("name", pattern.get("pattern_id", "")))

        if status in ("PROMOTED", "VERIFIED"):
            return f"[{status}] {name}"

        # CANDIDATE 이하: 확정 법칙 표현 금지, 참고 신호로만 기록.
        return f"{CANDIDATE_REFERENCE_LABEL} {name}"

    def assess(self, cluster: Dict[str, Any]) -> Dict[str, Any]:
        text = _normalize_text(
            cluster.get("topic_title", "")
            + " "
            + " ".join(
                str(item.get("keyword", "")) + " " + str(item.get("summary", ""))
                for item in cluster.get("items", [])
            )
        )

        hook_fit = 0.5
        story_structure_fit = 0.5
        visual_layout_fit = 0.5
        cta_fit = 0.5
        manipulation_risk = False
        used_patterns: List[str] = []
        risk_flags: List[str] = []

        for pattern in self.patterns:
            weight = self._pattern_weight(pattern)
            if weight <= 0.0:
                continue

            pattern_id = str(pattern.get("pattern_id", ""))
            is_dm_mechanic = (
                pattern.get("domain") == "engagement_mechanic"
                and ("dm" in pattern_id.lower() or "dm" in _normalize_text(pattern.get("name", "")))
            )

            if is_dm_mechanic:
                # DM/댓글 키워드 funnel mechanic은 절대 기본 추천하지 않는다.
                # cta_fit에 가산하지 않고 risk flag로만 기록한다.
                manipulation_risk = True
                if "dm_cta_manipulation_risk" not in risk_flags:
                    risk_flags.append("dm_cta_manipulation_risk")
                used_patterns.append(
                    self._pattern_note(pattern) + " — DM/키워드 funnel은 risk로만 기록, 추천 제외"
                )
                continue

            applied = False

            if "quote_reversal" in pattern_id and self._matches_any(
                text, ["발언", "논란", "반전", "인용", "말했다", "충격"]
            ):
                hook_fit += weight * 0.5
                applied = True

            if "numbered_curation" in pattern_id and self._matches_any(
                text, ["가지", "리스트", "총정리", "방법", "순위", "top", "곳"]
            ):
                story_structure_fit += weight * 0.5
                applied = True

            if "notice_style" in pattern_id and self._matches_any(
                text, ["공지", "기관", "지역", "지원", "정책", "안내"]
            ):
                visual_layout_fit += weight * 0.4
                applied = True

            if "character_illustration" in pattern_id and self._matches_any(
                text, ["건강", "병원", "공공", "캠페인"]
            ):
                visual_layout_fit += weight * 0.3
                applied = True

            if applied:
                used_patterns.append(self._pattern_note(pattern))

        # save/comment 계열 기본 CTA는 topic 설명 가능성에 따라 소폭 조정.
        if self._matches_any(text, ["정리", "방법", "혜택", "꿀팁", "기준"]):
            cta_fit += 0.2

        clamp = lambda value: round(max(0.0, min(1.0, value)), 4)

        return {
            "hook_fit": clamp(hook_fit),
            "story_structure_fit": clamp(story_structure_fit),
            "visual_layout_fit": clamp(visual_layout_fit),
            "cta_fit": clamp(cta_fit),
            "manipulation_risk": manipulation_risk,
            "risk_flags": risk_flags,
            "used_patterns": used_patterns,
        }

    def _matches_any(self, text: str, signals: List[str]) -> bool:
        return any(_normalize_text(signal) in text for signal in signals)


class CardNewsTopicSelector:
    """Community 점수와 Instagram fit을 합쳐 카드뉴스 TOP 5 후보를 만든다."""

    TOP_N = 5
    HIGH_RISK_EVIDENCE_THRESHOLD = 60
    EXPLAINABILITY_GO_THRESHOLD = 40

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def select(
        self,
        clusters: List[Dict[str, Any]],
        instagram_selector: InstagramLearningSelector,
    ) -> List[Dict[str, Any]]:
        candidates = []

        for cluster in clusters:
            fit = instagram_selector.assess(cluster)
            candidates.append(self._build_candidate(cluster, fit))

        candidates.sort(key=lambda candidate: candidate["total_score"], reverse=True)
        return candidates[: self.TOP_N]

    def _build_candidate(
        self,
        cluster: Dict[str, Any],
        fit: Dict[str, Any],
    ) -> Dict[str, Any]:
        scores = cluster["scores"]
        instagram_fit_total = round(
            (
                fit["hook_fit"]
                + fit["story_structure_fit"]
                + fit["visual_layout_fit"]
                + fit["cta_fit"]
            )
            / 4.0
            * 100.0,
            2,
        )
        total_score = round(
            0.7 * cluster["community_total_score"] + 0.3 * instagram_fit_total,
            2,
        )

        risk_flags = list(cluster.get("risk_flags", [])) + list(fit.get("risk_flags", []))
        evidence_needs = self._build_evidence_needs(cluster, risk_flags)
        go_no_go, go_reason = self._decide_go_no_go(cluster, risk_flags)
        title = cluster["topic_title"]

        return {
            "topic_title": title,
            "source_cluster": cluster["cluster_id"],
            "source_items": [
                {
                    "keyword": item.get("keyword", ""),
                    "source": item.get("source", "unknown"),
                    "link": item.get("link", ""),
                    "published_at": item.get("published_at", ""),
                    "collection_method": item.get("collection_method", ""),
                    "is_fallback": bool(item.get("is_fallback", False)),
                }
                for item in cluster.get("items", [])
            ],
            "total_score": total_score,
            "score_breakdown": {
                **scores,
                "community_total_score": cluster["community_total_score"],
                "hook_fit": fit["hook_fit"],
                "story_structure_fit": fit["story_structure_fit"],
                "visual_layout_fit": fit["visual_layout_fit"],
                "cta_fit": fit["cta_fit"],
                "instagram_fit_total": instagram_fit_total,
            },
            "recommended_angle": self._recommended_angle(cluster),
            "hook_candidates": self._hook_candidates(title),
            "story_structure": [
                "1. 이슈 요약: 무슨 일이 있었는지 한 장으로 정리",
                "2. 맥락/원인: 왜 이 이슈가 나왔는지 배경 설명",
                "3. 반응/쟁점: 커뮤니티에서 갈리는 지점 정리",
                "4. 정리/시사점: 독자가 가져갈 결론과 체크포인트",
            ],
            "cta_recommendation": self._cta_recommendation(fit),
            "visual_direction": self._visual_direction(cluster, fit),
            "risk_flags": risk_flags,
            "evidence_needs": evidence_needs,
            "go_no_go": go_no_go,
            "selection_reason": self._selection_reason(cluster, fit, total_score, go_reason),
            "instagram_pattern_notes": fit.get("used_patterns", []),
        }

    def _build_evidence_needs(
        self,
        cluster: Dict[str, Any],
        risk_flags: List[str],
    ) -> List[str]:
        needs = []

        if cluster["scores"]["evidence_feasibility_score"] < 60:
            needs.append("원문 링크/공식 발표 등 1차 근거 확보 필요")
        if not cluster.get("has_source_binding"):
            needs.append("실제 수집 source binding 확보 필요")
        if any(flag in HIGH_RISK_FLAGS for flag in risk_flags):
            needs.append("고위험(의료/법률/정치) 주제: 공식 기관 근거 필수")
        if "rumor_risk" in risk_flags:
            needs.append("루머성 신호 감지: 사실 확인 전 제작 금지")
        if "defamation_risk" in risk_flags:
            needs.append("명예훼손 위험 신호: 실명/특정인 언급 검증 필수")

        return needs

    def _decide_go_no_go(
        self,
        cluster: Dict[str, Any],
        risk_flags: List[str],
    ) -> (str, str):
        evidence_score = cluster["scores"]["evidence_feasibility_score"]
        explainability = cluster["scores"]["card_news_explainability_score"]

        if not cluster.get("has_source_binding"):
            return "NO_GO", "실제 source binding이 없어 제작 불가 (Instagram 패턴만으로는 GO 불가)."

        if "defamation_risk" in risk_flags:
            return "NO_GO", "명예훼손 위험 신호가 감지되어 제작 보류."

        if "rumor_risk" in risk_flags and evidence_score < self.HIGH_RISK_EVIDENCE_THRESHOLD:
            return "NO_GO", "루머성 신호가 있고 근거가 부족해 제작 보류."

        high_risk = [flag for flag in risk_flags if flag in HIGH_RISK_FLAGS]
        if high_risk and evidence_score < self.HIGH_RISK_EVIDENCE_THRESHOLD:
            return "NO_GO", f"고위험 카테고리({', '.join(high_risk)})인데 근거가 부족해 제작 보류."

        if explainability < self.EXPLAINABILITY_GO_THRESHOLD:
            return "NO_GO", "카드뉴스로 설명 가능한 구조가 부족해 제작 보류."

        return "GO", "source binding 존재, 치명 risk 없음, 카드뉴스 설명 구조 확보."

    def _recommended_angle(self, cluster: Dict[str, Any]) -> str:
        if cluster.get("community_sources"):
            return (
                f"커뮤니티({', '.join(cluster['community_sources'])})에서 반복 언급된 이슈를 "
                "사실관계 중심으로 정리해 주는 앵글"
            )
        return "뉴스 기반 이슈를 초보자도 이해할 수 있게 정리해 주는 앵글"

    def _hook_candidates(self, title: str) -> List[str]:
        return [
            f"\"{title}\" 아직도 모르면 손해인 이유",
            f"{title}, 커뮤니티가 뒤집어진 진짜 이유 3가지",
            f"{title} 한 장 정리 — 지금 알아야 할 핵심만",
            f"다들 {title} 얘기하는데, 정작 중요한 건 이것",
        ]

    def _cta_recommendation(self, fit: Dict[str, Any]) -> Dict[str, Any]:
        # DM CTA는 manipulation/funnel risk 때문에 기본 추천에서 제외한다.
        cta_type = "save" if fit["cta_fit"] >= 0.6 else "comment"
        return {
            "cta_type": cta_type,
            "reason": (
                "정보 정리형 카드뉴스에 적합한 저장/댓글 CTA를 기본으로 사용. "
                "DM/댓글 키워드 funnel CTA는 risk flag로만 기록하고 추천하지 않음."
            ),
        }

    def _visual_direction(self, cluster: Dict[str, Any], fit: Dict[str, Any]) -> str:
        direction = "텍스트 오버레이 중심의 정보 정리형 레이아웃 (1080x1080, 4장 구성 기준)"

        if fit["visual_layout_fit"] > 0.6:
            direction += (
                f" — {CANDIDATE_REFERENCE_LABEL} 공지/기관형 이슈에서는 실사진 비중을 "
                "높이는 레이아웃이 관찰된 바 있어 참고만 함"
            )

        if cluster["scores"]["image_feasibility_score"] < 50:
            direction += " / 민감 소재 감지: 인물·현장 이미지 대신 추상 그래픽 권장"

        return direction

    def _selection_reason(
        self,
        cluster: Dict[str, Any],
        fit: Dict[str, Any],
        total_score: float,
        go_reason: str,
    ) -> str:
        parts = [
            f"community_total={cluster['community_total_score']}",
            f"source_repeat={cluster['scores']['source_repeat_score']}",
            f"reaction={cluster['scores']['community_reaction_score']}",
            f"instagram_fit(참고 신호)={round((fit['hook_fit'] + fit['story_structure_fit'] + fit['visual_layout_fit'] + fit['cta_fit']) / 4.0, 4)}",
            f"total={total_score}",
        ]
        return f"{'; '.join(parts)}. {go_reason}"


class CardNewsTopicIntelligence:
    """세 구성요소를 묶는 facade. 어떤 실패도 workflow를 죽이지 않는다."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        registry_path: Optional[Path] = None,
        now: Optional[datetime] = None,
    ):
        self.config = config or {}
        self.registry_path = registry_path
        self.now = now

    def build(self, trend_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            return self._build(trend_result or {})
        except Exception as error:
            return self._fallback_result(f"topic_intelligence_error: {error}")

    def _build(self, trend_result: Dict[str, Any]) -> Dict[str, Any]:
        trends = trend_result.get("trends", [])
        if not isinstance(trends, list):
            trends = []

        radar = CommunityIssueRadar(self.config, now=self.now)
        clusters = radar.build_clusters(trends)

        if not clusters:
            return self._fallback_result("no_trend_items_available")

        instagram_selector = InstagramLearningSelector(
            registry_path=self.registry_path,
            config=self.config,
        )
        selector = CardNewsTopicSelector(self.config)
        top_candidates = selector.select(clusters, instagram_selector)

        selected_candidate = next(
            (candidate for candidate in top_candidates if candidate["go_no_go"] == "GO"),
            top_candidates[0] if top_candidates else {},
        )

        used_sources = sorted(
            {
                str(item.get("source", "unknown"))
                for candidate in top_candidates
                for item in candidate.get("source_items", [])
            }
            & KNOWN_SOURCES
        )

        warnings = []
        if not instagram_selector.is_available():
            warnings.append("pattern_registry를 읽지 못해 Instagram 학습 신호 없이 산출함.")
        if selected_candidate and selected_candidate.get("go_no_go") != "GO":
            warnings.append("GO 후보가 없어 최고점 후보를 NO_GO 상태로 반환함 (제작 진행 금지).")

        return {
            "status": "topic_intelligence_completed",
            "candidate_count": len(top_candidates),
            "top_candidates": top_candidates,
            "selected_candidate": selected_candidate,
            "used_sources": used_sources,
            "instagram_learning_used": instagram_selector.is_available(),
            "instagram_learning_policy": "candidate_patterns_reference_only",
            "fallback_used": False,
            "warnings": warnings,
            "created_at": datetime.now().isoformat(),
        }

    def _fallback_result(self, reason: str) -> Dict[str, Any]:
        return {
            "status": "topic_intelligence_completed",
            "candidate_count": 0,
            "top_candidates": [],
            "selected_candidate": {},
            "used_sources": [],
            "instagram_learning_used": False,
            "instagram_learning_policy": "candidate_patterns_reference_only",
            "fallback_used": True,
            "warnings": [f"fallback: {reason}"],
            "created_at": datetime.now().isoformat(),
        }
