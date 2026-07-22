"""Prepare selected CardNews candidates from an explicit owner queue.

The CLI performs deep discovery only with ``--execute-network``. It prepares
source-bound plans and render inputs but does not render, publish, or approve a
production package.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping

from modules.source_intake.owner_ranked_deep_dive_adapter import (
    adapt_owner_ranked_queue_to_selective_contract,
)
from modules.source_intake.selected_candidate_production_flow import (
    run_default_selected_candidate_production_flow,
)


class AccountProviderRouter:
    name = "account_deep_discovery_provider_router"

    def __init__(self, providers: Mapping[str, Any]) -> None:
        self.providers = {str(key).upper(): value for key, value in providers.items()}

    def discover(self, account: str, operation: str, request: Mapping[str, Any]) -> Dict[str, Any]:
        provider = self.providers.get(str(account).upper())
        if provider is None or not callable(getattr(provider, "discover", None)):
            return {
                "status": "error",
                "error": "account provider unavailable",
                "network_used": False,
                "assets": [],
            }
        return provider.discover(account, operation, request)


def _default_network_router() -> AccountProviderRouter:
    from modules.source_intake.community_comment_capture_provider import (
        CommunityCommentCaptureProvider,
    )
    from modules.source_intake.naver_youtube_discovery_provider import (
        NaverYoutubeDiscoveryProvider,
    )
    from modules.source_intake.newspaper4k_deep_discovery_provider import (
        Newspaper4kDeepDiscoveryProvider,
    )

    return AccountProviderRouter({
        "A": Newspaper4kDeepDiscoveryProvider(),
        "B": CommunityCommentCaptureProvider(),
        "C": NaverYoutubeDiscoveryProvider(),
    })


def run_owner_selected_flow(owner_queue: Any, provider: Any) -> Dict[str, Any]:
    selective_queue = adapt_owner_ranked_queue_to_selective_contract(owner_queue)
    if selective_queue.get("status") != "queue_ready":
        return {
            "status": "closed",
            "reason_code": selective_queue.get("reason_code", "owner_queue_not_ready"),
            "selective_queue": selective_queue,
            "production_flow": None,
            "render_executed": False,
            "publishing_executed": False,
        }
    production_flow = run_default_selected_candidate_production_flow(
        selective_queue,
        provider,
    )
    return {
        "status": production_flow.get("status", "closed"),
        "reason_code": production_flow.get("reason_code", "production_flow_closed"),
        "selective_queue": selective_queue,
        "production_flow": production_flow,
        "render_executed": False,
        "publishing_executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-queue", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute-network", action="store_true")
    args = parser.parse_args()

    if not args.execute_network:
        result = {
            "status": "closed",
            "reason_code": "explicit_execute_network_required",
            "selective_queue": None,
            "production_flow": None,
            "render_executed": False,
            "publishing_executed": False,
        }
    else:
        try:
            owner_queue = json.loads(args.owner_queue.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            result = {
                "status": "closed",
                "reason_code": f"owner_queue_read_failed:{type(exc).__name__}",
                "selective_queue": None,
                "production_flow": None,
                "render_executed": False,
                "publishing_executed": False,
            }
        else:
            result = run_owner_selected_flow(owner_queue, _default_network_router())

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "reason_code": result["reason_code"],
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"render_inputs_ready", "media_inputs_ready"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
