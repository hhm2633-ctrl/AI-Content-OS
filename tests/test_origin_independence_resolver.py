import copy
import unittest

from modules.source_intake.origin_independence_resolver import resolve_origin_independence


class OriginIndependenceResolverTests(unittest.TestCase):
    def test_invalid_candidate_fails_closed_with_required_axes(self):
        result = resolve_origin_independence(None)
        self.assertEqual(result["status"], "closed")
        self.assertIsNone(result["origin_independence"]["score"])
        self.assertIsNone(result["distribution_spread"]["score"])

    def test_portal_without_publisher_is_distribution_only_and_origin_unknown(self):
        candidate = {"source_id": "naver_news", "link": "https://news.naver.com/main"}
        result = resolve_origin_independence(candidate)
        self.assertIsNone(result["origin_independence"]["score"])
        self.assertEqual(result["origin_independence"]["independent_origin_count"], 0)
        self.assertEqual(result["distribution_spread"]["source_ids"], ["naver_news"])
        self.assertTrue(any("portal_underlying_origin_unknown" in item for item in result["origin_independence"]["unresolved"]))

    def test_portal_uses_genuinely_supplied_underlying_publisher(self):
        result = resolve_origin_independence({
            "source_id": "daum_news",
            "publisher": "지역일보",
            "link": "https://v.daum.net/v/1",
        })
        self.assertEqual(result["origin_independence"]["origin_groups"], ["publisher:지역일보"])
        self.assertEqual(result["origin_independence"]["score"], 0.5)

    def test_portal_source_name_snapshot_does_not_inflate_real_publisher_origin(self):
        result = resolve_origin_independence({
            "source_id": "naver_news",
            "publisher": "지역일보",
            "source_agreement": {
                "sources": [
                    {"source_id": "naver_news", "publisher": "naver_news"},
                ]
            },
        })
        self.assertEqual(
            result["origin_independence"]["origin_groups"],
            ["publisher:지역일보"],
        )
        self.assertNotIn(
            "publisher:naver_news",
            result["origin_independence"]["origin_groups"],
        )

    def test_wire_reposts_collapse_to_single_origin_but_keep_distribution_spread(self):
        candidate = {
            "source_id": "naver_news",
            "publisher": "연합뉴스",
            "source_agreement": {
                "sources": [
                    {"source_id": "naver_news", "publisher": "연합뉴스"},
                    {"source_id": "daum_news", "publisher": "연합뉴스"},
                    {"source_id": "yonhap", "link": "https://www.yna.co.kr/view/1"},
                ]
            },
        }
        result = resolve_origin_independence(candidate)
        self.assertEqual(result["origin_independence"]["origin_groups"], ["yonhap"])
        self.assertEqual(result["origin_independence"]["independent_origin_count"], 1)
        self.assertEqual(result["distribution_spread"]["distribution_count"], 3)
        self.assertEqual(result["distribution_spread"]["score"], 1.0)

    def test_distinct_wire_origins_are_independent(self):
        result = resolve_origin_independence({
            "source_id": "yonhap",
            "source_refs": [
                {"source_id": "newsis", "link": "https://www.newsis.com/view/1"},
                {"source_id": "news1", "link": "https://www.news1.kr/article/1"},
            ],
        })
        self.assertEqual(result["origin_independence"]["origin_groups"], ["news1", "newsis", "yonhap"])
        self.assertEqual(result["origin_independence"]["score"], 1.0)

    def test_two_resolved_origins_use_conservative_independence_score(self):
        result = resolve_origin_independence({
            "source_id": "yonhap",
            "source_refs": [{"source_id": "newsis"}],
        })
        self.assertEqual(result["origin_independence"]["independent_origin_count"], 2)
        self.assertEqual(result["origin_independence"]["score"], 0.8)

    def test_community_reposts_do_not_become_factual_origins(self):
        result = resolve_origin_independence({
            "source_id": "fmkorea",
            "publisher": "fmkorea",
            "source_refs": [
                {"source_id": "theqoo"},
                {"source_id": "ruliweb"},
            ],
        })
        self.assertIsNone(result["origin_independence"]["score"])
        self.assertEqual(result["origin_independence"]["origin_groups"], [])
        self.assertEqual(result["distribution_spread"]["distribution_count"], 3)

    def test_community_citation_resolves_underlying_wire_only(self):
        result = resolve_origin_independence({
            "source_id": "dogdrip",
            "source_attribution": "기사 출처: 뉴스1",
        })
        self.assertEqual(result["origin_independence"]["origin_groups"], ["news1"])
        self.assertNotIn("dogdrip", result["origin_independence"]["origin_groups"])

    def test_news_repost_attribution_overrides_distributor_news_origin(self):
        result = resolve_origin_independence({
            "source_id": "hankyung_economy",
            "link": "https://www.hankyung.com/economy/article/1",
            "source_attribution": "이 기사는 연합뉴스를 인용했습니다.",
        })
        self.assertEqual(result["origin_independence"]["origin_groups"], ["yonhap"])
        self.assertNotIn("hankyung_economy", result["origin_independence"]["origin_groups"])

    def test_unapproved_sources_do_not_inflate_either_axis(self):
        result = resolve_origin_independence({
            "source_id": "google_news_kr",
            "publisher": "연합뉴스",
        })
        self.assertIsNone(result["origin_independence"]["score"])
        self.assertIsNone(result["distribution_spread"]["score"])
        self.assertEqual(result["origin_independence"]["origin_groups"], [])

    def test_resolution_is_deterministic_and_does_not_mutate_input(self):
        candidate = {
            "source_id": "nate_news_rank",
            "publisher": "뉴시스",
            "source_refs": [{"source_id": "edaily"}],
        }
        before = copy.deepcopy(candidate)
        first = resolve_origin_independence(candidate)
        second = resolve_origin_independence(candidate)
        self.assertEqual(first, second)
        self.assertEqual(candidate, before)

    def test_malformed_nested_metadata_fails_closed_without_exception(self):
        result = resolve_origin_independence({
            "source_id": "naver_news",
            "source_agreement": {"sources": "bad"},
            "source_refs": ["bad"],
        })
        self.assertIsNone(result["origin_independence"]["score"])
        self.assertTrue(result["origin_independence"]["unresolved"])


if __name__ == "__main__":
    unittest.main()
