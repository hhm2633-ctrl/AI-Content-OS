---
name: ai-content-os-knowledge-intelligence
description: AI-Content-OS의 근거 기반 학습 패턴을 생성·검증·승격·폐기하고 pattern registry, source claim 연결, 버전·중복·supersedes 규칙을 점검할 때 사용한다.
---

# Ai Content Os Knowledge Intelligence

## Overview

기존 분석에서 근거가 확인된 학습 패턴만 등록하고, 승격·대체·폐기 게이트를 fail-closed로 운영한다.

## Required Workflow

1. 원자료를 수정하지 말고 기존 분석의 `source_claim_ids`만 참조한다.
2. 새 패턴은 `CANDIDATE`로 작성하고 `references/api_reference.md`의 정확한 계약을 적용한다.
3. `py .codex/skills/ai-content-os-knowledge-intelligence/scripts/example.py <jsonl>`로 레지스트리를 검증한다.
4. 독립 근거 확인 후에만 `VERIFIED` 새 버전을 추가한다.
5. 성과 증거와 명시적 사람 승인이 모두 있을 때만 `PatternRegistry.promote()`를 호출한다.
6. 동일/하위 버전, 의미 중복, 없는 supersedes 대상, 순환 연결은 거부한다.
7. 만료·실패·권리 문제는 `DEPRECATED` 또는 `REJECTED`로 닫는다.

`examples/candidate_pattern.json`을 입력 예시로, `golden/valid_candidate_report.json`을 기대 결과로 사용한다.

## Design Reference

[The workflow above is authoritative. Keep these reusable-resource principles:

**1. Workflow-Based** (best for sequential processes)
- Works well when there are clear step-by-step procedures
- Example: DOCX skill with "Workflow Decision Tree" -> "Reading" -> "Creating" -> "Editing"
- Structure: ## Overview -> ## Workflow Decision Tree -> ## Step 1 -> ## Step 2...

**2. Task-Based** (best for tool collections)
- Works well when the skill offers different operations/capabilities
- Example: PDF skill with "Quick Start" -> "Merge PDFs" -> "Split PDFs" -> "Extract Text"
- Structure: ## Overview -> ## Quick Start -> ## Task Category 1 -> ## Task Category 2...

**3. Reference/Guidelines** (best for standards or specifications)
- Works well for brand guidelines, coding standards, or requirements
- Example: Brand styling with "Brand Guidelines" -> "Colors" -> "Typography" -> "Features"
- Structure: ## Overview -> ## Guidelines -> ## Specifications -> ## Usage...

**4. Capabilities-Based** (best for integrated systems)
- Works well when the skill provides multiple interrelated features
- Example: Product Management with "Core Capabilities" -> numbered capability list
- Structure: ## Overview -> ## Core Capabilities -> ### 1. Feature -> ### 2. Feature...

Patterns can be mixed and matched as needed. Most skills combine patterns (e.g., start with task-based, add workflow for complex operations).

Keep deterministic checks in scripts, detailed contracts in references, concrete inputs in examples, and expected outputs in golden.]

## Safety Contracts

- 근거 없음, 권리 불명, 승인 없음, 성과 미확인은 승격 실패다.
- confidence는 근거·성과·승인을 대체하지 않는다.
- 한 파일에는 한 writer만 둔다. 공용 문서와 Git은 CTO/integration lane만 다룬다.
- WorkflowEngine, 원자료, 기존 학습 저장소를 변경하지 않는다.

## Resources (optional)

Create only the resource directories this skill actually needs. Delete this section if no resources are required.

### scripts/
Executable code (Python/Bash/etc.) that can be run directly to perform specific operations.

**Examples from other skills:**
- PDF skill: `fill_fillable_fields.py`, `extract_form_field_info.py` - utilities for PDF manipulation
- DOCX skill: `document.py`, `utilities.py` - Python modules for document processing

**Appropriate for:** Python scripts, shell scripts, or any executable code that performs automation, data processing, or specific operations.

**Note:** Scripts may be executed without loading into context, but can still be read by Codex for patching or environment adjustments.

### references/
Documentation and reference material intended to be loaded into context to inform Codex's process and thinking.

**Examples from other skills:**
- Product management: `communication.md`, `context_building.md` - detailed workflow guides
- BigQuery: API reference documentation and query examples
- Finance: Schema documentation, company policies

**Appropriate for:** In-depth documentation, API references, database schemas, comprehensive guides, or any detailed information that Codex should reference while working.

### assets/
Files not intended to be loaded into context, but rather used within the output Codex produces.

**Examples from other skills:**
- Brand styling: PowerPoint template files (.pptx), logo files
- Frontend builder: HTML/React boilerplate project directories
- Typography: Font files (.ttf, .woff2)

**Appropriate for:** Templates, boilerplate code, document templates, images, icons, fonts, or any files meant to be copied or used in the final output.

---

**Not every skill requires all three types of resources.**
