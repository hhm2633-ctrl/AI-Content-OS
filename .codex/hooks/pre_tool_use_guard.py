#!/usr/bin/env python3
"""AI-Content-OS project-local Codex guardrail.

The hook is intentionally small and deterministic.  It denies high-risk shell
commands and direct patches to protected/actively-owned files.  It does not
replace repository review, tests, or platform confirmation prompts.
"""

from __future__ import annotations

import fnmatch
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


HOOK_DIR = Path(__file__).resolve().parent
LOCKS_PATH = HOOK_DIR / "active_locks.json"

PROTECTED_EXACT = {
    "CURRENT_TASK.md",
    "ROADMAP.md",
    "MODULE_STATUS.md",
    "DECISIONS.md",
    "CHANGELOG.md",
    "PROJECT_SNAPSHOT.md",
    "docs/ACTIVE_PARALLEL_WORK_ORDERS.md",
    "config/source_data_storage.json",
}

GIT_WRITE_RE = re.compile(
    r"(?i)(?:^|[;&|])\s*(?:[^\s;&|]*[\\/])?git(?:\.exe)?\s+"
    r"(?:-[^\s]+\s+)*(?:push|pull|merge|rebase|reset|checkout|"
    r"switch|restore|clean|rm|mv|tag)(?:\s|$)"
)
BAD_MAIN_RE = re.compile(r"(?i)(?:^|\s)python(?:\.exe)?\s+-m\s+src\.main(?:\s|$)")
DESTRUCTIVE_RE = re.compile(
    r"(?i)(?:remove-item\b[^\r\n]*\s-(?:recurse|r)\b|\brm\s+-[^\s]*r[^\s]*f|"
    r"\bgit\s+reset\s+--hard|\bgit\s+clean\s+-[^\s]*f)"
)
DEPLOY_RE = re.compile(
    r"(?i)(?:\b(?:vercel|netlify)\b[^\r\n]*\bprod\b|\bfirebase\s+deploy\b|"
    r"\bnpm\s+run\s+deploy\b|\bgh\s+pr\s+(?:create|merge)\b)"
)
EXTERNAL_WRITE_RE = re.compile(
    r"(?i)(?:\bcurl\b[^\r\n]*(?:-X|--request)\s*(?:POST|PUT|PATCH|DELETE)"
    r"[^\r\n]*(?:graph\.facebook\.com|instagram\.com)|"
    r"\binvoke-restmethod\b[^\r\n]*-method\s+(?:POST|PUT|PATCH|DELETE)"
    r"[^\r\n]*(?:graph\.facebook\.com|instagram\.com))"
)
AUTOMATION_WRITE_RE = re.compile(
    r"(?i)(?:automation[_-]?(?:resume|enable|start)|resume[_-]?automation|"
    r"schtasks(?:\.exe)?\s+/(?:run|create|change)|start-scheduledtask)"
)
AFFILIATE_ISSUE_RE = re.compile(
    r"(?i)(?:affiliate[^\r\n]*(?:issue|create|generate)[_-]?link|"
    r"brandconnect[^\r\n]*(?:링크\s*발급|issue[_-]?link|generate[_-]?link))"
)
BAD_CLAUDE_LAUNCH_RE = re.compile(
    r"(?i)(?:^|[;&|])\s*"
    r"(?:\"[^\"\r\n]*[\\/]claude(?:\.cmd|\.exe)?\"|"
    r"[^\s;&|]*[\\/]claude(?:\.cmd|\.exe)?|claude(?:\.cmd|\.exe)?)"
    r"(?=$|\s)(?!\s+(?:--help|--version)\b)(?!\s+agents\s+--json\b)"
)
CLAUDE_RESUME_RE = re.compile(r"(?i)(?<![\w-])(?:--resume|--continue|-r|-c)(?![\w-])")
CLAUDE_BACKGROUND_RE = re.compile(r"(?i)(?<![\w-])--(?:bg|background)(?![\w-])")
CLAUDE_QUOTED_RE = re.compile(r"\"[^\"]*\"|'[^']*'")
CLAUDE_INACTIVE_STATUSES = {
    "completed", "failed", "stopped", "cancelled", "canceled",
    "exited", "done", "error", "terminated",
}
GENERIC_SPARK_THREAD_RE = re.compile(
    r"(?i)(?:create_thread[^\r\n]*spark|spark[^\r\n]*create_thread)"
)


def _normalize_path(value: str) -> str:
    return value.strip().strip('"').replace("\\", "/").lstrip("./")


def _load_lock_patterns() -> list[tuple[str, str]]:
    if not LOCKS_PATH.is_file():
        return []
    try:
        payload = json.loads(LOCKS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    patterns: list[tuple[str, str]] = []
    for entry in payload.get("active", []):
        if not isinstance(entry, dict):
            continue
        owner = str(entry.get("owner", "another writer"))
        for pattern in entry.get("paths", []):
            if isinstance(pattern, str) and pattern.strip():
                patterns.append((_normalize_path(pattern), owner))
    return patterns


def _patch_paths(command: str) -> list[str]:
    paths = []
    for match in re.finditer(
        r"(?m)^\*\*\* (?:Add|Update|Delete) File:\s*(.+?)\s*$|^\*\*\* Move to:\s*(.+?)\s*$",
        command,
    ):
        raw = match.group(1) or match.group(2)
        paths.append(_normalize_path(raw))
    return paths


def _deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _count_active_agents(agents: list[Any]) -> int:
    count = 0
    for entry in agents:
        if isinstance(entry, dict):
            status = str(entry.get("status", "")).strip().lower()
            state = str(entry.get("state", "")).strip().lower()
            if status in CLAUDE_INACTIVE_STATUSES or state in CLAUDE_INACTIVE_STATUSES:
                continue
        count += 1
    return count


def _claude_session_count() -> int | None:
    """Return the current active background-agent count, or None on probe failure."""

    executable = shutil.which("claude")
    if executable is None:
        return None
    try:
        result = subprocess.run(
            [executable, "agents", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            check=False,
        )
        payload = json.loads(result.stdout or "[]")
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    if isinstance(payload, list):
        return _count_active_agents(payload)
    if isinstance(payload, dict) and isinstance(payload.get("agents"), list):
        return _count_active_agents(payload["agents"])
    return None


def evaluate(payload: dict[str, Any], *, claude_session_count: int | None = None) -> dict[str, Any] | None:
    tool_name = str(payload.get("tool_name", ""))
    tool_input = payload.get("tool_input", {})
    if isinstance(tool_input, dict):
        command = tool_input.get(
            "cmd",
            tool_input.get("command", tool_input.get("patch", "")),
        )
    else:
        command = tool_input
    command = command if isinstance(command, str) else json.dumps(command, ensure_ascii=False)

    if tool_name.lower() in {"bash", "unified_exec", "exec_command"}:
        if BAD_MAIN_RE.search(command):
            return _deny("AI-Content-OS는 `python -m src.main`을 금지합니다. `py -m src.main`을 사용하세요.")
        if GIT_WRITE_RE.search(command):
            return _deny("Git 히스토리/원격/파일 상태를 바꾸는 명령(push/pull/merge/rebase/reset/checkout/switch/restore/clean/rm/mv/tag)은 CTO 최종 승인 전 금지됩니다. `git add`와 `git commit`은 자유롭게 사용 가능합니다.")
        if DESTRUCTIVE_RE.search(command):
            return _deny("재귀 삭제 또는 파괴적 복구 명령은 이 프로젝트 Hook이 차단합니다.")
        if DEPLOY_RE.search(command):
            return _deny("사이트 배포·PR 생성/병합은 별도 사용자 승인 전 금지됩니다.")
        if EXTERNAL_WRITE_RE.search(command):
            return _deny("Instagram/Meta 외부 쓰기 요청은 실제 게시/API 승인 전 금지됩니다.")
        if AUTOMATION_WRITE_RE.search(command):
            return _deny("자동화 시작·재개·등록은 사용자의 명시적 승인 전 금지됩니다.")
        if AFFILIATE_ISSUE_RE.search(command):
            return _deny("제휴 링크 발급은 사용자의 명시적 승인 전 금지됩니다.")
        launch = BAD_CLAUDE_LAUNCH_RE.search(command)
        if launch:
            # 플래그는 claude 호출 지점 이후, 따옴표 인자 밖에서만 인정한다.
            tail = CLAUDE_QUOTED_RE.sub(" ", command[launch.start():])
            is_resume = CLAUDE_RESUME_RE.search(tail) is not None
            is_background = CLAUDE_BACKGROUND_RE.search(tail) is not None
            if not (is_resume or is_background):
                return _deny(
                    "Claude 실행은 `--bg` 신규 background 세션 시작 또는 "
                    "`--resume/--continue` 기존 세션 재사용만 허용됩니다."
                )
            count = claude_session_count if claude_session_count is not None else _claude_session_count()
            if count is not None and count < 0:
                count = None
            if count is None:
                return _deny("`claude agents --json` 세션 확인에 실패해 Claude 실행을 차단했습니다.")
            if count > 1:
                return _deny(f"Claude 활성 세션이 {count}개라 실행을 차단했습니다. 한 세션만 남겨야 합니다.")
            if count == 1 and not is_resume:
                return _deny("Claude 활성 세션이 1개입니다. 새로 만들지 말고 `--resume`으로 기존 세션을 재사용하세요.")
            if count == 0 and not is_background:
                return _deny("활성 세션이 없습니다. 추적 가능한 단일 background 세션(`--bg`)으로 시작하세요.")
        if GENERIC_SPARK_THREAD_RE.search(command) and 'model_reasoning_summary="none"' not in command:
            return _deny("Spark는 generic create_thread가 아니라 model_reasoning_summary=\"none\" 전용 경로만 사용합니다.")

    if tool_name.lower() in {"apply_patch", "edit", "write"}:
        paths = _patch_paths(command)
        if "*** Delete File:" in command:
            return _deny("파일 삭제는 Hook에서 기본 차단됩니다. CTO가 범위와 복구 계획을 먼저 승인해야 합니다.")
        locks = _load_lock_patterns()
        for path in paths:
            if path in PROTECTED_EXACT:
                return _deny(f"공용 상태문서 `{path}`는 CTO/integration lane 단독 소유입니다.")
            if path == "storage" or path.startswith("storage/"):
                return _deny(f"런타임 산출물 `{path}`의 직접 패치는 금지됩니다. 정식 실행 경로를 사용하세요.")
            for pattern, owner in locks:
                if fnmatch.fnmatch(path, pattern):
                    return _deny(f"`{path}`는 현재 `{owner}`가 소유 중입니다. 병렬 writer 충돌을 피하세요.")
            if not path.startswith("tests/") and re.search(
                r"(?i)[\"']?actual_publish[\"']?\s*[:=]\s*(?:true|True)", command
            ):
                return _deny("테스트 외 파일에서 actual_publish=true 설정은 별도 게시 승인 전 금지됩니다.")
    return None


def _self_test() -> int:
    # (payload, should_deny, claude_session_count) — 음수 count는 프로브 실패를 뜻한다.
    cases = [
        ({"tool_name": "Bash", "tool_input": {"command": "python -m src.main"}}, True, 0),
        ({"tool_name": "Bash", "tool_input": {"command": "py -m src.main"}}, False, 0),
        ({"tool_name": "Bash", "tool_input": {"command": "git status --short"}}, False, 0),
        ({"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}, False, 0),
        ({"tool_name": "Bash", "tool_input": {"command": "git add -A"}}, False, 0),
        ({"tool_name": "Bash", "tool_input": {"command": "git push origin main"}}, True, 0),
        ({"tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}}, True, 0),
        ({"tool_name": "Bash", "tool_input": {"command": "git reset --hard HEAD~1"}}, True, 0),
        ({"tool_name": "Bash", "tool_input": {"command": "git clean -fd"}}, True, 0),
        ({"tool_name": "Bash", "tool_input": {"command": "git rebase -i HEAD~5"}}, True, 0),
        ({"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch\n*** Update File: ROADMAP.md\n@@\n-x\n+y\n*** End Patch"}}, True, 0),
        ({"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch\n*** Delete File: config/source_data_storage.json\n*** End Patch"}}, True, 0),
        ({"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch\n*** Update File: config/source_data_storage.json\n@@\n-x\n+y\n*** End Patch"}}, True, 0),
        ({"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch\n*** Update File: tests/test_guard.py\n@@\n-x\n+actual_publish = True\n*** End Patch"}}, False, 0),
        ({"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch\n*** Update File: modules/publishing/example.py\n@@\n-x\n+actual_publish = True\n*** End Patch"}}, True, 0),
    ]
    cases.extend(
        [
            ({"tool_name": "exec_command", "tool_input": {"cmd": "git commit -m x"}}, False, 0),
            ({"tool_name": "exec_command", "tool_input": {"cmd": "git push origin main"}}, True, 0),
            ({"tool_name": "exec_command", "tool_input": {"cmd": "python -m src.main"}}, True, 0),
            ({"tool_name": "exec_command", "tool_input": {"cmd": "  claude --bg task"}}, True, 1),
            ({"tool_name": "exec_command", "tool_input": {"cmd": "C:/Tools/claude.exe --bg task"}}, True, 1),
            ({"tool_name": "exec_command", "tool_input": {"cmd": "\"C:/Tools/claude.exe\" --bg task"}}, True, 1),
            ({"tool_name": "Bash", "tool_input": {"command": "claude agents --json"}}, False, 0),
            ({"tool_name": "Bash", "tool_input": {"command": "claude --version"}}, False, 0),
            ({"tool_name": "Bash", "tool_input": {"command": "claude -p task"}}, True, 0),
            ({"tool_name": "Bash", "tool_input": {"command": "claude"}}, True, 0),
            ({"tool_name": "Bash", "tool_input": {"command": "claude --bg task"}}, False, 0),
            ({"tool_name": "Bash", "tool_input": {"command": "claude --bg task"}}, True, 1),
            ({"tool_name": "Bash", "tool_input": {"command": "claude --resume abc123 -p task"}}, False, 1),
            ({"tool_name": "Bash", "tool_input": {"command": "claude --resume abc123 -p task"}}, True, 2),
            ({"tool_name": "Bash", "tool_input": {"command": "claude --bg task"}}, True, 2),
            ({"tool_name": "Bash", "tool_input": {"command": "claude --bg task"}}, True, -1),
            ({"tool_name": "Bash", "tool_input": {"command": "claude --resume abc123"}}, True, 0),
            ({"tool_name": "Bash", "tool_input": {"command": "claude -p \"task --bg\""}}, True, 0),
            ({"tool_name": "Bash", "tool_input": {"command": "echo --bg; claude -p task"}}, True, 0),
            ({"tool_name": "Bash", "tool_input": {"command": "Start-ScheduledTask -TaskName cardnews"}}, True, 0),
            ({"tool_name": "Bash", "tool_input": {"command": "brandconnect generate_link"}}, True, 0),
        ]
    )
    failures = []
    for index, (payload, should_deny, count) in enumerate(cases, start=1):
        denied = evaluate(payload, claude_session_count=count) is not None
        if denied != should_deny:
            failures.append(index)
    if _count_active_agents([{"status": "idle", "state": "done"}]) != 0:
        failures.append("done_agent_count")
    if _count_active_agents([{"status": "busy", "state": "working"}]) != 1:
        failures.append("active_agent_count")
    print(json.dumps({"cases": len(cases), "failures": failures, "passed": not failures}))
    return 1 if failures else 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    if "--self-test" in sys.argv:
        return _self_test()
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    decision = evaluate(payload)
    if decision is not None:
        print(json.dumps(decision, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
