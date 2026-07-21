import unittest
from unittest.mock import patch

from modules.trend_collector.nate_pann_collector import NatePannCollector
from modules.trend_collector.retry_policy import RetryPolicy
from modules.trend_collector.trend_source_manager import TrendSourceManager


class RetryPolicyTest(unittest.TestCase):
    def test_configured_retry_budget_is_not_silently_increased(self):
        calls = 0

        def collect():
            nonlocal calls
            calls += 1
            return []

        policy = RetryPolicy(enabled=True, max_retries=2, delay_seconds=0)

        with patch("modules.trend_collector.retry_policy.time.sleep"):
            results, status = policy.run_collect(
                collect_fn=collect,
                status_fn=lambda: {
                    "attempted": True,
                    "success": False,
                    "failed_reason": "connection_refused",
                },
            )

        self.assertEqual(results, [])
        self.assertEqual(calls, 3)
        self.assertEqual(status["retry_count"], 2)

    def test_zero_retry_budget_performs_one_attempt(self):
        calls = 0

        def collect():
            nonlocal calls
            calls += 1
            return []

        policy = RetryPolicy(enabled=True, max_retries=0, delay_seconds=0)
        _, status = policy.run_collect(
            collect_fn=collect,
            status_fn=lambda: {"success": False, "failed_reason": "timeout"},
        )

        self.assertEqual(calls, 1)
        self.assertEqual(status["retry_count"], 0)

    def test_nate_pann_navigation_heading_is_not_an_article_title(self):
        collector = NatePannCollector()

        self.assertFalse(collector._is_valid_title("톡커들의 선택 명예의 전당"))
        self.assertTrue(collector._is_valid_title("계란값 다들 인내심이 대단해졌네요"))

    def test_nate_pann_cache_reapplies_title_validation(self):
        manager = TrendSourceManager.__new__(TrendSourceManager)
        manager.nate_pann_collector = NatePannCollector()
        manager.nate_pann_cache_path = None
        manager._read_json = lambda _path: {
            "items": [
                {"keyword": "톡커들의 선택 명예의 전당"},
                {"keyword": "계란값 다들 인내심이 대단해졌네요"},
            ]
        }
        manager._now = lambda: "2026-07-11T00:00:00"

        results = manager._load_nate_pann_cache(
            {"name": "네이트판", "type": "community", "tier": 1, "weight": 30}
        )

        self.assertEqual([item["keyword"] for item in results], ["계란값 다들 인내심이 대단해졌네요"])


if __name__ == "__main__":
    unittest.main()
