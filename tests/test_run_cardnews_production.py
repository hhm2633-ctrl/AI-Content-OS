from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from PIL import Image

from scripts.run_cardnews_production import (
    _expected_slides,
    command_accept_visual_qa,
    command_bind_rules,
    command_execute_render_adapter,
    command_init,
    command_issue_render,
    command_record_render,
    command_transition,
)
from modules.card_news.production_controller import ProductionControllerError, canonical_hash


def _package(account: str) -> dict:
    candidate_id = f"candidate-{account.lower()}"
    return {
        "candidate": {"candidate_id": candidate_id, "account": account},
        "slide_count": 1,
        "story": {"summary": "source-bound story"},
        "evidence": {"sources": [{"url": f"https://example.com/{account.lower()}"}]},
        "slides": [{"page": 1, "role": "hook", "headline": "Short", "body": "One sentence"}],
        "feed_caption": "Separate natural feed caption",
        "media_plan": [{"page": 1, "slide_role": "hook", "media_type": "editorial"}],
    }


def _local_media_receipts(candidate_ids: list[str], source_root: Path) -> dict[str, list[dict]]:
    receipts: dict[str, list[dict]] = {}
    source_root.mkdir(parents=True, exist_ok=True)
    for candidate_id in candidate_ids:
        source_path = source_root / f"{candidate_id}.bin"
        source_path.write_bytes(f"source:{candidate_id}".encode("utf-8"))
        import hashlib

        body = {
            "schema_version": "local_media_pre_render_receipt.v1",
            "status": "completed",
            "request_id": f"prepare-{candidate_id}",
            "asset_id": f"asset-{candidate_id}",
            "owner_selected": True,
            "rights_cleared": True,
            "source": {
                "path": str(source_path),
                "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
                "preserved": True,
            },
            "output_root": "F:/AI-Content-OS-Data/external_tools/outputs/local_media_pipeline",
            "operations": [{"operation": "openclip", "status": "completed"}],
            "source_modified": False,
            "tools_executed": True,
            "pre_render_prepared": True,
            "implicit_execution": False,
        }
        body["receipt_hash"] = canonical_hash(body)
        receipts[candidate_id] = [body]
    return receipts


class RunCardnewsProductionTests(unittest.TestCase):
    def _write(self, path: Path, payload: object) -> Path:
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def _visual_receipt(self, output_set_id: str, candidate: str, account: str, image: Path) -> dict:
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        return {
            "schema_version": "cardnews_visual_qa_receipt_v1",
            "receipt_id": f"qa-{output_set_id}-{candidate}",
            "output_set_id": output_set_id,
            "reviewed_at": "2026-07-19T18:00:00+09:00",
            "maker": {"id": "renderer"},
            "reviewer": {"id": "independent-visual-qa", "independent_from_maker": True},
            "scope": {"kind": "representative", "accounts": [account], "candidate_ids": [candidate]},
            "feed_caption": "Separate natural feed caption",
            "slides": [{
                "candidate_id": candidate,
                "page": 1,
                "image_path": str(image),
                "image_sha256": digest,
                "findings": {
                    "mobile_readability": "pass",
                    "copy_readability": "pass",
                    "copy_density_ok": "pass",
                    "image_is_primary": "pass",
                    "content_not_blank": "pass",
                    "subject_focus": "pass",
                    "subject_crop_preserved": "pass",
                    "comment_readability": "not_applicable",
                    "story_progression": "pass",
                },
            }],
            "decision": "approve",
        }

    def _authorized_single_candidate(self, root: Path) -> tuple[Path, Path, dict, Path]:
        packages = self._write(root / "packages.json", [_package("A")])
        directives = self._write(root / "directives.json", {"directives": [
            {"claim_id": claim_id, "owner_approved": True, "rule": f"rule {claim_id}"}
            for claim_id in ("OD-CARD-017", "OD-CARD-018", "OD-CARD-019", "OD-CARD-020")
        ]})
        state_path = root / "state.json"
        command_init(SimpleNamespace(packages=packages, state=state_path, controller_id="controller-adapter"))
        command_bind_rules(SimpleNamespace(state=state_path, receipt_id="rules-adapter", directives=directives))
        representatives = self._write(root / "representatives.json", {
            "representatives": {"A": "candidate-a"},
            "local_media_receipts": _local_media_receipts(["candidate-a"], root / "sources"),
        })
        command_transition(SimpleNamespace(
            state=state_path,
            transition="authorize_representatives",
            receipt_id="reps-adapter",
            payload=representatives,
        ))
        fragments = root / "fragments"
        fragments.mkdir()
        self._write(fragments / "account_A.json", {"records": []})
        output_root = root / "rendered"
        authorization_path = root / "authorization.json"
        authorization = command_issue_render(SimpleNamespace(
            state=state_path,
            mode="representative",
            input_root=fragments,
            output_root=output_root,
            authorization=authorization_path,
            ttl_minutes=10,
            allow_non_f_test_output=True,
        ))
        return state_path, authorization_path, authorization, output_root

    def _adapter_request(self, root: Path, authorization: dict, package_path: Path) -> dict:
        return {
            "schema_version": "cardnews_renderer_request_v1",
            "render_request_id": "request-candidate-a",
            "candidate_id": "candidate-a",
            "mode": "representative",
            "output_set_id": authorization["authorization_id"],
            "input_sha256": authorization["input_sha256"],
            "output_root": str((root / "rendered" / "candidate-a").resolve()),
            "local_media_receipt_hashes": authorization["local_media_receipt_hashes"]["candidate-a"],
            "package_path": str(package_path),
            "slides": [{"page": 1}],
        }

    def _comment_package(self, path: Path, comment_path: Path, *, eligible: bool, account: str = "A") -> Path:
        comment_image = Path(comment_path)
        comment_item = {
            "text": "테스트 댓글",
            "screenshot_path": str(comment_image),
            "source_url": "https://example.com/comment",
            "is_real_comment": True,
            "comment_slide_eligible": eligible,
            "screenshot_sha256": hashlib.sha256(comment_image.read_bytes()).hexdigest(),
        }
        if not comment_image.exists():
            raise AssertionError(f"missing comment artifact for test: {comment_image}")
        payload = {
            "candidate": {"candidate_id": "candidate-a", "account": account},
            "slide_count": 1,
            "story": {"summary": "comment source-bound story"},
            "evidence": {"sources": [{"url": "https://example.com/comment"}]},
            "slides": [
                {
                    "page": 1,
                    "role": "real_comment",
                    "headline": "댓글 슬라이드",
                    "body": "실제 댓글이 들어갑니다.",
                    "media": f"{comment_image.name} 원본 비율 유지",
                    "media_type": "screenshot",
                }
            ],
            "real_comment_evidence": {"selected": [comment_item]},
            "feed_caption": "테스트 캡션",
        }
        return self._write(path, payload)

    class _PassingRendererRuntime:
        def __init__(self) -> None:
            self.contract_calls = 0
            self.render_calls = 0

        def render_contract(self, state, request, **kwargs):
            self.contract_calls += 1
            return {"ready": True, "subprocess_allowed": True, "reason": None}

        def run_render(self, state, request, **kwargs):
            self.render_calls += 1
            output = Path(request["output_root"]) / "page-001.png"
            output.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (1080, 1350), "white").save(output)
            digest = hashlib.sha256(output.read_bytes()).hexdigest()
            return {
                "status": "passed",
                "passed": True,
                "authorization_id": request["output_set_id"],
                "outputs": [str(output)],
                "receipt": {
                    "candidate_id": request["candidate_id"],
                    "rendered_slide_count": 1,
                    "output_hashes": {"1": digest},
                    "invoked_engines": ["satori", "resvg"],
                },
            }

    class _FailingRendererRuntime(_PassingRendererRuntime):
        def run_render(self, state, request, **kwargs):
            self.render_calls += 1
            return {"status": "failed", "passed": False, "reason": "mock_failure"}

    def test_execute_render_adapter_claims_once_and_routes_manifest_to_record_render(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state_path, authorization_path, authorization, output_root = self._authorized_single_candidate(root)
            package_path = self._write(root / "package-a.json", _package("A"))
            request_path = self._write(
                root / "render-request.json",
                self._adapter_request(root, authorization, package_path),
            )
            manifest_path = root / "manifest.json"
            before_state = state_path.read_bytes()
            runtime = self._PassingRendererRuntime()

            manifest = command_execute_render_adapter(SimpleNamespace(
                state=state_path,
                authorization=authorization_path,
                render_request=request_path,
                manifest=manifest_path,
                timeout_seconds=7.0,
                renderer_runtime=runtime,
            ))

            self.assertEqual(state_path.read_bytes(), before_state)
            self.assertEqual(runtime.contract_calls, 1)
            self.assertEqual(runtime.render_calls, 1)
            self.assertEqual(manifest["renderer_entry"], "cardnews_renderer_runtime")
            self.assertEqual(manifest["records"][0]["candidate_id"], "candidate-a")
            marker = output_root.parent / ".controller_authorizations" / (
                authorization["authorization_id"] + ".consumed.json"
            )
            marker_payload = json.loads(marker.read_text(encoding="utf-8"))
            self.assertEqual(marker_payload["status"], "completed")
            self.assertEqual(marker_payload["manifest_sha256"], hashlib.sha256(manifest_path.read_bytes()).hexdigest())

            with self.assertRaises(ProductionControllerError) as caught:
                command_execute_render_adapter(SimpleNamespace(
                    state=state_path,
                    authorization=authorization_path,
                    render_request=request_path,
                    manifest=root / "replayed-manifest.json",
                    timeout_seconds=7.0,
                    renderer_runtime=runtime,
                ))
            self.assertEqual(caught.exception.reason_code, "render_authorization_reused")
            self.assertEqual(runtime.render_calls, 1)

            state = command_record_render(SimpleNamespace(
                state=state_path,
                manifest=manifest_path,
                authorization=authorization_path,
                receipt_id="adapter-render-recorded",
            ))
            self.assertEqual(state["state"], "representative_render_recorded")
            self.assertEqual(state["used_render_authorization_ids"], [authorization["authorization_id"]])

    def test_execute_render_adapter_fails_when_comment_crop_ineligible(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state_path, authorization_path, authorization, output_root = self._authorized_single_candidate(root)
            bad_comment = root / "comment_001_UNMASKED_FAILED.png"
            Image.new("RGB", (1080, 1350), "black").save(bad_comment)
            package_path = self._comment_package(root / "package-a.json", bad_comment, eligible=False, account="A")
            request = self._adapter_request(root, authorization, package_path)
            request["slides"] = [{"page": 1, "role": "real_comment", "media": f"{bad_comment.name}"}]
            request["real_comment_count"] = 1
            request_path = self._write(root / "render-request.json", request)
            manifest_path = root / "manifest.json"
            runtime = self._PassingRendererRuntime()

            with self.assertRaises(ProductionControllerError) as caught:
                command_execute_render_adapter(SimpleNamespace(
                    state=state_path,
                    authorization=authorization_path,
                    render_request=request_path,
                    manifest=manifest_path,
                    timeout_seconds=7.0,
                    renderer_runtime=runtime,
                ))
            self.assertEqual(caught.exception.reason_code, "visual_qa_comment_slide_ineligible")
            marker = output_root.parent / ".controller_authorizations" / (
                authorization["authorization_id"] + ".consumed.json"
            )
            self.assertEqual(json.loads(marker.read_text(encoding="utf-8"))["status"], "failed")

    def test_execute_render_adapter_fails_when_subject_crop_guard_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state_path, _, authorization, _ = self._authorized_single_candidate(root)
            package_path = self._write(root / "package-a.json", _package("A"))
            request_path = self._write(
                root / "render-request.json",
                self._adapter_request(root, authorization, package_path),
            )

            missing_guard_auth = dict(authorization)
            tooling = dict(missing_guard_auth.get("tooling_authorization", {}))
            tooling.pop("subject_crop_guard", None)
            missing_guard_auth["tooling_authorization"] = tooling
            unhashed = dict(missing_guard_auth)
            unhashed.pop("authorization_id", None)
            missing_guard_auth["authorization_id"] = f"render-{canonical_hash(unhashed)[:24]}"
            missing_guard_auth_path = self._write(root / "missing-subject-crop-guard.json", missing_guard_auth)

            with self.assertRaises(ProductionControllerError) as caught:
                command_execute_render_adapter(SimpleNamespace(
                    state=state_path,
                    authorization=missing_guard_auth_path,
                    render_request=request_path,
                    manifest=root / "manifest.json",
                    timeout_seconds=7.0,
                    renderer_runtime=self._PassingRendererRuntime(),
                ))
            self.assertEqual(caught.exception.reason_code, "render_authorization_subject_crop_guard_missing")

    def test_execute_render_adapter_fails_when_subject_crop_guard_tampered(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state_path, _, authorization, _ = self._authorized_single_candidate(root)
            package_path = self._write(root / "package-a.json", _package("A"))
            request_path = self._write(
                root / "render-request.json",
                self._adapter_request(root, authorization, package_path),
            )

            tampered_auth = dict(authorization)
            tooling = dict(tampered_auth.get("tooling_authorization", {}))
            subject_crop_guard = dict(tooling.get("subject_crop_guard", {}))
            subject_crop_guard["max_subject_outside_ratio"] = 0.99
            tooling["subject_crop_guard"] = subject_crop_guard
            tampered_auth["tooling_authorization"] = tooling
            unhashed = dict(tampered_auth)
            unhashed.pop("authorization_id", None)
            tampered_auth["authorization_id"] = f"render-{canonical_hash(unhashed)[:24]}"
            tampered_auth_path = self._write(root / "tampered-subject-crop-guard.json", tampered_auth)

            with self.assertRaises(ProductionControllerError) as caught:
                command_execute_render_adapter(SimpleNamespace(
                    state=state_path,
                    authorization=tampered_auth_path,
                    render_request=request_path,
                    manifest=root / "manifest.json",
                    timeout_seconds=7.0,
                    renderer_runtime=self._PassingRendererRuntime(),
                ))
            self.assertEqual(caught.exception.reason_code, "render_authorization_subject_crop_guard_invalid")

    def test_expected_slides_rejects_ineligible_comment_crop(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "01.png"
            Image.new("RGB", (1080, 1350), "white").save(image)
            bad_comment = root / "comment_001_UNMASKED_FAILED.png"
            Image.new("RGB", (1080, 1350), "black").save(bad_comment)
            package = self._comment_package(root / "package.json", bad_comment, eligible=False, account="B")
            record = {
                "candidate_id": "candidate-b",
                "account": "B",
                "outputs": [str(image)],
                "package_path": str(package),
                "real_comment_count": 1,
            }
            with self.assertRaises(ProductionControllerError) as caught:
                _expected_slides({"records": [record]})
            self.assertEqual(caught.exception.reason_code, "visual_qa_comment_slide_ineligible")

    def test_execute_render_adapter_failed_run_does_not_mutate_state_and_cannot_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state_path, authorization_path, authorization, output_root = self._authorized_single_candidate(root)
            package_path = self._write(root / "package-a.json", _package("A"))
            request_path = self._write(
                root / "render-request.json",
                self._adapter_request(root, authorization, package_path),
            )
            manifest_path = root / "manifest.json"
            before_state = state_path.read_bytes()
            runtime = self._FailingRendererRuntime()

            with self.assertRaises(ProductionControllerError) as caught:
                command_execute_render_adapter(SimpleNamespace(
                    state=state_path,
                    authorization=authorization_path,
                    render_request=request_path,
                    manifest=manifest_path,
                    timeout_seconds=7.0,
                    renderer_runtime=runtime,
                ))
            self.assertEqual(caught.exception.reason_code, "renderer_adapter_execution_failed")
            self.assertEqual(state_path.read_bytes(), before_state)
            self.assertFalse(manifest_path.exists())
            marker = output_root.parent / ".controller_authorizations" / (
                authorization["authorization_id"] + ".consumed.json"
            )
            self.assertEqual(json.loads(marker.read_text(encoding="utf-8"))["status"], "failed")

            with self.assertRaises(ProductionControllerError) as caught:
                command_execute_render_adapter(SimpleNamespace(
                    state=state_path,
                    authorization=authorization_path,
                    render_request=request_path,
                    manifest=manifest_path,
                    timeout_seconds=7.0,
                    renderer_runtime=runtime,
                ))
            self.assertEqual(caught.exception.reason_code, "render_authorization_reused")
            self.assertEqual(runtime.render_calls, 1)

    def test_execute_render_adapter_rejects_tampered_stale_and_state_reused_authorization_before_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state_path, authorization_path, authorization, _ = self._authorized_single_candidate(root)
            package_path = self._write(root / "package-a.json", _package("A"))
            request_path = self._write(
                root / "render-request.json",
                self._adapter_request(root, authorization, package_path),
            )
            runtime = self._PassingRendererRuntime()

            tampered = dict(authorization)
            tampered["controller_id"] = "tampered"
            tampered_path = self._write(root / "tampered.json", tampered)
            with self.assertRaises(ProductionControllerError) as caught:
                command_execute_render_adapter(SimpleNamespace(
                    state=state_path, authorization=tampered_path, render_request=request_path,
                    manifest=root / "tampered-manifest.json", timeout_seconds=7.0,
                    renderer_runtime=runtime,
                ))
            self.assertEqual(caught.exception.reason_code, "render_authorization_tampered")

            stale = dict(authorization)
            stale["expires_at"] = "2000-01-01T00:00:00+09:00"
            stale.pop("authorization_id")
            stale["authorization_id"] = f"render-{canonical_hash(stale)[:24]}"
            stale_path = self._write(root / "stale.json", stale)
            with self.assertRaises(ProductionControllerError) as caught:
                command_execute_render_adapter(SimpleNamespace(
                    state=state_path, authorization=stale_path, render_request=request_path,
                    manifest=root / "stale-manifest.json", timeout_seconds=7.0,
                    renderer_runtime=runtime,
                ))
            self.assertEqual(caught.exception.reason_code, "render_authorization_expired")

            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["used_render_authorization_ids"] = [authorization["authorization_id"]]
            state_without_hash = dict(state)
            state_without_hash.pop("state_hash", None)
            state["state_hash"] = canonical_hash(state_without_hash)
            self._write(state_path, state)
            with self.assertRaises(ProductionControllerError) as caught:
                command_execute_render_adapter(SimpleNamespace(
                    state=state_path, authorization=authorization_path, render_request=request_path,
                    manifest=root / "reused-manifest.json", timeout_seconds=7.0,
                    renderer_runtime=runtime,
                ))
            self.assertIn(
                caught.exception.reason_code,
                {"render_authorization_reused", "render_authorization_binding_mismatch"},
            )
            self.assertEqual(runtime.render_calls, 0)

    def test_visual_qa_manifest_requires_package_and_identifiable_comment_crop(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "01.png"
            Image.new("RGB", (1080, 1350), "white").save(image)
            record = {
                "candidate_id": "candidate-b",
                "account": "B",
                "outputs": [str(image)],
                "package_path": str(root / "missing-package.json"),
                "real_comment_count": 1,
            }
            with self.assertRaises(ProductionControllerError) as caught:
                _expected_slides({"records": [record]})
            self.assertEqual(caught.exception.reason_code, "visual_qa_package_missing")

            package = self._write(root / "package.json", _package("B"))
            record["package_path"] = str(package)
            with self.assertRaises(ProductionControllerError) as caught:
                _expected_slides({"records": [record]})
            self.assertEqual(caught.exception.reason_code, "visual_qa_comment_crop_missing")

    def test_single_controller_chain_requires_representative_visual_qa_before_batch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            packages = self._write(root / "packages.json", [_package(account) for account in "ABC"])
            directives = self._write(root / "directives.json", {"directives": [
                {"claim_id": claim_id, "owner_approved": True, "rule": f"rule {claim_id}"}
                for claim_id in ("OD-CARD-017", "OD-CARD-018", "OD-CARD-019", "OD-CARD-020")
            ]})
            state_path = root / "state.json"
            command_init(SimpleNamespace(packages=packages, state=state_path, controller_id="controller-1"))
            command_bind_rules(SimpleNamespace(
                state=state_path, receipt_id="rules-1", directives=directives
            ))
            representatives = self._write(root / "representatives.json", {
                "representatives": {"A": "candidate-a", "B": "candidate-b", "C": "candidate-c"},
                "local_media_receipts": _local_media_receipts(
                    ["candidate-a", "candidate-b", "candidate-c"], root / "sources"
                ),
            })
            state = command_transition(SimpleNamespace(
                state=state_path,
                transition="authorize_representatives",
                receipt_id="reps-1",
                payload=representatives,
            ))
            self.assertEqual(state["state"], "representative_authorized")

            fragments = root / "fragments"
            fragments.mkdir()
            for account in "ABC":
                self._write(fragments / f"account_{account}.json", {"records": []})
            output = root / "rendered"
            authorization_path = root / "representative_authorization.json"
            authorization = command_issue_render(SimpleNamespace(
                state=state_path,
                mode="representative",
                input_root=fragments,
                output_root=output,
                authorization=authorization_path,
                ttl_minutes=10,
                allow_non_f_test_output=True,
            ))
            self.assertEqual(set(authorization["candidate_ids"]), {"candidate-a", "candidate-b", "candidate-c"})
            self.assertEqual(set(authorization["local_media_receipt_hashes"]), set(authorization["candidate_ids"]))
            self.assertEqual(authorization["tooling_authorization"]["scope"], "representative")
            self.assertTrue(authorization["tooling_authorization"]["authorization_metadata_only"])

            records = []
            qa_receipts = []
            for account in "ABC":
                candidate = f"candidate-{account.lower()}"
                candidate_dir = output / candidate
                candidate_dir.mkdir(parents=True)
                image = candidate_dir / "01.png"
                Image.new("RGB", (1080, 1350), "white").save(image)
                package_path = self._write(candidate_dir / "package.json", _package(account))
                records.append({
                    "candidate_id": candidate,
                    "account": account,
                    "status": "render_completed_pending_visual_qa",
                    "outputs": [str(image)],
                    "package_path": str(package_path),
                })
                qa_receipts.append(self._visual_receipt(authorization["authorization_id"], candidate, account, image))
            manifest = self._write(root / "manifest.json", {
                "schema_version": "cardnews_render_review_manifest_v2",
                "authorization_id": authorization["authorization_id"],
                "output_set_id": authorization["authorization_id"],
                "controller_state_hash": authorization["controller_state_hash"],
                "batch_hash": authorization["batch_hash"],
                "hard_rule_hash": authorization["hard_rule_hash"],
                "render_mode": "representative",
                "records": records,
            })
            expired_authorization = dict(authorization)
            expired_authorization["expires_at"] = "2000-01-01T00:00:00+09:00"
            expired_authorization.pop("authorization_id")
            expired_authorization["authorization_id"] = (
                f"render-{canonical_hash(expired_authorization)[:24]}"
            )
            expired_path = self._write(root / "expired_authorization.json", expired_authorization)
            with self.assertRaises(ProductionControllerError) as caught:
                command_record_render(SimpleNamespace(
                    state=state_path,
                    manifest=manifest,
                    authorization=expired_path,
                    receipt_id="expired-render",
                ))
            self.assertEqual(caught.exception.reason_code, "render_authorization_expired")
            state = command_record_render(SimpleNamespace(
                state=state_path,
                manifest=manifest,
                authorization=authorization_path,
                receipt_id="render-reps-1",
            ))
            self.assertEqual(state["state"], "representative_render_recorded")
            qa_path = self._write(root / "representative_qa.json", qa_receipts)
            state = command_accept_visual_qa(SimpleNamespace(
                state=state_path, manifest=manifest, qa_receipt=qa_path, receipt_id="qa-reps-1"
            ))
            self.assertEqual(state["state"], "representative_qa_passed")

            batch_payload = self._write(root / "batch.json", {
                "candidate_ids": ["candidate-a", "candidate-b", "candidate-c"],
                "local_media_receipts": _local_media_receipts(
                    ["candidate-a", "candidate-b", "candidate-c"], root / "sources"
                ),
            })
            state = command_transition(SimpleNamespace(
                state=state_path,
                transition="authorize_batch",
                receipt_id="batch-1",
                payload=batch_payload,
            ))
            self.assertEqual(state["state"], "batch_authorized")
            batch_authorization = command_issue_render(SimpleNamespace(
                state=state_path,
                mode="batch",
                input_root=fragments,
                output_root=output,
                authorization=root / "batch_authorization.json",
                ttl_minutes=10,
                allow_non_f_test_output=True,
            ))
            self.assertEqual(
                batch_authorization["representative_visual_qa_receipt_ids"],
                state["representative_qa_receipt_ids"],
            )
            self.assertEqual(batch_authorization["tooling_authorization"]["scope"], "batch")
            batch_manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
            batch_manifest_payload["authorization_id"] = batch_authorization["authorization_id"]
            batch_manifest_payload["output_set_id"] = batch_authorization["authorization_id"]
            batch_manifest_payload["controller_state_hash"] = batch_authorization["controller_state_hash"]
            batch_manifest_payload["batch_hash"] = batch_authorization["batch_hash"]
            batch_manifest_payload["hard_rule_hash"] = batch_authorization["hard_rule_hash"]
            batch_manifest_payload["render_mode"] = "batch"
            batch_manifest = self._write(root / "batch_manifest.json", batch_manifest_payload)
            state = command_record_render(SimpleNamespace(
                state=state_path,
                manifest=batch_manifest,
                authorization=root / "batch_authorization.json",
                receipt_id="render-batch-1",
            ))
            self.assertEqual(state["state"], "batch_render_recorded")

            slides = []
            for record in records:
                image = Path(record["outputs"][0])
                import hashlib
                slides.append({
                    "candidate_id": record["candidate_id"],
                    "page": 1,
                    "image_path": str(image),
                    "image_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                "findings": {
                    "mobile_readability": "pass",
                    "copy_readability": "pass",
                    "copy_density_ok": "pass",
                    "image_is_primary": "pass",
                    "content_not_blank": "pass",
                    "subject_focus": "pass",
                    "subject_crop_preserved": "pass",
                    "comment_readability": "not_applicable",
                    "story_progression": "pass",
                },
                })
            batch_qa = self._write(root / "batch_qa.json", {
                "schema_version": "cardnews_visual_qa_receipt_v1",
                "receipt_id": "qa-batch-1",
                "output_set_id": batch_authorization["authorization_id"],
                "reviewed_at": "2026-07-19T18:30:00+09:00",
                "maker": {"id": "renderer"},
                "reviewer": {"id": "independent-visual-qa", "independent_from_maker": True},
                "scope": {
                    "kind": "batch",
                    "accounts": ["A", "B", "C"],
                    "candidate_ids": ["candidate-a", "candidate-b", "candidate-c"],
                    "representative_receipt_ids": state["representative_qa_receipt_ids"],
                },
                "feed_caption": "Separate natural feed caption",
                "slides": slides,
                "decision": "approve",
            })
            state = command_accept_visual_qa(SimpleNamespace(
                state=state_path, manifest=batch_manifest, qa_receipt=batch_qa, receipt_id="qa-batch-1"
            ))
            self.assertEqual(state["state"], "manual_upload_ready")
            self.assertTrue(state["manual_upload_ready"])


if __name__ == "__main__":
    unittest.main()
