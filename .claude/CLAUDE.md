# graphify
- **graphify** (`.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

# Fail-fast and usage guard

- If any `PreToolUse` hook returns an error, do not retry the same tool call. Stop the turn and report the hook name and exact error once.
- Never repeat `Read`, `Glob`, or repository search merely because a hook failed. A hook failure is an environment/configuration fault, not a request to try more files.
- Keep bounded review work on the explicitly named files only. Do not widen the read set unless the work order explicitly requires it.
- Use Fable effort `medium` by default. Use `high` only when the work order explicitly requires high effort.
