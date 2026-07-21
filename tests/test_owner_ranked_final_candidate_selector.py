import unittest

from modules.source_intake.owner_ranked_final_candidate_selector import select_owner_ranked_final_candidates


class OwnerRankedFinalCandidateSelectorTests(unittest.TestCase):
    def _queue(self):
        requests = []
        for account in ("A", "B", "C"):
            for index in range(6):
                requests.append(
                    {
                        "request_id": f"owner_review:{account}-{index}",
                        "candidate_id": f"{account}-{index}",
                        "account": account,
                        "category": "뷰티" if account == "C" and index < 3 else f"cat-{index % 3}",
                        "title": f"{account} unique topic {index}",
                        "grade": "1" if index < 2 else "2",
                        "source_urls": [f"https://example.com/{account}/{index}"],
                        "requested_media": ["plan only"],
                    }
                )
        return {"schema_version": "owner_ranked_deep_dive_queue_v1", "requests": requests}

    def test_selects_four_per_account_and_preserves_all_candidates(self):
        queue = self._queue()
        result = select_owner_ranked_final_candidates(queue, {"schema_version": "brandconnect_second_stage.v1", "annotations": []})
        self.assertEqual(result["selected_count"], 12)
        self.assertEqual(result["not_selected_count"], 6)
        self.assertTrue(result["requested_media_is_plan_not_verified_availability"])
        for account in ("A", "B", "C"):
            self.assertEqual(result["accounts"][account]["selected_count"], 4)
            self.assertEqual(result["accounts"][account]["candidate_count"], 6)

    def test_commerce_is_positive_tiebreak_only_for_account_c(self):
        queue = self._queue()
        annotations = [
            {"candidate_id": "C-1", "commerce_status": "matched", "commerce_fit": 0.9, "matches": [{"title": "item"}]},
            {"candidate_id": "A-1", "commerce_status": "matched", "commerce_fit": 1.0, "matches": []},
        ]
        result = select_owner_ranked_final_candidates(queue, {"schema_version": "brandconnect_second_stage.v1", "annotations": annotations})
        c_selected = result["accounts"]["C"]["selected"]
        self.assertEqual(c_selected[0]["candidate_id"], "C-1")
        self.assertIn("natural_brandconnect_match_used_as_same_grade_tiebreak", c_selected[0]["selection_reasons"])
        self.assertEqual(result["accounts"]["A"]["selected"][0]["candidate_id"], "A-0")

    def test_soft_diversity_never_promotes_lower_grade_over_grade_one(self):
        queue = self._queue()
        for request in queue["requests"]:
            if request["account"] == "B":
                request["category"] = "연예·도파민"
                request["grade"] = "1" if int(request["candidate_id"].split("-")[-1]) < 5 else "2"
        result = select_owner_ranked_final_candidates(queue, {"annotations": []})
        self.assertEqual({item["grade"] for item in result["accounts"]["B"]["selected"]}, {"1"})

    def test_account_c_matches_are_not_arbitrarily_capped(self):
        queue = self._queue()
        annotations = [
            {"candidate_id": f"C-{index}", "commerce_status": "matched", "commerce_fit": 1 - index / 10, "matches": []}
            for index in range(4)
        ]
        result = select_owner_ranked_final_candidates(queue, {"annotations": annotations})
        matched = [item for item in result["accounts"]["C"]["selected"] if item["commerce_tie_break"] > 0]
        self.assertEqual(len(matched), 4)
        self.assertTrue(result["selection_policy"]["matched_product_use_is_optional_not_forced"])

    def test_unmatched_and_editorial_bypass_are_not_penalties(self):
        queue = self._queue()
        annotations = [
            {"candidate_id": "C-0", "commerce_status": "unmatched", "commerce_fit": None, "matches": []},
            {"candidate_id": "C-1", "commerce_status": "editorial_bypass", "commerce_fit": None, "matches": []},
        ]
        result = select_owner_ranked_final_candidates(queue, {"annotations": annotations})
        self.assertFalse(result["selection_policy"]["unmatched_or_editorial_bypass_penalty"])
        self.assertEqual([item["candidate_id"] for item in result["accounts"]["C"]["selected"][:2]], ["C-0", "C-1"])

    def test_obvious_same_event_headlines_are_grouped(self):
        queue = self._queue()
        queue["requests"][0]["title"] = "MC멩 8월 콘서트 예고, 공연장 대관 문의 없었다"
        queue["requests"][1]["title"] = "MC멩 복귀 콘서트, 공연장 대관 문의 없었다"
        result = select_owner_ranked_final_candidates(queue, {"annotations": []})
        self.assertGreaterEqual(result["duplicate_suppressed_count"], 1)
        duplicate = next(item for item in result["accounts"]["A"]["not_selected"] if item["candidate_id"] == "A-1")
        self.assertEqual(duplicate["reason_code"], "same_event_or_topic_duplicate")

    def test_different_brands_with_generic_runway_words_are_not_grouped(self):
        queue = self._queue()
        queue["requests"][0]["title"] = "[리뷰] 프라다 2027 S/S 남성복 컬렉션 이탈리아 럭셔리 브랜드"
        queue["requests"][1]["title"] = "[리뷰] 돌체앤가바나 2027 S/S 남성복 컬렉션 이탈리아 럭셔리"
        result = select_owner_ranked_final_candidates(queue, {"annotations": []})
        duplicates = {item["candidate_id"] for item in result["accounts"]["A"]["not_selected"] if item.get("reason_code") == "same_event_or_topic_duplicate"}
        self.assertNotIn("A-1", duplicates)

    def test_is_deterministic_and_does_not_mutate_inputs(self):
        queue = self._queue()
        original = repr(queue)
        first = select_owner_ranked_final_candidates(queue, {"annotations": []})
        second = select_owner_ranked_final_candidates(queue, {"annotations": []})
        self.assertEqual(first, second)
        self.assertEqual(repr(queue), original)

    def test_fail_closed(self):
        self.assertEqual(select_owner_ranked_final_candidates({}, {})["status"], "closed")


if __name__ == "__main__":
    unittest.main()
