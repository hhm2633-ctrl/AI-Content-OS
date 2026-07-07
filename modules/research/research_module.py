from modules.base_module import BaseModule


class ResearchModule(BaseModule):

    def __init__(self):
        super().__init__("Research")

    def run(self, input_data=None):

        print()

        print("========== Research Module ==========")

        print("Collecting research data...")

        result = {
            "topic": input_data,
            "keywords": [],
            "references": []
        }

        print("Research Complete")

        print()

        return result