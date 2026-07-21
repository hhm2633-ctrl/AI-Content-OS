import unittest
import xml.etree.ElementTree as ET

from modules.trend_collector.naver_news_collector import NaverNewsCollector


SOURCE = {
    "source_id": "naver_news",
    "name": "Naver News",
    "type": "news",
    "tier": 1,
    "weight": 30,
}


API_HUB_FAILED_RESULT = {
    "status": "failed",
    "query": "",
    "items": [],
    "count": 0,
    "error_type": "missing_credentials",
    "safe_message": "NAVER API HUB credentials are missing or empty; API path skipped.",
    "credentials_present": False,
    "collection_method": "naver_news_api_hub",
}


API_HUB_OK_RESULT = {
    "status": "ok",
    "query": "",
    "items": [
        {
            "title": "API 허브 기사 제목",
            "link": "https://news.example.com/api-hub-1",
            "description": "API 허브 기사 요약",
            "pubDate": "Tue, 14 Jul 2026 09:00:00 +0900",
        }
    ],
    "count": 1,
    "error_type": "",
    "safe_message": "",
    "credentials_present": True,
    "collection_method": "naver_news_api_hub",
}


RSS_PLAIN = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>naver news search</title>
    <item>
      <title>일반 RSS 기사 제목</title>
      <originallink>https://news.example.com/plain-1</originallink>
      <link>https://search.naver.com/redirect/plain-1</link>
      <description>일반 RSS 기사 요약</description>
      <pubDate>Tue, 14 Jul 2026 08:00:00 +0900</pubDate>
    </item>
  </channel>
</rss>
"""


RSS_DEFAULT_NAMESPACE = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns="http://example.com/rss-ns" version="2.0">
  <channel>
    <item>
      <title>기본 네임스페이스 기사</title>
      <link>https://news.example.com/ns-default-1</link>
      <description>기본 네임스페이스 요약</description>
      <pubDate>Tue, 14 Jul 2026 07:00:00 +0900</pubDate>
    </item>
  </channel>
</rss>
"""


RSS_PREFIXED_NAMESPACE = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:nns="http://example.com/naver-news" version="2.0">
  <channel>
    <nns:item>
      <nns:title>접두사 네임스페이스 기사</nns:title>
      <nns:link>https://news.example.com/ns-prefix-1</nns:link>
      <nns:description>접두사 네임스페이스 요약</nns:description>
      <nns:pubDate>Tue, 14 Jul 2026 06:00:00 +0900</nns:pubDate>
    </nns:item>
  </channel>
</rss>
"""


RSS_CASE_VARIED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <ITEM>
      <Title>대소문자 변형 기사</Title>
      <LINK>https://news.example.com/case-1</LINK>
      <Description>대소문자 변형 요약</Description>
      <PubDate>Tue, 14 Jul 2026 05:00:00 +0900</PubDate>
    </ITEM>
  </channel>
</rss>
"""


RSS_CDATA = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title><![CDATA[CDATA 기사 제목]]></title>
      <link>https://news.example.com/cdata-1</link>
      <description><![CDATA[CDATA 기사 <b>요약</b>]]></description>
      <pubDate>Tue, 14 Jul 2026 04:00:00 +0900</pubDate>
    </item>
  </channel>
</rss>
"""


# Not well-formed XML (stray & plus unbound prefix) with intact <item> blocks:
# ET.fromstring raises ParseError, the lenient recovery must still extract items.
RSS_MALFORMED_RECOVERABLE = """<rss version="2.0">
  <channel>
    <broken>&</broken>
    <media:item>
      <media:title><![CDATA[복구된 기사 제목]]></media:title>
      <media:link>https://news.example.com/lenient-1</media:link>
      <media:description>복구된 기사 요약</media:description>
      <media:pubDate>Tue, 14 Jul 2026 03:00:00 +0900</media:pubDate>
    </media:item>
    <item>
      <title>두번째 복구 기사</title>
      <link>https://news.example.com/lenient-2</link>
    </item>
  </channel>
</rss>
"""


RSS_HTML_PAYLOAD = """<!DOCTYPE html>
<html lang="ko"><head><title>검색 결과</title></head>
<body><p>RSS 엔드포인트가 HTML 페이지를 반환했습니다.</p></body></html>
"""


RSS_UNPARSABLE = "<<<this is not xml and has no item blocks>>>"


RSS_EMPTY_CHANNEL = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>empty</title></channel></rss>
"""


# Legacy news_tit markup with shuffled attribute order and single quotes.
HTML_NEWS_TIT_ATTR_ORDER = """<html><body>
<a title="속성 순서 변경 기사" data-extra="x" href="https://news.example.com/html-1"
   class="info news_tit">속성 순서 변경 기사</a>
<a href='https://news.example.com/html-2' class='news_tit'
   title='단일 인용부호 기사'>단일 인용부호 기사</a>
</body></html>
"""


# Legacy fallback form: news_tit anchor with no href/title attributes.
HTML_NEWS_TIT_TITLE_ONLY = """<html><body>
<a class="news_tit"><span>제목만 있는 기사</span></a>
</body></html>
"""


# Newer search markup: data-heatmap-target anchors with visible spans.
HTML_HEATMAP = """<html><body>
<a nocr="1" href="https://news.example.com/heatmap-1" data-heatmap-target=".tit">
  <span class="sds-comps-text sds-comps-text-ellipsis-1">히트맵 기사 제목</span>
</a>
<div class="sds-comps-profile-info-title"><span>언론사</span></div>
<a data-heatmap-target=".body" href="https://news.example.com/heatmap-1">
  <span class="sds-comps-text">히트맵 기사 요약 본문</span>
</a>
</body></html>
"""


HTML_EMPTY = "<html><body><p>기사가 없습니다.</p></body></html>"


class StubApiHubClient:
    """API Hub stub: returns a canned result, never touches the network."""

    def __init__(self, result=None):
        self.calls = []
        self._result = result if result is not None else dict(API_HUB_FAILED_RESULT)

    def search_news(self, query, display=5, sort="date"):
        self.calls.append(query)
        result = dict(self._result)
        result["query"] = query
        return result


class OfflineNaverNewsCollector(NaverNewsCollector):
    """Fixture-driven collector: _fetch_url serves canned payloads only.

    payloads: {"rss": <str or Exception>, "html": <str or Exception>}.
    A missing key means that path must not be fetched in the scenario.
    """

    def __init__(self, payloads, api_hub_client=None, **kwargs):
        super().__init__(
            api_hub_client=api_hub_client if api_hub_client is not None else StubApiHubClient(),
            **kwargs,
        )
        self.payloads = payloads
        self.fetched_urls = []

    def _fetch_url(self, url):
        self.fetched_urls.append(url)
        key = "rss" if "where=rss" in url else "html"

        if key not in self.payloads:
            raise AssertionError(f"unexpected {key} fetch in this scenario: {url}")

        payload = self.payloads[key]

        if isinstance(payload, Exception):
            raise payload

        return payload


class TestNaverNewsCollectorApiHubChain(unittest.TestCase):
    def test_api_hub_success_short_circuits_rss_and_html(self):
        collector = OfflineNaverNewsCollector(
            payloads={},
            api_hub_client=StubApiHubClient(API_HUB_OK_RESULT),
        )
        items = collector.collect(["전기차"], SOURCE)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["collection_method"], "naver_news_api_hub")
        self.assertEqual(items[0]["keyword"], "API 허브 기사 제목")
        self.assertEqual(collector.fetched_urls, [])
        self.assertTrue(collector.last_status["api_hub"]["used"])
        self.assertTrue(collector.last_status["success"])

    def test_api_hub_failure_falls_back_to_rss(self):
        collector = OfflineNaverNewsCollector(payloads={"rss": RSS_PLAIN})
        items = collector.collect(["전기차"], SOURCE)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["collection_method"], "naver_news_rss")
        self.assertFalse(collector.last_status["api_hub"]["used"])
        self.assertEqual(
            collector.last_status["api_hub"]["error_type"],
            "missing_credentials",
        )


class TestNaverNewsCollectorRssParsing(unittest.TestCase):
    def collect_single(self, rss_payload, extra_payloads=None):
        payloads = {"rss": rss_payload}

        if extra_payloads:
            payloads.update(extra_payloads)

        collector = OfflineNaverNewsCollector(payloads=payloads)
        return collector, collector.collect(["전기차"], SOURCE)

    def test_plain_rss_items_parse(self):
        collector, items = self.collect_single(RSS_PLAIN)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["keyword"], "일반 RSS 기사 제목")
        self.assertEqual(item["link"], "https://news.example.com/plain-1")
        self.assertEqual(item["summary"], "일반 RSS 기사 요약")
        self.assertEqual(item["published_at"], "Tue, 14 Jul 2026 08:00:00 +0900")
        self.assertEqual(item["publisher"], "news.example.com")
        self.assertEqual(item["collection_method"], "naver_news_rss")
        self.assertTrue(collector.last_status["success"])

    def test_default_namespace_items_parse_without_raising(self):
        collector, items = self.collect_single(RSS_DEFAULT_NAMESPACE)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["keyword"], "기본 네임스페이스 기사")
        self.assertEqual(items[0]["link"], "https://news.example.com/ns-default-1")
        self.assertEqual(items[0]["collection_method"], "naver_news_rss")
        self.assertEqual(collector.last_status["failed_reason"], "")

    def test_prefixed_namespace_items_parse_without_raising(self):
        collector, items = self.collect_single(RSS_PREFIXED_NAMESPACE)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["keyword"], "접두사 네임스페이스 기사")
        self.assertEqual(items[0]["link"], "https://news.example.com/ns-prefix-1")
        self.assertEqual(items[0]["summary"], "접두사 네임스페이스 요약")

    def test_case_varied_tags_parse_without_raising(self):
        collector, items = self.collect_single(RSS_CASE_VARIED)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["keyword"], "대소문자 변형 기사")
        self.assertEqual(items[0]["link"], "https://news.example.com/case-1")
        self.assertEqual(items[0]["published_at"], "Tue, 14 Jul 2026 05:00:00 +0900")

    def test_cdata_fields_extract_visible_text_only(self):
        collector, items = self.collect_single(RSS_CDATA)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["keyword"], "CDATA 기사 제목")
        self.assertEqual(items[0]["summary"], "CDATA 기사 요약")

    def test_malformed_rss_recovers_items_leniently(self):
        collector, items = self.collect_single(RSS_MALFORMED_RECOVERABLE)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["keyword"], "복구된 기사 제목")
        self.assertEqual(items[0]["link"], "https://news.example.com/lenient-1")
        self.assertEqual(items[0]["summary"], "복구된 기사 요약")
        self.assertEqual(items[1]["keyword"], "두번째 복구 기사")
        self.assertEqual(items[1]["summary"], "")
        self.assertEqual(items[0]["collection_method"], "naver_news_rss")
        # RSS recovered, so the HTML search path must not have been fetched.
        self.assertEqual(len(collector.fetched_urls), 1)

    def test_html_payload_on_rss_endpoint_falls_through_to_html_search(self):
        collector, items = self.collect_single(
            RSS_HTML_PAYLOAD,
            extra_payloads={"html": HTML_NEWS_TIT_ATTR_ORDER},
        )

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["collection_method"], "naver_news_html")
        self.assertTrue(collector.last_status["success"])
        self.assertEqual(collector.last_status["failed_reason"], "")


class TestNaverNewsCollectorHtmlParsing(unittest.TestCase):
    def collect_html(self, html_payload):
        collector = OfflineNaverNewsCollector(
            payloads={"rss": RSS_EMPTY_CHANNEL, "html": html_payload},
        )
        return collector, collector.collect(["전기차"], SOURCE)

    def test_attribute_order_and_quote_style_variations(self):
        collector, items = self.collect_html(HTML_NEWS_TIT_ATTR_ORDER)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["keyword"], "속성 순서 변경 기사")
        self.assertEqual(items[0]["link"], "https://news.example.com/html-1")
        self.assertEqual(items[1]["keyword"], "단일 인용부호 기사")
        self.assertEqual(items[1]["link"], "https://news.example.com/html-2")
        self.assertEqual(items[0]["collection_method"], "naver_news_html")

    def test_heatmap_layout_extracts_visible_title_link_summary(self):
        collector, items = self.collect_html(HTML_HEATMAP)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["keyword"], "히트맵 기사 제목")
        self.assertEqual(item["link"], "https://news.example.com/heatmap-1")
        self.assertEqual(item["summary"], "히트맵 기사 요약 본문")
        # Publisher is derived from the link domain only, never fabricated.
        self.assertEqual(item["publisher"], "news.example.com")
        self.assertEqual(item["published_at"], "")

    def test_title_only_anchor_never_fabricates_fields(self):
        collector, items = self.collect_html(HTML_NEWS_TIT_TITLE_ONLY)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["keyword"], "제목만 있는 기사")
        self.assertEqual(item["link"], "")
        self.assertEqual(item["summary"], "")
        self.assertEqual(item["publisher"], "")
        self.assertEqual(item["published_at"], "")


class TestNaverNewsCollectorReasonCodes(unittest.TestCase):
    def test_unparsable_rss_and_empty_html_reports_parse_failed(self):
        collector = OfflineNaverNewsCollector(
            payloads={"rss": RSS_UNPARSABLE, "html": HTML_EMPTY},
        )
        items = collector.collect(["전기차"], SOURCE)

        self.assertEqual(items, [])
        self.assertFalse(collector.last_status["success"])
        self.assertEqual(collector.last_status["failed_reason"], "parse_failed")
        self.assertEqual(collector.last_status["final_error_type"], "parse_failed")
        self.assertEqual(
            collector.last_status["service_diagnostic"].get("status"),
            "fallback_used",
        )
        # Both paths were attempted before the parse failure was reported.
        self.assertEqual(len(collector.fetched_urls), 2)

    def test_valid_but_empty_rss_and_html_reports_no_results(self):
        collector = OfflineNaverNewsCollector(
            payloads={"rss": RSS_EMPTY_CHANNEL, "html": HTML_EMPTY},
        )
        items = collector.collect(["전기차"], SOURCE)

        self.assertEqual(items, [])
        self.assertEqual(collector.last_status["failed_reason"], "no_results")
        self.assertEqual(collector.last_status["final_error_type"], "no_results")

    def test_rss_network_error_classification_is_preserved(self):
        collector = OfflineNaverNewsCollector(
            payloads={"rss": TimeoutError("timed out")},
        )
        items = collector.collect(["전기차"], SOURCE)

        self.assertEqual(items, [])
        self.assertEqual(collector.last_status["failed_reason"], "timeout")

    def test_parse_error_classification_helper(self):
        collector = OfflineNaverNewsCollector(payloads={})

        self.assertEqual(
            collector._classify_error(ET.ParseError("broken")),
            "parse_failed",
        )


if __name__ == "__main__":
    unittest.main()
