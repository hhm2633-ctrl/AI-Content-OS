from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image


class CardNewsQualityChecker:
    """
    생성된 카드뉴스 결과물(PNG 파일 + layout_result/rendering_result 메타데이터)을
    자동 QA한다. 새로운 렌더링/엔진 로직은 추가하지 않고 이미 만들어진 결과만 읽어서
    검사한다.

    검사 자체가 실패해도 예외를 던지지 않고 qa_score=0.0, passed=False,
    warnings에 에러를 기록한 안전한 결과를 반환한다. 이 결과가 workflow_failed를
    유발하는 일은 없다.

    Phase M7(CardNews Intelligence, 실제 사용 연결) 확장: Evidence/Social Proof/
    Debate는 "실제 데이터가 원래 없어서 unavailable"인 경우를 품질 실패로 감점하지
    않는다 - 실제 데이터가 있는데(available=True) 적용하지 못한 경우만 감점한다.
    이 조건부 채점은 `_conditional_ok()`로 통일해 처리한다.
    """

    MIN_CARD_COUNT = 4
    EXPECTED_RESOLUTION = (1024, 1024)
    READABILITY_PASS_THRESHOLD = 0.5

    # 총점 100 유지. story_flow_applied/evidence_applied/social_proof_applied/
    # debate_applied/attribution_present/readability_ok 6개는 Phase M7 Production
    # Quality 확장 항목이다. Phase M8(CardNews Production Quality)에서 10개 항목
    # (typography_hierarchy_ok ~ unlicensed_asset_not_rendered)이 추가되면서
    # 기존 14개 항목의 배점을 비례 축소(100 -> 70)하고 새 항목에 30점을
    # 배분했다 - 총점 100은 그대로 유지한다.
    # evidence_applied/social_proof_applied/debate_applied/attribution_present는
    # "가용하지 않으면 자동 통과"(조건부 채점)로 계산된다 - CHECK_POINTS의
    # 배점 자체는 고정이며, `_calculate_score()`에서 조건부로 적용 여부를 판정한다.
    CHECK_POINTS = {
        "card_count_ok": 8,
        "layout_result_exists": 6,
        "rendering_result_exists": 4,
        "layout_applied": 8,
        "cta_slide_exists": 7,
        "highlight_exists": 3,
        "resolution_ok": 5,
        "story_flow_applied": 6,
        "evidence_applied": 6,
        "social_proof_applied": 4,
        "debate_applied": 4,
        "slide_continuity_ok": 4,
        "readability_ok": 3,
        "attribution_present": 2,
        # Phase M8 (CardNews Production Quality) 확장 항목.
        "typography_hierarchy_ok": 4,
        "cover_readability_ok": 4,
        "mobile_readability_ok": 4,
        "visual_rhythm_ok": 3,
        "text_overflow_free": 3,
        "contrast_ok": 3,
        "source_legible": 1,
        "cta_focus_ok": 2,
        "prohibited_fake_screenshot_absent": 3,
        "unlicensed_asset_not_rendered": 3,
    }

    # evidence_applied/social_proof_applied/debate_applied/attribution_present는
    # 대응하는 "가용성" 플래그가 False이면 자동으로 만점 처리된다(조건부 채점).
    # Phase M8 확장 항목도 동일한 원칙("데이터가 원래 없어서 unavailable인
    # 경우를 감점하지 않는다")을 따른다 - 대응하는 *_exists/*_relevant 가용성
    # 플래그가 False면 자동 통과 처리한다.
    CONDITIONAL_CHECKS = {
        "evidence_applied": "evidence_available",
        "social_proof_applied": "social_proof_available",
        "debate_applied": "debate_required",
        "attribution_present": "attribution_needed",
        "typography_hierarchy_ok": "typography_result_exists",
        "cover_readability_ok": "design_quality_exists",
        "mobile_readability_ok": "mobile_readability_result_exists",
        "visual_rhythm_ok": "visual_rhythm_result_exists",
        "text_overflow_free": "mobile_readability_result_exists",
        "contrast_ok": "mobile_readability_result_exists",
        "source_legible": "source_legibility_relevant",
        "cta_focus_ok": "cta_focus_relevant",
    }

    PENALTIES = {
        "fallback_used": 15,
        "png_missing": 20,
        "zero_size_file": 15,
        "card_count_insufficient": 20,
        "layout_rendering_missing": 15,
    }

    PASS_THRESHOLD = 0.6

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def check(self, card_news_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            return self._check(card_news_result or {})
        except Exception as error:
            return {
                "qa_score": 0.0,
                "passed": False,
                "checks": {},
                "warnings": [f"QA 검사 중 예외 발생: {error}"],
                "recommendations": ["QA 검사 실패 - 카드뉴스 결과물을 수동으로 확인하세요."],
            }

    def _check(self, card_news_result: Dict[str, Any]) -> Dict[str, Any]:
        cards = card_news_result.get("cards", [])
        if not isinstance(cards, list):
            cards = []

        layout_result = card_news_result.get("layout_result")
        rendering_result = card_news_result.get("rendering_result")
        design_quality_result = card_news_result.get("design_quality_result")

        layout_result_exists = isinstance(layout_result, dict) and bool(layout_result)
        rendering_result_exists = isinstance(rendering_result, dict) and bool(rendering_result)
        design_quality_exists = isinstance(design_quality_result, dict) and bool(design_quality_result)

        warnings: List[str] = []

        missing_files, zero_size_files, resolutions = self._inspect_files(cards, warnings)

        png_exists = len(cards) > 0 and not missing_files
        file_size_ok = not zero_size_files
        card_count_ok = len(cards) >= self.MIN_CARD_COUNT

        resolution_ok = bool(resolutions) and all(
            size == self.EXPECTED_RESOLUTION or size[0] == size[1] for size in resolutions
        )

        layout_applied = bool(rendering_result.get("layout_applied")) if rendering_result_exists else False
        layout_fallback_used = bool(layout_result.get("fallback_used")) if layout_result_exists else False
        rendering_fallback_used = bool(rendering_result.get("fallback_used")) if rendering_result_exists else True
        fallback_used = layout_fallback_used or rendering_fallback_used

        highlight_keywords = layout_result.get("highlight_keywords") if layout_result_exists else None
        highlight_exists = isinstance(highlight_keywords, list) and len(highlight_keywords) > 0

        cta_slide_exists = self._has_cta_slide(layout_result if layout_result_exists else {})

        # Phase M7 (CardNews Intelligence, 실제 사용 연결): CardNewsModule.run()이
        # 이미 계산해 card_news_result에 실어 둔 실제 사용 여부(available/applied)를
        # 그대로 읽는다 - 새 판정 로직을 추가하지 않는다.
        story_flow_result = card_news_result.get("story_flow_result") or {}
        evidence_result = card_news_result.get("evidence_result") or {}
        social_proof_result = card_news_result.get("social_proof_result") or {}
        debate_result = card_news_result.get("debate_result") or {}
        typography_result = card_news_result.get("typography_result") or {}
        visual_rhythm_result = card_news_result.get("visual_rhythm_result") or {}
        mobile_readability_result = card_news_result.get("mobile_readability_result") or {}

        story_flow_applied = bool(story_flow_result.get("flow_matched")) and bool(
            story_flow_result.get("applied_roles")
        )
        evidence_available = bool(evidence_result.get("evidence_available"))
        evidence_applied = bool(card_news_result.get("evidence_applied"))
        social_proof_available = bool(social_proof_result.get("available"))
        social_proof_applied = bool(card_news_result.get("social_proof_applied"))
        debate_should_apply = bool(debate_result.get("should_apply"))
        debate_applied = bool(debate_result.get("applied"))
        debate_skip_reason = str(debate_result.get("skip_reason", "") or "").strip()
        debate_required = debate_should_apply and not debate_skip_reason
        attribution_needed = evidence_applied or social_proof_applied
        attribution_present = bool(card_news_result.get("attribution_present"))
        slide_continuity_ok = self._check_slide_continuity(cards)
        readability_ok = (
            isinstance(design_quality_result, dict)
            and float(design_quality_result.get("readability_score", 0.0) or 0.0) >= self.READABILITY_PASS_THRESHOLD
        )

        # Phase M8 (CardNews Production Quality): CardNewsModule.run()이 이미
        # 계산해 card_news_result에 실어 둔 typography_result/visual_rhythm_result/
        # mobile_readability_result를 그대로 읽어 검사한다 - 새 렌더링/판정 로직을
        # 여기서 새로 만들지 않는다.
        typography_result_exists = isinstance(typography_result, dict) and bool(typography_result.get("checks"))
        visual_rhythm_result_exists = isinstance(visual_rhythm_result, dict) and bool(
            visual_rhythm_result.get("assignments")
        )
        mobile_readability_result_exists = isinstance(mobile_readability_result, dict) and bool(
            mobile_readability_result
        )

        typography_hierarchy_ok = bool(typography_result.get("typography_hierarchy_ok"))

        slide_readability = design_quality_result.get("slide_readability") if design_quality_exists else []
        slide_readability = slide_readability if isinstance(slide_readability, list) else []
        cover_readability_entry = next(
            (item for item in slide_readability if isinstance(item, dict) and item.get("page") == 1),
            None,
        )
        cover_readability_ok = bool(
            design_quality_exists
            and design_quality_result.get("cover_optimized")
            and isinstance(cover_readability_entry, dict)
            and cover_readability_entry.get("headline_ok")
            and cover_readability_entry.get("body_ok")
        )

        mobile_readability_ok = bool(mobile_readability_result.get("mobile_readability_ok"))
        visual_rhythm_ok = bool(visual_rhythm_result.get("varied"))
        text_overflow_free = bool(mobile_readability_result.get("overflow_free"))
        contrast_ok = bool(mobile_readability_result.get("contrast_ok"))

        cta_slide_exists_flag = cta_slide_exists
        source_legibility_relevant = bool(mobile_readability_result_exists and (evidence_applied or social_proof_applied))
        cta_focus_relevant = bool(mobile_readability_result_exists and cta_slide_exists_flag)
        source_legible = bool(mobile_readability_result.get("source_legible"))
        cta_focus_ok = bool(mobile_readability_result.get("cta_legible"))

        # Part A(Evidence 오사용 방지) 계약과 교차 검증: 실제로 적용된 자산/인용이
        # 규칙을 어기지 않았는지 이미 계산된 필드(asset_role/render_allowed/
        # is_opinion/label/applied)만으로 재확인한다 - 새 판정 기준을 만들지 않는다.
        evidence_top_asset = evidence_result.get("top_evidence_asset") or {}
        social_proof_selected = social_proof_result.get("selected") or []
        social_proof_top = social_proof_selected[0] if social_proof_selected else {}

        fake_screenshot_risk = False
        if evidence_applied and evidence_top_asset.get("asset_role") != "topic_evidence":
            fake_screenshot_risk = True
        if social_proof_applied and not (social_proof_top.get("is_opinion") and social_proof_top.get("label")):
            fake_screenshot_risk = True
        prohibited_fake_screenshot_absent = not fake_screenshot_risk

        evidence_assets = evidence_result.get("evidence_assets") or []
        unlicensed_asset_not_rendered = all(
            not (isinstance(asset, dict) and asset.get("applied") and not asset.get("render_allowed", False))
            for asset in evidence_assets
            if isinstance(asset, dict)
        )

        checks = {
            "png_exists": png_exists,
            "card_count_ok": card_count_ok,
            "file_size_ok": file_size_ok,
            "resolution_ok": resolution_ok,
            "layout_result_exists": layout_result_exists,
            "rendering_result_exists": rendering_result_exists,
            "layout_applied": layout_applied,
            "layout_fallback_used": layout_fallback_used,
            "rendering_fallback_used": rendering_fallback_used,
            "fallback_used": fallback_used,
            "highlight_exists": highlight_exists,
            "cta_slide_exists": cta_slide_exists,
            "design_quality_exists": design_quality_exists,
            "story_flow_applied": story_flow_applied,
            "evidence_available": evidence_available,
            "evidence_applied": evidence_applied,
            "social_proof_available": social_proof_available,
            "social_proof_applied": social_proof_applied,
            "debate_should_apply": debate_should_apply,
            "debate_required": debate_required,
            "debate_applied": debate_applied,
            "attribution_needed": attribution_needed,
            "attribution_present": attribution_present,
            "slide_continuity_ok": slide_continuity_ok,
            "readability_ok": readability_ok,
            "typography_result_exists": typography_result_exists,
            "typography_hierarchy_ok": typography_hierarchy_ok,
            "cover_readability_ok": cover_readability_ok,
            "mobile_readability_result_exists": mobile_readability_result_exists,
            "mobile_readability_ok": mobile_readability_ok,
            "visual_rhythm_result_exists": visual_rhythm_result_exists,
            "visual_rhythm_ok": visual_rhythm_ok,
            "text_overflow_free": text_overflow_free,
            "contrast_ok": contrast_ok,
            "source_legibility_relevant": source_legibility_relevant,
            "source_legible": source_legible,
            "cta_focus_relevant": cta_focus_relevant,
            "cta_focus_ok": cta_focus_ok,
            "prohibited_fake_screenshot_absent": prohibited_fake_screenshot_absent,
            "unlicensed_asset_not_rendered": unlicensed_asset_not_rendered,
        }

        self._collect_warnings(
            warnings=warnings,
            checks=checks,
            cards=cards,
            missing_files=missing_files,
            zero_size_files=zero_size_files,
            resolutions=resolutions,
        )

        qa_score = self._calculate_score(checks)
        passed = qa_score >= self.PASS_THRESHOLD and card_count_ok and png_exists and file_size_ok

        recommendations = self._build_recommendations(checks, missing_files, zero_size_files)

        return {
            "qa_score": qa_score,
            "passed": bool(passed),
            "checks": checks,
            "warnings": warnings,
            "recommendations": recommendations,
        }

    def _inspect_files(
        self,
        cards: List[Dict[str, Any]],
        warnings: List[str],
    ) -> Tuple[List[Any], List[Any], List[Tuple[int, int]]]:
        missing_files: List[Any] = []
        zero_size_files: List[Any] = []
        resolutions: List[Tuple[int, int]] = []

        for card in cards:
            if not isinstance(card, dict):
                continue

            card_path = card.get("card_path")

            if not card_path:
                missing_files.append(card.get("index"))
                continue

            path = Path(card_path)

            if not path.exists():
                missing_files.append(card_path)
                continue

            try:
                file_size = path.stat().st_size
            except Exception as error:
                warnings.append(f"파일 크기 확인 실패 ({card_path}): {error}")
                file_size = 0

            if file_size <= 0:
                zero_size_files.append(card_path)
                continue

            try:
                with Image.open(path) as image:
                    resolutions.append(image.size)
            except Exception as error:
                warnings.append(f"이미지 해상도 확인 실패 ({card_path}): {error}")

        return missing_files, zero_size_files, resolutions

    def _has_cta_slide(self, layout_result: Dict[str, Any]) -> bool:
        slide_designs = layout_result.get("slide_designs")

        if isinstance(slide_designs, list):
            for design in slide_designs:
                if isinstance(design, dict) and (design.get("role") == "cta" or design.get("cta_area")):
                    return True

        return False

    def _check_slide_continuity(self, cards: List[Dict[str, Any]]) -> bool:
        """
        Phase M7 (CardNews Intelligence) - Slide 연결성. 카드 index가 1..N으로
        빠짐/중복 없이 이어지고, 각 카드에 headline이 실제로 있는지만 확인한다
        (새로운 NLP 분석이 아니라 이미 존재하는 `cards` 구조에 대한 순수 구조
        점검).
        """
        if not cards:
            return False

        indexes = [card.get("index") for card in cards if isinstance(card, dict)]
        expected_indexes = list(range(1, len(cards) + 1))

        if indexes != expected_indexes:
            return False

        return all(
            str(card.get("headline", "")).strip()
            for card in cards
            if isinstance(card, dict)
        )

    def _collect_warnings(
        self,
        warnings: List[str],
        checks: Dict[str, Any],
        cards: List[Dict[str, Any]],
        missing_files: List[Any],
        zero_size_files: List[Any],
        resolutions: List[Tuple[int, int]],
    ) -> None:
        if not cards:
            warnings.append("cards가 비어 있습니다.")

        if missing_files:
            warnings.append(f"누락된 PNG 파일 {len(missing_files)}건: {missing_files}")

        if zero_size_files:
            warnings.append(f"0KB 파일 {len(zero_size_files)}건: {zero_size_files}")

        if not checks.get("card_count_ok"):
            warnings.append(f"카드 개수 부족: {len(cards)}장 (최소 {self.MIN_CARD_COUNT}장 필요).")

        if not checks.get("resolution_ok") and resolutions:
            warnings.append(f"정사각형이 아니거나 예상 해상도와 다른 이미지가 있습니다: {resolutions}")

        if not checks.get("layout_result_exists"):
            warnings.append("layout_result가 없습니다.")

        if not checks.get("rendering_result_exists"):
            warnings.append("rendering_result가 없습니다.")

        if checks.get("rendering_fallback_used"):
            warnings.append("rendering_result.fallback_used=True (레이아웃 인지 렌더링이 일부/전부 fallback됨).")
        elif checks.get("layout_fallback_used"):
            warnings.append("layout_result.fallback_used=True (안전한 기존 레이아웃으로 대체 선택됨).")

        if not checks.get("cta_slide_exists"):
            warnings.append("CTA 슬라이드를 찾을 수 없습니다.")

        if not checks.get("highlight_exists"):
            warnings.append("highlight_keywords가 비어 있습니다.")

        if not checks.get("story_flow_applied"):
            warnings.append("story_flow_result가 없거나 서사 role이 슬라이드에 적용되지 않았습니다.")

        if checks.get("evidence_available") and not checks.get("evidence_applied"):
            warnings.append("evidence 자산이 실제로 있었는데 카드뉴스에 적용되지 않았습니다.")

        if checks.get("social_proof_available") and not checks.get("social_proof_applied"):
            warnings.append("social proof 후보가 실제로 있었는데 카드뉴스에 적용되지 않았습니다.")

        if checks.get("debate_required") and not checks.get("debate_applied"):
            warnings.append("debate 질문이 적용 대상이었는데 실제로 추가되지 않았습니다.")

        if checks.get("attribution_needed") and not checks.get("attribution_present"):
            warnings.append("evidence/social proof를 사용했는데 출처 표시가 없습니다.")

        if not checks.get("slide_continuity_ok"):
            warnings.append("슬라이드 index 순서가 어긋나거나 headline이 빈 슬라이드가 있습니다.")

        if not checks.get("readability_ok"):
            warnings.append(f"readability_score가 기준({self.READABILITY_PASS_THRESHOLD}) 미만입니다.")

        if checks.get("typography_result_exists") and not checks.get("typography_hierarchy_ok"):
            warnings.append("일부 슬라이드 텍스트가 typography_rules 기준(글자 수/줄 수)을 초과합니다.")

        if checks.get("design_quality_exists") and not checks.get("cover_readability_ok"):
            warnings.append("커버(1장) 슬라이드가 Cover Optimization 기준(문장 수/가독성)을 충족하지 않습니다.")

        if checks.get("mobile_readability_result_exists") and not checks.get("mobile_readability_ok"):
            warnings.append("모바일 축소 가독성 기준(폰트/여백/대비/줄 수)을 충족하지 않습니다.")

        if checks.get("visual_rhythm_result_exists") and not checks.get("visual_rhythm_ok"):
            warnings.append("슬라이드 시각 스타일이 다양화되지 않아 모든 장이 동일한 템플릿처럼 보일 수 있습니다.")

        if checks.get("mobile_readability_result_exists") and not checks.get("contrast_ok"):
            warnings.append("일부 텍스트/배경 색상 조합이 WCAG AA 대비 기준(4.5:1)에 미달합니다.")

        if checks.get("source_legibility_relevant") and not checks.get("source_legible"):
            warnings.append("출처 표시 글자 크기가 모바일 축소 상태에서 판독 어려울 수 있습니다.")

        if checks.get("cta_focus_relevant") and not checks.get("cta_focus_ok"):
            warnings.append("CTA 문구 글자 크기가 모바일 축소 상태에서 판독 어려울 수 있습니다.")

        if not checks.get("prohibited_fake_screenshot_absent"):
            warnings.append("경쟁계정 자료/미확인 인용이 실제 사건 증거나 원문 캡처처럼 표시되었을 위험이 있습니다.")

        if not checks.get("unlicensed_asset_not_rendered"):
            warnings.append("저작권 사용이 허용되지 않은(render_allowed=False) 자산이 실제로 렌더링에 적용되었습니다.")

    def _calculate_score(self, checks: Dict[str, Any]) -> float:
        points = 0

        for check_name, weight in self.CHECK_POINTS.items():
            if self._conditional_ok(checks, check_name):
                points += weight

        if checks.get("fallback_used"):
            points -= self.PENALTIES["fallback_used"]

        if not checks.get("png_exists"):
            points -= self.PENALTIES["png_missing"]

        if not checks.get("file_size_ok"):
            points -= self.PENALTIES["zero_size_file"]

        if not checks.get("card_count_ok"):
            points -= self.PENALTIES["card_count_insufficient"]

        if not checks.get("layout_result_exists") or not checks.get("rendering_result_exists"):
            points -= self.PENALTIES["layout_rendering_missing"]

        points = max(0, min(100, points))

        return round(points / 100, 4)

    def _conditional_ok(self, checks: Dict[str, Any], check_name: str) -> bool:
        """
        요구사항: 데이터가 원래 없어서 unavailable인 경우를 품질 실패로 감점하지
        않는다 - 실제 데이터가 있는데 적용하지 못한 경우만 감점한다.

        CONDITIONAL_CHECKS에 등록된 항목은 대응하는 가용성 플래그가 False면
        (애초에 적용할 대상이 없었으면) 자동으로 통과 처리한다. 그 외 항목은
        기존과 동일하게 checks[check_name] 값을 그대로 쓴다.
        """
        availability_key = self.CONDITIONAL_CHECKS.get(check_name)

        if availability_key is not None and not checks.get(availability_key):
            return True

        return bool(checks.get(check_name))

    def _build_recommendations(
        self,
        checks: Dict[str, Any],
        missing_files: List[Any],
        zero_size_files: List[Any],
    ) -> List[str]:
        recommendations = []

        if missing_files:
            recommendations.append("누락된 PNG 파일을 다시 생성하거나 CardNewsModule 실행 로그를 확인하세요.")

        if zero_size_files:
            recommendations.append("0KB로 저장된 파일이 있습니다. 디스크 공간/쓰기 권한을 확인하세요.")

        if not checks.get("card_count_ok"):
            recommendations.append("카드가 4장 미만입니다. content_result.slides를 확인하세요.")

        if not checks.get("layout_applied"):
            recommendations.append("레이아웃 인지 렌더링이 적용되지 않았습니다. layout_result/rendering_result를 점검하세요.")

        if checks.get("rendering_fallback_used"):
            recommendations.append("일부 카드가 기본 렌더링으로 fallback되었습니다. 원인을 로그에서 확인하세요.")
        elif checks.get("layout_fallback_used"):
            recommendations.append("중복·품질 보호 규칙으로 안전한 기존 레이아웃이 선택됐습니다. 필요하면 선택 근거만 검토하세요.")

        if not checks.get("cta_slide_exists"):
            recommendations.append("CTA 슬라이드가 감지되지 않았습니다. 콘텐츠 슬라이드 구조를 확인하세요.")

        if not checks.get("highlight_exists"):
            recommendations.append("강조 키워드가 없습니다. HighlightEngine 결과를 확인하세요.")

        if not checks.get("story_flow_applied"):
            recommendations.append("Story Flow가 슬라이드에 적용되지 않았습니다. Content Output Contract를 확인하세요.")

        if checks.get("evidence_available") and not checks.get("evidence_applied"):
            recommendations.append("사용 가능한 Evidence 자산이 있었는데 적용되지 않았습니다. _apply_evidence_asset()을 확인하세요.")

        if checks.get("social_proof_available") and not checks.get("social_proof_applied"):
            recommendations.append("사용 가능한 Social Proof 후보가 있었는데 적용되지 않았습니다. _apply_social_proof_quote()를 확인하세요.")

        if checks.get("debate_required") and not checks.get("debate_applied"):
            recommendations.append("Debate 질문이 적용 대상이었는데 반영되지 않았습니다. 글자 수 제한/충돌 방지 로직을 확인하세요.")

        if checks.get("attribution_needed") and not checks.get("attribution_present"):
            recommendations.append("출처 표시가 누락되었습니다. Evidence/Social Proof 적용 로직에 attribution을 포함하세요.")

        if not checks.get("slide_continuity_ok"):
            recommendations.append("슬라이드 연결성 문제가 있습니다. index 순서/headline 존재 여부를 확인하세요.")

        if not checks.get("readability_ok"):
            recommendations.append("가독성 점수가 낮습니다. CardNewsTextOptimizer 결과를 확인하세요.")

        if checks.get("typography_result_exists") and not checks.get("typography_hierarchy_ok"):
            recommendations.append("typography_rules 기준을 초과한 슬라이드가 있습니다. 문장을 줄이거나 분리하세요.")

        if checks.get("design_quality_exists") and not checks.get("cover_readability_ok"):
            recommendations.append("커버 슬라이드를 제목 1개 + 보조 문장 1개 이내로 정리하세요.")

        if checks.get("mobile_readability_result_exists") and not checks.get("mobile_readability_ok"):
            recommendations.append("모바일 축소 가독성 기준을 확인하세요. MobileReadabilityChecker 결과를 참고하세요.")

        if checks.get("visual_rhythm_result_exists") and not checks.get("visual_rhythm_ok"):
            recommendations.append("서사 role에 맞춰 슬라이드 시각 스타일을 다양화하세요(VisualRhythmSelector 참고).")

        if checks.get("mobile_readability_result_exists") and not checks.get("contrast_ok"):
            recommendations.append("텍스트/배경 색상 대비를 WCAG AA 기준(4.5:1) 이상으로 조정하세요.")

        if not checks.get("prohibited_fake_screenshot_absent"):
            recommendations.append("competitor_reference 자산이나 라벨 없는 인용이 사건 증거처럼 쓰이지 않았는지 확인하세요.")

        if not checks.get("unlicensed_asset_not_rendered"):
            recommendations.append("render_allowed=False인 자산이 렌더링에 쓰였습니다. _apply_evidence_asset 게이트를 확인하세요.")

        if not recommendations:
            recommendations.append("특별한 개선 필요 사항이 없습니다.")

        return recommendations
