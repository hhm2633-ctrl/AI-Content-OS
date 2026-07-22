import copy
import unittest

from scripts.build_selected_flow_production_packages import (
    build_packages_from_selected_flow,
)


def _plan(count):
    return {
        "schema_version": "selected_candidate_production_plan_v1",
        "status": "production_plan_ready",
        "candidate_id": "A-1",
        "account": "A",
        "category": "news",
        "title": "가변 뉴스",
        "slide_count": count,
        "slide_plan": [
            {"slide_role": "cover" if page == 1 else "source_context", "media_type": "editorial", "asset_refs": []}
            for page in range(1, count + 1)
        ],
        "copy_plan": {"source_credit": ["https://example.com/source"], "feed_body": "별도 캡션"},
        "asset_inventory": [{
            "asset_id": "source-1",
            "origin": "news",
            "asset_class": "source_evidence",
            "locator": "C:/approved/source.jpg",
            "source_url": "https://example.com/source",
            "rights_status": "licensed",
        }],
        "commerce": {"mode": "none", "required_for_readiness": False},
    }


class BuildSelectedFlowProductionPackagesTest(unittest.TestCase):
    def test_one_and_twenty_slide_plans_reach_pending_package_without_render(self):
        for count in (1, 20):
            with self.subTest(count=count):
                plan = _plan(count)
                render = {
                    "schema_version": "selected_candidate_render_input_v1",
                    "status": "renderer_input_ready",
                    "renderer_ready": True,
                    "render_executed": False,
                    "publish_executed": False,
                    "full_plan_preserved": copy.deepcopy(plan),
                }
                story = {
                    "candidate_id": "A-1",
                    "story": {"summary": "근거 기반 요약"},
                    "slide_copy": [
                        {"page": page, "headline": f"제목 {page}", "body": f"본문 {page}"}
                        for page in range(1, count + 1)
                    ],
                    "feed_caption": "별도 피드 캡션",
                }
                result = build_packages_from_selected_flow(
                    {"production_plans": [plan], "render_inputs": [render]},
                    {"stories": [story]},
                )

                self.assertEqual("pending", result["status"])
                self.assertEqual(1, result["pending_count"])
                self.assertEqual(count, len(result["packages"][0]["slides"]))
                self.assertFalse(result["render_executed"])
                self.assertFalse(result["publishing_executed"])


if __name__ == "__main__":
    unittest.main()
