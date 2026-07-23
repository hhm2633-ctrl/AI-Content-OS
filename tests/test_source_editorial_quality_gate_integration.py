import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from modules.media_intelligence import source_editorial_localizer as localizer


class _PassingGate:
    def evaluate(
        self,
        candidates,
        *,
        headline,
        body,
        bilingual_visual_labels,
    ):
        del headline, body, bilingual_visual_labels
        passed = []
        for index, candidate in enumerate(candidates):
            passed.append(
                {
                    **candidate,
                    "quality_gate": {
                        "passed": True,
                        "relevant_score": 0.9 - (index * 0.1),
                    },
                }
            )
        return {
            "status": "passed",
            "render_allowed": True,
            "passed_candidates": passed,
            "rejected_candidates": [],
        }


def _package(labels_status="supplied"):
    visual_spec = {
        "visual_type": "cover_editorial",
        "visual_relevance_labels_status": labels_status,
    }
    if labels_status == "supplied":
        visual_spec["visual_relevance_labels"] = {
            "relevant": ["a financial warning news scene"],
            "distractors": ["a pet", "an empty template"],
        }
    return {
        "status": "production_package_ready",
        "reason_code": "learning_driven_package_composed",
        "evidence": {
            "assets": [
                {
                    "asset_id": "asset-1",
                    "remote_url": "https://example.com/one.jpg",
                    "source_url": "https://example.com/article",
                    "rights_status": "source_editorial_usable",
                    "topic_relevant": True,
                    "attribution_required": True,
                    "publish_authorized": False,
                }
            ]
        },
        "slides": [
            {
                "page": 1,
                "headline": "경고 신호",
                "body": "금융 변화가 확인됐다.",
                "visual_spec": visual_spec,
            }
        ],
        "media_plan": [{"page": 1}],
        "gates": {"render": {"status": "ready", "authorized": False}},
    }


def _fake_download(url, destination):
    del url
    Image.new("RGB", (320, 180), "red").save(destination)
    return 320, 180


def test_localizer_blocks_when_visual_labels_are_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(localizer, "_download_image", _fake_download)
    result = localizer.localize_source_editorial_media(
        _package("missing"),
        Path("F:/quality-gate-test"),
        quality_gate=_PassingGate(),
    )

    assert result["status"] == "blocked"
    assert result["gates"]["render"]["status"] == "blocked"
    assert result["evidence"]["assets"] == []
    assert (
        result["evidence"]["source_media_quality"]["receipts"][0]["reason_code"]
        == "visual_relevance_labels_missing"
    )


def test_localizer_assigns_only_quality_verified_unique_media(monkeypatch):
    monkeypatch.setattr(localizer, "_download_image", _fake_download)
    result = localizer.localize_source_editorial_media(
        _package(),
        Path("F:/quality-gate-test"),
        quality_gate=_PassingGate(),
    )

    assert result["status"] == "production_package_ready"
    assert result["source_editorial_localization"]["quality_gate_status"] == "passed"
    selected = result["slides"][0]["visual_spec"]["source_media_candidate"]
    assert selected["quality_gate"]["passed"] is True
    assert len(result["evidence"]["assets"]) == 1


class SourceEditorialQualityGateIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.output_root = (
            Path("F:/AI-Content-OS-Data/test-tmp")
            / f"source-editorial-gate-{uuid.uuid4().hex}"
        )

    def tearDown(self):
        shutil.rmtree(self.output_root, ignore_errors=True)

    def test_missing_labels_block_render(self):
        with patch.object(localizer, "_download_image", _fake_download):
            result = localizer.localize_source_editorial_media(
                _package("missing"),
                self.output_root,
                quality_gate=_PassingGate(),
            )

        self.assertEqual("blocked", result["status"])
        self.assertEqual("blocked", result["gates"]["render"]["status"])
        self.assertEqual([], result["evidence"]["assets"])

    def test_only_verified_unique_media_is_assigned(self):
        with patch.object(localizer, "_download_image", _fake_download):
            result = localizer.localize_source_editorial_media(
                _package(),
                self.output_root,
                quality_gate=_PassingGate(),
            )

        self.assertEqual("production_package_ready", result["status"])
        self.assertEqual(
            "passed",
            result["source_editorial_localization"]["quality_gate_status"],
        )
        selected = result["slides"][0]["visual_spec"][
            "source_media_candidate"
        ]
        self.assertTrue(selected["quality_gate"]["passed"])
