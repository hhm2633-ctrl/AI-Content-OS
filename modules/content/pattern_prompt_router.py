from pathlib import Path
from typing import Any, Dict, Optional


class PatternPromptRouter:
    """
    pattern_type에 따라 Content Prompt에 주입할 패턴별 가이드 텍스트를 선택한다.

    prompts/patterns/<pattern_type>_prompt.md 파일이 있으면 그 내용을 사용하고,
    파일이 없거나 읽기 실패하면 내장된 기본 가이드 텍스트로 대체한다.
    알 수 없는 pattern_type이 들어와도 예외를 던지지 않고 'resource' 기본
    가이드로 안전하게 대체한다.
    """

    PATTERN_TYPES = [
        "warning",
        "tutorial",
        "comparison",
        "story",
        "number_list",
        "resource",
    ]

    DEFAULT_GUIDES = {
        "warning": (
            "경고형 패턴: 흔한 실수와 위험을 먼저 보여주고, 왜 위험한지 이유를 설명한 뒤 "
            "해결 방법을 제시한다. 톤은 다급하지만 신뢰감 있게 유지한다."
        ),
        "tutorial": (
            "튜토리얼 패턴: 초보자가 바로 따라 할 수 있도록 준비물과 핵심 실행 단계를 "
            "순서대로 설명한다. 어려운 용어 없이 쉬운 말투를 사용한다."
        ),
        "comparison": (
            "비교형 패턴: 비교 기준을 먼저 제시하고 두 옵션의 장단점을 대비시킨 뒤 "
            "상황별 추천으로 마무리한다. 편향 없이 균형 있게 서술한다."
        ),
        "story": (
            "스토리형 패턴: 개인적인 경험과 고민을 먼저 보여주고, 전환점과 그로부터 얻은 "
            "교훈을 진솔하게 전달한다. 공감을 얻는 말투를 사용한다."
        ),
        "number_list": (
            "숫자 리스트 패턴: 숫자로 기대감을 준 뒤 왜 중요한지 짧게 설명하고, 핵심 항목을 "
            "간결하게 나열한다. 저장하고 싶게 정보 밀도를 높인다."
        ),
        "resource": (
            "리소스 큐레이션 패턴: 저장을 유도하는 후킹 뒤 선정 기준을 설명하고, 실제 "
            "추천 리소스를 나열한다. 실용적이고 신뢰할 수 있는 톤을 사용한다."
        ),
    }

    def __init__(self, config=None, prompts_dir: Optional[Path] = None):
        self.config = config or {}
        self.prompts_dir = prompts_dir or Path("prompts/patterns")

    def get_guide(self, pattern_type: str) -> Dict[str, Any]:
        pattern_type = str(pattern_type or "").strip()

        if pattern_type not in self.PATTERN_TYPES:
            fallback_type = "resource"

            return {
                "pattern_type": fallback_type,
                "guide": self.DEFAULT_GUIDES[fallback_type],
                "source": "default_fallback",
                "reason": (
                    f"알 수 없는 pattern_type '{pattern_type}'이라 "
                    f"'{fallback_type}' 기본 가이드로 대체함."
                ),
            }

        file_guide = self._load_prompt_file(pattern_type)

        if file_guide:
            return {
                "pattern_type": pattern_type,
                "guide": file_guide,
                "source": "prompt_file",
                "reason": f"prompts/patterns/{pattern_type}_prompt.md 파일을 사용함.",
            }

        return {
            "pattern_type": pattern_type,
            "guide": self.DEFAULT_GUIDES[pattern_type],
            "source": "default_guide",
            "reason": f"prompt 파일이 없어 '{pattern_type}' 기본 가이드를 사용함.",
        }

    def _load_prompt_file(self, pattern_type: str) -> str:
        file_path = self.prompts_dir / f"{pattern_type}_prompt.md"

        if not file_path.exists():
            return ""

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read().strip()
        except Exception:
            return ""
