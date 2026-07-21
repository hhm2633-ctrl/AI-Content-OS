import html
import json
import os
import re
import socket
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError

API_HUB_NEWS_ENDPOINT = "https://naverapihub.apigw.ntruss.com/search/v1/news"
CLIENT_ID_ENV = "NAVER_API_HUB_CLIENT_ID"
CLIENT_SECRET_ENV = "NAVER_API_HUB_CLIENT_SECRET"

_DOTENV_LOADED = False


def _load_dotenv_once() -> None:
    global _DOTENV_LOADED

    if _DOTENV_LOADED:
        return

    _DOTENV_LOADED = True

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass


class NaverApiHubClient:
    """Optional NAVER API HUB news search client.

    Credentials come from NAVER_API_HUB_CLIENT_ID / NAVER_API_HUB_CLIENT_SECRET
    and are used only to build request headers. They are never logged, printed,
    or copied into any status or diagnostic payload — every safe_message below
    is a fixed template keyed by error type, with no interpolated error text.

    search_news() never raises: any failure is returned as a diagnostic dict so
    the caller can fall through to the RSS/cache/settings fallback chain.
    """

    SAFE_MESSAGES = {
        "missing_credentials": (
            "NAVER API HUB credentials are missing or empty; API path skipped."
        ),
        "http_401_unauthorized": (
            "NAVER API HUB rejected the credentials (401); check the issued key pair."
        ),
        "http_403_forbidden": (
            "NAVER API HUB refused the request (403); check API subscription state."
        ),
        "http_429_rate_limited": (
            "NAVER API HUB rate limit reached (429); retry later."
        ),
        "http_error": "NAVER API HUB returned an HTTP error response.",
        "timeout": "NAVER API HUB request timed out.",
        "network_error": "NAVER API HUB request failed at the network layer.",
        "invalid_json": "NAVER API HUB response was not valid JSON.",
        "malformed_response": "NAVER API HUB response JSON had an unexpected shape.",
        "empty_result": "NAVER API HUB returned no news items for the query.",
        "unknown_error": "NAVER API HUB request failed for an unclassified reason.",
    }

    def __init__(
        self,
        timeout: int = 8,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        endpoint: str = API_HUB_NEWS_ENDPOINT,
    ):
        self.timeout = timeout
        self.endpoint = endpoint
        self._client_id = self._resolve_credential(client_id, CLIENT_ID_ENV)
        self._client_secret = self._resolve_credential(client_secret, CLIENT_SECRET_ENV)

    def _resolve_credential(self, explicit: Optional[str], env_name: str) -> str:
        if explicit is not None:
            return str(explicit).strip()

        _load_dotenv_once()
        return str(os.getenv(env_name, "") or "").strip()

    def is_configured(self) -> bool:
        return bool(self._client_id and self._client_secret)

    def search_news(
        self,
        query: str,
        display: int = 5,
        sort: str = "date",
    ) -> Dict[str, Any]:
        result = self._empty_result(query)

        if not self.is_configured():
            return self._fail(result, "missing_credentials")

        try:
            payload = self._request_news(query=query, display=display, sort=sort)
        except Exception as error:
            return self._fail(result, self._classify_error(error))

        try:
            parsed = json.loads(payload)
        except Exception:
            return self._fail(result, "invalid_json")

        if not isinstance(parsed, dict) or not isinstance(parsed.get("items"), list):
            return self._fail(result, "malformed_response")

        items = self._normalize_items(parsed["items"])

        if not items:
            return self._fail(result, "empty_result")

        result["status"] = "ok"
        result["items"] = items
        result["count"] = len(items)
        return result

    def _empty_result(self, query: str) -> Dict[str, Any]:
        return {
            "status": "failed",
            "query": query,
            "items": [],
            "count": 0,
            "error_type": "",
            "safe_message": "",
            "credentials_present": self.is_configured(),
            "collection_method": "naver_news_api_hub",
        }

    def _fail(self, result: Dict[str, Any], error_type: str) -> Dict[str, Any]:
        result["status"] = "failed"
        result["error_type"] = error_type
        result["safe_message"] = self.SAFE_MESSAGES.get(
            error_type,
            self.SAFE_MESSAGES["unknown_error"],
        )
        return result

    def _request_news(self, query: str, display: int, sort: str) -> str:
        params = urllib.parse.urlencode(
            {
                "query": query,
                "display": max(1, min(int(display), 100)),
                "start": 1,
                "sort": sort,
                "format": "json",
            }
        )
        request = urllib.request.Request(
            f"{self.endpoint}?{params}",
            headers={
                "X-NCP-APIGW-API-KEY-ID": self._client_id,
                "X-NCP-APIGW-API-KEY": self._client_secret,
                "Accept": "application/json",
            },
        )

        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return response.read().decode("utf-8", errors="ignore")

    def _normalize_items(self, raw_items: List[Any]) -> List[Dict[str, Any]]:
        items = []

        for raw in raw_items:
            if not isinstance(raw, dict):
                continue

            title = self._clean_text(raw.get("title", ""))

            if not title:
                continue

            link = str(raw.get("originallink") or raw.get("link") or "").strip()
            items.append(
                {
                    "title": title,
                    "link": link,
                    "description": self._clean_text(raw.get("description", "")),
                    "pubDate": str(raw.get("pubDate", "") or "").strip(),
                    "source": "naver_api_hub",
                    "collection_method": "naver_news_api_hub",
                }
            )

        return items

    def _clean_text(self, text: Any) -> str:
        if not text:
            return ""

        cleaned = re.sub(r"<.*?>", "", str(text))
        cleaned = html.unescape(cleaned)
        cleaned = cleaned.replace("\n", " ").replace("\t", " ")
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    def _classify_error(self, error: Exception) -> str:
        if isinstance(error, HTTPError):
            if error.code == 401:
                return "http_401_unauthorized"

            if error.code == 403:
                return "http_403_forbidden"

            if error.code == 429:
                return "http_429_rate_limited"

            return "http_error"

        if isinstance(error, (TimeoutError, socket.timeout)):
            return "timeout"

        if isinstance(error, URLError):
            reason = getattr(error, "reason", "")

            if isinstance(reason, (TimeoutError, socket.timeout)):
                return "timeout"

            reason_text = str(reason).lower()

            if "timed out" in reason_text or "timeout" in reason_text:
                return "timeout"

            return "network_error"

        return "unknown_error"
