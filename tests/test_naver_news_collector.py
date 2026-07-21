import unittest
from unittest import mock

from modules.trend_collector.naver_news_collector import NaverNewsCollector

SOURCE = {
    "source_id": "naver_news",
    "name": "Naver News",
    "type": "news",
    "tier": 1,
    "weight": 30,
}


class StubApiHubClient:
    def __init__(self, result):
        self.result = result
        self.queries = []

    def is_configured(self):
        return bool(self.result.get("credentials_present"))

    def search_news(self, query, display=5, sort="date"):
        self.queries.append(query)
        payload = dict(self.result)
        payload["query"] = query
        return payload


def _ok_result():
    return {
        "status": "ok",
        "items": [
            {
                "title": "API HUB 기사 제목",
                "link": "https://example.com/api-hub-article",
                "description": "API HUB 기사 요약",
                "pubDate": "Tue, 14 Jul 2026 08:30:00 +0900",
                "source": "naver_api_hub",
                "collection_method": "naver_news_api_hub",
            }
        ],
        "count": 1,
        "error_type": "",
        "safe_message": "",
        "credentials_present": True,
        "collection_method": "naver_news_api_hub",
    }


def _failed_result(error_type, credentials_present=True):
    return {
        "status": "failed",
        "items": [],
        "count": 0,
        "error_type": error_type,
        "safe_message": f"safe message for {error_type}",
        "credentials_present": credentials_present,
        "collection_method": "naver_news_api_hub",
    }


def _rss_item(collector):
    return collector._build_trend_item(
        query="AI",
        title="RSS 기사 제목",
        link="https://example.com/rss-article",
        summary="RSS 요약",
        published_at="",
        index=1,
        source=SOURCE,
        collection_method="naver_news_rss",
    )


class NaverNewsCollectorApiHubTest(unittest.TestCase):
    def test_rss_success_skips_html_and_api_hub(self):
        stub = StubApiHubClient(_ok_result())
        collector = NaverNewsCollector(api_hub_client=stub)

        with mock.patch.object(
            collector,
            "_collect_from_rss",
            return_value=[_rss_item(collector)],
        ), mock.patch.object(
            collector,
            "_collect_from_search_result",
        ) as html_mock:
            results = collector.collect(query_keywords=["AI"], source=SOURCE)

        html_mock.assert_not_called()
        self.assertEqual(stub.queries, [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["collection_method"], "naver_news_rss")
        api_status = collector.last_status["api_hub"]
        self.assertFalse(api_status["attempted"])
        self.assertFalse(api_status["used"])
        self.assertIsNone(api_status["credentials_present"])

    def test_html_success_after_empty_rss_skips_api_hub(self):
        stub = StubApiHubClient(_ok_result())
        collector = NaverNewsCollector(api_hub_client=stub)
        html_item = collector._build_trend_item(
            query="AI",
            title="HTML 기사 제목",
            link="https://example.com/html-article",
            summary="HTML 요약",
            published_at="",
            index=1,
            source=SOURCE,
            collection_method="naver_news_html",
        )

        with mock.patch.object(
            collector,
            "_collect_from_rss",
            return_value=[],
        ), mock.patch.object(
            collector,
            "_collect_from_search_result",
            return_value=[html_item],
        ):
            results = collector.collect(query_keywords=["AI"], source=SOURCE)

        self.assertEqual(stub.queries, [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["collection_method"], "naver_news_html")

    def test_api_hub_success_is_used_after_both_free_paths_are_empty(self):
        stub = StubApiHubClient(_ok_result())
        collector = NaverNewsCollector(api_hub_client=stub)

        with mock.patch.object(
            collector,
            "_collect_from_rss",
            return_value=[],
        ), mock.patch.object(
            collector,
            "_collect_from_search_result",
            return_value=[],
        ):
            results = collector.collect(query_keywords=["AI"], source=SOURCE)

        self.assertEqual(stub.queries, ["AI"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["collection_method"], "naver_news_api_hub")
        api_status = collector.last_status["api_hub"]
        self.assertTrue(api_status["attempted"])
        self.assertTrue(api_status["used"])

    def test_api_hub_failure_after_free_misses_is_non_fatal(self):
        stub = StubApiHubClient(_failed_result("http_401_unauthorized"))
        collector = NaverNewsCollector(api_hub_client=stub)

        with mock.patch.object(
            collector,
            "_collect_from_rss",
            return_value=[],
        ), mock.patch.object(
            collector,
            "_collect_from_search_result",
            return_value=[],
        ):
            results = collector.collect(query_keywords=["AI"], source=SOURCE)

        self.assertEqual(results, [])
        self.assertEqual(stub.queries, ["AI"])
        self.assertFalse(collector.last_status["success"])
        self.assertEqual(collector.last_status["failed_reason"], "no_results")

        api_status = collector.last_status["api_hub"]
        self.assertFalse(api_status["used"])
        self.assertEqual(api_status["error_type"], "http_401_unauthorized")
        self.assertTrue(api_status["credentials_present"])

    def test_missing_credentials_is_diagnostic_only(self):
        stub = StubApiHubClient(
            _failed_result("missing_credentials", credentials_present=False)
        )
        collector = NaverNewsCollector(api_hub_client=stub)

        with mock.patch.object(
            collector,
            "_collect_from_rss",
            return_value=[],
        ), mock.patch.object(
            collector,
            "_collect_from_search_result",
            return_value=[],
        ):
            results = collector.collect(query_keywords=["AI"], source=SOURCE)

        self.assertEqual(results, [])
        self.assertEqual(stub.queries, ["AI"])
        api_status = collector.last_status["api_hub"]
        self.assertFalse(api_status["attempted"])
        self.assertFalse(api_status["used"])
        self.assertFalse(api_status["credentials_present"])
        self.assertEqual(api_status["error_type"], "missing_credentials")

    def test_api_hub_exception_never_breaks_collection(self):
        stub = StubApiHubClient(_ok_result())
        stub.search_news = mock.Mock(side_effect=RuntimeError("boom"))
        collector = NaverNewsCollector(api_hub_client=stub)

        with mock.patch.object(
            collector,
            "_collect_from_rss",
            return_value=[],
        ), mock.patch.object(
            collector,
            "_collect_from_search_result",
            return_value=[],
        ):
            results = collector.collect(query_keywords=["AI"], source=SOURCE)

        self.assertEqual(results, [])
        self.assertEqual(stub.search_news.call_count, 1)
        api_status = collector.last_status["api_hub"]
        self.assertTrue(api_status["attempted"])
        self.assertEqual(api_status["error_type"], "unknown_error")

    def test_each_query_allows_at_most_one_api_hub_call(self):
        stub = StubApiHubClient(_failed_result("http_429_rate_limited"))
        collector = NaverNewsCollector(api_hub_client=stub)

        with mock.patch.object(
            collector,
            "_collect_from_rss",
            return_value=[],
        ), mock.patch.object(
            collector,
            "_collect_from_search_result",
            return_value=[],
        ):
            collector.collect(query_keywords=["AI", "패션"], source=SOURCE)

        self.assertEqual(stub.queries, ["AI", "패션"])


if __name__ == "__main__":
    unittest.main()
