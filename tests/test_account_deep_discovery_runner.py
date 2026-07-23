"""Focused tests for the bounded account deep-discovery runner."""

import unittest

from modules.source_intake.account_deep_discovery_runner import (
    ACCOUNT_DISCOVERY_PLANS,
    MAX_REQUESTS_PER_ACCOUNT,
    run_account_deep_discovery,
)


def _selection(account, count, prefix=None):
    prefix = prefix or account
    return {
        "accounts": {
            account: {
                "selected": [
                    {
                        "candidate_id": f"{prefix}-{index}",
                        "title": f"후보 {index}",
                        "category": "테스트",
                        "grade": "1",
                        "source_urls": ["https://example.com"],
                    }
                    for index in range(count)
                ]
            }
        }
    }


class FakeProvider:
    """Offline fake provider; records calls and returns injected results."""

    name = "fake_offline_provider"

    def __init__(self, results=None, errors=None, network_used=False):
        self.results = results or {}
        self.errors = errors or {}
        self.network_used = network_used
        self.calls = []

    def discover(self, account, operation, request):
        self.calls.append((account, operation, request["candidate_id"]))
        if operation in self.errors:
            raise self.errors[operation]
        return {
            "status": "ok",
            "network_used": self.network_used,
            "assets": self.results.get(operation, []),
        }


class AccountDeepDiscoveryRunnerTest(unittest.TestCase):
    def test_selected_only_bounded_to_five_per_account(self):
        provider = FakeProvider()
        result = run_account_deep_discovery(_selection("A", 6), provider)
        bucket = result["accounts"]["A"]
        self.assertEqual(bucket["requested"], 6)
        self.assertEqual(bucket["executed"], MAX_REQUESTS_PER_ACCOUNT)
        self.assertEqual(bucket["skipped_over_limit"], ["A-5"])
        executed_ids = {call[2] for call in provider.calls}
        self.assertEqual(executed_ids, {"A-0", "A-1", "A-2", "A-3", "A-4"})
        self.assertEqual(result["accounts"]["B"]["executed"], 0)

    def test_deduplicates_provider_work_before_account_limit(self):
        provider = FakeProvider()
        selected = [
            {
                "candidate_id": "A-duplicate",
                "title": "최초 제목",
                "category": "국내뉴스",
                "grade": "1",
                "source_urls": ["https://example.com/first"],
            },
            {
                "candidate_id": "A-duplicate",
                "title": "후속 중복 제목",
                "category": "국내뉴스",
                "grade": "2",
                "source_urls": ["https://example.com/duplicate"],
            },
            *[
                {
                    "candidate_id": f"A-unique-{index}",
                    "title": f"고유 후보 {index}",
                    "category": "국내뉴스",
                    "grade": "1",
                    "source_urls": [],
                }
                for index in range(4)
            ],
        ]
        result = run_account_deep_discovery(
            {"accounts": {"A": {"selected": selected}}},
            provider,
        )
        bucket = result["accounts"]["A"]

        self.assertEqual(bucket["requested"], 6)
        self.assertEqual(bucket["unique_requested"], 5)
        self.assertEqual(bucket["executed"], MAX_REQUESTS_PER_ACCOUNT)
        self.assertEqual(bucket["skipped_over_limit"], [])
        self.assertEqual(
            bucket["deduplicated_requests"],
            [
                {
                    "candidate_id": "A-duplicate",
                    "category": "국내뉴스",
                    "duplicate_operations_eliminated": len(ACCOUNT_DISCOVERY_PLANS["A"]),
                }
            ],
        )
        self.assertEqual(bucket["duplicate_operations_eliminated"], 5)
        self.assertEqual(bucket["provider_calls_without_dedupe"], 25)
        self.assertEqual(bucket["provider_calls_planned"], 25)
        self.assertEqual(bucket["provider_call_reduction"], 0)
        self.assertEqual(len(provider.calls), 5 * len(ACCOUNT_DISCOVERY_PLANS["A"]))
        duplicate_calls = [call for call in provider.calls if call[2] == "A-duplicate"]
        self.assertEqual(len(duplicate_calls), len(ACCOUNT_DISCOVERY_PLANS["A"]))
        self.assertEqual(bucket["results"][0]["title"], "최초 제목")

    def test_same_candidate_in_different_categories_is_not_deduplicated(self):
        provider = FakeProvider()
        result = run_account_deep_discovery(
            {
                "requests": [
                    {"account": "C", "candidate_id": "C-1", "category": "패션"},
                    {"account": "C", "candidate_id": "C-1", "category": "뷰티"},
                ]
            },
            provider,
        )
        bucket = result["accounts"]["C"]

        self.assertEqual(bucket["executed"], 2)
        self.assertEqual(bucket["deduplicated_requests"], [])
        self.assertEqual(len(provider.calls), 2 * len(ACCOUNT_DISCOVERY_PLANS["C"]))

    def test_measures_provider_call_reduction_for_repeated_selection(self):
        provider = FakeProvider()
        repeated = {
            "accounts": {
                "A": {
                    "selected": [
                        {
                            "candidate_id": "A-same",
                            "title": "같은 후보",
                            "category": "국내뉴스",
                        }
                        for _ in range(4)
                    ]
                }
            }
        }
        result = run_account_deep_discovery(repeated, provider)
        bucket = result["accounts"]["A"]

        self.assertEqual(bucket["provider_calls_without_dedupe"], 20)
        self.assertEqual(bucket["provider_calls_planned"], 5)
        self.assertEqual(bucket["provider_call_reduction"], 15)
        self.assertEqual(len(provider.calls), 5)

    def test_account_specific_operations_and_artifact_roles(self):
        provider = FakeProvider()
        selection = {
            "accounts": {
                account: _selection(account, 1)["accounts"][account]
                for account in ("A", "B", "C")
            }
        }
        result = run_account_deep_discovery(selection, provider)
        for account, plan in ACCOUNT_DISCOVERY_PLANS.items():
            operations = result["accounts"][account]["results"][0]["operations"]
            self.assertEqual(
                [(op["operation"], op["artifact_role"]) for op in operations],
                [(step["operation"], step["artifact_role"]) for step in plan],
            )
        roles_b = [op["artifact_role"] for op in result["accounts"]["B"]["results"][0]["operations"]]
        self.assertIn("real_comment", roles_b)
        self.assertIn("reconstruction_scene_fact", roles_b)

    def test_account_a_includes_bounded_auxiliary_media_discovery_contract(self):
        plan = {
            step["operation"]: step["artifact_role"]
            for step in ACCOUNT_DISCOVERY_PLANS["A"]
        }
        self.assertEqual(plan["search_related_news"], "related_news")
        self.assertEqual(
            plan["locate_embedded_or_broadcast_video"],
            "broadcast_video",
        )
        self.assertEqual(plan["search_open_images"], "open_image")

        provider = FakeProvider()
        result = run_account_deep_discovery(_selection("A", 1), provider)
        operations = {
            operation["operation"]: operation
            for operation in result["accounts"]["A"]["results"][0]["operations"]
        }
        for operation in (
            "search_related_news",
            "locate_embedded_or_broadcast_video",
            "search_open_images",
        ):
            self.assertIn(operation, operations)
            self.assertEqual(operations[operation]["status"], "empty")

    def test_provider_failure_is_additive_and_safe(self):
        provider = FakeProvider(errors={"collect_news_images": RuntimeError("timeout")})
        result = run_account_deep_discovery(_selection("A", 1), provider)
        operations = {op["operation"]: op for op in result["accounts"]["A"]["results"][0]["operations"]}
        failed = operations["collect_news_images"]
        self.assertEqual(failed["status"], "provider_failed")
        self.assertEqual(failed["error"], "timeout")
        self.assertEqual(failed["assets"], [])
        self.assertEqual(operations["fetch_article_body"]["status"], "empty")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(
            result["failures"],
            [{"account": "A", "candidate_id": "A-0", "operation": "collect_news_images", "error": "timeout"}],
        )

    def test_ap_assets_are_reference_only(self):
        provider = FakeProvider(
            results={
                "collect_news_images": [
                    {"url": "https://img/1", "credit": "AP Photo"},
                    {"url": "https://img/2", "source": "Associated Press"},
                    {"url": "https://img/3", "source": "Newsis"},
                ]
            }
        )
        result = run_account_deep_discovery(_selection("A", 1), provider)
        operations = {op["operation"]: op for op in result["accounts"]["A"]["results"][0]["operations"]}
        assets = operations["collect_news_images"]["assets"]
        by_url = {asset["url"]: asset for asset in assets}
        for url in ("https://img/1", "https://img/2"):
            self.assertTrue(by_url[url]["reference_only"])
            self.assertFalse(by_url[url]["usable_in_production"])
            self.assertEqual(by_url[url]["restriction_reason"], "ap_reference_only")
        self.assertFalse(by_url["https://img/3"]["reference_only"])
        self.assertTrue(by_url["https://img/3"]["usable_in_production"])

    def test_ap_related_news_assets_remain_reference_only(self):
        provider = FakeProvider(
            results={
                "search_related_news": [
                    {
                        "url": "https://example.com/ap-coverage",
                        "publisher": "Associated Press",
                        "metadata_only": True,
                    }
                ]
            }
        )
        result = run_account_deep_discovery(_selection("A", 1), provider)
        operations = {
            operation["operation"]: operation
            for operation in result["accounts"]["A"]["results"][0]["operations"]
        }
        asset = operations["search_related_news"]["assets"][0]
        self.assertTrue(asset["reference_only"])
        self.assertFalse(asset["usable_in_production"])
        self.assertEqual(asset["restriction_reason"], "ap_reference_only")

    def test_real_comments_require_provider_verification_flag(self):
        provider = FakeProvider(
            results={
                "collect_real_comments": [
                    {"text": "진짜 댓글", "is_real_comment": True},
                    {"text": "출처 불명 댓글"},
                    {"text": "가짜 표시", "is_real_comment": "yes"},
                ]
            }
        )
        result = run_account_deep_discovery(_selection("B", 1), provider)
        operations = {op["operation"]: op for op in result["accounts"]["B"]["results"][0]["operations"]}
        comments = operations["collect_real_comments"]
        self.assertEqual([asset["text"] for asset in comments["assets"]], ["진짜 댓글"])
        self.assertEqual(len(comments["rejected"]), 2)
        self.assertTrue(all(item["reason"] == "unverified_comment_rejected" for item in comments["rejected"]))

    def test_execution_and_network_flags_are_honest(self):
        offline = FakeProvider(network_used=False)
        result = run_account_deep_discovery(_selection("C", 1), offline)
        self.assertTrue(result["execution_enabled"])
        self.assertFalse(result["network_executed"])
        self.assertEqual(result["provider"], "fake_offline_provider")

        online = FakeProvider(network_used=True)
        result = run_account_deep_discovery(_selection("C", 1), online)
        self.assertTrue(result["network_executed"])

    def test_missing_provider_or_empty_selection_closes_safely(self):
        closed = run_account_deep_discovery(_selection("A", 1), None)
        self.assertEqual(closed["status"], "closed")
        self.assertEqual(closed["reason_code"], "missing_provider")
        self.assertFalse(closed["execution_enabled"])
        self.assertFalse(closed["network_executed"])

        empty = run_account_deep_discovery({"accounts": {}}, FakeProvider())
        self.assertEqual(empty["reason_code"], "no_selected_requests")

    def test_accepts_owner_queue_request_list_shape(self):
        provider = FakeProvider()
        payload = {
            "requests": [
                {"candidate_id": "B-9", "account": "B", "title": "썰", "grade": "1"},
                {"candidate_id": "X-1", "account": "Z", "title": "무효 계정"},
            ]
        }
        result = run_account_deep_discovery(payload, provider)
        self.assertEqual(result["accounts"]["B"]["executed"], 1)
        self.assertEqual(result["accounts"]["A"]["executed"], 0)


if __name__ == "__main__":
    unittest.main()
