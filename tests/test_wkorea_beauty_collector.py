import unittest
from unittest import mock

from modules.trend_collector.wkorea_beauty_collector import WKoreaBeautyCollector


WKOREA_FIXTURE = """
<section class="category-list"><ul>
  <li class="large">
    <a href="https://www.wkorea.com/2026/07/16/여름-웰니스-운동/">
      <div class="content">
        <h3 class="s_tit">필라테스와 요가, 나에게 맞는 운동은?</h3>
        <p class="date">2026.07.16<span>by 에디터</span></p>
      </div>
    </a>
  </li>
  <li><a href="/2026/07/13/안정형-애인-알아보는-법/"><h3>안정형 애인 알아보는 법 5</h3></a><p class="date">2026.07.13</p></li>
  <li><a href="/2026/07/12/제철-채소-건강법/"><h3>복날에 챙겨 먹는 제철 채소 4</h3></a><p class="date">2026.07.12</p></li>
  <li><a href="/2026/07/11/새로운-뷰티-씬/"><h3>지금 주목할 새로운 뷰티 씬</h3></a><p class="date">2026.07.11</p></li>
  <li><a href="/2026/07/10/차갑게-쓰는-마스크/"><h3>냉장고에 넣어둔 마스크</h3></a><p class="date">2026.07.10</p></li>
  <li>
    <div class="content">
      <a href="/2026/07/14/여름-두피-관리/"><h3 class="s_tit">여름철 두피 관리법</h3></a>
      <p class="date">2026.07.14<span>by 에디터</span></p>
      <p class="summary">목록에 노출된 두피 관리 요약입니다.</p>
    </div>
  </li>
  <li><a href="/beauty/"><h3>W Beauty 메뉴</h3></a></li>
  <li><a href="https://example.com/2026/07/16/외부-기사/"><h3>외부 기사</h3></a></li>
</ul></section>
"""


class TestWKoreaBeautyCollector(unittest.TestCase):
    def setUp(self):
        self.source = {
            "source_id": "wkorea_beauty",
            "name": "W Korea",
            "url": "https://www.wkorea.com/category/beauty/",
            "type": "consumer_beauty_editorial",
        }

    def test_visible_fields_keep_absent_category_honest(self):
        rows = WKoreaBeautyCollector(max_items=10).parse_public_list(WKOREA_FIXTURE)
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[0]["title"], "필라테스와 요가, 나에게 맞는 운동은?")
        self.assertEqual(rows[0]["published_at"], "2026.07.16")
        self.assertIsNone(rows[0]["category"])
        self.assertFalse(rows[0]["editorial_topic_eligible"])
        self.assertEqual(
            rows[0]["editorial_topic_eligibility_reason"], "generic_wellness_topic"
        )
        self.assertFalse(rows[1]["editorial_topic_eligible"])
        self.assertEqual(
            rows[1]["editorial_topic_eligibility_reason"], "relationship_topic"
        )
        self.assertFalse(rows[2]["editorial_topic_eligible"])
        self.assertEqual(
            rows[2]["editorial_topic_eligibility_reason"], "diet_or_food_topic"
        )
        self.assertTrue(rows[3]["editorial_topic_eligible"])
        self.assertEqual(
            rows[3]["editorial_topic_eligibility_reason"], "beauty_title_keyword"
        )
        self.assertTrue(rows[4]["editorial_topic_eligible"])
        self.assertEqual(
            rows[4]["editorial_topic_eligibility_reason"], "beauty_title_keyword"
        )
        self.assertEqual(rows[5]["summary"], "목록에 노출된 두피 관리 요약입니다.")
        self.assertEqual(rows[5]["published_at"], "2026.07.14")
        self.assertTrue(rows[5]["editorial_topic_eligible"])
        self.assertEqual(
            rows[5]["editorial_topic_eligibility_reason"], "beauty_title_keyword"
        )
        self.assertTrue(all("wkorea.com" in row["link"] for row in rows))

    def test_max_items_bounds_list(self):
        self.assertEqual(
            len(WKoreaBeautyCollector(max_items=1).parse_public_list(WKOREA_FIXTURE)),
            1,
        )

    def test_disabled_and_injected_live_paths_preserve_fallback_contract(self):
        blocked_fetcher = mock.Mock(side_effect=AssertionError("must not fetch"))
        blocked = WKoreaBeautyCollector(
            config={"cache_path": "tests/_missing_wkorea_beauty_cache.json"},
            fetcher=blocked_fetcher,
        )
        self.assertEqual(blocked.collect(self.source), [])
        blocked_fetcher.assert_not_called()
        self.assertEqual(
            blocked.last_status["failed_reason"],
            WKoreaBeautyCollector.LIVE_REJECTION_REASON,
        )

        live = WKoreaBeautyCollector(
            config={
                "allow_live_fetch": True,
                "cache_path": "tests/_missing_wkorea_beauty_cache.json",
            },
            fetcher=mock.Mock(return_value=(self.source["url"], WKOREA_FIXTURE)),
        )
        items = live.collect(self.source)
        self.assertEqual(len(items), 6)
        self.assertEqual(items[0]["collection_method"], "wkorea_beauty_public_list")
        self.assertFalse(items[0]["is_fallback"])


if __name__ == "__main__":
    unittest.main()
