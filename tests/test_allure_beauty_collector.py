import unittest
from unittest import mock

from modules.trend_collector.allure_beauty_collector import AllureBeautyCollector


ALLURE_FIXTURE = """
<main><ul>
  <li class="beauty-card">
    <a href="https://www.allurekorea.com/2026/07/16/여름-메이크업-포인트/">
      <p class="category">MAKEUP</p>
      <h3 class="s_tit">제니가 선택한 올여름 메이크업 키 포인트</h3>
      <p class="summary">공개 목록에 표시된 메이크업 요약입니다.</p>
      <p class="date">2026.07.16<span>by 에디터</span></p>
    </a>
  </li>
  <li><a href="/beauty/skincare/"><h3>스킨케어 메뉴</h3></a></li>
  <li><a href="https://example.com/2026/07/16/외부-기사/"><h3>외부 기사</h3></a></li>
  <li><a href="/2026/07/15/여름-헤어-컬러/"><h3>여름에 어울리는 헤어 컬러</h3></a></li>
  <li><a href="/2026/07/14/여름-카디건-스타일링/"><h3>한여름에도 입는 얇은 카디건</h3></a></li>
  <li><a href="/2026/07/13/에디터의-뷰티템/"><h3>에디터가 고른 여름 뷰티템</h3></a></li>
  <li><a href="/2026/07/12/새로운-뷰티-소식/"><h3>지금 알아둘 새로운 뷰티 소식</h3></a></li>
</ul></main>
"""


class TestAllureBeautyCollector(unittest.TestCase):
    def setUp(self):
        self.source = {
            "source_id": "allure_beauty",
            "name": "Allure Korea",
            "url": "https://www.allurekorea.com/beauty/",
            "type": "consumer_beauty_editorial",
        }

    def test_visible_fields_and_strict_article_links(self):
        rows = AllureBeautyCollector(max_items=10).parse_public_list(ALLURE_FIXTURE)
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["title"], "제니가 선택한 올여름 메이크업 키 포인트")
        self.assertEqual(rows[0]["category"], "MAKEUP")
        self.assertEqual(rows[0]["published_at"], "2026.07.16")
        self.assertEqual(rows[0]["summary"], "공개 목록에 표시된 메이크업 요약입니다.")
        self.assertEqual(rows[0]["rank_basis"], "visible_list_order")
        self.assertTrue(rows[1]["link"].startswith("https://www.allurekorea.com/"))
        self.assertTrue(rows[0]["editorial_topic_eligible"])
        self.assertEqual(
            rows[0]["editorial_topic_eligibility_reason"], "beauty_category_signal"
        )
        self.assertTrue(rows[1]["editorial_topic_eligible"])
        self.assertFalse(rows[2]["editorial_topic_eligible"])
        self.assertEqual(
            rows[2]["editorial_topic_eligibility_reason"], "fashion_apparel_topic"
        )
        self.assertTrue(rows[3]["editorial_topic_eligible"])
        self.assertEqual(
            rows[3]["editorial_topic_eligibility_reason"], "beauty_title_keyword"
        )
        self.assertTrue(rows[4]["editorial_topic_eligible"])
        self.assertEqual(
            rows[4]["editorial_topic_eligibility_reason"], "beauty_title_keyword"
        )

    def test_max_items_bounds_list(self):
        rows = AllureBeautyCollector(max_items=1).parse_public_list(ALLURE_FIXTURE)
        self.assertEqual(len(rows), 1)

    def test_disabled_live_is_honest_and_does_not_fetch(self):
        fetcher = mock.Mock(side_effect=AssertionError("network must stay disabled"))
        collector = AllureBeautyCollector(
            config={"cache_path": "tests/_missing_allure_beauty_cache.json"},
            fetcher=fetcher,
        )
        self.assertEqual(collector.collect(self.source), [])
        fetcher.assert_not_called()
        self.assertEqual(
            collector.last_status["failed_reason"],
            AllureBeautyCollector.LIVE_REJECTION_REASON,
        )
        self.assertFalse(collector.last_status["used_cache"])

    def test_injected_public_list_is_non_fallback(self):
        collector = AllureBeautyCollector(
            config={
                "allow_live_fetch": True,
                "cache_path": "tests/_missing_allure_beauty_cache.json",
            },
            fetcher=mock.Mock(return_value=(self.source["url"], ALLURE_FIXTURE)),
        )
        items = collector.collect(self.source)
        self.assertEqual(len(items), 5)
        self.assertFalse(items[0]["is_fallback"])
        self.assertEqual(items[0]["collection_method"], "allure_beauty_public_list")
        self.assertTrue(collector.last_status["success"])


if __name__ == "__main__":
    unittest.main()
