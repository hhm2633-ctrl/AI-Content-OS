import copy
import json
import os
import shutil
import unittest
from unittest import mock
import socket
import urllib.request

from modules.source_intake.daily_collection_executor import execute_daily_shallow_collection


class FakeSourceManager:
    def __init__(self):
        self.calls = []

    def _collect_naver_news(self, source):
        self.calls.append(("naver_news", source["source_id"]))
        return [{"keyword": "domestic issue", "source_id": "naver_news"}]

    def _collect_nate_pann(self, source):
        self.calls.append(("nate_pann", source["source_id"]))
        return [{"keyword": "community issue", "source_id": "nate_pann"}]

    def _collect_fmkorea(self, source):
        self.calls.append(("fmkorea", source["source_id"]))
        return []

    def _collect_bobaedream(self, source):
        self.calls.append(("bobaedream", source["source_id"]))
        return [{"keyword": "road issue", "source_id": "bobaedream"}]


class ExplodingSourceManager(FakeSourceManager):
    def _collect_naver_news(self, source):
        raise RuntimeError("network exploded")


class TestDailySourceCollectionExecutor(unittest.TestCase):
    def setUp(self):
        self.today = "2099-01-03"
        self.output_root = os.path.join("storage", "_tmp_daily_executor")
        if os.path.exists(self.output_root):
            shutil.rmtree(self.output_root, ignore_errors=True)
        self._socket_connect_patch = mock.patch(
            "socket.create_connection",
            side_effect=OSError("network disabled in executor tests"),
        )
        self._socket_bind_patch = mock.patch(
            "socket.socket.connect",
            side_effect=OSError("network disabled in executor tests"),
        )
        self._urlopen_patch = mock.patch(
            "urllib.request.urlopen",
            side_effect=RuntimeError("network disabled in executor tests"),
        )
        self._socket_connect_patch.start()
        self._socket_bind_patch.start()
        self._urlopen_patch.start()

    def tearDown(self):
        self._urlopen_patch.stop()
        self._socket_bind_patch.stop()
        self._socket_connect_patch.stop()
        if os.path.exists(self.output_root):
            shutil.rmtree(self.output_root, ignore_errors=True)

    @staticmethod
    def _plan_for_sources(sources, lane_id):
        return {
            "plan_status": "ok",
            "lanes": [
                {
                    "lane_id": lane_id,
                    "shallow_profiles": sources,
                }
            ],
        }

    def test_executes_only_existing_collectors_and_writes_json(self):
        manager = FakeSourceManager()
        plan = self._plan_for_sources(
            ["naver_news", "nate_pann", "fmkorea", "bobaedream"], "lane_exec"
        )
        with mock.patch(
            "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
            return_value=plan,
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
                source_manager=manager,
            )

        self.assertEqual(result["status"], "completed")
        self.assertTrue(os.path.isfile(result["output_path"]))
        self.assertIn(("naver_news", "naver_news"), manager.calls)
        self.assertIn(("nate_pann", "nate_pann"), manager.calls)
        self.assertIn(("fmkorea", "fmkorea"), manager.calls)
        self.assertIn(("bobaedream", "bobaedream"), manager.calls)

        with open(result["output_path"], "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        self.assertEqual(loaded["schema_version"], "daily_shallow_collection_v1")
        self.assertEqual(loaded["item_count"], 3)
        self.assertIn("quality_summary", loaded)
        self.assertEqual(
            loaded["quality_summary"]["schema_version"],
            "collection_quality_summary_v1",
        )
        self.assertFalse(loaded["quality_summary"]["cardnews_readiness_claimed"])
        self.assertIn("source_agreement_summary", loaded)
        self.assertEqual(
            loaded["source_agreement_summary"]["source_agreement_version"],
            "source_agreement_v1",
        )

    def test_collects_daum_news_and_news1_via_direct_factories_without_network(self):
        collected = []

        class FakeDaumCollector:
            def __init__(self, *args, **kwargs):
                collected.append(("daum", "init"))

            def collect(self, source):
                collected.append(("daum", source["source_id"]))
                return [
                    {
                        "keyword": "다음 뉴스 샘플",
                        "source_id": source["source_id"],
                    }
                ]

        class FakeNews1Collector:
            def __init__(self, *args, **kwargs):
                collected.append(("news1", "init"))

            def collect(self, source):
                collected.append(("news1", source["source_id"]))
                return [
                    {
                        "keyword": "뉴스원 샘플",
                        "source_id": source["source_id"],
                    }
                ]

        plan = self._plan_for_sources(
            ["daum_news", "news1"], "lane_direct_factories"
        )

        with (
            mock.patch(
                "modules.source_intake.daily_collection_executor.DaumNewsCollector",
                return_value=FakeDaumCollector(),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.News1Collector",
                return_value=FakeNews1Collector(),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
                return_value=plan,
            ),
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
            )

        source_results = {
            item["source_id"]: item for item in result["source_results"]
        }

        self.assertEqual(result["item_count"], 2)
        self.assertEqual(source_results["daum_news"]["source_id"], "daum_news")
        self.assertEqual(source_results["news1"]["source_id"], "news1")
        self.assertFalse(source_results["daum_news"]["skipped"])
        self.assertFalse(source_results["news1"]["skipped"])
        self.assertEqual(result["source_results"][0]["count"], 1)
        self.assertTrue(("daum", "daum_news") in collected)
        self.assertTrue(("news1", "news1") in collected)

    def test_manager_methods_precede_direct_factories(self):
        collected = []

        class ManagerWithMethods:
            def _collect_daum_news(self, source):
                collected.append(("manager", "daum_news"))
                return [{"keyword": "manager daum", "source_id": "daum_news"}]

            def _collect_news1(self, source):
                collected.append(("manager", "news1"))
                return [{"keyword": "manager news1", "source_id": "news1"}]

            def _collect_yonhap(self, source):
                collected.append(("manager", "yonhap"))
                return [{"keyword": "manager yonhap", "source_id": "yonhap"}]

        plan = self._plan_for_sources(
            ["daum_news", "news1", "yonhap"], "lane_precedence"
        )

        with (
            mock.patch("modules.source_intake.daily_collection_executor.DaumNewsCollector") as daum,
            mock.patch("modules.source_intake.daily_collection_executor.News1Collector") as news1,
            mock.patch("modules.source_intake.daily_collection_executor.YonhapCollector") as yonhap,
            mock.patch(
                "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
                return_value=plan,
            ),
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
                source_manager=ManagerWithMethods(),
            )

        source_results = {
            item["source_id"]: item for item in result["source_results"]
        }
        self.assertEqual(result["item_count"], 3)
        self.assertEqual(source_results["daum_news"]["count"], 1)
        self.assertEqual(source_results["news1"]["count"], 1)
        self.assertEqual(source_results["yonhap"]["count"], 1)
        self.assertEqual(
            collected,
            [
                ("manager", "daum_news"),
                ("manager", "news1"),
                ("manager", "yonhap"),
            ],
        )
        self.assertEqual(daum.call_count, 0)
        self.assertEqual(news1.call_count, 0)
        self.assertEqual(yonhap.call_count, 0)

    def test_collects_yonhap_via_direct_factory_without_network(self):
        calls = []

        class FakeYonhapCollector:
            def __init__(self, *args, **kwargs):
                calls.append(("init", kwargs.get("config", {})))
                self.last_status = {
                    "collection_method": "yonhap_fixture",
                    "failed_reason": "",
                    "used_cache": False,
                    "retry_count": 0,
                }

            def collect(self, source):
                calls.append(("collect", source["source_id"]))
                return [
                    {
                        "keyword": "연합뉴스 샘플",
                        "source_id": source["source_id"],
                        "collection_method": "yonhap_fixture",
                    }
                ]

        plan = self._plan_for_sources(["yonhap"], "news_society_economy")
        with (
            mock.patch(
                "modules.source_intake.daily_collection_executor.YonhapCollector",
                FakeYonhapCollector,
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
                return_value=plan,
            ),
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
            )

        self.assertEqual(result["item_count"], 1)
        self.assertEqual(result["items"][0]["source_id"], "yonhap")
        self.assertEqual(
            result["items"][0]["source_lane_id"], "news_society_economy"
        )
        self.assertEqual(result["source_results"][0]["source_id"], "yonhap")
        self.assertTrue(result["source_results"][0]["attempted"])
        self.assertTrue(result["source_results"][0]["success"])
        self.assertFalse(result["source_results"][0]["skipped"])
        self.assertEqual(result["source_results"][0]["count"], 1)
        self.assertEqual(
            result["source_results"][0]["collection_method"], "yonhap_fixture"
        )
        self.assertFalse(result["source_results"][0]["used_cache"])
        self.assertTrue(calls[0][1]["allow_live_fetch"])
        self.assertEqual(calls[-1], ("collect", "yonhap"))

    def test_direct_factories_map_public_live_flag_to_internal_collector_gates(self):
        class FakeCapabilityMap:
            def get(self, source_id):
                return {
                    "source_id": source_id,
                    "url": "https://example.com/",
                    "source_type": "news",
                    "access_status": "ok",
                    "collector_allowed": True,
                    "allow_live_fetch": True,
                }

        observed = {}

        class FakeNateCollector:
            def __init__(self, *args, **kwargs):
                observed["nate"] = kwargs["config"]
                self.last_status = {"collection_method": "fixture", "used_cache": False}

            def collect(self, source):
                return [{"title": "nate", "source_id": source["source_id"]}]

        class FakeYonhapCollector:
            def __init__(self, *args, **kwargs):
                observed["yonhap"] = kwargs["config"]
                self.last_status = {"collection_method": "fixture", "used_cache": False}

            def collect(self, source):
                return [{"title": "yonhap", "source_id": source["source_id"]}]

        plan = self._plan_for_sources(
            ["nate_news_rank", "yonhap"], "news_society_economy"
        )
        with (
            mock.patch(
                "modules.source_intake.daily_collection_executor.NateNewsRankCollector",
                FakeNateCollector,
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.YonhapCollector",
                FakeYonhapCollector,
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
                return_value=plan,
            ),
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
                capability_map=FakeCapabilityMap(),
            )

        self.assertEqual(result["item_count"], 2)
        self.assertTrue(observed["nate"]["live_collection_enabled"])
        self.assertTrue(observed["yonhap"]["allow_live_fetch"])

    def test_direct_zero_result_preserves_real_collector_diagnostic(self):
        class EmptyYonhapCollector:
            def __init__(self, *args, **kwargs):
                self.last_status = {}

            def collect(self, source):
                self.last_status = {
                    "collection_method": "yonhap_no_data",
                    "failed_reason": "connection_reset",
                    "fallback_reason": "connection_reset",
                    "final_error_type": "connection_reset",
                    "used_cache": False,
                    "retry_count": 2,
                    "service_diagnostic": {
                        "service": "yonhap",
                        "status": "fallback_used",
                        "error_type": "connection_reset",
                    },
                }
                return []

        plan = self._plan_for_sources(["yonhap"], "news_society_economy")
        with (
            mock.patch(
                "modules.source_intake.daily_collection_executor.YonhapCollector",
                EmptyYonhapCollector,
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
                return_value=plan,
            ),
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
            )

        source_result = result["source_results"][0]
        self.assertFalse(source_result["success"])
        self.assertEqual(source_result["failed_reason"], "connection_reset")
        self.assertEqual(source_result["collection_method"], "yonhap_no_data")
        self.assertEqual(source_result["retry_count"], 2)
        self.assertEqual(
            source_result["service_diagnostic"]["error_type"], "connection_reset"
        )

    def test_collects_dcinside_and_ppomppu_via_direct_factories_without_network(self):
        calls = []

        class FakeCollector:
            def __init__(self, source_id, *args, **kwargs):
                self.source_id = source_id
                calls.append(("init", source_id))

            def collect(self, source):
                calls.append(("collect", source["source_id"]))
                return [
                    {
                        "keyword": f"{self.source_id} fixture",
                        "source_id": source["source_id"],
                    }
                ]

        plan = self._plan_for_sources(
            ["dcinside", "ppomppu"], "dopamine_community"
        )
        with (
            mock.patch(
                "modules.source_intake.daily_collection_executor.DcinsideCollector",
                side_effect=lambda *args, **kwargs: FakeCollector(
                    "dcinside", *args, **kwargs
                ),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.PpomppuCollector",
                side_effect=lambda *args, **kwargs: FakeCollector(
                    "ppomppu", *args, **kwargs
                ),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
                return_value=plan,
            ),
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
            )

        self.assertEqual(result["item_count"], 2)
        self.assertEqual(
            [entry["source_id"] for entry in result["source_results"]],
            ["dcinside", "ppomppu"],
        )
        self.assertEqual(
            [item["source_lane_id"] for item in result["items"]],
            ["dopamine_community", "dopamine_community"],
        )
        self.assertIn(("collect", "dcinside"), calls)
        self.assertIn(("collect", "ppomppu"), calls)

    def test_manager_methods_precede_dcinside_and_ppomppu_direct_factories(self):
        calls = []

        class CommunityManager:
            def _collect_dcinside(self, source):
                calls.append(("manager", "dcinside"))
                return [{"keyword": "dc manager", "source_id": "dcinside"}]

            def _collect_ppomppu(self, source):
                calls.append(("manager", "ppomppu"))
                return [{"keyword": "pp manager", "source_id": "ppomppu"}]

        plan = self._plan_for_sources(
            ["dcinside", "ppomppu"], "dopamine_community"
        )
        with (
            mock.patch(
                "modules.source_intake.daily_collection_executor.DcinsideCollector"
            ) as dcinside,
            mock.patch(
                "modules.source_intake.daily_collection_executor.PpomppuCollector"
            ) as ppomppu,
            mock.patch(
                "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
                return_value=plan,
            ),
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
                source_manager=CommunityManager(),
            )

        self.assertEqual(result["item_count"], 2)
        self.assertEqual(
            calls,
            [("manager", "dcinside"), ("manager", "ppomppu")],
        )
        self.assertEqual(dcinside.call_count, 0)
        self.assertEqual(ppomppu.call_count, 0)

    def test_collects_ruliweb_and_dogdrip_via_direct_factories_without_network(self):
        calls = []

        class FakeCollector:
            def __init__(self, source_id, *args, **kwargs):
                self.source_id = source_id
                calls.append(("init", source_id))

            def collect(self, source):
                calls.append(("collect", source["source_id"]))
                return [
                    {
                        "keyword": f"{self.source_id} fixture",
                        "source_id": source["source_id"],
                    }
                ]

        plan = self._plan_for_sources(
            ["ruliweb", "dogdrip"], "dopamine_community"
        )
        with (
            mock.patch(
                "modules.source_intake.daily_collection_executor.RuliwebCollector",
                side_effect=lambda *args, **kwargs: FakeCollector(
                    "ruliweb", *args, **kwargs
                ),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.DogdripCollector",
                side_effect=lambda *args, **kwargs: FakeCollector(
                    "dogdrip", *args, **kwargs
                ),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
                return_value=plan,
            ),
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
            )

        self.assertEqual(result["item_count"], 2)
        self.assertEqual(
            [entry["source_id"] for entry in result["source_results"]],
            ["ruliweb", "dogdrip"],
        )
        self.assertIn(("collect", "ruliweb"), calls)
        self.assertIn(("collect", "dogdrip"), calls)

    def test_collects_account_c_specialists_via_direct_factories(self):
        calls = []

        class FakeCollector:
            def __init__(self, source_id, *args, **kwargs):
                self.source_id = source_id

            def collect(self, source):
                calls.append(source["source_id"])
                return [
                    {
                        "title": f"{self.source_id} Account C fixture",
                        "link": f"https://example.com/{self.source_id}",
                        "source_id": source["source_id"],
                        "rank_position": 1,
                    }
                ]

        plan = self._plan_for_sources(
            [
                "fashionn",
                "musinsa_monthly_ranking",
                "glowpick_ranking",
                "musinsa_beauty",
                "oliveyoung_ranking",
                "musinsa_boutique",
            ],
            "beauty_fashion",
        )
        with (
            mock.patch(
                "modules.source_intake.daily_collection_executor.FashionNCollector",
                side_effect=lambda *args, **kwargs: FakeCollector("fashionn"),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.MusinsaMonthlyRankingCollector",
                side_effect=lambda *args, **kwargs: FakeCollector("musinsa_monthly_ranking"),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.GlowpickRankingCollector",
                side_effect=lambda *args, **kwargs: FakeCollector("glowpick_ranking"),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.MusinsaBeautyCollector",
                side_effect=lambda *args, **kwargs: FakeCollector("musinsa_beauty"),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.OliveYoungRankingCollector",
                side_effect=lambda *args, **kwargs: FakeCollector("oliveyoung_ranking"),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.MusinsaBoutiqueCollector",
                side_effect=lambda *args, **kwargs: FakeCollector("musinsa_boutique"),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
                return_value=plan,
            ),
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
            )

        self.assertEqual(result["item_count"], 6)
        self.assertEqual(
            calls,
            [
                "fashionn",
                "musinsa_monthly_ranking",
                "glowpick_ranking",
                "musinsa_beauty",
                "oliveyoung_ranking",
                "musinsa_boutique",
            ],
        )
        self.assertTrue(
            all(item["source_lane_id"] == "beauty_fashion" for item in result["items"])
        )
        by_source = {item["source_id"]: item for item in result["items"]}
        self.assertEqual(
            by_source["fashionn"]["topic_selection_role"], "primary_editorial"
        )
        self.assertTrue(by_source["fashionn"]["editorial_topic_eligible"])
        self.assertEqual(
            by_source["musinsa_monthly_ranking"]["account_c_vertical"],
            "fashion",
        )
        self.assertFalse(
            by_source["oliveyoung_ranking"]["editorial_topic_eligible"]
        )
        self.assertEqual(
            by_source["glowpick_ranking"]["account_c_source_role"],
            "consumer_review_evidence",
        )
        self.assertTrue(by_source["musinsa_boutique"]["post_selection_only"])

    def test_collects_account_c_direct_editorial_replacements(self):
        calls = []

        class FakeCollector:
            def __init__(self, source_id, config):
                self.source_id = source_id
                self.config = config

            def collect(self, source):
                calls.append((self.source_id, self.config.get("allow_live_fetch")))
                return [{
                    "title": f"{self.source_id} editorial fixture",
                    "link": f"https://example.com/{self.source_id}",
                    "source_id": self.source_id,
                    "rank_position": 1,
                }]

        source_ids = ["fashionbiz", "apparelnews", "cosin"]
        plan = self._plan_for_sources(source_ids, "beauty_fashion")
        with (
            mock.patch(
                "modules.source_intake.daily_collection_executor.FashionBizCollector",
                side_effect=lambda *args, **kwargs: FakeCollector("fashionbiz", kwargs["config"]),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.ApparelNewsCollector",
                side_effect=lambda *args, **kwargs: FakeCollector("apparelnews", kwargs["config"]),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.CosinCollector",
                side_effect=lambda *args, **kwargs: FakeCollector("cosin", kwargs["config"]),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
                return_value=plan,
            ),
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
            )

        self.assertEqual(result["item_count"], 3)
        self.assertEqual([source_id for source_id, _ in calls], source_ids)
        self.assertTrue(all(live_enabled for _, live_enabled in calls))
        by_source = {item["source_id"]: item for item in result["items"]}
        self.assertEqual(by_source["fashionbiz"]["account_c_vertical"], "fashion")
        self.assertEqual(by_source["apparelnews"]["topic_selection_role"], "primary_editorial")
        self.assertTrue(by_source["cosin"]["editorial_topic_eligible"])
        self.assertEqual(by_source["cosin"]["topic_selection_role"], "primary_editorial")

    def test_collects_account_c_consumer_beauty_editorials_with_audience_roles(self):
        calls = []

        class FakeCollector:
            def __init__(self, source_id, config):
                self.source_id = source_id
                self.config = config

            def collect(self, source):
                calls.append((self.source_id, self.config.get("allow_live_fetch")))
                return [{
                    "title": f"{self.source_id} seasonal beauty fixture",
                    "link": f"https://example.com/{self.source_id}",
                    "source_id": self.source_id,
                    "rank_position": 1,
                }]

        source_ids = ["allure_beauty", "vogue_beauty", "wkorea_beauty", "gq_grooming"]
        plan = self._plan_for_sources(source_ids, "beauty_fashion")
        with (
            mock.patch(
                "modules.source_intake.daily_collection_executor.AllureBeautyCollector",
                side_effect=lambda *args, **kwargs: FakeCollector("allure_beauty", kwargs["config"]),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.VogueBeautyCollector",
                side_effect=lambda *args, **kwargs: FakeCollector("vogue_beauty", kwargs["config"]),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.WKoreaBeautyCollector",
                side_effect=lambda *args, **kwargs: FakeCollector("wkorea_beauty", kwargs["config"]),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.GqGroomingCollector",
                side_effect=lambda *args, **kwargs: FakeCollector("gq_grooming", kwargs["config"]),
            ),
            mock.patch(
                "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
                return_value=plan,
            ),
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
            )

        self.assertEqual(result["item_count"], 4)
        self.assertEqual([source_id for source_id, _ in calls], source_ids)
        self.assertTrue(all(live_enabled for _, live_enabled in calls))
        by_source = {item["source_id"]: item for item in result["items"]}
        self.assertTrue(all(item["editorial_topic_eligible"] for item in by_source.values()))
        self.assertTrue(all(
            item["topic_selection_role"] == "primary_consumer_editorial"
            for item in by_source.values()
        ))
        self.assertEqual(by_source["allure_beauty"]["account_c_audience"], "women_general")
        self.assertEqual(by_source["gq_grooming"]["account_c_audience"], "men")
        self.assertIn("makeup", by_source["vogue_beauty"]["beauty_topic_categories"])
        self.assertIn("shaving", by_source["gq_grooming"]["beauty_topic_categories"])

    def test_manager_methods_precede_ruliweb_and_dogdrip_direct_factories(self):
        calls = []

        class CommunityManager:
            def _collect_ruliweb(self, source):
                calls.append(("manager", "ruliweb"))
                return [{"keyword": "ruli manager", "source_id": "ruliweb"}]

            def _collect_dogdrip(self, source):
                calls.append(("manager", "dogdrip"))
                return [{"keyword": "dog manager", "source_id": "dogdrip"}]

        plan = self._plan_for_sources(
            ["ruliweb", "dogdrip"], "dopamine_community"
        )
        with (
            mock.patch(
                "modules.source_intake.daily_collection_executor.RuliwebCollector"
            ) as ruliweb,
            mock.patch(
                "modules.source_intake.daily_collection_executor.DogdripCollector"
            ) as dogdrip,
            mock.patch(
                "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
                return_value=plan,
            ),
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
                source_manager=CommunityManager(),
            )

        self.assertEqual(result["item_count"], 2)
        self.assertEqual(
            calls,
            [("manager", "ruliweb"), ("manager", "dogdrip")],
        )
        self.assertEqual(ruliweb.call_count, 0)
        self.assertEqual(dogdrip.call_count, 0)

    def test_sources_without_collectors_are_skipped_not_failed(self):
        plan = self._plan_for_sources(["unknown_source"], "lane_unknown")
        with mock.patch(
            "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
            return_value=plan,
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
                source_manager=FakeSourceManager(),
            )
        skipped = [
            source for source in result["source_results"]
            if source.get("skip_reason") == "collector_not_implemented"
        ]

        self.assertTrue(skipped)
        self.assertTrue(all(source["skipped"] for source in skipped))

    def test_collector_exception_is_captured_per_source(self):
        plan = self._plan_for_sources(["naver_news"], "lane_naver")
        with mock.patch(
            "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
            return_value=plan,
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
                source_manager=ExplodingSourceManager(),
            )
        naver_result = [
            source for source in result["source_results"]
            if source["source_id"] == "naver_news"
        ][0]

        self.assertFalse(naver_result["success"])
        self.assertIn("network exploded", naver_result["error"])
        self.assertEqual(result["status"], "completed")

    def test_unknown_lane_fails_closed_but_still_writes(self):
        plan = {"plan_status": "empty_plan", "lanes": []}
        with mock.patch(
            "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
            return_value=plan,
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
                source_manager=FakeSourceManager(),
            )

        self.assertEqual(result["plan"]["plan_status"], "empty_plan")
        self.assertEqual(result["source_results"], [])
        self.assertTrue(os.path.isfile(result["output_path"]))

    def test_moneytoday_collects_from_shallow_plan_once_with_fixture_items_and_diagnostics(self):
        fixture_path = os.path.join(
            "external_workclaude",
            "source_collector_work_orders",
            "2026-07-14",
            "MONEYTODAY_FIXTURE_CONTRACT.json",
        )
        with open(fixture_path, "r", encoding="utf-8") as handle:
            fixture_contract = json.load(handle)

        host = fixture_contract["canonical_host"].replace("https://", "")
        item = {
            "keyword": "샘플 시장 브리핑",
            "link": f"{fixture_contract['canonical_host']}/economy/2026/07/15/2026071500000000001",
            "summary": "",
            "publisher": "머니투데이",
            "published_at": "2026.07.15 09:12",
            "query": "",
            "source_id": "moneytoday",
            "source_name": fixture_contract["site_name"],
            "source_type": "news",
            "tier": 1,
            "weight": 22,
            "base_score": 117,
            "trend_reason": "머니투데이 수집(moneytoday_sitemap)",
            "collection_method": "moneytoday_sitemap",
            "is_fallback": False,
            "collected_at": "2026-07-15T09:12:34.567890",
            "article_id": "2026071500000000001",
            "category": "economy",
            "reporter": "",
            "rank_position": None,
            "service_diagnostic": {
                "service": "moneytoday",
                "status": "ok",
                "error_type": "",
                "safe_message": "",
                "api_key_present": None,
            },
        }

        class MoneytodayFakeManager:
            def __init__(self):
                self.calls = []

            def _collect_moneytoday(self, source):
                self.calls.append(source["source_id"])
                return [
                    dict(item, source_lane_id="lane_moneytoday"),
                ]

        plan = {
            "plan_status": "ok",
            "lanes": [
                {
                    "lane_id": "lane_moneytoday",
                    "shallow_profiles": ["moneytoday"],
                }
            ],
        }

        capability_map = {
            "moneytoday": {
                "name": fixture_contract["site_name"],
                "source_type": "news",
                "tier": 1,
                "weight": 22,
                "url": fixture_contract["canonical_host"],
                "canonical_host": host,
            }
        }
        manager = MoneytodayFakeManager()

        with mock.patch(
            "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
            return_value=plan,
        ):
            result = execute_daily_shallow_collection(
                today=self.today,
                output_root=self.output_root,
                source_manager=manager,
                capability_map=capability_map,
            )

        self.assertEqual(manager.calls, ["moneytoday"])
        self.assertEqual(result["item_count"], 1)
        self.assertEqual(result["items"][0]["keyword"], "샘플 시장 브리핑")
        self.assertEqual(result["items"][0]["collection_method"], "moneytoday_sitemap")
        self.assertEqual(result["items"][0]["service_diagnostic"]["status"], "ok")
        moneytoday_result = [
            source for source in result["source_results"]
            if source["source_id"] == "moneytoday"
        ][0]
        self.assertFalse(moneytoday_result["skipped"])
        self.assertTrue(moneytoday_result["success"])

    def test_sequential_calls_do_not_accumulate_items_or_mutate_plan_inputs(self):
        first_plan = {
            "plan_status": "ok",
            "lanes": [
                {
                    "lane_id": "lane_alpha",
                    "shallow_profiles": ["nate_pann"],
                }
            ],
        }
        second_plan = {
            "plan_status": "ok",
            "lanes": [
                {
                    "lane_id": "lane_beta",
                    "shallow_profiles": ["bobaedream"],
                }
            ],
        }
        expected_first_plan = copy.deepcopy(first_plan)
        expected_second_plan = copy.deepcopy(second_plan)

        class SequentialManager:
            def __init__(self):
                self.calls = []

            def _collect_nate_pann(self, source):
                self.calls.append(source["source_id"])
                return [{"keyword": "community issue", "source_id": "nate_pann"}]

            def _collect_bobaedream(self, source):
                self.calls.append(source["source_id"])
                return [{"keyword": "road issue", "source_id": "bobaedream"}]

        manager = SequentialManager()

        with mock.patch(
            "modules.source_intake.daily_collection_executor.build_daily_collection_plan",
            side_effect=[first_plan, second_plan],
        ):
            first = execute_daily_shallow_collection(
                account_profiles=["news_society_economy"],
                today=self.today,
                output_root=self.output_root,
                source_manager=manager,
            )
            second = execute_daily_shallow_collection(
                account_profiles=["news_society_economy"],
                today=self.today,
                output_root=self.output_root,
                source_manager=manager,
            )

        self.assertEqual(first["item_count"], 1)
        self.assertEqual(second["item_count"], 1)
        self.assertEqual(first["source_results"][0]["source_id"], "nate_pann")
        self.assertEqual(second["source_results"][0]["source_id"], "bobaedream")
        self.assertEqual(first["items"][0]["source_id"], "nate_pann")
        self.assertEqual(second["items"][0]["source_id"], "bobaedream")
        self.assertEqual(manager.calls, ["nate_pann", "bobaedream"])
        self.assertEqual(first_plan, expected_first_plan)
        self.assertEqual(second_plan, expected_second_plan)
        self.assertEqual(first["source_results"][0]["lane_id"], "lane_alpha")
        self.assertEqual(second["items"][0]["source_lane_id"], "lane_beta")


if __name__ == "__main__":
    unittest.main()
