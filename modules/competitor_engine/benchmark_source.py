import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class BenchmarkSource(object):
    """
    Competitor Engine - Benchmark 소스.

    `benchmark/*.md`는 이미 ChatGPT CTO가 분석해 GitHub에 저장한 결론 문서다
    (research.md 규칙: Claude는 원자료를 재분석하지 않지만, 이미 분석된 GitHub
    문서는 프로젝트 컨텍스트로 사용한다). 이 소스는 `### N. 제목` 형식 섹션과
    `- ` 불릿 목록을 가벼운 구조로만 파싱한다 (원문 재해석/재작성 없음).

    `INSTAGRAM_BENCHMARK.md`(계정별 `### 계정명` 형식)와
    `TOOLS_AND_FUNNEL_REFERENCES.md`(`## N. 제목` 형식)는 헤더 구조가 달라
    Sprint 13부터 각각 `InstagramBenchmarkParser`/`ToolsFunnelParser` 전용
    파서가 담당하며 여기서는 다루지 않는다 (헤더 불일치로 0건 파싱되던 문제 수정).

    파일이 없거나 파싱에 실패해도 예외를 던지지 않고 빈 목록을 반환한다.
    """

    DEFAULT_FILES = [
        "benchmark/HOOK_LIBRARY.md",
        "benchmark/CTA_LIBRARY.md",
        "benchmark/CONTENT_PATTERNS.md",
        "benchmark/AI_CONTENT_STRATEGY.md",
    ]

    SECTION_HEADER_PATTERN = re.compile(r"^###\s+\d+\.\s*(.+)$")
    BULLET_PATTERN = re.compile(r"^-\s+(.+)$")
    MAX_EXAMPLES_PER_SECTION = 5

    def __init__(self, config: Optional[Dict[str, Any]] = None, files: Optional[List[str]] = None):
        self.config = config or {}
        self.files = files or self.DEFAULT_FILES

    def collect(self) -> Dict[str, Any]:
        sections: List[Dict[str, Any]] = []
        files_read = 0
        files_missing = []

        for relative_path in self.files:
            path = Path(relative_path)

            if not path.exists():
                files_missing.append(relative_path)
                continue

            try:
                sections.extend(self._parse_file(path))
                files_read += 1
            except Exception as error:
                print(f"Benchmark Source Parse Failed ({relative_path}): {error}")

        return {
            "status": "benchmark_collected" if files_read else "benchmark_unavailable",
            "sections": sections,
            "files_read": files_read,
            "files_missing": files_missing,
            "fallback_used": files_read == 0,
        }

    def _parse_file(self, path: Path) -> List[Dict[str, Any]]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()

        sections: List[Dict[str, Any]] = []
        current_title = ""
        current_examples: List[str] = []

        def flush():
            if current_title:
                sections.append({
                    "file": path.name,
                    "title": current_title,
                    "examples": current_examples[: self.MAX_EXAMPLES_PER_SECTION],
                })

        for line in lines:
            header_match = self.SECTION_HEADER_PATTERN.match(line.strip())

            if header_match:
                flush()
                current_title = header_match.group(1).strip()
                current_examples = []
                continue

            bullet_match = self.BULLET_PATTERN.match(line.strip())

            if bullet_match and current_title and len(current_examples) < self.MAX_EXAMPLES_PER_SECTION:
                current_examples.append(bullet_match.group(1).strip())

        flush()

        return sections
