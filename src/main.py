"""
AI-Content-OS
Main Entry Point
Version: 1.0
"""

import json
from datetime import datetime
from pathlib import Path

from src.workflow_engine import WorkflowEngine


def banner():
    print("=" * 50)
    print("        AI-Content-OS")
    print("=" * 50)
    print(f"Started : {datetime.now()}")
    print()


def load_config():
    config_path = Path("config/settings.json")

    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)

    return config


def main():
    banner()

    config = load_config()

    engine = WorkflowEngine(config)
    engine.run()

    print()
    print("AI-Content-OS Ready.")


if __name__ == "__main__":
    main()