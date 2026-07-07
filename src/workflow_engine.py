"""
AI-Content-OS
Workflow Engine
Version: 1.0
"""

from modules.research.research_module import ResearchModule
from modules.content.content_module import ContentModule


class WorkflowEngine:
    def __init__(self):
        self.status = "READY"
        self.research_module = ResearchModule()
        self.content_module = ContentModule()

    def start(self):
        print("=" * 50)
        print("Workflow Engine Started")
        print("=" * 50)

    def stop(self):
        print("=" * 50)
        print("Workflow Engine Stopped")
        print("=" * 50)

    def run(self):
        print("Running Workflow...")

        research_result = self.research_module.run("AI content automation")
        print("Research Result:")
        print(research_result)

        content_result = self.content_module.run(research_result)
        print("Content Result:")
        print(content_result)