import json
import os
from typing import Any, Dict

from dotenv import load_dotenv

from src.workflow_engine import WorkflowEngine


def load_config() -> Dict[str, Any]:
    """
    settings.json 로드
    없거나 깨져 있으면 기본 config로 실행
    """

    config_path = "settings.json"

    default_config = {
        "topic": "AI content automation",
        "llm": {
            "model": "gpt-4.1-mini",
            "temperature": 0.7,
            "max_retries": 3,
            "retry_delay": 2,
        },
        "research": {
            "topic": "AI content automation",
        },
        "content": {},
        "image_prompt": {},
        "image_generation": {
            "output_dir": os.path.join("storage", "images"),
        },
        "card_news": {
            "output_dir": os.path.join("storage", "card_news"),
            "width": 1080,
            "height": 1080,
        },
        "publishing": {
            "output_dir": os.path.join("storage", "publishing"),
        },
    }

    if not os.path.exists(config_path):
        print("settings.json 없음. 기본 config로 실행합니다.")
        return default_config

    try:
        with open(config_path, "r", encoding="utf-8") as file:
            loaded_config = json.load(file)

        merged_config = default_config.copy()
        merged_config.update(loaded_config)

        return merged_config

    except Exception as error:
        print(f"settings.json 로드 실패: {error}")
        print("기본 config로 실행합니다.")
        return default_config


def main() -> None:
    load_dotenv()

    print("AI-Content-OS Started")

    config = load_config()
    engine = WorkflowEngine(config)

    result = engine.run()

    print("")
    print("Final Status:", result.get("status"))
    print("AI-Content-OS Ready.")


if __name__ == "__main__":
    main()