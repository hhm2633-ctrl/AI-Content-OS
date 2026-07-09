---
name: ai-content-os-doc-update
description: AI-Content-OS의 PROJECT_SNAPSHOT, CHANGELOG, MODULE_STATUS, ROADMAP, DECISIONS 문서를 변경사항에 맞게 일관되게 업데이트하는 절차.
---

# AI-Content-OS Documentation Update Skill

## Purpose

Use this skill after meaningful repository changes.

## Required Docs

Usually update:

- `PROJECT_SNAPSHOT.md`
- `CHANGELOG.md`
- `MODULE_STATUS.md`

When architecture, roadmap, or decision changes occur, also update:

- `PROJECT_MASTER.md`
- `ROADMAP.md`
- `DECISIONS.md`
- `CURRENT_TASK.md` if current work changes

## Project Snapshot

`PROJECT_SNAPSHOT.md` should include:

- updated timestamp
- execution command:

```powershell
py -m src.main
```

- final workflow status
- current WorkflowEngine sequence
- important new modules/docs
- protected rules

Do not include secrets.

## Changelog

`CHANGELOG.md` should include:

- date/time
- change summary
- execution command
- compile result if available
- workflow result if available

## Module Status

`MODULE_STATUS.md` should classify items as:

- Completed
- Operational Complete
- Planning
- Roadmap
- Notes

For planning-only documents, do not mark engines as implemented.

## Decisions

`DECISIONS.md` should record durable decisions, such as:

- External research is analyzed by ChatGPT CTO first.
- Claude/Codex should use repository research documents, not re-analyze raw external materials.
- WorkflowEngine must remain stable.
- Fallback-first behavior is mandatory.

## Roadmap

Roadmap should separate:

- near-term CardNews MVP items
- later Shorts/Video/Animation items
- analytics/dashboard items
- research/knowledge items

## Do Not

- Do not overstate implementation status.
- Do not mark planning docs as working modules.
- Do not remove old decisions.
- Do not rewrite the whole project history unless instructed.
