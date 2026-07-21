import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from modules.card_news.category_media_pack import (
    CategoryMediaPackBuilder,
    load_package_config,
)
from modules.publishing.category_publish_package import CategoryPublishPackageBuilder

CONFIG, CONFIG_WARNINGS = load_package_config()
SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts/build_category_publish_packages.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("build_category_publish_packages", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestCategoryPublishPackage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.package_dir = self.root / "package"
        self.media_builder = CategoryMediaPackBuilder(config=CONFIG)
        self.package_builder = CategoryPublishPackageBuilder(config=CONFIG)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_media(self, name, payload=b"media-bytes"):
        path = self.root / name
        path.write_bytes(payload)
        return str(path)

    def _news_topic(self, caption="집중호우 대응이 왜 늦었는지 정리했습니다.", sources=None):
        return {
            "topic_id": "news-topic-01",
            "title": "집중호우 대응 논란",
            "category": "major_news_policy",
            "caption": caption,
            "sources": sources if sources is not None else [
                {"publisher": "JTBC 사건반장", "url": "https://news.example.com/article/1"}
            ],
            "slides": [
                {"order": 1, "slide_role": "cover", "media_type": "image",
                 "origin": "local_created", "asset_class": "auxiliary",
                 "local_path": self._write_media("cover.png")},
                {"order": 2, "slide_role": "clip", "media_type": "video",
                 "origin": "local_created", "asset_class": "auxiliary",
                 "local_path": self._write_media("clip.mp4")},
            ],
        }

    def _build(self, topic):
        media_pack = self.media_builder.build(topic, self.package_dir)
        return self.package_builder.build(topic, media_pack, self.package_dir)

    def test_news_package_ready_with_ordered_mixed_slides(self):
        topic = self._news_topic()
        manifest = self._build(topic)

        self.assertEqual(manifest["status"], "publish_package_ready")
        self.assertEqual(manifest["publish_status"], "manual_upload_pending")
        self.assertEqual(manifest["upload_mode"], "manual")
        self.assertFalse(manifest["published"])
        self.assertEqual(manifest["slide_count"], 2)

        publish_dir = self.package_dir / "publish_package"
        self.assertTrue((publish_dir / "slide_01.png").is_file())
        self.assertTrue((publish_dir / "slide_02.mp4").is_file())
        self.assertTrue((self.package_dir / "manifest.json").is_file())

        slides = manifest["slides"]
        self.assertEqual([slide["file"] for slide in slides],
                         ["publish_package/slide_01.png", "publish_package/slide_02.mp4"])
        self.assertEqual(slides[0]["slide_role"], "cover")
        self.assertEqual(slides[1]["media_type"], "video")

    def test_news_caption_retains_supplied_attribution_without_extras(self):
        topic = self._news_topic()
        self._build(topic)

        caption = (self.package_dir / "publish_package/caption.txt").read_text(encoding="utf-8")
        self.assertEqual(
            caption,
            "집중호우 대응이 왜 늦었는지 정리했습니다.\n\n참고: JTBC 사건반장\n",
        )
        for forbidden in ("팩트체크", "취재", "내부 검토", "게시 불가"):
            self.assertNotIn(forbidden, caption)

        sources_text = (self.package_dir / "publish_package/sources.txt").read_text(encoding="utf-8")
        self.assertIn("JTBC 사건반장", sources_text)
        self.assertIn("https://news.example.com/article/1", sources_text)

    def test_news_caption_with_existing_attribution_is_not_duplicated(self):
        topic = self._news_topic(caption="정리했습니다.\n\n참고: JTBC 사건반장")
        self._build(topic)
        caption = (self.package_dir / "publish_package/caption.txt").read_text(encoding="utf-8")
        self.assertEqual(caption.count("JTBC 사건반장"), 1)

    def test_community_story_never_invents_source_line(self):
        topic = {
            "topic_id": "story-01",
            "title": "결혼 준비 썰",
            "category": "community_buzz",
            "caption": "결혼 직전에 가족과 연을 끊은 이유, 이해가 감?",
            "slides": [
                {"order": 1, "slide_role": "cover", "media_type": "image",
                 "origin": "local_created", "local_path": self._write_media("story.png")},
            ],
        }
        manifest = self._build(topic)

        self.assertEqual(manifest["status"], "publish_package_ready")
        caption = (self.package_dir / "publish_package/caption.txt").read_text(encoding="utf-8")
        self.assertEqual(caption, "결혼 직전에 가족과 연을 끊은 이유, 이해가 감?\n")
        self.assertNotIn("참고:", caption)
        sources_text = (self.package_dir / "publish_package/sources.txt").read_text(encoding="utf-8")
        self.assertIn("supplied sources: none", sources_text)

    def test_news_without_supplied_source_blocks_honestly(self):
        topic = self._news_topic(sources=[])
        manifest = self._build(topic)

        self.assertEqual(manifest["status"], "publish_package_blocked")
        self.assertTrue(any("news_source_missing" in reason
                            for reason in manifest["blocking_reasons"]))
        self.assertFalse((self.package_dir / "publish_package/caption.txt").exists())
        self.assertTrue((self.package_dir / "manifest.json").is_file())

    def test_missing_caption_blocks_without_exception(self):
        topic = self._news_topic()
        topic.pop("caption")
        manifest = self._build(topic)

        self.assertEqual(manifest["status"], "publish_package_blocked")
        self.assertFalse(manifest["published"])
        self.assertTrue(any("caption_missing" in reason
                            for reason in manifest["blocking_reasons"]))
        self.assertFalse((self.package_dir / "publish_package/caption.txt").exists())

    def test_internal_review_marker_in_caption_blocks(self):
        topic = self._news_topic(caption="내부 검토 후 게시 여부를 결정합니다.")
        manifest = self._build(topic)
        self.assertEqual(manifest["status"], "publish_package_blocked")
        self.assertTrue(any("internal_review_marker_in_caption" in reason
                            for reason in manifest["blocking_reasons"]))

    def test_blocked_media_pack_carries_reasons_into_manifest(self):
        topic = {
            "topic_id": "fashion-01",
            "title": "beauty_fashion without vertical",
            "category": "beauty_fashion",
            "caption": "시즌 컨셉 정리",
            "slides": [
                {"order": 1, "origin": "official",
                 "local_path": self._write_media("look.png")},
            ],
        }
        manifest = self._build(topic)
        self.assertEqual(manifest["status"], "publish_package_blocked")
        self.assertTrue(any("beauty_fashion_vertical_missing" in reason
                            for reason in manifest["blocking_reasons"]))
        self.assertIsNone(manifest["category"]["canonical_category"])

    def test_preview_uses_relative_paths_only(self):
        topic = self._news_topic()
        self._build(topic)

        preview = (self.package_dir / "publish_package/preview.html").read_text(encoding="utf-8")
        self.assertIn('src="slide_01.png"', preview)
        self.assertIn('<video src="slide_02.mp4" controls>', preview)
        self.assertNotIn(str(self.package_dir), preview)
        self.assertNotIn("file://", preview)

    def test_manifest_never_marks_published(self):
        ready = self._build(self._news_topic())
        blocked = self.package_builder.build(None, None, self.root / "blocked")
        for manifest in (ready, blocked):
            self.assertEqual(manifest["upload_mode"], "manual")
            self.assertFalse(manifest["published"])
            self.assertIn(manifest["publish_status"], ("manual_upload_pending", "blocked"))

    def test_invalid_inputs_return_blocked_manifest(self):
        manifest = self.package_builder.build(None, None, self.root / "invalid")
        self.assertEqual(manifest["status"], "publish_package_blocked")
        self.assertTrue(manifest["blocking_reasons"])
        self.assertTrue((self.root / "invalid/manifest.json").is_file())


class TestBuildScript(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.output_root = self.root / "artifacts"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_emits_category_separated_packages(self):
        (self.root / "cover.png").write_bytes(b"png-bytes")
        topics = {
            "topics": [
                {
                    "topic_id": "story-cli-01",
                    "title": "CLI community story",
                    "category": "community_buzz",
                    "caption": "이 상황, 참을 수 있음?",
                    "slides": [
                        {"order": 1, "slide_role": "cover", "media_type": "image",
                         "origin": "local_created", "local_path": "cover.png"},
                    ],
                },
                {
                    "topic_id": "fashion-cli-01",
                    "title": "beauty_fashion blocked topic",
                    "category": "beauty_fashion",
                    "caption": "시즌 정리",
                    "slides": [
                        {"order": 1, "origin": "official", "local_path": "cover.png"},
                    ],
                },
            ]
        }
        input_path = self.root / "reviewed_topics.json"
        input_path.write_text(json.dumps(topics, ensure_ascii=False), encoding="utf-8")

        module = load_script_module()
        exit_code = module.main([
            str(input_path),
            "--output-root", str(self.output_root),
            "--date", "2026-07-17",
        ])
        self.assertEqual(exit_code, 0)

        ready_dir = self.output_root / "2026-07-17/community_story/story-cli-01"
        self.assertTrue((ready_dir / "manifest.json").is_file())
        self.assertTrue((ready_dir / "publish_package/slide_01.png").is_file())
        self.assertTrue((ready_dir / "publish_package/caption.txt").is_file())
        self.assertTrue((ready_dir / "media_pack/media_pack.json").is_file())

        blocked_dir = self.output_root / "2026-07-17/_blocked/fashion-cli-01"
        self.assertTrue((blocked_dir / "manifest.json").is_file())
        blocked_manifest = json.loads(
            (blocked_dir / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(blocked_manifest["status"], "publish_package_blocked")


if __name__ == "__main__":
    unittest.main()
