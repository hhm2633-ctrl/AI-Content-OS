from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from PIL import Image

from scripts.generate_visual_qa_receipt_from_media import (
    _analyze_slide,
    _assess_final_receipt,
    _candidate_feed_caption,
    _bounded_ordered_map,
    _load_visual_qa_model_cache,
    _model_evidence_cacheable,
    _feed_caption_finding,
    _receipt_scope,
    _visual_qa_cache_key,
    _visual_qa_model_config,
    _write_visual_qa_model_cache,
)


def _build_text(length: int) -> str:
    base = "카드는 짧고 명확하게 읽힐수록 전달력이 좋아요. "
    text = (base * ((length // len(base)) + 1))[:length]
    return text


def _build_lines(line_count: int, per_line: str = "요약 라인") -> list[str]:
    return [f"{idx + 1}. {per_line}" for idx in range(line_count)]


def _mock_ocr(
    text: str,
    lines: list[str],
    boxes: list[list[float]] | None = None,
) -> object:
    return SimpleNamespace(
        status="completed",
        text=text,
        lines=lines,
        boxes=boxes or [],
        polys=[],
        scores=[0.99] * max(1, len(lines)),
        success=True,
        input_bytes=1_024,
        reason="",
    )


def _create_temp_image() -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    image_path = Path(tmp.name)
    tmp.close()
    image = Image.new("RGB", (640, 640), color=(250, 250, 250))
    image.save(image_path)
    return image_path


class GenerateVisualQaCopyDensityTests(TestCase):
    def test_successful_model_evidence_cache_round_trip_and_config_invalidation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = _visual_qa_model_config(
                {
                    "model": {
                        "model_name": "RN50-quickgelu",
                        "revision": "revision-a",
                        "sha256": "weights-a",
                    }
                },
                openclip_timeout=30.0,
                ocr_timeout=30.0,
            )
            cache_key = _visual_qa_cache_key(
                image_sha256="image-a",
                expected_copy="예상 카피",
                semantic_context={"candidate_title": "제목"},
                config_hash=config["config_hash"],
            )
            cache_path = root / f"{cache_key}.json"
            evidence = {
                "ocr": {
                    "status": "completed",
                    "success": True,
                    "text": "예상 카피",
                    "lines": ["예상 카피"],
                    "boxes": [[10, 10, 100, 40]],
                    "polys": [],
                    "scores": [0.99],
                    "input_bytes": 100,
                    "reason": "",
                },
                "openclip_result": {
                    "status": "completed",
                    "passed": True,
                    "ranked_topics": [],
                },
            }
            self.assertTrue(_model_evidence_cacheable(evidence))
            self.assertTrue(
                _write_visual_qa_model_cache(
                    cache_path,
                    cache_key=cache_key,
                    config=config,
                    image_sha256="image-a",
                    expected_copy="예상 카피",
                    model_evidence=evidence,
                )
            )
            loaded = _load_visual_qa_model_cache(
                cache_path,
                cache_key=cache_key,
                config_hash=config["config_hash"],
            )
            self.assertEqual(evidence, loaded)
            self.assertIsNone(
                _load_visual_qa_model_cache(
                    cache_path,
                    cache_key=cache_key,
                    config_hash="changed-config",
                )
            )

    def test_failed_model_evidence_is_not_cacheable(self):
        evidence = {
            "ocr": {"status": "failed", "success": False},
            "openclip_result": {"status": "failed", "passed": False},
        }
        self.assertFalse(_model_evidence_cacheable(evidence))

    def test_bounded_parallel_map_preserves_input_order(self):
        rows = [3, 1, 2, 0]
        self.assertEqual(
            [30, 10, 20, 0],
            _bounded_ordered_map(
                rows,
                lambda value: value * 10,
                max_workers=3,
            ),
        )

    def test_assessment_consumes_the_same_final_receipt_that_is_returned(self):
        receipt = {
            "scope": {
                "kind": "batch",
                "representative_receipt_ids": {"A": "qa-a"},
            },
            "feed_caption_by_candidate": {"candidate-a": "Caption A"},
            "slides": [
                {
                    "candidate_id": "candidate-a",
                    "page": 1,
                    "findings": {"feed_caption_present": "pass"},
                }
            ],
        }
        captured = {}

        def assess_final(value, *_args, **_kwargs):
            captured["receipt"] = value
            return {
                "visual_qa_passed": True,
                "failures": [],
            }

        with patch(
            "scripts.generate_visual_qa_receipt_from_media.assess_visual_qa_receipt",
            side_effect=assess_final,
        ):
            final_receipt, assessed = _assess_final_receipt(
                receipt,
                [],
                output_set_id="batch-output",
                scope=receipt["scope"],
            )

        self.assertIs(final_receipt, captured["receipt"])
        self.assertEqual(
            "pass",
            captured["receipt"]["slides"][0]["findings"][
                "feed_caption_present"
            ],
        )
        self.assertEqual([], assessed["failures"])

    def test_batch_metadata_is_candidate_scoped(self):
        captions = {
            "candidate-a": "Caption A",
            "candidate-b": "Caption B",
        }
        self.assertEqual(
            "Caption A",
            _candidate_feed_caption("candidate-a", {}, captions),
        )
        self.assertEqual(
            "Package fallback",
            _candidate_feed_caption(
                "candidate-c",
                {"feed_caption": "Package fallback"},
                captions,
            ),
        )
        self.assertEqual("pass", _feed_caption_finding("candidate-a", captions))
        self.assertEqual("fail", _feed_caption_finding("candidate-c", captions))
        scope = _receipt_scope(
            ["candidate-a", "candidate-b"],
            ["A", "B"],
            {"A": "qa-a", "B": "qa-b"},
        )
        self.assertEqual("batch", scope["kind"])
        self.assertEqual(
            {"A": "qa-a", "B": "qa-b"},
            scope["representative_receipt_ids"],
        )

    def test_representative_scope_keeps_existing_shape(self):
        scope = _receipt_scope(
            ["candidate-a"],
            ["A"],
            {"A": "qa-a"},
        )
        self.assertEqual("representative", scope["kind"])
        self.assertNotIn("representative_receipt_ids", scope)

    def _analyze_copy_density(
        self,
        text: str,
        lines: list[str],
        media_type: str = "image",
        *,
        headline: str | None = None,
        body: str | None = None,
        page: int = 1,
        boxes: list[list[float]] | None = None,
        blankness_proxy: float = 0.05,
        asset_refs: list[str] | None = None,
        visual_type: str = "",
        source_media: bool = False,
    ) -> dict:
        image_path = _create_temp_image()

        class FakeOpenClipRuntime:
            def score_image_topics(self, *_args, **_kwargs):
                return {
                    "status": "completed",
                    "reason": "",
                    "ranked_topics": [{"topic": "fashion", "cosine_similarity": 0.99}],
                    "runtime_ready": True,
                }

        slide = {
            "page": page,
            "image_path": str(image_path),
            "account": "C",
            "template_crop_window": None,
            "media_type": media_type,
        }

        package = {
            "candidate": {"title": "DIOR MEN 시즌", "category": "패션", "account": "C"},
            "slides": [{
                "page": page,
                "role": "summary",
                "headline": headline if headline is not None else text,
                "body": body if body is not None else "",
                "media_type": media_type,
                "asset_refs": asset_refs or [],
                "visual_spec": {
                    "visual_type": visual_type,
                    "source_media_candidate": (
                        {"asset_id": "source-media"}
                        if source_media
                        else None
                    ),
                },
            }],
            "story": {"summary": "DIOR MEN"},
        }

        try:
            with patch(
                "scripts.generate_visual_qa_receipt_from_media.extract_korean_text",
                return_value=_mock_ocr(text, lines, boxes),
            ), patch(
                "scripts.generate_visual_qa_receipt_from_media._sample_signal",
                return_value=(
                    True,
                    {
                        "width": 640,
                        "height": 640,
                        "blankness_proxy": blankness_proxy,
                    },
                ),
            ), patch(
                "scripts.generate_visual_qa_receipt_from_media._read_subject_bbox_from_image",
                return_value={"status": "subject_bbox_not_evaluated"},
            ):
                findings, analysis, _ = _analyze_slide(
                    slide,
                    package,
                    openclip_runtime=FakeOpenClipRuntime(),
                    openclip_timeout=0.1,
                    ocr_timeout=0.1,
                    default_account="C",
                    default_candidate_title="DIOR MEN 시즌",
                )

            return {"findings": findings, "analysis": analysis}
        finally:
            image_path.unlink(missing_ok=True)

    def test_copy_density_ok_normal_korean_copy_pass(self):
        text = (
            "이번 시즌 오버사이즈 실루엣은 과한 장식보다 움직임을 먼저 보여줍니다. "
            "첫 프레임은 핵심 메시지를 한 줄로 남기고, 다음 라인에서 보조 포인트만 짧게 보강해 가독성을 높였습니다."
        )
        lines = [
            "이미지 중심으로 구성된 시즌 리뷰는 핵심 카피를 1~2문장으로 정리합니다.",
            "과도한 설명보다 톤과 분위기 정보가 읽기 쉬워야 카드뉴스가 오래 보입니다.",
        ]
        result = self._analyze_copy_density(text, lines)
        self.assertEqual("pass", result["findings"]["copy_density_ok"])
        self.assertLess(result["analysis"]["ocr"]["text_char_count"], 151)
        self.assertLessEqual(len(lines), 5)

    def test_copy_density_ok_boundary_below_limit_still_passes(self):
        text = _build_text(230)
        lines = _build_lines(10)
        result = self._analyze_copy_density(text, lines)
        self.assertEqual("pass", result["findings"]["copy_density_ok"])
        self.assertEqual(230, result["analysis"]["ocr"]["text_char_count"])
        self.assertEqual(10, result["analysis"]["ocr"]["line_count"])

    def test_copy_density_ok_boundary_above_limit_fails(self):
        text = _build_text(280)
        lines = _build_lines(13)
        result = self._analyze_copy_density(text, lines)
        self.assertEqual("fail", result["findings"]["copy_density_ok"])
        self.assertEqual(280, result["analysis"]["ocr"]["text_char_count"])
        self.assertEqual(13, result["analysis"]["ocr"]["line_count"])

    def test_editorial_text_card_does_not_fail_image_primary_rule(self):
        result = self._analyze_copy_density(
            _build_text(280), _build_lines(13), media_type="editorial"
        )
        self.assertEqual("pass", result["findings"]["image_is_primary"])
        self.assertEqual("fail", result["findings"]["copy_density_ok"])

    def test_expected_slide_copy_omission_fails_closed(self):
        result = self._analyze_copy_density(
            "제주 투자 소식",
            ["제주 투자 소식"],
            headline="한일 양국 자본이 제주 스타트업에 첫 투자한다",
            body="첫 투자기업과 펀드 조성 배경을 구체적으로 설명합니다",
        )
        self.assertEqual("fail", result["findings"]["copy_readability"])
        integrity = result["analysis"]["copy_integrity"]
        self.assertLess(integrity["expected_copy_coverage"], 0.55)
        self.assertIn(
            "expected_copy_coverage_below_minimum",
            integrity["reason_codes"],
        )

    def test_headline_repeated_at_body_start_fails_closed(self):
        headline = "한일 양국 자본이 제주 스타트업에 첫 투자한다"
        result = self._analyze_copy_density(
            f"{headline} {headline} 첫 투자기업은 새로핌입니다",
            [headline, f"{headline} 첫 투자기업은 새로핌입니다"],
            headline=headline,
            body=f"{headline}. 첫 투자기업은 새로핌입니다.",
        )
        self.assertEqual("fail", result["findings"]["copy_readability"])
        self.assertTrue(result["analysis"]["copy_integrity"]["duplicate_detected"])
        self.assertIn(
            "headline_repeated_at_body_start",
            result["analysis"]["copy_integrity"]["reason_codes"],
        )

    def test_ocr_bbox_outside_bottom_safe_area_fails_readability(self):
        text = "핵심 내용이 화면 하단에서 잘리지 않아야 합니다"
        result = self._analyze_copy_density(
            text,
            [text],
            boxes=[[40, 600, 590, 635]],
        )
        self.assertEqual("fail", result["findings"]["mobile_readability"])
        self.assertEqual("fail", result["findings"]["copy_readability"])
        self.assertIn(
            "ocr_bbox_outside_safe_area",
            result["analysis"]["layout_safety"]["reason_codes"],
        )

    def test_detail_high_blankness_without_media_or_copy_fails_closed(self):
        text = "투자 핵심 요약"
        result = self._analyze_copy_density(
            text,
            [text],
            media_type="editorial",
            page=2,
            boxes=[[80, 120, 240, 150]],
            blankness_proxy=0.38,
        )
        self.assertEqual("fail", result["findings"]["content_not_blank"])
        self.assertIn(
            "detail_high_blankness_with_insufficient_text_and_media",
            result["analysis"]["detail_blankness"]["reason_codes"],
        )

    def test_detail_with_confirmed_media_is_not_blocked_by_blankness_rule(self):
        text = "투자 핵심 요약"
        result = self._analyze_copy_density(
            text,
            [text],
            page=2,
            boxes=[[80, 120, 240, 150]],
            blankness_proxy=0.38,
            asset_refs=["asset:jeju-investment"],
        )
        self.assertEqual("pass", result["findings"]["content_not_blank"])
        self.assertTrue(result["analysis"]["detail_blankness"]["has_media"])

    def test_image_primary_ignores_unrelated_source_image_text_bbox(self):
        headline = "제주 스타트업 첫 투자 소식"
        source_sign = "행사장 현수막 안내문"
        result = self._analyze_copy_density(
            f"{headline} {source_sign}",
            [headline, source_sign],
            headline=headline,
            boxes=[
                [80, 120, 430, 170],
                [30, 600, 590, 635],
            ],
            asset_refs=["asset:jeju-event-photo"],
        )
        safety = result["analysis"]["layout_safety"]
        self.assertEqual("pass", result["findings"]["mobile_readability"])
        self.assertTrue(safety["passed"])
        self.assertEqual("expected_overlay_copy_only", safety["scope"])
        self.assertEqual(1, safety["ignored_source_text_box_count"])

    def test_media_with_openclip_topic_pass_survives_lower_third_text_panel(self):
        headline = "제주 스타트업 첫 투자 소식"
        result = self._analyze_copy_density(
            headline,
            [headline],
            headline=headline,
            boxes=[[30, 350, 610, 600]],
            asset_refs=["asset:topic-0291-photo"],
            visual_type="cover_editorial",
            source_media=True,
        )
        evidence = result["analysis"]["image_primary_evidence"]
        self.assertGreater(evidence["text_area_ratio"], 0.15)
        self.assertTrue(evidence["source_media_present"])
        self.assertTrue(evidence["openclip_topic_pass"])
        self.assertTrue(evidence["media_topic_primary"])
        self.assertEqual("pass", result["findings"]["image_is_primary"])
        self.assertEqual(
            "expected_overlay_copy_only",
            result["analysis"]["layout_safety"]["scope"],
        )

    def test_source_media_lower_third_excludes_background_ocr_from_copy_checks(self):
        headline = "구미에 2600억원 반도체 투자"
        body = "구미시와 월덱스가 반도체 부품 생산시설 증설 협약을 맺었습니다"
        background_lines = [
            f"배경 간판 문구 {index}" for index in range(12)
        ]
        overlay_lines = [
            headline,
            "구미시와 월덱스가",
            "반도체 부품 생산시설 증설",
            "협약을 맺었습니다",
        ]
        lines = background_lines + overlay_lines
        boxes = [
            [20, 80 + index * 20, 635 if index == 3 else 400, 98 + index * 20]
            for index in range(12)
        ] + [
            [40, 300 + index * 70, 600, 350 + index * 70]
            for index in range(4)
        ]
        result = self._analyze_copy_density(
            " ".join(lines),
            lines,
            headline=headline,
            body=body,
            boxes=boxes,
            asset_refs=["asset:topic-0291-photo"],
            visual_type="cover_editorial",
            source_media=True,
        )
        measurement = result["analysis"]["copy_measurement"]
        self.assertEqual(
            "source_media_lower_third_expected_overlay",
            measurement["scope"],
        )
        self.assertEqual(16, measurement["raw_line_count"])
        self.assertEqual(4, measurement["effective_line_count"])
        self.assertEqual(12, measurement["excluded_source_ocr_line_count"])
        self.assertGreaterEqual(measurement["effective_avg_text_conf"], 0.28)
        self.assertEqual("pass", result["findings"]["copy_density_ok"])
        self.assertEqual("pass", result["findings"]["copy_readability"])
        self.assertEqual("pass", result["findings"]["mobile_readability"])

    def test_detail_without_media_keeps_all_ocr_bbox_safety_checks(self):
        headline = "제주 투자 핵심"
        source_sign = "행사장 현수막 안내문"
        result = self._analyze_copy_density(
            f"{headline} {source_sign}",
            [headline, source_sign],
            headline=headline,
            page=2,
            boxes=[
                [80, 120, 430, 170],
                [30, 600, 590, 635],
            ],
        )
        safety = result["analysis"]["layout_safety"]
        self.assertEqual("fail", result["findings"]["mobile_readability"])
        self.assertFalse(safety["passed"])
        self.assertEqual("all_ocr_text", safety["scope"])
        self.assertEqual(0, safety["ignored_source_text_box_count"])
