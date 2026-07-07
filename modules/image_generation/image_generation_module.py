"""
Image Generation Module
AI-Content-OS

OpenAI Images API를 사용해 카드뉴스용 이미지를 생성하고
storage/images 폴더에 PNG 파일로 저장한다.
"""

import base64
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from modules.base_module import BaseModule


class ImageGenerationModule(BaseModule):
    def __init__(self, config):
        super().__init__(config)

        load_dotenv()

        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        self.output_dir = Path("storage/outputs")
        self.image_dir = Path("storage/images")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.image_dir.mkdir(parents=True, exist_ok=True)

    def run(self, image_prompt_result):
        print("Image Generation Module Started")

        title = image_prompt_result.get("title", "")
        image_prompts = image_prompt_result.get("image_prompts", [])

        generated_images = []

        for item in image_prompts:
            slide_number = item.get("slide")
            image_prompt = item.get("image_prompt")

            print(f"Generating image for slide {slide_number}...")

            response = self.client.images.generate(
                model="gpt-image-1",
                prompt=image_prompt,
                size="1024x1024",
                quality="medium",
                n=1
            )

            image_base64 = response.data[0].b64_json
            image_bytes = base64.b64decode(image_base64)

            image_filename = f"card_slide_{slide_number}.png"
            image_path = self.image_dir / image_filename

            with open(image_path, "wb") as image_file:
                image_file.write(image_bytes)

            generated_image = {
                "slide": slide_number,
                "image_prompt": image_prompt,
                "image_path": str(image_path),
                "status": "image_generated"
            }

            generated_images.append(generated_image)

            print(f"Image Saved: {image_path}")

        result = {
            "title": title,
            "generated_images": generated_images,
            "status": "image_generation_completed"
        }

        output_path = self.output_dir / "image_generation_result.json"

        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)

        print("Image Generation Result Saved:", output_path)

        return result