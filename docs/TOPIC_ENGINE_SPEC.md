# AI-Content-OS
# Topic Engine Specification

Version: 1.0

---

## 1. Purpose

Topic Engine은 사람이 직접 주제를 정하지 않아도  
AI-Content-OS가 매일 제작할 콘텐츠 주제를 자동으로 찾고 선택하는 시스템이다.

최종 목표는 다음과 같다.

- 오늘 사람들이 관심 가질 주제 찾기
- 카드뉴스로 만들기 좋은 주제 고르기
- 계정별로 맞는 주제 분류하기
- 중복 주제 제거하기
- 위험하거나 부적절한 주제 제외하기
- 최종 제작 후보를 ResearchModule에 전달하기

---

## 2. Role

Topic Engine은 콘텐츠 제작의 시작점이다.

기존 흐름:

Research  
↓  
Content  
↓  
Image Prompt  
↓  
Image Generation  
↓  
Card News  
↓  
Publishing

변경될 흐름:

Trend Collector  
↓  
Topic Engine  
↓  
Research  
↓  
Content  
↓  
Image Prompt  
↓  
Image Generation  
↓  
Card News  
↓  
Publishing

---

## 3. Input

Topic Engine이 받는 입력값은 다음과 같다.

```json
{
  "raw_topics": [
    {
      "title": "수집된 주제 제목",
      "source": "news | community | search | youtube | manual",
      "url": "원본 URL",
      "published_at": "수집 또는 게시 시간",
      "summary": "수집된 내용 요약",
      "keywords": ["키워드1", "키워드2"]
    }
  ]
}