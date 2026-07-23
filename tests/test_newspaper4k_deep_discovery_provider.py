"""Offline contract tests for the optional Newspaper4k deep-discovery adapter."""

import unittest
from datetime import datetime, timezone

from modules.source_intake.account_deep_discovery_runner import run_account_deep_discovery
from modules.source_intake.newspaper4k_deep_discovery_provider import (
    Newspaper4kDeepDiscoveryProvider,
)


class FakeArticle:
    title = "폭염이 바꾼 여름 옷차림"
    text = "선택된 원문 기사 본문입니다."
    authors = ["기자 이름"]
    publish_date = datetime(2026, 7, 18, 8, 0, tzinfo=timezone.utc)
    canonical_link = "https://news.example.com/articles/heat"
    top_image = "https://cdn.example.com/top.jpg"
    images = {
        "https://cdn.example.com/top.jpg",
        "https://cdn.example.com/gallery.jpg",
        "file:///local/not-allowed.jpg",
    }
    movies = ["https://www.youtube.com/embed/abc123", "http://127.0.0.1/private"]


class RecordingFactory:
    def __init__(self, article=None, error=None):
        self.article = article or FakeArticle()
        self.error = error
        self.calls = []

    def __call__(self, url, language):
        self.calls.append((url, language))
        if self.error:
            raise self.error
        return self.article


REQUEST = {
    "candidate_id": "A-1",
    "title": "폭염 기사",
    "category": "사회",
    "source_urls": ["https://news.example.com/articles/heat"],
}


class Newspaper4kDeepDiscoveryProviderTest(unittest.TestCase):
    def test_three_runner_operations_parse_the_article_only_once(self):
        factory = RecordingFactory()
        provider = Newspaper4kDeepDiscoveryProvider(article_factory=factory)
        result = run_account_deep_discovery(
            {"accounts": {"A": {"selected": [REQUEST]}}},
            provider,
        )
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["network_executed"])
        self.assertEqual(len(factory.calls), 1)

        operations = {
            item["operation"]: item
            for item in result["accounts"]["A"]["results"][0]["operations"]
        }
        body = operations["fetch_article_body"]["assets"][0]
        self.assertEqual(body["body"], FakeArticle.text)
        self.assertTrue(body["reference_only"])
        self.assertFalse(body["usable_in_production"])

        images = operations["collect_news_images"]["assets"]
        self.assertEqual({item["url"] for item in images}, {
            "https://cdn.example.com/top.jpg",
            "https://cdn.example.com/gallery.jpg",
        })
        for image in images:
            self.assertEqual(image["rights_status"], "source_editorial_usable")
            self.assertTrue(image["topic_relevant"])
            self.assertTrue(image["attribution_required"])
            self.assertEqual(image["attribution_source_url"], REQUEST["source_urls"][0])
            self.assertFalse(image["publish_authorized"])
            self.assertFalse(image["reference_only"])
            self.assertTrue(image["usable_in_production"])

        videos = operations["locate_embedded_or_broadcast_video"]["assets"]
        self.assertEqual([item["url"] for item in videos], ["https://www.youtube.com/embed/abc123"])
        self.assertEqual(videos[0]["rights_status"], "source_editorial_usable")
        self.assertFalse(videos[0]["publish_authorized"])

    def test_ap_media_remains_reference_only_despite_editorial_candidate_fields(self):
        class APProvider:
            name = "ap_fixture"

            def discover(self, account, operation, request):
                return {
                    "status": "ok",
                    "network_used": False,
                    "assets": [{
                        "type": "news_image",
                        "url": "https://ap.example.com/photo.jpg",
                        "source_url": request["source_urls"][0],
                        "provider": "Associated Press",
                        "rights_status": "source_editorial_usable",
                        "topic_relevant": True,
                        "attribution_required": True,
                        "publish_authorized": False,
                        "reference_only": False,
                        "usable_in_production": True,
                    }],
                }

        result = run_account_deep_discovery(
            {"accounts": {"A": {"selected": [REQUEST]}}},
            APProvider(),
        )
        assets = [
            asset
            for operation in result["accounts"]["A"]["results"][0]["operations"]
            for asset in operation["assets"]
        ]

        self.assertTrue(assets)
        self.assertTrue(all(asset["reference_only"] for asset in assets))
        self.assertTrue(all(asset["rights_status"] == "reference_only" for asset in assets))
        self.assertTrue(all(asset["publish_authorized"] is False for asset in assets))
        self.assertTrue(all(asset["usable_in_production"] is False for asset in assets))
        self.assertTrue(all(asset["restriction_reason"] == "ap_reference_only" for asset in assets))

    def test_missing_and_unsafe_urls_do_not_call_parser(self):
        factory = RecordingFactory()
        provider = Newspaper4kDeepDiscoveryProvider(article_factory=factory)
        missing = provider.discover("A", "fetch_article_body", {"source_urls": []})
        unsafe = provider.discover(
            "A", "fetch_article_body", {"source_urls": ["http://127.0.0.1/private"]}
        )
        self.assertEqual(missing["error_type"], "missing_source_url")
        self.assertEqual(unsafe["error_type"], "unsafe_source_url")
        self.assertEqual(factory.calls, [])

    def test_other_accounts_and_operations_fail_closed(self):
        provider = Newspaper4kDeepDiscoveryProvider(article_factory=RecordingFactory())
        account = provider.discover("B", "capture_original_post", REQUEST)
        operation = provider.discover("A", "collect_real_comments", REQUEST)
        self.assertEqual(account["error_type"], "unsupported_account")
        self.assertEqual(operation["error_type"], "unsupported_operation")

    def test_account_c_can_parse_article_body_for_copy_evidence(self):
        factory = RecordingFactory()
        provider = Newspaper4kDeepDiscoveryProvider(article_factory=factory)
        result = provider.discover("C", "fetch_article_body", REQUEST)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["assets"][0]["body"], FakeArticle.text)
        self.assertTrue(result["assets"][0]["reference_only"])
        self.assertEqual(len(factory.calls), 1)

    def test_dependency_and_parse_failures_are_safe(self):
        dependency = Newspaper4kDeepDiscoveryProvider(
            article_factory=RecordingFactory(error=RuntimeError("dependency_missing"))
        ).discover("A", "fetch_article_body", REQUEST)
        parse = Newspaper4kDeepDiscoveryProvider(
            article_factory=RecordingFactory(error=ValueError("secret response details"))
        ).discover("A", "fetch_article_body", REQUEST)
        self.assertEqual(dependency["error_type"], "dependency_missing")
        self.assertFalse(dependency["network_used"])
        self.assertNotIn("secret response details", str(parse))
        self.assertEqual(parse["error_type"], "parse_failed")


if __name__ == "__main__":
    unittest.main()
