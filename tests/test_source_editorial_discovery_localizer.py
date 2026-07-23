import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from modules.media_intelligence.source_editorial_localizer import (
    localize_discovered_media_assets,
)


class PassingGate:
    def evaluate(self, candidates, *, headline, body, bilingual_visual_labels):
        passed = []
        for index, candidate in enumerate(candidates):
            item = dict(candidate)
            item["quality_gate"] = {"relevant_score": 0.9 - index * 0.1}
            passed.append(item)
        return {
            "status": "passed",
            "reason_code": "",
            "passed_candidates": passed,
            "rejected_candidates": [],
            "render_allowed": True,
        }


class RelativeFallbackGate:
    def evaluate(self, candidates, *, headline, body, bilingual_visual_labels):
        rejected = []
        for candidate in candidates:
            item = dict(candidate)
            item["quality_gate"] = {
                "passed": False,
                "reason_code": "insufficient_visual_relevance",
                "relevant_score": 0.22,
                "distractor_score": 0.16,
                "openclip": {
                    "ranked_topics": [
                        {"topic": headline, "cosine_similarity": 0.22},
                        {"topic": "generic abstract background", "cosine_similarity": 0.16},
                    ]
                },
            }
            rejected.append(item)
        return {
            "status": "blocked",
            "reason_code": "no_candidate_passed_quality_gate",
            "passed_candidates": [],
            "rejected_candidates": rejected,
            "render_allowed": False,
        }


class SourceEditorialDiscoveryLocalizerTests(unittest.TestCase):
    def test_open_asset_is_downloaded_deduplicated_and_ranked(self):
        output_root = Path("F:/AI-Content-OS-Data/qa/localizer_unit")
        asset = {
            "asset_id": "commons-1",
            "remote_url": "https://upload.wikimedia.org/test.png",
            "source_url": "https://commons.wikimedia.org/wiki/File:test.png",
            "source_provider": "wikimedia_commons",
            "rights_status": "open_license",
            "topic_relevant": True,
            "attribution_required": True,
            "publish_authorized": False,
            "render_allowed": True,
        }

        def fake_download(url, destination):
            destination.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (80, 60), "green").save(destination)
            return 80, 60

        with patch(
            "modules.media_intelligence.source_editorial_localizer._download_image",
            side_effect=fake_download,
        ):
            result = localize_discovered_media_assets(
                [asset, dict(asset, asset_id="commons-duplicate")],
                output_root,
                query="초록 이미지",
                quality_gate=PassingGate(),
            )

        self.assertEqual("completed", result["status"])
        self.assertEqual(1, result["selected_count"])
        self.assertEqual(1, result["duplicate_count"])
        self.assertTrue(Path(result["assets"][0]["local_path"]).is_file())
        self.assertEqual(
            "https://commons.wikimedia.org/wiki/File:test.png",
            result["assets"][0]["source_url"],
        )

    def test_open_license_relative_relevance_can_be_manual_review_candidate(self):
        output_root = Path("F:/AI-Content-OS-Data/qa/localizer_relative_unit")
        asset = {
            "asset_id": "commons-relative",
            "remote_url": "https://upload.wikimedia.org/relevant.jpg",
            "source_url": "https://commons.wikimedia.org/wiki/File:relevant.jpg",
            "source_provider": "wikimedia_commons",
            "rights_status": "open_license",
            "topic_relevant": True,
            "attribution_required": True,
            "publish_authorized": False,
            "render_allowed": True,
        }

        def fake_download(url, destination):
            destination.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (80, 60), "blue").save(destination)
            return 80, 60

        with patch(
            "modules.media_intelligence.source_editorial_localizer._download_image",
            side_effect=fake_download,
        ):
            result = localize_discovered_media_assets(
                [asset],
                output_root,
                query="rainy season in Seoul",
                quality_gate=RelativeFallbackGate(),
            )

        self.assertEqual("completed", result["status"])
        self.assertEqual(1, result["selected_count"])
        self.assertEqual(
            "relative_visual_relevance_fallback",
            result["assets"][0]["quality_gate"]["reason_code"],
        )
        self.assertTrue(result["assets"][0]["manual_visual_review_required"])

    def test_global_cache_reuses_content_across_output_roots(self):
        base = Path("F:/AI-Content-OS-Data/qa")
        base.mkdir(parents=True, exist_ok=True)
        asset = {
            "asset_id": "commons-cache",
            "remote_url": "https://upload.wikimedia.org/cache.png",
            "source_url": "https://commons.wikimedia.org/wiki/File:cache.png",
            "source_provider": "wikimedia_commons",
            "rights_status": "open_license",
            "topic_relevant": True,
            "attribution_required": True,
            "publish_authorized": False,
            "render_allowed": True,
        }

        def fake_download(url, destination):
            destination.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (96, 72), "orange").save(destination)
            return 96, 72

        with tempfile.TemporaryDirectory(dir=base) as temporary:
            task_root = Path(temporary)
            cache_root = task_root / "shared-cache"
            with patch(
                "modules.media_intelligence.source_editorial_localizer._download_image",
                side_effect=fake_download,
            ) as downloader:
                first = localize_discovered_media_assets(
                    [asset],
                    task_root / "candidate-a",
                    query="주황 이미지",
                    quality_gate=PassingGate(),
                    cache_root=cache_root,
                )
                second = localize_discovered_media_assets(
                    [dict(asset, asset_id="commons-cache-second")],
                    task_root / "candidate-b",
                    query="주황 이미지",
                    quality_gate=PassingGate(),
                    cache_root=cache_root,
                )

            self.assertEqual(1, downloader.call_count)
            self.assertEqual(0, first["cache_hit_count"])
            self.assertEqual(1, second["cache_hit_count"])
            self.assertEqual(
                first["assets"][0]["content_sha256"],
                second["assets"][0]["content_sha256"],
            )
            index = json.loads(
                (cache_root / "reuse_index.json").read_text(encoding="utf-8")
            )
            self.assertEqual(1, len(index["by_cache_key"]))
            self.assertEqual(1, len(index["by_content_sha256"]))

    def test_missing_cached_file_falls_back_to_download(self):
        base = Path("F:/AI-Content-OS-Data/qa")
        base.mkdir(parents=True, exist_ok=True)
        asset = {
            "asset_id": "commons-missing-cache",
            "remote_url": "https://upload.wikimedia.org/missing-cache.png",
            "source_url": (
                "https://commons.wikimedia.org/wiki/File:missing-cache.png"
            ),
            "source_provider": "wikimedia_commons",
            "rights_status": "open_license",
            "topic_relevant": True,
            "attribution_required": True,
            "publish_authorized": False,
            "render_allowed": True,
        }

        def fake_download(url, destination):
            destination.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (64, 64), "navy").save(destination)
            return 64, 64

        with tempfile.TemporaryDirectory(dir=base) as temporary:
            task_root = Path(temporary)
            cache_root = task_root / "shared-cache"
            with patch(
                "modules.media_intelligence.source_editorial_localizer._download_image",
                side_effect=fake_download,
            ) as downloader:
                first = localize_discovered_media_assets(
                    [asset],
                    task_root / "candidate-a",
                    query="남색 이미지",
                    quality_gate=PassingGate(),
                    cache_root=cache_root,
                )
                Path(first["assets"][0]["local_path"]).unlink()
                second = localize_discovered_media_assets(
                    [asset],
                    task_root / "candidate-b",
                    query="남색 이미지",
                    quality_gate=PassingGate(),
                    cache_root=cache_root,
                )

            self.assertEqual(2, downloader.call_count)
            self.assertEqual(0, second["cache_hit_count"])
            self.assertTrue(Path(second["assets"][0]["local_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
