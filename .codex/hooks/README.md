# AI-Content-OS project hooks

These hooks are project-local guardrails for Codex sessions.

- `session_context.py` injects the minimum execution and approval contract.
- `pre_tool_use_guard.py` blocks known unsafe shell/edit actions.
- `active_locks.json` prevents Codex from editing files currently owned by an external writer.

Hooks are not a complete security boundary. Codex's unified/streaming execution
path is not fully intercepted by current `PreToolUse` support, and Claude Code
does not load Codex hooks. Repository review and one-writer work orders remain
mandatory.

After creating or changing a hook, open `/hooks` in Codex and trust the exact
project hook definitions before expecting them to run.
