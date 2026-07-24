"""Optional Newspaper4k provider for selected news article deep discovery.

The existing Naver/YouTube provider discovers candidate URLs.  This adapter
handles the next, selected-only step for article-backed Accounts A and C: parse an original article
once and expose its body, images, and embedded video references through the
``account_deep_discovery_runner`` provider contract.

``newspaper4k`` is deliberately an optional dependency.  Importing or creating
this provider performs no network work.  A URL is fetched only when ``discover``
is called, and results are cached per provider instance so the runner's three
Account-A operations do not download the same article three times.
"""

from __future__ import annotations

import re

import ipaddress
import urllib.parse
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Mapping, Optional


SUPPORTED_OPERATIONS = {
    "fetch_article_body",
    "collect_news_images",
    "locate_embedded_or_broadcast_video",
}

SAFE_ERRORS = {
    "unsupported_account": "newspaper4k deep discovery supports article-backed Accounts A and C only.",
    "unsupported_operation": "the requested operation is not supported by this provider.",
    "missing_source_url": "the selected item has no original source URL to parse.",
    "unsafe_source_url": "the source URL is not a permitted public HTTP(S) address.",
    "dependency_missing": "the optional newspaper4k dependency is not installed.",
    "parse_failed": "newspaper4k could not parse the selected article.",
}

ArticleFactory = Callable[[str, str], Any]


def _default_article_factory(url: str, language: str) -> Any:
    try:
        import newspaper  # provided by the ``newspaper4k`` PyPI package
    except ImportError as error:
        raise RuntimeError("dependency_missing") from error
    return newspaper.article(url, language=language)


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _serialized_date(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return _text(value)


def _public_http_url(value: Any) -> str:
    """Return a normalized public HTTP(S) URL or an empty string.

    Blocking localhost/private literal IPs prevents a candidate payload from
    turning this local parser into a trivial SSRF primitive.  Domain-name DNS
    rebinding is outside this small adapter and should be handled by the future
    network policy layer.
    """

    url = _text(value)
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return ""
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return url
    if not address.is_global:
        return ""
    return url


class Newspaper4kDeepDiscoveryProvider:
    """Selected-only article body/media discovery provider for Accounts A and C."""

    name = "newspaper4k_deep_discovery_provider"

    def __init__(
        self,
        article_factory: Optional[ArticleFactory] = None,
        language: str = "ko",
    ) -> None:
        self._article_factory = article_factory or _default_article_factory
        self.language = _text(language) or "ko"
        self._cache: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _error(error_type: str, network_used: bool = False) -> Dict[str, Any]:
        return {
            "status": "error",
            "error_type": error_type,
            "error": SAFE_ERRORS[error_type],
            "network_used": network_used,
            "assets": [],
        }

    def discover(self, account: str, operation: str, request: Mapping[str, Any]) -> Dict[str, Any]:
        if _text(account).upper() not in {"A", "C"}:
            return self._error("unsupported_account")
        operation = _text(operation)
        if operation not in SUPPORTED_OPERATIONS:
            return self._error("unsupported_operation")

        source_urls = request.get("source_urls") if isinstance(request, Mapping) else None
        raw_url = next(
            (item for item in source_urls if _text(item)),
            "",
        ) if isinstance(source_urls, list) else ""
        if not raw_url:
            return self._error("missing_source_url")
        url = _public_http_url(raw_url)
        if not url:
            return self._error("unsafe_source_url")

        parsed = self._parse_once(url)
        if parsed.get("status") == "error":
            return dict(parsed)

        if operation == "fetch_article_body":
            assets = self._body_assets(url, parsed)
        elif operation == "collect_news_images":
            assets = self._media_assets(url, parsed, media_type="news_image")
        else:
            assets = self._media_assets(url, parsed, media_type="embedded_video")
        return {
            "status": "ok",
            "network_used": True,
            "source_url": url,
            "assets": assets,
        }

    def _parse_once(self, url: str) -> Dict[str, Any]:
        if url in self._cache:
            return self._cache[url]
        try:
            article = self._article_factory(url, self.language)
        except RuntimeError as error:
            error_type = "dependency_missing" if _text(error) == "dependency_missing" else "parse_failed"
            parsed = self._error(error_type, network_used=error_type != "dependency_missing")
            self._cache[url] = parsed
            return parsed
        except Exception:
            parsed = self._error("parse_failed", network_used=True)
            self._cache[url] = parsed
            return parsed

        top_image = _public_http_url(getattr(article, "top_image", ""))
        images = self._unique_public_urls([top_image, *list(getattr(article, "images", []) or [])])
        movies = self._unique_public_urls(list(getattr(article, "movies", []) or []))
        parsed = {
            "status": "ok",
            "title": _text(getattr(article, "title", "")),
            "body": _text(getattr(article, "text", "")),
            "authors": [_text(value) for value in (getattr(article, "authors", []) or []) if _text(value)],
            "published_at": _serialized_date(getattr(article, "publish_date", "")),
            "canonical_url": _public_http_url(getattr(article, "canonical_link", "")) or url,
            "top_image": top_image,
            "images": images,
            "movies": movies,
        }
        self._cache[url] = parsed
        return parsed

    @staticmethod
    def _unique_public_urls(values: List[Any]) -> List[str]:
        result: List[str] = []
        seen = set()
        for value in values:
            raw = _text(value)
            if "," in raw or " " in raw:
                raw = raw.split(",", 1)[0].strip().split(" ", 1)[0]
            url = _public_http_url(raw)
            key = Newspaper4kDeepDiscoveryProvider._media_identity(url)
            if url and key not in seen:
                seen.add(key)
                result.append(url)
        return result

    @staticmethod
    def _media_identity(url: str) -> str:
        """Collapse publisher resize/proxy URLs that point to the same image."""

        if not url:
            return ""
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        proxied = _public_http_url(urllib.parse.unquote(_text((query.get("url") or [""])[0])))
        return proxied or url

    @staticmethod
    def _editorial_media_url(url: str, top_image: str) -> bool:
        if url == top_image:
            return True
        parsed = urllib.parse.urlparse(url)
        lowered = url.casefold()
        path = parsed.path.casefold()
        extension = path.rsplit(".", 1)[-1] if "." in path.rsplit("/", 1)[-1] else ""
        if extension in {"svg", "ico"}:
            return False
        excluded_markers = (
            "/logo",
            "logo_",
            "_logo",
            "/icon",
            "_icon",
            "icon-",
            "favicon",
            "google_g_logo",
            "/common/",
            "/assets/",
            "/menu",
            "sns_",
            "/sns/",
            "search_",
            "floating",
            "img.youtube.com/",
            "man_sample",
            "avatar",
            "profile",
            "banner",
            "/ad/",
            "advert",
        )
        if any(marker in lowered for marker in excluded_markers):
            return False
        if "/cdn-cgi/image/" in path and "." not in path.rsplit("/", 1)[-1]:
            return False
        top_date = re.search(r"/photos/\d{4}/\d{1,2}/\d{1,2}/", top_image)
        candidate_date = re.search(r"/photos/\d{4}/\d{1,2}/\d{1,2}/", url)
        if top_date and candidate_date and top_date.group(0) != candidate_date.group(0):
            return False
        return True

    @staticmethod
    def _body_assets(url: str, parsed: Mapping[str, Any]) -> List[Dict[str, Any]]:
        body = _text(parsed.get("body"))
        if not body:
            return []
        return [
            {
                "type": "article_body",
                "url": _text(parsed.get("canonical_url")) or url,
                "title": _text(parsed.get("title")),
                "body": body,
                "authors": list(parsed.get("authors") or []),
                "published_at": _text(parsed.get("published_at")),
                "source_provider": "newspaper4k",
                "reference_only": True,
                "usable_in_production": False,
                "restriction_reason": "source_text_reference_not_republication",
            }
        ]

    @staticmethod
    def _media_assets(
        source_url: str,
        parsed: Mapping[str, Any],
        media_type: str,
    ) -> List[Dict[str, Any]]:
        key = "images" if media_type == "news_image" else "movies"
        top_image = _text(parsed.get("top_image"))
        return [
            {
                "type": media_type,
                "url": url,
                "source_url": source_url,
                "source_provider": "newspaper4k",
                "is_top_image": media_type == "news_image" and url == top_image,
                "status": "source_editorial_candidate",
                "rights_status": "source_editorial_usable",
                "reference_only": False,
                "usable_in_production": True,
                "topic_relevant": True,
                "attribution_required": True,
                "attribution_source_url": source_url,
                "manual_visual_review_required": True,
                "publish_authorized": False,
                "usage_scope": "attributed_news_editorial_excerpt",
                "restriction_reason": "",
            }
            for url in list(parsed.get(key) or [])
            if Newspaper4kDeepDiscoveryProvider._editorial_media_url(url, top_image)
        ]


__all__ = ["Newspaper4kDeepDiscoveryProvider", "SUPPORTED_OPERATIONS"]
