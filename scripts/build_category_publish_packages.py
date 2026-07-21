"""Build category-first manual publish packages from reviewed topic input.

Manual production helper. It reads an owner-reviewed JSON file (one topic
object, a list, or ``{"topics": [...]}``), separates every topic into its
canonical category bucket, builds a media pack from the supplied local paths
and remote URLs, and emits a manual-upload publish package beneath the configured
external artifact root at ``publish_packages/<date>/<category>/<topic_slug>/``. It performs no
search, no publishing, no Instagram/Meta API calls, and no WorkflowEngine
changes. Remote URLs are downloaded only with the explicit ``--download-remote``
opt-in and only from the supplied URLs.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.card_news.category_media_pack import (  # noqa: E402
    CategoryMediaPackBuilder,
    build_topic_slug,
    load_package_config,
    resolve_category,
)
from modules.publishing.category_publish_package import (  # noqa: E402
    CategoryPublishPackageBuilder,
)
from modules.common.external_storage import resolve_external_path  # noqa: E402

BLOCKED_BUCKET = "_blocked"
STORAGE_CONFIG = REPO_ROOT / "config" / "source_data_storage.json"


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Reviewed topic JSON file")
    parser.add_argument("--output-root", type=Path, default=None,
                        help="Package root (default: configured external artifact root)")
    parser.add_argument("--date", default=None, help="Package date folder (YYYY-MM-DD)")
    parser.add_argument("--config", type=Path, default=None,
                        help="Path to cardnews_category_packages.json")
    parser.add_argument("--download-remote", action="store_true",
                        help="Explicit opt-in: fetch only the supplied remote URLs "
                             "under timeout/size/type limits")
    return parser.parse_args(argv)


def load_topics(input_path: Path) -> List[Any]:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("topics"), list):
        return data["topics"]
    if isinstance(data, list):
        return data
    return [data]


def resolve_package_dir(output_root: Path, date_folder: str, bucket: str, slug: str) -> Path:
    package_dir = output_root / date_folder / bucket / slug
    suffix = 2
    while package_dir.exists() and any(package_dir.iterdir()):
        package_dir = output_root / date_folder / bucket / f"{slug}-{suffix}"
        suffix += 1
    return package_dir


def resolve_output_root(output_override: Optional[Path]) -> Path:
    """Keep explicit CLI paths exact; otherwise use configured heavy storage."""
    if output_override is not None:
        return output_override
    return resolve_external_path(
        "artifacts", "publish_packages", config_path=STORAGE_CONFIG
    )


def build_packages(argv: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    args = parse_args(argv)
    config, config_warnings = load_package_config(args.config)
    for warning in config_warnings:
        print(f"[config] {warning}")

    try:
        topics = load_topics(args.input)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"[error] reviewed input could not be read: {args.input} ({type(exc).__name__})")
        return []

    output_root = resolve_output_root(args.output_root)
    date_folder = args.date or datetime.now().strftime("%Y-%m-%d")
    local_media_root = args.input.resolve().parent

    media_builder = CategoryMediaPackBuilder(config=config)
    package_builder = CategoryPublishPackageBuilder(config=config)

    results: List[Dict[str, Any]] = []
    for topic in topics:
        category = resolve_category(topic, config)
        bucket = category["canonical_category"] or BLOCKED_BUCKET
        slug = build_topic_slug(topic)
        package_dir = resolve_package_dir(output_root, date_folder, bucket, slug)

        media_pack = media_builder.build(
            topic,
            package_dir,
            download_remote=args.download_remote,
            local_media_root=local_media_root,
        )
        manifest = package_builder.build(topic, media_pack, package_dir)
        results.append(manifest)

        reasons = "; ".join(manifest.get("blocking_reasons", [])) or "-"
        print(
            f"[{manifest['status']}] category={bucket} slug={slug} "
            f"slides={manifest.get('slide_count', 0)} dir={package_dir} reasons={reasons}"
        )

    ready = sum(1 for item in results if item.get("status") == "publish_package_ready")
    print(f"[summary] topics={len(results)} ready={ready} blocked={len(results) - ready} "
          f"(manual upload only; nothing was published)")
    return results


def main(argv: Optional[List[str]] = None) -> int:
    results = build_packages(argv)
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())
