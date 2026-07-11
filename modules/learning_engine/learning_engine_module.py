import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.base_module import BaseModule
from modules.brand_dna_engine.brand_dna_interface import BrandDNAInterface
from modules.common.metadata_standard import SOURCE_LOCAL_QUALITY, SOURCE_RUNTIME, build_standard_metadata
from modules.competitor_learning.competitor_learning_interface import CompetitorLearningInterface
from modules.competitor_learning.competitor_learning_storage import CompetitorLearningStorage
from modules.learning_engine.content_performance_history import ContentPerformanceHistory
from modules.learning_engine.learning_history import LearningHistory
from modules.learning_engine.learning_interface import LearningInterface
from modules.learning_engine.learning_performance_analyzer import LearningPerformanceAnalyzer
from modules.learning_engine.learning_score import LearningScorer
from modules.learning_engine.learning_selector import LearningSelector
from modules.learning_engine.learning_storage import LearningStorage


class LearningEngineModule(BaseModule):
    """
    Learning Engine v2 (Sprint 13).

    실제 SNS 성과 데이터(조회수/저장수 등)는 없으므로 가짜 성과를 만들지 않는다.
    대신 이미 로컬에서 실제로 계산된 audit_score + performance_score +
    knowledge_score(이번 실행에서 Knowledge Engine이 추출한 top_knowledge의
    overall_score 평균)를 합쳐 `internal_learning_score`를 만든다.

    `internal_learning_score`가 기준(0.65) 이상인 "좋은 실행"에서 나온 고성과
    Hook/CTA/Pattern/Layout/Brand Knowledge만 골라
    storage/learning/learning_memory.json에 승격(promote)한다. 같은 항목이 여러 번
    좋은 실행에서 반복되면 memory_score가 점점 올라간다(reinforcement).

    Knowledge DB를 실제로 읽어 knowledge_score/승격 후보를 만들므로
    `knowledge_used`/`knowledge_items`/`knowledge_influence` 필드로 사용 흔적을
    남긴다.

    이 Engine은 외부 네트워크/LLM을 호출하지 않으며, 계산 실패 시 승격 없이 안전한
    기본 결과를 반환한다.

    Self Reference Guard 검증 (Sprint 16-0, Intelligence Feedback Safety Audit):
    `run()`/`_build_result()`는 `knowledge_result`/`performance_score_result`/
    `audit_result` 3개만 입력으로 받는다 - `planner_result`나 AI Planner의 어떤
    출력도 파라미터로 받지 않으며, `internal_learning_score`는 항상 이 3개
    입력에서 실제로 계산된 값에서만 나온다. 즉 Learning Engine은 "Planner
    Decision을 무조건 강화"할 수 없다 - Planner를 아예 참조하지 않기 때문이다.
    이 사실은 `evidence_metadata`/`planner_evidence_used: False` 필드로 결과에
    명시적으로 기록되며, `tests/test_intelligence_feedback_safety.py`가 이
    시그니처(파라미터 이름 목록에 "planner"가 없는지)를 회귀 테스트로 고정한다.
    """

    # Instagram Intelligence Phase 최종 검증: content_performance_history/
    # Knowledge Feedback/learning_delta는 실제 Instagram 좋아요/댓글/저장/
    # 공유/도달 성과가 아니라 발행 전 내부 content quality_score(Content
    # Engine이 이미 계산한 값)를 사용한다. 실제 외부 성과 API 연동 전까지
    # 이 사실을 결과 구조에 항상 명시적으로 기록한다 - 실제 시장 성과로
    # 오인되지 않도록 하기 위함이다. 값을 새로 만들지 않고, 이미 참인 사실을
    # 라벨링만 한다.
    INTERNAL_QUALITY_PROXY_METADATA = {
        "performance_source": "internal_quality_proxy",
        "external_metrics_used": False,
        "external_metrics_available": False,
        "learning_scope": "pre_publish_internal_feedback",
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}

        self.selector = LearningSelector(self.config)
        self.scorer = LearningScorer(self.config)
        self.storage = LearningStorage()
        self.history = LearningHistory()
        self.interface = LearningInterface(self.storage)

        # Instagram Intelligence Phase 2: Learning Engine 확장.
        # 새 Engine을 만들지 않고, 같은 modules/learning_engine/ 안에서
        # Performance History 저장/분석 클래스만 추가한다.
        self.performance_history = ContentPerformanceHistory()
        self.performance_analyzer = LearningPerformanceAnalyzer(self.config)

        # 이미 존재하는 다른 Engine의 최신 산출물을 읽기 전용으로 참고한다
        # (WorkflowEngine 호출부는 건드리지 않는다 - 이 Engine이 스스로 파일을
        # 읽는다. Pattern Engine/Content Module 모두 Learning Engine보다 먼저
        # 실행되므로 storage/pattern/pattern_result.json과
        # storage/workflow_results/05_content_result.json은 이번 실행의 실제
        # 결과다).
        self.pattern_result_path = Path("storage/pattern/pattern_result.json")
        self.content_result_path = Path("storage/workflow_results/05_content_result.json")
        self.brand_dna_interface = BrandDNAInterface()

        # Knowledge Feedback (Instagram Intelligence Phase 2): Competitor
        # Learning Knowledge Database의 entry별 confidence만 조정한다 - 새
        # 스코어링 알고리즘을 만들지 않고 CompetitorLearningStorage에 추가된
        # adjust_entry_confidence()(기존 overall_score 공식 재사용)를 그대로
        # 호출한다.
        self.competitor_learning_storage = CompetitorLearningStorage()

        # Dashboard 병합 대상은 Competitor Learning Engine이 이미 소유한
        # storage/dashboard/daily_learning_report.json이다 - 새 Dashboard
        # Engine을 만들지 않고 같은 Storage를 재사용한다.
        self.dashboard_storage = self.competitor_learning_storage

    def run(
        self,
        knowledge_result: Optional[Dict[str, Any]] = None,
        performance_score_result: Optional[Dict[str, Any]] = None,
        audit_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        print("Learning Engine Module Started")

        try:
            result = self._build_result(
                knowledge_result or {}, performance_score_result or {}, audit_result or {}
            )
        except Exception as error:
            print(f"Learning Engine Module Failed, safe fallback returned: {error}")
            result = self._fallback_result(reason=f"learning_engine_exception: {error}")

        print("Learning Engine Module Finished")
        return result

    def _build_result(
        self,
        knowledge_result: Dict[str, Any],
        performance_score_result: Dict[str, Any],
        audit_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        top_knowledge = knowledge_result.get("top_knowledge", [])
        if not isinstance(top_knowledge, list):
            top_knowledge = []

        selection = self.selector.select(top_knowledge, performance_score_result, audit_result)
        candidates: List[Dict[str, Any]] = selection.get("candidates", [])

        existing_memory = {
            record.get("knowledge_id"): record
            for record in self.storage.load_memory()
            if isinstance(record, dict) and record.get("knowledge_id")
        }

        promoted_entries = []

        for candidate in candidates:
            knowledge_id = candidate.get("knowledge_id")
            existing_entry = existing_memory.get(knowledge_id)

            score_result = self.scorer.compute(existing_entry, float(candidate.get("overall_score", 0.0)))

            promoted_entries.append({
                "knowledge_id": knowledge_id,
                "type": candidate.get("type"),
                "title": candidate.get("title"),
                "memory_score": score_result.get("memory_score", 0.0),
                "reinforced_count": score_result.get("reinforced_count", 1),
                "promoted_at": datetime.now().isoformat(),
            })

        if promoted_entries:
            self.storage.upsert_memory(promoted_entries)

        statistics = self.storage.update_statistics(
            is_good_run=bool(selection.get("is_good_run", False)),
            promoted_count=len(promoted_entries),
        )

        # Instagram Intelligence Phase 2: learning_delta는 "직전 실행 대비
        # internal_learning_score가 얼마나 바뀌었는지"이므로, 이번 실행 기록을
        # 남기기 전에 이전 기록부터 먼저 읽어 둔다.
        previous_learning_records = self.history.load()
        previous_internal_learning_score = (
            previous_learning_records[-1].get("internal_learning_score")
            if previous_learning_records and isinstance(previous_learning_records[-1], dict)
            else None
        )

        self.history.record(
            internal_learning_score=selection.get("internal_learning_score", 0.0),
            is_good_run=bool(selection.get("is_good_run", False)),
            promoted_count=len(promoted_entries),
        )

        knowledge_items = [
            {"knowledge_id": item.get("knowledge_id"), "type": item.get("type"), "title": item.get("title")}
            for item in top_knowledge
        ]

        learning_delta = self._compute_learning_delta(
            selection.get("internal_learning_score", 0.0), previous_internal_learning_score
        )

        performance_history_entry = self._record_performance_history()
        performance_analysis = self.performance_analyzer.analyze(self.performance_history.load_all())
        knowledge_feedback = self._apply_knowledge_feedback(
            performance_history_entry, bool(selection.get("is_good_run", False))
        )

        self._merge_dashboard(performance_analysis, learning_delta, knowledge_feedback)

        return {
            "status": "learning_completed",
            "internal_learning_score": selection.get("internal_learning_score", 0.0),
            "audit_score": selection.get("audit_score", 0.0),
            "performance_score": selection.get("performance_score", 0.0),
            "knowledge_score": selection.get("knowledge_score", 0.0),
            "is_good_run": selection.get("is_good_run", False),
            "promoted_count": len(promoted_entries),
            "promoted_entries": promoted_entries,
            "total_memory_count": statistics.get("total_memory_count", 0),
            "knowledge_used": selection.get("knowledge_used", bool(knowledge_items)),
            "knowledge_items": knowledge_items,
            "knowledge_influence": (
                f"knowledge_score={selection.get('knowledge_score', 0.0)}를 internal_learning_score 계산에 "
                f"반영함(가중치 {LearningSelector.KNOWLEDGE_WEIGHT}). {len(promoted_entries)}건을 "
                "learning_memory에 승격함." if knowledge_items else
                "이번 실행에서 참고할 Knowledge 항목이 없어 knowledge_score는 기본값(0.5)을 사용함."
            ),
            "reason": selection.get("reason", ""),
            "fallback_used": False,
            # Learning 검증 (Sprint 16-0): internal_learning_score의 3개 구성
            # 요소가 전부 이번 실행에서 실제로 계산된 로컬 품질 대리 지표임을
            # 명시한다. Evidence가 실제로 없으면(모두 계산 실패) Learning
            # Score를 올릴 근거 자체가 없다는 점도 이 metadata로 드러난다.
            "evidence_metadata": {
                "audit_score": build_standard_metadata(
                    source=SOURCE_LOCAL_QUALITY, confidence=None, note="Audit Engine이 이번 실행에서 실제로 계산."
                ),
                "performance_score": build_standard_metadata(
                    source=SOURCE_LOCAL_QUALITY, confidence=None, note="Performance Score Engine이 이번 실행에서 실제로 계산."
                ),
                "knowledge_score": build_standard_metadata(
                    source=SOURCE_RUNTIME,
                    confidence=None,
                    note="이번 실행에서 Knowledge Engine이 추출한 top_knowledge의 실제 overall_score 평균.",
                ),
            },
            # Self Reference Guard 검증 (Sprint 16-0): Learning Engine은
            # AI Planner의 어떤 출력도 입력으로 받지 않는다 - internal_learning_
            # score는 항상 audit/performance/knowledge 3개의 실제 계산값에서만
            # 나온다. 이 필드는 항상 False이며, 향후 누군가 실수로 Planner
            # Decision을 강화 근거로 추가하면 이 값과 그 근거를 함께 갱신해야
            # 한다(회귀 테스트로 고정됨).
            "planner_evidence_used": False,
            # Instagram Intelligence Phase 2: Content -> Performance History ->
            # Learning -> Knowledge -> Brand DNA -> Pattern -> Content Closed
            # Loop. 이 4개 필드는 모두 이미 계산된 값의 기록/집계/참고 조정
            # 결과이며, 새로운 선택 알고리즘이 아니다.
            "performance_history_entry": performance_history_entry,
            "performance_analysis": {**performance_analysis, **self.INTERNAL_QUALITY_PROXY_METADATA},
            "knowledge_feedback": knowledge_feedback,
            "learning_delta": learning_delta,
            # 이번 최종 검증 지시의 명시적 요구: 이 4개 필드는 실제 Instagram
            # 좋아요/댓글/저장/공유/도달이 아니라 발행 전 내부 content
            # quality_score 기반 값임을 결과 최상위에서도 다시 한번 명시한다.
            **self.INTERNAL_QUALITY_PROXY_METADATA,
            "created_at": datetime.now().isoformat(),
        }

    def _load_pattern_result(self) -> Dict[str, Any]:
        try:
            if not self.pattern_result_path.exists():
                return {}
            with open(self.pattern_result_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            return data if isinstance(data, dict) else {}
        except Exception as error:
            print(f"Learning Engine Pattern Result Load Failed: {error}")
            return {}

    def _load_content_result(self) -> Dict[str, Any]:
        try:
            if not self.content_result_path.exists():
                return {}
            with open(self.content_result_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            return data if isinstance(data, dict) else {}
        except Exception as error:
            print(f"Learning Engine Content Result Load Failed: {error}")
            return {}

    def _record_performance_history(self) -> Dict[str, Any]:
        """
        Performance History 구축 (Instagram Intelligence Phase 2): 이미
        계산되어 있는 값(pattern_result.json/05_content_result.json/Brand DNA
        Interface)만 옮겨 적는다. 존재하지 않는 값은 만들어내지 않고 그대로
        비워 둔다. 실패해도 예외를 던지지 않는다.
        """
        try:
            pattern_result = self._load_pattern_result()
            content_result = self._load_content_result()

            pattern_plan = pattern_result.get("pattern_plan") or {}
            content_intelligence = content_result.get("content_intelligence") or {}

            title = str(content_result.get("title", ""))
            caption = str(content_result.get("caption", ""))
            recorded_at = datetime.now().isoformat()

            # 위험 A 방지: content_id는 콘텐츠 자체의 값(title/caption)만으로
            # 구성한다 - 기록 시각(recorded_at)을 id에 섞으면 같은 콘텐츠를
            # 다시 처리할 때마다 다른 id가 나와 record_once()의 중복 방지가
            # 작동하지 않게 된다.
            entry = {
                "content_id": self.performance_history.build_content_id(title, caption),
                "created_at": recorded_at,
                "hook": pattern_plan.get("hook_type", ""),
                "cta": pattern_plan.get("cta_type", ""),
                "pattern": pattern_plan.get("pattern_type", ""),
                "layout": pattern_plan.get("layout_type", ""),
                "brand_dna_snapshot": self.brand_dna_interface.get_dominant_preferences(),
                "quality_score": content_intelligence.get("quality_score"),
                "competitor_reference": content_result.get("competitor_learning_items", []),
                "knowledge_reference": content_result.get("knowledge_items", []),
                **self.INTERNAL_QUALITY_PROXY_METADATA,
            }

            was_recorded = self.performance_history.record_once(entry)
            entry["deduplicated"] = not was_recorded
            return entry
        except Exception as error:
            print(f"Learning Engine Performance History Record Failed: {error}")
            return {
                "content_id": "",
                "created_at": datetime.now().isoformat(),
                "hook": "",
                "cta": "",
                "pattern": "",
                "layout": "",
                "brand_dna_snapshot": {},
                "quality_score": None,
                "competitor_reference": [],
                "knowledge_reference": [],
                "reason": str(error),
                **self.INTERNAL_QUALITY_PROXY_METADATA,
            }

    def _apply_knowledge_feedback(
        self, performance_history_entry: Dict[str, Any], is_good_run: bool
    ) -> Dict[str, Any]:
        """
        Knowledge Feedback (Instagram Intelligence Phase 2): 이번 실행이 좋은
        실행(is_good_run)이면 이번에 실제로 선택된 hook/cta/pattern에 해당하는
        Competitor Learning Knowledge Database 항목의 confidence를
        `LearningScorer.REINFORCEMENT_STEP`(기존 상수 재사용, 새 값을 발명하지
        않음)만큼 올리고, 아니면 같은 폭만큼 내린다. knowledge_id가 정확히
        일치하는 항목만 조정하며, 없으면 아무 것도 하지 않는다(새 entry를
        만들지 않는다).

        layout은 의도적으로 제외한다 - 이번 pattern_plan.layout_type은
        카드뉴스 LayoutSelector 어휘(bold_ai 등)이고, Competitor Learning의
        layout entry는 Instagram 게시물 형식(carousel 등)이라 서로 다른
        체계다(Pattern Engine의 Competitor Learning 소비와 동일한 이유로
        매핑하지 않는다).

        위험 B 방지: `performance_history_entry["deduplicated"]`가 True면(=
        이 content_id가 이미 이전에 기록된 적이 있어 이번에는 History에
        새로 추가되지 않았으면) confidence를 다시 조정하지 않는다 - 같은
        콘텐츠를 반복 처리해도 ±0.05가 매번 누적되지 않도록 한다.
        """
        try:
            if performance_history_entry.get("deduplicated"):
                return {
                    "is_good_run": is_good_run,
                    "delta_applied": 0.0,
                    "adjusted_count": 0,
                    "adjustments": [],
                    "skipped_reason": "이미 처리된 content_id라 confidence를 다시 조정하지 않음(중복 방지).",
                }

            delta = LearningScorer.REINFORCEMENT_STEP if is_good_run else -LearningScorer.REINFORCEMENT_STEP
            adjustments = []

            for entry_type, value in (
                ("hook", performance_history_entry.get("hook")),
                ("cta", performance_history_entry.get("cta")),
                ("pattern", performance_history_entry.get("pattern")),
            ):
                if not value:
                    continue

                knowledge_id = f"competitor_learning_{entry_type}_{value}"
                updated_entry = self.competitor_learning_storage.adjust_entry_confidence(knowledge_id, delta)

                if updated_entry is not None:
                    adjustments.append({
                        "knowledge_id": knowledge_id,
                        "type": entry_type,
                        "value": value,
                        "delta": delta,
                        "new_confidence": (updated_entry.get("score") or {}).get("confidence"),
                    })

            return {
                "is_good_run": is_good_run,
                "delta_applied": delta if adjustments else 0.0,
                "adjusted_count": len(adjustments),
                "adjustments": adjustments,
            }
        except Exception as error:
            print(f"Learning Engine Knowledge Feedback Failed: {error}")
            return {
                "is_good_run": is_good_run,
                "delta_applied": 0.0,
                "adjusted_count": 0,
                "adjustments": [],
                "reason": str(error),
            }

    def _compute_learning_delta(
        self, current_internal_learning_score: float, previous_internal_learning_score: Optional[float]
    ) -> Dict[str, Any]:
        try:
            if not isinstance(previous_internal_learning_score, (int, float)):
                return {
                    "previous": None,
                    "current": current_internal_learning_score,
                    "delta": None,
                    "reason": "이전 실행 기록이 없어 delta를 계산하지 않음.",
                }

            delta = round(float(current_internal_learning_score) - float(previous_internal_learning_score), 4)
            return {
                "previous": previous_internal_learning_score,
                "current": current_internal_learning_score,
                "delta": delta,
            }
        except Exception as error:
            return {"previous": None, "current": current_internal_learning_score, "delta": None, "reason": str(error)}

    def _merge_dashboard(
        self,
        performance_analysis: Dict[str, Any],
        learning_delta: Dict[str, Any],
        knowledge_feedback: Dict[str, Any],
    ) -> None:
        """
        Dashboard (Instagram Intelligence Phase 2): storage/dashboard/
        daily_learning_report.json은 Competitor Learning Engine이 이미
        소유한 파일이다. 이 메서드는 그 파일을 불러와 top_performing_pattern/
        weakest_pattern/learning_delta/knowledge_delta 키만 추가/갱신하고
        나머지 키(hook_top10 등, Brand DNA가 이미 추가한 brand_dna_change 등)는
        그대로 둔다 - 새 Dashboard Engine을 만들지 않는다.
        """
        try:
            report = self.dashboard_storage.load_dashboard()
            if not isinstance(report, dict):
                report = {}

            report["top_performing_pattern"] = performance_analysis.get("top_performing_pattern", "")
            report["weakest_pattern"] = performance_analysis.get("weakest_pattern", "")
            report["learning_delta"] = learning_delta
            report["knowledge_delta"] = {
                "adjusted_count": knowledge_feedback.get("adjusted_count", 0),
                "delta_applied": knowledge_feedback.get("delta_applied", 0.0),
            }
            # 최종 검증 지시: Dashboard에서도 top_performing_pattern/weakest_pattern/
            # learning_delta/knowledge_delta가 실제 Instagram 성과가 아니라
            # 발행 전 내부 quality_score 기반 값임을 명시한다("Internal Quality
            # Feedback" - 실제 게시 후 성과 데이터가 아님).
            report["internal_quality_feedback_metadata"] = {
                **self.INTERNAL_QUALITY_PROXY_METADATA,
                "label": "Internal Quality Feedback (Pre-Publish)",
                "note": (
                    "top_performing_pattern/weakest_pattern/learning_delta/knowledge_delta는 "
                    "실제 Instagram 좋아요/댓글/저장/공유/도달 성과가 아니라, 발행 전 내부 "
                    "content quality_score를 기반으로 한 값이다. 실제 게시 후 성과는 "
                    "Meta API/게시 결과 Import가 연결되기 전까지 존재하지 않는다."
                ),
            }

            self.dashboard_storage.save_dashboard(report)
        except Exception as error:
            print(f"Learning Engine Dashboard Merge Failed: {error}")

    def _fallback_result(self, reason: str) -> Dict[str, Any]:
        try:
            statistics = self.storage.load_statistics()
        except Exception:
            statistics = {}

        return {
            "status": "learning_completed",
            "internal_learning_score": 0.0,
            "audit_score": 0.0,
            "performance_score": 0.0,
            "knowledge_score": 0.0,
            "is_good_run": False,
            "promoted_count": 0,
            "promoted_entries": [],
            "total_memory_count": statistics.get("total_memory_count", 0) if isinstance(statistics, dict) else 0,
            "knowledge_used": False,
            "knowledge_items": [],
            "knowledge_influence": "",
            "evidence_metadata": {
                "audit_score": build_standard_metadata(source=SOURCE_LOCAL_QUALITY, confidence=None, note="계산 실패로 기본값 사용."),
                "performance_score": build_standard_metadata(source=SOURCE_LOCAL_QUALITY, confidence=None, note="계산 실패로 기본값 사용."),
                "knowledge_score": build_standard_metadata(source=SOURCE_RUNTIME, confidence=None, note="계산 실패로 기본값 사용."),
            },
            "planner_evidence_used": False,
            "performance_history_entry": {**self.INTERNAL_QUALITY_PROXY_METADATA},
            "performance_analysis": {
                "sample_size": 0,
                "average_quality_score": None,
                "top_performance": [],
                "worst_performance": [],
                "top_performing_pattern": "",
                "weakest_pattern": "",
                **self.INTERNAL_QUALITY_PROXY_METADATA,
            },
            "knowledge_feedback": {"is_good_run": False, "delta_applied": 0.0, "adjusted_count": 0, "adjustments": []},
            **self.INTERNAL_QUALITY_PROXY_METADATA,
            "learning_delta": {"previous": None, "current": 0.0, "delta": None},
            "reason": reason,
            "fallback_used": True,
            "created_at": datetime.now().isoformat(),
        }
