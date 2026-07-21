# AI-Content-OS Knowledge Library

The Knowledge Library is a standalone source of truth for external references, local programs,
policies, and project-authored analysis. It is not connected to `WorkflowEngine`.

## Intake boundary

A registry record is a `SourcePacket`. It stores metadata, a bounded project-authored summary,
classification, routing, and adoption decisions. It must not copy an external document, repository,
caption collection, image, video, or other source in full. URLs and local paths are pointers; rights
and verification state still govern use.

The contract fields are `source_id`, `title`, `source_type`, `original_url`, `local_path`,
`received_at`, `provided_by`, `user_intent`, `content_hash`, `publisher`, `published_at`,
`rights_status`, `authority_level`, `verification_status`, `analysis_status`, `summary`,
`project_relevance`, `risks`, `tags`, `related_domains`, `routed_teams`, `adoption_decision`,
`decision_reason`, `recheck_at`, and `related_documents`.

Lifecycle states are `RECEIVED`, `VERIFIED`, `ANALYZED`, `ROUTED`, `ADOPTED`, `HELD`, `REJECTED`,
and `STALE`. Unknown provenance, rights, metrics, or policy details remain explicit.

## Taxonomy and routing

`taxonomy.json` is a versioned stable schema. Each category has a stable ID, aliases, keywords,
default domains, and deterministic team rules. A source can carry multiple categories, tags,
domains, and teams. Existing normalized tags are preserved and merged with inferred category IDs.
Unknown explicit tags/domains/teams remain in contract-named output fields and dedicated
`unknown_*` fields, but they do not trigger automatic routing.

Classification uses only bounded metadata: title, summary, project relevance, user intent,
publisher, source type, and explicit tags/domains. URLs, Windows paths, secret values, and raw source
bodies are not classification signals.

```python
from modules.knowledge import KnowledgeRouter

result = KnowledgeRouter().classify_and_route({
    "title": "Instagram Reels policy and metric provenance",
    "source_type": "policy",
    "tags": ["reels", "new_unreviewed_tag"],
})
```

The router accepts a mapping or an object with SourcePacket-like attributes and deliberately does
not import contract/registry modules.

## Safety

- Duplicate ID, normalized URL, or content hash must fail closed at registry intake.
- Persistence is deterministic UTF-8 JSONL with atomic replacement.
- Paths, URLs, and secret-bearing inputs are sanitized or rejected before persistence.
- Classification never implies verification, adoption, scraping, media reuse, or publishing rights.
- External APIs, login, scraping, and live publishing remain separate CTO gates.
