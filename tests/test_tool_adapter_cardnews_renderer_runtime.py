import json
import copy
from pathlib import Path
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest import mock

from modules.tool_adapters.cardnews_renderer_runtime import (
    CANVAS_PROFILES,
    ENGINE_PACKAGES,
    MAX_RENDER_TIMEOUT_SECONDS,
    MAX_SMOKE_TIMEOUT_SECONDS,
    CardNewsRendererRuntime,
    probe_cardnews_renderer,
)
from modules.card_news.production_controller import (
    BATCH_AUTHORIZED,
    REPRESENTATIVE_AUTHORIZED,
    STATE_SCHEMA_VERSION,
    canonical_hash,
)


DECLARED = {
    "@motion-canvas/2d": "3.17.2",
    "@motion-canvas/core": "3.17.2",
    "@resvg/resvg-js": "2.6.2",
    "fabric": "7.4.0",
    "satori": "0.28.0",
    "esbuild": "0.28.1",
}
HASH_A = "a" * 64
HASH_B = "b" * 64


def authorized_state(mode="representative"):
    rules = [{"claim_id": "OD-CARD-017", "rule": "test", "source": "test"}]
    state = {
        "schema_version": STATE_SCHEMA_VERSION,
        "controller_id": "controller-test",
        "state": REPRESENTATIVE_AUTHORIZED if mode == "representative" else BATCH_AUTHORIZED,
        "batch_hash": HASH_B,
        "hard_rule_evidence": rules,
        "hard_rule_hash": canonical_hash(rules),
        "representatives": {"A": "A-1"},
        "candidate_ids": ["A-1"],
        "accounts": ["A"],
        "local_media_receipt_hashes": {"A-1": [HASH_A]},
        "representative_qa_receipt_ids": {} if mode == "representative" else {"A": "qa-A"},
        "batch_authorization_hash": None if mode == "representative" else "c" * 64,
    }
    state["state_hash"] = canonical_hash(state)
    return state


def render_request(mode="representative"):
    value = {
        "mode": mode,
        "render_request_id": "render-A-1",
        "candidate_id": "A-1",
        "output_set_id": "output-A-1",
        "output_root": r"F:\AI-Content-OS-Data\cardnews\A-1",
        "local_media_receipt_hashes": [HASH_A],
        "input_sha256": HASH_B,
        "canvas_profile": copy.deepcopy(CANVAS_PROFILES["instagram_portrait_4_5"]),
        "slides": [
            {
                "page": 1,
                "width": 1080,
                "height": 1350,
                "tree": {"type": "div", "props": {"children": "짧은 제목"}},
                "media_classification": "generated_editorial",
                "display_label": "AI 연출 이미지",
                "assets": [
                    {
                        "asset_id": "asset-1",
                        "source_width": 1200,
                        "source_height": 1200,
                        "target_bounds": {"x": 50, "y": 150, "width": 900, "height": 1000},
                        "focus_bounds": {"x": 0.2, "y": 0.2, "width": 0.4, "height": 0.4},
                        "crop_strategy": "contain",
                        "protected_subjects": [
                            {
                                "kind": "hair",
                                "source_bounds": {"x": 0.25, "y": 0.1, "width": 0.3, "height": 0.25},
                                "canvas_bounds": {"x": 100, "y": 200, "width": 200, "height": 300},
                            }
                        ],
                    }
                ],
            }
        ],
    }
    if mode == "batch":
        value["representative_qa_receipt_ids"] = {"A": "qa-A"}
    return value


def issued_authorization(state, request):
    candidates = (
        sorted(state["representatives"].values())
        if request["mode"] == "representative"
        else sorted(state["candidate_ids"])
    )
    media = {candidate: list(state["local_media_receipt_hashes"][candidate]) for candidate in candidates}
    body = {
        "schema_version": "cardnews_render_authorization_v1",
        "authorized": True,
        "mode": request["mode"],
        "candidate_ids": candidates,
        "input_sha256": request["input_sha256"],
        "output_root": request["output_root"],
        "expires_at": (datetime.now().astimezone() + timedelta(minutes=10)).isoformat(),
        "controller_state_path": "test-state.json",
        "controller_state_hash": state["state_hash"],
        "controller_id": state["controller_id"],
        "hard_rule_hash": state["hard_rule_hash"],
        "batch_hash": state["batch_hash"],
        "local_media_receipt_hashes": media,
        "local_media_binding_hash": canonical_hash(media),
        "representative_visual_qa_receipt_ids": (
            dict(state["representative_qa_receipt_ids"])
            if request["mode"] == "batch"
            else {}
        ),
        "tooling_authorization": {
            "satori": True,
            "resvg": True,
            "fabric": False,
            "motion": False,
            "renderer": True,
            "scope": request["mode"],
            "representative_qa_gate_satisfied": request["mode"] == "batch",
            "authorization_metadata_only": True,
            "execution_performed": False,
        },
    }
    body["authorization_id"] = f"render-{canonical_hash(body)[:24]}"
    request["output_set_id"] = body["authorization_id"]
    return body


def render_context(mode="representative"):
    state = authorized_state(mode)
    request = render_request(mode)
    authorization = issued_authorization(state, request)
    return state, request, authorization


class CardNewsRendererRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "cardnews-renderer"
        self.root.mkdir()
        self.node = Path(self.temp_dir.name) / "node.exe"
        self.node.write_text("test node placeholder", encoding="utf-8")
        (self.root / "smoke.mjs").write_text("// fixture only", encoding="utf-8")
        (self.root / "production-render.mjs").write_text("// fixture only", encoding="utf-8")
        package = {
            "dependencies": {name: version for name, version in DECLARED.items() if name != "esbuild"},
            "devDependencies": {"esbuild": DECLARED["esbuild"]},
        }
        (self.root / "package.json").write_text(json.dumps(package), encoding="utf-8")
        for package_name, version in DECLARED.items():
            manifest = self.root / "node_modules" / Path(package_name) / "package.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(json.dumps({"name": package_name, "version": version}), encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def runtime(self) -> CardNewsRendererRuntime:
        return CardNewsRendererRuntime(self.root, node_executable=self.node)

    def test_probe_reports_all_four_engines_without_launching_subprocess(self):
        with mock.patch("subprocess.run") as run:
            result = self.runtime().probe()
        self.assertTrue(result["ready"])
        self.assertEqual(result["status"], "ready")
        self.assertEqual(set(result["engines"]), set(ENGINE_PACKAGES))
        self.assertTrue(all(engine["ready"] for engine in result["engines"].values()))
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["boundaries"]["production_render"])
        self.assertFalse(result["boundaries"]["media_output_files"])
        run.assert_not_called()

    def test_probe_blocks_on_missing_or_version_mismatched_package(self):
        manifest = self.root / "node_modules" / "satori" / "package.json"
        manifest.write_text(json.dumps({"version": "0.0.0"}), encoding="utf-8")
        result = self.runtime().probe()
        self.assertFalse(result["ready"])
        self.assertIn("engine_not_ready:satori", result["errors"])
        state = result["engines"]["satori"]["packages"][0]
        self.assertEqual(state["reason"], "version_mismatch")

        manifest.unlink()
        result = self.runtime().probe()
        self.assertFalse(result["engines"]["satori"]["ready"])
        self.assertIn("missing:satori", result["engines"]["satori"]["packages"][0]["reason"])

    def test_probe_blocks_when_package_manifest_smoke_or_node_is_missing(self):
        (self.root / "package.json").unlink()
        (self.root / "smoke.mjs").unlink()
        result = probe_cardnews_renderer(self.root, node_executable=self.root / "missing-node.exe")
        self.assertFalse(result["ready"])
        self.assertIn("missing:package.json", result["errors"])
        self.assertIn("smoke_script_missing", result["errors"])
        self.assertIn("node_not_found", result["errors"])

    def test_smoke_contract_is_fixed_no_shell_and_bounded(self):
        contract = self.runtime().smoke_contract(timeout_seconds=7)
        self.assertEqual(contract["command"], [str(self.node.resolve()), str((self.root / "smoke.mjs").resolve())])
        self.assertEqual(contract["cwd"], str(self.root.resolve()))
        self.assertEqual(contract["timeout_seconds"], 7.0)
        self.assertFalse(contract["shell"])
        self.assertFalse(contract["writes_media_files"])
        with self.assertRaises(ValueError):
            self.runtime().smoke_contract(timeout_seconds=0)
        with self.assertRaises(ValueError):
            self.runtime().smoke_contract(timeout_seconds=MAX_SMOKE_TIMEOUT_SECONDS + 1)

    def test_run_smoke_accepts_only_complete_capability_payload(self):
        payload = {
            "korean_font": True,
            "fabric_browser_bundle_bytes": 120,
            "motion_bundle_bytes": 130,
            "resvg_png_bytes": 140,
            "satori_svg": True,
        }
        runner = mock.Mock(
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout=json.dumps(payload) + "\n", stderr=""
            )
        )
        result = self.runtime().run_smoke(timeout_seconds=6, runner=runner)
        self.assertTrue(result["passed"])
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["payload"], payload)
        _, kwargs = runner.call_args
        self.assertEqual(kwargs["timeout"], 6.0)
        self.assertFalse(kwargs["shell"])
        self.assertFalse(any(path.suffix in {".png", ".svg", ".mp4"} for path in self.root.rglob("*")))

    def test_run_smoke_does_not_invoke_runner_when_probe_is_blocked(self):
        (self.root / "smoke.mjs").unlink()
        runner = mock.Mock()
        result = self.runtime().run_smoke(runner=runner)
        self.assertEqual(result["status"], "blocked")
        runner.assert_not_called()

    def test_run_smoke_reports_timeout_nonzero_and_invalid_payload(self):
        timeout_runner = mock.Mock(side_effect=subprocess.TimeoutExpired(cmd=["node"], timeout=2))
        self.assertEqual(self.runtime().run_smoke(runner=timeout_runner)["status"], "timeout")

        nonzero = mock.Mock(
            return_value=subprocess.CompletedProcess(args=[], returncode=2, stdout="", stderr="failed")
        )
        result = self.runtime().run_smoke(runner=nonzero)
        self.assertEqual(result["reason"], "nonzero_exit")
        self.assertEqual(result["stderr_tail"], "failed")

        invalid = mock.Mock(
            return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout='{"satori_svg": true}\n', stderr="")
        )
        result = self.runtime().run_smoke(runner=invalid)
        self.assertEqual(result["reason"], "invalid_smoke_payload")

    def test_representative_render_contract_binds_controller_media_and_f_output(self):
        state, request, authorization = render_context()
        contract = self.runtime().render_contract(state, request, authorization=authorization)

        self.assertTrue(contract["ready"])
        self.assertTrue(contract["subprocess_allowed"])
        self.assertEqual(
            contract["command"],
            [str(self.node.resolve()), str((self.root / "production-render.mjs").resolve())],
        )
        payload = json.loads(contract["stdin_json"])
        self.assertEqual(payload["authorization"]["controller_state_hash"], state["state_hash"])
        self.assertEqual(payload["local_media_receipt_hashes"], [HASH_A])
        self.assertEqual(payload["canvas_profile"], CANVAS_PROFILES["instagram_portrait_4_5"])
        self.assertEqual(contract["canvas_profile_hash"], payload["canvas_profile_hash"])
        self.assertEqual(contract["invoked_engines"], ["satori", "resvg"])
        self.assertEqual(contract["capability_only_engines"], ["fabric", "motion_canvas"])

    def test_render_blocks_before_subprocess_without_current_authorization_or_media_hashes(self):
        runner = mock.Mock()
        state, request, _ = render_context()
        no_token = self.runtime().run_render(state, request, runner=runner)
        self.assertEqual(no_token["reason"], "issued_render_authorization_required")

        stale = authorized_state()
        stale_request = render_request()
        stale_authorization = issued_authorization(stale, stale_request)
        stale["state_hash"] = "0" * 64
        result = self.runtime().run_render(
            stale, stale_request, authorization=stale_authorization, runner=runner
        )
        self.assertEqual(result["reason"], "controller_authorization_invalid")

        state, request, authorization = render_context()
        request["local_media_receipt_hashes"] = ["d" * 64]
        result = self.runtime().run_render(state, request, authorization=authorization, runner=runner)
        self.assertEqual(result["reason"], "local_media_hash_binding_mismatch")
        runner.assert_not_called()

    def test_render_blocks_non_f_output_external_tree_and_unlabelled_generated_media(self):
        runner = mock.Mock()
        state, request, authorization = render_context()
        request["output_root"] = r"C:\temp\render"
        self.assertEqual(
            self.runtime().run_render(state, request, authorization=authorization, runner=runner)["reason"],
            "render_authorization_output_mismatch",
        )

        state, request, authorization = render_context()
        request["slides"][0]["tree"]["props"]["backgroundImage"] = "url(https://example.com/a.jpg)"
        self.assertEqual(
            self.runtime().run_render(state, request, authorization=authorization, runner=runner)["reason"],
            "slide_tree_invalid_or_external",
        )

        state, request, authorization = render_context()
        request["slides"][0]["display_label"] = ""
        self.assertEqual(
            self.runtime().run_render(state, request, authorization=authorization, runner=runner)["reason"],
            "generated_or_motion_label_missing",
        )
        runner.assert_not_called()

    def test_batch_render_requires_exact_representative_qa_binding(self):
        state, request, authorization = render_context("batch")
        request["representative_qa_receipt_ids"] = {"A": "wrong"}
        blocked = self.runtime().render_contract(state, request, authorization=authorization)
        self.assertEqual(blocked["reason"], "representative_qa_binding_mismatch")

        request["representative_qa_receipt_ids"] = {"A": "qa-A"}
        ready = self.runtime().render_contract(state, request, authorization=authorization)
        self.assertTrue(ready["ready"])

    def test_canvas_profile_is_carousel_wide_and_safe_preview_metadata_is_exact(self):
        state, request, authorization = render_context()
        request["canvas_profile"]["safe_previews"]["central_square"]["y"] = 0
        self.assertEqual(
            self.runtime().render_contract(state, request, authorization=authorization)["reason"],
            "canvas_profile_invalid",
        )

        state, request, authorization = render_context()
        request["slides"][0]["height"] = 1080
        self.assertEqual(
            self.runtime().render_contract(state, request, authorization=authorization)["reason"],
            "carousel_canvas_profile_mismatch",
        )

    def test_center_cover_that_loses_protected_subject_is_blocked_from_render(self):
        state, request, authorization = render_context()
        asset = request["slides"][0]["assets"][0]
        asset["source_width"] = 1600
        asset["source_height"] = 800
        asset["crop_strategy"] = "center_cover"
        asset["focus_bounds"] = {"x": 0.35, "y": 0.2, "width": 0.2, "height": 0.3}
        asset["protected_subjects"][0]["source_bounds"] = {
            "x": 0.05,
            "y": 0.1,
            "width": 0.2,
            "height": 0.25,
        }
        contract = self.runtime().render_contract(state, request, authorization=authorization)
        self.assertTrue(contract["reason"].startswith("center_cover_would_crop_protected_subject"))
        self.assertFalse(contract["subprocess_allowed"])

    def test_motion_slide_is_capability_only_and_cannot_claim_a_motion_render(self):
        state, request, authorization = render_context()
        request["slides"][0]["media_classification"] = "motion_graphic"
        request["slides"][0]["display_label"] = "그래픽 연출"
        contract = self.runtime().render_contract(state, request, authorization=authorization)
        self.assertEqual(contract["reason"], "motion_canvas_not_production_connected")
        self.assertEqual(contract["capability_only_engines"], ["fabric", "motion_canvas"])

    def test_run_render_accepts_only_exact_static_engine_receipt(self):
        state, request, authorization = render_context()
        contract = self.runtime().render_contract(state, request, authorization=authorization)
        expected = json.loads(contract["stdin_json"])
        receipt = {
            "schema_version": "cardnews_renderer_receipt_v1",
            "status": "render_completed_pending_visual_qa",
            "render_request_id": expected["render_request_id"],
            "candidate_id": expected["candidate_id"],
            "mode": expected["mode"],
            "output_set_id": expected["output_set_id"],
            "controller_state_hash": state["state_hash"],
            "batch_hash": state["batch_hash"],
            "hard_rule_hash": state["hard_rule_hash"],
            "local_media_receipt_hashes": [HASH_A],
            "canvas_profile_hash": expected["canvas_profile_hash"],
            "safe_previews": expected["canvas_profile"]["safe_previews"],
            "expected_slide_count": 1,
            "rendered_slide_count": 1,
            "output_root": request["output_root"],
            "output_hashes": {"1": "e" * 64},
            "invoked_engines": ["satori", "resvg"],
            "capability_only_engines": ["fabric", "motion_canvas"],
            "visual_preservation_verified": False,
            "media_labels": [
                {
                    "page": 1,
                    "media_classification": "generated_editorial",
                    "display_label": "AI 연출 이미지",
                }
            ],
            "requires_independent_visual_qa": True,
        }
        runner = mock.Mock(
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout=json.dumps(receipt, ensure_ascii=False), stderr=""
            )
        )
        result = self.runtime().run_render(
            state, request, authorization=authorization, timeout_seconds=7, runner=runner
        )

        self.assertTrue(result["passed"])
        self.assertEqual(result["receipt"]["invoked_engines"], ["satori", "resvg"])
        _, kwargs = runner.call_args
        self.assertEqual(kwargs["input"], contract["stdin_json"])
        self.assertEqual(kwargs["timeout"], 7.0)
        self.assertEqual(kwargs["encoding"], "utf-8")
        self.assertFalse(kwargs["shell"])

        forged = dict(receipt)
        forged["invoked_engines"] = ["satori", "resvg", "fabric", "motion_canvas"]
        invalid_runner = mock.Mock(
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout=json.dumps(forged), stderr=""
            )
        )
        invalid = self.runtime().run_render(
            state, request, authorization=authorization, runner=invalid_runner
        )
        self.assertEqual(invalid["reason"], "invalid_render_receipt")

    def test_render_timeout_is_bounded_and_reported(self):
        with self.assertRaises(ValueError):
            state, request, authorization = render_context()
            self.runtime().render_contract(
                state,
                request,
                authorization=authorization,
                timeout_seconds=MAX_RENDER_TIMEOUT_SECONDS + 1,
            )
        runner = mock.Mock(side_effect=subprocess.TimeoutExpired(cmd=["node"], timeout=1))
        state, request, authorization = render_context()
        result = self.runtime().run_render(
            state,
            request,
            authorization=authorization,
            timeout_seconds=1,
            runner=runner,
        )
        self.assertEqual(result["status"], "timeout")


if __name__ == "__main__":
    unittest.main()
