import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class InstagramBenchmarkParser(object):
    """
    Competitor Engine - INSTAGRAM_BENCHMARK.md 파서 (Sprint 13).

    실시간 Instagram API/크롤링을 사용하지 않는다. 이미 ChatGPT CTO가 분석해
    GitHub에 저장한 `benchmark/INSTAGRAM_BENCHMARK.md`(계정별 관찰 패턴 문서)만
    파싱해 계정별 hook/pattern/layout/cta/image_strategy/priority 신호를
    구조화한다 (원문 재해석 없음, 문서에 이미 있는 구조만 추출).

    파일이 없거나 파싱에 실패해도 예외를 던지지 않고 빈 목록을 반환한다.
    """

    DEFAULT_PATH = Path("benchmark/INSTAGRAM_BENCHMARK.md")
    STOP_MARKER = "## Key Learnings"

    LABEL_PATTERN = re.compile(r"^(Category|Priority)\s*:\s*(.+)$")
    LIST_LABEL_PATTERN = re.compile(r"^(Observed Pattern|Common Hooks|Common Patterns|AI-Content-OS\s*적용)\s*:\s*$")
    BULLET_PATTERN = re.compile(r"^-\s+(.+)$")

    LAYOUT_KEYWORDS = {
        "notebook": ["손글씨", "노트"],
        "dark_editorial": ["어두운 톤", "다크", "권위형", "고급스러운"],
        "character_diary": ["캐릭터", "다이어리", "인물 기반", "마스코트"],
        "comparison": ["비교"],
        "tutorial": ["단계", "가이드", "튜토리얼"],
        "checklist": ["체크리스트"],
        "bold_ai": ["ai 영상", "썸네일 텍스트", "강조 텍스트", "흰색 제목"],
    }

    CTA_KEYWORDS = {
        "save": ["저장"],
        "comment": ["댓글"],
        "dm": ["dm"],
        "profile": ["프로필"],
        "follow": ["팔로우", "follow"],
        "share": ["공유", "태그"],
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None, path: Optional[Path] = None):
        self.config = config or {}
        self.path = path or self.DEFAULT_PATH

    def parse(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"status": "instagram_benchmark_unavailable", "accounts": [], "fallback_used": True}

        try:
            text = self.path.read_text(encoding="utf-8", errors="ignore")
            accounts = self._parse_accounts(text)

            return {
                "status": "instagram_benchmark_parsed",
                "accounts": accounts,
                "fallback_used": False,
            }
        except Exception as error:
            print(f"Instagram Benchmark Parse Failed: {error}")
            return {
                "status": "instagram_benchmark_error",
                "accounts": [],
                "fallback_used": True,
                "reason": str(error),
            }

    def _parse_accounts(self, text: str) -> List[Dict[str, Any]]:
        body_text = text.split(self.STOP_MARKER)[0]
        chunks = body_text.split("\n### ")[1:]

        accounts = []

        for chunk in chunks:
            lines = chunk.splitlines()

            if not lines:
                continue

            handle = lines[0].strip()

            if not handle:
                continue

            account = self._parse_account_body(handle, lines[1:])
            accounts.append(account)

        return accounts

    def _parse_account_body(self, handle: str, lines: List[str]) -> Dict[str, Any]:
        category = ""
        priority = ""
        current_list_label = None
        collected: Dict[str, List[str]] = {}

        for raw_line in lines:
            line = raw_line.strip()

            if not line:
                current_list_label = None
                continue

            label_match = self.LABEL_PATTERN.match(line)
            if label_match:
                key, value = label_match.group(1), label_match.group(2).strip()

                if key == "Category":
                    category = value
                elif key == "Priority":
                    priority = value

                current_list_label = None
                continue

            list_label_match = self.LIST_LABEL_PATTERN.match(line)
            if list_label_match:
                current_list_label = list_label_match.group(1)
                collected.setdefault(current_list_label, [])
                continue

            bullet_match = self.BULLET_PATTERN.match(line)
            if bullet_match and current_list_label:
                collected[current_list_label].append(bullet_match.group(1).strip())

        observed_pattern = collected.get("Observed Pattern", [])
        hook_signals = collected.get("Common Hooks", []) or collected.get("Common Patterns", [])
        applications = collected.get("AI-Content-OS 적용", [])

        combined_text = " ".join([category] + observed_pattern + applications).lower()

        return {
            "account": handle,
            "category": category,
            "observed_pattern": observed_pattern,
            "hook_signals": hook_signals,
            "pattern_signal": observed_pattern[0] if observed_pattern else category,
            "layout_signal": self._match_keyword(combined_text, self.LAYOUT_KEYWORDS),
            "cta_signals": self._match_all_keywords(combined_text, self.CTA_KEYWORDS),
            "image_strategy_signal": self._infer_image_strategy(combined_text),
            "ai_content_os_applications": applications,
            "priority": priority,
        }

    def _match_keyword(self, text: str, mapping: Dict[str, List[str]]) -> str:
        for key, keywords in mapping.items():
            for keyword in keywords:
                if keyword in text:
                    return key

        return ""

    def _match_all_keywords(self, text: str, mapping: Dict[str, List[str]]) -> List[str]:
        matched = []

        for key, keywords in mapping.items():
            for keyword in keywords:
                if keyword in text:
                    matched.append(key)
                    break

        return matched

    def _infer_image_strategy(self, text: str) -> str:
        if any(keyword in text for keyword in ("실사", "영상", "썸네일")):
            return "ai_image"

        if any(keyword in text for keyword in ("캐릭터", "일러스트")):
            return "character_image"

        if any(keyword in text for keyword in ("손글씨", "노트")):
            return "handwriting_style"

        if any(keyword in text for keyword in ("템플릿", "캐러셀")):
            return "template_image"

        return "text_overlay"
