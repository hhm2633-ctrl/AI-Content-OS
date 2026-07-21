import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.knowledge_query import freshness_of, load_registry, query_knowledge, redact
from scripts.knowledge_validate import main as validate_main, validate_registry


def source(**changes):
    row = {
        "source_id": "src-001", "title": "Official retrieval guide", "source_type": "documentation",
        "original_url": "https://example.com/guide", "local_path": None,
        "received_at": "2026-07-12T00:00:00+00:00", "provided_by": "CTO",
        "user_intent": "retrieval", "content_hash": "sha256:" + "a" * 64,
        "publisher": "Example", "published_at": "2026-07-01T00:00:00+00:00",
        "rights_status": "open", "authority_level": "official", "verification_status": "VERIFIED",
        "analysis_status": "ANALYZED", "summary": "Use a safe knowledge bundle",
        "project_relevance": "Knowledge retrieval", "risks": [], "tags": ["knowledge", "qa"],
        "related_domains": ["research"], "routed_teams": ["Library"],
        "adoption_decision": "ADOPTED", "decision_reason": "Approved",
        "recheck_at": "2027-01-01T00:00:00+00:00", "related_documents": ["docs/guide.md"],
        "status": "VERIFIED",
    }
    row.update(changes)
    return row


def pattern(**changes):
    row = {
        "pattern_id": "pat-001", "name": "Official first", "domain": "research",
        "source_claim_ids": ["src-001"], "preconditions": ["registry exists"],
        "recommended_action": "prefer official", "prohibited_actions": [],
        "success_metrics": ["correct result"], "failure_signals": [], "confidence": 0.9,
        "status": "PROMOTED", "version": "1.0", "reviewed_at": "2026-07-12T00:00:00+00:00",
        "owner_skill": "library", "supersedes": None, "expires_at": "2027-01-01T00:00:00+00:00",
    }
    row.update(changes)
    return row


class KnowledgeFixture(unittest.TestCase):
    def setUp(self):
        base = Path.cwd() / ".codex-test-tmp"
        base.mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="knowledge_query_", dir=base))
        (self.root / "docs").mkdir()
        (self.root / "docs" / "guide.md").write_text("guide", encoding="utf-8")
        self.registry = self.root / "sources.jsonl"
        self.patterns = self.root / "patterns.jsonl"

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write_sources(self, *rows, raw=None):
        text = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
        if raw is not None: text += ("\n" if text else "") + raw
        self.registry.write_text(text + ("\n" if text else ""), encoding="utf-8")

    def write_patterns(self, *rows, raw=None):
        text = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
        if raw is not None: text += ("\n" if text else "") + raw
        self.patterns.write_text(text + ("\n" if text else ""), encoding="utf-8")

    def bundle(self, **filters):
        return query_knowledge(self.registry, patterns_registry=self.patterns, **filters)


class QueryTests(KnowledgeFixture):
    def setUp(self):
        super().setUp(); self.write_sources(source()); self.write_patterns(pattern())

    def test_bundle_shape(self):
        result = self.bundle(); self.assertEqual("KnowledgeBundle", result["bundle_type"]); self.assertTrue(result["read_only"])

    def test_text_filter(self): self.assertEqual(1, self.bundle(text="RETRIEVAL")["count"])
    def test_text_filter_miss(self): self.assertEqual(0, self.bundle(text="absent")["count"])
    def test_tag_filter(self): self.assertEqual(1, self.bundle(tags=["qa"])["count"])
    def test_multiple_tags_are_and(self): self.assertEqual(1, self.bundle(tags=["qa", "knowledge"])["count"])
    def test_missing_tag(self): self.assertEqual(0, self.bundle(tags=["missing"])["count"])
    def test_domain_filter(self): self.assertEqual(1, self.bundle(domains=["research"])["count"])
    def test_status_filter(self): self.assertEqual(1, self.bundle(status=["VERIFIED"])["count"])
    def test_authority_filter(self): self.assertEqual(1, self.bundle(authority=["official"])["count"])
    def test_source_type_filter(self): self.assertEqual(1, self.bundle(source_type=["documentation"])["count"])
    def test_routed_team_filter(self): self.assertEqual(1, self.bundle(routed_team=["library"])["count"])
    def test_fresh_filter(self): self.assertEqual(1, self.bundle(freshness=["fresh"])["count"])

    def test_stale_status(self):
        self.write_sources(source(status="STALE")); result = self.bundle(); self.assertEqual(["src-001"], result["stale"])

    def test_unknown_freshness(self):
        self.write_sources(source(recheck_at=None)); result = self.bundle(); self.assertEqual(["src-001"], result["unknown"])

    def test_official_sorted_first(self):
        other = source(source_id="src-002", title="Community", authority_level="community", content_hash="sha256:" + "b" * 64)
        self.write_sources(other, source()); self.assertEqual("src-001", self.bundle()["sources"][0]["source_id"])

    def test_limit(self):
        self.write_sources(source(), source(source_id="src-002", content_hash="sha256:" + "b" * 64)); self.assertEqual(1, self.bundle(limit=1)["count"])

    def test_related_document(self): self.assertEqual(["docs/guide.md"], self.bundle()["documents"])
    def test_pattern_join(self): self.assertEqual(["pat-001"], self.bundle()["pattern_ids"])

    def test_latest_pattern_version(self):
        self.write_patterns(pattern(status="VERIFIED"), pattern(version="2.0", status="PROMOTED")); self.assertEqual("2.0", self.bundle()["patterns"][0]["version"])

    def test_unrelated_pattern_excluded(self):
        self.write_patterns(pattern(source_claim_ids=["other"])); self.assertEqual([], self.bundle()["patterns"])

    def test_malformed_source_is_fail_safe(self):
        self.write_sources(source(), raw="{bad"); result = self.bundle(); self.assertEqual(1, result["count"]); self.assertEqual("malformed_jsonl", result["diagnostics"][0]["code"])

    def test_malformed_pattern_is_fail_safe(self):
        self.write_patterns(pattern(), raw="{bad"); result = self.bundle(); self.assertEqual(["pat-001"], result["pattern_ids"]); self.assertTrue(result["diagnostics"])

    def test_missing_source_registry(self):
        self.registry.unlink(); self.assertEqual("registry_unavailable", self.bundle()["diagnostics"][0]["code"])

    def test_missing_pattern_registry_does_not_hide_sources(self):
        self.patterns.unlink(); result = self.bundle(); self.assertEqual(1, result["count"]); self.assertTrue(result["diagnostics"])

    def test_redacts_direct_secret(self): self.assertEqual("***REDACTED***", redact({"client_secret": "abc"})["client_secret"])
    def test_redacts_url_token(self): self.assertNotIn("abc", redact("https://x.test/a?token=abc"))
    def test_redacts_private_windows_path(self): self.assertIn("REDACTED_PRIVATE_PATH", redact(r"C:\Users\alice\secret.txt"))
    def test_redacts_private_path_with_spaced_username(self): self.assertEqual("[REDACTED_PRIVATE_PATH]", redact(r"C:\Users\name with spaces\secret.txt"))
    def test_risk_contradiction_surface(self):
        self.write_sources(source(risks=["contradicts prior policy"])); self.assertEqual(["contradicts prior policy"], self.bundle()["contradictions"])

    def test_freshness_explicit(self): self.assertEqual("stale", freshness_of({"freshness": "stale"}))
    def test_non_object_row_diagnostic(self):
        self.registry.write_text("[]\n", encoding="utf-8"); rows, diagnostics = load_registry(self.registry); self.assertEqual([], rows); self.assertTrue(diagnostics)

    def test_compact_registry_name_and_related_docs(self):
        compact = {"source_id": "compact-1", "name": "Official compact guide", "locator": "docs/guide.md",
                   "tags": ["qa"], "authority": "official", "status": "available",
                   "related_docs": ["docs/guide.md"], "routed_team": "Library", "recheck": "on_update"}
        self.write_sources(compact)
        result = self.bundle(text="compact", routed_team=["library"])
        self.assertEqual(1, result["count"]); self.assertEqual(["docs/guide.md"], result["documents"])


class ValidatorTests(KnowledgeFixture):
    def setUp(self):
        super().setUp(); self.write_sources(source()); self.write_patterns(pattern())

    def report(self):
        return validate_registry(self.registry, root=self.root, patterns_path=self.patterns, now=datetime(2026, 7, 12, tzinfo=timezone.utc))

    def codes(self): return {item["code"] for item in self.report()["findings"]}
    def test_valid_registry_go(self):
        report = self.report(); self.assertEqual("GO", report["status"], report["findings"])

    def test_duplicate_id(self):
        self.write_sources(source(), source(content_hash="sha256:" + "b" * 64)); self.assertIn("DUPLICATE_ID", self.codes())

    def test_broken_document(self):
        self.write_sources(source(related_documents=["docs/missing.md"])); self.assertIn("BROKEN_DOCUMENT", self.codes())

    def test_missing_field(self):
        row = source(); del row["title"]; self.write_sources(row); self.assertIn("MISSING_REQUIRED_FIELD", self.codes())

    def test_missing_status(self):
        row = source(); del row["status"]; self.write_sources(row); self.assertIn("MISSING_STATUS", self.codes())

    def test_invalid_status(self):
        self.write_sources(source(status="UNKNOWN")); self.assertIn("INVALID_STATUS", self.codes())

    def test_stale_entry_warning(self):
        self.write_sources(source(status="STALE")); self.assertIn("STALE_ENTRY", self.codes())

    def test_token_url(self):
        self.write_sources(source(original_url="https://example.com/?token=secret")); self.assertIn("TOKEN_BEARING_URL", self.codes())

    def test_secret_text(self):
        self.write_sources(source(summary="api_key=secret")); self.assertIn("SECRET_TEXT", self.codes())

    def test_copyright_blob(self):
        self.write_sources(source(rights_status="unknown", summary="copyright " + "x" * 2100)); self.assertIn("COPYRIGHTED_BLOB", self.codes())

    def test_malformed_source_jsonl(self):
        self.write_sources(source(), raw="{"); self.assertIn("MALFORMED_JSONL", self.codes())

    def test_duplicate_pattern_version(self):
        self.write_patterns(pattern(), pattern()); self.assertIn("DUPLICATE_PATTERN_VERSION", self.codes())

    def test_promoted_pattern_orphan(self):
        self.write_patterns(pattern(source_claim_ids=["missing"])); self.assertIn("PROMOTED_PATTERN_ORPHAN", self.codes())

    def test_malformed_pattern_jsonl(self):
        self.write_patterns(pattern(), raw="{"); self.assertIn("MALFORMED_JSONL", self.codes())

    def test_expired_pattern_warning(self):
        self.write_patterns(pattern(expires_at="2026-01-01T00:00:00+00:00")); self.assertIn("STALE_PATTERN", self.codes())

    def test_unsafe_document_path(self):
        self.write_sources(source(related_documents=["../secret.md"])); self.assertIn("UNSAFE_DOCUMENT_PATH", self.codes())

    def test_missing_registry_no_go(self):
        self.registry.unlink(); self.assertEqual("NO-GO", self.report()["status"])

    def test_validator_cli_nonzero_on_no_go(self):
        self.registry.unlink(); self.assertEqual(1, validate_main(["--registry", str(self.registry), "--patterns", str(self.patterns), "--root", str(self.root)]))


if __name__ == "__main__":
    unittest.main()
