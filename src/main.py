"""
AI-Content-OS
Main Entry Point
Version: 1.0
"""

from datetime import datetime
from src.workflow_engine import WorkflowEngine


def banner():
    print("=" * 50)
    print("        AI-Content-OS")
    print("=" * 50)
    print(f"Started : {datetime.now()}")
    print()


def main():
    banner()

    engine = WorkflowEngine()
    engine.start()
    engine.run()
    engine.stop()

    print()
    print("AI-Content-OS Ready.")


if __name__ == "__main__":
    main()