import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from modules.base_module import BaseModule
except ImportError:
    from src.base_module import BaseModule

from modules.ai_planner.planner_consumer_adapter import PlannerConsumerAdapter, build_consumption_metadata
from modules.image_strategy.ai_image_decision import AIImageDecision
from modules.image_strategy.content_type_classifier import ContentTypeClassifier
from modules.image_strategy.image_source_selector import ImageSourceSelector
from modules.knowledge_engine.knowledge_interface import KnowledgeInterface


class ImageStrategyModule(BaseModule):
    """
    Image Strategy v1.

    WorkflowEngine에서 ContentModule 이후, ImagePromptModule 이전에 실행되어
    이번 콘텐츠가 AI 이미지 생성을 실제로 필요로 하는지 결정한다. 목표는
    "AI 이미지를 잘 만드는 것"이 아니라 "AI 이미지를 가능한 적게 사용하는
    것"이다.

    이 모듈 자체가 실패해도 workflow_completed를 깨지 않도록, 실패 시 항상
    need_ai_image=True(기존 AI 생성 경로로 계속 진행)인 안전한 기본 결과를
    반환한다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}
        self.output_dir = Path("storage/image_strategy")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.content_type_classifier = ContentTypeClassifier()
        self.image_source_selector = ImageSourceSelector()
        self.ai_image_decision = AIImageDecision()

        # Knowledge Interface 실제 연결(Sprint 12): 이미지 전략 결정 로직은 그대로 두고,
        # 축적된 Knowledge DB의 상위 image_strategy/tool 참고 정보만 결과에 덧붙인다.
        self.knowledge_interface = KnowledgeInterface()

        # AI Planner Consumer Adapter 실제 연결(Sprint 15-3): ContentTypeClassifier의
        # 기존 분류는 그대로 두고, Planner Hint가 유효/충분히 확신할 만하고 지원되는
        # content_type일 때만 그 값으로 교체한다. 이 교체는 어떤 content_type을
        # 쓸지에만 영향을 주며, ImageSourceSelector/AIImageDecision의 "실제 이미지
        # 우선, AI 이미지는 마지막 수단" 로직 자체는 그대로 실행되므로 Planner가
        # AI 이미지 생성을 강제로 켤 수 없다.
        self.planner_consumer_adapter = PlannerConsumerAdapter()

    def run(
        self,
        content_result: Optional[Dict[str, Any]] = None,
        research_result: Optional[Dict[str, Any]] = None,
        planner_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        print("Image Strategy Module Started")

        result = self._build_result(content_result or {}, research_result or {}, planner_result)
        result["knowledge_reference"] = self._build_knowledge_reference()

        try:
            self._save_result(result)
        except Exception as error:
            print(f"Image Strategy Result Save Failed: {error}")

        print("Image Strategy Module Finished")
        return result

    def _build_knowledge_reference(self) -> Dict[str, Any]:
        try:
            return {
                "top_image_strategies": self.knowledge_interface.get_image_strategy_knowledge(limit=3),
                "top_tools": self.knowledge_interface.get_tool_knowledge(limit=3),
            }
        except Exception as error:
            print(f"Image Strategy Knowledge Reference Failed: {error}")
            return {"top_image_strategies": [], "top_tools": []}

    def _build_result(
        self,
        content_result: Dict[str, Any],
        research_result: Dict[str, Any],
        planner_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            classification = self.content_type_classifier.classify(research_result, content_result)
            engine_content_type = classification.get("content_type", "education")

            image_consumption = self.planner_consumer_adapter.resolve_image_strategy(
                planner_result=planner_result,
                engine_content_type=engine_content_type,
            )
            content_type = image_consumption.get("content_type", engine_content_type)

            source_result = self.image_source_selector.select(content_type)
            decision = self.ai_image_decision.decide(content_type, source_result)

            need_ai_image = bool(decision.get("need_ai_image", True))

            planner_requested_image_strategy = (
                planner_result.get("selected_image_strategy") if isinstance(planner_result, dict) else None
            )

            return {
                "status": "image_strategy_completed",
                "content_type": content_type,
                "content_type_reason": classification.get("reason", ""),
                "image_source": decision.get("image_source", "ai_image"),
                "priority": decision.get("priority", ["ai_image"]),
                "need_ai_image": need_ai_image,
                "reason": decision.get("reason", ""),
                "image_usage_plan": self._build_image_usage_plan(
                    content_type=content_type,
                    need_ai_image=need_ai_image,
                    decision=decision,
                ),
                "fallback_used": bool(
                    classification.get("fallback_used")
                    or source_result.get("fallback_used")
                    or decision.get("fallback_used")
                ),
                "planner_consumption": {
                    "image_strategy": build_consumption_metadata(
                        planner_result=planner_result,
                        hint_applied=bool(image_consumption.get("hint_applied")),
                        requested_value=planner_requested_image_strategy,
                        original_value=engine_content_type,
                        final_value=content_type,
                        reason=image_consumption.get("reason", ""),
                    ),
                },
                "created_at": datetime.now().isoformat(),
            }

        except Exception as error:
            print(f"Image Strategy Build Failed, using safe AI fallback: {error}")
            return self._fallback_result(reason=f"image_strategy_exception: {error}")

    def _build_image_usage_plan(
        self,
        content_type: str,
        need_ai_image: bool,
        decision: Dict[str, Any],
    ) -> Dict[str, Any]:
        if need_ai_image:
            return {
                "mode": "ai_generation",
                "notes": "실제 이미지 소스가 아직 자동화되지 않아 AI 이미지 생성으로 진행함.",
            }

        return {
            "mode": "real_image_required",
            "recommended_source": decision.get("image_source", ""),
            "priority": decision.get("priority", []),
            "notes": (
                f"content_type '{content_type}'은 AI 이미지 대신 실제 이미지"
                f"({decision.get('image_source', '')})를 사용하는 것을 권장함. "
                "실제 수집/캡처 자동화는 아직 구현되지 않았으므로 수동 소싱 또는 "
                "향후 Sprint 연동이 필요하며, 이번 실행은 AI 이미지 생성을 생략함."
            ),
        }

    def _fallback_result(self, reason: str) -> Dict[str, Any]:
        return {
            "status": "image_strategy_completed",
            "content_type": "education",
            "content_type_reason": "",
            "image_source": "ai_image",
            "priority": ["ai_image"],
            "need_ai_image": True,
            "reason": reason,
            "image_usage_plan": {
                "mode": "ai_generation",
                "notes": "Image Strategy 계산 실패로 안전하게 AI 이미지 생성으로 진행함.",
            },
            "fallback_used": True,
            "created_at": datetime.now().isoformat(),
        }

    def _save_result(self, result: Dict[str, Any]) -> None:
        file_path = self.output_dir / "image_strategy_result.json"

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)

        print(f"Image Strategy Result Saved: {file_path}")
