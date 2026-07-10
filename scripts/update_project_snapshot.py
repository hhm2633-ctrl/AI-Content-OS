import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "PROJECT_SNAPSHOT.md"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
WORKFLOW_RESULT_PATH = ROOT / "storage" / "workflow_results" / "99_final_result.json"

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

# Runtime-output directories (see .gitignore) whose file-by-file listing would
# otherwise flood the project tree below. Only the directory itself is shown;
# individual files are summarized instead of enumerated.
TRUNCATED_RUNTIME_DIRS = {
    "storage/content",
    "storage/llm_logs",
    "storage/trends/snapshots",
    "storage/workflow_results",
    "storage/generated_images",
    "storage/card_news",
    "storage/images",
}

EXECUTION_COMMAND = "py -m src.main"


def load_json(path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not path.exists():
        return default or {}

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data
    except Exception:
        pass

    return default or {}


def iter_project_tree(max_depth: int = 3) -> Iterable[str]:
    def walk(directory: Path, prefix: str, depth: int) -> Iterable[str]:
        if depth > max_depth:
            return

        try:
            entries = sorted(
                directory.iterdir(),
                key=lambda item: (not item.is_dir(), item.name.lower()),
            )
        except Exception:
            return

        visible_entries = [
            entry for entry in entries
            if entry.name not in EXCLUDED_DIRS
        ]

        for index, entry in enumerate(visible_entries):
            connector = "`-- " if index == len(visible_entries) - 1 else "|-- "
            child_prefix = "    " if index == len(visible_entries) - 1 else "|   "
            label = f"{entry.name}/" if entry.is_dir() else entry.name
            yield f"{prefix}{connector}{label}"

            if entry.is_dir():
                relative_path = entry.relative_to(ROOT).as_posix()

                if relative_path in TRUNCATED_RUNTIME_DIRS:
                    try:
                        file_count = sum(1 for item in entry.rglob("*") if item.is_file())
                    except Exception:
                        file_count = 0

                    if file_count:
                        yield (
                            f"{prefix}{child_prefix}`-- "
                            f"({file_count} runtime file(s) omitted; gitignored, see .gitignore)"
                        )

                    continue

                yield from walk(entry, prefix + child_prefix, depth + 1)

    yield f"{ROOT.name}/"
    yield from walk(ROOT, "", 1)


def get_workflow_summary(workflow_result: Dict[str, Any]) -> Dict[str, Any]:
    # Keep this list in sync with WorkflowEngine.run()'s actual call sequence
    # (src/workflow_engine.py). It intentionally does not derive the list
    # dynamically to avoid depending on WorkflowEngine internals.
    modules = [
        "trend",
        "topic",
        "pattern",
        "research",
        "content",
        "image_strategy",
        "image_prompt",
        "image_generation",
        "card_news",
        "publishing",
        "knowledge",
        "performance_score",
        "audit",
        "learning",
        "analytics",
        "brand_dna",
        "trend_memory",
        "competitor",
    ]

    module_statuses = {}

    for module_name in modules:
        module_result = workflow_result.get(module_name, {})
        if isinstance(module_result, dict):
            module_statuses[module_name] = module_result.get("status", "unknown")
        else:
            module_statuses[module_name] = "unknown"

    return {
        "status": workflow_result.get("status", "unknown"),
        "modules": module_statuses,
    }


def collect_recent_completed_features(workflow_summary: Dict[str, Any]) -> List[str]:
    labels = {
        "trend": "Trend collection",
        "topic": "Topic selection",
        "pattern": "Pattern selection",
        "research": "Research",
        "content": "Content generation",
        "image_strategy": "Image strategy selection",
        "image_prompt": "Image prompt generation",
        "image_generation": "Image generation",
        "card_news": "Card news rendering",
        "publishing": "Publishing preparation",
        "knowledge": "Knowledge extraction",
        "performance_score": "Performance score",
        "audit": "Content audit",
        "learning": "Learning engine",
        "analytics": "Analytics prediction",
        "brand_dna": "Brand DNA update",
        "trend_memory": "Trend memory record",
        "competitor": "Competitor profile",
    }

    features = []

    for module_name, status in workflow_summary.get("modules", {}).items():
        if status and status != "unknown":
            features.append(f"{labels.get(module_name, module_name)}: {status}")

    if not features:
        features.append("No completed workflow module result found yet.")

    return features


def build_snapshot(workflow_result: Dict[str, Any]) -> str:
    updated_at = datetime.now().isoformat(timespec="seconds")
    workflow_summary = get_workflow_summary(workflow_result)
    recent_features = collect_recent_completed_features(workflow_summary)
    tree_lines = list(iter_project_tree())

    # Keep this string in sync with WorkflowEngine.run()'s actual call sequence
    # (src/workflow_engine.py) -- this is the exact bug Sprint 5 corrected:
    # PatternEngineModule was wired into the pipeline but this line still
    # skipped straight from TopicEngineModule to ResearchModule.
    module_lines = [
        "TrendCollectorModule -> TopicEngineModule -> PatternEngineModule -> "
        "ResearchModule -> ContentModule -> ImageStrategyModule -> "
        "ImagePromptModule -> ImageGenerationModule -> CardNewsModule -> "
        "PublishingModule -> KnowledgeModule -> PerformanceScoreModule -> "
        "AuditEngineModule -> LearningEngineModule -> AnalyticsEngineModule -> "
        "BrandDNAEngineModule -> TrendMemoryModule -> CompetitorEngineModule"
    ]

    snapshot_lines = [
        "# AI-Content-OS Project Snapshot",
        "",
        f"Updated at: {updated_at}",
        "",
        "## Execution Command",
        "",
        f"```powershell\n{EXECUTION_COMMAND}\n```",
        "",
        "Do not use `python -m src.main` for this project.",
        "",
        "## Workflow Result",
        "",
        f"- Final status: `{workflow_summary.get('status', 'unknown')}`",
        f"- Result file: `{WORKFLOW_RESULT_PATH.relative_to(ROOT).as_posix()}`",
        "",
        "## Recent Completed Features",
        "",
    ]

    snapshot_lines.extend(f"- {feature}" for feature in recent_features)
    snapshot_lines.extend([
        "",
        "## Current WorkflowEngine",
        "",
    ])
    snapshot_lines.extend(f"- {line}" for line in module_lines)
    snapshot_lines.extend([
        "",
        "## Current Project Tree",
        "",
        "```text",
    ])
    snapshot_lines.extend(tree_lines)
    snapshot_lines.extend([
        "```",
        "",
        "## Current Work",
        "",
        "- Project status document auto-update script maintained.",
        "- Sprint 5 snapshot generator correction completed: PatternEngineModule is included in the current WorkflowEngine line.",
        "- Runtime storage directories are collapsed in the project tree instead of listing every generated file.",
        "- Runtime storage outputs are gitignored and excluded from commit targets.",
        "- Keep fallback-first workflow behavior intact.",
        "",
        "## Protected Rules",
        "",
        "- Keep existing WorkflowEngine structure.",
        "- Use `py -m src.main` as the execution command.",
        "- Do not use `python -m src.main`.",
        "- Keep `workflow_completed` from regressing.",
        "- Keep fallback behavior for internet, LLM, and image failures.",
        "",
    ])

    return "\n".join(snapshot_lines)


def write_snapshot(workflow_result: Dict[str, Any]) -> None:
    SNAPSHOT_PATH.write_text(
        build_snapshot(workflow_result),
        encoding="utf-8",
    )


def append_changelog(
    workflow_result: Dict[str, Any],
    change_message: str,
    execution_result: Optional[str] = None,
) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    workflow_summary = get_workflow_summary(workflow_result)
    status = execution_result or workflow_summary.get("status", "unknown")

    entry_lines = [
        f"## {now}",
        "",
        f"- Change: {change_message}",
        f"- Execution command: `{EXECUTION_COMMAND}`",
        f"- Workflow result: `{status}`",
        "",
    ]

    existing = ""
    if CHANGELOG_PATH.exists():
        existing = CHANGELOG_PATH.read_text(encoding="utf-8")

    header = "# Changelog\n\n"
    if existing.strip():
        if existing.startswith("# Changelog"):
            content = existing
        else:
            content = header + existing.strip() + "\n"
    else:
        content = header

    CHANGELOG_PATH.write_text(
        content.rstrip() + "\n\n" + "\n".join(entry_lines),
        encoding="utf-8",
    )


def update_docs_after_workflow(
    workflow_result: Optional[Dict[str, Any]] = None,
    change_message: str = "Project snapshot auto-update support added.",
    update_changelog: bool = True,
) -> Dict[str, Any]:
    result = workflow_result or load_json(WORKFLOW_RESULT_PATH)

    write_snapshot(result)

    if update_changelog:
        append_changelog(
            workflow_result=result,
            change_message=change_message,
            execution_result=result.get("status", "unknown"),
        )

    return {
        "status": "project_docs_updated",
        "snapshot_path": str(SNAPSHOT_PATH.relative_to(ROOT)).replace("\\", "/"),
        "changelog_path": str(CHANGELOG_PATH.relative_to(ROOT)).replace("\\", "/"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update AI-Content-OS project snapshot and changelog."
    )
    parser.add_argument(
        "--message",
        default="Project snapshot updated.",
        help="Change message to append to CHANGELOG.md.",
    )
    parser.add_argument(
        "--no-changelog",
        action="store_true",
        help="Update PROJECT_SNAPSHOT.md only.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = update_docs_after_workflow(
        change_message=args.message,
        update_changelog=not args.no_changelog,
    )

    print("Project docs updated")
    print(f"Snapshot: {result['snapshot_path']}")
    print(f"Changelog: {result['changelog_path']}")


if __name__ == "__main__":
    main()
