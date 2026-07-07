from modules.research.research_module import ResearchModule
from modules.content.content_module import ContentModule
from modules.image_prompt.image_prompt_module import ImagePromptModule
from modules.image_generation.image_generation_module import ImageGenerationModule
from modules.card_news.card_news_module import CardNewsModule
from modules.publishing.publishing_module import PublishingModule


class WorkflowEngine:
    def __init__(self, config):
        self.config = config

        self.research_module = ResearchModule(config)
        self.content_module = ContentModule(config)
        self.image_prompt_module = ImagePromptModule(config)
        self.image_generation_module = ImageGenerationModule(config)
        self.card_news_module = CardNewsModule(config)
        self.publishing_module = PublishingModule(config)

    def run(self):
        print("Workflow Engine Started")

        research_result = self.research_module.run()
        content_result = self.content_module.run(research_result)
        image_prompt_result = self.image_prompt_module.run(content_result)
        image_generation_result = self.image_generation_module.run(image_prompt_result)
        card_news_result = self.card_news_module.run(content_result, image_generation_result)
        publishing_result = self.publishing_module.run(content_result, card_news_result)

        print("Workflow Engine Stopped")

        return {
            "research_result": research_result,
            "content_result": content_result,
            "image_prompt_result": image_prompt_result,
            "image_generation_result": image_generation_result,
            "card_news_result": card_news_result,
            "publishing_result": publishing_result
        }