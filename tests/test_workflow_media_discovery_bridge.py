import unittest

from modules.source_intake.workflow_media_discovery_bridge import (
    WorkflowMediaDiscoveryBridge,
    run_workflow_media_discovery,
)


class FakeProvider:
    def __init__(self, results=None, error=None):
        self.results = results or {}
        self.error = error
        self.calls = []

    def discover(self, account, operation, request):
        self.calls.append((account, operation, dict(request)))
        if self.error:
            raise self.error
        return self.results.get(
            operation,
            {"status": "empty", "network_used": False, "assets": []},
        )


def result(*assets, status="ok", network_used=True):
    return {
        "status": status,
        "network_used": network_used,
        "assets": list(assets),
    }


class WorkflowMediaDiscoveryBridgeTests(unittest.TestCase):
    def test_combines_providers_deduplicates_urls_and_preserves_relevance(self):
        duplicate = "https://img.example/a.jpg?utm_source=x"
        naver_youtube = FakeProvider(
            {
                "search_related_news": result(
                    {
                        "type": "news_article",
                        "url": "https://news.example/story",
                        "metadata_only": True,
                    }
                ),
                "collect_official_video": result(
                    {
                        "type": "video",
                        "url": "https://youtube.com/watch?v=1",
                        "remote_url": duplicate,
                        "thumbnail_url": duplicate,
                        "metadata_only": True,
                        "usable_in_production": True,
                        "rights_status": "source_editorial_usable",
                        "topic_relevant": True,
                    }
                ),
            }
        )
        open_media = FakeProvider(
            {
                "search_open_images": result(
                    {
                        "type": "open_image",
                        "url": "https://img.example/a.jpg",
                        "remote_url": "https://img.example/a.jpg",
                        "usable_in_production": True,
                        "rights_status": "open_license",
                        "topic_relevant": False,
                    },
                    {
                        "type": "open_image",
                        "url": "https://img.example/b.jpg",
                        "remote_url": "https://img.example/b.jpg",
                        "usable_in_production": True,
                        "rights_status": "public_domain",
                        "topic_relevant": True,
                    },
                )
            }
        )

        output = WorkflowMediaDiscoveryBridge(
            naver_youtube_provider=naver_youtube,
            open_media_provider=open_media,
            reaction_media_provider=FakeProvider(),
        ).discover({"title": "테스트 주제"}, account="A")

        self.assertEqual("completed", output["status"])
        self.assertEqual(3, output["asset_count"])
        self.assertEqual(2, output["render_asset_count"])
        self.assertIsNone(output["assets"][0]["topic_relevant"])
        self.assertTrue(output["assets"][1]["topic_relevant"])
        self.assertTrue(output["assets"][1]["render_allowed"])
        self.assertTrue(output["assets"][2]["render_allowed"])
        self.assertEqual(
            ["search_related_news", "collect_official_video"],
            [call[1] for call in naver_youtube.calls],
        )
        self.assertEqual("search_open_images", open_media.calls[0][1])

    def test_unverified_rights_stay_as_non_render_candidate(self):
        candidate = {
            "url": "https://img.example/unverified.jpg",
            "remote_url": "https://img.example/unverified.jpg",
            "usable_in_production": True,
            "topic_relevant": True,
        }
        output = run_workflow_media_discovery(
            {"title": "topic"},
            naver_youtube_provider=FakeProvider(),
            open_media_provider=FakeProvider(
                {"search_open_images": result(candidate)}
            ),
            reaction_media_provider=FakeProvider(),
        )

        self.assertEqual(1, output["asset_count"])
        self.assertEqual(0, output["render_asset_count"])
        self.assertEqual("unverified", output["assets"][0]["rights_status"])
        self.assertFalse(output["assets"][0]["render_allowed"])

    def test_explicit_render_denial_is_preserved(self):
        candidate = {
            "url": "https://img.example/denied.jpg",
            "remote_url": "https://img.example/denied.jpg",
            "usable_in_production": True,
            "rights_status": "public_domain",
            "topic_relevant": True,
            "render_allowed": False,
        }
        output = run_workflow_media_discovery(
            {"title": "topic"},
            naver_youtube_provider=FakeProvider(),
            open_media_provider=FakeProvider(
                {"search_open_images": result(candidate)}
            ),
            reaction_media_provider=FakeProvider(),
        )

        self.assertFalse(output["assets"][0]["render_allowed"])

    def test_owner_approved_local_reaction_asset_is_renderable(self):
        candidate = {
            "local_path": "F:/AI-Content-OS-Data/reaction_media/frame.png",
            "source_url": "https://example.com/reaction",
            "usable_in_production": True,
            "rights_status": "owner_approved",
            "topic_relevant": True,
            "render_allowed": True,
        }
        output = run_workflow_media_discovery(
            {"title": "topic"},
            naver_youtube_provider=FakeProvider(),
            open_media_provider=FakeProvider(),
            reaction_media_provider=FakeProvider(
                {"search_reaction_media": result(candidate, network_used=False)}
            ),
        )

        self.assertEqual(1, output["render_asset_count"])
        self.assertTrue(output["render_assets"][0]["render_allowed"])

    def test_provider_exception_becomes_structured_partial_fallback(self):
        output = run_workflow_media_discovery(
            {"category": "fashion"},
            naver_youtube_provider=FakeProvider(error=TimeoutError("timeout")),
            open_media_provider=FakeProvider(
                {
                    "search_open_images": result(
                        {
                            "url": "https://img.example/open.jpg",
                            "remote_url": "https://img.example/open.jpg",
                            "usable_in_production": True,
                            "rights_status": "open_license",
                            "topic_relevant": True,
                        }
                    )
                }
            ),
            reaction_media_provider=FakeProvider(),
        )

        self.assertEqual("partial", output["status"])
        self.assertTrue(output["fallback_used"])
        self.assertEqual("some_media_providers_failed", output["reason_code"])
        self.assertEqual(1, output["render_asset_count"])
        self.assertEqual(
            ["provider_exception", "provider_exception", "", ""],
            [item["reason_code"] for item in output["diagnostics"]],
        )

    def test_all_provider_failures_return_fallback_without_raising(self):
        output = run_workflow_media_discovery(
            {"title": "topic"},
            naver_youtube_provider=FakeProvider(error=RuntimeError("offline")),
            open_media_provider=FakeProvider(error=RuntimeError("offline")),
            reaction_media_provider=FakeProvider(error=RuntimeError("offline")),
        )

        self.assertEqual("fallback", output["status"])
        self.assertEqual("all_media_providers_failed", output["reason_code"])
        self.assertEqual([], output["assets"])
        self.assertFalse(output["network_executed"])


if __name__ == "__main__":
    unittest.main()
