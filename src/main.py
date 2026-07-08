import json
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

from src.workflow_engine import WorkflowEngine


def load_settings() -> Dict[str, Any]:
    settings_path = Path("settings.json")

    if not settings_path.exists():
        print("settings.json 없음. 기본 config로 실행합니다.")
        return {}

    try:
        with open(settings_path, "r", encoding="utf-8") as file:
            settings = json.load(file)

        print("settings.json 로드 완료.")
        return settings

    except Exception as error:
        print("settings.json 로드 실패. 기본 config로 실행합니다.")
        print(error)
        return {}


def main():
    print("AI-Content-OS Started")

    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY가 없습니다. .env 파일을 확인하세요.")

    config = load_settings()

    engine = WorkflowEngine(config)
    result = engine.run()

    print("")
    print("Final Status:", result.get("status"))
    print("AI-Content-OS Ready.")


if __name__ == "__main__":
    main()