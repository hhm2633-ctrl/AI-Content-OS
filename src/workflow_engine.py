import json
import os
from typing import Any, Dict, Optional

from modules.research.research_module import ResearchModule
from modules.content.content_module import ContentModule
from modules.image_prompt.image_prompt_module import ImagePromptModule
from modules.image_generation.image_generation_module import ImageGenerationModule
from modules.card_news.card_news_module import CardNewsModule
from modules.publishing.publishing_module import PublishingModule


class WorkflowEngine:
    """
    AI-Content-OS Workflow Engine

    실행 순서:
    1. ResearchModule
    2. ContentModule
    3. ImagePromptModule
    4. ImageGenerationModule
    5. CardNewsModule
    6. PublishingModule
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        self.research_module = ResearchModule(self.config.get("research", self.config))
        self.content_module = ContentModule(self.config.get("content", self.config))
        self.image_prompt_module = ImagePromptModule(
            self.config.get("image_prompt", self.config)
        )
        self.image_generation_module = ImageGenerationModule(
            self.config.get("image_generation", self.config)
        )
        self.card_news_module = CardNewsModule(
            self.config.get("card_news", self.config)
        )
        self.publishing_module = PublishingModule(
            self.config.get("publishing", self.config)
        )

    def run(self) -> Dict[str, Any]:
        print("=" * 50)
        print("Workflow Engine Started")
        print("=" * 50)

        research_result = self.research_module.run()
        self._save_step_result("01_research_result.json", research_result)

        content_result = self.content_module.run(research_result)
        self._save_step_result("02_content_result.json", content_result)

        image_prompt_result = self.image_prompt_module.run(content_result)
        self._save_step_result("03_image_prompt_result.json", image_prompt_result)

        image_generation_result = self.image_generation_module.run(image_prompt_result)
        self._save_step_result("04_image_generation_result.json", image_generation_result)

        card_news_result = self.card_news_module.run(
            content_result=content_result,
            image_generation_result=image_generation_result,
        )
        self._save_step_result("05_card_news_result.json", card_news_result)

        publishing_result = self.publishing_module.run(card_news_result)
        self._save_step_result("06_publishing_result.json", publishing_result)

        final_result = {
            "research_result": research_result,
            "content_result": content_result,
            "image_prompt_result": image_prompt_result,
            "image_generation_result": image_generation_result,
            "card_news_result": card_news_result,
            "publishing_result": publishing_result,
            "status": "workflow_completed",
        }

        self._save_step_result("final_result.json", final_result)

        print("=" * 50)
        print("Workflow Engine Finished")
        print("=" * 50)

        return final_result

    def _save_step_result(self, filename: str, data: Dict[str, Any]) -> None:
        output_dir = os.path.join("storage", "workflow_results")
        os.makedirs(output_dir, exist_ok=True)

        file_path = os.path.join(output_dir, filename)

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        print(f"Workflow Result Saved: {file_path}")