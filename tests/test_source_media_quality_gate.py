import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageColor

from modules.media_intelligence.source_media_quality_gate import (
    SourceMediaQualityGate,
)


class FakeOpenClip:
    def __init__(self, scores=None, *, status="passed", reason=None):
        self.scores = scores or {}
        self.status = status
        self.reason = reason
        self.calls = []

    def score_image_topics(self, path, topics, *, timeout_seconds):
        self.calls.append((Path(path), list(topics), timeout_seconds))
        return {
            "status": self.status,
            "passed": self.status == "passed",
            "reason": self.reason,
            "ranked_topics": [
                {"topic": topic, "cosine_similarity": self.scores.get(topic, 0.0)}
                for topic in topics
            ],
        }


def fake_ocr(text=""):
    def extract(path, *, timeout_seconds):
        return {
            "status": "completed",
            "success": True,
            "input_unchanged": True,
            "text": text,
            "lines": [text] if text else [],
        }

    return extract


class SourceMediaQualityGateTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def image(self, name, color, accent=None):
        path = self.root / name
        image = Image.new("RGB", (64, 64), color)
        if accent is not None:
            pixel = ImageColor.getrgb(accent) if isinstance(accent, str) else accent
            for x in range(32, 64):
                for y in range(64):
                    image.putpixel((x, y), pixel)
        image.save(path)
        return path

    def labels(self):
        return {
            "relevant": ["housing finance warning", "주거 금융 경고"],
            "distractors": ["cute animal", "generic abstract background"],
        }

    def test_returns_only_candidate_supported_by_both_tools(self):
        path = self.image("relevant.png", "white", "black")
        clip = FakeOpenClip(
            {
                "housing finance warning": 0.62,
                "주거 금융 경고": 0.44,
                "cute animal": 0.03,
                "generic abstract background": 0.08,
            }
        )
        result = SourceMediaQualityGate(
            ocr_extractor=fake_ocr("주거 금융 경고"),
            openclip=clip,
        ).evaluate(
            [{"candidate_id": "asset-1", "local_path": str(path)}],
            headline="주거 금융 경고",
            body="관련 변화를 확인합니다",
            bilingual_visual_labels=self.labels(),
        )
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["render_allowed"])
        self.assertEqual([item["candidate_id"] for item in result["passed_candidates"]], ["asset-1"])
        self.assertFalse(result["proxy_boundary"]["rights_or_license_evidence"])
        self.assertFalse(result["proxy_boundary"]["automatic_production_approval"])

    def test_perceptual_duplicate_is_rejected_even_with_different_files(self):
        first = self.image("first.png", "white", "black")
        second = self.image("second.jpg", "white", "black")
        clip = FakeOpenClip(
            {
                "housing finance warning": 0.7,
                "주거 금융 경고": 0.5,
                "cute animal": 0.0,
                "generic abstract background": 0.0,
            }
        )
        result = SourceMediaQualityGate(
            ocr_extractor=fake_ocr(),
            openclip=clip,
        ).evaluate(
            [
                {"candidate_id": "first", "local_path": str(first)},
                {"candidate_id": "second", "local_path": str(second)},
            ],
            headline="주거 금융 경고",
            body="변화",
            bilingual_visual_labels=self.labels(),
        )
        self.assertEqual(len(result["passed_candidates"]), 1)
        duplicate = result["rejected_candidates"][0]["quality_gate"]
        self.assertEqual(duplicate["reason_code"], "perceptual_duplicate")
        self.assertEqual(duplicate["duplicate_of"], "first")

    def test_distractor_dominance_blocks_candidate(self):
        path = self.image("cat-like.png", "orange", "white")
        clip = FakeOpenClip(
            {
                "housing finance warning": 0.25,
                "주거 금융 경고": 0.2,
                "cute animal": 0.71,
                "generic abstract background": 0.1,
            }
        )
        result = SourceMediaQualityGate(
            ocr_extractor=fake_ocr(),
            openclip=clip,
        ).evaluate(
            [{"candidate_id": "distractor", "local_path": str(path)}],
            headline="주거 금융 경고",
            body="변화",
            bilingual_visual_labels=self.labels(),
        )
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["render_allowed"])
        self.assertEqual(
            result["rejected_candidates"][0]["quality_gate"]["reason_code"],
            "distractor_dominant",
        )

    def test_ocr_unavailable_is_distinct_and_fail_closed(self):
        path = self.image("ocr-blocked.png", "gray", "black")

        def unavailable(path, *, timeout_seconds):
            return {
                "status": "failed",
                "success": False,
                "reason": "runtime_not_ready",
            }

        result = SourceMediaQualityGate(
            ocr_extractor=unavailable,
            openclip=FakeOpenClip(),
        ).evaluate(
            [{"local_path": str(path)}],
            headline="주거 금융 경고",
            body="변화",
            bilingual_visual_labels=self.labels(),
        )
        self.assertFalse(result["render_allowed"])
        self.assertEqual(
            result["rejected_candidates"][0]["quality_gate"]["reason_code"],
            "ocr_unavailable",
        )

    def test_openclip_timeout_is_distinct_and_fail_closed(self):
        path = self.image("clip-timeout.png", "gray", "white")
        result = SourceMediaQualityGate(
            ocr_extractor=fake_ocr(),
            openclip=FakeOpenClip(status="timeout", reason="score_timeout"),
        ).evaluate(
            [{"local_path": str(path)}],
            headline="주거 금융 경고",
            body="변화",
            bilingual_visual_labels=self.labels(),
        )
        self.assertFalse(result["render_allowed"])
        self.assertEqual(
            result["rejected_candidates"][0]["quality_gate"]["reason_code"],
            "openclip_timeout",
        )

    def test_detected_unrelated_text_blocks_even_when_clip_score_is_high(self):
        path = self.image("wrong-text.png", "white", "blue")
        clip = FakeOpenClip(
            {
                "housing finance warning": 0.65,
                "주거 금융 경고": 0.41,
                "cute animal": 0.02,
                "generic abstract background": 0.05,
            }
        )
        result = SourceMediaQualityGate(
            ocr_extractor=fake_ocr("반려동물 사료 할인"),
            openclip=clip,
        ).evaluate(
            [{"local_path": str(path)}],
            headline="주거 금융 경고",
            body="변화",
            bilingual_visual_labels=self.labels(),
        )
        self.assertFalse(result["render_allowed"])
        self.assertEqual(
            result["rejected_candidates"][0]["quality_gate"]["reason_code"],
            "ocr_context_mismatch",
        )


if __name__ == "__main__":
    unittest.main()
