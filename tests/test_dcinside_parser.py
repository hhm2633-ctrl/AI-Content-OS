import unittest

from modules.trend_collector.dcinside_parser import DcinsideParser


def _dcinside_fixture_html():
    return """
<table class="gall_list">
  <tbody>
    <tr class="ub-content us-post" data-no="445680" data-type="icon_txt">
      <td class="gall_num">1</td>
      <td class="gall_tit ub-word">
        <a href="/board/view/?id=dcbest&no=445680&page=1&_dcbest=1">
          <strong>[해갤]</strong>여자들도 눈물. 아이사랑두. 호날두 국내에서 민심 최고조이던 시절. ㄷ
        </a>
        <a class="reply_numbox">
          <span class="reply_num">[2109/6]</span>
        </a>
      </td>
      <td class="gall_writer ub-writer" data-nick="" data-uid="" data-ip="x.y.z.w"></td>
      <td class="gall_date" title="2026-07-15 00:00:00">07.15</td>
      <td class="gall_count">1234</td>
      <td class="gall_recommend">57</td>
    </tr>
    <tr class="ub-content" data-no="공지" data-type="icon_notice">
      <td class="gall_num">공지</td>
      <td class="gall_tit ub-word">
        <a href="/board/view/?id=dcbest&no=100">&lt;공지&gt;</a>
      </td>
      <td class="gall_date" title="2026-07-15 00:01:00">07.15</td>
      <td class="gall_count">-</td>
      <td class="gall_recommend">-</td>
    </tr>
    <tr class="ub-content us-post thum" data-no="445681" data-type="icon_pic">
      <td class="gall_num">2</td>
      <td class="gall_tit ub-word">
        <a href="/board/view/?id=dcbest&no=445681&page=1">
          정국 오늘도 예쁘네요
        </a>
        <a class="reply_numbox"><span class="reply_num">[42]</span></a>
      </td>
      <td class="gall_writer ub-writer" data-nick="nick"></td>
      <td class="gall_date" title="2026-07-14 21:55:00">21:55</td>
      <td class="gall_count">-</td>
      <td class="gall_recommend">15</td>
    </tr>
  </tbody>
</table>
"""


def _dcinside_home_best_fixture_html():
    return """
<ul>
  <li><a href="https://gall.dcinside.com/board/view/?id=dcbest&amp;no=445881"
      class="main_log" section_code="realtime_best_p">
    <div class="txt_box"><strong class="tit">첫 번째 실시간 베스트</strong></div>
  </a></li>
  <li><a href="https://gall.dcinside.com/board/view/?id=dcbest&amp;no=445873"
      class="main_log" section_code="realtime_best_p">
    <div class="box besttxt"><p>두 번째 실시간 베스트</p><span class="num">[125]</span></div>
    <div class="box best_info"><span class="name">싱글벙글 지구촌</span><span class="time">19:55</span></div>
  </a></li>
  <li><a href="https://gall.dcinside.com/board/view/?id=other&amp;no=1"
      class="main_log" section_code="realtime_best_p"><strong class="tit">제외</strong></a></li>
</ul>
"""


class DcinsideParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = DcinsideParser()

    def test_parse_us_post_rows_only_and_rank_by_row_order(self):
        items = self.parser.parse_board_list_payload("dcbest", _dcinside_fixture_html())

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["rank"], 1)
        self.assertEqual(items[1]["rank"], 2)

    def test_parse_expected_fields_without_fabrication(self):
        items = self.parser.parse_board_list_payload("dcbest", _dcinside_fixture_html())
        first = items[0]

        self.assertEqual(first["post_no"], "445680")
        self.assertEqual(first["post_type"], "icon_txt")
        self.assertEqual(
            first["title"],
            "여자들도 눈물. 아이사랑두. 호날두 국내에서 민심 최고조이던 시절. ㄷ",
        )
        self.assertEqual(first["origin_board_tag"], "해갤")
        self.assertEqual(first["url"], "https://gall.dcinside.com/board/view/?id=dcbest&no=445680&page=1&_dcbest=1")
        self.assertEqual(first["posted_at"], "2026-07-15 00:00:00")
        self.assertEqual(first["views"], 1234)
        self.assertEqual(first["comments"], 2109)
        self.assertEqual(first["recommends"], 57)

    def test_views_zero_when_dash_and_comments_strip_prefix(self):
        items = self.parser.parse_board_list_payload("dcbest", _dcinside_fixture_html())
        second = items[1]

        self.assertEqual(second["views"], 0)
        self.assertEqual(second["comments"], 42)
        self.assertEqual(second["origin_board_tag"], None)
        self.assertEqual(second["title"], "정국 오늘도 예쁘네요")

    def test_parse_public_homepage_realtime_best_without_fabricating_metrics(self):
        items = self.parser.parse_board_list_payload("dcbest", _dcinside_home_best_fixture_html())

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["title"], "첫 번째 실시간 베스트")
        self.assertEqual(items[0]["rank"], 1)
        self.assertIsNone(items[0]["views"])
        self.assertIsNone(items[0]["recommends"])
        self.assertEqual(items[1]["comments"], 125)
        self.assertEqual(items[1]["origin_board_tag"], "싱글벙글 지구촌")
        self.assertEqual(items[1]["posted_at"], "19:55")


if __name__ == "__main__":
    unittest.main()
