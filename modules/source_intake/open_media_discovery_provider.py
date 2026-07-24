"""Read-only Google license-filtered image and Wikimedia Commons discovery."""

from __future__ import annotations

import html
import json
import os
import re
import socket
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional
from urllib.error import HTTPError, URLError


GOOGLE_CSE_ENDPOINT = "https://customsearch.googleapis.com/customsearch/v1"
COMMONS_API_ENDPOINT = "https://commons.wikimedia.org/w/api.php"
GOOGLE_RIGHTS_FILTER = "cc_publicdomain|cc_attribute|cc_sharealike"
COMMONS_MAX_QUERIES = 3
COMMONS_DOCUMENT_EXTENSIONS = {
    ".djvu",
    ".djv",
    ".pdf",
    ".svg",
}
COMMONS_DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "image/svg+xml",
    "image/vnd.djvu",
}
COMMONS_RASTER_MIME_TYPES = {
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
}
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


def _positive_int(value: Any) -> Optional[int]:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _iter_search_terms(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        for item in re.split(r"[,;\n|]+", value):
            if _text(item):
                yield _text(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            cleaned = _text(item)
            if cleaned:
                yield cleaned


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
        queries = self._expanded_queries(request)
        if not queries:
            return self._error("missing_query")
        query = queries[0]
        requested_source = _text(request.get("open_media_source")).casefold()
        google = (
            self._google(query)
            if requested_source in ("", "google_cse")
            else {"status": "not_requested", "network_used": False, "assets": []}
        )
        commons = (
            self._commons(queries)
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
            "queries": queries,
            "assets": assets,
            "diagnostics": {
                "google": google.get("error_type") or google.get("status"),
                "commons": commons.get("error_type") or commons.get("status"),
            },
        }

    @staticmethod
    def _expanded_queries(request: Mapping[str, Any]) -> List[str]:
        candidates: List[str] = []
        title = _text(request.get("title"))
        if title:
            candidates.append(title)
        candidates.extend(_iter_search_terms(request.get("search_terms")))
        candidates.extend(_iter_search_terms(request.get("search_query")))
        candidates.extend(_iter_search_terms(request.get("keywords")))
        category = _text(request.get("category"))
        if category and not title:
            candidates.append(category)
        queries: List[str] = []
        seen = set()
        for candidate in candidates:
            normalized = candidate.casefold()
            if title and category and normalized == category.casefold():
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            queries.append(candidate)
            if len(queries) >= COMMONS_MAX_QUERIES:
                break
        return queries

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

    @staticmethod
    def _commons_media_is_usable(page: Mapping[str, Any], info: Mapping[str, Any]) -> bool:
        title = _text(page.get("title"))
        extension = os.path.splitext(title.casefold())[1]
        mime = _text(info.get("mime")).casefold()
        media_type = _text(info.get("mediatype")).casefold()
        if extension in COMMONS_DOCUMENT_EXTENSIONS or mime in COMMONS_DOCUMENT_MIME_TYPES:
            return False
        if media_type and media_type != "bitmap":
            return False
        return mime in COMMONS_RASTER_MIME_TYPES

    @staticmethod
    def _commons_photo_priority(asset: Mapping[str, Any]) -> tuple:
        mime = _text(asset.get("mime_type")).casefold()
        return (
            0 if mime == "image/jpeg" else 1,
            -int(asset.get("pixel_area") or 0),
            _text(asset.get("title")).casefold(),
        )

    def _commons(self, queries: List[str]) -> Dict[str, Any]:
        assets: List[Dict[str, Any]] = []
        seen_urls = set()
        first_error = ""
        for query in queries[:COMMONS_MAX_QUERIES]:
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
                    "iiprop": "url|extmetadata|mime|mediatype|size",
                    "iiurlwidth": 1600,
                }
            )
            result = self._fetch(f"{COMMONS_API_ENDPOINT}?{params}")
            if "error_type" in result:
                first_error = first_error or result["error_type"]
                continue
            pages = result["parsed"].get("query", {}).get("pages", [])
            if isinstance(pages, Mapping):
                pages = list(pages.values())
            for page in pages if isinstance(pages, list) else []:
                if not isinstance(page, Mapping):
                    continue
                infos = page.get("imageinfo")
                info = (
                    infos[0]
                    if isinstance(infos, list) and infos and isinstance(infos[0], Mapping)
                    else {}
                )
                if not self._commons_media_is_usable(page, info):
                    continue
                metadata = (
                    info.get("extmetadata")
                    if isinstance(info.get("extmetadata"), Mapping)
                    else {}
                )
                remote_url = _text(info.get("thumburl") or info.get("url"))
                original_url = _text(info.get("url"))
                source_url = _text(info.get("descriptionurl"))
                license_name = _metadata_value(metadata.get("LicenseShortName"))
                attribution = _metadata_value(metadata.get("Artist")) or _metadata_value(
                    metadata.get("Credit")
                )
                if (
                    not remote_url
                    or remote_url in seen_urls
                    or not source_url
                    or not license_name
                ):
                    continue
                seen_urls.add(remote_url)
                lowered = license_name.casefold()
                rights_status = (
                    "public_domain"
                    if "public domain" in lowered or "cc0" in lowered
                    else "open_license"
                )
                width = _positive_int(info.get("width"))
                height = _positive_int(info.get("height"))
                assets.append(
                    {
                        "type": "open_image",
                        "url": remote_url,
                        "remote_url": remote_url,
                        "original_url": original_url,
                        "source_url": source_url,
                        "title": _text(page.get("title")),
                        "matched_query": query,
                        "source_provider": "wikimedia_commons",
                        "source_api": "wikimedia_commons",
                        "rights_status": rights_status,
                        "license": license_name,
                        "license_name": license_name,
                        "attribution": attribution,
                        "attribution_text": attribution,
                        "mime_type": _text(info.get("mime")),
                        "media_type": _text(info.get("mediatype")),
                        "width": width,
                        "height": height,
                        "pixel_area": (width * height) if width and height else None,
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
        assets.sort(key=self._commons_photo_priority)
        if not assets and first_error:
            return self._error(first_error, network_used=True)
        assets = assets[: self.max_results]
        return {"status": "ok", "network_used": True, "assets": assets}


__all__ = [
    "COMMONS_API_ENDPOINT",
    "COMMONS_MAX_QUERIES",
    "GOOGLE_CSE_ENDPOINT",
    "GOOGLE_RIGHTS_FILTER",
    "OpenMediaDiscoveryProvider",
]
