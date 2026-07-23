import unittest

from scripts.run_selected_candidate_production_flow import (
    AccountProviderRouter,
    run_owner_selected_flow,
)


class LocalProvider:
    name = "local_test_provider"

    def __init__(self):
        self.calls = []

    def discover(self, account, operation, request):
        self.calls.append((account, operation, dict(request)))
        if operation == "fetch_article_body":
            return {
                "status": "ok",
                "network_used": False,
                "assets": [{
                    "type": "article_body",
                    "url": request["source_urls"][0],
                    "body": "확인된 첫 문장\n확인된 둘째 문장",
                    "reference_only": True,
                    "usable_in_production": False,
                }],
            }
        return {"status": "ok", "network_used": False, "assets": []}


class RunSelectedCandidateProductionFlowTest(unittest.TestCase):
    def test_router_can_override_one_account_operation(self):
        default = LocalProvider()
        article = LocalProvider()
        router = AccountProviderRouter(
            {"C": default},
            {("C", "fetch_article_body"): article},
        )

        router.discover("C", "fetch_article_body", {
            "candidate_id": "beauty-1",
            "title": "뷰티 기사",
            "category": "beauty",
            "source_urls": ["https://example.com/beauty"],
        })
        router.discover("C", "collect_official_video", {
            "candidate_id": "beauty-1",
            "title": "뷰티 기사",
            "category": "beauty",
            "source_urls": ["https://example.com/beauty"],
        })

        self.assertEqual(article.calls[0][1], "fetch_article_body")
        self.assertEqual(default.calls[0][1], "collect_official_video")

    def test_owner_queue_reaches_deep_discovery_without_field_loss(self):
        queue = {
            "schema_version": "owner_ranked_deep_dive_queue_v1",
            "requests": [{
                "candidate_id": "news-1",
                "grade": "1",
                "account": "A",
                "category": "society",
                "title": "검증 뉴스",
                "source_urls": ["https://example.com/news-1"],
                "requested_media": ["article_body"],
            }],
        }
        provider = LocalProvider()

        result = run_owner_selected_flow(queue, provider)

        self.assertEqual("render_inputs_ready", result["status"])
        self.assertEqual(5, len(provider.calls))
        first_request = provider.calls[0][2]
        self.assertEqual("news-1", first_request["candidate_id"])
        self.assertEqual("검증 뉴스", first_request["title"])
        self.assertEqual("society", first_request["category"])
        self.assertEqual("1", first_request["grade"])
        self.assertEqual(["https://example.com/news-1"], first_request["source_urls"])
        plan = result["production_flow"]["production_plans"][0]
        self.assertEqual(
            ["확인된 첫 문장", "확인된 둘째 문장"],
            plan["copy_plan"]["key_points"],
        )
        self.assertFalse(result["render_executed"])
        self.assertFalse(result["publishing_executed"])


if __name__ == "__main__":
    unittest.main()
