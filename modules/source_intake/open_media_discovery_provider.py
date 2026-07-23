"""Read-only Google license-filtered image and Wikimedia Commons discovery."""

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


GOOGLE_CSE_ENDPOINT = "https://customsearch.googleapis.com/customsearch/v1"
COMMONS_API_ENDPOINT = "https://commons.wikimedia.org/w/api.php"
GOOGLE_RIGHTS_FILTER = "cc_publicdomain|cc_attribute|cc_sharealike"
Transport = Callable[[str, Mapping[str, str], float], str]


def _transport(url: str, headers: Mapping[str, str], timeout: float) -> str:
    request = urllib.request.Request(url, headers=dict(headers))
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def _text(value: Any) -> str:
    cleaned = html.unescape(re.sub(r"<.*?>", "", str(value or "")))
    return re.sub(r"\s+", " ", cleaned).strip()


def _metadata_value(value: Any) -> str:
    return _text(value.get("value")) if isinstance(value, Mapping) else ""


class OpenMediaDiscoveryProvider:
    name = "open_media_discovery_provider"

    def __init__(
        self,
        transport: Optional[Transport] = None,
        google_api_key: Optional[str] = None,
        google_cx: Optional[str] = None,
        google_cse_id: Optional[str] = None,
        timeout: float = 10.0,
        max_results: int = 5,
    ) -> None:
        self._transport = transport or _transport
        self.google_api_key = _text(
            google_api_key if google_api_key is not None else os.getenv("GOOGLE_CSE_API_KEY")
        )
        configured_cx = google_cx if google_cx is not None else google_cse_id
        self.google_cx = _text(
            configured_cx if configured_cx is not None else os.getenv("GOOGLE_CSE_CX")
        )
        self.timeout = timeout
        self.max_results = max(1, min(int(max_results), 10))

    @staticmethod
    def _error(reason: str, *, network_used: bool = False) -> Dict[str, Any]:
        return {
            "status": "error",
            "error_type": reason,
            "network_used": network_used,
            "assets": [],
        }

    def _fetch(self, url: str) -> Dict[str, Any]:
        try:
            body = self._transport(
                url,
                {"Accept": "application/json", "User-Agent": "AI-Content-OS/1.0"},
                self.timeout,
            )
            parsed = json.loads(body)
        except (HTTPError, URLError, TimeoutError, socket.timeout):
            return {"error_type": "network_error"}
        except (ValueError, TypeError, json.JSONDecodeError):
            return {"error_type": "invalid_json"}
        return {"parsed": parsed} if isinstance(parsed, Mapping) else {"error_type": "malformed_response"}

    def discover(
        self,
        account: str,
        operation: str,
        request: Mapping[str, Any],
    ) -> Dict[str, Any]:
        if operation != "search_open_images":
            return self._error("unsupported_operation")
        query = _text(request.get("title") or request.get("category"))
        if not query:
            return self._error("missing_query")
        requested_source = _text(request.get("open_media_source")).casefold()
        google = (
            self._google(query)
            if requested_source in ("", "google_cse")
            else {"status": "not_requested", "network_used": False, "assets": []}
        )
        commons = (
            self._commons(query)
            if requested_source in ("", "wikimedia_commons")
            else {"status": "not_requested", "network_used": False, "assets": []}
        )
        assets = [
            *google.get("assets", []),
            *commons.get("assets", []),
        ]
        return {
            "status": "ok" if assets else "empty",
            "network_used": bool(google.get("network_used") or commons.get("network_used")),
            "query": query,
            "assets": assets,
            "diagnostics": {
                "google": google.get("error_type") or google.get("status"),
                "commons": commons.get("error_type") or commons.get("status"),
            },
        }

    def _google(self, query: str) -> Dict[str, Any]:
        if not self.google_api_key or not self.google_cx:
            return self._error("google_credentials_missing")
        params = urllib.parse.urlencode(
            {
                "key": self.google_api_key,
                "cx": self.google_cx,
                "q": query,
                "searchType": "image",
                "rights": GOOGLE_RIGHTS_FILTER,
                "safe": "active",
                "num": self.max_results,
            }
        )
        result = self._fetch(f"{GOOGLE_CSE_ENDPOINT}?{params}")
        if "error_type" in result:
            return self._error(result["error_type"], network_used=True)
        assets: List[Dict[str, Any]] = []
        for raw in result["parsed"].get("items", []):
            if not isinstance(raw, Mapping):
                continue
            image = raw.get("image") if isinstance(raw.get("image"), Mapping) else {}
            remote_url = _text(raw.get("link"))
            source_url = _text(image.get("contextLink"))
            if not remote_url or not source_url:
                continue
            assets.append(
                {
                    "type": "open_image",
                    "url": remote_url,
                    "remote_url": remote_url,
                    "source_url": source_url,
                    "title": _text(raw.get("title")),
                    "source_provider": "google_cse",
                    "source_api": "google_custom_search",
                    "rights_status": "source_editorial_usable",
                    "license_filter": GOOGLE_RIGHTS_FILTER,
                    "metadata_only": False,
                    "downloaded": False,
                    "reference_only": False,
                    "usable_in_production": True,
                    "topic_relevant": True,
                    "attribution_required": True,
                    "manual_visual_review_required": True,
                    "publish_authorized": False,
                    "usage_scope": "google_license_filtered_editorial_candidate",
                }
            )
        return {"status": "ok", "network_used": True, "assets": assets}

    def _commons(self, query: str) -> Dict[str, Any]:
        params = urllib.parse.urlencode(
            {
                "action": "query",
                "format": "json",
                "formatversion": 2,
                "generator": "search",
                "gsrsearch": f"file:{query}",
                "gsrnamespace": 6,
                "gsrlimit": self.max_results,
                "prop": "imageinfo",
                "iiprop": "url|extmetadata",
                "iiurlwidth": 1600,
            }
        )
        result = self._fetch(f"{COMMONS_API_ENDPOINT}?{params}")
        if "error_type" in result:
            return self._error(result["error_type"], network_used=True)
        pages = result["parsed"].get("query", {}).get("pages", [])
        if isinstance(pages, Mapping):
            pages = list(pages.values())
        assets: List[Dict[str, Any]] = []
        for page in pages if isinstance(pages, list) else []:
            if not isinstance(page, Mapping):
                continue
            infos = page.get("imageinfo")
            info = infos[0] if isinstance(infos, list) and infos and isinstance(infos[0], Mapping) else {}
            metadata = info.get("extmetadata") if isinstance(info.get("extmetadata"), Mapping) else {}
            remote_url = _text(info.get("thumburl") or info.get("url"))
            source_url = _text(info.get("descriptionurl"))
            license_name = _metadata_value(metadata.get("LicenseShortName"))
            attribution = _metadata_value(metadata.get("Artist")) or _metadata_value(metadata.get("Credit"))
            if not remote_url or not source_url or not license_name:
                continue
            lowered = license_name.casefold()
            rights_status = "public_domain" if (
                "public domain" in lowered or "cc0" in lowered
            ) else "open_license"
            assets.append(
                {
                    "type": "open_image",
                    "url": remote_url,
                    "remote_url": remote_url,
                    "source_url": source_url,
                    "title": _text(page.get("title")),
                    "source_provider": "wikimedia_commons",
                    "source_api": "wikimedia_commons",
                    "rights_status": rights_status,
                    "license": license_name,
                    "license_name": license_name,
                    "attribution": attribution,
                    "attribution_text": attribution,
                    "metadata_only": False,
                    "downloaded": False,
                    "reference_only": False,
                    "usable_in_production": True,
                    "topic_relevant": True,
                    "attribution_required": True,
                    "manual_visual_review_required": True,
                    "publish_authorized": False,
                    "usage_scope": "open_license_editorial_candidate",
                }
            )
        return {"status": "ok", "network_used": True, "assets": assets}


__all__ = [
    "COMMONS_API_ENDPOINT",
    "GOOGLE_CSE_ENDPOINT",
    "GOOGLE_RIGHTS_FILTER",
    "OpenMediaDiscoveryProvider",
]
