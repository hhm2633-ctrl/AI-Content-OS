import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from modules.trend_collector.gq_grooming_collector import GqGroomingCollector


GQ_GROOMING_FIXTURE = """
<main>
  <nav><a href="/style/grooming/">그루밍 홈</a></nav>
  <ul class="post-list">
    <li id="p_410001">
      <a href="/2026/07/11/여름철-남자-그루밍-팁/">
        <div class="content">
          <p class="category">grooming</p>
          <h3 class="s_tit">쉽게 깔끔해 보이는 여름철 남자 그루밍 팁</h3>
          <p class="summary">목록에 공개된 피부와 면도 관리 요약입니다.</p>
          <p class="date">2026.07.11<span>by 김에디터</span></p>
        </div>
      </a>
    </li>
    <li id="p_410002">
      <a href="https://www.gqkorea.co.kr/2026/07/08/산뜻한-시트러스-향수/">
        <div class="content">
          <p class="category">grooming</p>
          <h3 class="s_tit">남자를 위한 산뜻한 시트러스 향수 추천</h3>
          <p class="date">2026.07.08<span>by 조에디터</span></p>
        </div>
      </a>
    </li>
    <li><a href="/style/">같은 도메인 탐색 링크</a></li>
    <li><a href="https://outside.example/2026/07/01/article/">외부 기사</a></li>
  </ul>
</main>
"""

GQ_GROOMING_SCOPE_FIXTURE = """
<ul class="post-list">
  <li>
    <a href="/2026/07/12/가죽-구두를-오래-신는-관리법/">
      <p class="category">grooming</p>
      <h3>가죽 구두를 오래 신는 관리법</h3>
      <p class="date">2026.07.12</p>
    </a>
  </li>
  <li>
    <a href="/2026/07/10/두피와-모발을-위한-샴푸법/">
      <p class="category">grooming</p>
      <h3>두피와 모발을 위한 올바른 샴푸법</h3>
      <p class="date">2026.07.10</p>
    </a>
  </li>
</ul>
"""


class TestGqGroomingCollector(unittest.TestCase):
    def setUp(self):
        self.source = {
            "source_id": "gq_grooming",
            "name": "GQ Korea",
            "url": GqGroomingCollector.DEFAULT_URL,
            "type": "male_grooming_editorial",
        }
        self.no_cache = "tests/_nonexistent_gq_grooming_cache.json"

    def test_utf8_korean_list_preserves_only_visible_card_metadata(self):
        fixture = GQ_GROOMING_FIXTURE.encode("utf-8").decode("utf-8")

        rows = GqGroomingCollector(max_items=10).parse_public_list(fixture)

        self.assertEqual(len(rows), 2)
        first, second = rows
        self.assertEqual(first["title"], "쉽게 깔끔해 보이는 여름철 남자 그루밍 팁")
        self.assertEqual(
            first["link"],
            "https://www.gqkorea.co.kr/2026/07/11/여름철-남자-그루밍-팁/",
        )
        self.assertEqual(first["section_category"], "grooming")
        self.assertEqual(first["visible_date"], "2026.07.11")
        self.assertEqual(first["summary"], "목록에 공개된 피부와 면도 관리 요약입니다.")
        self.assertIsNone(second["summary"])
        self.assertEqual(second["rank_position"], 2)

    def test_parser_is_bounded_and_rejects_navigation_and_external_links(self):
        rows = GqGroomingCollector(max_items=1).parse_public_list(
            GQ_GROOMING_FIXTURE
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["rank_basis"], "visible_list_order")

    def test_live_items_carry_male_grooming_scope_without_detail_collection(self):
        collector = GqGroomingCollector(
            config={"allow_live_fetch": True, "cache_path": self.no_cache},
            fetcher=lambda url: (url, GQ_GROOMING_FIXTURE),
        )

        items = collector.collect(self.source)

        self.assertEqual(len(items), 2)
        first = items[0]
        self.assertEqual(first["source_id"], "gq_grooming")
        self.assertEqual(first["source_type"], "male_grooming_editorial")
        self.assertEqual(first["collection_method"], GqGroomingCollector.LIVE_METHOD)
        self.assertEqual(
            first["grooming_topic_labels"],
            ["male_grooming", "skincare", "hair", "scalp", "shaving", "body", "fragrance"],
        )
        self.assertTrue(first["grooming_editorial"])
        self.assertTrue(first["editorial_topic_eligible"])
        self.assertEqual(
            first["editorial_topic_eligibility_reason"],
            "matched_title_keyword:male_grooming",
        )
        self.assertFalse(first["article_detail_collected"])
        self.assertFalse(first["is_fallback"])

    def test_out_of_scope_row_is_preserved_but_not_editorial_topic_eligible(self):
        collector = GqGroomingCollector(
            config={"allow_live_fetch": True, "cache_path": self.no_cache},
            fetcher=lambda url: (url, GQ_GROOMING_SCOPE_FIXTURE),
        )

        items = collector.collect(self.source)

        self.assertEqual(len(items), 2)
        shoe_care, shampoo = items
        self.assertEqual(shoe_care["title"], "가죽 구두를 오래 신는 관리법")
        self.assertFalse(shoe_care["editorial_topic_eligible"])
        self.assertEqual(
            shoe_care["editorial_topic_eligibility_reason"],
            GqGroomingCollector.OUT_OF_SCOPE_REASON,
        )
        self.assertTrue(shampoo["editorial_topic_eligible"])
        self.assertEqual(
            shampoo["editorial_topic_eligibility_reason"],
            "matched_title_keyword:hair",
        )

    def test_live_false_negative_titles_are_male_grooming_eligible(self):
        exact_cases = (
            ("남성 장발 스타일을 깔끔하게 관리하는 법", "matched_title_keyword:hair"),
            ("예쁜 손을 만드는 남자 손 관리 습관", "matched_title_keyword:hand_care"),
            ("건조한 계절에 쓰기 좋은 핸드워시", "matched_title_keyword:hand_care"),
        )

        for title, expected_reason in exact_cases:
            with self.subTest(title=title):
                eligible, reason = GqGroomingCollector._classify_editorial_topic(title)
                self.assertTrue(eligible)
                self.assertEqual(reason, expected_reason)

    def test_disabled_live_is_honest_and_does_not_fetch(self):
        fetcher = mock.Mock(side_effect=AssertionError("network must remain disabled"))
        collector = GqGroomingCollector(
            config={"cache_path": self.no_cache}, fetcher=fetcher
        )

        self.assertEqual(collector.collect(self.source), [])
        fetcher.assert_not_called()
        self.assertEqual(
            collector.last_status["failed_reason"],
            GqGroomingCollector.LIVE_REJECTION_REASON,
        )
        self.assertEqual(
            collector.last_status["collection_method"],
            GqGroomingCollector.NO_DATA_METHOD,
        )

    def test_network_failure_uses_fresh_bounded_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            cache_path = Path(directory) / "gq_grooming.json"
            cache_path.write_text(
                json.dumps(
                    {
                        "updated_at": datetime.now().astimezone().isoformat(),
                        "items": [
                            {
                                "title": "캐시 남성 스킨케어 기사",
                                "link": "https://www.gqkorea.co.kr/2026/07/01/남성-스킨케어/",
                                "rank_position": 1,
                                "section_category": "grooming",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            collector = GqGroomingCollector(
                max_items=1,
                config={"allow_live_fetch": True, "cache_path": str(cache_path)},
                fetcher=lambda _url: (_ for _ in ()).throw(OSError("offline")),
            )

            items = collector.collect(self.source)

        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["is_fallback"])
        self.assertTrue(collector.last_status["used_cache"])
        self.assertEqual(
            collector.last_status["collection_method"],
            GqGroomingCollector.CACHE_METHOD,
        )


if __name__ == "__main__":
    unittest.main()
