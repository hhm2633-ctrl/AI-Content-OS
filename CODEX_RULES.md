# AI-Content-OS Codex Rules

## Purpose

This document defines how Codex should work inside the AI-Content-OS repository.

The primary goal is to minimize token usage while maximizing development speed and maintaining workflow stability.

---

# General Rules

- Never create a new project.
- Never change the overall architecture.
- Keep WorkflowEngine intact.
- Keep all existing module names.
- Keep folder structure.
- Keep class names.
- Extend the current system only.

---

# Workflow Rules

workflow_completed must never break.

Internet failures must become fallback events.

LLM failures must become fallback events.

Image failures must become fallback events.

The workflow must always finish safely.

---

# Execution Rules

Always use

py -m src.main

Never use

python -m src.main

Compile command

py -m compileall src modules scripts

---

# Development Rules

Develop in Sprint units.

Implement 5~10 related features together.

Avoid tiny commits.

Avoid unnecessary refactoring.

Prefer extending existing modules.

---

# Testing Rules

Default

Module tests only.

Do NOT run the full workflow after every feature.

Run the complete workflow only

- Sprint completion
- Major architecture change
- Explicit request from ChatGPT

---

# Browser Rules

Do NOT perform browser validation unless explicitly requested.

Browser Plugin is used only when

- Collector development
- DOM verification
- Source verification

Never use Browser Plugin during ordinary Python development.

---

# API Rules

Do not test

- Image APIs
- LLM APIs
- Publishing APIs

unless required by the Sprint.

Fallback validation is sufficient.

---

# Documentation Rules

Update only when changes are meaningful.

Possible files

- PROJECT_MASTER.md
- PROJECT_SNAPSHOT.md
- CHANGELOG.md
- MODULE_STATUS.md
- Sprint documents

Avoid unnecessary documentation updates.

---

# Performance Rules

Minimize token usage.

Prefer one large Sprint over many small requests.

Avoid repeating repository analysis.

Reuse existing architecture whenever possible.

---

# Development Philosophy

Build reusable engines.

Every engine should be reusable by

- Card News
- Shorts
- Blog
- Instagram
- Threads
- Smart Store
- Future platforms

---

# Priority

1. Stability
2. Reusability
3. Token efficiency
4. Development speed
5. Code quality

Never sacrifice workflow stability.