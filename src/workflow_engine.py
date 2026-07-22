import hashlib
import json
import os
import shutil
import time
from pathlib import Path

from modules.ai_planner.planner_module import AIPlannerModule
from modules.ai_planner.planning_context import PlanningContext
from modules.common.metadata_standard import (
    SOURCE_ESTIMATED,
    SOURCE_HISTORICAL,
    SOURCE_LOCAL_QUALITY,
    SOURCE_RUNTIME,
    build_standard_metadata,
)
from modules.common.card_news_output_set import CardNewsOutputSetTransaction
from modules.trend_collector.trend_collector_module import TrendCollectorModule
from modules.topic_engine.topic_engine_module import TopicEngineModule
from modules.pattern_engine.pattern_engine_module import PatternEngineModule
from modules.pattern_engine.pattern_result_writer import PatternResultWriter
from modules.research.research_module import ResearchModule
from modules.content.content_module import ContentModule
from modules.image_strategy.image_strategy_module import ImageStrategyModule
from modules.image_prompt.image_prompt_module import ImagePromptModule
from modules.image_generation.image_generation_module import ImageGenerationModule
from modules.card_news.canvas_contract import is_allowed_card_slide_count
from modules.card_news.card_news_module import CardNewsModule
from modules.publishing.publishing_module import PublishingModule
from modules.knowledge_engine.knowledge_module import KnowledgeModule
from modules.performance_score.performance_score_module import PerformanceScoreModule
from modules.audit_engine.audit_engine_module import AuditEngineModule
from modules.learning_engine.learning_engine_module import LearningEngineModule
from modules.analytics_engine.analytics_engine_module import AnalyticsEngineModule
from modules.brand_dna_engine.brand_dna_engine_module import BrandDNAEngineModule
from modules.trend_memory.trend_memory_module import TrendMemoryModule
from modules.competitor_engine.competitor_engine_module import CompetitorEngineModule
from modules.compliance.card_news_publish_gate import CardNewsPublishGate
from modules.compliance.rights_intake_loader import load_verified_rights_intake
from modules.compliance.manual_image_intake_loader import (
    load_staged_manual_images,
    load_verified_manual_images,
)
from modules.compliance.copy_intake_loader import load_verified_copy_intake


# Content that must never appear in a canonical, release-ready CardNews /
# Publishing / queue payload built via the Copy Intake path -- these are the
# exact stale phrases identified in the CN-006 false-ready incident (a
# different topic's title/headline/generic-safety-fallback copy that had
# been silently deep-copied forward by create_release_revision).
COPY_INTAKE_BANNED_PHRASES = (
    "다이어트",
    "연예인",
    "이 주제, 바로 써도 될까요",
    "제목만으로는 판단 못 합니다",
    "출처부터 다시 확인하세요",
    "확인 전에는 발행하지 마세요",
)


class WorkflowEngine:
    def __init__(self, config=None):
        self.config = config or {}
        self.output_dir = Path("storage/workflow_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.trend_collector = TrendCollectorModule(self.config)
        self.topic_engine = TopicEngineModule(self.config)
        # AI Planner (Sprint 15-3): actually wired in. Runs after TopicEngineModule
        # and before PatternEngineModule as a Hint Layer only - see
        # modules/ai_planner/planner_contract.py (PlannerContract.WORKFLOW_INTEGRATION_NOTE).
        # Its (optional) output is threaded through to Pattern/Content/Image
        # Strategy/Knowledge below, which each decide independently (via
        # PlannerConsumerAdapter) whether to use it - it never replaces their own
        # selection logic.
        self.ai_planner_module = AIPlannerModule(self.config)
        self.pattern_engine = PatternEngineModule(self.config)
        self.research_module = ResearchModule(self.config)
        self.content_module = ContentModule(self.config)
        self.image_strategy_module = ImageStrategyModule(self.config)
        self.image_prompt_module = ImagePromptModule(self.config)
        self.image_generation_module = ImageGenerationModule(self.config)
        self.card_news_module = CardNewsModule(self.config)
        self.publishing_module = PublishingModule(self.config)
        self.knowledge_module = KnowledgeModule(self.config)
        self.performance_score_module = PerformanceScoreModule(self.config)
        self.audit_engine_module = AuditEngineModule(self.config)
        self.learning_engine_module = LearningEngineModule(self.config)
        self.analytics_engine_module = AnalyticsEngineModule(self.config)
        self.brand_dna_engine_module = BrandDNAEngineModule(self.config)
        self.trend_memory_module = TrendMemoryModule(self.config)
        self.competitor_engine_module = CompetitorEngineModule(self.config)

    def run(self):
        print("=" * 50)
        print("Workflow Engine Started")
        print("=" * 50)

        try:
            trend_result = self.trend_collector.run()
            self._save_workflow_result("01_trend_result.json", trend_result)

            topic_result = self.topic_engine.run(trend_result)
            self._save_workflow_result("02_topic_result.json", topic_result)

            # AI Planner (Sprint 15-3): Hint Layer only. Runs after TopicEngineModule,
            # before PatternEngineModule. If it raises or returns nothing usable,
            # planner_result is None and every downstream Engine below runs exactly as
            # it did before this Sprint (see _run_ai_planner()'s try/except).
            planner_result = self._run_ai_planner(trend_result, topic_result)
            self._save_workflow_result("02b_planner_result.json", planner_result or {})

            pattern_result = self._run_pattern_engine(topic_result, trend_result, planner_result)
            self._save_workflow_result("03_pattern_result.json", pattern_result)

            research_result = self.research_module.run(topic_result)
            self._save_workflow_result("04_research_result.json", research_result)

            content_result = self.content_module.run(research_result, planner_result)
            self._save_workflow_result("05_content_result.json", content_result)

            image_strategy_result = self.image_strategy_module.run(content_result, research_result, planner_result)
            self._save_workflow_result("05b_image_strategy_result.json", image_strategy_result)

            image_prompt_result = self.image_prompt_module.run(content_result, image_strategy_result)
            self._save_workflow_result("06_image_prompt_result.json", image_prompt_result)

            image_generation_result = self.image_generation_module.run(image_prompt_result)
            self._save_workflow_result("07_image_generation_result.json", image_generation_result)

            card_news_result, publishing_result, output_set_manifest = (
                self._build_blocked_standard_production_results(image_generation_result)
            )
            self._save_workflow_result("08_card_news_result.json", card_news_result)
            self._save_workflow_result("09_publishing_result.json", publishing_result)

            knowledge_result = self._run_knowledge_engine(
                trend_result=trend_result,
                topic_result=topic_result,
                pattern_result=pattern_result,
                research_result=research_result,
                content_result=content_result,
                image_strategy_result=image_strategy_result,
                card_news_result=card_news_result,
                publishing_result=publishing_result,
                planner_result=planner_result,
            )
            self._save_workflow_result("10_knowledge_result.json", knowledge_result)

            # Trend Memory는 Audit Engine의 duplicate_check가 topic_repeat_risk를
            # 함께 참고할 수 있도록 Performance Score/Audit보다 먼저 실행한다.
            trend_memory_result = self._run_safe(
                "Trend Memory Engine",
                self._empty_trend_memory_result,
                self.trend_memory_module.run,
                pattern_result=pattern_result,
                card_news_result=card_news_result,
                image_strategy_result=image_strategy_result,
            )
            self._save_workflow_result("11_trend_memory_result.json", trend_memory_result)

            performance_score_result = self._run_safe(
                "Performance Score Engine",
                self._empty_performance_score_result,
                self.performance_score_module.run,
                content_result=content_result,
                card_news_result=card_news_result,
                image_strategy_result=image_strategy_result,
            )
            self._save_workflow_result("12_performance_score_result.json", performance_score_result)

            audit_result = self._run_safe(
                "Audit Engine",
                self._empty_audit_result,
                self.audit_engine_module.run,
                content_result=content_result,
                pattern_result=pattern_result,
                card_news_result=card_news_result,
                image_strategy_result=image_strategy_result,
                performance_score_result=performance_score_result,
                knowledge_result=knowledge_result,
                trend_memory_result=trend_memory_result,
            )
            self._save_workflow_result("13_audit_result.json", audit_result)

            learning_result = self._run_safe(
                "Learning Engine",
                self._empty_learning_result,
                self.learning_engine_module.run,
                knowledge_result=knowledge_result,
                performance_score_result=performance_score_result,
                audit_result=audit_result,
            )
            self._save_workflow_result("14_learning_result.json", learning_result)

            analytics_result = self._run_safe(
                "Analytics Engine",
                self._empty_analytics_result,
                self.analytics_engine_module.run,
                performance_score_result=performance_score_result,
                audit_result=audit_result,
            )
            self._save_workflow_result("15_analytics_result.json", analytics_result)

            brand_dna_result = self._run_safe(
                "Brand DNA Engine",
                self._empty_brand_dna_result,
                self.brand_dna_engine_module.run,
                pattern_result=pattern_result,
                content_result=content_result,
                card_news_result=card_news_result,
            )
            self._save_workflow_result("16_brand_dna_result.json", brand_dna_result)

            competitor_result = self._run_safe(
                "Competitor Engine",
                self._empty_competitor_result,
                self.competitor_engine_module.run,
            )
            self._save_workflow_result("17_competitor_result.json", competitor_result)

            final_result = {
                "status": "workflow_completed",
                "output_set_id": output_set_manifest["output_set_id"],
                "trend": trend_result,
                "topic": topic_result,
                "planner": planner_result,
                "pattern": pattern_result,
                "research": research_result,
                "content": content_result,
                "image_strategy": image_strategy_result,
                "image_prompt": image_prompt_result,
                "image_generation": image_generation_result,
                "card_news": card_news_result,
                "publishing": publishing_result,
                "card_news_output_set": output_set_manifest,
                "knowledge": knowledge_result,
                "performance_score": performance_score_result,
                "audit": audit_result,
                "learning": learning_result,
                "analytics": analytics_result,
                "brand_dna": brand_dna_result,
                "trend_memory": trend_memory_result,
                "competitor": competitor_result
            }

            self._save_workflow_result("99_final_result.json", final_result)

            print("=" * 50)
            print("workflow_completed")
            print("=" * 50)

            return final_result

        except Exception as error:
            error_result = {
                "status": "workflow_failed",
                "error": str(error)
            }

            self._save_workflow_result("00_workflow_error.json", error_result)

            print("=" * 50)
            print("workflow_failed")
            print(str(error))
            print("=" * 50)

            return error_result

    @staticmethod
    def _build_blocked_standard_production_results(image_generation_result):
        """Keep the legacy Workflow side-effect free.

        Real CardNews production is owned by the selected-candidate production
        controller. The standard Workflow still completes planning and learning,
        but it must never create or promote an output set on its own.
        """
        reason_code = "selected_candidate_controller_authorization_required"
        card_news_result = {
            "module": "CardNewsModule",
            "status": "card_news_production_blocked",
            "slides": [],
            "cards": [],
            "card_paths": [],
            "production_ready": False,
            "publishing_ready": False,
            "reason_code": reason_code,
            "image_generation_status": image_generation_result.get("status"),
            "card_news_quality": {
                "passed": False,
                "status": "not_run",
                "reason_code": reason_code,
            },
        }
        publishing_result = {
            "module": "PublishingModule",
            "status": "publishing_blocked",
            "publishing_ready": False,
            "package_ready": False,
            "actual_publish": False,
            "publish_queue": [],
            "reason_code": reason_code,
        }
        output_set_manifest = {
            "status": "output_set_not_created",
            "output_set_id": None,
            "promoted": False,
            "reason_code": reason_code,
        }
        return card_news_result, publishing_result, output_set_manifest

    def _run_card_news_output_transaction(
        self,
        content_result,
        image_generation_result,
        image_strategy_result,
    ):
        """Render and publish one complete CardNews set before selecting it.

        CardNews and Publishing keep their existing implementations.  The common
        engine temporarily redirects their file output into a run-scoped area,
        validates the complete set, and selects only the immutable committed set.
        """
        transaction = CardNewsOutputSetTransaction(Path("."))
        run_dir = transaction.store / ".runs" / transaction.output_set_id
        card_dir = run_dir / "card_news"
        publishing_dir = run_dir / "publishing"
        card_dir.mkdir(parents=True, exist_ok=False)
        publishing_dir.mkdir(parents=True, exist_ok=False)

        original_card_dir = self.card_news_module.card_dir
        original_publishing_dir = self.publishing_module.publishing_dir
        self.card_news_module.card_dir = card_dir
        self.publishing_module.publishing_dir = publishing_dir

        try:
            image_generation_result["output_set_id"] = transaction.output_set_id
            card_news_result = self.card_news_module.run(
                content_result,
                image_generation_result,
                image_strategy_result,
            )
            quality_result = card_news_result.get("card_news_quality")
            if not isinstance(quality_result, dict):
                raise ValueError("CardNews quality result is missing")

            self._apply_manual_image_intake(
                card_news_result, card_dir, transaction.output_set_id,
            )

            card_news_result["output_set_id"] = transaction.output_set_id
            quality_result["output_set_id"] = transaction.output_set_id
            pre_publish_attestation = self._build_pre_publish_attestation(
                card_news_result,
                quality_result,
                transaction.output_set_id,
            )
            card_news_result["card_news_manifest"] = pre_publish_attestation

            publishing_result = self.publishing_module.run(card_news_result)
            publishing_result["output_set_id"] = transaction.output_set_id
            publishing_result["actual_publish"] = False
            publishing_result.setdefault(
                "pre_publish_attestation",
                pre_publish_attestation,
            )
            readiness = self.publishing_module._resolve_package_readiness(
                card_news_result,
                publishing_result.get("card_paths", []),
                publishing_result.get("operations", {}),
            )
            publishing_result["package_readiness"] = readiness
            if not readiness["ready"]:
                publishing_result["status"] = "publishing_blocked"
                publishing_result["operations"]["publishing_blocked"] = True
                publishing_result["operations"]["blocking_reasons"] = list(
                    dict.fromkeys(
                        publishing_result["operations"].get("blocking_reasons", [])
                        + readiness["blocking_reasons"]
                    )
                )

            transaction.stage(card_news_result, quality_result, publishing_result)
            transaction.rebind_publishing(
                self.publishing_module.rebind_committed_paths
            )
            output_set_manifest = transaction.promote()
            active = CardNewsOutputSetTransaction.resolve_active(Path("."))

            card_news_result = self._load_output_set_json(active["card_news_result"])
            publishing_result = self._load_output_set_json(active["publishing"])
            quality_result = self._load_output_set_json(active["quality"])

            self._correct_committed_attestation(
                active, card_news_result, publishing_result, quality_result,
                transaction.output_set_id,
            )

            card_news_result["card_news_quality"] = quality_result
            card_news_result["output_set_manifest"] = output_set_manifest
            publishing_result["output_set_manifest"] = output_set_manifest

            self._write_compatible_output_set_receipts(
                active,
                image_generation_result=image_generation_result,
            )
            print(
                "CardNews Output Set Promoted: "
                f"{transaction.output_set_id}"
            )
            return card_news_result, publishing_result, output_set_manifest
        finally:
            self.card_news_module.card_dir = original_card_dir
            self.publishing_module.publishing_dir = original_publishing_dir
            shutil.rmtree(run_dir, ignore_errors=True)

    def _apply_manual_image_intake(self, card_news_result, card_dir, output_set_id):
        """Substitute validated operator-supplied real images (V2.0) into the
        still-mutable, run-scoped scratch `card_dir`, before
        `CardNewsOutputSetTransaction.stage()` commits anything.

        `load_verified_manual_images` already rejects, per image, any
        absolute/.runs/.staging path, corrupt or wrong-size file, and any
        image missing a validated rights record -- this method only ever
        copies bytes that already passed every one of those checks. A slot
        with no genuine manual image keeps CardNewsModule's own generated/
        fallback PNG completely untouched, so with no manual intake file this
        is a no-op and the existing fallback/PUBLISH_NO_GO behavior is
        unchanged. `manual_image_required` is only cleared when all active slots
        are covered by validated manual images; partial coverage is recorded
        in `real_image_used_count` but leaves the manual-image gate blocked.
        This never touches `actual_publish` (forced False unconditionally
        elsewhere in this same transaction, regardless of image sourcing).
        """
        manual_images = load_verified_manual_images(output_set_id)
        cards = card_news_result.get("cards")
        if not manual_images or not isinstance(cards, list):
            return

        cards_by_index = {
            item.get("index"): item for item in cards if isinstance(item, dict)
        }
        applied_count = 0
        for index, entry in manual_images.items():
            card = cards_by_index.get(index)
            if card is None:
                continue
            destination = card_dir / f"card_news_{index}.png"
            shutil.copyfile(entry["resolved_path"], destination)
            card["card_path"] = str(destination)
            card["image_source"] = "manual_intake"
            card["image_sha256"] = entry["sha256"]
            card["rights_record"] = {
                key: value for key, value in entry["rights_record"].items()
                if key != "asset_id"
            }
            applied_count += 1

        status = card_news_result.get("image_sourcing_status")
        if not isinstance(status, dict):
            status = {}
            card_news_result["image_sourcing_status"] = status
        try:
            previous_count = int(status.get("real_image_used_count", 0) or 0)
        except (TypeError, ValueError):
            previous_count = 0
        status["real_image_used_count"] = max(previous_count, applied_count)
        status["manual_intake_applied_indices"] = sorted(manual_images.keys())
        if applied_count == len(cards_by_index):
            status["manual_image_required"] = False

    def apply_staged_manual_image_intake_to_active_set(self, content_id, output_set_id=None):
        """Two-stage Manual Image Intake binding (V2.0.1).

        `_apply_manual_image_intake` above only works *before* a fresh
        workflow run stages/commits, because it needs to know the run's
        `output_set_id` -- but that id is only generated once the run starts,
        so an operator cannot pre-write an intake file keyed by an id that
        does not exist yet. Staged intake
        (`storage/manual_image_intake/staged/<content_id>.json`, see
        `modules.compliance.manual_image_intake_loader.load_staged_manual_images`)
        solves this by keying to a stable, operator-chosen `content_id`
        instead, and this method performs the second stage: binding already-
        staged, already-validated images onto whatever CardNews output set is
        *currently active* (already committed), computing each image's
        SHA-256 fresh against the exact committed path it replaces.

        This never re-runs CardNewsModule/ImageGenerationModule/PublishingModule,
        never touches `active.json`/`manifest.json` identity, and never
        fabricates readiness: it atomically replaces only the 4 committed PNG
        files' bytes, updates `cards[]`/`image_sourcing_status` accordingly,
        then re-derives readiness through the exact same, unmodified
        `_correct_committed_attestation` this engine already uses post-commit
        -- so `PUBLISH_MANUAL_IMAGE_REQUIRED` clears only if genuinely
        satisfied, and rights/evidence/compliance blockers are always left
        exactly as they already were (this method never reads or writes a
        V1.9 rights intake file).
        """
        active = CardNewsOutputSetTransaction.resolve_active(Path("."))
        card_news_result = self._load_output_set_json(active["card_news_result"])
        publishing_result = self._load_output_set_json(active["publishing"])
        quality_result = self._load_output_set_json(active["quality"])

        active_output_set_id = card_news_result.get("output_set_id")
        if output_set_id is not None and str(output_set_id).strip() != str(active_output_set_id).strip():
            raise ValueError(
                f"requested output_set_id {output_set_id!r} does not match "
                f"the currently active set {active_output_set_id!r}"
            )

        staged_images = load_staged_manual_images(content_id)
        cards = card_news_result.get("cards")
        if not staged_images or not isinstance(cards, list):
            return {
                "applied": False,
                "output_set_id": active_output_set_id,
                "applied_count": 0,
                "reason": "no valid staged manual image intake found for this content_id",
            }

        cards_by_index = {
            item.get("index"): item for item in cards if isinstance(item, dict)
        }
        applied_indices = []
        for index, entry in staged_images.items():
            card = cards_by_index.get(index)
            if card is None:
                continue
            committed_path = Path(card.get("card_path", ""))
            if not committed_path.is_file():
                continue
            self._atomic_replace_committed_file(committed_path, entry["resolved_path"])
            card["image_source"] = "manual_intake"
            card["image_sha256"] = self._sha256_of_file(committed_path)
            card["rights_record"] = {
                key: value for key, value in entry["rights_record"].items()
                if key != "asset_id"
            }
            applied_indices.append(index)

        if not applied_indices:
            return {
                "applied": False,
                "output_set_id": active_output_set_id,
                "applied_count": 0,
                "reason": "staged images did not match any committed card slot",
            }

        status = card_news_result.get("image_sourcing_status")
        if not isinstance(status, dict):
            status = {}
            card_news_result["image_sourcing_status"] = status
        try:
            previous_count = int(status.get("real_image_used_count", 0) or 0)
        except (TypeError, ValueError):
            previous_count = 0
        status["real_image_used_count"] = max(previous_count, len(applied_indices))
        status["manual_intake_applied_indices"] = sorted(
            set(status.get("manual_intake_applied_indices", []) or []) | set(applied_indices)
        )
        if set(applied_indices) >= set(cards_by_index):
            status["manual_image_required"] = False

        # Re-derive the image-sourcing gate through the same unmodified logic
        # PublishingModule.run() would have used, so the correction below sees
        # a freshly accurate operations dict rather than whatever this active
        # set's original run last persisted (which may have forced
        # publishing_blocked=True for an unrelated reason at the time).
        publishing_result["operations"] = self.publishing_module._resolve_publishing_gate(status)

        self._correct_committed_attestation(
            active, card_news_result, publishing_result, quality_result, active_output_set_id,
        )
        self._write_compatible_output_set_receipts(active, image_generation_result=None)

        return {
            "applied": True,
            "output_set_id": active_output_set_id,
            "applied_count": len(applied_indices),
            "applied_indices": sorted(applied_indices),
        }

    def reevaluate_active_set_compliance(self, output_set_id=None):
        """Re-run Rights/Compliance/Attestation for the currently active
        CardNews output set, with no new asset bytes changing.

        Use when a new operator rights intake file
        (`storage/rights_intake/<output_set_id>.json`,
        `modules.compliance.rights_intake_loader.load_verified_rights_intake`)
        becomes available for an already-committed set -- e.g. a retroactive
        operator approval -- and the resulting blocker_codes must reflect it.

        This never edits `blocker_codes`/`readiness_checks` by hand: it
        reloads the active set's three committed JSON files and calls the
        exact same, unmodified `_correct_committed_attestation` this engine
        already uses immediately after every fresh commit (which itself only
        ever calls the real `CardNewsPublishGate`,
        `PublishingModule._resolve_package_readiness`, and
        `PublishingModule.rebind_committed_paths`), then mirrors the result
        through `_write_compatible_output_set_receipts` exactly as a normal
        run would. A blocker can only disappear here if the real gate, given
        genuine new input, no longer raises it -- and `actual_publish` is
        never touched by this path (forced False unconditionally elsewhere).
        """
        active = CardNewsOutputSetTransaction.resolve_active(Path("."))
        card_news_result = self._load_output_set_json(active["card_news_result"])
        publishing_result = self._load_output_set_json(active["publishing"])
        quality_result = self._load_output_set_json(active["quality"])

        active_output_set_id = card_news_result.get("output_set_id")
        if output_set_id is not None and str(output_set_id).strip() != str(active_output_set_id).strip():
            raise ValueError(
                f"requested output_set_id {output_set_id!r} does not match "
                f"the currently active set {active_output_set_id!r}"
            )

        # publishing_result["operations"]["publishing_blocked"] as persisted on
        # disk may already have been forced True by a *previous*
        # _correct_committed_attestation call, simply because some other gate
        # (rights/evidence/compliance) was not ready at that time -- that
        # forced value must never be treated as this run's own image-sourcing
        # signal. Recompute it fresh from the authoritative source
        # (card_news_result["image_sourcing_status"]) through the same,
        # unmodified PublishingModule._resolve_publishing_gate every ordinary
        # run already uses, so a repeated reevaluation is fully idempotent
        # rather than compounding a stale flag.
        image_sourcing_status = card_news_result.get("image_sourcing_status")
        if isinstance(image_sourcing_status, dict):
            publishing_result["operations"] = self.publishing_module._resolve_publishing_gate(
                image_sourcing_status
            )

        self._correct_committed_attestation(
            active, card_news_result, publishing_result, quality_result, active_output_set_id,
        )
        self._write_compatible_output_set_receipts(active, image_generation_result=None)

        corrected_publishing = self._load_output_set_json(active["publishing"])
        return {
            "output_set_id": active_output_set_id,
            "blocker_codes": corrected_publishing.get("blocker_codes"),
            "publishing_ready": corrected_publishing.get("publishing_ready"),
            "package_ready": corrected_publishing.get("package_ready"),
            "actual_publish": corrected_publishing.get("actual_publish"),
            "status": corrected_publishing.get("status"),
        }

    def create_release_revision(self, source_output_set_id=None, content_id=None):
        """Create a brand-new, immutable CardNews output set carrying
        forward the SAME 4 committed card images (byte-identical, same
        SHA-256) and the SAME verified Rights/Compliance approval from the
        currently active set, rebound to a fresh output_set_id and fresh
        committed paths -- without ever mutating the source set's bytes.

        `reevaluate_active_set_compliance` can prove rights/evidence/
        compliance all pass for an already-committed set, but can never make
        `status`/`manifest.release_ready` become "publishing_ready"/True for
        THAT set, because `manifest.json` is frozen at commit time and can
        never be revised (see that method's docstring). The only way to get
        a committed set whose manifest is honestly frozen with
        release_ready=True is to make CardNewsOutputSetTransaction decide
        that *for the first and only time*, during its own one-time
        `rebind_publishing` call -- which is exactly what this method does,
        by passing a custom `rebind_fn` wrapper that builds the real
        attestation (via the unmodified `_build_pre_publish_attestation` /
        `load_verified_rights_intake` / `_resolve_package_readiness`) using
        the genuinely final, already-moved-into-place committed paths, then
        delegates to the real, unmodified `PublishingModule.rebind_committed_paths`.

        Refuses outright unless the active set is already fully verified
        (publishing_ready/package_ready True, no blocker_codes) and has a
        real rights intake file on disk -- this never fabricates approval,
        it only carries forward an approval that has already been
        independently confirmed. `actual_publish` is never set True anywhere
        in this path. If staging/rebind/promote fails at any point,
        `CardNewsOutputSetTransaction`'s own rollback (discard staging /
        rmtree the half-committed directory / never touch active.json until
        the very last step) leaves the source set as the sole active set,
        untouched.

        `content_id` (new, optional): when given, this method never deep-
        copies the source's semantic content (title/headline/body/CTA) at
        all. Instead it resolves a verified Copy Intake contract for that
        exact `content_id` (`modules.compliance.copy_intake_loader`),
        verifies the source's committed card images byte-for-byte match
        the Copy Intake's approved SHA-256 hashes, constructs a brand-new
        CardNews result whose only text source is that Copy Intake, and
        regenerates Publishing's caption/hashtags/package/queue fresh (via
        `PublishingModule.run`) instead of carrying forward the source's
        stale caption/queue -- this is the fix for the CN-006 semantic
        false-ready incident (stale metadata from a prior, unrelated topic
        was being deep-copied onto a new output_set_id by the legacy path
        below). See `_create_release_revision_from_copy_intake`. When
        `content_id` is omitted, behavior is byte-for-byte identical to
        before this fix (full legacy deep-copy path), preserving every
        existing caller and regression test unchanged.
        """
        active = CardNewsOutputSetTransaction.resolve_active(Path("."))
        source_card_news = self._load_output_set_json(active["card_news_result"])
        source_quality = self._load_output_set_json(active["quality"])
        source_publishing = self._load_output_set_json(active["publishing"])
        source_id = source_card_news.get("output_set_id")

        if source_output_set_id is not None and str(source_output_set_id).strip() != str(source_id).strip():
            raise ValueError(
                f"requested source_output_set_id {source_output_set_id!r} does not match "
                f"the currently active set {source_id!r}"
            )
        if (
            source_publishing.get("blocker_codes")
            or source_publishing.get("publishing_ready") is not True
            or source_publishing.get("package_ready") is not True
        ):
            raise ValueError(
                "the active set is not fully rights/evidence/compliance verified; "
                "refusing to create a release revision"
            )

        source_rights_intake_path = Path("storage/rights_intake") / f"{source_id}.json"
        if not source_rights_intake_path.is_file():
            raise ValueError(
                "no rights intake file exists for the active set; refusing to create a release revision"
            )
        source_rights_intake_raw = json.loads(source_rights_intake_path.read_text(encoding="utf-8"))

        if content_id is not None:
            return self._create_release_revision_from_copy_intake(
                content_id=content_id,
                source_card_news=source_card_news,
                source_quality=source_quality,
                source_id=source_id,
                source_rights_intake_raw=source_rights_intake_raw,
            )

        source_cards = source_card_news.get("cards")
        source_card_count = len(source_cards) if isinstance(source_cards, list) else 0
        if not is_allowed_card_slide_count(source_card_count):
            raise ValueError("source card_news_result has invalid slide count for release revision")
        source_card_indexes = list(range(1, source_card_count + 1))

        transaction = CardNewsOutputSetTransaction(Path("."))
        new_id = transaction.output_set_id
        new_committed_paths = [
            (transaction.committed / f"cards/card_news_{i}.png").relative_to(transaction.root).as_posix()
            for i in source_card_indexes
        ]

        new_rights_intake_raw = json.loads(json.dumps(source_rights_intake_raw))
        new_rights_intake_raw["output_set_id"] = new_id
        cards_by_index = {
            item.get("card_index"): item
            for item in new_rights_intake_raw.get("cards", [])
            if isinstance(item, dict)
        }
        for index in source_card_indexes:
            if index in cards_by_index:
                cards_by_index[index]["card_path"] = new_committed_paths[index - 1]
        new_rights_intake_path = Path("storage/rights_intake") / f"{new_id}.json"

        new_card_news_result = json.loads(json.dumps(source_card_news))
        new_card_news_result.pop("card_news_manifest", None)
        new_quality_result = json.loads(json.dumps(source_quality))
        new_publishing_result = json.loads(json.dumps(source_publishing))
        for stale_key in ("pre_publish_attestation", "package_readiness", "publish_queue_path", "readiness_checks"):
            new_publishing_result.pop(stale_key, None)
        new_publishing_result["status"] = "publishing_blocked"
        new_publishing_result["publishing_ready"] = False
        new_publishing_result["package_ready"] = False
        new_publishing_result["blocker_codes"] = []
        new_publishing_result["actual_publish"] = False
        stale_package = new_publishing_result.get("operator_upload_package")
        if isinstance(stale_package, dict):
            stale_package.pop("publish_queue_path", None)

        build_pre_publish_attestation = self._build_pre_publish_attestation
        publishing_module = self.publishing_module
        real_rebind = publishing_module.rebind_committed_paths

        def _rebind_with_fresh_attestation(publishing, committed_paths, output_set_id, queue_target):
            # By this point CardNewsOutputSetTransaction.rebind_publishing has
            # already moved staged files to their final committed location,
            # so committed_paths reference real, decodable, existing images
            # -- exactly what CardNewsPublishGate needs. Build the real
            # attestation here, the first and only time, instead of via a
            # later correction that a frozen manifest.json could never
            # reflect.
            card_news_view = {
                "cards": [
                    {"index": index, "card_path": committed_paths[index - 1]}
                    for index in source_card_indexes
                ]
            }
            rights_intake = load_verified_rights_intake(output_set_id, card_news_view)
            attestation = build_pre_publish_attestation(
                card_news_view, new_quality_result, output_set_id, rights_intake=rights_intake,
            )

            committed_card_news_path = transaction.committed / "08_card_news_result.json"
            committed_card_news = json.loads(committed_card_news_path.read_text(encoding="utf-8"))
            committed_card_news["card_news_manifest"] = attestation
            committed_card_news_path.write_text(
                json.dumps(committed_card_news, ensure_ascii=False, indent=2), encoding="utf-8",
            )

            publishing["pre_publish_attestation"] = attestation
            readiness = publishing_module._resolve_package_readiness(
                {
                    "output_set_id": output_set_id,
                    "cards": card_news_view["cards"],
                    "card_news_manifest": attestation,
                },
                committed_paths,
                publishing.get("operations", {}),
            )
            publishing["package_readiness"] = readiness
            publishing["readiness_checks"] = readiness["checks"]
            publishing["blocker_codes"] = list(readiness["blocking_reasons"])
            publishing["status"] = "publishing_ready" if readiness["ready"] else "publishing_blocked"
            publishing["publishing_ready"] = readiness["ready"]
            publishing["package_ready"] = readiness["ready"]
            return real_rebind(publishing, committed_paths, output_set_id, queue_target)

        new_rights_intake_path.write_text(
            json.dumps(new_rights_intake_raw, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        try:
            transaction.stage(new_card_news_result, new_quality_result, new_publishing_result)
            transaction.rebind_publishing(_rebind_with_fresh_attestation)
            transaction.promote()
        except Exception:
            new_rights_intake_path.unlink(missing_ok=True)
            raise

        new_active = CardNewsOutputSetTransaction.resolve_active(Path("."))
        self._write_compatible_output_set_receipts(new_active, image_generation_result=None)
        final_publishing = self._load_output_set_json(new_active["publishing"])

        return {
            "new_output_set_id": new_id,
            "source_output_set_id": source_id,
            "blocker_codes": final_publishing.get("blocker_codes"),
            "status": final_publishing.get("status"),
            "publishing_ready": final_publishing.get("publishing_ready"),
            "package_ready": final_publishing.get("package_ready"),
            "actual_publish": final_publishing.get("actual_publish"),
        }

    def _create_release_revision_from_copy_intake(
        self,
        content_id,
        source_card_news,
        source_quality,
        source_id,
        source_rights_intake_raw,
    ):
        """Copy-Intake-driven release revision: never deep-copies source
        semantic content; builds everything from a verified, hash-bound
        contract instead. See `create_release_revision`'s docstring for the
        incident this fixes and the overall division of responsibility.
        """
        trusted_content_id = str(content_id).strip()
        if not trusted_content_id:
            raise ValueError("content_id must be a non-empty string")

        existing_content_id = str(source_card_news.get("content_id") or "").strip()
        if existing_content_id and existing_content_id != trusted_content_id:
            raise ValueError(
                f"requested content_id {trusted_content_id!r} does not match the source "
                f"card_news_result's own content_id {existing_content_id!r}"
            )

        copy_intake = load_verified_copy_intake(trusted_content_id)
        if copy_intake is None:
            raise ValueError(
                f"no verified Copy Intake exists for content_id {trusted_content_id!r}; "
                "refusing to create a release revision"
            )
        copy_intake_slide_indexes = sorted(copy_intake["slides"].keys())
        if not is_allowed_card_slide_count(len(copy_intake_slide_indexes)):
            raise ValueError("Copy Intake slide count is outside the allowed range")

        source_cards = source_card_news.get("cards", [])
        cards_by_index = {}
        for item in source_cards:
            if not isinstance(item, dict):
                continue
            try:
                index = int(item.get("index"))
            except (TypeError, ValueError):
                continue
            cards_by_index[index] = item
        if sorted(cards_by_index) != copy_intake_slide_indexes:
            raise ValueError(
                "source card_news_result does not match Copy Intake indexed cards"
            )

        # Bind every slide's approved image hash to the ACTUAL committed
        # asset before anything new is built. A mismatch here (wrong PNG for
        # a correct headline, or vice versa) must refuse outright -- never
        # silently substitute the Copy Intake's hash for reality.
        for index in copy_intake_slide_indexes:
            card_path_value = cards_by_index[index].get("card_path")
            card_path_text = str(card_path_value).strip() if card_path_value else ""
            path_parts = card_path_text.replace("\\", "/").lower().split("/")
            if (
                not card_path_text
                or Path(card_path_text).is_absolute()
                or ".runs" in path_parts
                or ".staging" in path_parts
            ):
                raise ValueError(f"source card path for slide {index} is missing or unsafe")
            actual_hash = self._sha256_of_file(card_path_text)
            expected_hash = copy_intake["slides"][index]["image_sha256"]
            if actual_hash != expected_hash:
                raise ValueError(
                    f"image SHA256 mismatch at slide {index}: Copy Intake requires "
                    f"{expected_hash}, committed asset is {actual_hash}"
                )

        transaction = CardNewsOutputSetTransaction(Path("."))
        new_id = transaction.output_set_id
        new_committed_paths = [
            (transaction.committed / f"cards/card_news_{i}.png").relative_to(transaction.root).as_posix()
            for i in copy_intake_slide_indexes
        ]

        new_rights_intake_raw = json.loads(json.dumps(source_rights_intake_raw))
        new_rights_intake_raw["output_set_id"] = new_id
        rights_cards_by_index = {
            item.get("card_index"): item
            for item in new_rights_intake_raw.get("cards", [])
            if isinstance(item, dict)
        }
        for index in copy_intake_slide_indexes:
            if index in rights_cards_by_index:
                rights_cards_by_index[index]["card_path"] = new_committed_paths[index - 1]
        new_rights_intake_path = Path("storage/rights_intake") / f"{new_id}.json"

        # Build a brand-new, clean CardNews result. The ONLY source of
        # title/headline/body/role/CTA text is the verified Copy Intake.
        # image_sourcing_status is carried forward because it describes the
        # (unchanged, hash-verified) images' provenance/operational state,
        # never any semantic topic copy.
        source_image_sourcing_status = source_card_news.get("image_sourcing_status")
        if not isinstance(source_image_sourcing_status, dict):
            source_image_sourcing_status = {}
        new_image_sourcing_status = json.loads(json.dumps(source_image_sourcing_status))

        new_quality_result = json.loads(json.dumps(source_quality))
        new_quality_result["output_set_id"] = new_id

        new_cards = []
        for index in copy_intake_slide_indexes:
            slide = copy_intake["slides"][index]
            source_card = cards_by_index[index]
            rights_record = source_card.get("rights_record")
            card_entry = {
                "index": index,
                "card_path": source_card.get("card_path"),
                "role": slide["role"],
                "headline": slide["headline"],
                "body": slide["body"],
                "status": "created",
                "image_source": source_card.get("image_source"),
                "image_sha256": slide["image_sha256"],
                "rights_record": json.loads(json.dumps(rights_record)) if isinstance(rights_record, dict) else {},
            }
            if slide["role"] == "cta":
                card_entry["cta_type"] = slide["cta_type"]
                card_entry["cta_label"] = slide["cta_label"]
            new_cards.append(card_entry)

        new_card_news_result = {
            "module": "CardNewsModule",
            "status": "card_news_completed",
            "content_id": copy_intake["content_id"],
            "title": copy_intake["title"],
            "cards": new_cards,
            "card_news_quality": new_quality_result,
            "image_sourcing_status": new_image_sourcing_status,
            "copy_intake_binding": {
                "content_id": copy_intake["content_id"],
                "approved_at": copy_intake["approved_at"],
                "operator_id": copy_intake["operator_id"],
            },
        }

        # Regenerate Publishing's caption/hashtags/package/queue fresh, from
        # the clean CardNews result -- never carry forward the source's
        # (possibly stale) caption/queue. PublishingModule.run() writes to
        # self.publishing_module.publishing_dir, so that is redirected to a
        # throwaway scratch directory for the duration of this call, exactly
        # like WorkflowEngine._run_card_news_output_transaction does for a
        # fresh workflow run.
        publishing_module = self.publishing_module
        original_publishing_dir = publishing_module.publishing_dir
        scratch_dir = transaction.store / ".runs" / new_id / "publishing_release_revision"
        scratch_dir.mkdir(parents=True, exist_ok=True)
        publishing_module.publishing_dir = scratch_dir
        try:
            new_publishing_result = publishing_module.run(new_card_news_result)
        finally:
            publishing_module.publishing_dir = original_publishing_dir
            shutil.rmtree(scratch_dir, ignore_errors=True)

        new_publishing_result["output_set_id"] = new_id
        new_publishing_result["actual_publish"] = False
        new_publishing_result["status"] = "publishing_blocked"
        new_publishing_result["publishing_ready"] = False
        new_publishing_result["package_ready"] = False
        new_publishing_result["blocker_codes"] = []
        stale_package = new_publishing_result.get("operator_upload_package")
        if isinstance(stale_package, dict):
            stale_package.pop("publish_queue_path", None)
        new_publishing_result.pop("publish_queue_path", None)

        build_pre_publish_attestation = self._build_pre_publish_attestation
        real_rebind = publishing_module.rebind_committed_paths
        assert_clean_semantics = self._assert_release_revision_semantics_clean

        def _rebind_with_fresh_attestation(publishing, committed_paths, output_set_id, queue_target):
            card_news_view = {
                "cards": [
                    {"index": index, "card_path": committed_paths[index - 1]}
                    for index in copy_intake_slide_indexes
                ]
            }
            rights_intake = load_verified_rights_intake(output_set_id, card_news_view)
            attestation = build_pre_publish_attestation(
                card_news_view, new_quality_result, output_set_id, rights_intake=rights_intake,
            )

            committed_card_news_path = transaction.committed / "08_card_news_result.json"
            committed_card_news = json.loads(committed_card_news_path.read_text(encoding="utf-8"))
            committed_card_news["card_news_manifest"] = attestation
            committed_card_news_path.write_text(
                json.dumps(committed_card_news, ensure_ascii=False, indent=2), encoding="utf-8",
            )

            publishing["pre_publish_attestation"] = attestation
            readiness = publishing_module._resolve_package_readiness(
                {
                    "output_set_id": output_set_id,
                    "cards": card_news_view["cards"],
                    "card_news_manifest": attestation,
                    "image_sourcing_status": new_image_sourcing_status,
                },
                committed_paths,
                publishing.get("operations", {}),
            )
            publishing["package_readiness"] = readiness
            publishing["readiness_checks"] = readiness["checks"]
            publishing["blocker_codes"] = list(readiness["blocking_reasons"])
            publishing["status"] = "publishing_ready" if readiness["ready"] else "publishing_blocked"
            publishing["publishing_ready"] = readiness["ready"]
            publishing["package_ready"] = readiness["ready"]
            publishing["manual_image_required"] = bool(
                new_image_sourcing_status.get("manual_image_required", False)
            )

            # PublishingModule.run() necessarily built the queue/package
            # BEFORE this attestation existed, so their status strings were
            # frozen at "blocked" (attestation-missing) even though the real
            # readiness computed here may now be fully clear. Correct those
            # nested labels here -- the one place that knows the genuine
            # final readiness -- rather than letting a stale nested "blocked"
            # ride alongside a root "ready" (the exact CN-006 defect this
            # release-revision path exists to close). This never fabricates
            # readiness: it only propagates the SAME `readiness["ready"]`
            # verdict already computed above into the nested queue/package
            # views that PublishingModule.run() could not have known yet.
            if readiness["ready"]:
                package = publishing.get("operator_upload_package")
                if isinstance(package, dict):
                    package["status"] = "ready_for_manual_upload"
                    package["blocker_codes"] = []
                queue = publishing.get("publish_queue")
                if isinstance(queue, dict):
                    queue["status"] = "queue_ready"
                    queue["blocker_codes"] = []
                    for item in queue.get("items", []):
                        if isinstance(item, dict):
                            item["status"] = "ready_for_manual_upload"
                            item["manual_image_required"] = False
                            item["blocker_codes"] = []
                            item_operations = item.get("operations")
                            if isinstance(item_operations, dict):
                                item_operations["publishing_blocked"] = False
                                item_operations["blocking_reasons"] = []
                                item_operations["package_ready"] = True

            rebound = real_rebind(publishing, committed_paths, output_set_id, queue_target)

            # Fail-closed gate: only reached after CardNewsOutputSetTransaction
            # has already moved staging into the committed directory but
            # BEFORE promote() ever runs, so any exception here still leaves
            # active.json pointing at the untouched source set --
            # rebind_publishing's own except-clause rmtree's this half-built
            # committed directory.
            assert_clean_semantics(
                committed_card_news, rebound, copy_intake, output_set_id, committed_paths,
            )
            return rebound

        new_rights_intake_path.write_text(
            json.dumps(new_rights_intake_raw, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        try:
            transaction.stage(new_card_news_result, new_quality_result, new_publishing_result)
            transaction.rebind_publishing(_rebind_with_fresh_attestation)
            transaction.promote()
        except Exception:
            new_rights_intake_path.unlink(missing_ok=True)
            raise

        new_active = CardNewsOutputSetTransaction.resolve_active(Path("."))
        self._write_compatible_output_set_receipts(new_active, image_generation_result=None)
        final_publishing = self._load_output_set_json(new_active["publishing"])

        return {
            "new_output_set_id": new_id,
            "source_output_set_id": source_id,
            "content_id": copy_intake["content_id"],
            "blocker_codes": final_publishing.get("blocker_codes"),
            "status": final_publishing.get("status"),
            "publishing_ready": final_publishing.get("publishing_ready"),
            "package_ready": final_publishing.get("package_ready"),
            "actual_publish": final_publishing.get("actual_publish"),
        }

    @staticmethod
    def _assert_release_revision_semantics_clean(
        committed_card_news, publishing, copy_intake, output_set_id, committed_paths,
    ):
        """Fail-closed final gate for the Copy-Intake release path, run once
        after real paths/attestation/readiness are known but strictly before
        `CardNewsOutputSetTransaction.promote()` ever runs. Raises ValueError
        (never silently downgrades or truncates) on the first violation
        found, covering every attack scenario the CN-006 incident review
        required: wrong/stale text, wrong image, id mixing, and root/nested
        readiness or manual-image-required disagreement.
        """
        haystack = json.dumps(committed_card_news, ensure_ascii=False) + json.dumps(publishing, ensure_ascii=False)
        for phrase in COPY_INTAKE_BANNED_PHRASES:
            if phrase in haystack:
                raise ValueError(f"banned stale phrase found in release revision content: {phrase!r}")

        if str(committed_card_news.get("title") or "") != copy_intake["title"]:
            raise ValueError("committed title does not exactly match the verified Copy Intake title")

        cards = committed_card_news.get("cards")
        copy_intake_slide_indexes = sorted(copy_intake["slides"].keys())
        if not is_allowed_card_slide_count(len(cards)):
            raise ValueError("committed card_news_result does not have valid slide count")
        cards_by_index = {item.get("index"): item for item in cards if isinstance(item, dict)}
        if sorted(cards_by_index) != copy_intake_slide_indexes:
            raise ValueError("committed cards are not indexed exactly like Copy Intake")

        for index in copy_intake_slide_indexes:
            slide = copy_intake["slides"][index]
            card = cards_by_index[index]
            if str(card.get("role") or "") != slide["role"]:
                raise ValueError(f"committed card {index} role does not match Copy Intake")
            if str(card.get("headline") or "") != slide["headline"]:
                raise ValueError(f"committed card {index} headline does not match Copy Intake")
            if str(card.get("body") or "") != slide["body"]:
                raise ValueError(f"committed card {index} body does not match Copy Intake")
            if slide["role"] == "cta":
                if str(card.get("cta_type") or "") != slide["cta_type"] or str(card.get("cta_label") or "") != slide["cta_label"]:
                    raise ValueError("committed CTA slide does not match Copy Intake")
            committed_path = committed_paths[index - 1]
            actual_hash = WorkflowEngine._sha256_of_file(committed_path)
            if actual_hash != slide["image_sha256"]:
                raise ValueError(f"committed card {index} image SHA256 does not match Copy Intake after staging")
            if str(card.get("image_sha256") or "") != slide["image_sha256"]:
                raise ValueError(f"committed card {index} recorded image_sha256 field does not match Copy Intake")

        # output_set_id singleton across every reachable identity field.
        ids = [committed_card_news.get("output_set_id"), publishing.get("output_set_id")]
        package = publishing.get("operator_upload_package")
        if isinstance(package, dict):
            ids.append(package.get("output_set_id"))
        queue = publishing.get("publish_queue")
        if isinstance(queue, dict):
            ids.append(queue.get("output_set_id"))
            for item in queue.get("items", []):
                if isinstance(item, dict):
                    ids.append(item.get("output_set_id"))
        if any(value != output_set_id for value in ids):
            raise ValueError("output_set_id is not a singleton across the release revision payload")

        # root/nested manual_image_required agreement.
        root_manual_required = publishing.get("manual_image_required")
        card_news_manual_required = committed_card_news.get("image_sourcing_status", {}).get("manual_image_required")
        publishing_sourcing_manual_required = publishing.get("image_sourcing_status", {}).get("manual_image_required")
        manual_flags = [root_manual_required, card_news_manual_required, publishing_sourcing_manual_required]
        if isinstance(queue, dict):
            for item in queue.get("items", []):
                if isinstance(item, dict):
                    manual_flags.append(item.get("manual_image_required"))
        if any(flag is not False for flag in manual_flags):
            raise ValueError("manual_image_required is not false everywhere (root/nested disagreement)")

        real_image_used_count = committed_card_news.get("image_sourcing_status", {}).get("real_image_used_count")
        if real_image_used_count != len(copy_intake_slide_indexes):
            raise ValueError("real_image_used_count does not match Copy Intake slide count")

        if publishing.get("package_ready") is not True or publishing.get("publishing_ready") is not True:
            raise ValueError("package_ready/publishing_ready did not both reach True")
        if publishing.get("blocker_codes"):
            raise ValueError("blocker_codes is not empty")
        if publishing.get("actual_publish") is not False:
            raise ValueError("actual_publish is not false")

        if isinstance(package, dict):
            # Whitelist the one valid ready status rather than blacklisting
            # known-blocked strings: a whitelist also refuses any OTHER
            # unexpected status value, which is the correct fail-closed
            # default for a package the root claims is ready.
            if package.get("status") != "ready_for_manual_upload" or package.get("actual_publish") is not False:
                raise ValueError("operator_upload_package is not genuinely ready while root reports ready")
        if isinstance(queue, dict):
            if queue.get("status") != "queue_ready":
                raise ValueError("nested publish_queue is not genuinely ready while root reports ready")
            items = queue.get("items")
            if not isinstance(items, list) or not items:
                raise ValueError("nested publish_queue has no items")
            for item in items:
                if (
                    not isinstance(item, dict)
                    or item.get("status") != "ready_for_manual_upload"
                    or item.get("actual_publish") is not False
                ):
                    raise ValueError("nested publish_queue item is not genuinely ready while root reports ready")

    @staticmethod
    def _sha256_of_file(path):
        digest = hashlib.sha256()
        with open(path, "rb") as file:
            for chunk in iter(lambda: file.read(1024 * 64), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _atomic_replace_committed_file(destination, source):
        """Atomically overwrite one already-committed binary file in place.

        Mirrors `_atomic_write_committed_json`'s safety pattern (temp file +
        `os.replace`) for PNG bytes instead of JSON, used only by
        `apply_staged_manual_image_intake_to_active_set`.
        """
        destination = Path(destination)
        temporary = destination.with_name(f".{destination.name}.manual_intake.tmp")
        try:
            with open(source, "rb") as source_file:
                data = source_file.read()
            with open(temporary, "wb") as file:
                file.write(data)
                file.flush()
                os.fsync(file.fileno())
            WorkflowEngine._replace_receipt_with_retry(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    def _correct_committed_attestation(
        self, active, card_news_result, publishing_result, quality_result, output_set_id,
    ):
        """Rebuild the pre-publish attestation using real, committed, repo-relative
        paths, then persist the correction into the two already-committed JSON
        files -- fixing PUBLISH_MANIFEST_PATH_MISMATCH at its source.

        The attestation built earlier in `_run_card_news_output_transaction` (before
        `transaction.stage()`) necessarily referenced CardNewsModule's run-scoped,
        absolute `.runs/<id>/card_news/...` paths, because that is the only place
        the rendered PNGs physically existed at that point. CardNewsPublishGate
        correctly rejects any non-repo-relative path
        (`final_cards_invalid`), so that early attestation's `cards` list was always
        empty and `manifest_paths_match` always false -- independent of whether
        rights/evidence would otherwise pass (see
        external_workclaude/content_portfolio_v1/PUBLISH_BLOCKER_AUDIT_V1_6.md for
        the full trace).

        This method only runs after `transaction.promote()` and
        `CardNewsOutputSetTransaction.resolve_active()` have already succeeded, so a
        stage/commit failure never reaches this code and can never produce a
        "successful" attestation (the caller's try/finally still applies around the
        whole transaction). It calls the real, unmodified `CardNewsPublishGate`
        (via `_build_pre_publish_attestation`) and the real, unmodified
        `PublishingModule._resolve_package_readiness` /
        `PublishingModule.rebind_committed_paths` a second time, now with paths that
        are genuinely repo-relative, `.runs`/`.staging`-free, and backed by files
        that actually exist at that exact location -- it never fabricates or
        bypasses the compliance/rights/evidence decision. Only fields derived from
        `manifest_paths_match` change; rights, evidence, and manual-image blockers
        are untouched because nothing about rights, evidence, or image sourcing
        changed.
        """
        rights_intake = load_verified_rights_intake(output_set_id, card_news_result)
        corrected_attestation = self._build_pre_publish_attestation(
            card_news_result, quality_result, output_set_id, rights_intake=rights_intake,
        )
        card_news_result["card_news_manifest"] = corrected_attestation
        publishing_result["pre_publish_attestation"] = corrected_attestation

        corrected_readiness = self.publishing_module._resolve_package_readiness(
            card_news_result,
            publishing_result.get("card_paths", []),
            publishing_result.get("operations", {}),
        )
        previous_readiness_codes = set(
            publishing_result.get("package_readiness", {}).get("blocking_reasons", [])
        )
        publishing_result["package_readiness"] = corrected_readiness
        publishing_result["readiness_checks"] = corrected_readiness["checks"]
        # CardNewsOutputSetTransaction._validate_directory cross-checks
        # manifest.json's own frozen `release_ready` flag against
        # `quality.passed and publishing.status == "publishing_ready"` every
        # time resolve_active() runs. manifest.json is written once (by
        # promote()/rebind_publishing()) and can never be revised afterward
        # (the immutability invariant). `status` must always mirror whatever
        # that frozen flag already says -- never derived fresh from
        # corrected_readiness here -- or resolve_active() permanently refuses
        # the set ("manifest release readiness mismatch"). For a set whose
        # manifest was frozen not-ready (the overwhelmingly common case,
        # since nothing could ever fully pass before this rights-intake path
        # existed), status stays "publishing_blocked" forever, no matter how
        # complete a later rights intake is -- only a fresh commit (see
        # create_release_revision) can ever produce a genuinely
        # release_ready=True manifest. publishing_ready/package_ready are
        # plain booleans _validate_directory never inspects, so they can
        # safely and accurately reflect the real corrected_readiness verdict
        # for reporting purposes regardless of the frozen manifest.
        try:
            frozen_manifest = json.loads(
                (active["card_news_result"].parent / "manifest.json").read_text(encoding="utf-8")
            )
            frozen_release_ready = frozen_manifest.get("release_ready") is True
        except (OSError, json.JSONDecodeError):
            frozen_release_ready = False
        publishing_result["status"] = "publishing_ready" if frozen_release_ready else "publishing_blocked"
        publishing_result["publishing_ready"] = corrected_readiness["ready"]
        publishing_result["package_ready"] = corrected_readiness["ready"]
        publishing_result["operations"]["publishing_blocked"] = not corrected_readiness["ready"]
        publishing_result["operations"]["blocking_reasons"] = list(
            dict.fromkeys(
                [
                    reason
                    for reason in publishing_result["operations"].get("blocking_reasons", [])
                    if reason not in previous_readiness_codes
                ]
                + corrected_readiness["blocking_reasons"]
            )
        )
        # PublishingModule.rebind_committed_paths is intentionally NOT called
        # here (unlike earlier revisions of this method). Its success branch
        # writes a real cards/09_publish_queue.json file and expects
        # manifest.json's own artifacts dict to already reference it -- but
        # manifest.json was frozen by CardNewsOutputSetTransaction.promote()
        # before this correction ever runs, and can never be updated
        # afterward (the whole point of an immutable committed set). Every
        # previous call site only ever exercised rebind_committed_paths'
        # failure branch (the hardcoded stub attestation could never fully
        # pass), so this hazard was latent until a genuinely complete rights
        # intake made a real pass possible; reaching the write branch here
        # corrupts the committed set (CardNewsOutputSetTransaction.resolve_active
        # then refuses to resolve it, since the queue is not referenced in
        # manifest.artifacts). The aggregate PUBLISH_COMMITTED_ATTESTATION_INVALID
        # check that function also performed is exactly
        # `not corrected_readiness["ready"]` -- the same 11 checks, already
        # computed above -- so it is preserved without needing to call the
        # queue-writing function at all.
        blocker_codes = list(corrected_readiness["blocking_reasons"])
        if not corrected_readiness["ready"]:
            blocker_codes.append("PUBLISH_COMMITTED_ATTESTATION_INVALID")
        publishing_result["blocker_codes"] = list(dict.fromkeys(blocker_codes))
        publishing_result["actual_publish"] = False
        # Defensively clear any queue-file reference: this correction never
        # establishes a real, manifest-consistent publish queue post-commit,
        # so no committed JSON may claim one exists.
        publishing_result.pop("publish_queue_path", None)
        package = publishing_result.get("operator_upload_package")
        if isinstance(package, dict):
            package.pop("publish_queue_path", None)
            package["blocker_codes"] = list(publishing_result["blocker_codes"])
        queue = publishing_result.get("publish_queue")
        if isinstance(queue, dict):
            queue["blocker_codes"] = list(publishing_result["blocker_codes"])

        self._atomic_write_committed_json(active["card_news_result"], card_news_result)
        self._atomic_write_committed_json(active["publishing"], publishing_result)
        # Remove any stray queue file a prior, now-fixed run of this method
        # may have already written -- its mere presence, even unreferenced,
        # is misleading now that this correction never creates one.
        stray_queue = active["card_1"].parent / "09_publish_queue.json"
        stray_queue.unlink(missing_ok=True)

    def _atomic_write_committed_json(self, path, payload):
        """Atomically overwrite one already-committed output-set JSON file in place.

        Used only by `_correct_committed_attestation` for the narrow post-commit
        correction described there -- never for first-time staging, which remains
        `CardNewsOutputSetTransaction`'s exclusive responsibility. This never
        touches `manifest.json`, `active.json`, or any PNG.
        """
        path = Path(path)
        marker = str(payload.get("output_set_id") or "correction")
        temporary = path.with_name(f".{path.name}.{marker}.tmp")
        try:
            with open(temporary, "w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)
                file.flush()
                os.fsync(file.fileno())
            self._replace_receipt_with_retry(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _build_pre_publish_attestation(card_news_result, quality_result, output_set_id, rights_intake=None):
        """Build the one-way input contract used before Publishing packaging.

        `rights_intake` is an optional pre-validated fragment produced by
        `modules.compliance.rights_intake_loader.load_verified_rights_intake`
        (V1.9). When it is `None` (no genuine operator intake exists for this
        exact committed output set), `assets`/`evidence`/`claims`/`campaign`/
        `disclosures`/`operator_checklist` fall back to the same hardcoded,
        always-blocked stub this function has always used -- so behavior is
        byte-for-byte identical to before V1.9 whenever no real rights intake
        is present. When it is a dict, its already-validated contents are fed,
        unmodified, into the real `CardNewsPublishGate` below; this function
        never itself decides rights/evidence/compliance outcomes.
        """
        cards = card_news_result.get("cards", [])
        checks = quality_result.get("checks", {})
        unlicensed_clear = checks.get("unlicensed_asset_not_rendered") is True
        attribution_needed = checks.get("attribution_needed") is True
        attribution_clear = (
            not attribution_needed or checks.get("attribution_present") is True
        )
        rights_ready = unlicensed_clear and attribution_clear
        evidence_available = checks.get("evidence_available")
        evidence_applied = checks.get("evidence_applied")
        evidence_status = (
            "applied" if evidence_applied is True
            else "unavailable" if evidence_available is False
            else "not_applied"
        )
        if isinstance(rights_intake, dict):
            assets = rights_intake.get("assets", [])
            evidence = rights_intake.get("evidence", [])
            claims = rights_intake.get("claims", [])
            campaign = rights_intake.get("campaign", {})
            disclosures = rights_intake.get("disclosures", [])
            operator_checklist = rights_intake.get("operator_checklist", {})
        else:
            assets = [
                {
                    "asset_id": f"card_{item.get('index')}",
                    "classification": "technical_fixture",
                    "asset_path": item.get("card_path"),
                }
                for item in cards if isinstance(item, dict)
            ]
            evidence = []
            claims = []
            campaign = {
                "is_advertising": False,
                "is_sponsored": False,
                "has_affiliate_link": False,
                "commercial_relationship_reviewed": False,
            }
            disclosures = []
            operator_checklist = {}
        compliance_result = CardNewsPublishGate().check({
            "package_id": f"card-news-{output_set_id}",
            "output_set_id": output_set_id,
            "assets": assets,
            "evidence": evidence,
            "claims": claims,
            "campaign": campaign,
            "disclosures": disclosures,
            "operator_checklist": operator_checklist,
            "final_cards": [
                {
                    "path": item.get("card_path"),
                    "output_set_id": output_set_id,
                }
                for item in cards if isinstance(item, dict)
            ],
            "quality": {
                "passed": quality_result.get("passed") is True,
                "output_set_id": output_set_id,
            },
        })
        attestation = compliance_result.get("pre_publish_attestation")
        if not isinstance(attestation, dict):
            raise ValueError("Compliance pre-publish attestation is missing")
        return attestation

    @staticmethod
    def _load_output_set_json(path):
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    def _write_compatible_output_set_receipts(
        self,
        active,
        image_generation_result=None,
    ):
        """Keep canonical stage JSON paths without reintroducing loose PNGs."""
        # A legacy Publishing receipt can otherwise keep advertising a global
        # mutable queue while the new immutable receipts are being installed.
        # Remove that queue first, then replace Publishing truth before CardNews
        # truth. Any interrupted mixed generation is therefore fail-closed.
        Path("storage/publishing/publish_queue.json").unlink(missing_ok=True)
        receipts = (
            (self.output_dir / "08_publishing_result.json", active["publishing"]),
            (self.output_dir / "06_publishing_result.json", active["publishing"]),
            (self.output_dir / "09_publishing_result.json", active["publishing"]),
            (Path("storage/publishing/publishing_result.json"), active["publishing"]),
            (Path("storage/outputs/publishing_result.json"), active["publishing"]),
            (self.output_dir / "05_card_news_result.json", active["card_news_result"]),
            (self.output_dir / "07_card_news_result.json", active["card_news_result"]),
            (self.output_dir / "08_card_news_result.json", active["card_news_result"]),
            (Path("storage/outputs/card_news_result.json"), active["card_news_result"]),
            (Path("storage/card_news/card_news_quality.json"), active["quality"]),
        )
        direct_receipts = {}
        publishing_payload = self._load_output_set_json(active["publishing"])
        direct_receipts[self.output_dir / "final_result.json"] = {
            "status": "legacy_receipt_blocked",
            "output_set_id": publishing_payload["output_set_id"],
            "release_ready": False,
            "package_ready": False,
            "publishing_ready": False,
            "actual_publish": False,
            "selectable": False,
            "superseded_by": "storage/workflow_results/99_final_result.json",
        }
        if isinstance(image_generation_result, dict):
            direct_receipts[
                self.output_dir / "07_image_generation_result.json"
            ] = image_generation_result
            direct_receipts[
                Path("storage/outputs/image_generation_result.json")
            ] = image_generation_result
        for destination, source in receipts:
            payload = self._load_output_set_json(source)
            temporary = destination.with_name(
                f".{destination.name}.{payload['output_set_id']}.tmp"
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                with open(temporary, "w", encoding="utf-8") as file:
                    json.dump(payload, file, ensure_ascii=False, indent=2)
                    file.flush()
                    os.fsync(file.fileno())
                self._replace_receipt_with_retry(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)

        for destination, payload in direct_receipts.items():
            temporary = destination.with_name(
                f".{destination.name}.{payload['output_set_id']}.tmp"
            )
            try:
                with open(temporary, "w", encoding="utf-8") as file:
                    json.dump(payload, file, ensure_ascii=False, indent=2)
                    file.flush()
                    os.fsync(file.fileno())
                self._replace_receipt_with_retry(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)

        for legacy_card in Path("storage/card_news").glob("card_news_*.png"):
            legacy_card.unlink(missing_ok=True)

    @staticmethod
    def _replace_receipt_with_retry(source, destination):
        for attempt in range(20):
            try:
                os.replace(source, destination)
                return
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(0.01)

    def _run_ai_planner(self, trend_result, topic_result):
        """
        AI Planner (Sprint 15-3): Hint Layer 실행. 실패하거나 예외가 나면 반드시
        `None`을 반환한다 - 호출자(및 이 결과를 받는 모든 하위 Engine의
        PlannerConsumerAdapter)는 `None`을 "Planner 없음"과 동일하게 다뤄
        기존 로직을 그대로 사용한다("Planner Result 없음 -> 기존 Engine 그대로"
        절대 규칙). 이 메서드 자체가 예외를 던지는 일은 없다.
        """
        try:
            interface = self.ai_planner_module.interface
            historical_inputs = interface.load_historical_inputs()
            brand_profile = interface.load_brand_profile()

            context = PlanningContext(
                trend_result=trend_result if isinstance(trend_result, dict) else {},
                topic_result=topic_result if isinstance(topic_result, dict) else {},
                brand_profile=brand_profile,
                **historical_inputs,
            )

            return self.ai_planner_module.run(context)
        except Exception as error:
            print(f"AI Planner Fallback Used (Workflow continues unaffected): {error}")
            return None

    def _run_pattern_engine(self, topic_result, trend_result, planner_result=None):
        try:
            selected_topic = {}

            if isinstance(topic_result, dict):
                selected_topic = topic_result.get("selected_topic", {})

            return self.pattern_engine.run(
                selected_topic=selected_topic,
                trend_result=trend_result,
                planner_result=planner_result,
            )

        except Exception as error:
            pattern_result = {
                "status": "pattern_selected",
                "selected_topic": {},
                "topic_intelligence": {
                    "keywords": [],
                    "keyword_weights": {},
                    "category": "trend",
                    "cluster": "general_trend_cluster",
                    "confidence_score": 0.0,
                    "blocked": False,
                    "reason": f"fallback: pattern_engine_error: {error}",
                },
                "pattern_plan": {
                    "pattern_type": "resource",
                    "hook_type": "saveable_tip",
                    "cta_type": "save",
                    "layout_type": "bold_ai",
                    "reason": "PatternEngineModule failed; safe default pattern used.",
                },
                "fallback_used": True,
            }

            try:
                PatternResultWriter().write(pattern_result)
            except Exception as write_error:
                print(f"Pattern Fallback Write Failed: {write_error}")

            print(f"Pattern Engine Fallback Used: {error}")
            return pattern_result

    def _run_knowledge_engine(
        self,
        trend_result,
        topic_result,
        pattern_result,
        research_result,
        content_result,
        image_strategy_result,
        card_news_result,
        publishing_result,
        planner_result=None,
    ):
        try:
            return self.knowledge_module.run(
                pattern_result=pattern_result,
                research_result=research_result,
                content_result=content_result,
                image_strategy_result=image_strategy_result,
                card_news_result=card_news_result,
                publishing_result=publishing_result,
                trend_result=trend_result,
                topic_result=topic_result,
                planner_result=planner_result,
            )
        except Exception as error:
            print(f"Knowledge Engine Fallback Used: {error}")
            return {
                "status": "knowledge_extracted",
                "extracted_count": 0,
                "new_count": 0,
                "updated_count": 0,
                "total_knowledge_count": 0,
                "by_type": {},
                "top_knowledge": [],
                "statistics": {},
                "fallback_used": True,
                "reason": f"knowledge_engine_error: {error}",
            }

    def _run_safe(self, engine_label, empty_result_fn, run_fn, **kwargs):
        """
        Sprint 12에서 추가된 Engine들의 공용 안전 실행 래퍼. 각 Engine의 run()이
        자체적으로 내부 fallback을 갖추고 있어도, WorkflowEngine 레벨에서 한 번 더
        try/except로 감싸 어떤 Engine 하나가 완전히 실패하더라도 workflow_failed로
        이어지지 않고 안전한 기본 결과로 다음 단계가 계속 진행되도록 한다
        (Pattern Engine/Knowledge Engine과 동일한 이중 안전망 패턴).
        """
        try:
            return run_fn(**kwargs)
        except Exception as error:
            print(f"{engine_label} Fallback Used: {error}")
            return empty_result_fn(reason=f"{engine_label.lower().replace(' ', '_')}_error: {error}")

    def _empty_performance_score_result(self, reason):
        # Sprint 16-0: 이 WorkflowEngine 레벨 안전망은 PerformanceScoreModule 자신의
        # run()/_fallback_result()가 잡지 못한 완전한 예외 상황에서만 쓰인다 - 그런
        # 경우에도 Codex 검수 지적대로 Metadata 표준 필드가 빠지면 안 되므로 동일하게
        # 채운다.
        return {
            "status": "performance_score_completed",
            "hook_score": 0.5, "cta_score": 0.5, "layout_score": 0.5,
            "brand_score": 0.5, "image_score": 0.5, "overall_performance_score": 0.5,
            "planner_used": False,
            "planner_helpful": False,
            "planner_rejected": False,
            "planner_reason": f"Performance Score 완전 실패로 Planner 적용 여부를 판정하지 않음: {reason}",
            "fallback_used": True,
            "reason": reason,
        }

    def _empty_audit_result(self, reason):
        return {
            "status": "audit_completed",
            "checks": {},
            "audit_score": 0.0,
            "passed": False,
            "strengths": [],
            "weaknesses": [],
            "recommendations": ["audit_engine 계산 실패 - 수동 검수 필요"],
            "knowledge_used": False,
            "knowledge_items": [],
            "knowledge_influence": "",
            "fallback_used": True,
            "reason": reason,
        }

    def _empty_learning_result(self, reason):
        return {
            "status": "learning_completed",
            "internal_learning_score": 0.0,
            "audit_score": 0.0,
            "performance_score": 0.0,
            "knowledge_score": 0.0,
            "is_good_run": False,
            "promoted_count": 0,
            "promoted_entries": [],
            "total_memory_count": 0,
            "knowledge_used": False,
            "knowledge_items": [],
            "knowledge_influence": "",
            "evidence_metadata": {
                "audit_score": build_standard_metadata(source=SOURCE_LOCAL_QUALITY, confidence=None, note=f"완전 실패: {reason}"),
                "performance_score": build_standard_metadata(source=SOURCE_LOCAL_QUALITY, confidence=None, note=f"완전 실패: {reason}"),
                "knowledge_score": build_standard_metadata(source=SOURCE_RUNTIME, confidence=None, note=f"완전 실패: {reason}"),
            },
            "planner_evidence_used": False,
            "fallback_used": True,
            "reason": reason,
        }

    def _empty_analytics_result(self, reason):
        return {
            "status": "analytics_completed",
            "current_performance_score": 0.0,
            "current_audit_score": 0.0,
            "historical_average_performance_score": None,
            "sample_size": 0,
            "quality_trend": "insufficient_history",
            "measurement_metadata": {
                "current_performance_score": build_standard_metadata(source=SOURCE_LOCAL_QUALITY, confidence=None, note=f"완전 실패: {reason}"),
                "current_audit_score": build_standard_metadata(source=SOURCE_LOCAL_QUALITY, confidence=None, note=f"완전 실패: {reason}"),
                "historical_average_performance_score": build_standard_metadata(source=SOURCE_HISTORICAL, confidence=None, sample_size=0, note=f"완전 실패: {reason}"),
                "quality_trend": build_standard_metadata(source=SOURCE_ESTIMATED, confidence=None, sample_size=0, note=f"완전 실패: {reason}"),
            },
            "fallback_used": True,
            "reason": reason,
        }

    def _empty_brand_dna_result(self, reason):
        return {
            "status": "brand_dna_updated",
            "brand_profile": {},
            "observation": {},
            "dominant_hook_type": "",
            "dominant_cta_type": "",
            "dominant_layout_type": "",
            "dominant_color": "",
            "total_observations": 0,
            "fallback_used": True,
            "reason": reason,
        }

    def _empty_trend_memory_result(self, reason):
        return {
            "status": "trend_memory_recorded",
            "current": {},
            "topic_repeat_risk": "low",
            "topic_similarity": 0.0,
            "matched_topic": "",
            "element_repeat_counts": {},
            "total_memory_count": 0,
            "fallback_used": True,
            "reason": reason,
        }

    def _empty_competitor_result(self, reason):
        return {
            "status": "competitor_profile_built",
            "benchmark": {"status": "benchmark_unavailable", "sections": [], "fallback_used": True},
            "community": {"status": "community_unavailable", "sources": [], "fallback_used": True},
            "news": {"status": "news_unavailable", "source": {}, "fallback_used": True},
            "instagram_benchmark": {"status": "instagram_benchmark_unavailable", "accounts": [], "fallback_used": True},
            "tools_funnel": {"status": "tools_funnel_unavailable", "references": [], "fallback_used": True},
            "account_profiles": [],
            "hook_and_cta_map": {"hook_sections": [], "cta_sections": []},
            "repeated_content_patterns": [],
            "format_comparison": {
                "status": "no_account_profiles",
                "account_count": 0,
                "layout_distribution": {},
                "cta_distribution": {},
                "image_strategy_distribution": {},
            },
            "gap_analysis_input": {
                "benchmark_hook_count": 0,
                "benchmark_cta_count": 0,
                "community_signal_available": False,
                "news_signal_available": False,
                "account_profile_count": 0,
                "high_priority_account_count": 0,
            },
            "fallback_used": True,
            "reason": reason,
        }

    def _save_workflow_result(self, filename, data):
        file_path = self.output_dir / filename

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        print(f"Workflow Result Saved: {file_path}")
