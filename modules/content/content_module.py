import json
from typing import Any, Dict, Optional

try:
    from modules.base_module import BaseModule
except ImportError:
    from src.base_module import BaseModule

from src.llm_client import LLMClient
from modules.knowledge_engine.knowledge_interface import KnowledgeInterface
from modules.content.content_prompt_builder import ContentPromptBuilder
from modules.content.brand_rule_evaluator import BrandRuleEvaluator
from modules.content.content_duplicate_detector import ContentDuplicateDetector
from modules.content.content_quality_scorer import ContentQualityScorer
from modules.content.publishing_hint_generator import PublishingHintGenerator


class ContentModule(BaseModule):
    def __init__(self, config: Optional[Dict[str, Any]] = None, llm_client: Optional[LLMClient] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}
        self.llm_client = llm_client or getattr(self, "llm_client", None) or LLMClient(
            self.config.get("llm", self.config)
        )
        self.prompt_builder = ContentPromptBuilder(self.config)

        self.quality_scorer = ContentQualityScorer(self.config)
        self.duplicate_detector = ContentDuplicateDetector(self.config)
        self.publishing_hint_generator = PublishingHintGenerator(self.config)
        self.brand_rule_evaluator = BrandRuleEvaluator(self.config)

        # Knowledge Interface 실제 연결(Sprint 13): 축적된 Knowledge DB의 상위
        # hook/cta를 실제로 읽어 LLM user_prompt에 참고 예시로 주입한다(그대로
        # 복사 금지 문구 포함). 프롬프트 빌더/파싱 로직 자체는 바꾸지 않는다.
        self.knowledge_interface = KnowledgeInterface()

    def run(self, research_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        print("Content Module Started")

        research_result = research_result or {}

        keyword = research_result.get("keyword") or research_result.get("topic") or "AI content automation"
        title = research_result.get("title") or f"{keyword} 카드뉴스"
        summary = research_result.get("summary", "")
        key_points = research_result.get("key_points", [])
        target = research_result.get("target", "AI 자동화와 부업에 관심 있는 초보자")
        topic_angle = research_result.get("topic_angle", "")

        prompt_source = "legacy"
        prompt_meta: Dict[str, Any] = {}

        try:
            pattern_aware_prompt = self.prompt_builder.build(research_result)
        except Exception as error:
            print(f"Content Prompt Builder Failed, falling back to legacy prompt: {error}")
            pattern_aware_prompt = None

        knowledge_guidance = self._fetch_knowledge_guidance()

        if pattern_aware_prompt:
            system_prompt = pattern_aware_prompt["system_prompt"]
            user_prompt = pattern_aware_prompt["user_prompt"] + knowledge_guidance["guidance_text"]
            prompt_source = "pattern_aware"
            prompt_meta = pattern_aware_prompt.get("meta", {})
        else:
            system_prompt = self._legacy_system_prompt()
            user_prompt = self._legacy_user_prompt(
                keyword=keyword,
                title=title,
                summary=summary,
                key_points=key_points,
                target=target,
                topic_angle=topic_angle,
            ) + knowledge_guidance["guidance_text"]

        llm_response = self.llm_client.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        content_result = self._safe_json_parse(llm_response, keyword)
        content_result["prompt_source"] = prompt_source
        content_result["pattern_prompt_meta"] = prompt_meta
        content_result["content_intelligence"] = self._build_content_intelligence(
            content_result=content_result,
            research_result=research_result,
            prompt_meta=prompt_meta,
        )

        knowledge_items = knowledge_guidance["knowledge_items"]
        content_result["knowledge_used"] = bool(knowledge_items)
        content_result["knowledge_items"] = knowledge_items
        content_result["knowledge_influence"] = (
            f"LLM user_prompt에 상위 Hook/CTA 참고 예시 {len(knowledge_items)}건을 추가함."
            if knowledge_items
            else "참고할 만큼 점수가 높은 Knowledge 항목이 아직 없어 프롬프트를 그대로 사용함."
        )

        print("Content Module Finished")
        return content_result

    def _fetch_knowledge_guidance(self) -> Dict[str, Any]:
        try:
            top_hooks = self.knowledge_interface.get_top_hooks(limit=2)
            top_ctas = self.knowledge_interface.get_top_ctas(limit=2)
        except Exception as error:
            print(f"Content Knowledge Fetch Failed: {error}")
            top_hooks, top_ctas = [], []

        guidance_lines = []
        knowledge_items = []

        for item in top_hooks:
            headline = str((item.get("content") or {}).get("headline", "")).strip()

            if headline:
                guidance_lines.append(f"- (참고 Hook, 문장 그대로 복사 금지) {headline}")
                knowledge_items.append({
                    "knowledge_id": item.get("knowledge_id"),
                    "type": "hook",
                    "title": item.get("title"),
                })

        for item in top_ctas:
            headline = str((item.get("content") or {}).get("headline", "")).strip()

            if headline:
                guidance_lines.append(f"- (참고 CTA, 문장 그대로 복사 금지) {headline}")
                knowledge_items.append({
                    "knowledge_id": item.get("knowledge_id"),
                    "type": "cta",
                    "title": item.get("title"),
                })

        guidance_text = ""
        if guidance_lines:
            guidance_text = (
                "\n\n참고 (과거 실행에서 점수가 높았던 Hook/CTA 스타일 - 그대로 복사하지 말고 "
                "이번 주제에 맞게 새로 쓸 것):\n" + "\n".join(guidance_lines)
            )

        return {"guidance_text": guidance_text, "knowledge_items": knowledge_items}

    def _build_content_intelligence(
        self,
        content_result: Dict[str, Any],
        research_result: Dict[str, Any],
        prompt_meta: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            brand_result = self.brand_rule_evaluator.evaluate(content_result)
            quality_result = self.quality_scorer.score(
                content_result, research_result, prompt_meta, brand_result
            )
            duplicate_result = self.duplicate_detector.check(content_result)

            pattern_plan = research_result.get("pattern_plan") or {}
            cta_type = prompt_meta.get("cta_type") if isinstance(prompt_meta, dict) else None

            publishing_hint = self.publishing_hint_generator.generate(
                content_result,
                pattern_plan=pattern_plan,
                cta_type=cta_type,
            )

            recommendations = self._build_recommendations(quality_result, duplicate_result, brand_result)

            self.duplicate_detector.record(content_result)

            return {
                "quality_score": quality_result.get("quality_score", 0.0),
                "duplicate_risk": duplicate_result.get("duplicate_risk", "low"),
                "brand_rule_passed": brand_result.get("brand_rule_passed", False),
                "publishing_hint": publishing_hint,
                "recommendations": recommendations,
                "details": {
                    "quality": quality_result,
                    "duplicate": duplicate_result,
                    "brand_rule": brand_result,
                },
            }

        except Exception as error:
            print(f"Content Intelligence Build Failed: {error}")

            return {
                "quality_score": 0.0,
                "duplicate_risk": "low",
                "brand_rule_passed": False,
                "publishing_hint": {},
                "details": {
                    "quality": {},
                    "duplicate": {},
                    "brand_rule": {},
                    "error": str(error),
                },
                "recommendations": ["content_intelligence 계산 실패 - 수동 검수 필요"],
            }

    def _build_recommendations(
        self,
        quality_result: Dict[str, Any],
        duplicate_result: Dict[str, Any],
        brand_result: Dict[str, Any],
    ) -> list:
        recommendations = []

        quality_score = quality_result.get("quality_score", 0.0)
        if quality_score < 0.5:
            recommendations.append("quality_score가 낮습니다. headline/body를 더 구체적으로 다시 작성하세요.")

        checks = quality_result.get("checks", {})
        if not checks.get("hook_present", True):
            recommendations.append("hook 슬라이드가 빈약합니다. 후킹 문구를 보강하세요.")
        if not checks.get("cta_present", True):
            recommendations.append("CTA 슬라이드가 빈약합니다. 행동 유도 문구를 보강하세요.")
        if not checks.get("topic_reflected", True):
            recommendations.append("선택된 주제 키워드가 콘텐츠에 잘 드러나지 않습니다.")

        duplicate_risk = duplicate_result.get("duplicate_risk", "low")
        if duplicate_risk == "high":
            recommendations.append("최근 콘텐츠와 매우 유사합니다. 주제/문구를 다시 검토하세요.")
        elif duplicate_risk == "medium":
            recommendations.append("최근 콘텐츠와 유사도가 있습니다. 차별점을 강화하세요.")

        if not brand_result.get("brand_rule_passed", True):
            recommendations.append("브랜드 금지 표현 또는 과장 표현이 감지되었습니다. 문구를 수정하세요.")

        if not recommendations:
            recommendations.append("특별한 개선 필요 사항이 없습니다.")

        return recommendations

    def _legacy_system_prompt(self) -> str:
        return """
너는 인스타그램 카드뉴스 전문 기획자이자 카피라이터다.
초보자가 바로 이해할 수 있게 짧고 강하게 쓴다.
허위 수익 보장, 과장 광고, 투자 권유 표현은 피한다.
각 슬라이드는 headline과 body를 반드시 분리한다.
반드시 JSON 형식으로만 답변한다.
"""

    def _legacy_user_prompt(
        self,
        keyword: str,
        title: str,
        summary: str,
        key_points: Any,
        target: str,
        topic_angle: str,
    ) -> str:
        return f"""
아래 리서치 내용을 바탕으로 인스타그램 카드뉴스 4장을 만들어줘.

주제:
{keyword}

제목:
{title}

요약:
{summary}

핵심 포인트:
{key_points}

타깃:
{target}

콘텐츠 관점:
{topic_angle}

조건:
- 1장은 강한 후킹
- 2장은 문제 설명
- 3장은 해결 구조
- 4장은 저장/팔로우 유도
- headline은 짧게
- body는 1~2문장
- 초보자 말투
- 너무 어려운 용어 금지

아래 JSON 형식으로만 답변해줘.

{{
  "title": "카드뉴스 전체 제목",
  "slides": [
    {{
      "page": 1,
      "role": "hook",
      "headline": "1장 제목",
      "body": "1장 본문"
    }},
    {{
      "page": 2,
      "role": "problem",
      "headline": "2장 제목",
      "body": "2장 본문"
    }},
    {{
      "page": 3,
      "role": "solution",
      "headline": "3장 제목",
      "body": "3장 본문"
    }},
    {{
      "page": 4,
      "role": "cta",
      "headline": "4장 제목",
      "body": "4장 본문"
    }}
  ],
  "caption": "인스타그램 본문 캡션",
  "hashtags": ["#AI콘텐츠", "#콘텐츠자동화", "#카드뉴스", "#부업준비", "#인스타콘텐츠"],
  "status": "content_created"
}}
"""

    def _safe_json_parse(self, text: str, keyword: str) -> Dict[str, Any]:
        try:
            result = json.loads(text)

            if not isinstance(result, dict):
                raise ValueError("LLM result is not dict")

            if result.get("status") == "llm_failed":
                raise ValueError(result.get("error", "llm_failed"))

            if "slides" not in result or not isinstance(result["slides"], list):
                raise ValueError("slides missing")

            result["slides"] = self._normalize_slides(result["slides"], keyword)
            result["status"] = "content_created"
            result["fallback_used"] = False
            result["fallback_reason"] = ""

            if not result.get("title"):
                result["title"] = f"{keyword} 카드뉴스"

            if not result.get("caption"):
                result["caption"] = f"{keyword}는 작게 시작해서 자동화 구조로 키우는 것이 중요합니다."

            if not result.get("hashtags"):
                result["hashtags"] = ["#AI콘텐츠", "#콘텐츠자동화", "#카드뉴스", "#부업준비"]

            return result

        except Exception as error:
            return {
                "title": f"{keyword} 지금 시작해야 하는 이유",
                "slides": self._fallback_slides(keyword),
                "caption": f"{keyword}는 처음부터 완벽하게 만들기보다, 작은 구조부터 자동화하는 것이 중요합니다. 저장해두고 하나씩 따라가세요.",
                "hashtags": ["#AI콘텐츠", "#콘텐츠자동화", "#카드뉴스", "#부업준비", "#인스타콘텐츠"],
                "status": "content_created",
                "fallback_used": True,
                "fallback_reason": f"llm_or_json_parse_failed: {error}",
            }

    def _normalize_slides(self, slides, keyword: str):
        fallback = self._fallback_slides(keyword)
        normalized = []

        for index in range(4):
            source = slides[index] if index < len(slides) and isinstance(slides[index], dict) else {}

            normalized.append({
                "page": index + 1,
                "role": source.get("role") or fallback[index]["role"],
                "headline": str(source.get("headline") or fallback[index]["headline"]),
                "body": str(source.get("body") or fallback[index]["body"]),
            })

        return normalized

    def _fallback_slides(self, keyword: str):
        return [
            {
                "page": 1,
                "role": "hook",
                "headline": "콘텐츠, 아직 손으로만 만드세요?",
                "body": f"{keyword}는 반복 작업을 줄이고 카드뉴스 제작 속도를 높이는 핵심 구조입니다.",
            },
            {
                "page": 2,
                "role": "problem",
                "headline": "문제는 시간이 너무 많이 든다는 것",
                "body": "주제 찾기, 글쓰기, 이미지 만들기, 발행 준비를 매번 손으로 하면 금방 지칩니다.",
            },
            {
                "page": 3,
                "role": "solution",
                "headline": "그래서 흐름을 나눠야 합니다",
                "body": "주제 선택, 리서치, 문안 작성, 이미지 생성, 카드뉴스 제작을 모듈로 나누면 안정적으로 반복할 수 있습니다.",
            },
            {
                "page": 4,
                "role": "cta",
                "headline": "작게 만들고 계속 개선하세요",
                "body": "처음 목표는 완벽한 자동화가 아니라 매일 돌아가는 구조입니다. 저장하고 하나씩 따라오세요.",
            },
        ]
