import json
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

from modules.knowledge.pattern_contract import Pattern, PatternStatus, parse_version
from modules.knowledge.pattern_registry import PatternRegistry, PatternRegistryError


NOW = "2026-07-12T12:00:00+09:00"


def pattern(**overrides):
    data = {
        "pattern_id": "pat-api-first",
        "name": "API first",
        "domain": "integration",
        "source_claim_ids": ["claim-001"],
        "preconditions": ["An official API is available"],
        "recommended_action": "Use the official API before browser automation.",
        "prohibited_actions": ["Bypass access controls"],
        "success_metrics": ["API feasibility recorded"],
        "failure_signals": ["API capability is missing"],
        "confidence": 0.8,
        "status": PatternStatus.CANDIDATE,
        "version": "1.0.0",
        "reviewed_at": None,
        "owner_skill": "ai-content-os-knowledge-intelligence",
        "supersedes": None,
        "expires_at": None,
    }
    data.update(overrides)
    return Pattern(**data)


class PatternContractTests(unittest.TestCase):
    def test_accepts_exact_schema(self):
        self.assertEqual(pattern().pattern_id, "pat-api-first")

    def test_round_trip_dict(self):
        item = pattern()
        self.assertEqual(Pattern.from_dict(item.to_dict()).to_dict(), item.to_dict())

    def test_missing_field_rejected(self):
        raw = pattern().to_dict()
        raw.pop("domain")
        with self.assertRaises(ValueError):
            Pattern.from_dict(raw)

    def test_unknown_field_rejected(self):
        raw = pattern().to_dict()
        raw["approval"] = True
        with self.assertRaises(ValueError):
            Pattern.from_dict(raw)

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValueError):
            pattern(status="ACTIVE")

    def test_all_statuses_supported(self):
        for status in PatternStatus:
            kwargs = {"status": status}
            if status is PatternStatus.PROMOTED:
                kwargs["reviewed_at"] = NOW
            self.assertEqual(pattern(**kwargs).status, status)

    def test_confidence_zero_allowed(self):
        self.assertEqual(pattern(confidence=0).confidence, 0.0)

    def test_confidence_one_allowed(self):
        self.assertEqual(pattern(confidence=1).confidence, 1.0)

    def test_confidence_below_zero_rejected(self):
        with self.assertRaises(ValueError):
            pattern(confidence=-0.01)

    def test_confidence_above_one_rejected(self):
        with self.assertRaises(ValueError):
            pattern(confidence=1.01)

    def test_boolean_confidence_rejected(self):
        with self.assertRaises(ValueError):
            pattern(confidence=True)

    def test_non_numeric_version_rejected(self):
        with self.assertRaises(ValueError):
            pattern(version="v1")

    def test_version_is_numeric_tuple(self):
        self.assertEqual(parse_version("2.10.3"), (2, 10, 3))

    def test_bad_datetime_rejected(self):
        with self.assertRaises(ValueError):
            pattern(reviewed_at="yesterday")

    def test_self_supersedes_rejected(self):
        with self.assertRaises(ValueError):
            pattern(supersedes="pat-api-first")

    def test_promoted_requires_sources(self):
        with self.assertRaises(ValueError):
            pattern(status="PROMOTED", source_claim_ids=[], reviewed_at=NOW)

    def test_promoted_requires_success_metrics(self):
        with self.assertRaises(ValueError):
            pattern(status="PROMOTED", success_metrics=[], reviewed_at=NOW)

    def test_promoted_requires_human_review_timestamp(self):
        with self.assertRaises(ValueError):
            pattern(status="PROMOTED", reviewed_at=None)

    def test_lists_deduplicate_preserving_order(self):
        item = pattern(source_claim_ids=["claim-2", "claim-1", "claim-2"])
        self.assertEqual(item.source_claim_ids, ["claim-2", "claim-1"])

    def test_empty_recommended_action_rejected(self):
        with self.assertRaises(ValueError):
            pattern(recommended_action="  ")


class PatternRegistryTests(unittest.TestCase):
    def setUp(self):
        self.path = Path("memory-pattern-registry.jsonl")
        class MemoryRegistry(PatternRegistry):
            def __init__(self, path):
                super().__init__(path)
                self.records = []

            def load_all(self):
                self._validate_history(self.records)
                return list(self.records)

            def _append_safely(self, item):
                self.records.append(item)

        self.registry = MemoryRegistry(self.path)

    def _reach_verified(self, pattern_id="pat-api-first"):
        self.registry.register(pattern(pattern_id=pattern_id))
        verified = pattern(pattern_id=pattern_id, status="VERIFIED", version="1.1.0", reviewed_at=NOW)
        self.registry.register(verified)
        return verified

    def test_missing_registry_is_empty(self):
        self.assertEqual(self.registry.load_all(), [])

    def test_register_creates_parent_and_file(self):
        self.registry.register(pattern())
        self.assertEqual(len(self.registry.load_all()), 1)

    def test_register_and_get(self):
        self.registry.register(pattern())
        self.assertEqual(self.registry.get("pat-api-first").name, "API first")

    def test_require_unknown_rejected(self):
        with self.assertRaises(PatternRegistryError):
            self.registry.require("missing")

    def test_same_version_rejected(self):
        self.registry.register(pattern())
        with self.assertRaises(PatternRegistryError):
            self.registry.register(pattern())

    def test_lower_version_rejected(self):
        self.registry.register(pattern(version="2.0.0"))
        with self.assertRaises(PatternRegistryError):
            self.registry.register(pattern(version="1.9.9", status="VERIFIED", reviewed_at=NOW))

    def test_trailing_zero_equivalent_version_rejected(self):
        self.registry.register(pattern(version="1"))
        with self.assertRaises(PatternRegistryError):
            self.registry.register(pattern(version="1.0", status="VERIFIED", reviewed_at=NOW))

    def test_valid_candidate_to_verified(self):
        self._reach_verified()
        self.assertEqual(self.registry.get("pat-api-first").status, PatternStatus.VERIFIED)

    def test_candidate_to_promoted_transition_rejected(self):
        self.registry.register(pattern())
        promoted = pattern(status="PROMOTED", version="2.0.0", reviewed_at=NOW)
        with self.assertRaises(PatternRegistryError):
            self.registry.promote(promoted, performance_met=True, human_approved=True)

    def test_candidate_to_deprecated_rejected(self):
        self.registry.register(pattern())
        with self.assertRaises(PatternRegistryError):
            self.registry.register(pattern(status="DEPRECATED", version="2.0.0", reviewed_at=NOW))

    def test_promotion_requires_performance(self):
        self._reach_verified()
        promoted = pattern(status="PROMOTED", version="2.0.0", reviewed_at=NOW)
        with self.assertRaises(PatternRegistryError):
            self.registry.promote(promoted, performance_met=False, human_approved=True)

    def test_promotion_requires_human_approval(self):
        self._reach_verified()
        promoted = pattern(status="PROMOTED", version="2.0.0", reviewed_at=NOW)
        with self.assertRaises(PatternRegistryError):
            self.registry.promote(promoted, performance_met=True, human_approved=False)

    def test_generic_register_cannot_bypass_promotion_gates(self):
        self._reach_verified()
        promoted = pattern(status="PROMOTED", version="2.0.0", reviewed_at=NOW)
        with self.assertRaises(PatternRegistryError):
            self.registry.register(promoted)

    def test_valid_promotion(self):
        self._reach_verified()
        promoted = pattern(status="PROMOTED", version="2.0.0", reviewed_at=NOW)
        self.registry.promote(promoted, performance_met=True, human_approved=True)
        self.assertEqual(self.registry.get("pat-api-first").status, PatternStatus.PROMOTED)

    def test_promoted_to_deprecated(self):
        self._reach_verified()
        promoted = pattern(status="PROMOTED", version="2.0.0", reviewed_at=NOW)
        self.registry.promote(promoted, performance_met=True, human_approved=True)
        self.registry.register(pattern(status="DEPRECATED", version="3.0.0", reviewed_at=NOW))
        self.assertEqual(self.registry.get("pat-api-first").status, PatternStatus.DEPRECATED)

    def test_terminal_rejected_cannot_transition(self):
        self.registry.register(pattern())
        self.registry.register(pattern(status="REJECTED", version="2.0.0", reviewed_at=NOW))
        with self.assertRaises(PatternRegistryError):
            self.registry.register(pattern(status="VERIFIED", version="3.0.0", reviewed_at=NOW))

    def test_semantic_duplicate_rejected(self):
        self.registry.register(pattern())
        with self.assertRaises(PatternRegistryError):
            self.registry.register(pattern(pattern_id="pat-copy", version="1.0.1"))

    def test_different_action_is_not_semantic_duplicate(self):
        self.registry.register(pattern())
        other = pattern(pattern_id="pat-other", recommended_action="Run a feasibility spike first.")
        self.registry.register(other)
        self.assertIsNotNone(self.registry.get("pat-other"))

    def test_unknown_supersedes_target_rejected(self):
        with self.assertRaises(PatternRegistryError):
            self.registry.register(pattern(supersedes="missing"))

    def test_supersedes_cycle_rejected(self):
        b = pattern(pattern_id="pat-b", name="B", recommended_action="Do B")
        self.registry.register(b)
        a = pattern(pattern_id="pat-a", name="A", recommended_action="Do A", supersedes="pat-b")
        self.registry.register(a)
        b2 = pattern(pattern_id="pat-b", name="B", recommended_action="Do B", status="VERIFIED", version="2.0.0", reviewed_at=NOW, supersedes="pat-a")
        with self.assertRaises(PatternRegistryError):
            self.registry.register(b2)

    def test_corrupt_json_rejected_with_line(self):
        disk_registry = PatternRegistry(self.path)
        with patch.object(Path, "exists", return_value=True), patch.object(
            Path, "open", mock_open(read_data="{bad json}\n")
        ):
            with self.assertRaisesRegex(PatternRegistryError, "line 1"):
                disk_registry.load_all()

    def test_blank_lines_are_ignored(self):
        data = "\n" + json.dumps(pattern().to_dict()) + "\n\n"
        with patch.object(Path, "exists", return_value=True), patch.object(
            Path, "open", mock_open(read_data=data)
        ):
            self.assertEqual(len(PatternRegistry(self.path).load_all()), 1)

    def test_current_returns_highest_version(self):
        self._reach_verified()
        self.assertEqual(self.registry.current()["pat-api-first"].version, "1.1.0")

    def test_list_can_include_history(self):
        self._reach_verified()
        self.assertEqual(len(self.registry.list_patterns(current_only=False)), 2)

    def test_list_filters_current_status(self):
        self._reach_verified()
        self.registry.register(pattern(pattern_id="pat-other", name="Other", recommended_action="Do another thing"))
        results = self.registry.list_patterns(status=PatternStatus.VERIFIED)
        self.assertEqual([item.pattern_id for item in results], ["pat-api-first"])

    def test_append_keeps_valid_jsonl(self):
        self.registry.register(pattern())
        self.registry.register(pattern(pattern_id="pat-other", name="Other", recommended_action="Do another thing"))
        lines = [json.dumps(item.to_dict()) for item in self.registry.load_all()]
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(isinstance(json.loads(line), dict) for line in lines))


if __name__ == "__main__":
    unittest.main()
