import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class ToolsFunnelParser(object):
    """
    Competitor Engine - TOOLS_AND_FUNNEL_REFERENCES.md 파서 (Sprint 13).

    이미 분석되어 GitHub에 저장된 문서를 `## N. Title` 섹션 단위로 파싱해
    Tool/Funnel 참고 데이터(Core Value/AI-Content-OS 적용/Implementation
    Priority)를 구조화한다. 실시간 크롤링/API 호출은 하지 않는다.

    파일이 없거나 파싱에 실패해도 예외를 던지지 않고 빈 목록을 반환한다.
    """

    DEFAULT_PATH = Path("benchmark/TOOLS_AND_FUNNEL_REFERENCES.md")
    FUNNEL_SECTION_MARKER = "## Funnel Model Observed"

    SECTION_HEADER_PATTERN = re.compile(r"^##\s+\d+\.\s*(.+)$")
    SOURCE_PATTERN = re.compile(r"^Source\s*:\s*(.+)$")
    LIST_LABEL_PATTERN = re.compile(r"^(Core Value|AI-Content-OS\s*적용|Observed Tools/Topics)\s*:\s*$")
    BULLET_PATTERN = re.compile(r"^-\s+(.+)$")
    PRIORITY_PATTERN = re.compile(r"^Implementation Priority\s*:\s*(.+)$")

    def __init__(self, config: Optional[Dict[str, Any]] = None, path: Optional[Path] = None):
        self.config = config or {}
        self.path = path or self.DEFAULT_PATH

    def parse(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"status": "tools_funnel_unavailable", "references": [], "fallback_used": True}

        try:
            text = self.path.read_text(encoding="utf-8", errors="ignore")
            references = self._parse_sections(text)

            return {
                "status": "tools_funnel_parsed",
                "references": references,
                "fallback_used": False,
            }
        except Exception as error:
            print(f"Tools Funnel Parse Failed: {error}")
            return {
                "status": "tools_funnel_error",
                "references": [],
                "fallback_used": True,
                "reason": str(error),
            }

    def _parse_sections(self, text: str) -> List[Dict[str, Any]]:
        body_text = text.split(self.FUNNEL_SECTION_MARKER)[0]
        lines = body_text.splitlines()

        sections: List[Dict[str, Any]] = []
        current_title = ""
        current_lines: List[str] = []

        def flush() -> None:
            if current_title:
                sections.append(self._parse_section_body(current_title, current_lines))

        for line in lines:
            header_match = self.SECTION_HEADER_PATTERN.match(line.strip())

            if header_match:
                flush()
                current_title = header_match.group(1).strip()
                current_lines = []
                continue

            current_lines.append(line)

        flush()

        return sections

    def _parse_section_body(self, title: str, lines: List[str]) -> Dict[str, Any]:
        source = ""
        priority = ""
        current_list_label = None
        collected: Dict[str, List[str]] = {}

        for raw_line in lines:
            line = raw_line.strip()

            if not line:
                current_list_label = None
                continue

            source_match = self.SOURCE_PATTERN.match(line)
            if source_match:
                source = source_match.group(1).strip()
                current_list_label = None
                continue

            priority_match = self.PRIORITY_PATTERN.match(line)
            if priority_match:
                priority = priority_match.group(1).strip()
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

        return {
            "title": title,
            "source": source,
            "core_value": collected.get("Core Value", []) or collected.get("Observed Tools/Topics", []),
            "ai_content_os_applications": collected.get("AI-Content-OS 적용", []),
            "priority": priority,
        }
