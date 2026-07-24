import unittest

from modules.design_learning.reference_recipe_selector import (
    ReferenceRecipeSelector,
)


def _blueprint(blueprint_id="bp-news-cover"):
    return {
        "blueprint_id": blueprint_id,
        "blueprint_version": "1.0",
        "geometry_hash": "geometry-hash",
        "canvas": {"width": 1080, "height": 1350},
        "regions": [
            {
                "region_id": "media",
                "role": "primary_media",
                "box_norm": [0.0, 0.0, 1.0, 1.0],
            },
            {
                "region_id": "headline",
                "role": "headline",
                "box_norm": [0.06, 0.68, 0.88, 0.2],
            },
        ],
    }


def _specimen(reference_id="owner-ref-1"):
    return {
        "reference_id": reference_id,
        "blueprint_id": "bp-news-cover",
        "approval_status": "owner_approved",
        "owner_approval_receipt_id": "owner-receipt-1",
        "reference_only": False,
        "measured_performance_claimed": False,
        "account_fit": ["news"],
        "slide_role_fit": ["hook"],
        "emotion_fit": ["warning"],
        "season_fit": ["summer"],
        "topic_fit": ["금융", "투자"],
        "media_requirements": {
            "min_count": 1,
            "max_count": 1,
            "aspects": ["portrait"],
        },
        "max_copy_char_count": 42,
    }


class ReferenceRecipeSelectorTest(unittest.TestCase):
    def setUp(self):
        self.selector = ReferenceRecipeSelector()
        self.context = {
            "account": "news",
            "slide_role": "hook",
            "emotion": "warning",
            "season": "summer",
            "topic_tokens": ["금융", "투자"],
            "media_count": 1,
            "media_aspect": "portrait",
            "copy_char_count": 20,
        }

    def test_selects_one_complete_reference_without_field_mixing(self):
        result = self.selector.select(
            specimens=[_specimen()],
            blueprints={"bp-news-cover": _blueprint()},
            context=self.context,
        )

        self.assertEqual("selected", result["status"])
        self.assertEqual("owner-ref-1", result["primary_reference_id"])
        self.assertEqual("bp-news-cover", result["primary_blueprint_id"])
        self.assertFalse(result["field_mixing_allowed"])
        self.assertEqual("geometry-hash", result["geometry_hash"])

    def test_rejects_unapproved_specimen(self):
        specimen = _specimen()
        specimen["approval_status"] = "candidate"
        result = self.selector.select(
            specimens=[specimen],
            blueprints={"bp-news-cover": _blueprint()},
            context=self.context,
        )

        self.assertEqual("blocked", result["status"])
        self.assertEqual(
            "owner_approval_required",
            result["rejection_reasons"][0]["reason_code"],
        )

    def test_rejects_incomplete_geometry(self):
        result = self.selector.select(
            specimens=[_specimen()],
            blueprints={"bp-news-cover": {"blueprint_id": "bp-news-cover"}},
            context=self.context,
        )

        self.assertEqual("blocked", result["status"])
        self.assertEqual(
            "complete_geometry_blueprint_required",
            result["rejection_reasons"][0]["reason_code"],
        )

    def test_rejects_media_and_copy_mismatch_before_ranking(self):
        context = dict(self.context)
        context["media_count"] = 0
        context["copy_char_count"] = 90
        result = self.selector.select(
            specimens=[_specimen()],
            blueprints={"bp-news-cover": _blueprint()},
            context=context,
        )

        self.assertEqual("blocked", result["status"])
        self.assertEqual(
            "media_contract_incompatible",
            result["rejection_reasons"][0]["reason_code"],
        )

    def test_selection_is_deterministic(self):
        specimens = [_specimen("owner-ref-b"), _specimen("owner-ref-a")]
        first = self.selector.select(
            specimens=specimens,
            blueprints={"bp-news-cover": _blueprint()},
            context=self.context,
        )
        second = self.selector.select(
            specimens=list(reversed(specimens)),
            blueprints={"bp-news-cover": _blueprint()},
            context=self.context,
        )

        self.assertEqual("owner-ref-a", first["primary_reference_id"])
        self.assertEqual(first["selection_hash"], second["selection_hash"])

    def test_detail_reference_accepts_semantic_news_slide_roles(self):
        specimen = _specimen()
        specimen["slide_role_fit"] = ["card", "detail", "source_context"]
        context = dict(self.context)
        context["slide_role"] = "key_number"

        result = self.selector.select(
            specimens=[specimen],
            blueprints={"bp-news-cover": _blueprint()},
            context=context,
        )

        self.assertEqual("selected", result["status"])
        self.assertEqual(1.0, result["selection_reasons"]["slide_role_match"])

    def test_cover_reference_does_not_match_detail_slide(self):
        context = dict(self.context)
        context["slide_role"] = "meaning_next_action"

        result = self.selector.select(
            specimens=[_specimen()],
            blueprints={"bp-news-cover": _blueprint()},
            context=context,
        )

        self.assertEqual("blocked", result["status"])
        self.assertEqual(
            "slide_role_incompatible",
            result["rejection_reasons"][0]["reason_code"],
        )


if __name__ == "__main__":
    unittest.main()
