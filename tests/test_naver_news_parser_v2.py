import unittest

from modules.trend_collector.naver_news_parser_v2 import NaverNewsParserV2


RSS_RETURNING_HTML = """<!doctype html><html><body><div>Search service temporary layout</div></body></html>"""

SEARCH_SDS_FIXTURE = """
<div data-template-id="news">
  <a nocr="1" data-heatmap-target=".tit" href="https://news.ifm.kr/news/articleView.html?idxno=111">
    <span class="sds-comps-text sds-comps-text-type-headline1">새로운 정책 <mark>회복</mark></span>
  </a>
  <a href="#" data-heatmap-target=".body">
    <span class="sds-comps-text sds-comps-text-type-body1">정책 복구 본문 요약</span>
  </a>
  <div class="sds-comps-profile-info-title">
    <span class="sds-comps-text-type-body2">테크데일리</span>
    <span class="sds-comps-text-type-body2">20분 전</span>
  </div>
</div>
<div class="fender-ui_xyz">
  <a nocr="1" data-heatmap-target=".tit" href="https://example.com/press/222">
    <span class="sds-comps-text sds-comps-text-type-headline1">두 번째 헤드라인</span>
  </a>
  <a data-heatmap-target=".body" href="https://example.com/press/222">
    <span class="sds-comps-text sds-comps-text-type-body2">요약 없음</span>
  </a>
  <div class="sds-comps-profile-info-title">
    <span class="sds-comps-text-type-body2">이슈리뷰</span>
    <span class="sds-comps-text-type-body2">1시간 전</span>
  </div>
</div>
"""

RANKING_FIXTURE_BYTES = (
    "<div class='rankingnews_box_wrap _popularRanking'>"
    "  <div class='rankingnews_box'>"
    '    <strong class="rankingnews_name">ABC</strong>'
    '    <a class="list_title list_title1" href="https://n.news.naver.com/article/ABC/0000000001">'
    "      랭킹 제목 1"
    "    </a>"
    '    <em class="list_ranking_num">1<span class="blind">위</span></em>'
    '    <a class="list_title list_title2" href="https://n.news.naver.com/article/ABC/0000000002">'
    "      랭킹 제목 2"
    "    </a>"
    '    <em class="list_ranking_num">2<span class="blind">위</span></em>'
    "  </div>"
    "</div>"
).encode("euc-kr")

SECTION_FIXTURE = """
<div class="sa_item">
  <a class="sa_text_title" href="https://n.news.naver.com/mnews/article/ABC/0000000011" data-nlog-params="{&quot;section1_id&quot;:&quot;100&quot;,&quot;rank&quot;:1}">
    <strong class="sa_text_strong">섹션 제목 1</strong>
  </a>
  <span class="sa_text_press">ABC</span>
  <span class="sa_text_datetime is_recent"><b>19분전</b></span>
</div>
<div class="sa_item">
  <a class="sa_text_title" href="https://n.news.naver.com/mnews/article/ABC/0000000012" data-nlog-params="{&quot;section1_id&quot;:&quot;100&quot;,&quot;rank&quot;:2}">
    <strong class="sa_text_strong">섹션 제목 2</strong>
  </a>
  <span class="sa_text_press">ABC</span>
  <span class="sa_text_datetime is_recent"><b>35분전</b></span>
</div>
"""


class TestNaverNewsParserV2(unittest.TestCase):
    def setUp(self):
        self.parser = NaverNewsParserV2()
        self.source = {
            "source_id": "naver_news",
            "name": "Naver News",
            "type": "news",
            "tier": 1,
            "weight": 30,
            "keyword": "테스트",
        }

    def test_rss_endpoint_returning_html_falls_back_to_html_search_parser(self):
        result = self.parser.parse_query(
            query="인플레이션",
            source=self.source,
            rss_payload=RSS_RETURNING_HTML,
            search_payload=SEARCH_SDS_FIXTURE,
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["collection_method"], "naver_news_html")
        self.assertIn("새로운 정책", result[0]["keyword"])

    def test_search_markup_parses_new_sds_components(self):
        result = self.parser.parse_search_payload("경제", self.source, SEARCH_SDS_FIXTURE)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["keyword"], "새로운 정책 회복")
        self.assertEqual(result[0]["link"], "https://news.ifm.kr/news/articleView.html?idxno=111")
        self.assertEqual(result[0]["summary"], "정책 복구 본문 요약")
        self.assertEqual(result[0]["collection_method"], "naver_news_html")
        self.assertEqual(result[0]["publisher"], "news.ifm.kr")

    def test_ranking_markup_parses_press_name_title_and_rank(self):
        ranking_html = self.parser.decode_euc_kr_html(RANKING_FIXTURE_BYTES)
        result = self.parser.parse_ranking_payload(source=self.source, raw_html=ranking_html)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["collection_method"], "naver_news_ranking")
        self.assertEqual(result[0]["rank"], 1)
        self.assertEqual(result[0]["keyword"], "랭킹 제목 1")
        self.assertEqual(result[0]["publisher"], "ABC")
        self.assertEqual(result[1]["rank"], 2)
        self.assertEqual(result[1]["link"], "https://n.news.naver.com/article/ABC/0000000002")

    def test_section_markup_parses_category_and_rank_from_data_nlog_params(self):
        result = self.parser.parse_section_payload(section_id="100", source=self.source, raw_html=SECTION_FIXTURE)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["collection_method"], "naver_news_section")
        self.assertEqual(result[0]["category"], "100")
        self.assertEqual(result[0]["rank"], 1)
        self.assertEqual(result[0]["keyword"], "섹션 제목 1")
        self.assertEqual(result[0]["published_at"], "19분전")


if __name__ == "__main__":
    unittest.main()

