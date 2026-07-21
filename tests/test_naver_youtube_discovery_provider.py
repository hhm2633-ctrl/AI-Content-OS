"""Focused offline tests for the Naver/YouTube discovery provider."""

import json
import unittest
from urllib.error import HTTPError

from modules.source_intake.naver_youtube_discovery_provider import (
    NaverYoutubeDiscoveryProvider,
    SAFE_MESSAGES,
)

REQUEST = {"candidate_id": "A-1", "title": "폭염 경보 확산", "category": "사회"}
NAVER_SECRET = "naver-secret-value"
YOUTUBE_SECRET = "youtube-key-value"


class RecordingTransport:
    def __init__(self, body="{}", error=None):
        self.body = body
        self.error = error
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append({"url": url, "headers": dict(headers), "timeout": timeout})
        if self.error is not None:
            raise self.error
        return self.body


def provider_with(transport, naver=True, youtube=True):
    return NaverYoutubeDiscoveryProvider(
        transport=transport,
        naver_client_id="naver-id" if naver else "",
        naver_client_secret=NAVER_SECRET if naver else "",
        youtube_api_key=YOUTUBE_SECRET if youtube else "",
    )


class NaverYoutubeDiscoveryProviderTest(unittest.TestCase):
    def test_missing_naver_credentials_fail_without_network(self):
        transport = RecordingTransport()
        result = provider_with(transport, naver=False).discover("A", "fetch_article_body", REQUEST)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_type"], "missing_credentials")
        self.assertFalse(result["network_used"])
        self.assertEqual(result["assets"], [])
        self.assertEqual(transport.calls, [])

    def test_missing_youtube_key_fails_without_network(self):
        transport = RecordingTransport()
        result = provider_with(transport, youtube=False).discover(
            "A", "locate_embedded_or_broadcast_video", REQUEST
        )
        self.assertEqual(result["error_type"], "missing_api_key")
        self.assertFalse(result["network_used"])
        self.assertEqual(transport.calls, [])

    def test_naver_success_normalizes_real_source_refs(self):
        body = json.dumps(
            {
                "items": [
                    {
                        "title": "<b>폭염</b> 경보 확산",
                        "originallink": "https://news.example.co.kr/article/1",
                        "link": "https://n.naver.com/1",
                        "description": "전국 <b>폭염</b> 특보",
                        "pubDate": "Fri, 17 Jul 2026 09:00:00 +0900",
                    },
                    {"title": "", "link": "https://drop.me"},
                ]
            }
        )
        transport = RecordingTransport(body=body)
        result = provider_with(transport).discover("A", "collect_news_images", REQUEST)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["network_used"])
        self.assertEqual(len(result["assets"]), 1)
        asset = result["assets"][0]
        self.assertEqual(asset["url"], "https://news.example.co.kr/article/1")
        self.assertEqual(asset["title"], "폭염 경보 확산")
        self.assertEqual(asset["published_at"], "Fri, 17 Jul 2026 09:00:00 +0900")
        self.assertEqual(asset["publisher"], "news.example.co.kr")
        self.assertTrue(asset["metadata_only"])
        self.assertFalse(asset["downloaded"])

    def test_youtube_success_normalizes_video_metadata(self):
        body = json.dumps(
            {
                "items": [
                    {
                        "id": {"videoId": "abc123"},
                        "snippet": {
                            "title": "런웨이 공식 영상",
                            "description": "공식 채널",
                            "publishedAt": "2026-07-16T10:00:00Z",
                            "channelTitle": "Dior",
                        },
                    }
                ]
            }
        )
        transport = RecordingTransport(body=body)
        result = provider_with(transport).discover("C", "collect_official_video", REQUEST)
        self.assertEqual(result["status"], "ok")
        asset = result["assets"][0]
        self.assertEqual(asset["url"], "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(asset["channel"], "Dior")
        self.assertEqual(asset["published_at"], "2026-07-16T10:00:00Z")
        self.assertEqual(asset["source_api"], "youtube_data_api_v3")

    def test_http_error_becomes_structured_failure(self):
        error = HTTPError("https://x", 403, "Forbidden", None, None)
        result = provider_with(RecordingTransport(error=error)).discover(
            "A", "fetch_article_body", REQUEST
        )
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_type"], "http_403_forbidden")
        self.assertTrue(result["network_used"])
        self.assertEqual(result["assets"], [])

    def test_invalid_and_malformed_responses_fail_safely(self):
        invalid = provider_with(RecordingTransport(body="not-json")).discover(
            "A", "fetch_article_body", REQUEST
        )
        self.assertEqual(invalid["error_type"], "invalid_json")
        self.assertTrue(invalid["network_used"])

        malformed = provider_with(RecordingTransport(body=json.dumps({"items": "nope"}))).discover(
            "A", "fetch_article_body", REQUEST
        )
        self.assertEqual(malformed["error_type"], "malformed_response")

    def test_real_comments_operation_is_refused_not_fabricated(self):
        transport = RecordingTransport()
        result = provider_with(transport).discover("B", "collect_real_comments", REQUEST)
        self.assertEqual(result["error_type"], "unsupported_operation")
        self.assertFalse(result["network_used"])
        self.assertEqual(result["assets"], [])
        self.assertEqual(transport.calls, [])

    def test_missing_query_fails_without_network(self):
        transport = RecordingTransport()
        result = provider_with(transport).discover("A", "fetch_article_body", {"candidate_id": "A-9"})
        self.assertEqual(result["error_type"], "missing_query")
        self.assertFalse(result["network_used"])
        self.assertEqual(transport.calls, [])

    def test_secrets_never_leak_into_results(self):
        error = HTTPError("https://x", 401, "Unauthorized", None, None)
        for operation in ("fetch_article_body", "collect_official_video"):
            result = provider_with(RecordingTransport(error=error)).discover("A", operation, REQUEST)
            serialized = json.dumps(result, ensure_ascii=False)
            self.assertNotIn(NAVER_SECRET, serialized)
            self.assertNotIn(YOUTUBE_SECRET, serialized)
            self.assertIn(result["error_type"], SAFE_MESSAGES)

    def test_no_network_unless_discover_is_executed(self):
        transport = RecordingTransport()
        provider_with(transport)
        self.assertEqual(transport.calls, [])

    def test_runner_integration_reports_honest_network_flag(self):
        from modules.source_intake.account_deep_discovery_runner import run_account_deep_discovery

        body = json.dumps({"items": [{"title": "기사", "link": "https://news.example.com/1"}]})
        provider = provider_with(RecordingTransport(body=body), youtube=False)
        selection = {"accounts": {"A": {"selected": [dict(REQUEST)]}}}
        result = run_account_deep_discovery(selection, provider)
        self.assertTrue(result["network_executed"])
        operations = {
            op["operation"]: op for op in result["accounts"]["A"]["results"][0]["operations"]
        }
        self.assertEqual(operations["fetch_article_body"]["status"], "ok")
        self.assertEqual(
            operations["locate_embedded_or_broadcast_video"]["status"], "provider_failed"
        )


if __name__ == "__main__":
    unittest.main()
