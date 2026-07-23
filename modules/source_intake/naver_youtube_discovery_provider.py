"""Read-only Naver News / YouTube Data API v3 discovery provider.

Implements the injected-provider contract of
``modules.source_intake.account_deep_discovery_runner``: metadata-only search,
no downloading, no generated evidence, no publishing. Network happens only when
``discover`` is explicitly executed with usable credentials, through an
injectable transport so tests stay offline.

Credentials come from environment variables and are used only to build request
headers/parameters. They are never logged or copied into any returned payload;
every error message below is a fixed template with no interpolated error text.
"""

from __future__ import annotations

import html
import json
import os
import re
import socket
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Mapping, Optional
from urllib.error import HTTPError, URLError

NAVER_NEWS_ENDPOINT = "https://naverapihub.apigw.ntruss.com/search/v1/news"
YOUTUBE_SEARCH_ENDPOINT = "https://www.googleapis.com/youtube/v3/search"

NAVER_CLIENT_ID_ENV = "NAVER_API_HUB_CLIENT_ID"
NAVER_CLIENT_SECRET_ENV = "NAVER_API_HUB_CLIENT_SECRET"
YOUTUBE_API_KEY_ENV = "YOUTUBE_API_KEY"

YOUTUBE_OPERATIONS = {
    "locate_embedded_or_broadcast_video",
    "collect_official_video",
    "collect_official_show_or_lookbook",
}
NAVER_OPERATIONS = {
    "fetch_article_body",
    "collect_news_images",
    "search_related_news",
    "capture_original_post",
    "extract_reconstruction_scene_facts",
    "collect_campaign_assets",
    "collect_official_product_assets",
}
# Real comments cannot be verified through these read-only search APIs, and the
# runner only accepts provider-verified is_real_comment=true items, so this
# provider refuses the operation instead of inventing or mislabeling comments.
UNSUPPORTED_OPERATIONS = {"collect_real_comments"}

SAFE_MESSAGES = {
    "missing_query": "discovery request had no usable title/category query.",
    "unsupported_operation": (
        "this provider cannot verify real comments read-only; operation refused."
    ),
    "missing_credentials": "NAVER API HUB credentials are missing; call skipped.",
    "missing_api_key": "YouTube API key is missing; call skipped.",
    "http_401_unauthorized": "the API rejected the credentials (401).",
    "http_403_forbidden": "the API refused the request (403).",
    "http_429_rate_limited": "the API rate limit was reached (429).",
    "http_error": "the API returned an HTTP error response.",
    "timeout": "the API request timed out.",
    "network_error": "the API request failed at the network layer.",
    "invalid_json": "the API response was not valid JSON.",
    "malformed_response": "the API response JSON had an unexpected shape.",
    "unknown_error": "the API request failed for an unclassified reason.",
}

Transport = Callable[[str, Mapping[str, str], float], str]


def _urllib_transport(url: str, headers: Mapping[str, str], timeout: float) -> str:
    request = urllib.request.Request(url, headers=dict(headers))
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def _clean_text(value: Any) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"<.*?>", "", str(value))
    cleaned = html.unescape(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _hostname(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).hostname or ""
    except ValueError:
        return ""


def _classify_error(error: Exception) -> str:
    if isinstance(error, HTTPError):
        return {
            401: "http_401_unauthorized",
            403: "http_403_forbidden",
            429: "http_429_rate_limited",
        }.get(error.code, "http_error")
    if isinstance(error, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(error, URLError):
        reason = getattr(error, "reason", "")
        if isinstance(reason, (TimeoutError, socket.timeout)) or "time" in str(reason).lower():
            return "timeout"
        return "network_error"
    return "unknown_error"


class NaverYoutubeDiscoveryProvider:
    """Injected-transport, metadata-only discovery provider for the runner."""

    name = "naver_youtube_discovery_provider"

    def __init__(
        self,
        transport: Optional[Transport] = None,
        naver_client_id: Optional[str] = None,
        naver_client_secret: Optional[str] = None,
        youtube_api_key: Optional[str] = None,
        timeout: float = 8.0,
        max_results: int = 5,
    ) -> None:
        self._transport = transport or _urllib_transport
        self.timeout = timeout
        self.max_results = max(1, min(int(max_results), 25))
        self._naver_client_id = self._credential(naver_client_id, NAVER_CLIENT_ID_ENV)
        self._naver_client_secret = self._credential(naver_client_secret, NAVER_CLIENT_SECRET_ENV)
        self._youtube_api_key = self._credential(youtube_api_key, YOUTUBE_API_KEY_ENV)

    @staticmethod
    def _credential(explicit: Optional[str], env_name: str) -> str:
        if explicit is not None:
            return str(explicit).strip()
        return str(os.getenv(env_name, "") or "").strip()

    @staticmethod
    def _error(error_type: str, network_used: bool) -> Dict[str, Any]:
        return {
            "status": "error",
            "error_type": error_type,
            "error": SAFE_MESSAGES.get(error_type, SAFE_MESSAGES["unknown_error"]),
            "network_used": network_used,
            "assets": [],
        }

    def discover(self, account: str, operation: str, request: Mapping[str, Any]) -> Dict[str, Any]:
        operation = str(operation or "")
        if operation in UNSUPPORTED_OPERATIONS:
            return self._error("unsupported_operation", network_used=False)

        title = _clean_text(request.get("title") if isinstance(request, Mapping) else "")
        category = _clean_text(request.get("category") if isinstance(request, Mapping) else "")
        query = title or category
        if not query:
            return self._error("missing_query", network_used=False)

        if operation in YOUTUBE_OPERATIONS:
            return self._discover_youtube(query)
        return self._discover_naver(query)

    def _fetch_json(self, url: str, headers: Mapping[str, str]) -> Dict[str, Any]:
        """Run one transport call; returns {'error_type': ...} or {'parsed': ...}."""
        try:
            body = self._transport(url, headers, self.timeout)
        except Exception as error:
            return {"error_type": _classify_error(error)}
        try:
            parsed = json.loads(body)
        except Exception:
            return {"error_type": "invalid_json"}
        if not isinstance(parsed, dict):
            return {"error_type": "malformed_response"}
        return {"parsed": parsed}

    def _discover_naver(self, query: str) -> Dict[str, Any]:
        if not (self._naver_client_id and self._naver_client_secret):
            return self._error("missing_credentials", network_used=False)

        params = urllib.parse.urlencode(
            {"query": query, "display": self.max_results, "start": 1, "sort": "date", "format": "json"}
        )
        outcome = self._fetch_json(
            f"{NAVER_NEWS_ENDPOINT}?{params}",
            {
                "X-NCP-APIGW-API-KEY-ID": self._naver_client_id,
                "X-NCP-APIGW-API-KEY": self._naver_client_secret,
                "Accept": "application/json",
            },
        )
        if "error_type" in outcome:
            return self._error(outcome["error_type"], network_used=True)

        items = outcome["parsed"].get("items")
        if not isinstance(items, list):
            return self._error("malformed_response", network_used=True)

        assets: List[Dict[str, Any]] = []
        for raw in items:
            if not isinstance(raw, Mapping):
                continue
            title = _clean_text(raw.get("title"))
            url = str(raw.get("originallink") or raw.get("link") or "").strip()
            if not title or not url:
                continue
            assets.append(
                {
                    "type": "news_article",
                    "url": url,
                    "title": title,
                    "description": _clean_text(raw.get("description")),
                    "published_at": str(raw.get("pubDate", "") or "").strip(),
                    "publisher": _hostname(url),
                    "source_api": "naver_news_search",
                    "metadata_only": True,
                    "downloaded": False,
                }
            )
        return {
            "status": "ok",
            "network_used": True,
            "endpoint": "naver_news_search",
            "query": query,
            "assets": assets,
        }

    def _discover_youtube(self, query: str) -> Dict[str, Any]:
        if not self._youtube_api_key:
            return self._error("missing_api_key", network_used=False)

        params = urllib.parse.urlencode(
            {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": self.max_results,
                "order": "relevance",
                "key": self._youtube_api_key,
            }
        )
        outcome = self._fetch_json(
            f"{YOUTUBE_SEARCH_ENDPOINT}?{params}", {"Accept": "application/json"}
        )
        if "error_type" in outcome:
            return self._error(outcome["error_type"], network_used=True)

        parsed = outcome["parsed"]
        if isinstance(parsed.get("error"), Mapping):
            return self._error("http_error", network_used=True)
        items = parsed.get("items")
        if not isinstance(items, list):
            return self._error("malformed_response", network_used=True)

        assets: List[Dict[str, Any]] = []
        for raw in items:
            if not isinstance(raw, Mapping):
                continue
            video_id = raw.get("id", {}).get("videoId") if isinstance(raw.get("id"), Mapping) else ""
            snippet = raw.get("snippet") if isinstance(raw.get("snippet"), Mapping) else {}
            title = _clean_text(snippet.get("title"))
            thumbnails = snippet.get("thumbnails") if isinstance(snippet.get("thumbnails"), Mapping) else {}
            thumbnail = ""
            for quality in ("maxres", "standard", "high", "medium", "default"):
                value = thumbnails.get(quality)
                if isinstance(value, Mapping) and str(value.get("url") or "").strip():
                    thumbnail = str(value["url"]).strip()
                    break
            if not video_id or not title:
                continue
            assets.append(
                {
                    "type": "youtube_video",
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "title": title,
                    "description": _clean_text(snippet.get("description")),
                    "published_at": str(snippet.get("publishedAt", "") or "").strip(),
                    "channel": _clean_text(snippet.get("channelTitle")),
                    "thumbnail_url": thumbnail,
                    "source_api": "youtube_data_api_v3",
                    "metadata_only": True,
                    "downloaded": False,
                    "rights_status": "source_editorial_usable",
                    "reference_only": False,
                    "usable_in_production": bool(thumbnail),
                    "topic_relevant": True,
                    "attribution_required": True,
                    "source_url": f"https://www.youtube.com/watch?v={video_id}",
                    "remote_url": thumbnail,
                    "manual_visual_review_required": True,
                    "publish_authorized": False,
                    "usage_scope": "attributed_youtube_thumbnail_editorial_candidate",
                }
            )
        return {
            "status": "ok",
            "network_used": True,
            "endpoint": "youtube_search",
            "query": query,
            "assets": assets,
        }


__all__ = [
    "NaverYoutubeDiscoveryProvider",
    "NAVER_NEWS_ENDPOINT",
    "YOUTUBE_SEARCH_ENDPOINT",
    "NAVER_OPERATIONS",
    "YOUTUBE_OPERATIONS",
    "UNSUPPORTED_OPERATIONS",
    "SAFE_MESSAGES",
]
