import json
import tempfile
import unittest
from pathlib import Path

from modules.knowledge.pattern_contract import Pattern, PatternStatus
from modules.knowledge.pattern_registry import PatternRegistry
from scripts.import_instagram_learning_patterns import (
    ALLOWED_EVIDENCE_STATUSES,
    ImportValidationError,
    build_pattern,
    compute_dataset_hash,
    load_candidates,
    load_raw_urls,
    parse_preconditions,
    run_import,
    LEARNING_CANDIDATES_PATH,
    RAW_OBSERVATIONS_PATH,
)


DM_CTA_TEXT = "댓글에 특정 키워드를 남기면 DM으로 자료를 보내주는 CTA가 있는 게시물은 댓글:좋아요 비율이 반복적으로 높게 나타난다"
OTHER_TEXT = "번호형 큐레이션 리스트 구조(장소/계정/제품 N개 나열, 각 항목 동일 포맷 반복)는 여행·지역, 생활정보, 유머·이슈 분야에서 공통적으로 나타난다"


def _candidate(**overrides):
    data = {
        "candidate": OTHER_TEXT,
        "evidence_urls": [
            "https://www.instagram.com/p/DZZko8HESg3/",
            "https://www.instagram.com/p/DMR7KeXyMRs/",
            "https://www.instagram.com/p/DZ1m16hEoJS/",
        ],
        "observation_count": 3,
        "account_count": 3,
        "category_count": 3,
        "confidence": "benchmark_observed",
        "note": "structure repeats across three categories",
    }
    data.update(overrides)
    return data


def _dm_candidate(**overrides):
    data = {
        "candidate": DM_CTA_TEXT,
        "evidence_urls": [
            "https://www.instagram.com/p/DaCzy3oD-RH/",
            "https://www.instagram.com/p/DYUI6eKk80S/",
        ],
        "observation_count": 11,
        "account_count": 11,
        "category_count": 2,
        "confidence": "benchmark_observed",
        "note": "comment:like ratio repeatedly elevated",
    }
    data.update(overrides)
    return data


class DatasetHashTests(unittest.TestCase):
    def test_hash_is_deterministic_and_content_addressed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "raw.json"
            path.write_text('{"a": 1}', encoding="utf-8")
            first = compute_dataset_hash(path)
            second = compute_dataset_hash(path)
            self.assertEqual(first, second)
            self.assertTrue(first.startswith("sha256:"))

            path.write_text('{"a": 2}', encoding="utf-8")
            third = compute_dataset_hash(path)
            self.assertNotEqual(first, third)

    def test_real_source_files_are_readable(self):
        # Guards against the script's paths silently drifting from the actual
        # external_workclaude layout without touching/modifying those files.
        self.assertTrue(RAW_OBSERVATIONS_PATH.is_file())
        self.assertTrue(LEARNING_CANDIDATES_PATH.is_file())
        urls = load_raw_urls(RAW_OBSERVATIONS_PATH)
        self.assertGreaterEqual(len(urls), 39)
        candidates = load_candidates(LEARNING_CANDIDATES_PATH)
        self.assertGreaterEqual(len(candidates), 1)


class BuildPatternTests(unittest.TestCase):
    def setUp(self):
        self.raw_urls = load_raw_urls(RAW_OBSERVATIONS_PATH)
        self.dataset_hash = "sha256:deadbeef"

    def test_status_standard_only_two_values_accepted(self):
        self.assertEqual(ALLOWED_EVIDENCE_STATUSES, {"benchmark_observed", "hypothesis_only"})

    def test_disallowed_evidence_status_rejected(self):
        for bad in ("validated", "proven", "confirmed", "candidate"):
            with self.assertRaises(ImportValidationError):
                build_pattern(
                    _candidate(confidence=bad), dataset_hash=self.dataset_hash, raw_urls=self.raw_urls
                )

    def test_unresolvable_evidence_url_rejected(self):
        with self.assertRaises(ImportValidationError):
            build_pattern(
                _candidate(evidence_urls=["https://www.instagram.com/p/DOES_NOT_EXIST/"]),
                dataset_hash=self.dataset_hash,
                raw_urls=self.raw_urls,
            )

    def test_non_integer_counts_rejected(self):
        with self.assertRaises(ImportValidationError):
            build_pattern(
                _candidate(observation_count="3"), dataset_hash=self.dataset_hash, raw_urls=self.raw_urls
            )

    def test_ordinary_candidate_is_content_pattern_domain(self):
        pattern = build_pattern(_candidate(), dataset_hash=self.dataset_hash, raw_urls=self.raw_urls)
        self.assertEqual(pattern.domain, "content_pattern")
        self.assertEqual(pattern.status, PatternStatus.CANDIDATE)
        self.assertEqual(pattern.confidence, 0.5)

    def test_hypothesis_only_maps_to_lower_confidence(self):
        pattern = build_pattern(
            _candidate(confidence="hypothesis_only"), dataset_hash=self.dataset_hash, raw_urls=self.raw_urls
        )
        self.assertEqual(pattern.confidence, 0.25)

    def test_evidence_urls_preserved_verbatim_as_source_claim_ids(self):
        candidate = _candidate()
        pattern = build_pattern(candidate, dataset_hash=self.dataset_hash, raw_urls=self.raw_urls)
        self.assertEqual(pattern.source_claim_ids, candidate["evidence_urls"])

    def test_counts_and_dataset_hash_preserved_in_preconditions(self):
        candidate = _candidate()
        pattern = build_pattern(candidate, dataset_hash=self.dataset_hash, raw_urls=self.raw_urls)
        markers = parse_preconditions(pattern.preconditions)
        self.assertEqual(markers["observation_count"], "3")
        self.assertEqual(markers["account_count"], "3")
        self.assertEqual(markers["category_count"], "3")
        self.assertEqual(markers["dataset_hash"], self.dataset_hash)
        self.assertEqual(markers["evidence_status"], "benchmark_observed")
        self.assertIn("import_version", markers)

    def test_dm_cta_is_engagement_mechanic_not_content_pattern(self):
        pattern = build_pattern(_dm_candidate(), dataset_hash=self.dataset_hash, raw_urls=self.raw_urls)
        self.assertEqual(pattern.domain, "engagement_mechanic")
        self.assertIn("pattern.instagram_learning.engagement_mechanic.", pattern.pattern_id)

    def test_dm_cta_carries_risk_flags_marker(self):
        pattern = build_pattern(_dm_candidate(), dataset_hash=self.dataset_hash, raw_urls=self.raw_urls)
        markers = parse_preconditions(pattern.preconditions)
        self.assertEqual(markers["risk_flags"], "manipulation_risk,funnel_risk")

    def test_dm_cta_prohibits_default_recommendation(self):
        pattern = build_pattern(_dm_candidate(), dataset_hash=self.dataset_hash, raw_urls=self.raw_urls)
        joined = " ".join(pattern.prohibited_actions).casefold()
        self.assertIn("default", joined)
        self.assertIn("primary", joined)
        self.assertIn("recommend", pattern.recommended_action.casefold() + joined)

    def test_dm_cta_never_registered_as_promoted_or_validated(self):
        pattern = build_pattern(_dm_candidate(), dataset_hash=self.dataset_hash, raw_urls=self.raw_urls)
        self.assertEqual(pattern.status, PatternStatus.CANDIDATE)
        self.assertNotIn("validated", pattern.recommended_action.casefold())
        self.assertNotIn("proven", pattern.recommended_action.casefold())


class RunImportTests(unittest.TestCase):
    def setUp(self):
        self.raw_urls = load_raw_urls(RAW_OBSERVATIONS_PATH)
        self.dataset_hash = "sha256:fixedforthistest"
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.registry_path = Path(self.tmpdir.name) / "pattern_registry.jsonl"

    def _registry(self) -> PatternRegistry:
        return PatternRegistry(self.registry_path)

    def test_first_run_imports_all_valid_candidates(self):
        candidates = [_candidate(), _dm_candidate()]
        report = run_import(
            self._registry(), candidates, dataset_hash=self.dataset_hash, raw_urls=self.raw_urls
        )
        self.assertEqual(report.attempted, 2)
        self.assertEqual(report.imported, 2)
        self.assertEqual(report.skipped_duplicate, 0)
        self.assertEqual(report.rejected, 0)
        self.assertEqual(report.registry_status_counts, {"CANDIDATE": 2})

    def test_second_run_is_idempotent_no_new_records(self):
        candidates = [_candidate(), _dm_candidate()]
        registry = self._registry()
        run_import(registry, candidates, dataset_hash=self.dataset_hash, raw_urls=self.raw_urls)
        before = self.registry_path.read_bytes()

        second_report = run_import(
            self._registry(), candidates, dataset_hash=self.dataset_hash, raw_urls=self.raw_urls
        )
        after = self.registry_path.read_bytes()

        self.assertEqual(before, after)
        self.assertEqual(second_report.imported, 0)
        self.assertEqual(second_report.skipped_duplicate, 2)
        self.assertEqual(second_report.rejected, 0)

    def test_two_consecutive_idempotency_runs_hold(self):
        candidates = [_candidate()]
        registry = self._registry()
        run_import(registry, candidates, dataset_hash=self.dataset_hash, raw_urls=self.raw_urls)
        snapshot_1 = self.registry_path.read_bytes()
        run_import(self._registry(), candidates, dataset_hash=self.dataset_hash, raw_urls=self.raw_urls)
        snapshot_2 = self.registry_path.read_bytes()
        run_import(self._registry(), candidates, dataset_hash=self.dataset_hash, raw_urls=self.raw_urls)
        snapshot_3 = self.registry_path.read_bytes()
        self.assertEqual(snapshot_1, snapshot_2)
        self.assertEqual(snapshot_2, snapshot_3)

    def test_dry_run_never_writes_to_disk(self):
        candidates = [_candidate()]
        report = run_import(
            self._registry(),
            candidates,
            dataset_hash=self.dataset_hash,
            raw_urls=self.raw_urls,
            dry_run=True,
        )
        self.assertEqual(report.imported, 1)
        self.assertFalse(self.registry_path.exists())

    def test_changed_dataset_hash_is_rejected_not_overwritten(self):
        candidates = [_candidate()]
        registry = self._registry()
        run_import(registry, candidates, dataset_hash=self.dataset_hash, raw_urls=self.raw_urls)
        before = self.registry_path.read_bytes()

        report = run_import(
            self._registry(),
            candidates,
            dataset_hash="sha256:differenthash",
            raw_urls=self.raw_urls,
        )
        after = self.registry_path.read_bytes()

        self.assertEqual(before, after, "registry must be untouched when dataset_hash conflicts")
        self.assertEqual(report.imported, 0)
        self.assertEqual(report.rejected, 1)
        self.assertIn("dataset_hash", report.rejected_items[0].reason)

    def test_invalid_candidate_is_rejected_and_valid_ones_still_import(self):
        candidates = [_candidate(), _candidate(confidence="validated")]
        report = run_import(
            self._registry(), candidates, dataset_hash=self.dataset_hash, raw_urls=self.raw_urls
        )
        self.assertEqual(report.imported, 1)
        self.assertEqual(report.rejected, 1)

    def test_existing_unrelated_registry_data_is_preserved(self):
        registry = self._registry()
        seed = Pattern(
            pattern_id="pattern.pre_existing_seed",
            name="Pre-existing seed pattern",
            domain="governance",
            source_claim_ids=[],
            preconditions=["seeded before import script ran"],
            recommended_action="Keep this record untouched.",
            prohibited_actions=["Deleting or rewriting this record"],
            success_metrics=["Record byte-for-byte unchanged after import"],
            failure_signals=["Record disappears from the registry"],
            confidence=0.5,
            status=PatternStatus.CANDIDATE,
            version="1.0.0",
            reviewed_at=None,
            owner_skill="ai-content-os-cto-review",
            supersedes=None,
            expires_at=None,
        )
        registry.register(seed)

        run_import(self._registry(), [_candidate()], dataset_hash=self.dataset_hash, raw_urls=self.raw_urls)

        reloaded = PatternRegistry(self.registry_path)
        preserved = reloaded.require("pattern.pre_existing_seed")
        self.assertEqual(preserved.to_dict(), seed.to_dict())
        self.assertEqual(len(reloaded.current()), 2)

    def test_real_learning_candidates_file_imports_cleanly(self):
        # End-to-end sanity check against the real, unmodified source file.
        candidates = load_candidates(LEARNING_CANDIDATES_PATH)
        dataset_hash = compute_dataset_hash(RAW_OBSERVATIONS_PATH)
        report = run_import(
            self._registry(), candidates, dataset_hash=dataset_hash, raw_urls=self.raw_urls
        )
        self.assertEqual(report.attempted, len(candidates))
        self.assertEqual(report.rejected, 0)
        self.assertEqual(report.imported, len(candidates))
        self.assertGreaterEqual(report.imported, 1)
        # exactly one of the real candidates is the DM-keyword engagement mechanic
        mechanic_ids = [pid for pid in reloaded_ids(self._registry()) if "engagement_mechanic" in pid]
        self.assertEqual(len(mechanic_ids), 1)


def reloaded_ids(registry: PatternRegistry):
    return list(registry.current().keys())


if __name__ == "__main__":
    unittest.main()
