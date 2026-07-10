import json
from pathlib import Path
from typing import Any, Dict, Optional


class BrandProfileLoader(object):
    """
    Brand DNA Engine - config/brand_profile.json 로더.

    파일이 없거나 손상되어도 예외를 던지지 않고 안전한 기본 프로필로 대체한다
    (PublishingModule._load_publishing_config()과 동일한 규칙).
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("config/brand_profile.json")

    def load(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return self._fallback_profile()

        try:
            with open(self.config_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict) and data:
                return data
        except Exception:
            pass

        return self._fallback_profile()

    def _fallback_profile(self) -> Dict[str, Any]:
        return {
            "brand_name": "AI-Content-OS",
            "voice": "친근하고 신뢰감 있는 초보자 친화적 말투",
            "tone_keywords": ["쉬운 설명", "실전형", "신뢰감"],
            "banned_words": ["대박", "무조건", "100% 보장", "확정 수익"],
            "target_audience": "AI 자동화와 부업, 콘텐츠 자동화에 관심 있는 초보자",
            "cta_style": "저장/팔로우를 자연스럽게 유도하되 과도한 강매 느낌은 피함",
        }
