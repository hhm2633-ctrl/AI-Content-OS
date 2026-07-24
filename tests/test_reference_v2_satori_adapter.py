import unittest

from modules.card_news.reference_v2_satori_adapter import (
    build_reference_v2_satori_tree,
)


class ReferenceV2SatoriAdapterTests(unittest.TestCase):
    def _walk_nodes(self, node):
        if not isinstance(node, dict):
            return
        yield node
        children = node.get("props", {}).get("children")
        if isinstance(children, list):
            for child in children:
                yield from self._walk_nodes(child)

    def _detail_slide(self, *, headline, body, reference_id="reference-a"):
        return {
            "status": "adapted",
            "primary_reference_id": reference_id,
            "geometry_hash": "detail-geometry",
            "style_tokens": {
                "background": "#EFE9DD",
                "accent": "#C77944",
                "font_size": 34,
            },
            "regions": [
                {
                    "region_id": "title",
                    "role": "headline",
                    "box_norm": [0.08, 0.14, 0.84, 0.3],
                    "z_index": 2,
                },
                {
                    "region_id": "body",
                    "role": "body",
                    "box_norm": [0.08, 0.5, 0.84, 0.3],
                    "z_index": 2,
                },
            ],
            "content_bindings": [
                {"region_id": "title", "content": headline},
                {"region_id": "body", "content": body},
            ],
            "reference_consumption_receipt": {
                "geometry_modified": False,
                "geometry_hash": "detail-geometry",
                "primary_reference_id": reference_id,
            },
        }

    def test_preserves_geometry_and_builds_media_and_text_nodes(self):
        adapted = {
            "status": "adapted",
            "geometry_hash": "hash-1",
            "regions": [
                {
                    "region_id": "photo",
                    "role": "primary_media",
                    "box_norm": [0.0, 0.0, 1.0, 0.7],
                    "z_index": 1,
                },
                {
                    "region_id": "title",
                    "role": "headline",
                    "box_norm": [0.08, 0.72, 0.84, 0.2],
                    "z_index": 2,
                },
            ],
            "media_bindings": [
                {
                    "region_id": "photo",
                    "asset": {"remote_url": "https://img.example/photo.jpg"},
                }
            ],
            "content_bindings": [
                {"region_id": "title", "content": "학습된 제목"}
            ],
            "reference_consumption_receipt": {
                "geometry_modified": False,
                "geometry_hash": "hash-1",
            },
        }

        result = build_reference_v2_satori_tree(adapted)

        self.assertEqual("ready", result["status"])
        children = result["tree"]["props"]["children"]
        self.assertEqual("70.000000%", children[0]["props"]["style"]["height"])
        self.assertEqual("학습된 제목", children[1]["props"]["children"])
        self.assertFalse(
            result["reference_consumption_receipt"]["geometry_modified"]
        )

    def test_missing_adapted_geometry_blocks(self):
        result = build_reference_v2_satori_tree({"status": "blocked"})
        self.assertEqual("blocked", result["status"])

    def test_page_one_with_source_image_keeps_cover_contract(self):
        adapted = self._detail_slide(
            headline="출처 이미지가 있는 첫 장",
            body="핵심 내용을 짧게 설명합니다.",
        )

        result = build_reference_v2_satori_tree(
            adapted,
            page=1,
            fallback_image_uri="data:image/png;base64,owned",
        )

        self.assertEqual("ready", result["status"])
        self.assertIsNone(result["detail_family"])
        image = result["tree"]["props"]["children"][0]
        self.assertEqual("img", image["type"])
        self.assertEqual("100%", image["props"]["style"]["height"])

    def test_detail_pages_use_four_structural_families_without_adjacent_repeat(self):
        samples = (
            ("매출 101억 돌파", "전년보다 42% 증가한 수치입니다."),
            ("관계자는 “계속 지원하겠다”고 밝혔다", "공식 발언의 맥락입니다."),
            ("협약 이후 3개월의 변화", "첫 단계부터 다음 일정까지 정리합니다."),
            ("확인된 핵심 근거", "자료에 기록된 사실을 간결하게 설명합니다."),
            ("지원 규모 250건", "대상과 범위를 숫자로 확인합니다."),
            ("“현장에서 답을 찾았다”", "당사자의 발언을 그대로 요약합니다."),
            ("2단계부터 적용", "이후 일정과 기간을 순서대로 보여줍니다."),
            ("추가 확인 사항", "출처에 기록된 배경과 의미를 설명합니다."),
        )
        results = [
            build_reference_v2_satori_tree(
                self._detail_slide(headline=headline, body=body),
                page=index + 2,
            )
            for index, (headline, body) in enumerate(samples)
        ]
        families = [result["detail_family"] for result in results]

        self.assertEqual({"key-fact", "evidence-brief", "quote", "progression"}, set(families))
        self.assertTrue(
            all(left != right for left, right in zip(families, families[1:]))
        )
        self.assertTrue(
            all(result["reference_consumption_receipt"] for result in results)
        )

        family_shapes = {
            result["detail_family"]: tuple(
                (
                    child["type"],
                    child.get("props", {}).get("style", {}).get("left"),
                    child.get("props", {}).get("style", {}).get("top"),
                    child.get("props", {}).get("style", {}).get("borderRight"),
                )
                for child in result["tree"]["props"]["children"]
            )
            for result in results
        }
        self.assertEqual(4, len(set(family_shapes.values())))

    def test_each_detail_family_has_visible_nonempty_headline_and_body(self):
        palette_contract = {
            "key-fact": ("#FFFFFF", "#102B30", "#0B1F24"),
            "evidence-brief": ("#FFFFFF", "#102B30", "#0B1F24"),
            "quote": ("#0B1F24", "#FFFFFF", "#F4EFE5"),
            "progression": ("#0B1F24", "#0B1F24", "#F4EFE5"),
        }
        samples = (
            ("매출 101억 돌파", "전년보다 42% 증가한 수치입니다."),
            ("관계자는 “지원을 계속하겠다”고 밝혔다", "공식 발언의 배경입니다."),
            ("협약 이후 3개월", "첫 단계부터 다음 일정까지 정리합니다."),
            ("확인된 핵심 근거", "출처에 기록된 사실을 설명합니다."),
        )
        by_family = {}
        for page in range(2, 10):
            for headline, body in samples:
                result = build_reference_v2_satori_tree(
                    self._detail_slide(headline=headline, body=body),
                    page=page,
                )
                by_family.setdefault(result["detail_family"], result)

        self.assertEqual(set(palette_contract), set(by_family))
        for family, result in by_family.items():
            headline_color, body_color, background = palette_contract[family]
            tree = result["tree"]
            self.assertEqual(
                background,
                tree["props"]["style"]["backgroundColor"],
            )
            nodes = list(self._walk_nodes(tree))
            headline_nodes = [
                node
                for node in nodes
                if node.get("props", {}).get("dataTextRole") == "headline"
            ]
            body_nodes = [
                node
                for node in nodes
                if node.get("props", {}).get("dataTextRole") == "body"
            ]
            self.assertTrue(headline_nodes)
            self.assertTrue(body_nodes)
            self.assertTrue(
                all(node["props"]["children"] for node in headline_nodes)
            )
            self.assertTrue(
                all(node["props"]["children"] for node in body_nodes)
            )
            self.assertTrue(
                all(
                    node["props"]["style"]["color"] == headline_color
                    for node in headline_nodes
                )
            )
            self.assertTrue(
                all(
                    node["props"]["style"]["color"] == body_color
                    for node in body_nodes
                )
            )

        quote_tree = by_family["quote"]["tree"]
        quote_card = next(
            node
            for node in self._walk_nodes(quote_tree)
            if node.get("props", {}).get("dataRole")
            == "quote-body-card"
        )
        self.assertEqual("“", quote_card["props"]["children"])
        quote_body = next(
            node
            for node in quote_tree["props"]["children"]
            if node.get("props", {}).get("dataTextRole") == "body"
        )
        self.assertEqual(
            "12.962963%",
            quote_body["props"]["style"]["left"],
        )
        self.assertEqual(
            "58.518519%",
            quote_body["props"]["style"]["top"],
        )
        self.assertEqual(
            "74.074074%",
            quote_body["props"]["style"]["width"],
        )
        self.assertEqual(
            "13.333333%",
            quote_body["props"]["style"]["height"],
        )
        self.assertEqual("#FFFFFF", quote_body["props"]["style"]["color"])
        self.assertGreater(quote_body["props"]["style"]["zIndex"], 1)
        self.assertTrue(quote_body["props"]["children"])

    def test_detail_family_selection_never_forces_quote_without_direct_quote(self):
        numeric = build_reference_v2_satori_tree(
            self._detail_slide(
                headline="지원 대상 370명",
                body="사업 규모는 총 2600억 원입니다.",
            ),
            page=5,
        )
        no_quote = build_reference_v2_satori_tree(
            self._detail_slide(
                headline="협약의 주요 배경",
                body="확인된 자료와 일반적인 배경을 설명합니다.",
            ),
            page=6,
        )
        actual_quote = build_reference_v2_satori_tree(
            self._detail_slide(
                headline="관계자는 “지원을 계속하겠다”고 밝혔다",
                body="공식 발언의 배경과 확인된 내용을 정리합니다.",
            ),
            page=7,
        )

        self.assertEqual("key-fact", numeric["detail_family"])
        self.assertNotEqual("quote", no_quote["detail_family"])
        self.assertEqual("evidence-brief", no_quote["detail_family"])
        self.assertEqual("quote", actual_quote["detail_family"])

    def test_people_count_overrides_progression_word_and_builds_giant_number(self):
        result = build_reference_v2_satori_tree(
            self._detail_slide(
                headline="신규 일자리 370명 이상",
                body="이번 투자 과정에서 지역 고용을 확대합니다.",
            ),
            page=5,
        )

        self.assertEqual("key-fact", result["detail_family"])
        giant = next(
            node
            for node in self._walk_nodes(result["tree"])
            if node.get("props", {}).get("dataRole")
            == "key-fact-giant"
        )
        self.assertEqual("370명", giant["props"]["children"])
        self.assertGreaterEqual(giant["props"]["style"]["fontSize"], 130)
        self.assertEqual("#E5B04A", giant["props"]["style"]["color"])
        self.assertEqual(
            "#0B1F24",
            result["tree"]["props"]["style"]["backgroundColor"],
        )

    def test_detail_scaffold_omits_empty_body_card(self):
        adapted = self._detail_slide(
            headline="신규 일자리 370명 이상",
            body="",
        )

        result = build_reference_v2_satori_tree(adapted, page=4)
        body_cards = [
            node
            for node in self._walk_nodes(result["tree"])
            if node.get("props", {}).get("dataRole") == "detail-body-card"
        ]

        self.assertEqual([], body_cards)


if __name__ == "__main__":
    unittest.main()
