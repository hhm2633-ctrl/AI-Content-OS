import os
import base64
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI

from modules.base_module import BaseModule


class ImageGenerationModule(BaseModule):
    def __init__(self, config=None):
        super().__init__(config)

        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        self.image_dir = Path("storage/generated_images")
        self.image_dir.mkdir(parents=True, exist_ok=True)

    def _extract_prompts(self, image_prompt_result: Dict[str, Any]) -> List[str]:
        prompts = []

        if isinstance(image_prompt_result, dict):
            if isinstance(image_prompt_result.get("image_prompts"), list):
                prompts = image_prompt_result.get("image_prompts")

            elif isinstance(image_prompt_result.get("prompts"), list):
                prompts = image_prompt_result.get("prompts")

            elif isinstance(image_prompt_result.get("result"), list):
                prompts = image_prompt_result.get("result")

        clean_prompts = []

        for item in prompts:
            if isinstance(item, str):
                clean_prompts.append(item)

            elif isinstance(item, dict):
                prompt = (
                    item.get("prompt")
                    or item.get("image_prompt")
                    or item.get("description")
                    or item.get("text")
                )

                if prompt:
                    clean_prompts.append(prompt)

        if not clean_prompts:
            clean_prompts = [
                "Modern Korean Instagram card news image, AI content automation theme, clean and professional, square format",
                "AI content workflow dashboard, modern digital workspace, clean Korean startup mood, square format",
                "Social media content planning desk, realistic clean style, bright lighting, square format",
                "Instagram card news background, modern minimal design, content creator style, square format",
            ]

        return clean_prompts[:4]

    def _generate_image(self, prompt: str, index: int) -> Dict[str, Any]:
        print(f"OpenAI Image API Generating: ai_image_{index}.png")

        response = self.client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024",
            n=1,
        )

        image_base64 = response.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        image_path = self.image_dir / f"ai_image_{index}.png"

        with open(image_path, "wb") as file:
            file.write(image_bytes)

        return {
            "index": index,
            "prompt": prompt,
            "image_path": str(image_path).replace("\\", "/"),
            "status": "generated",
        }

    def run(self, image_prompt_result: Dict[str, Any]) -> Dict[str, Any]:
        print("Image Generation Module Started")

        prompts = self._extract_prompts(image_prompt_result)
        images = []

        for index, prompt in enumerate(prompts, start=1):
            try:
                image_result = self._generate_image(prompt, index)
                images.append(image_result)

            except Exception as error:
                print(f"Image Generation Failed: ai_image_{index}.png")
                print(error)

                images.append({
                    "index": index,
                    "prompt": prompt,
                    "image_path": None,
                    "status": "failed",
                    "error": str(error),
                })

        result = {
            "module": "ImageGenerationModule",
            "status": "image_generation_completed",
            "images": images,
            "fallback_used": any(image.get("status") != "generated" for image in images),
            "fallback_reason": "image_api_failed" if any(image.get("status") != "generated" for image in images) else "",
        }

        print("Image Generation Module Finished")
        return result
