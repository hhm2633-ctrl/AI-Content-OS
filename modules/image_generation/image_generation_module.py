import os
import base64
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from modules.base_module import BaseModule
from modules.common.service_diagnostic import ServiceDiagnostic


class ImageGenerationModule(BaseModule):
    def __init__(self, config=None):
        super().__init__(config)

        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        self.image_dir = Path("storage/generated_images")
        self.image_dir.mkdir(parents=True, exist_ok=True)

        self.service_diagnostic = ServiceDiagnostic(self.config)
        self.retry_backoff_seconds = self.config.get("image_retry_backoff_seconds", [2, 5, 10])
        if not isinstance(self.retry_backoff_seconds, list):
            self.retry_backoff_seconds = [2, 5, 10]
        self.retry_count = int(self.config.get("image_retry_count", len(self.retry_backoff_seconds)))

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

        retry_count_used = 0
        max_attempts = 1 + max(0, self.retry_count)
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
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
                    "retry_count": retry_count_used,
                    "final_error_type": "",
                }
            except Exception as error:
                last_error = error
                final_error_type = self.service_diagnostic.classify_error(
                    error,
                    bool(os.getenv("OPENAI_API_KEY")),
                )
                print(
                    f"Image Generation Retry Status: ai_image_{index}.png "
                    f"attempt={attempt}, final_error_type={final_error_type}"
                )

                if attempt < max_attempts and self._is_retryable_error_type(final_error_type):
                    delay = self._retry_delay_for_retry(retry_count_used)
                    retry_count_used += 1
                    print(
                        f"Image Generation Retry Scheduled: ai_image_{index}.png "
                        f"retry_count={retry_count_used}, delay_seconds={delay}"
                    )
                    time.sleep(delay)
                    continue

                raise ImageGenerationRetryError(
                    final_error_type=final_error_type,
                    retry_count=retry_count_used,
                    original_error=last_error,
                ) from error

        raise ImageGenerationRetryError(
            final_error_type="unknown_error",
            retry_count=retry_count_used,
            original_error=last_error,
        )

    def _is_retryable_error_type(self, error_type: str) -> bool:
        return error_type in {"connection_refused", "timeout", "unknown_error"}

    def _retry_delay_for_retry(self, retry_index: int) -> float:
        try:
            return float(self.retry_backoff_seconds[retry_index])
        except Exception:
            return 10.0

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
                final_error_type = getattr(error, "final_error_type", "unknown_error")
                retry_count = int(getattr(error, "retry_count", 0) or 0)
                print(f"Image Generation Final Error Type: {final_error_type}")

                images.append({
                    "index": index,
                    "prompt": prompt,
                    "image_path": None,
                    "status": "failed",
                    "error": final_error_type,
                    "retry_count": retry_count,
                    "final_error_type": final_error_type,
                })

        fallback_used = any(image.get("status") != "generated" for image in images)

        result = {
            "module": "ImageGenerationModule",
            "status": "image_generation_completed",
            "images": images,
            "fallback_used": fallback_used,
            "fallback_reason": "image_api_failed" if fallback_used else "",
        }

        if fallback_used:
            result["service_diagnostic"] = self._build_and_record_diagnostic(images)

        print("Image Generation Module Finished")
        return result

    def _build_and_record_diagnostic(self, images: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            first_error = next(
                (image.get("error") for image in images if image.get("status") != "generated"),
                None,
            )

            diagnostic = self.service_diagnostic.build_service_diagnostic(
                service="image",
                env_var_name="OPENAI_API_KEY",
                error=first_error,
                status="fallback_used",
            )
            diagnostic["retry_count"] = max(
                int(image.get("retry_count", 0) or 0)
                for image in images
            ) if images else 0
            diagnostic["final_error_type"] = diagnostic.get("error_type", "unknown_error")
            self.service_diagnostic.record(diagnostic)
            return diagnostic
        except Exception as error:
            print(f"Image Service Diagnostic Failed: {error}")
            return {
                "service": "image",
                "status": "fallback_used",
                "error_type": "unknown_error",
                "safe_message": "알 수 없는 오류가 발생했습니다.",
                "api_key_present": bool(os.getenv("OPENAI_API_KEY")),
                "retry_count": 0,
                "final_error_type": "unknown_error",
            }


class ImageGenerationRetryError(Exception):
    def __init__(self, final_error_type: str, retry_count: int, original_error: Any = None):
        super().__init__(final_error_type)
        self.final_error_type = final_error_type
        self.retry_count = retry_count
        self.original_error = original_error
