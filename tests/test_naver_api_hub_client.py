import json
import socket
import unittest
from unittest import mock
from urllib.error import HTTPError, URLError

from modules.trend_collector.naver_api_hub_client import (
    API_HUB_NEWS_ENDPOINT,
    NaverApiHubClient,
)

FAKE_CLIENT_ID = "fixture-client-id-123"
FAKE_CLIENT_SECRET = "fixture-client-secret-456"

FIXTURE_PAYLOAD = {
    "lastBuildDate": "Tue, 14 Jul 2026 09:00:00 +0900",
    "total": 2,
    "start": 1,
    "display": 2,
    "items": [
        {
            "title": "AI <b>자동화</b> 뉴스 &quot;인용&quot;",
            "originallink": "https://example.com/original-a",
            "link": "https://n.news.naver.com/article/a",
            "description": "요약 <b>본문</b>   내용",
            "pubDate": "Tue, 14 Jul 2026 08:30:00 +0900",
        },
        {
            "title": "두 번째 기사",
            "originallink": "",
            "link": "https://n.news.naver.com/article/b",
            "description": "",
            "pubDate": "",
        },
    ],
}


class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _make_client(**kwargs) -> NaverApiHubClient:
    kwargs.setdefault("client_id", FAKE_CLIENT_ID)
    kwargs.setdefault("client_secret", FAKE_CLIENT_SECRET)
    return NaverApiHubClient(**kwargs)


def _json_response(payload) -> _FakeResponse:
    return _FakeResponse(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


class NaverApiHubClientNormalizationTest(unittest.TestCase):
    def test_success_normalizes_items(self):
        client = _make_client()

        with mock.patch("urllib.request.urlopen", return_value=_json_response(FIXTURE_PAYLOAD)):
            result = client.search_news("AI 자동화")

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["error_type"], "")
        self.assertTrue(result["credentials_present"])
        self.assertEqual(result["collection_method"], "naver_news_api_hub")

        first = result["items"][0]
        self.assertEqual(first["title"], 'AI 자동화 뉴스 "인용"')
        self.assertEqual(first["link"], "https://example.com/original-a")
        self.assertEqual(first["description"], "요약 본문 내용")
        self.assertEqual(first["pubDate"], "Tue, 14 Jul 2026 08:30:00 +0900")
        self.assertEqual(first["source"], "naver_api_hub")
        self.assertEqual(first["collection_method"], "naver_news_api_hub")

        second = result["items"][1]
        self.assertEqual(second["link"], "https://n.news.naver.com/article/b")

        # No fabricated metrics: only the normalized field set is emitted.
        expected_keys = {
            "title",
            "link",
            "description",
            "pubDate",
            "source",
            "collection_method",
        }
        self.assertEqual(set(first.keys()), expected_keys)
        self.assertEqual(set(second.keys()), expected_keys)

    def test_items_without_title_are_dropped(self):
        payload = {"items": [{"title": "<b></b>", "link": "https://example.com/x"}]}
        client = _make_client()

        with mock.patch("urllib.request.urlopen", return_value=_json_response(payload)):
            result = client.search_news("AI")

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "empty_result")

    def test_request_targets_api_hub_endpoint_with_expected_headers(self):
        client = _make_client()
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["request"] = request
            captured["timeout"] = timeout
            return _json_response(FIXTURE_PAYLOAD)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client.search_news("커피", display=2)

        request = captured["request"]
        self.assertTrue(request.full_url.startswith(API_HUB_NEWS_ENDPOINT))
        self.assertIn("query=", request.full_url)
        self.assertIn("format=json", request.full_url)
        self.assertEqual(
            request.get_header("X-ncp-apigw-api-key-id"),
            FAKE_CLIENT_ID,
        )
        self.assertEqual(
            request.get_header("X-ncp-apigw-api-key"),
            FAKE_CLIENT_SECRET,
        )


class NaverApiHubClientDiagnosticTest(unittest.TestCase):
    def _search_with_error(self, error):
        client = _make_client()

        with mock.patch("urllib.request.urlopen", side_effect=error):
            return client.search_news("AI")

    def test_missing_credentials_skips_request(self):
        client = NaverApiHubClient(client_id="", client_secret="")

        with mock.patch("urllib.request.urlopen") as urlopen_mock:
            result = client.search_news("AI")

        urlopen_mock.assert_not_called()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "missing_credentials")
        self.assertFalse(result["credentials_present"])
        self.assertEqual(result["items"], [])

    def test_http_401_is_diagnosed(self):
        result = self._search_with_error(
            HTTPError("url", 401, "Unauthorized", None, None)
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "http_401_unauthorized")

    def test_http_403_is_diagnosed(self):
        result = self._search_with_error(
            HTTPError("url", 403, "Forbidden", None, None)
        )
        self.assertEqual(result["error_type"], "http_403_forbidden")

    def test_http_429_is_diagnosed(self):
        result = self._search_with_error(
            HTTPError("url", 429, "Too Many Requests", None, None)
        )
        self.assertEqual(result["error_type"], "http_429_rate_limited")

    def test_timeout_is_diagnosed(self):
        result = self._search_with_error(URLError(socket.timeout("timed out")))
        self.assertEqual(result["error_type"], "timeout")

    def test_network_error_is_diagnosed(self):
        result = self._search_with_error(URLError(ConnectionRefusedError("refused")))
        self.assertEqual(result["error_type"], "network_error")

    def test_invalid_json_is_diagnosed(self):
        client = _make_client()

        with mock.patch(
            "urllib.request.urlopen",
            return_value=_FakeResponse(b"<html>gateway error</html>"),
        ):
            result = client.search_news("AI")

        self.assertEqual(result["error_type"], "invalid_json")

    def test_malformed_response_is_diagnosed(self):
        client = _make_client()

        with mock.patch(
            "urllib.request.urlopen",
            return_value=_json_response({"items": "not-a-list"}),
        ):
            result = client.search_news("AI")

        self.assertEqual(result["error_type"], "malformed_response")

    def test_empty_result_is_diagnosed(self):
        client = _make_client()

        with mock.patch(
            "urllib.request.urlopen",
            return_value=_json_response({"items": []}),
        ):
            result = client.search_news("AI")

        self.assertEqual(result["error_type"], "empty_result")

    def test_no_secret_ever_appears_in_results(self):
        for error in (
            HTTPError("url", 401, "Unauthorized", None, None),
            URLError(socket.timeout("timed out")),
        ):
            result = self._search_with_error(error)
            serialized = json.dumps(result, ensure_ascii=False)
            self.assertNotIn(FAKE_CLIENT_ID, serialized)
            self.assertNotIn(FAKE_CLIENT_SECRET, serialized)

        client = _make_client()

        with mock.patch("urllib.request.urlopen", return_value=_json_response(FIXTURE_PAYLOAD)):
            success = client.search_news("AI")

        serialized_success = json.dumps(success, ensure_ascii=False)
        self.assertNotIn(FAKE_CLIENT_ID, serialized_success)
        self.assertNotIn(FAKE_CLIENT_SECRET, serialized_success)


if __name__ == "__main__":
    unittest.main()
