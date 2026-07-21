"""CLI for building the Source Health / Collector Statistics dashboard."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Iterable, Optional

from modules.source_intake.source_health_dashboard import (
    DASHBOARD_STATUS_BLOCKED,
    DASHBOARD_STATUS_READY,
    DASHBOARD_STATUS_PARTIAL,
    build_source_health_dashboard,
    write_source_health_dashboard,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a deterministic source health dashboard from explicit artifact inputs.",
    )
    parser.add_argument(
        "--status-bundle",
        required=True,
        type=str,
        help="Path to source_intake_status_bundle.json",
    )
    parser.add_argument(
        "--gap-report",
        required=True,
        type=str,
        help="Path to collection_gap_report.json",
    )
    parser.add_argument(
        "--lane-summary",
        required=True,
        type=str,
        help="Path to lane_collection_summary.json",
    )
    parser.add_argument(
        "--source-health",
        type=str,
        default=None,
        help="Optional path to storage/trends/source_health.json",
    )
    parser.add_argument(
        "--collector-statistics",
        type=str,
        default=None,
        help="Optional path to storage/trends/collector_statistics.json",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=str,
        help="Output JSON path for the generated dashboard",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON output from the main result.",
    )
    return parser


def build_dashboard_result(
    status_bundle: str,
    gap_report: str,
    lane_summary: str,
    output: str,
    source_health: Optional[str],
    collector_statistics: Optional[str],
) -> dict[str, Any]:
    dashboard = build_source_health_dashboard(
        status_bundle_path=status_bundle,
        gap_report_path=gap_report,
        lane_summary_path=lane_summary,
        source_health_path=source_health,
        collector_statistics_path=collector_statistics,
    )
    write_result = write_source_health_dashboard(dashboard=dashboard, output_path=output)

    return {
        "status": write_result["status"],
        "output_path": output,
        "dashboard_status": dashboard.get("dashboard_status"),
        "dashboard": write_result["dashboard"],
    }


def run(argv: Optional[Iterable[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_dashboard_result(
        status_bundle=args.status_bundle,
        gap_report=args.gap_report,
        lane_summary=args.lane_summary,
        output=args.output,
        source_health=args.source_health,
        collector_statistics=args.collector_statistics,
    )

    indent = None if args.compact else 2
    print(json.dumps(result, ensure_ascii=False, indent=indent))

    if result["status"] == "write_failed":
        return 1
    if result["dashboard_status"] == DASHBOARD_STATUS_BLOCKED:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(run())

