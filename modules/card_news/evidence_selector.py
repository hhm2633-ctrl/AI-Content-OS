import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class EvidenceSelector:
    """
    CardNews Intelligence (Phase M7 - Evidence 오사용 방지 보정) - Evidence Selection.

    이전 버전의 결함: screenshot_path가 디스크에 실제 존재한다는 이유만으로
    evidence asset을 "사용 가능"으로 취급했다. 파일이 존재한다는 사실과 그
    자산이 (1) 지금 주제와 실제로 관련이 있는지, (2) 우리 콘텐츠에 저작권상
    사용해도 되는지는 완전히 다른 질문이다. 이 버전은 그 세 가지를 명확히
    분리한다:

    - candidate_found: 파일이 실제로 디스크에 있는지
    - topic_relevant: selected_topic/research_result와 실질적으로 관련 있는지
      (공통 단어 1개만 일치해도 통과시키지 않는다 - 최소 2개 이상의 의미
      있는 용어 일치 + 임계치 이상의 점수를 함께 요구한다)
    - render_allowed: copyright_status가 실제 게시용 렌더링에 쓸 수 있는
      값인지
    - asset_role: Instagram Research/Competitor Learning에서 온 자산은
      기본적으로 "competitor_reference"(경쟁 계정 참고 자료)로 취급하고,
      "topic_evidence"(이 사건/주제의 실제 증거)로는 강한 확인 신호가 없는 한
      승격하지 않는다. competitor_reference는 카드뉴스 본문 배경에 자동
      적용되지 않는다(card_news_module.py의 게이트에서 최종 차단).
    - available: 위 네 조건을 모두 만족해야 True. 파일 존재만으로는 False.

    존재하지 않는 asset_path를 만들지 않는다. 다운로드되지 않은 이미지를
    있다고 기록하지 않는다. AI 생성 이미지는 실제 자산이 하나도 없을 때만
    fallback 후보로 표시하고, evidence로 위장하지 않는다.
    """

    RESEARCH_RESULT_PATH = Path("storage/research/research_result.json")
    POSTS_PATH = Path("storage/research/instagram/posts.json")

    NEWS_SOURCES = ("naver_news",)
    COMMUNITY_SOURCES = ("nate_pann", "fmkorea", "bobaedream")

    REAL_PHOTO_IMAGE_SOURCES = ("news_image", "product_image", "real_photo")
    ONSITE_PHOTO_IMAGE_SOURCES = ("post_capture", "comment_capture")

    ASSET_TYPES = (
        "official",
        "news",
        "real_photo",
        "article_screenshot",
        "social_screenshot",
        "comment_screenshot",
        "statistic",
        "none",
    )

    # 저작권상 자동 게시용 Renderer에 실제 사용해도 되는 값만 render_allowed=True.
    # 출처 표시는 사용 허가를 대신하지 않는다 - attribution_required와 별개로
    # copyright_status 자체가 허용 목록에 있어야 한다.
    RENDER_ALLOWED_COPYRIGHT_STATUSES = (
        "owned",
        "licensed",
        "public_domain",
        "official_reuse_allowed",
        "user_supplied_with_permission",
    )
    RENDER_BLOCKED_COPYRIGHT_STATUSES = (
        "third_party_unlicensed_reference",
        "unknown",
        "restricted",
    )

    # 관련성 판정: 최소 2개 이상의 의미 있는 용어가 겹쳐야 하고, 점수도
    # 임계치 이상이어야 한다 - 단어 1개 우연 일치로 통과시키지 않는다.
    RELEVANCE_THRESHOLD = 0.34
    MIN_MATCHED_TERMS = 2
    MIN_TERM_LENGTH = 2

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def select(
        self,
        image_strategy_result: Optional[Dict[str, Any]] = None,
        generated_image_paths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        try:
            return self._select(image_strategy_result or {}, generated_image_paths or [])
        except Exception as error:
            return self._empty_result(reason=f"evidence_selection_exception: {error}")

    def _select(
        self,
        image_strategy_result: Dict[str, Any],
        generated_image_paths: List[str],
    ) -> Dict[str, Any]:
        research_result = self._load_research_result()
        research_context = research_result.get("research_context")
        source_signals = research_context.get("source_signals") if isinstance(research_context, dict) else {}
        if not isinstance(source_signals, dict):
            source_signals = {}

        topic_terms = self._build_topic_terms(research_result)

        # 신호 수준 정보(기존 유지, 정보용 - "무엇이 수집됐는지"의 요약).
        evidence_items: List[Dict[str, Any]] = [
            self._source_item("news_article", self.NEWS_SOURCES, source_signals, "기사/뉴스 수집 신호"),
            self._source_item("sns_capture", self.COMMUNITY_SOURCES, source_signals, "커뮤니티/SNS 반응 수집 신호"),
            self._photo_item("real_photo", self.REAL_PHOTO_IMAGE_SOURCES, image_strategy_result),
            self._photo_item("onsite_photo", self.ONSITE_PHOTO_IMAGE_SOURCES, image_strategy_result),
            self._unavailable_item("official_announcement", "공식 발표를 수집하는 소스가 아직 없음."),
            self._unavailable_item("statistics", "이번 주제에 대한 실제 통계 데이터를 수집하는 소스가 아직 없음."),
        ]

        evidence_assets = self._collect_screenshot_assets(topic_terms)

        usable_assets = [asset for asset in evidence_assets if asset["available"]]

        fallback_asset = None
        if not usable_assets and generated_image_paths:
            fallback_asset = {
                "asset_type": "none",
                "asset_path": generated_image_paths[0],
                "is_ai_generated": True,
                "treated_as_evidence": False,
                "selection_reason": "실제 evidence 자산이 없어 AI 생성 이미지를 fallback으로만 표시함(evidence 아님).",
            }

        available_items = [item for item in evidence_items if item["available"]]
        evidence_score = round(sum(item["score"] for item in evidence_items) / len(evidence_items), 4) if evidence_items else 0.0

        return {
            "evidence_items": evidence_items,
            "available_count": len(available_items),
            "evidence_score": evidence_score,
            "top_evidence_type": available_items[0]["type"] if available_items else "",
            "evidence_assets": evidence_assets,
            "candidate_found_count": sum(1 for asset in evidence_assets if asset["candidate_found"]),
            "topic_relevant_count": sum(1 for asset in evidence_assets if asset["topic_relevant"]),
            "render_allowed_count": sum(1 for asset in evidence_assets if asset["render_allowed"]),
            "evidence_available": bool(usable_assets),
            "top_evidence_asset": usable_assets[0] if usable_assets else None,
            "fallback_asset": fallback_asset,
            "fallback_used": False,
        }

    # ---- 주제 관련성 ----

    def _build_topic_terms(self, research_result: Dict[str, Any]) -> Set[str]:
        terms: Set[str] = set()

        topic_intelligence = research_result.get("topic_intelligence")
        if isinstance(topic_intelligence, dict):
            for keyword in topic_intelligence.get("keywords") or []:
                terms.update(self._tokenize(str(keyword)))
            category = topic_intelligence.get("category")
            if category:
                terms.update(self._tokenize(str(category)))

        for field in ("keyword", "title", "summary"):
            value = research_result.get(field)
            if isinstance(value, str):
                terms.update(self._tokenize(value))

        for point in research_result.get("key_points") or []:
            if isinstance(point, str):
                terms.update(self._tokenize(point))

        research_context = research_result.get("research_context")
        if isinstance(research_context, dict):
            for field in ("keyword", "category", "cluster"):
                value = research_context.get(field)
                if isinstance(value, str):
                    terms.update(self._tokenize(value))

        return terms

    def _tokenize(self, text: str) -> Set[str]:
        if not text:
            return set()

        # 해시태그/기호를 제거하고 공백 기준으로 나눈다. 완벽한 형태소 분석기는
        # 아니지만, "단어 1개 우연 일치"를 걸러내기 위한 최소 길이 필터와
        # 함께 쓰면 실용적인 관련성 신호를 만든다.
        cleaned = re.sub(r"[#\.\,\!\?\"'\(\)\[\]:;]", " ", text)
        tokens = [token.strip().lower() for token in cleaned.split()]
        return {token for token in tokens if len(token) >= self.MIN_TERM_LENGTH}

    def _score_relevance(self, candidate_terms: Set[str], topic_terms: Set[str]) -> Dict[str, Any]:
        if not topic_terms or not candidate_terms:
            return {"score": 0.0, "matched_terms": [], "relevant": False}

        matched = sorted(candidate_terms & topic_terms)
        # 후보 쪽 용어 수 대비 겹침 비율 - 후보 텍스트가 길어도(해시태그+캡션)
        # 실제로 겹치는 비율이 낮으면 점수가 낮아지도록 한다.
        score = round(len(matched) / max(1, min(len(candidate_terms), len(topic_terms)) or 1), 4)
        score = min(1.0, score)

        relevant = len(matched) >= self.MIN_MATCHED_TERMS and score >= self.RELEVANCE_THRESHOLD

        return {"score": score, "matched_terms": matched, "relevant": relevant}

    # ---- 실제 자산(스크린샷) 수집 ----

    def _collect_screenshot_assets(self, topic_terms: Set[str]) -> List[Dict[str, Any]]:
        posts = self._load_posts()
        assets: List[Dict[str, Any]] = []

        for post in posts:
            if not isinstance(post, dict):
                continue

            screenshot_path = post.get("screenshot_path")

            if not isinstance(screenshot_path, str) or not screenshot_path.strip():
                continue

            candidate_found = Path(screenshot_path).exists() and Path(screenshot_path).is_file()

            candidate_terms = self._tokenize(str(post.get("caption_text", "")))
            for hashtag in post.get("hashtags") or []:
                candidate_terms.update(self._tokenize(str(hashtag)))

            relevance = self._score_relevance(candidate_terms, topic_terms)

            # Instagram Research/Competitor Learning 출처는 기본적으로 경쟁
            # 계정 참고 자료다 - "이 사건/주제의 실제 증거"로 확인할 강한
            # 신호(예: 공식 발표 계정, 뉴스 소스 등)가 이 프로젝트에는 아직
            # 없으므로 topic_evidence로 승격하지 않는다. 정직하게 gap으로
            # 남긴다.
            asset_role = "competitor_reference"
            copyright_status = "third_party_unlicensed_reference"
            render_allowed = copyright_status in self.RENDER_ALLOWED_COPYRIGHT_STATUSES
            analysis_only = not render_allowed

            available = bool(
                candidate_found
                and relevance["relevant"]
                and render_allowed
                and asset_role == "topic_evidence"
            )

            if not candidate_found:
                selection_status = "rejected_file_missing"
                rejection_reason = f"screenshot_path가 디스크에 없음: {screenshot_path}"
            elif not relevance["relevant"]:
                selection_status = "rejected_irrelevant"
                rejection_reason = (
                    f"주제 관련 용어 일치 {len(relevance['matched_terms'])}건/점수 {relevance['score']}로 "
                    f"기준(최소 {self.MIN_MATCHED_TERMS}건, 점수 {self.RELEVANCE_THRESHOLD}) 미달."
                )
            elif asset_role != "topic_evidence":
                selection_status = "rejected_competitor_reference"
                rejection_reason = (
                    "Instagram Research 출처는 경쟁 계정 참고 자료(competitor_reference)로 분류되며, "
                    "이 사건/주제의 실제 증거(topic_evidence)로 확인된 것이 아니라 카드뉴스 본문에 "
                    "자동 적용하지 않음."
                )
            elif not render_allowed:
                selection_status = "rejected_unlicensed"
                rejection_reason = f"copyright_status '{copyright_status}'는 자동 게시용 렌더링에 사용할 수 없음."
            else:
                selection_status = "accepted"
                rejection_reason = ""

            assets.append({
                "asset_type": "social_screenshot",
                "asset_path": screenshot_path if candidate_found else None,
                "source_url": str(post.get("post_url", "")),
                "source_name": str(post.get("account_handle", "")),
                "copyright_status": copyright_status,
                "attribution_required": True,
                "trust_score": 0.6 if candidate_found else 0.0,
                "selection_reason": (
                    f"Instagram Research가 실제로 수집해 디스크에 저장한 스크린샷 파일이 존재함"
                    f"({screenshot_path})."
                    if candidate_found
                    else f"screenshot_path가 기록되어 있으나 파일이 디스크에 없음({screenshot_path})."
                ),
                "candidate_found": candidate_found,
                "topic_relevance_score": relevance["score"],
                "relevance_evidence": relevance["matched_terms"],
                "relevance_threshold": self.RELEVANCE_THRESHOLD,
                "topic_relevant": relevance["relevant"],
                "asset_role": asset_role,
                "analysis_only": analysis_only,
                "render_allowed": render_allowed,
                "available": available,
                "applied": False,
                "selection_status": selection_status,
                "rejection_reason": rejection_reason,
            })

        return assets

    def _source_item(
        self,
        evidence_type: str,
        source_ids: "tuple",
        source_signals: Dict[str, Any],
        label: str,
    ) -> Dict[str, Any]:
        matched_sources = []
        total_count = 0

        for source_id in source_ids:
            signal = source_signals.get(source_id)

            if isinstance(signal, dict) and signal.get("success") and int(signal.get("count", 0) or 0) > 0:
                matched_sources.append(source_id)
                total_count += int(signal.get("count", 0) or 0)

        available = bool(matched_sources)
        score = min(1.0, round(total_count / 10, 4)) if available else 0.0

        return {
            "type": evidence_type,
            "available": available,
            "score": score,
            "sources": matched_sources,
            "reason": (
                f"{label} {total_count}건 확인됨 ({', '.join(matched_sources)})."
                if available
                else f"{label}가 없거나 수집에 실패함."
            ),
        }

    def _photo_item(
        self,
        evidence_type: str,
        matching_image_sources: "tuple",
        image_strategy_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        need_ai_image = image_strategy_result.get("need_ai_image", True)
        image_source = str(image_strategy_result.get("image_source", ""))

        available = bool(image_source in matching_image_sources and not need_ai_image)

        return {
            "type": evidence_type,
            "available": available,
            "score": 0.8 if available else 0.0,
            "sources": [image_source] if available else [],
            "reason": (
                f"Image Strategy가 실제 이미지 소스 '{image_source}'를 선택함."
                if available
                else "Image Strategy가 AI 이미지 경로를 선택했거나 이 증거 유형에 맞는 실제 이미지 소스가 아님."
            ),
        }

    def _unavailable_item(self, evidence_type: str, reason: str) -> Dict[str, Any]:
        return {"type": evidence_type, "available": False, "score": 0.0, "sources": [], "reason": reason}

    def _load_research_result(self) -> Dict[str, Any]:
        return self._load_json(self.RESEARCH_RESULT_PATH, {})

    def _load_posts(self) -> List[Dict[str, Any]]:
        """
        bare list와 `{"posts": [...]}` 두 형식 모두 실제 데이터로 인식한다
        (social_proof_selector.py와 동일한 이유 - 실제 디스크의 데이터 형식이
        `InstagramResearchStorage.save_posts()`가 쓰는 bare list와 다르다).
        """
        data = self._load_json(self.POSTS_PATH, [])

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
            print(f"Evidence Selector Load Failed ({path}): {error}")
            return default

    def _empty_result(self, reason: str) -> Dict[str, Any]:
        return {
            "evidence_items": [],
            "available_count": 0,
            "evidence_score": 0.0,
            "top_evidence_type": "",
            "evidence_assets": [],
            "candidate_found_count": 0,
            "topic_relevant_count": 0,
            "render_allowed_count": 0,
            "evidence_available": False,
            "top_evidence_asset": None,
            "fallback_asset": None,
            "fallback_used": True,
            "reason": reason,
        }
