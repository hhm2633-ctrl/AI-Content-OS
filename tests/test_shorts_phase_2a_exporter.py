import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.shorts.shorts_exporter import ShortsExporter


def _phase_one_result():
    captions = [
        {"scene_id": 1, "start_seconds": 0.0, "end_seconds": 3.0, "text": "첫 장면입니다."},
        {"scene_id": 2, "start_seconds": 3.0, "end_seconds": 9.0, "text": "문제를 확인합니다."},
        {"scene_id": 3, "start_seconds": 9.0, "end_seconds": 21.0, "text": "해결 방법을 적용합니다."},
        {"scene_id": 4, "start_seconds": 21.0, "end_seconds": 25.0, "text": "저장하고 다시 확인하세요."},
    ]
    scenes = [
        {
            "scene_id": item["scene_id"],
            "script_line_ids": [item["scene_id"]],
            "visual_type": "text_over_background",
            "duration_seconds": item["end_seconds"] - item["start_seconds"],
            "transition": "cut",
        }
        for item in captions
    ]
    return {
        "status": "shorts_planning_completed",
        "shorts_brief_result": {
            "module": "ShortsBriefBuilder",
            "status": "shorts_brief_created",
            "source_content_ref": {"title": "AI 자동화 가이드", "caption_hash": "abc123"},
            "topic": {"title": "AI 자동화 가이드"},
            "fallback_used": False,
            "reason": "",
        },
        "shorts_script_result": {
            "module": "ShortsScriptPlanner",
            "status": "shorts_script_created",
            "total_estimated_seconds": 25.0,
            "fallback_used": False,
            "reason": "",
        },
        "shorts_scene_plan_result": {
            "module": "ShortsScenePlanner",
            "status": "shorts_scene_plan_created",
            "scenes": scenes,
            "fallback_used": False,
            "reason": "",
        },
        "shorts_asset_plan_result": {"status": "shorts_asset_plan_created", "fallback_used": True, "reason": "manual"},
        "shorts_caption_result": {
            "module": "ShortsCaptionPlanner",
            "status": "shorts_captions_created",
            "caption_source": "script_text_only",
            "transcription_used": False,
            "captions": captions,
            "fallback_used": False,
            "reason": "",
        },
        "shorts_audio_plan_result": {"status": "shorts_audio_plan_created", "fallback_used": True, "reason": "manual"},
        "shorts_render_plan_result": {"status": "shorts_render_plan_created", "fallback_used": True, "reason": "manual"},
        "shorts_qa_result": {"status": "shorts_qa_completed", "fallback_used": False, "reason": ""},
        "shorts_publish_prep_result": {"status": "shorts_publish_prep_manual_required", "fallback_used": True, "reason": "manual"},
    }


class TestShortsPhase2AExporter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.exporter = ShortsExporter(self.root / "exports")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _package_dir(self, result):
        return self.exporter.export_root / result["export_root"]

    def test_deterministic_offline_export_writes_required_package(self):
        result = self.exporter.run(_phase_one_result())
        package_dir = self._package_dir(result)

        self.assertEqual(result["status"], "shorts_editing_package_partial")
        self.assertTrue(result["fallback_used"])
        self.assertFalse(result["external_calls_attempted"])
        self.assertFalse(result["rendered"])
        self.assertFalse(result["published"])
        self.assertEqual(set(result["files"].values()), {
            "source_contracts.json",
            "editing_package.json",
            "timeline_manifest.json",
            "captions.srt",
            "asset_validation.json",
            "manual_checklist.json",
        })
        self.assertTrue(all((package_dir / name).is_file() for name in result["files"].values()))
        self.assertTrue((package_dir / "licenses" / "README.json").is_file())

        second_root = self.root / "second"
        second = ShortsExporter(second_root).run(_phase_one_result())
        self.assertEqual(result["package_id"], second["package_id"])
        self.assertEqual(
            (package_dir / "captions.srt").read_text(encoding="utf-8"),
            (second_root / second["export_root"] / "captions.srt").read_text(encoding="utf-8"),
        )

    def test_manifest_is_vertical_1080x1920_and_timeline_is_contiguous(self):
        result = self.exporter.run(_phase_one_result())
        manifest = json.loads(
            (self._package_dir(result) / "timeline_manifest.json").read_text(encoding="utf-8")
        )

        self.assertEqual(manifest["canvas"]["width"], 1080)
        self.assertEqual(manifest["canvas"]["height"], 1920)
        self.assertFalse(manifest["rendering_supported"])
        self.assertIsNone(manifest["render_plan"]["renderer"])
        self.assertEqual(manifest["duration_seconds"], 25.0)
        self.assertEqual(
            [(scene["start_seconds"], scene["end_seconds"]) for scene in manifest["scenes"]],
            [(0.0, 3.0), (3.0, 9.0), (9.0, 21.0), (21.0, 25.0)],
        )

    def test_srt_uses_script_timing_and_preserves_korean(self):
        result = self.exporter.run(_phase_one_result())
        srt = (self._package_dir(result) / "captions.srt").read_text(encoding="utf-8")

        self.assertIn("1\n00:00:00,000 --> 00:00:03,000\n첫 장면입니다.", srt)
        self.assertIn("4\n00:00:21,000 --> 00:00:25,000\n저장하고 다시 확인하세요.", srt)

    def test_approved_user_asset_is_copied_to_normalized_path(self):
        source = self.root / "사용자 파일 이름.PNG"
        source.write_bytes(b"\x89PNG\r\n\x1a\nlocal-image-data")
        assets = [{
            "scene_id": 1,
            "file_path": str(source),
            "asset_type": "image",
            "topic_relevant": True,
            "copyright_status": "owned",
            "provided_by": "user",
        }]
        result = self.exporter.run(_phase_one_result(), assets)
        package_dir = self._package_dir(result)
        validation = json.loads((package_dir / "asset_validation.json").read_text(encoding="utf-8"))
        first = validation["items"][0]

        self.assertTrue(first["render_allowed"])
        self.assertEqual(first["package_path"], "assets/scene-001.png")
        self.assertEqual((package_dir / first["package_path"]).read_bytes(), source.read_bytes())
        self.assertTrue(first["magic_valid"])

    def test_missing_unapproved_and_unlicensed_assets_remain_manual(self):
        existing = self.root / "clip.mp4"
        existing.write_bytes(b"\x00\x00\x00\x18ftypmp42video-placeholder")
        assets = [
            {"scene_id": 1, "file_path": str(existing), "topic_relevant": True, "copyright_status": "unknown", "provided_by": "user"},
            {"scene_id": 2, "file_path": str(existing), "topic_relevant": True, "copyright_status": "licensed", "provided_by": "user"},
            {"scene_id": 3, "file_path": str(self.root / "missing.mp4"), "topic_relevant": True, "copyright_status": "owned", "provided_by": "user"},
        ]
        result = self.exporter.run(_phase_one_result(), assets)
        validation = json.loads(
            (self._package_dir(result) / "asset_validation.json").read_text(encoding="utf-8")
        )

        self.assertEqual(validation["manual_asset_required_count"], 4)
        self.assertTrue(all(not item["render_allowed"] for item in validation["items"]))
        self.assertIn("Copyright status is not approved", validation["items"][0]["warnings"])
        self.assertIn("Licensed asset requires an existing license evidence file", validation["items"][1]["warnings"])

    def test_licensed_asset_requires_reference_and_then_is_allowed(self):
        source = self.root / "licensed.mov"
        source.write_bytes(b"\x00\x00\x00\x18ftypqt  licensed-video")
        evidence = self.root / "license-receipt.txt"
        evidence.write_text("license evidence", encoding="utf-8")
        result = self.exporter.run(
            _phase_one_result(),
            [{
                "scene_id": 1,
                "file_path": str(source),
                "topic_relevant": True,
                "copyright_status": "licensed",
                "license_reference": str(evidence),
                "provided_by": "user",
            }],
        )
        validation = json.loads(
            (self._package_dir(result) / "asset_validation.json").read_text(encoding="utf-8")
        )
        self.assertTrue(validation["items"][0]["render_allowed"])
        licenses = json.loads(
            (self._package_dir(result) / "licenses" / "README.json").read_text(encoding="utf-8")
        )
        self.assertEqual(licenses["items"][0]["license_reference"], "license-receipt.txt")
        self.assertTrue(licenses["items"][0]["license_evidence_exists"])

    def test_asset_requires_verified_user_provider(self):
        source = self.root / "owned.png"
        source.write_bytes(b"\x89PNG\r\n\x1a\nowned-image")
        result = self.exporter.run(
            _phase_one_result(),
            [{
                "scene_id": 1,
                "file_path": str(source),
                "topic_relevant": True,
                "copyright_status": "owned",
                "provided_by": "crawler",
            }],
        )
        validation = json.loads(
            (self._package_dir(result) / "asset_validation.json").read_text(encoding="utf-8")
        )

        self.assertFalse(validation["items"][0]["provided_by_valid"])
        self.assertFalse(validation["items"][0]["render_allowed"])
        self.assertIn("provided_by must be 'user'", validation["items"][0]["warnings"])

    def test_overwrite_is_blocked_without_explicit_opt_in(self):
        first = self.exporter.run(_phase_one_result())
        marker = self._package_dir(first) / "marker.txt"
        marker.write_text("preserve", encoding="utf-8")
        blocked = self.exporter.run(_phase_one_result())

        self.assertEqual(blocked["status"], "shorts_editing_package_fallback")
        self.assertIn("overwrite is disabled", blocked["reason"])
        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")
        replaced = self.exporter.run(_phase_one_result(), overwrite=True)
        self.assertEqual(replaced["package_id"], first["package_id"])
        self.assertFalse(marker.exists())

    def test_invalid_input_returns_fallback_without_writing(self):
        for value in (None, "invalid", 123, {}):
            with self.subTest(value=value):
                result = self.exporter.run(value)
                self.assertEqual(result["status"], "shorts_editing_package_fallback")
                self.assertTrue(result["fallback_used"])
                self.assertFalse(result["external_calls_attempted"])
        self.assertFalse((self.root / "exports").exists())

    def test_partial_contract_and_invalid_caption_timing_are_diagnostic(self):
        source = _phase_one_result()
        source.pop("shorts_audio_plan_result")
        source["shorts_caption_result"]["captions"][1]["start_seconds"] = 2.0
        result = self.exporter.run(source)

        self.assertEqual(result["status"], "shorts_editing_package_partial")
        self.assertIn("Missing or invalid contract: shorts_audio_plan_result", result["reason"])
        self.assertIn("invalid timing", result["reason"])

    def test_empty_captions_create_partial_package_with_srt_warning(self):
        source = _phase_one_result()
        source["shorts_caption_result"]["captions"] = []
        result = self.exporter.run(source)

        self.assertEqual(result["status"], "shorts_editing_package_partial")
        self.assertIn("No valid captions", result["reason"])
        self.assertEqual(
            (self._package_dir(result) / "captions.srt").read_text(encoding="utf-8"),
            "",
        )

    def test_unsafe_relative_path_and_unknown_scene_are_ignored(self):
        result = self.exporter.run(
            _phase_one_result(),
            [
                {"scene_id": 1, "file_path": "../outside.mp4", "topic_relevant": True, "copyright_status": "owned", "provided_by": "user"},
                {"scene_id": 99, "file_path": "unknown.mp4", "topic_relevant": True, "copyright_status": "owned", "provided_by": "user"},
            ],
        )
        package_dir = self._package_dir(result)
        validation = json.loads((package_dir / "asset_validation.json").read_text(encoding="utf-8"))

        self.assertFalse(validation["items"][0]["render_allowed"])
        self.assertTrue(
            any("outside the allowed asset root" in warning for warning in validation["items"][0]["warnings"])
        )
        self.assertIn("unknown scene 99", result["reason"])
        self.assertEqual(list((package_dir / "assets").iterdir()), [])

    def test_write_failure_never_exposes_incomplete_final_package(self):
        original = self.exporter._write_json
        calls = 0

        def fail_during_staging(path, payload):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError("injected write failure")
            return original(path, payload)

        with patch.object(self.exporter, "_write_json", side_effect=fail_during_staging):
            result = self.exporter.run(_phase_one_result())

        self.assertEqual(result["status"], "shorts_editing_package_fallback")
        self.assertFalse((self.exporter.export_root / result["export_root"]).exists())
        self.assertEqual(list((self.root / "exports").glob(".*.staging-*")), [])

    def test_failed_overwrite_preserves_previous_complete_package(self):
        first = self.exporter.run(_phase_one_result())
        package_dir = self._package_dir(first)
        original_manifest = (package_dir / "timeline_manifest.json").read_bytes()

        with patch.object(self.exporter, "_verify_staging", side_effect=OSError("verification failed")):
            failed = self.exporter.run(_phase_one_result(), overwrite=True)

        self.assertEqual(failed["status"], "shorts_editing_package_fallback")
        self.assertEqual((package_dir / "timeline_manifest.json").read_bytes(), original_manifest)
        self.assertEqual(list((self.root / "exports").glob(".*.staging-*")), [])

    def test_package_id_hashes_scene_caption_asset_and_provenance(self):
        base = self.exporter.run(_phase_one_result())

        scene_changed = _phase_one_result()
        scene_changed["shorts_scene_plan_result"]["scenes"][0]["duration_seconds"] = 2.5
        scene_result = ShortsExporter(self.root / "scene").run(scene_changed)

        caption_changed = _phase_one_result()
        caption_changed["shorts_caption_result"]["captions"][0]["text"] = "변경된 자막"
        caption_result = ShortsExporter(self.root / "caption").run(caption_changed)

        asset = self.root / "identity.png"
        asset.write_bytes(b"\x89PNG\r\n\x1a\nidentity-one")
        asset_input = [{
            "scene_id": 1,
            "file_path": str(asset),
            "topic_relevant": True,
            "copyright_status": "owned",
            "provided_by": "user",
        }]
        asset_result = ShortsExporter(self.root / "asset").run(_phase_one_result(), asset_input)
        asset.write_bytes(b"\x89PNG\r\n\x1a\nidentity-two")
        content_result = ShortsExporter(self.root / "asset2").run(_phase_one_result(), asset_input)
        provenance_input = [dict(asset_input[0], copyright_status="public_domain")]
        provenance_result = ShortsExporter(self.root / "provenance").run(
            _phase_one_result(), provenance_input
        )

        ids = {
            base["package_id"],
            scene_result["package_id"],
            caption_result["package_id"],
            asset_result["package_id"],
            content_result["package_id"],
            provenance_result["package_id"],
        }
        self.assertEqual(len(ids), 6)

    def test_manifest_caption_ids_equal_srt_cue_ids_after_sorting(self):
        source = _phase_one_result()
        source["shorts_caption_result"]["captions"] = list(
            reversed(source["shorts_caption_result"]["captions"])
        )
        result = self.exporter.run(source)
        package_dir = self._package_dir(result)
        manifest = json.loads((package_dir / "timeline_manifest.json").read_text(encoding="utf-8"))
        srt = (package_dir / "captions.srt").read_text(encoding="utf-8")
        manifest_ids = [cue_id for scene in manifest["scenes"] for cue_id in scene["caption_ids"]]
        srt_ids = [int(block.splitlines()[0]) for block in srt.strip().split("\n\n")]

        self.assertEqual(sorted(manifest_ids), srt_ids)
        self.assertEqual(srt_ids, [1, 2, 3, 4])

    def test_duplicate_scene_id_is_blocked_before_writing(self):
        source = _phase_one_result()
        source["shorts_scene_plan_result"]["scenes"][1]["scene_id"] = 1
        result = self.exporter.run(source)

        self.assertEqual(result["status"], "shorts_editing_package_fallback")
        self.assertIn("Duplicate scene IDs", result["reason"])
        self.assertFalse((self.root / "exports").exists())

    def test_duplicate_asset_scene_id_is_blocked_before_read_or_write(self):
        asset = self.root / "duplicate.png"
        asset.write_bytes(b"\x89PNG\r\n\x1a\nduplicate")
        candidate = {"scene_id": 1, "file_path": str(asset), "topic_relevant": True, "copyright_status": "owned", "provided_by": "user"}
        with patch.object(self.exporter, "_file_sha256", wraps=self.exporter._file_sha256) as hash_mock:
            result = self.exporter.run(_phase_one_result(), [candidate, dict(candidate)])

        self.assertEqual(result["status"], "shorts_editing_package_fallback")
        self.assertEqual(result["blockers"][0]["code"], "DUPLICATE_ASSET_SCENE_ID")
        self.assertEqual(hash_mock.call_count, 0)
        self.assertFalse((self.root / "exports").exists())

    def test_license_evidence_outside_asset_root_is_rejected_without_path_leak(self):
        asset = self.root / "licensed-inside.mov"
        asset.write_bytes(b"\x00\x00\x00\x18ftypqt  licensed-video")
        outside_evidence = self.root.parent / "outside-license.txt"
        result = self.exporter.run(
            _phase_one_result(),
            [{"scene_id": 1, "file_path": str(asset), "topic_relevant": True, "copyright_status": "licensed", "license_reference": str(outside_evidence), "provided_by": "user"}],
        )
        package_dir = self._package_dir(result)
        validation = json.loads((package_dir / "asset_validation.json").read_text(encoding="utf-8"))

        self.assertFalse(validation["items"][0]["render_allowed"])
        self.assertTrue(any("outside the allowed asset root" in warning for warning in validation["items"][0]["warnings"]))
        self.assertNotIn(str(outside_evidence), json.dumps(validation, ensure_ascii=False))

    def test_spoofed_extension_is_rejected_by_magic_validation(self):
        spoofed = self.root / "spoofed.png"
        spoofed.write_bytes(b"this is not a png")
        result = self.exporter.run(
            _phase_one_result(),
            [{
                "scene_id": 1,
                "file_path": str(spoofed),
                "topic_relevant": True,
                "copyright_status": "owned",
                "provided_by": "user",
            }],
        )
        validation = json.loads(
            (self._package_dir(result) / "asset_validation.json").read_text(encoding="utf-8")
        )

        self.assertFalse(validation["items"][0]["magic_valid"])
        self.assertFalse(validation["items"][0]["render_allowed"])
        self.assertIn("content signature", validation["items"][0]["warnings"][0])

    def test_video_magic_is_checked_but_codec_remains_phase_2b_gate(self):
        video = self.root / "container.mp4"
        video.write_bytes(b"\x00\x00\x00\x18ftypmp42not-a-decoded-video")
        result = self.exporter.run(
            _phase_one_result(),
            [{
                "scene_id": 1,
                "file_path": str(video),
                "topic_relevant": True,
                "copyright_status": "owned",
                "provided_by": "user",
            }],
        )
        package_dir = self._package_dir(result)
        validation = json.loads((package_dir / "asset_validation.json").read_text(encoding="utf-8"))
        manifest = json.loads((package_dir / "timeline_manifest.json").read_text(encoding="utf-8"))

        self.assertTrue(validation["items"][0]["magic_valid"])
        self.assertEqual(validation["items"][0]["codec_validation"], "not_performed_phase_2b_gate")
        self.assertEqual(manifest["render_plan"]["codec_validation"], "not_performed_phase_2b_gate")

    def test_non_directory_package_collision_is_blocked(self):
        package_id = self.exporter._package_id(_phase_one_result(), None)
        collision = self.root / "exports" / package_id
        collision.parent.mkdir(parents=True)
        collision.write_text("attacker-controlled file", encoding="utf-8")

        result = self.exporter.run(_phase_one_result())

        self.assertEqual(result["status"], "shorts_editing_package_fallback")
        self.assertIn("non-directory", result["reason"])
        self.assertEqual(collision.read_text(encoding="utf-8"), "attacker-controlled file")

    def test_path_is_validated_before_hash_size_or_magic_read(self):
        outside = self.root.parent / "outside-asset.png"
        directory = self.root / "asset-directory.png"
        directory.mkdir()
        candidates = [
            {"scene_id": 1, "file_path": str(outside), "topic_relevant": True, "copyright_status": "owned", "provided_by": "user"},
            {"scene_id": 2, "file_path": str(directory), "topic_relevant": True, "copyright_status": "owned", "provided_by": "user"},
        ]
        with patch.object(self.exporter, "_file_sha256", wraps=self.exporter._file_sha256) as hash_mock, patch.object(
            self.exporter, "_valid_magic", wraps=self.exporter._valid_magic
        ) as magic_mock:
            result = self.exporter.run(_phase_one_result(), candidates)

        validation = json.loads(
            (self._package_dir(result) / "asset_validation.json").read_text(encoding="utf-8")
        )
        self.assertFalse(validation["items"][0]["render_allowed"])
        self.assertFalse(validation["items"][1]["render_allowed"])
        self.assertEqual(hash_mock.call_count, 0)
        self.assertEqual(magic_mock.call_count, 0)

    def test_symlink_asset_is_rejected_before_read(self):
        link = self.root / "linked.png"
        link.write_bytes(b"\x89PNG\r\n\x1a\ntarget")
        original_is_symlink = Path.is_symlink

        def simulate_symlink(path):
            return path == link or original_is_symlink(path)

        with patch.object(Path, "is_symlink", autospec=True, side_effect=simulate_symlink), patch.object(
            self.exporter, "_file_sha256", wraps=self.exporter._file_sha256
        ) as hash_mock:
            result = self.exporter.run(
                _phase_one_result(),
                [{"scene_id": 1, "file_path": str(link), "topic_relevant": True, "copyright_status": "owned", "provided_by": "user"}],
            )
        validation = json.loads(
            (self._package_dir(result) / "asset_validation.json").read_text(encoding="utf-8")
        )
        self.assertFalse(validation["items"][0]["render_allowed"])
        self.assertTrue(
            any("symlinks are not allowed" in warning for warning in validation["items"][0]["warnings"])
        )
        self.assertEqual(hash_mock.call_count, 0)

    def test_output_redacts_credentials_absolute_paths_and_raw_exceptions(self):
        source = _phase_one_result()
        source["shorts_brief_result"]["api_key"] = "super-secret-key"
        source["shorts_brief_result"]["debug_path"] = str(self.root / "private")
        result = self.exporter.run(source)
        package_dir = self._package_dir(result)
        contracts_text = (package_dir / "source_contracts.json").read_text(encoding="utf-8")

        self.assertNotIn("super-secret-key", contracts_text)
        self.assertIn("[REDACTED]", contracts_text)
        self.assertIn("[REDACTED_PATH]", contracts_text)
        self.assertNotIn(str(self.root), contracts_text)
        self.assertFalse(Path(result["export_root"]).is_absolute())

        with patch.object(ShortsExporter, "_write_json", side_effect=OSError(str(self.root / "secret-path"))):
            failed = ShortsExporter(self.root / "failure").run(_phase_one_result())
        self.assertEqual(failed["reason"], "Editing package export failed.")
        self.assertNotIn(str(self.root), json.dumps(failed, ensure_ascii=False))
        self.assertEqual(failed["blockers"][0]["code"], "EXPORT_FAILED")

    def test_copy_failure_removes_orphan_and_keeps_staging_manifest_consistent(self):
        source = self.root / "copy.png"
        source.write_bytes(b"\x89PNG\r\n\x1a\ncopy-source")

        def partial_copy(_, destination):
            Path(destination).write_bytes(b"partial")
            raise OSError("raw path must not escape")

        with patch("modules.shorts.shorts_exporter.shutil.copy2", side_effect=partial_copy):
            result = self.exporter.run(
                _phase_one_result(),
                [{"scene_id": 1, "file_path": str(source), "topic_relevant": True, "copyright_status": "owned", "provided_by": "user"}],
            )
        package_dir = self._package_dir(result)
        validation = json.loads((package_dir / "asset_validation.json").read_text(encoding="utf-8"))
        self.assertEqual(validation["items"][0]["validation_status"], "asset_copy_failed")
        self.assertEqual(list((package_dir / "assets").iterdir()), [])
        self.assertNotIn(str(self.root), json.dumps(validation, ensure_ascii=False))

    def test_backup_cleanup_failure_restores_old_package_with_blocker(self):
        first = self.exporter.run(_phase_one_result())
        package_dir = self._package_dir(first)
        marker = package_dir / "old-marker.txt"
        marker.write_text("old", encoding="utf-8")
        original_remove = self.exporter._remove_internal_tree

        def fail_backup_cleanup(path):
            if ".backup-" in path.name:
                raise OSError("cleanup denied")
            return original_remove(path)

        with patch.object(self.exporter, "_remove_internal_tree", side_effect=fail_backup_cleanup):
            result = self.exporter.run(_phase_one_result(), overwrite=True)

        self.assertEqual(result["status"], "shorts_editing_package_fallback")
        self.assertEqual(marker.read_text(encoding="utf-8"), "old")
        self.assertIn("BACKUP_CLEANUP_FAILED", {item["code"] for item in result["blockers"]})
        self.assertEqual(list(self.exporter.export_root.glob(".*.backup-*")), [])

    def test_atomic_restore_failure_is_structured_and_never_exposes_raw_error(self):
        first = self.exporter.run(_phase_one_result())
        with patch.object(self.exporter, "_remove_internal_tree", side_effect=OSError("backup raw")), patch.object(
            self.exporter, "_remove_final_tree", side_effect=OSError("restore raw")
        ):
            result = self.exporter.run(_phase_one_result(), overwrite=True)

        self.assertEqual(result["status"], "shorts_editing_package_fallback")
        self.assertIn("ATOMIC_RESTORE_FAILED", {item["code"] for item in result["blockers"]})
        self.assertNotIn("backup raw", json.dumps(result))
        self.assertNotIn("restore raw", json.dumps(result))

    def test_package_id_is_independent_of_asset_paths_and_input_order(self):
        first_a = self.root / "first-a.png"
        first_b = self.root / "first-b.png"
        second_a = self.root / "second-a.png"
        second_b = self.root / "second-b.png"
        for path, content in ((first_a, b"A"), (second_a, b"A"), (first_b, b"B"), (second_b, b"B")):
            path.write_bytes(b"\x89PNG\r\n\x1a\n" + content)
        assets_one = [
            {"scene_id": 1, "file_path": str(first_a), "topic_relevant": True, "copyright_status": "owned", "provided_by": "user"},
            {"scene_id": 2, "file_path": str(first_b), "topic_relevant": True, "copyright_status": "owned", "provided_by": "user"},
        ]
        assets_two = [
            {"scene_id": 2, "file_path": str(second_b), "topic_relevant": True, "copyright_status": "owned", "provided_by": "user"},
            {"scene_id": 1, "file_path": str(second_a), "topic_relevant": True, "copyright_status": "owned", "provided_by": "user"},
        ]
        captions_reordered = _phase_one_result()
        captions_reordered["shorts_caption_result"]["captions"].reverse()

        one = self.exporter.run(_phase_one_result(), assets_one)
        two = ShortsExporter(self.root / "other").run(captions_reordered, assets_two)
        self.assertEqual(one["package_id"], two["package_id"])


if __name__ == "__main__":
    unittest.main()
