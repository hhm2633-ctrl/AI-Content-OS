import json
import tempfile
import unittest
from pathlib import Path

from modules.card_news.category_media_pack import (
    CategoryMediaPackBuilder,
    build_topic_slug,
    load_package_config,
    resolve_category,
)

CONFIG, CONFIG_WARNINGS = load_package_config()


def fail_fetcher(url, timeout_seconds, max_bytes):
    raise AssertionError(f"network fetch must not happen for {url}")


class TestCategoryResolution(unittest.TestCase):
    def test_legacy_buckets_map_to_canonical_categories(self):
        expected = {
            "major_news_policy": "news_policy_society",
            "incident_conflict": "news_incident",
            "economy_market": "news_economy_market",
            "entertainment_relationship": "relationship_entertainment",
            "community_buzz": "community_story",
        }
        for legacy, canonical in expected.items():
            result = resolve_category({"category": legacy}, CONFIG)
            self.assertEqual(result["status"], "resolved", legacy)
            self.assertEqual(result["canonical_category"], canonical)

    def test_canonical_category_passes_through(self):
        result = resolve_category({"category": "fashion"}, CONFIG)
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["canonical_category"], "fashion")

    def test_beauty_fashion_splits_from_explicit_vertical(self):
        result = resolve_category({"category": "beauty_fashion", "vertical": "뷰티"}, CONFIG)
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["canonical_category"], "beauty")

        result = resolve_category({"category": "beauty_fashion", "vertical": "Fashion"}, CONFIG)
        self.assertEqual(result["canonical_category"], "fashion")

    def test_beauty_fashion_blocks_without_vertical_metadata(self):
        result = resolve_category({"category": "beauty_fashion"}, CONFIG)
        self.assertEqual(result["status"], "blocked")
        self.assertIsNone(result["canonical_category"])
        self.assertIn("beauty_fashion_vertical_missing", result["reason"])

    def test_missing_and_unknown_categories_block(self):
        self.assertIn("category_missing", resolve_category({}, CONFIG)["reason"])
        self.assertIn(
            "category_unknown",
            resolve_category({"category": "sports"}, CONFIG)["reason"],
        )

    def test_topic_slug_is_filesystem_safe_and_deterministic(self):
        topic = {"topic_id": "Topic 42: Housing!"}
        first = build_topic_slug(topic)
        self.assertEqual(first, build_topic_slug(topic))
        self.assertRegex(first, r"^[a-z0-9_-]+$")
        korean = build_topic_slug({"title": "시어머니 밀키트 논란"})
        self.assertRegex(korean, r"^topic-[0-9a-f]{10}$")


class TestCategoryMediaPackBuilder(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.package_dir = self.root / "package"
        self.builder = CategoryMediaPackBuilder(config=CONFIG, fetcher=fail_fetcher)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_media(self, name, payload=b"media-bytes"):
        path = self.root / name
        path.write_bytes(payload)
        return str(path)

    def _topic(self, slides, category="community_buzz", **extra):
        topic = {
            "topic_id": "topic-001",
            "title": "reviewed topic",
            "category": category,
            "caption": "caption text",
            "slides": slides,
        }
        topic.update(extra)
        return topic

    def test_local_file_is_packaged_with_metadata_preserved(self):
        slides = [{
            "order": 1,
            "slide_role": "cover",
            "media_type": "image",
            "origin": "community",
            "asset_class": "source_evidence",
            "source_url": "https://example.com/post/1",
            "publisher": "네이트판",
            "brand": "",
            "local_path": self._write_media("cover.png"),
        }]
        result = self.builder.build(self._topic(slides), self.package_dir)

        self.assertEqual(result["status"], "media_pack_ready")
        self.assertEqual(result["category"]["canonical_category"], "community_story")
        item = result["items"][0]
        self.assertEqual(item["status"], "packaged")
        self.assertTrue(item["publishable"])
        self.assertEqual(item["source_url"], "https://example.com/post/1")
        self.assertEqual(item["publisher"], "네이트판")
        self.assertEqual(item["origin"], "community")
        self.assertEqual(item["asset_class"], "source_evidence")
        self.assertEqual(item["slide_role"], "cover")
        packaged = self.package_dir / item["packaged_file"]
        self.assertTrue(packaged.is_file())
        self.assertTrue((self.package_dir / "media_pack" / "media_pack.json").is_file())
        pack_json = json.loads(
            (self.package_dir / "media_pack" / "media_pack.json").read_text(encoding="utf-8")
        )
        self.assertEqual(pack_json["status"], "media_pack_ready")

    def test_missing_local_file_produces_diagnostic_not_exception(self):
        slides = [{"order": 1, "origin": "local_created",
                   "local_path": str(self.root / "missing.png")}]
        result = self.builder.build(self._topic(slides), self.package_dir)

        self.assertEqual(result["status"], "media_pack_blocked")
        self.assertTrue(any("no_publishable_media" in reason
                            for reason in result["blocking_reasons"]))
        item = result["items"][0]
        self.assertEqual(item["status"], "invalid")
        self.assertTrue(any("missing" in diag for diag in item["diagnostics"]))

    def test_remote_url_stays_reference_without_download_mode(self):
        slides = [{"order": 1, "origin": "news",
                   "remote_url": "https://news.example.com/image.png"}]
        result = self.builder.build(self._topic(slides), self.package_dir)

        item = result["items"][0]
        self.assertEqual(item["status"], "remote_reference")
        self.assertFalse(item["publishable"])
        self.assertEqual(item["remote_url"], "https://news.example.com/image.png")
        self.assertIsNone(item["packaged_file"])

    def test_download_mode_fetches_only_supplied_url_with_limits(self):
        seen = []

        def stub_fetcher(url, timeout_seconds, max_bytes):
            seen.append(url)
            return b"png-bytes", "image/png"

        builder = CategoryMediaPackBuilder(config=CONFIG, fetcher=stub_fetcher)
        slides = [{"order": 1, "origin": "official",
                   "remote_url": "https://brand.example.com/look.png"}]
        result = builder.build(self._topic(slides), self.package_dir, download_remote=True)

        self.assertEqual(seen, ["https://brand.example.com/look.png"])
        item = result["items"][0]
        self.assertEqual(item["status"], "downloaded")
        self.assertTrue((self.package_dir / item["packaged_file"]).is_file())

    def test_download_rejects_oversize_and_disallowed_type(self):
        config = json.loads(json.dumps(CONFIG))
        config["download"]["max_bytes"] = 8

        def oversize_fetcher(url, timeout_seconds, max_bytes):
            return b"x" * (max_bytes + 1), "image/png"

        builder = CategoryMediaPackBuilder(config=config, fetcher=oversize_fetcher)
        slides = [{"order": 1, "remote_url": "https://a.example.com/big.png", "origin": "news"}]
        result = builder.build(self._topic(slides), self.package_dir / "big", download_remote=True)
        item = result["items"][0]
        self.assertEqual(item["status"], "download_failed")
        self.assertTrue(any("limit" in diag for diag in item["diagnostics"]))

        def html_fetcher(url, timeout_seconds, max_bytes):
            return b"<html>", "text/html"

        builder = CategoryMediaPackBuilder(config=CONFIG, fetcher=html_fetcher)
        result = builder.build(self._topic(slides), self.package_dir / "html", download_remote=True)
        item = result["items"][0]
        self.assertEqual(item["status"], "download_failed")
        self.assertTrue(any("content type" in diag for diag in item["diagnostics"]))

    def test_download_failure_keeps_url_as_reference_diagnostic(self):
        def broken_fetcher(url, timeout_seconds, max_bytes):
            raise OSError("connection refused")

        builder = CategoryMediaPackBuilder(config=CONFIG, fetcher=broken_fetcher)
        slides = [{"order": 1, "remote_url": "https://a.example.com/x.png", "origin": "news"}]
        result = builder.build(self._topic(slides), self.package_dir, download_remote=True)
        item = result["items"][0]
        self.assertEqual(item["status"], "download_failed")
        self.assertEqual(item["remote_url"], "https://a.example.com/x.png")

    def test_ap_items_stay_reference_only_even_in_download_mode(self):
        def stub_fetcher(url, timeout_seconds, max_bytes):
            raise AssertionError("AP material must never be fetched into the package")

        builder = CategoryMediaPackBuilder(config=CONFIG, fetcher=stub_fetcher)
        slides = [
            {"order": 1, "origin": "news", "publisher": "Associated Press",
             "remote_url": "https://ap.example.com/photo.jpg"},
            {"order": 2, "origin": "news", "publisher": "AP통신",
             "local_path": self._write_media("ap_local.jpg")},
        ]
        result = builder.build(
            self._topic(slides, category="major_news_policy"),
            self.package_dir,
            download_remote=True,
        )
        for item in result["items"]:
            self.assertEqual(item["status"], "reference_only")
            self.assertTrue(item["reference_only"])
            self.assertFalse(item["publishable"])
            self.assertIsNone(item["packaged_file"])

    def test_generated_media_cannot_be_source_evidence(self):
        slides = [{
            "order": 1,
            "origin": "generated",
            "asset_class": "source_evidence",
            "local_path": self._write_media("generated.png"),
        }]
        result = self.builder.build(self._topic(slides), self.package_dir)
        item = result["items"][0]
        self.assertEqual(item["status"], "blocked")
        self.assertFalse(item["publishable"])
        self.assertTrue(any("evidence" in diag for diag in item["diagnostics"]))

    def test_mixed_media_order_is_preserved(self):
        slides = [
            {"order": 2, "slide_role": "clip", "media_type": "video",
             "origin": "local_created", "local_path": self._write_media("clip.mp4")},
            {"order": 1, "slide_role": "cover", "media_type": "image",
             "origin": "local_created", "local_path": self._write_media("cover.webp")},
        ]
        result = self.builder.build(self._topic(slides), self.package_dir)
        self.assertEqual(result["status"], "media_pack_ready")
        self.assertEqual(
            [item["slide_role"] for item in result["items"]], ["cover", "clip"]
        )
        self.assertTrue(result["items"][0]["packaged_file"].endswith(".webp"))
        self.assertTrue(result["items"][1]["packaged_file"].endswith(".mp4"))

    def test_invalid_input_returns_blocked_manifest_without_exception(self):
        for bad_input in (None, [], "text", {}):
            result = self.builder.build(bad_input, self.package_dir / "bad")
            self.assertEqual(result["status"], "media_pack_blocked")
            self.assertTrue(result["blocking_reasons"])
            self.assertTrue(result["fallback_used"])

    def test_beauty_fashion_without_vertical_blocks_pack(self):
        slides = [{"order": 1, "origin": "official",
                   "local_path": self._write_media("look.png")}]
        result = self.builder.build(
            self._topic(slides, category="beauty_fashion"), self.package_dir
        )
        self.assertEqual(result["status"], "media_pack_blocked")
        self.assertTrue(any("beauty_fashion_vertical_missing" in reason
                            for reason in result["blocking_reasons"]))


if __name__ == "__main__":
    unittest.main()
