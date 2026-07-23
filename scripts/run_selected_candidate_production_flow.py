"""Prepare selected CardNews candidates from an explicit owner queue.

The CLI performs deep discovery only with ``--execute-network``. It prepares
source-bound plans and render inputs but does not render, publish, or approve a
production package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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

    def __init__(
        self,
        providers: Mapping[str, Any],
        operation_providers: Mapping[tuple[str, str], Any] | None = None,
    ) -> None:
        self.providers = {str(key).upper(): value for key, value in providers.items()}
        self.operation_providers = {
            (str(account).upper(), str(operation)): provider
            for (account, operation), provider in (operation_providers or {}).items()
        }

    def discover(self, account: str, operation: str, request: Mapping[str, Any]) -> Dict[str, Any]:
        normalized_account = str(account).upper()
        provider = self.operation_providers.get(
            (normalized_account, str(operation)),
            self.providers.get(normalized_account),
        )
        if provider is None or not callable(getattr(provider, "discover", None)):
            return {
                "status": "error",
                "error": "account provider unavailable",
                "network_used": False,
                "assets": [],
            }
        return provider.discover(account, operation, request)


class CachedAccountProviderRouter(AccountProviderRouter):
    def __init__(
        self,
        providers: Mapping[str, Any],
        operation_providers: Mapping[tuple[str, str], Any] | None = None,
        cache_root: Path | None = None,
    ) -> None:
        super().__init__(providers, operation_providers)
        self.cache_root = cache_root or Path(
            os.getenv(
                "AI_CONTENT_OS_DEEP_CACHE_ROOT",
                r"F:\AI-Content-OS-Data\cache\source_intake\deep_discovery",
            )
        )

    def _cache_path(
        self,
        account: str,
        operation: str,
        request: Mapping[str, Any],
    ) -> Path:
        body = json.dumps(
            {
                "account": str(account).upper(),
                "operation": str(operation),
                "candidate_id": str(request.get("candidate_id") or ""),
                "title": str(request.get("title") or ""),
                "source_urls": list(request.get("source_urls") or []),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        return self.cache_root / str(account).upper() / f"{digest}.json"

    def discover(self, account: str, operation: str, request: Mapping[str, Any]) -> Dict[str, Any]:
        result = super().discover(account, operation, request)
        cache_path = self._cache_path(account, operation, request)
        assets = result.get("assets") if isinstance(result, Mapping) else None
        if result.get("status") == "ok" and isinstance(assets, list) and assets:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = cache_path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary.replace(cache_path)
            return {**result, "cache_status": "refreshed", "fallback_used": False}
        if cache_path.is_file():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                return result
            if isinstance(cached, Mapping) and isinstance(cached.get("assets"), list):
                return {
                    **dict(cached),
                    "network_used": bool(result.get("network_used")),
                    "cache_status": "fallback_hit",
                    "fallback_used": True,
                    "fallback_reason": str(result.get("error_type") or result.get("status") or "empty"),
                }
        return {**result, "cache_status": "miss", "fallback_used": False}


def _default_network_router() -> AccountProviderRouter:
    from dotenv import load_dotenv

    from modules.source_intake.community_comment_capture_provider import (
        CommunityCommentCaptureProvider,
    )
    from modules.source_intake.naver_youtube_discovery_provider import (
        NaverYoutubeDiscoveryProvider,
    )
    from modules.source_intake.open_media_discovery_provider import (
        OpenMediaDiscoveryProvider,
    )
    from modules.source_intake.newspaper4k_deep_discovery_provider import (
        Newspaper4kDeepDiscoveryProvider,
    )

    load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
    article_provider = Newspaper4kDeepDiscoveryProvider()
    search_provider = NaverYoutubeDiscoveryProvider()
    open_media_provider = OpenMediaDiscoveryProvider()
    return CachedAccountProviderRouter(
        {
            "A": article_provider,
            "B": CommunityCommentCaptureProvider(),
            "C": NaverYoutubeDiscoveryProvider(),
        },
        operation_providers={
            ("C", "fetch_article_body"): article_provider,
            ("A", "search_related_news"): search_provider,
            ("A", "locate_embedded_or_broadcast_video"): search_provider,
            ("A", "search_open_images"): open_media_provider,
        },
    )


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
