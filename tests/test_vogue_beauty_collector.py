import unittest
from unittest import mock

from modules.trend_collector.vogue_beauty_collector import VogueBeautyCollector


VOGUE_FIXTURE = """
<section class="beauty-list">
  <div class="list_highlight">
    <a href="/2026/07/09/궁극의-브러시/">
      <div class="post_content">
        <p><span>뷰티 화보</span><span>2026.07.09</span></p>
        <h3>뷰티 전문가가 꼽은 궁극의 브러시</h3>
        <p class="summary">목록에서 확인되는 브러시 소개입니다.</p>
      </div>
    </a>
  </div>
  <ul><li>
    <a href="https://www.vogue.co.kr/2026/07/16/여름-샴푸/">
      <p class="category">뷰티 트렌드</p>
      <h3 class="s_tit">마트 샴푸도 괜찮을까?</h3>
      <p class="date">2026.07.16<span>by 에디터</span></p>
    </a>
  </li>
  <li>
    <a href="/2026/07/15/숙면을-위한-저녁-습관/">
      <p class="category">웰니스</p>
      <h3 class="s_tit">숙면을 위한 저녁 습관</h3>
      <p class="date">2026.07.15</p>
    </a>
  </li>
  <li><a href="/category/beauty/"><h3>뷰티 메뉴</h3></a></li>
  <li><a href="https://www.allurekorea.com/2026/07/16/외부-기사/"><h3>외부 기사</h3></a></li>
  </ul>
</section>
"""


class TestVogueBeautyCollector(unittest.TestCase):
    def setUp(self):
        self.source = {
            "source_id": "vogue_beauty",
            "name": "Vogue Korea",
            "url": "https://www.vogue.co.kr/category/beauty/",
            "type": "consumer_beauty_editorial",
        }

    def test_utf8_visible_fields_and_same_domain_filter(self):
        rows = VogueBeautyCollector(max_items=10).parse_public_list(VOGUE_FIXTURE)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["title"], "마트 샴푸도 괜찮을까?")
        self.assertEqual(rows[0]["category"], "뷰티 트렌드")
        self.assertEqual(rows[0]["published_at"], "2026.07.16")
        self.assertFalse(rows[1]["editorial_topic_eligible"])
        self.assertEqual(
            rows[1]["editorial_topic_eligibility_reason"], "generic_wellness_topic"
        )
        highlight = rows[2]
        self.assertEqual(highlight["category"], "뷰티 화보")
        self.assertEqual(highlight["summary"], "목록에서 확인되는 브러시 소개입니다.")
        self.assertTrue(all("vogue.co.kr" in row["link"] for row in rows))

    def test_max_items_bounds_list(self):
        self.assertEqual(
            len(VogueBeautyCollector(max_items=1).parse_public_list(VOGUE_FIXTURE)),
            1,
        )

    def test_fallback_first_policy_and_injected_live_result(self):
        blocked_fetcher = mock.Mock(side_effect=AssertionError("must not fetch"))
        blocked = VogueBeautyCollector(
            config={"cache_path": "tests/_missing_vogue_beauty_cache.json"},
            fetcher=blocked_fetcher,
        )
        self.assertEqual(blocked.collect(self.source), [])
        blocked_fetcher.assert_not_called()
        self.assertEqual(blocked.last_status["collection_method"], "vogue_beauty_no_data")

        live = VogueBeautyCollector(
            config={
                "allow_live_fetch": True,
                "cache_path": "tests/_missing_vogue_beauty_cache.json",
            },
            fetcher=mock.Mock(return_value=(self.source["url"], VOGUE_FIXTURE)),
        )
        items = live.collect(self.source)
        self.assertEqual(len(items), 3)
        self.assertFalse(items[0]["is_fallback"])
        self.assertEqual(items[0]["publisher"], "Vogue Korea")


if __name__ == "__main__":
    unittest.main()
