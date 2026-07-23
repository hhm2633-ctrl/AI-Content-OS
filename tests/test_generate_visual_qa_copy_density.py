from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from PIL import Image

from scripts.generate_visual_qa_receipt_from_media import _analyze_slide


def _build_text(length: int) -> str:
    base = "카드는 짧고 명확하게 읽힐수록 전달력이 좋아요. "
    text = (base * ((length // len(base)) + 1))[:length]
    return text


def _build_lines(line_count: int, per_line: str = "요약 라인") -> list[str]:
    return [f"{idx + 1}. {per_line}" for idx in range(line_count)]


def _mock_ocr(text: str, lines: list[str]) -> object:
    return SimpleNamespace(
        status="completed",
        text=text,
        lines=lines,
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
    def _analyze_copy_density(
        self, text: str, lines: list[str], media_type: str = "image"
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
            "page": 1,
            "image_path": str(image_path),
            "account": "C",
            "template_crop_window": None,
            "media_type": media_type,
        }

        package = {
            "candidate": {"title": "DIOR MEN 시즌", "category": "패션", "account": "C"},
            "slides": [{"role": "summary", "headline": "DIOR", "body": "시즌 요약", "media_type": "image"}],
            "story": {"summary": "DIOR MEN"},
        }

        try:
            with patch(
                "scripts.generate_visual_qa_receipt_from_media.extract_korean_text",
                return_value=_mock_ocr(text, lines),
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
