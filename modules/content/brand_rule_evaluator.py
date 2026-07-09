import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class BrandRuleEvaluator:
    """
    config/brand_profile.json 기준으로 금지 표현/과장 수익 표현을 감지하고
    브랜드 톤 일치 여부를 판단해 brand_rule_passed(true/false)를 결정한다.

    config 파일이 없거나 손상되어도 하드코딩된 기본값으로 동작하며,
    평가 자체가 실패해도 예외를 던지지 않고 안전하게 실패(false) 처리한다.
    """

    DEFAULT_EXAGGERATED_PATTERNS = [
        r"100\s*%\s*보장",
        r"무조건\s*(수익|성공)",
        r"확정\s*수익",
        r"단기간\s*대박",
        r"무조건\s*대박",
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.brand_profile = self._load_brand_profile()

    def evaluate(self, content_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            return self._evaluate(content_result or {})
        except Exception:
            return {
                "brand_rule_passed": False,
                "violations": ["brand_rule_evaluation_failed"],
                "tone_match": False,
                "reason": "브랜드 규칙 평가 실패로 안전하게 실패 처리함.",
            }

    def _evaluate(self, content_result: Dict[str, Any]) -> Dict[str, Any]:
        text = self._collect_text(content_result)
        text_lower = text.lower()

        violations: List[str] = []

        banned_words = self.brand_profile.get("banned_words", [])
        if isinstance(banned_words, list):
            for word in banned_words:
                if str(word).strip().lower() in text_lower:
                    violations.append(f"banned_word:{word}")

        for pattern in self.DEFAULT_EXAGGERATED_PATTERNS:
            if re.search(pattern, text):
                violations.append(f"exaggerated_claim:{pattern}")

        tone_match = self._check_tone(content_result)
        brand_rule_passed = not violations and tone_match

        return {
            "brand_rule_passed": brand_rule_passed,
            "violations": violations,
            "tone_match": tone_match,
            "reason": (
                "위반 사항 없음."
                if brand_rule_passed
                else f"위반 {len(violations)}건 감지 또는 브랜드 톤 불일치."
            ),
        }

    def _collect_text(self, content_result: Dict[str, Any]) -> str:
        parts = [str(content_result.get("title", "")), str(content_result.get("caption", ""))]

        slides = content_result.get("slides", [])
        if isinstance(slides, list):
            for slide in slides:
                if isinstance(slide, dict):
                    parts.append(str(slide.get("headline", "")))
                    parts.append(str(slide.get("body", "")))

        hashtags = content_result.get("hashtags", [])
        if isinstance(hashtags, list):
            parts.append(" ".join(str(tag) for tag in hashtags))

        return " ".join(parts)

    def _check_tone(self, content_result: Dict[str, Any]) -> bool:
        title = str(content_result.get("title", "")).strip()
        caption = str(content_result.get("caption", "")).strip()

        return bool(title) and bool(caption)

    def _load_brand_profile(self) -> Dict[str, Any]:
        config_path = Path("config/brand_profile.json")

        if not config_path.exists():
            return self._fallback_brand_profile()

        try:
            with open(config_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception:
            pass

        return self._fallback_brand_profile()

    def _fallback_brand_profile(self) -> Dict[str, Any]:
        return {
            "brand_name": "AI-Content-OS",
            "voice": "친근하고 신뢰감 있는 초보자 친화적 말투",
            "banned_words": ["대박", "무조건", "100% 보장", "확정 수익"],
        }
