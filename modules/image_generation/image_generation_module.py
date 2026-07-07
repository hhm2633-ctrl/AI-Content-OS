import os
from typing import Any, Dict, List, Optional

try:
    from modules.base_module import BaseModule
except ImportError:
    from src.base_module import BaseModule


class ImageGenerationModule(BaseModule):
    """
    ImageGenerationModule

    역할:
    - ImagePromptModule 결과를 받아 이미지 생성 결과 구조를 만든다.
    - 현재 단계에서는 실제 이미지 API 호출 전 단계로, 안전한 placeholder 구조를 생성한다.
    - 나중에 OpenAI Images API를 붙일 때 이 파일만 확장하면 된다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}

        self.output_dir = (
            self.config.get("output_dir")
            or self.config.get("image_output_dir")
            or os.path.join("storage", "images")
        )

        os.makedirs(self.output_dir, exist_ok=True)

    def run(self, image_prompt_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        print("Image Generation Module Started")

        image_prompt_result = image_prompt_result or {}

        title = image_prompt_result.get("title", "AI content automation")
        image_prompts = image_prompt_result.get("image_prompts", [])

        generated_images = self._create_placeholder_results(image_prompts)

        result = {
            "title": title,
            "images": generated_images,
            "status": "image_generation_prepared",
        }

        print("Image Generation Module Finished")
        return result

    def _create_placeholder_results(
        self,
        image_prompts: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        images = []

        if not image_prompts:
            image_prompts = [
                {
                    "page": 1,
                    "prompt": "Clean modern AI content automation concept image, no text",
                    "style": "clean modern instagram card news",
                    "ratio": "1:1",
                }
            ]

        for item in image_prompts:
            page = item.get("page", len(images) + 1)
            prompt = item.get("prompt", "")

            filename = f"image_page_{page}.png"
            file_path = os.path.join(self.output_dir, filename)

            images.append(
                {
                    "page": page,
                    "prompt": prompt,
                    "image_path": file_path,
                    "status": "placeholder_ready",
                }
            )

        return images