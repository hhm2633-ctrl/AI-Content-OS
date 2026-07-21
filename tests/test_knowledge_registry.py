import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.knowledge.knowledge_contract import (
    KnowledgeContractError, SourcePacket, SourceStatus, normalize_local_path,
    normalize_url, validate_source_packet,
)
from modules.knowledge.knowledge_registry import (
    DuplicateSourceError, KnowledgeRegistry, KnowledgeRegistryError,
    RegistryCorruptionError, RegistryWriteError,
)


def packet(**changes):
    value = {
        "source_id": "src-001", "title": "Policy evidence", "source_type": "policy",
        "original_url": "HTTPS://Example.COM/policy?b=2&a=1#frag", "local_path": None,
        "received_at": "2026-07-12T09:00:00+09:00", "provided_by": "CTO",
        "user_intent": "register evidence", "content_hash": "a" * 64,
        "publisher": "Example", "published_at": "2026-07-01T00:00:00Z",
        "rights_status": "link_only", "authority_level": "primary",
        "verification_status": "verified", "analysis_status": "analyzed",
        "summary": "Official policy summary", "project_relevance": "Publishing guard",
        "risks": ["policy drift"], "tags": ["policy", "publishing"],
        "related_domains": ["publishing"], "routed_teams": ["Publishing"],
        "adoption_decision": "HELD", "decision_reason": "Needs recheck",
        "recheck_at": "2026-08-01T00:00:00+09:00",
        "related_documents": ["docs/policy.md"],
    }
    value.update(changes)
    return value


class ContractTests(unittest.TestCase):
    def test_accepts_complete_packet(self): self.assertEqual(validate_source_packet(packet()).source_id, "src-001")
    def test_default_status_received(self): self.assertEqual(validate_source_packet(packet()).status, SourceStatus.RECEIVED)
    def test_all_statuses(self):
        for status in SourceStatus: self.assertEqual(validate_source_packet(packet(status=status.value)).status, status)
    def test_rejects_unknown_status(self):
        with self.assertRaises(KnowledgeContractError): validate_source_packet(packet(status="NEW"))
    def test_rejects_missing_field(self):
        raw = packet(); raw.pop("title")
        with self.assertRaises(KnowledgeContractError): validate_source_packet(raw)
    def test_rejects_unknown_field(self):
        with self.assertRaises(KnowledgeContractError): validate_source_packet(packet(raw_content="forbidden"))
    def test_rejects_non_mapping(self):
        with self.assertRaises(KnowledgeContractError): validate_source_packet([])
    def test_rejects_bad_id(self):
        with self.assertRaises(KnowledgeContractError): validate_source_packet(packet(source_id="x"))
    def test_rejects_bad_hash(self):
        with self.assertRaises(KnowledgeContractError): validate_source_packet(packet(content_hash="abc"))
    def test_normalizes_hash(self): self.assertEqual(validate_source_packet(packet(content_hash="sha256:" + "A"*64)).content_hash, "sha256:" + "a"*64)
    def test_requires_locator(self):
        with self.assertRaises(KnowledgeContractError): validate_source_packet(packet(original_url=None, local_path=None))
    def test_accepts_local_only(self): self.assertEqual(validate_source_packet(packet(original_url=None, local_path="docs\\x.md")).local_path, "docs/x.md")
    def test_rejects_absolute_windows_path(self):
        with self.assertRaises(KnowledgeContractError): normalize_local_path("C:\\secret.txt")
    def test_rejects_unc_path(self):
        with self.assertRaises(KnowledgeContractError): normalize_local_path("\\\\server\\share")
    def test_rejects_parent_traversal(self):
        with self.assertRaises(KnowledgeContractError): normalize_local_path("docs/../secret")
    def test_rejects_non_http_url(self):
        with self.assertRaises(KnowledgeContractError): normalize_url("file:///secret")
    def test_rejects_url_credentials(self):
        with self.assertRaises(KnowledgeContractError): normalize_url("https://user:pass@example.com/x")
    def test_url_is_canonical(self): self.assertEqual(normalize_url("HTTPS://Example.COM/p?b=2&a=1#x"), "https://example.com/p?a=1&b=2")
    def test_url_redacts_secret_query(self): self.assertIn("%2A%2A%2AREDACTED%2A%2A%2A", normalize_url("https://e.com/?token=secret"))
    def test_rejects_naive_timestamp(self):
        with self.assertRaises(KnowledgeContractError): validate_source_packet(packet(received_at="2026-07-12T00:00:00"))
    def test_rejects_bad_timestamp(self):
        with self.assertRaises(KnowledgeContractError): validate_source_packet(packet(received_at="today"))
    def test_lists_are_deduplicated_sorted(self): self.assertEqual(validate_source_packet(packet(tags=["z", "a", "a"])).tags, ("a", "z"))
    def test_rejects_scalar_list(self):
        with self.assertRaises(KnowledgeContractError): validate_source_packet(packet(tags="policy"))
    def test_redacts_secret_in_summary(self): self.assertNotIn("supersecret", validate_source_packet(packet(summary="api_key=supersecret")).summary)
    def test_rejects_full_document_sized_summary(self):
        with self.assertRaises(KnowledgeContractError): validate_source_packet(packet(summary="x" * 16001))
    def test_to_dict_is_json_ready(self): json.dumps(validate_source_packet(packet()).to_dict())
    def test_canonical_hash_is_stable(self): self.assertEqual(validate_source_packet(packet()).canonical_hash, validate_source_packet(packet()).canonical_hash)
    def test_validate_preserves_instance(self):
        item = validate_source_packet(packet()); self.assertIs(validate_source_packet(item), item)


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.path = Path(self.temp.name) / "registry.jsonl"; self.registry = KnowledgeRegistry(self.path)
    def tearDown(self): self.temp.cleanup()
    def test_missing_registry_is_empty(self): self.assertEqual(self.registry.read_all(), [])
    def test_default_write_timeout_is_bounded(self): self.assertEqual(self.registry.write_timeout_seconds, 2.0)
    def test_absolute_write_timeout_cap(self): self.assertEqual(KnowledgeRegistry(self.path, write_timeout_seconds=90).write_timeout_seconds, 30.0)
    def test_custom_write_timeout(self): self.assertEqual(KnowledgeRegistry(self.path, write_timeout_seconds=0.25).write_timeout_seconds, 0.25)
    def test_invalid_write_timeout_fails_closed(self):
        with self.assertRaises(ValueError): KnowledgeRegistry(self.path, write_timeout_seconds=0)
    def test_write_error_contract(self):
        error = RegistryWriteError("failed", error_code="REGISTRY_WRITE_TIMEOUT", timeout_seconds=5.0)
        self.assertEqual((error.status, error.error_code, error.timeout_seconds), ("FAILED", "REGISTRY_WRITE_TIMEOUT", 5.0))
    def test_register_and_get(self): self.registry.register(packet()); self.assertEqual(self.registry.get("src-001").title, "Policy evidence")
    def test_get_missing_is_none(self): self.assertIsNone(self.registry.get("missing"))
    def test_duplicate_id_fails_closed(self):
        self.registry.register(packet())
        with self.assertRaises(DuplicateSourceError): self.registry.register(packet(content_hash="b"*64, original_url="https://e.com/2"))
    def test_duplicate_hash_fails_closed(self):
        self.registry.register(packet())
        with self.assertRaises(DuplicateSourceError): self.registry.register(packet(source_id="src-002", original_url="https://e.com/2"))
    def test_duplicate_canonical_url_fails_closed(self):
        self.registry.register(packet())
        with self.assertRaises(DuplicateSourceError): self.registry.register(packet(source_id="src-002", content_hash="b"*64, original_url="https://example.com/policy?a=1&b=2"))
    def test_deterministic_source_id_order(self):
        self.registry.register(packet(source_id="src-002")); self.registry.register(packet(source_id="src-001", content_hash="b"*64, original_url="https://e.com/1"))
        self.assertEqual([p.source_id for p in self.registry.read_all()], ["src-001", "src-002"])
    def test_deterministic_json_keys(self):
        self.registry.register(packet()); raw = self.path.read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(list(json.loads(raw)), sorted(json.loads(raw)))
    def test_corrupt_json_fails_closed(self):
        self.path.write_text("{bad\n", encoding="utf-8")
        with self.assertRaises(RegistryCorruptionError): self.registry.read_all()
    def test_corrupt_schema_fails_closed(self):
        self.path.write_text(json.dumps({"source_id": "x"}) + "\n", encoding="utf-8")
        with self.assertRaises(RegistryCorruptionError): self.registry.read_all()
    def test_existing_duplicate_file_fails_closed(self):
        item = validate_source_packet(packet()).to_dict(); self.path.write_text(json.dumps(item)+"\n"+json.dumps(item)+"\n", encoding="utf-8")
        with self.assertRaises(DuplicateSourceError): self.registry.read_all()
    def test_replace_updates_packet(self):
        self.registry.register(packet()); self.registry.replace("src-001", packet(title="Updated")); self.assertEqual(self.registry.get("src-001").title, "Updated")
    def test_replace_requires_existing(self):
        with self.assertRaises(KeyError): self.registry.replace("src-001", packet())
    def test_replace_keeps_id_immutable(self):
        self.registry.register(packet())
        with self.assertRaises(KnowledgeRegistryError): self.registry.replace("src-001", packet(source_id="src-002"))
    def test_atomic_failure_preserves_old_registry(self):
        self.registry.register(packet()); before = self.path.read_bytes()
        with patch("modules.knowledge.knowledge_registry.os.replace", side_effect=OSError("fail")):
            with self.assertRaises(KnowledgeRegistryError): self.registry.replace("src-001", packet(title="new"))
        self.assertEqual(self.path.read_bytes(), before)
    def test_query_source_type(self): self.registry.register(packet()); self.assertEqual(len(self.registry.query(source_type="policy")), 1)
    def test_query_status(self): self.registry.register(packet(status="VERIFIED")); self.assertEqual(len(self.registry.query(status=SourceStatus.VERIFIED)), 1)
    def test_query_all_tags(self): self.registry.register(packet()); self.assertEqual(len(self.registry.query(tags=["policy", "publishing"])), 1)
    def test_query_domains(self): self.registry.register(packet()); self.assertEqual(len(self.registry.query(related_domains=["publishing"])), 1)
    def test_query_teams(self): self.registry.register(packet()); self.assertEqual(len(self.registry.query(routed_teams=["Publishing"])), 1)
    def test_query_authority(self): self.registry.register(packet()); self.assertEqual(len(self.registry.query(authority_level="primary")), 1)
    def test_query_verification(self): self.registry.register(packet()); self.assertEqual(len(self.registry.query(verification_status="verified")), 1)
    def test_query_analysis(self): self.registry.register(packet()); self.assertEqual(len(self.registry.query(analysis_status="analyzed")), 1)
    def test_query_adoption(self): self.registry.register(packet()); self.assertEqual(len(self.registry.query(adoption_decision="HELD")), 1)
    def test_query_text_casefold(self): self.registry.register(packet()); self.assertEqual(len(self.registry.query(text="OFFICIAL")), 1)
    def test_query_combines_filters(self): self.registry.register(packet()); self.assertEqual(len(self.registry.query(source_type="policy", tags=["policy"], text="guard")), 1)
    def test_query_mismatch_empty(self): self.registry.register(packet()); self.assertEqual(self.registry.query(tags=["missing"]), [])


if __name__ == "__main__": unittest.main()
