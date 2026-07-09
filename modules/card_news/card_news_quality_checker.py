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
    """

    MIN_CARD_COUNT = 4
    EXPECTED_RESOLUTION = (1024, 1024)

    CHECK_POINTS = {
        "card_count_ok": 15,
        "layout_result_exists": 15,
        "rendering_result_exists": 10,
        "layout_applied": 20,
        "cta_slide_exists": 15,
        "highlight_exists": 10,
        "resolution_ok": 15,
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

        layout_result_exists = isinstance(layout_result, dict) and bool(layout_result)
        rendering_result_exists = isinstance(rendering_result, dict) and bool(rendering_result)

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

        checks = {
            "png_exists": png_exists,
            "card_count_ok": card_count_ok,
            "file_size_ok": file_size_ok,
            "resolution_ok": resolution_ok,
            "layout_result_exists": layout_result_exists,
            "rendering_result_exists": rendering_result_exists,
            "layout_applied": layout_applied,
            "fallback_used": fallback_used,
            "highlight_exists": highlight_exists,
            "cta_slide_exists": cta_slide_exists,
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

    def _collect_warnings(
        self,
        warnings: List[str],
        checks: Dict[str, bool],
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

        if checks.get("fallback_used"):
            warnings.append("rendering_result.fallback_used=True (레이아웃 인지 렌더링이 일부/전부 fallback됨).")

        if not checks.get("cta_slide_exists"):
            warnings.append("CTA 슬라이드를 찾을 수 없습니다.")

        if not checks.get("highlight_exists"):
            warnings.append("highlight_keywords가 비어 있습니다.")

    def _calculate_score(self, checks: Dict[str, bool]) -> float:
        points = 0

        for check_name, weight in self.CHECK_POINTS.items():
            if checks.get(check_name):
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

    def _build_recommendations(
        self,
        checks: Dict[str, bool],
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

        if checks.get("fallback_used"):
            recommendations.append("일부 카드가 기본 렌더링으로 fallback되었습니다. 원인을 로그에서 확인하세요.")

        if not checks.get("cta_slide_exists"):
            recommendations.append("CTA 슬라이드가 감지되지 않았습니다. 콘텐츠 슬라이드 구조를 확인하세요.")

        if not checks.get("highlight_exists"):
            recommendations.append("강조 키워드가 없습니다. HighlightEngine 결과를 확인하세요.")

        if not recommendations:
            recommendations.append("특별한 개선 필요 사항이 없습니다.")

        return recommendations
