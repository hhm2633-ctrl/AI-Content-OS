"""Read-only media discovery bridge for the default CardNews workflow."""

from __future__ import annotations

import copy
import urllib.parse
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from modules.source_intake.naver_youtube_discovery_provider import (
    NaverYoutubeDiscoveryProvider,
)
from modules.source_intake.open_media_discovery_provider import (
    OpenMediaDiscoveryProvider,
)
from modules.source_intake.reaction_media_discovery_provider import (
    ReactionMediaDiscoveryProvider,
)


SCHEMA_VERSION = "workflow_media_discovery_bridge_v1"
_TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}
_RENDERABLE_RIGHTS = {
    "open_license",
    "owner_approved",
    "public_domain",
    "source_editorial_usable",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _canonical_url(value: Any) -> str:
    raw = _text(value)
    if not raw:
        return ""
    try:
        parsed = urllib.parse.urlsplit(raw)
    except ValueError:
        return raw.casefold()
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    filtered = [
        (key, item)
        for key, item in query
        if key.casefold() not in _TRACKING_QUERY_KEYS
    ]
    return urllib.parse.urlunsplit(
        (
            parsed.scheme.casefold(),
            parsed.netloc.casefold(),
            parsed.path.rstrip("/"),
            urllib.parse.urlencode(filtered),
            "",
        )
    )


def _asset_identity(asset: Mapping[str, Any]) -> str:
    for key in ("remote_url", "thumbnail_url", "url", "source_url"):
        canonical = _canonical_url(asset.get(key))
        if canonical:
            return canonical
    return ""


def _has_visual_asset(asset: Mapping[str, Any]) -> bool:
    return bool(
        _text(
            asset.get("local_path")
            or asset.get("remote_url")
            or asset.get("thumbnail_url")
        )
    ) and (
        asset.get("metadata_only") is not True or bool(_text(asset.get("thumbnail_url")))
    )


def _render_allowed(asset: Mapping[str, Any]) -> bool:
    if asset.get("render_allowed") is False:
        return False
    if asset.get("topic_relevant") is False:
        return False
    if asset.get("usable_in_production") is not True:
        return False
    if _text(asset.get("rights_status")).casefold() not in _RENDERABLE_RIGHTS:
        return False
    return _has_visual_asset(asset)


def _normalize_asset(
    raw: Mapping[str, Any],
    *,
    provider_name: str,
    operation: str,
) -> Dict[str, Any]:
    asset = copy.deepcopy(dict(raw))
    asset.setdefault("source_provider", provider_name)
    asset["discovery_operation"] = operation
    if "topic_relevant" in raw:
        asset["topic_relevant"] = raw.get("topic_relevant")
    else:
        asset["topic_relevant"] = None
    asset["render_allowed"] = _render_allowed(asset)
    if not _text(asset.get("rights_status")):
        asset["rights_status"] = "unverified"
    return asset


def _provider_call(
    provider: Any,
    *,
    provider_name: str,
    account: str,
    operation: str,
    request: Mapping[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    try:
        result = provider.discover(account, operation, request)
    except Exception as error:
        return [], {
            "provider": provider_name,
            "operation": operation,
            "status": "fallback",
            "reason_code": "provider_exception",
            "reason": str(error),
            "network_used": False,
            "asset_count": 0,
        }
    if not isinstance(result, Mapping):
        return [], {
            "provider": provider_name,
            "operation": operation,
            "status": "fallback",
            "reason_code": "malformed_provider_result",
            "reason": "provider result was not a mapping",
            "network_used": False,
            "asset_count": 0,
        }
    raw_assets = result.get("assets")
    assets = [
        _normalize_asset(
            item,
            provider_name=provider_name,
            operation=operation,
        )
        for item in raw_assets if isinstance(item, Mapping)
    ] if isinstance(raw_assets, list) else []
    provider_status = _text(result.get("status")) or "unknown"
    failed = provider_status == "error"
    return assets, {
        "provider": provider_name,
        "operation": operation,
        "status": "fallback" if failed else provider_status,
        "reason_code": _text(result.get("error_type")) if failed else "",
        "reason": _text(result.get("error")) if failed else "",
        "network_used": bool(result.get("network_used")),
        "asset_count": len(assets),
    }


def _deduplicate(assets: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    unique: List[Dict[str, Any]] = []
    seen = set()
    for raw in assets:
        identity = _asset_identity(raw)
        if identity and identity in seen:
            continue
        if identity:
            seen.add(identity)
        unique.append(copy.deepcopy(dict(raw)))
    return unique


class WorkflowMediaDiscoveryBridge:
    """Reuse existing providers behind one fallback-first workflow API."""

    def __init__(
        self,
        *,
        naver_youtube_provider: Optional[Any] = None,
        open_media_provider: Optional[Any] = None,
        reaction_media_provider: Optional[Any] = None,
    ) -> None:
        self.naver_youtube_provider = (
            naver_youtube_provider
            if naver_youtube_provider is not None
            else NaverYoutubeDiscoveryProvider()
        )
        self.open_media_provider = (
            open_media_provider
            if open_media_provider is not None
            else OpenMediaDiscoveryProvider()
        )
        self.reaction_media_provider = (
            reaction_media_provider
            if reaction_media_provider is not None
            else ReactionMediaDiscoveryProvider()
        )

    def discover(
        self,
        request: Mapping[str, Any],
        *,
        account: str = "",
    ) -> Dict[str, Any]:
        safe_request = copy.deepcopy(dict(request)) if isinstance(request, Mapping) else {}
        calls = (
            (
                self.naver_youtube_provider,
                "naver_youtube_discovery_provider",
                "search_related_news",
            ),
            (
                self.naver_youtube_provider,
                "naver_youtube_discovery_provider",
                "collect_official_video",
            ),
            (
                self.open_media_provider,
                "open_media_discovery_provider",
                "search_open_images",
            ),
            (
                self.reaction_media_provider,
                "reaction_media_discovery_provider",
                "search_reaction_media",
            ),
        )
        gathered: List[Dict[str, Any]] = []
        diagnostics: List[Dict[str, Any]] = []
        for provider, provider_name, operation in calls:
            assets, diagnostic = _provider_call(
                provider,
                provider_name=provider_name,
                account=_text(account),
                operation=operation,
                request=safe_request,
            )
            gathered.extend(assets)
            diagnostics.append(diagnostic)

        assets = _deduplicate(gathered)
        render_assets = [
            copy.deepcopy(asset)
            for asset in assets
            if asset.get("render_allowed") is True
        ]
        fallback_count = sum(
            1 for diagnostic in diagnostics if diagnostic.get("status") == "fallback"
        )
        if fallback_count == len(diagnostics):
            status = "fallback"
        elif fallback_count:
            status = "partial"
        else:
            status = "completed"
        return {
            "schema_version": SCHEMA_VERSION,
            "status": status,
            "fallback_used": fallback_count > 0,
            "reason_code": (
                "all_media_providers_failed"
                if status == "fallback"
                else "some_media_providers_failed"
                if status == "partial"
                else ""
            ),
            "network_executed": any(
                diagnostic.get("network_used") is True for diagnostic in diagnostics
            ),
            "query": _text(safe_request.get("title") or safe_request.get("category")),
            "assets": assets,
            "render_assets": render_assets,
            "asset_count": len(assets),
            "render_asset_count": len(render_assets),
            "diagnostics": diagnostics,
        }


def run_workflow_media_discovery(
    request: Mapping[str, Any],
    *,
    account: str = "",
    naver_youtube_provider: Optional[Any] = None,
    open_media_provider: Optional[Any] = None,
    reaction_media_provider: Optional[Any] = None,
) -> Dict[str, Any]:
    """Single function entry point intended for the default workflow."""

    return WorkflowMediaDiscoveryBridge(
        naver_youtube_provider=naver_youtube_provider,
        open_media_provider=open_media_provider,
        reaction_media_provider=reaction_media_provider,
    ).discover(request, account=account)


__all__ = [
    "SCHEMA_VERSION",
    "WorkflowMediaDiscoveryBridge",
    "run_workflow_media_discovery",
]
