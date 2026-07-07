import json
from pathlib import Path
from modules.base_module import BaseModule


class ImagePromptModule(BaseModule):
    def __init__(self, config):
        super().__init__(config)
        self.output_dir = Path("storage/outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, content_result):
        print("Image Prompt Module Started")

        title = content_result.get("title", "")
        body = content_result.get("body", [])

        image_prompts = []

        for index, slide_text in enumerate(body, start=1):
            prompt = {
                "slide": index,
                "text": slide_text,
                "image_prompt": (
                    f"Create a realistic Korean Instagram card news image. "
                    f"Topic: {title}. "
                    f"Slide message: {slide_text}. "
                    f"Style: clean, modern, high readability, social media optimized, "
                    f"professional editorial design, 1:1 square ratio, no text inside image."
                ),
                "negative_prompt": (
                    "blurry, low quality, distorted face, broken hands, unreadable text, "
                    "watermark, logo, messy layout, excessive details"
                ),
                "size": "1024x1024"
            }

            image_prompts.append(prompt)

        result = {
            "title": title,
            "image_prompts": image_prompts,
            "status": "image_prompts_created"
        }

        output_path = self.output_dir / "image_prompt_result.json"

        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)

        print("Image Prompt Result Saved:", output_path)

        return result