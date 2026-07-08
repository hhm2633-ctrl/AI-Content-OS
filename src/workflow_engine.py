import json
from pathlib import Path

from modules.trend_collector.trend_collector_module import TrendCollectorModule
from modules.topic_engine.topic_engine_module import TopicEngineModule
from modules.research.research_module import ResearchModule
from modules.content.content_module import ContentModule
from modules.image_prompt.image_prompt_module import ImagePromptModule
from modules.image_generation.image_generation_module import ImageGenerationModule
from modules.card_news.card_news_module import CardNewsModule
from modules.publishing.publishing_module import PublishingModule


class WorkflowEngine:
    def __init__(self, config=None):
        self.config = config or {}
        self.output_dir = Path("storage/workflow_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.trend_collector = TrendCollectorModule(self.config)
        self.topic_engine = TopicEngineModule(self.config)
        self.research_module = ResearchModule(self.config)
        self.content_module = ContentModule(self.config)
        self.image_prompt_module = ImagePromptModule(self.config)
        self.image_generation_module = ImageGenerationModule(self.config)
        self.card_news_module = CardNewsModule(self.config)
        self.publishing_module = PublishingModule(self.config)

    def run(self):
        print("=" * 50)
        print("Workflow Engine Started")
        print("=" * 50)

        try:
            trend_result = self.trend_collector.run()
            self._save_workflow_result("01_trend_result.json", trend_result)

            topic_result = self.topic_engine.run(trend_result)
            self._save_workflow_result("02_topic_result.json", topic_result)

            research_result = self.research_module.run(topic_result)
            self._save_workflow_result("03_research_result.json", research_result)

            content_result = self.content_module.run(research_result)
            self._save_workflow_result("04_content_result.json", content_result)

            image_prompt_result = self.image_prompt_module.run(content_result)
            self._save_workflow_result("05_image_prompt_result.json", image_prompt_result)

            image_generation_result = self.image_generation_module.run(image_prompt_result)
            self._save_workflow_result("06_image_generation_result.json", image_generation_result)

            card_news_result = self.card_news_module.run(
                content_result,
                image_generation_result
            )
            self._save_workflow_result("07_card_news_result.json", card_news_result)

            publishing_result = self.publishing_module.run(card_news_result)
            self._save_workflow_result("08_publishing_result.json", publishing_result)

            final_result = {
                "status": "workflow_completed",
                "trend": trend_result,
                "topic": topic_result,
                "research": research_result,
                "content": content_result,
                "image_prompt": image_prompt_result,
                "image_generation": image_generation_result,
                "card_news": card_news_result,
                "publishing": publishing_result
            }

            self._save_workflow_result("99_final_result.json", final_result)

            print("=" * 50)
            print("workflow_completed")
            print("=" * 50)

            return final_result

        except Exception as error:
            error_result = {
                "status": "workflow_failed",
                "error": str(error)
            }

            self._save_workflow_result("00_workflow_error.json", error_result)

            print("=" * 50)
            print("workflow_failed")
            print(str(error))
            print("=" * 50)

            return error_result

    def _save_workflow_result(self, filename, data):
        file_path = self.output_dir / filename

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        print(f"Workflow Result Saved: {file_path}")