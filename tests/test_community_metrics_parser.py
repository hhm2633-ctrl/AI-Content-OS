"""Community Metrics Parser V1 tests.

Fixture HTML below is modeled on real list-page captures (2026-07-14) of
pann.nate.com/talk/ranking, fmkorea.com/best, and bobaedream.co.kr/list?code=best.
The contract under test:
- visible_metrics (views/comments/likes/...) are parsed from HTML when present
- anything not present in the HTML stays None — never estimated or fabricated
- media_flags.has_image is True with image_count >= 1 when an image marker exists
- Korean labels / commas / whitespace around numbers are tolerated
- a structure change degrades to the legacy title/link parse, never to a crash
"""

import unittest

from modules.source_intake.source_intake_schema import (
    VISIBLE_METRIC_KEYS,
    validate_shallow_item,
    build_shallow_item,
)
from modules.trend_collector.bobaedream_collector import BobaedreamCollector
from modules.trend_collector.fmkorea_collector import FMKoreaCollector
from modules.trend_collector.nate_pann_collector import NatePannCollector


NATE_PANN_FIXTURE = """
<div class="cntList">
  <ul class="post_wrap">
    <li>
      <div class="rankNum"><span class="no1"><span>1</span></span></div>
      <div class="thumb">
        <a href="/talk/375515410"><img src="https://thumb.pann.com/tc_100x100/a.jpg" width="71" height="70" alt="썸네일" /></a>
      </div>
      <dl>
        <dt><h2><a href="/talk/375515410" title="첫번째 인기 게시글 제목">첫번째 인기 게시글 제목</a></h2><span class="reple-num">(98)</span></dt>
        <dd class="txt"><a href="/talk/375515410">본문 요약 텍스트입니다...</a></dd>
        <dd class="info"><span class="count">조회 74,428</span><span class="rcm">추천 249</span></dd>
      </dl>
    </li><li>
      <div class="rankNum"><span class="no2"><span>2</span></span></div>
      <dl>
        <dt><h2><a href="/talk/375515499" title="두번째 게시글은 지표 없음">두번째 게시글은 지표 없음</a></h2></dt>
        <dd class="txt"><a href="/talk/375515499">지표 표기가 없는 게시글</a></dd>
      </dl>
    </li>
  </ul>
</div>
"""

FMKOREA_FIXTURE = """
<div class="fm_best_widget _bd_pc">
<ul>
<li class="li li_best2_pop1"><div class="li" style="padding-left:50px;position:relative;">
  <a href="/index.php?mid=best2&amp;document_srl=10081998462" class="pc_voted_count pc_voted_count_plus"> <span class="label">추천 </span> <span class="count">1,614</span> </a>
  <h3 class="title" data-title-ellipsis="true"> <a href="/index.php?mid=best2&amp;document_srl=10081998462" class=" hotdeal_var8"> <span class="ellipsis-target">에펨 베스트 첫번째 글 제목</span>&nbsp; <span class="comment_count">[356]</span> </a> </h3>
  <div> <span class="category"> <a href="/humor">유머</a> /</span> <span class="regdate">3 시간 전</span> </div>
</div></li>
<li class="li li_best2_pop0"><div class="li" style="padding-left:120px;position:relative;">
  <a href="/best/10082800480" class="pc_voted_count pc_voted_count_plus pc_voted_count_short"> <span class="label">추천 </span> <span class="count">143</span> </a>
  <a href="/best/10082800480"> <img class="thumb" src="//image.fmkorea.com/classes/lazy/img/transparent.gif" data-original="//image.fmkorea.com/thumb.webp" alt="썸네일" /> </a>
  <h3 class="title" data-title-ellipsis="true"> <a href="/best/10082800480" class=" hotdeal_var8"> <span class="ellipsis-target">썸네일 있는 두번째 글 제목</span>&nbsp; <span class="comment_count">[125]</span> </a> </h3>
  <div> <span class="category"> <a href="/humor">유머</a> </span> </div>
</div></li>
<li class="li li_best2_pop0"><div class="li">
  <h3 class="title"> <a href="/best/10082800999" class=" hotdeal_var8"> <span class="ellipsis-target">지표가 하나도 없는 세번째 글</span> </a> </h3>
</div></li>
</ul>
</div>
"""

BOBAEDREAM_FIXTURE = """
<table>
<tr itemscope itemtype="http://schema.org/Article" data-summary="목격자가 공개한 사고 당시 상황입니다.">
  <td class="category" title="신유머/이슈/움짤"><a href="/list.php?code=humor">신유머/이..</a></td>
  <td class="pl14">
    <a class="bsubject" style="padding:0;font-size:13px;" href="/view?code=best&No=1009828&vdate=" itemprop="name">보배드림 첫번째 베스트 글</a><img style="padding-left:3px" class="jpg" src="//image.bobaedream.co.kr/newimg/jpg.gif" alt="첨부파일" />&nbsp;<a style="padding-left:2px" href="/view?code=best&No=1009828&vdate=&cmt=1"><span class="Comment">(<strong class="totreply">17</strong>)</span></a>
  </td>
  <td class="author02"><span class="author">작성자</span></td>
  <td class="date">18:38</td>
  <td class="recomm"><font style="color:#ff7234;font-weight:bold;">114</font><font color="#999999"></font></td>
  <td class="count" style="color:#666666"><strong>5,904</strong></td>
</tr>
<tr itemscope itemtype="http://schema.org/Article">
  <td class="category" title="정치게시판"><a href="/list.php?code=politic">정치게시판</a></td>
  <td class="pl14">
    <a class="bsubject" href="/view?code=best&No=1009823&vdate=" itemprop="name">첨부파일 없는 두번째 글</a>
  </td>
  <td class="author02"><span class="author">작성자</span></td>
  <td class="date">18:25</td>
</tr>
</table>
"""


class NatePannParserTests(unittest.TestCase):
    def setUp(self):
        self.articles = NatePannCollector()._parse_articles(NATE_PANN_FIXTURE)

    def test_two_articles_parsed(self):
        self.assertEqual(len(self.articles), 2)

    def test_views_comments_likes_parsed(self):
        metrics = self.articles[0]["visible_metrics"]
        self.assertEqual(metrics["views"], 74428)
        self.assertEqual(metrics["comments"], 98)
        self.assertEqual(metrics["likes"], 249)

    def test_thumbnail_sets_media_flags(self):
        flags = self.articles[0]["media_flags"]
        self.assertTrue(flags["has_image"])
        self.assertGreaterEqual(flags["image_count"], 1)

    def test_absent_metrics_stay_none(self):
        metrics = self.articles[1]["visible_metrics"]
        self.assertIsNone(metrics["views"])
        self.assertIsNone(metrics["comments"])
        self.assertIsNone(metrics["likes"])

    def test_absent_image_marker_stays_none(self):
        flags = self.articles[1]["media_flags"]
        self.assertIsNone(flags["has_image"])
        self.assertIsNone(flags["image_count"])

    def test_link_and_summary_preserved(self):
        self.assertEqual(self.articles[0]["link"], "https://pann.nate.com/talk/375515410")
        self.assertIn("본문 요약", self.articles[0]["summary"])


class FMKoreaParserTests(unittest.TestCase):
    def setUp(self):
        self.articles = FMKoreaCollector()._parse_articles(FMKOREA_FIXTURE)

    def test_three_articles_parsed(self):
        self.assertEqual(len(self.articles), 3)

    def test_comments_and_likes_parsed(self):
        metrics = self.articles[0]["visible_metrics"]
        self.assertEqual(metrics["comments"], 356)
        self.assertEqual(metrics["likes"], 1614)

    def test_views_not_visible_on_best_list_stays_none(self):
        # fmkorea best list shows 추천/댓글 only; views must never be invented
        self.assertIsNone(self.articles[0]["visible_metrics"].get("views"))

    def test_category_parsed(self):
        self.assertEqual(self.articles[0]["board_or_category"], "유머")

    def test_thumbnail_sets_media_flags(self):
        flags = self.articles[1]["media_flags"]
        self.assertTrue(flags["has_image"])
        self.assertGreaterEqual(flags["image_count"], 1)

    def test_no_thumbnail_stays_none(self):
        flags = self.articles[0]["media_flags"]
        self.assertIsNone(flags["has_image"])
        self.assertIsNone(flags["image_count"])

    def test_article_without_any_metric_is_all_none(self):
        metrics = self.articles[2]["visible_metrics"]
        self.assertIsNone(metrics.get("comments"))
        self.assertIsNone(metrics.get("likes"))

    def test_title_comes_from_ellipsis_target_without_comment_count(self):
        self.assertEqual(self.articles[0]["title"], "에펨 베스트 첫번째 글 제목")


class BobaedreamParserTests(unittest.TestCase):
    def setUp(self):
        self.articles = BobaedreamCollector()._parse_articles(BOBAEDREAM_FIXTURE)

    def test_two_articles_parsed(self):
        self.assertEqual(len(self.articles), 2)

    def test_views_comments_likes_parsed(self):
        metrics = self.articles[0]["visible_metrics"]
        self.assertEqual(metrics["views"], 5904)
        self.assertEqual(metrics["comments"], 17)
        self.assertEqual(metrics["likes"], 114)

    def test_category_parsed(self):
        self.assertEqual(self.articles[0]["board_or_category"], "신유머/이슈/움짤")
        self.assertEqual(self.articles[1]["board_or_category"], "정치게시판")

    def test_attachment_icon_sets_media_flags(self):
        flags = self.articles[0]["media_flags"]
        self.assertTrue(flags["has_image"])
        self.assertGreaterEqual(flags["image_count"], 1)

    def test_visible_row_summary_is_preserved_without_inference(self):
        self.assertEqual(
            self.articles[0]["summary"],
            "목격자가 공개한 사고 당시 상황입니다.",
        )
        self.assertEqual(self.articles[1]["summary"], "")

    def test_visible_summary_element_is_cleaned(self):
        fixture = """
        <table><tr><td class="pl14">
          <a class="bsubject" href="/view?code=best&No=2">요약 요소가 있는 게시글</a>
          <p class="list-desc"><b>공개된</b> 행 요약 텍스트</p>
        </td></tr></table>
        """
        articles = BobaedreamCollector()._parse_articles(fixture)
        self.assertEqual(articles[0]["summary"], "공개된 행 요약 텍스트")

    def test_row_without_metrics_stays_none(self):
        metrics = self.articles[1]["visible_metrics"]
        self.assertIsNone(metrics["views"])
        self.assertIsNone(metrics["comments"])
        self.assertIsNone(metrics["likes"])
        self.assertIsNone(self.articles[1]["media_flags"]["has_image"])


class MetricNumberParsingTests(unittest.TestCase):
    """Korean labels / commas / whitespace never break number parsing,
    and unparsable text becomes None instead of a guessed value."""

    def setUp(self):
        self.parse = NatePannCollector()._parse_metric_number

    def test_plain_comma_number(self):
        self.assertEqual(self.parse("1,234"), 1234)

    def test_korean_view_label(self):
        self.assertEqual(self.parse("조회 1,234"), 1234)

    def test_korean_comment_label(self):
        self.assertEqual(self.parse("댓글 56"), 56)

    def test_whitespace_defense(self):
        self.assertEqual(self.parse("  추천   249  "), 249)

    def test_exact_korean_unit_conversion(self):
        self.assertEqual(self.parse("1.2만"), 12000)
        self.assertEqual(self.parse("3천"), 3000)

    def test_unparsable_text_is_none(self):
        self.assertIsNone(self.parse("NEW"))
        self.assertIsNone(self.parse(""))
        self.assertIsNone(self.parse(None))

    def test_fractional_without_unit_is_none(self):
        # "1.5" alone cannot be an exact count -> refuse rather than round
        self.assertIsNone(self.parse("1.5"))

    def test_same_helper_on_all_collectors(self):
        for collector in [FMKoreaCollector(), BobaedreamCollector()]:
            self.assertEqual(collector._parse_metric_number("조회 1,234"), 1234)
            self.assertIsNone(collector._parse_metric_number("없음"))


class BuildItemsIntegrationTests(unittest.TestCase):
    """Parsed metrics survive _build_items intact; existing fields are kept
    and rank_position matches the build order."""

    EXISTING_FIELDS = [
        "keyword", "link", "summary", "publisher", "published_at",
        "source_id", "source_name", "source_type", "tier", "weight",
        "base_score", "trend_reason", "collection_method",
        "is_fallback", "collected_at",
    ]

    def build(self, collector, fixture, source_name):
        articles = collector._parse_articles(fixture)
        return collector._build_items(
            articles=articles,
            source={"name": source_name, "type": "community"},
            collection_method="test",
        )

    def assert_items_contract(self, items):
        for index, item in enumerate(items, start=1):
            for field in self.EXISTING_FIELDS:
                self.assertIn(field, item)
            self.assertEqual(item["rank_position"], index)
            self.assertIn("board_or_category", item)
            self.assertIn("visible_metrics", item)
            self.assertIn("media_flags", item)
            self.assertNotIn("fabricated_metrics", item)
            for key in VISIBLE_METRIC_KEYS:
                value = item["visible_metrics"][key]
                if value is not None:
                    self.assertIsInstance(value, int)
                    self.assertGreaterEqual(value, 0)

    def test_nate_pann_items(self):
        items = self.build(NatePannCollector(), NATE_PANN_FIXTURE, "네이트판")
        self.assert_items_contract(items)
        self.assertEqual(items[0]["visible_metrics"]["views"], 74428)

    def test_fmkorea_items(self):
        items = self.build(FMKoreaCollector(), FMKOREA_FIXTURE, "FM코리아")
        self.assert_items_contract(items)
        self.assertEqual(items[0]["visible_metrics"]["likes"], 1614)
        self.assertIsNone(items[0]["visible_metrics"]["views"])

    def test_bobaedream_items(self):
        items = self.build(BobaedreamCollector(), BOBAEDREAM_FIXTURE, "보배드림")
        self.assert_items_contract(items)
        self.assertEqual(items[0]["visible_metrics"]["comments"], 17)

    def test_items_validate_as_shallow_schema(self):
        items = self.build(BobaedreamCollector(), BOBAEDREAM_FIXTURE, "보배드림")
        for item in items:
            shallow = build_shallow_item(
                source_id=item["source_id"],
                source_type=item["source_type"],
                title=item["keyword"],
                url=item["link"],
                rank_position=item["rank_position"],
                board_or_category=item["board_or_category"],
                visible_metrics=item["visible_metrics"],
                media_flags=item["media_flags"],
            )
            ok, errors = validate_shallow_item(shallow)
            self.assertTrue(ok, errors)


class StructureChangeFallbackTests(unittest.TestCase):
    """A layout change must degrade to the legacy title/link parse (metrics
    None), and garbage input must return an empty list, never raise."""

    def test_nate_pann_legacy_markup_still_parses_titles(self):
        legacy_html = '<a href="/talk/12345">예전 구조의 게시글 제목</a>'
        articles = NatePannCollector()._parse_articles(legacy_html)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["title"], "예전 구조의 게시글 제목")
        self.assertNotIn("visible_metrics", articles[0])

    def test_fmkorea_legacy_markup_still_parses_titles(self):
        legacy_html = '<a href="/12345">예전 구조의 게시글 제목</a>'
        articles = FMKoreaCollector()._parse_articles(legacy_html)
        self.assertEqual(len(articles), 1)

    def test_bobaedream_legacy_markup_still_parses_titles(self):
        legacy_html = '<a href="/view?code=best&No=1">예전 구조의 게시글 제목</a>'
        articles = BobaedreamCollector()._parse_articles(legacy_html)
        self.assertEqual(len(articles), 1)

    def test_garbage_input_returns_empty_list(self):
        for collector in [NatePannCollector(), FMKoreaCollector(), BobaedreamCollector()]:
            self.assertEqual(collector._parse_articles(""), [])
            self.assertEqual(collector._parse_articles("<html><body>no list</body></html>"), [])


if __name__ == "__main__":
    unittest.main()
