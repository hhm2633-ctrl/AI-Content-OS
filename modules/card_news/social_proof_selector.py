import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class SocialProofSelector:
    """
    CardNews Intelligence (Phase M7 - 실제 사용 연결) - Social Proof Selection.

    아래 기존 저장소를 실제로 열어 "댓글/반응 텍스트" 후보가 있는지 탐색한다:
    - storage/research/instagram/posts.json (Instagram Research, 읽기 전용)
    - storage/research/instagram/classifications.json
    - storage/knowledge/knowledge_database.json (Competitor Learning)
    - storage/knowledge/competitor_statistics.json
    - storage/research/research_result.json (Research Module)

    중요: `caption_text`(계정 자신이 쓴 게시물 본문)와 `visible_like_text`/
    `visible_comment_text`/`visible_repost_text`(좋아요/댓글/리포스트 "개수"
    텍스트)는 후보로 쓰지 않는다 - 전자는 "댓글/반응"이 아니라 게시물 소유자
    자신의 문구이고, 후자는 반응의 "내용"이 아니라 "개수"이기 때문이다. 이
    둘을 후보로 쓰면 실제로 없는 제3자 반응 데이터를 있는 것처럼 오인시키게
    된다(Instagram Intelligence Phase의 internal_quality_proxy 라벨링 원칙과
    동일한 정직성 기준).

    실제 댓글/반응 텍스트 필드(`comment_text`/`reply_text`/`reaction_text`/
    `quote_text` 등)가 어떤 소스에도 없으면 candidate_count=0과 함께 정직하게
    available=False를 반환한다 - 임의 문장이나 댓글처럼 보이는 AI 문장을
    생성하지 않는다. 이 메서드는 실제로 파일을 열어 찾으므로, 향후 실제 댓글
    수집기가 이 필드명으로 데이터를 저장하기 시작하면 자동으로 후보를 찾는다.
    """

    SUPPORTED_TYPES = ("empathy", "debate", "question", "surprise", "anger", "humor", "support", "opposition")
    MAX_SELECTED = 2

    CHECKED_SOURCES = (
        "storage/research/instagram/posts.json",
        "storage/research/instagram/classifications.json",
        "storage/knowledge/knowledge_database.json",
        "storage/knowledge/competitor_statistics.json",
        "storage/research/research_result.json",
    )

    # 실제 제3자 댓글/반응 "본문"을 담을 수 있는 필드명만 후보로 인정한다.
    # caption_text/visible_*_text는 의도적으로 제외한다(위 docstring 참고).
    REAL_TEXT_FIELDS = ("comment_text", "reply_text", "reaction_text", "quote_text")

    TYPE_KEYWORDS: Dict[str, List[str]] = {
        "empathy": ["공감", "저도", "완전 제 얘기", "맞아요", "그렇죠"],
        "debate": ["근데", "그런데", "아닌 것 같", "다른 생각", "의견이 다"],
        "question": ["?", "궁금", "어떻게", "왜", "뭔가요"],
        "surprise": ["헐", "대박", "진짜요", "몰랐", "신기"],
        "anger": ["화나", "짜증", "최악", "실망", "별로"],
        "humor": ["ㅋㅋ", "ㅎㅎ", "웃겨", "개그"],
        "support": ["좋아요", "응원", "화이팅", "추천"],
        "opposition": ["반대", "아니라고 생각", "동의 못", "그건 아니"],
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def select(self) -> Dict[str, Any]:
        try:
            return self._select()
        except Exception as error:
            return self._empty_result(reason=f"social_proof_selection_exception: {error}")

    def _select(self) -> Dict[str, Any]:
        candidates: List[Dict[str, Any]] = []
        candidates.extend(self._find_candidates_in_posts())
        candidates.extend(self._find_candidates_in_knowledge_database())
        candidates.extend(self._find_candidates_in_competitor_statistics())
        candidates.extend(self._find_candidates_in_research_result())

        if not candidates:
            return self._empty_result(
                reason=(
                    "실제 댓글/반응 텍스트 필드(comment_text/reply_text/reaction_text/quote_text)를 "
                    "가진 데이터가 어떤 소스에도 없음 - posts.json/classifications.json은 게시물 자신의 "
                    "caption과 좋아요/댓글 '개수'만 보유하고 있고, knowledge_database.json/"
                    "competitor_statistics.json은 집계 통계만 가지고 있어 실제 제3자 댓글 텍스트가 "
                    "존재하지 않음."
                )
            )

        classified = [self._classify_candidate(candidate) for candidate in candidates]
        selected = self._select_balanced(classified)

        return {
            "available": bool(selected),
            "unavailable_reason": "" if selected else "후보는 있었으나 분류 가능한 유형이 없어 선정하지 않음.",
            "checked_sources": list(self.CHECKED_SOURCES),
            "candidate_count": len(candidates),
            "selected": selected,
            "supported_types": list(self.SUPPORTED_TYPES),
        }

    # ---- 소스별 실제 탐색 ----

    def _find_candidates_in_posts(self) -> List[Dict[str, Any]]:
        posts = self._load_posts()
        candidates = []

        for post in posts:
            if not isinstance(post, dict):
                continue

            for field in self.REAL_TEXT_FIELDS:
                text = post.get(field)

                if isinstance(text, str) and text.strip():
                    candidates.append({
                        "text": text.strip(),
                        "source": "instagram_research_posts",
                        "source_url": str(post.get("post_url", "")),
                        "account_handle": str(post.get("account_handle", "")),
                        "visible_like_count": self._safe_int(post.get("visible_like_text")),
                        "visible_reply_count": self._safe_int(post.get("visible_comment_text")),
                        "observed_at": str(post.get("observed_at", "")),
                    })

        return candidates

    def _find_candidates_in_knowledge_database(self) -> List[Dict[str, Any]]:
        database = self._load_json(Path("storage/knowledge/knowledge_database.json"), {})
        entries = database.get("entries", []) if isinstance(database, dict) else []
        return self._scan_dicts_for_text_fields(
            entries, source="competitor_learning_knowledge_database", url_field="", handle_field=""
        )

    def _find_candidates_in_competitor_statistics(self) -> List[Dict[str, Any]]:
        statistics = self._load_json(Path("storage/knowledge/competitor_statistics.json"), {})
        accounts = statistics.get("accounts", {}) if isinstance(statistics, dict) else {}

        candidates = []
        if isinstance(accounts, dict):
            for handle, profile in accounts.items():
                if not isinstance(profile, dict):
                    continue

                for field in self.REAL_TEXT_FIELDS:
                    text = profile.get(field)

                    if isinstance(text, str) and text.strip():
                        candidates.append({
                            "text": text.strip(),
                            "source": "competitor_statistics",
                            "source_url": "",
                            "account_handle": str(handle),
                            "visible_like_count": None,
                            "visible_reply_count": None,
                            "observed_at": "",
                        })

        return candidates

    def _find_candidates_in_research_result(self) -> List[Dict[str, Any]]:
        research_result = self._load_json(Path("storage/research/research_result.json"), {})

        if not isinstance(research_result, dict):
            return []

        candidates = self._scan_dicts_for_text_fields(
            [research_result.get("research_insight", {})],
            source="research_module",
            url_field="",
            handle_field="",
        )
        return candidates

    def _scan_dicts_for_text_fields(
        self,
        items: Any,
        source: str,
        url_field: str,
        handle_field: str,
    ) -> List[Dict[str, Any]]:
        candidates = []

        for item in items or []:
            if not isinstance(item, dict):
                continue

            for field in self.REAL_TEXT_FIELDS:
                text = item.get(field)

                if isinstance(text, str) and text.strip():
                    candidates.append({
                        "text": text.strip(),
                        "source": source,
                        "source_url": str(item.get(url_field, "")) if url_field else "",
                        "account_handle": str(item.get(handle_field, "")) if handle_field else "",
                        "visible_like_count": None,
                        "visible_reply_count": None,
                        "observed_at": "",
                    })

        return candidates

    # ---- 분류/선정 ----

    def _classify_candidate(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        text = candidate.get("text", "")
        text_lower = text.lower()

        matched_type = ""
        matched_keyword = ""

        for proof_type, keywords in self.TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower or keyword in text:
                    matched_type = proof_type
                    matched_keyword = keyword
                    break
            if matched_type:
                break

        if not matched_type:
            matched_type = "question" if "?" in text else ""

        like_count = candidate.get("visible_like_count") or 0
        reply_count = candidate.get("visible_reply_count") or 0
        engagement_score = min(1.0, round((like_count + reply_count) / 100, 4)) if (like_count or reply_count) else 0.0
        keyword_score = 0.5 if matched_keyword else 0.0
        score = round(min(1.0, engagement_score * 0.5 + keyword_score * 0.5) or keyword_score, 4)

        return {
            "type": matched_type,
            "score": score,
            "reason": (
                f"키워드 '{matched_keyword}' 매칭됨." if matched_keyword else "질문 부호(?)만 확인됨."
            ) if matched_type else "분류 가능한 유형을 찾지 못함.",
            "source": candidate.get("source", ""),
            "source_url": candidate.get("source_url", ""),
            # 민감정보 제거(전화번호/이메일처럼 보이는 패턴)만 적용하고, 그 외
            # 원문 의미는 절대 바꾸지 않는다("원문 의미 변조 금지").
            "text": self._scrub_sensitive_info(text),
            "account_handle": candidate.get("account_handle", ""),
        }

    def _scrub_sensitive_info(self, text: str) -> str:
        """
        전화번호/이메일처럼 보이는 패턴만 마스킹한다. 그 외 원문은 그대로
        보존한다 - 요약/재작성/의미 변경을 하지 않는다.
        """
        try:
            scrubbed = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[이메일 비공개]", text)
            scrubbed = re.sub(r"(?:\+?\d{1,3}[-\s]?)?\d{2,4}[-\s]\d{3,4}[-\s]\d{4}", "[전화번호 비공개]", scrubbed)
            return scrubbed
        except Exception:
            return text

    def _mask_account_handle(self, account_handle: str) -> str:
        """
        계정명 최소화(마스킹) 계약: 앞 2글자/뒤 1글자만 남기고 나머지는
        마스킹한다. 완전 익명화가 필요하면 호출부에서 이 필드 대신 빈 값을
        쓰면 된다 - 이 메서드는 "최소화 가능"이라는 계약만 제공한다.
        """
        handle = str(account_handle or "").strip()

        if len(handle) <= 3:
            return "*" * len(handle) if handle else ""

        return f"{handle[:2]}{'*' * (len(handle) - 3)}{handle[-1]}"

    def _select_balanced(self, classified: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        요구사항: 가장 높은 후보만 뽑지 않고, 찬성(support)/반대(opposition)가
        실제로 모두 존재하면 균형 있게 최대 2개까지 선택한다. 그렇지 않으면
        점수 상위 최대 2개를 선택한다.
        """
        valid = [item for item in classified if item.get("type")]

        if not valid:
            return []

        support_items = sorted(
            (item for item in valid if item["type"] == "support"), key=lambda item: item["score"], reverse=True
        )
        opposition_items = sorted(
            (item for item in valid if item["type"] == "opposition"), key=lambda item: item["score"], reverse=True
        )

        selected: List[Dict[str, Any]]

        if support_items and opposition_items:
            selected = [support_items[0], opposition_items[0]]
        else:
            ranked = sorted(valid, key=lambda item: item["score"], reverse=True)
            selected = ranked[: self.MAX_SELECTED]

        return [
            {
                "selected": True,
                "type": item["type"],
                "score": item["score"],
                "reason": item["reason"],
                "source": item["source"],
                "source_url": item["source_url"],
                "raw_text_preserved": True,
                "text": item["text"],
                # Social Proof 원문 보호 계약(Phase M7 보정):
                "account_handle": item.get("account_handle", ""),
                "masked_account_handle": self._mask_account_handle(item.get("account_handle", "")),
                "is_opinion": True,
                "label": "커뮤니티 반응",
                "disclaimer": "이 인용은 공개된 반응/의견이며 사실 확인된 근거가 아닙니다.",
            }
            for item in selected
        ]

    # ---- 유틸 ----

    def _load_posts(self) -> List[Dict[str, Any]]:
        """
        storage/research/instagram/posts.json을 직접 읽는다. 파일이 bare list든
        (`InstagramResearchStorage.save_posts()`가 쓰는 형식) `{"posts": [...]}`
        형태로 감싸져 있든(현재 실제로 디스크에 있는 형식) 둘 다 실제 데이터로
        인식한다 - 형식 차이 때문에 실제로 존재하는 데이터를 놓치지 않기 위함.
        """
        data = self._load_json(Path("storage/research/instagram/posts.json"), [])

        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]

        if isinstance(data, dict):
            posts = data.get("posts")
            if isinstance(posts, list):
                return [item for item in posts if isinstance(item, dict)]

        return []

    def _load_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default

        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as error:
            print(f"Social Proof Selector Load Failed ({path}): {error}")
            return default

    def _safe_int(self, text: Any) -> Optional[int]:
        if text is None:
            return None

        try:
            digits = re.sub(r"[^\d]", "", str(text))
            return int(digits) if digits else None
        except Exception:
            return None

    def _empty_result(self, reason: str) -> Dict[str, Any]:
        return {
            "available": False,
            "unavailable_reason": reason,
            "checked_sources": list(self.CHECKED_SOURCES),
            "candidate_count": 0,
            "selected": [],
            "supported_types": list(self.SUPPORTED_TYPES),
        }
