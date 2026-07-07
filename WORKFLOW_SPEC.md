# WORKFLOW_SPEC.md

# AI-Content-OS
Workflow Specification

Version: 1.0

---

# Purpose

본 문서는 AI-Content-OS의 전체 작업 흐름(Workflow)을 정의한다.

모든 작업은 Workflow Engine이 제어하며,
각 Module은 Workflow Engine의 요청에 따라 순차적으로 실행된다.

Workflow는 재사용 가능해야 하며,
새로운 Workflow를 쉽게 추가할 수 있어야 한다.

---

# Workflow Principles

모든 Workflow는 다음 규칙을 따른다.

- 시작(Start)이 존재한다.
- 종료(End)가 존재한다.
- 각 단계는 독립적으로 실행된다.
- 실패 시 재시도(Retry)를 수행한다.
- 실패가 지속되면 Human Review 상태로 전환한다.
- 모든 단계는 로그를 기록한다.

---

# Standard Workflow Structure

Start

↓

Task Creation

↓

Task Validation

↓

Workflow Selection

↓

Module Execution

↓

Quality Check

↓

Save

↓

Complete

↓

End

---

# Workflow Engine Responsibilities

Workflow Engine의 역할은 다음과 같다.

- Workflow 선택
- Module 호출
- 실행 순서 관리
- 상태 관리
- 오류 처리
- 로그 기록
- 결과 저장

---

# Workflow Status

각 Workflow는 아래 상태를 가진다.

- Pending
- Ready
- Running
- Waiting
- Completed
- Failed
- Retry
- Cancelled

---

# Workflow 01 - Content Creation

목적

콘텐츠 자동 생성

Flow

Research Module

↓

Keyword Module

↓

Content Module

↓

SEO Module

↓

QA Module

↓

Save

↓

Complete

---

# Workflow 02 - Image Generation

목적

이미지 생성

Flow

Prompt

↓

Image Module

↓

Quality Check

↓

Save

↓

Complete

---

# Workflow 03 - Thumbnail Creation

목적

썸네일 제작

Flow

Product Data

↓

Image Module

↓

Thumbnail Module

↓

QA Module

↓

Save

↓

Complete

---

# Workflow 04 - Publishing

목적

콘텐츠 업로드

Flow

Approved Content

↓

Platform Formatter

↓

Publishing Module

↓

Upload Verification

↓

Complete

---

# Workflow 05 - Analytics

목적

성과 분석

Flow

Collect Data

↓

Analytics Module

↓

Generate Report

↓

Store Result

↓

Complete

---

# Workflow 06 - Full Automation

목적

완전 자동 운영

Flow

Scheduler

↓

Research

↓

Keyword

↓

Content

↓

Image

↓

Thumbnail

↓

SEO

↓

QA

↓

Publishing

↓

Analytics

↓

Memory Update

↓

Complete

---

# Workflow Validation

모든 Workflow는 다음 항목을 검증한다.

- Input Validation
- Output Validation
- Required Data
- Permission
- Resource Availability

---

# Retry Policy

실패 시

1차 Retry

↓

2차 Retry

↓

Fallback

↓

Human Review

↓

Abort

최대 Retry 횟수는 설정값(Config)에 따른다.

---

# Logging

Workflow 실행 시 다음 정보를 기록한다.

- Workflow Name
- Workflow ID
- Task ID
- Start Time
- End Time
- Execution Time
- Status
- Error
- Retry Count
- Module History

---

# Workflow Configuration

모든 Workflow는 Config 파일에서 관리한다.

예시

- Timeout
- Retry Count
- Parallel Execution
- Priority
- Schedule

---

# Parallel Execution Rules

병렬 실행 가능한 Module

- Image Generation
- Thumbnail Generation
- SEO Analysis
- Analytics Collection

순차 실행이 필요한 Module

- Research
- Content Generation
- QA
- Publishing

---

# Workflow Security

모든 Workflow는 다음 정책을 따른다.

- Input Validation
- Output Validation
- Access Control
- Logging
- Audit Trail

---

# Future Workflows

향후 추가 예정

- Instagram Workflow
- SmartStore Workflow
- Coupang Workflow
- YouTube Workflow
- Threads Workflow
- Pinterest Workflow
- Email Marketing Workflow
- AI Training Workflow

---

# End