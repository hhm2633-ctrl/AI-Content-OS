from datetime import datetime
from typing import Any, Dict, Optional

from modules.base_module import BaseModule
from modules.brand_dna_engine.brand_dna_history import BrandDNAHistory
from modules.brand_dna_engine.brand_dna_interface import BrandDNAInterface
from modules.brand_dna_engine.brand_dna_storage import BrandDNAStorage
from modules.brand_dna_engine.brand_dna_tracker import BrandDNATracker
from modules.brand_dna_engine.brand_profile_loader import BrandProfileLoader
from modules.competitor_learning.competitor_learning_interface import CompetitorLearningInterface
from modules.competitor_learning.competitor_learning_storage import CompetitorLearningStorage
from modules.learning_engine.learning_interface import LearningInterface


class BrandDNAEngineModule(BaseModule):
    """
    Brand DNA Engine v1.

    config/brand_profile.json(톤/금칙어/타깃)에 더해, 실제 실행마다 사용된
    hook_type/cta_type/layout_type/highlight_color를 누적 관찰해 "이 브랜드가
    실제로 반복해서 사용하는 톤/색상/레이아웃/CTA/Hook"을 storage/brand_dna/에 쌓는다.

    이 Engine은 외부 네트워크/LLM을 호출하지 않으며, 계산 실패 시 브랜드 프로필만
    포함한 안전한 기본 결과를 반환한다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}

        self.profile_loader = BrandProfileLoader()
        self.tracker = BrandDNATracker(self.config)
        self.storage = BrandDNAStorage()
        self.history = BrandDNAHistory()
        self.interface = BrandDNAInterface(self.storage)

        # Competitor Learning Interface 연결(Sprint 18): 우리 브랜드 자신의
        # dominant_hook_type/dominant_cta_type/dominant_layout_type 계산 로직은
        # 전혀 건드리지 않고, Instagram Research로 관찰한 "계정별(경쟁 계정)"
        # hook/cta/pattern/layout 통계를 참고 정보로만 덧붙인다.
        self.competitor_learning_interface = CompetitorLearningInterface()

        # Phase: Instagram Intelligence. Dashboard 병합 대상 storage
        # (storage/dashboard/daily_learning_report.json)는 Competitor Learning
        # Engine이 이미 소유한 CompetitorLearningStorage를 그대로 재사용한다 -
        # 새 Dashboard Engine을 만들지 않는다.
        self.dashboard_storage = CompetitorLearningStorage()

        # Instagram Intelligence Phase 2: Brand DNA Feedback. Learning
        # Engine이 이미 계산해 둔 통계(storage/learning/learning_statistics.json)를
        # 참고만 한다 - 새 계산 로직을 만들지 않는다.
        self.learning_interface = LearningInterface()

        # Self Reference Guard 재사용(Phase 1의 PatternEngineModule과 동일한
        # 기준, AI Planner Decision Engine이 이미 쓰는 "독립 관찰 5회"와도
        # 동일) - Brand DNA 자신의 관찰 수가 이 기준을 넘기 전에는 Learning
        # 통계를 신뢰하지 않는다.
        self.LEARNING_FEEDBACK_MIN_INDEPENDENT_OBSERVATIONS = 5

    def run(
        self,
        pattern_result: Optional[Dict[str, Any]] = None,
        content_result: Optional[Dict[str, Any]] = None,
        card_news_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        print("Brand DNA Engine Module Started")

        try:
            result = self._build_result(pattern_result or {}, content_result or {}, card_news_result or {})
        except Exception as error:
            print(f"Brand DNA Engine Module Failed, safe fallback returned: {error}")
            result = self._fallback_result(reason=f"brand_dna_exception: {error}")

        print("Brand DNA Engine Module Finished")
        return result

    def _build_result(
        self,
        pattern_result: Dict[str, Any],
        content_result: Dict[str, Any],
        card_news_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        brand_profile = self.profile_loader.load()

        pattern_plan = pattern_result.get("pattern_plan") or {}
        layout_result = card_news_result.get("layout_result") or {}
        content_intelligence = content_result.get("content_intelligence") or {}
        brand_rule_passed = bool(content_intelligence.get("brand_rule_passed", True))

        # Self Reference Guard (Sprint 16-0): 이번 실행의 pattern_type/hook_type/
        # cta_type이 AI Planner Hint로 대체된 결과였는지 확인한다
        # (PatternEngineModule.planner_consumption.pattern.planner_applied, Sprint
        # 15-3에서 실제로 기록되기 시작한 필드). 이 관찰이 "독립적인 실제 브랜드
        # 사용 패턴"인지 "Planner 자신이 만든 결과"인지 구분해 tracker에 전달한다.
        planner_consumption = pattern_result.get("planner_consumption") or {}
        planner_influenced = bool((planner_consumption.get("pattern") or {}).get("planner_applied"))

        observation = self.tracker.observe(pattern_plan, layout_result, brand_rule_passed, planner_influenced)

        # Phase: Instagram Intelligence. update() 이전의 DNA 스냅샷을 먼저 잡아
        # 둬야 "이번 실행으로 무엇이 바뀌었는지"(brand_dna_change)를 계산할 수
        # 있다 - update() 자체는 기존 로직 그대로(관찰 1건 반영)이며 이 스냅샷은
        # 그 계산에 끼어들지 않는다.
        previous_dna = self.storage.load()

        dna = self.storage.update(brand_profile, observation)
        self.history.record(observation)

        brand_dna_change = self._compute_brand_dna_change(previous_dna, dna)
        brand_dna_delta = self._compute_brand_dna_delta(brand_dna_change)
        self._merge_brand_dna_change_into_dashboard(brand_dna_change, brand_dna_delta)

        return {
            "status": "brand_dna_updated",
            "brand_profile": brand_profile,
            "observation": observation,
            "dominant_hook_type": dna.get("dominant_hook_type", ""),
            "dominant_cta_type": dna.get("dominant_cta_type", ""),
            "dominant_layout_type": dna.get("dominant_layout_type", ""),
            "dominant_color": dna.get("dominant_color", ""),
            "total_observations": dna.get("total_observations", 0),
            "competitor_learning_reference": self._build_competitor_learning_reference(),
            "brand_dna_change": brand_dna_change,
            "brand_dna_delta": brand_dna_delta,
            "learning_feedback_reference": self._build_learning_feedback_reference(dna),
            "fallback_used": False,
            "created_at": datetime.now().isoformat(),
        }

    def _build_competitor_learning_reference(self) -> Dict[str, Any]:
        """
        Competitor Learning DB 참고(Sprint 18, Phase: Instagram Intelligence에서
        knowledge_database_change 추가): storage/knowledge/competitor_statistics.json
        (계정별 hook/cta/pattern/layout 통계)과 storage/knowledge/
        knowledge_database.json의 최신 new_count/total_count(Competitor Learning
        Engine이 이미 계산한 "이번 학습으로 늘어난 지식" 값)를 읽기 전용으로
        참고만 한다. 이 Engine 자신의 dominant_* 계산/저장 로직은 전혀 바꾸지
        않으며, 이 메서드는 절대 예외를 던지지 않는다.
        """
        try:
            if not self.competitor_learning_interface.is_available():
                return {
                    "available": False,
                    "account_profiles": {},
                    "account_count": 0,
                    "knowledge_database_change": {"new_count": 0, "total_count": 0},
                }

            competitor_statistics = self.competitor_learning_interface.get_competitor_statistics()
            accounts = competitor_statistics.get("accounts", {})
            knowledge_database = self.competitor_learning_interface.get_knowledge_database()

            return {
                "available": True,
                "account_profiles": accounts if isinstance(accounts, dict) else {},
                "account_count": competitor_statistics.get("account_count", 0),
                "knowledge_database_change": {
                    "new_count": knowledge_database.get("new_count", 0),
                    "total_count": knowledge_database.get("total_count", 0),
                },
            }
        except Exception as error:
            print(f"Brand DNA Competitor Learning Reference Failed: {error}")
            return {
                "available": False,
                "account_profiles": {},
                "account_count": 0,
                "knowledge_database_change": {"new_count": 0, "total_count": 0},
                "reason": str(error),
            }

    def _compute_brand_dna_change(self, previous_dna: Dict[str, Any], dna: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase: Instagram Intelligence. 이번 실행 전/후 Brand DNA의 dominant_*
        값을 비교해 "이번 학습으로 브랜드 성향이 실제로 바뀌었는지"를 기록한다.
        dominant_* 계산 자체(BrandDNAStorage.update())는 건드리지 않고, 이미
        계산된 이전/이후 값을 비교만 한다. 실패해도 예외를 던지지 않는다.
        """
        try:
            previous_dna = previous_dna if isinstance(previous_dna, dict) else {}
            fields = ("dominant_hook_type", "dominant_cta_type", "dominant_layout_type", "dominant_color")
            changes = {}

            for field in fields:
                previous_value = previous_dna.get(field, "")
                current_value = dna.get(field, "")
                changes[field] = {
                    "previous": previous_value,
                    "current": current_value,
                    "changed": bool(previous_value) and previous_value != current_value,
                }

            return {
                "changes": changes,
                "any_changed": any(entry["changed"] for entry in changes.values()),
                "total_observations": dna.get("total_observations", 0),
            }
        except Exception as error:
            return {"changes": {}, "any_changed": False, "total_observations": 0, "reason": str(error)}

    def _compute_brand_dna_delta(self, brand_dna_change: Dict[str, Any]) -> Dict[str, Any]:
        """
        Instagram Intelligence Phase 2: `brand_dna_change`(필드별 이전/이후
        상세)를 요약한 값이다 - 새 계산을 하지 않고 이미 계산된 `changes`를
        세기만 한다.
        """
        try:
            changes = brand_dna_change.get("changes") or {}
            changed_fields = [field for field, entry in changes.items() if isinstance(entry, dict) and entry.get("changed")]

            return {
                "changed_fields_count": len(changed_fields),
                "changed_fields": changed_fields,
                "any_changed": bool(brand_dna_change.get("any_changed", False)),
            }
        except Exception as error:
            return {"changed_fields_count": 0, "changed_fields": [], "any_changed": False, "reason": str(error)}

    def _build_learning_feedback_reference(self, dna: Dict[str, Any]) -> Dict[str, Any]:
        """
        Brand DNA Feedback (Instagram Intelligence Phase 2): Learning Engine이
        이미 계산해 둔 통계(storage/learning/learning_statistics.json:
        total_runs/total_good_runs)를 참고만 한다 - Brand DNA 자신의 dominant_*
        계산/저장 로직은 전혀 바꾸지 않는다.

        Self Reference Guard 유지: `total_observations`에서
        `planner_influenced_observations`를 뺀 "독립 관찰 수"가
        `LEARNING_FEEDBACK_MIN_INDEPENDENT_OBSERVATIONS`(5, Pattern Engine의
        Brand DNA 소비 및 AI Planner Decision Engine과 동일한 기준) 미만이면
        참고하지 않는다 - Phase 1에서 Pattern Engine에 적용한 것과 동일한
        가드를 그대로 재사용한다.
        """
        try:
            total_observations = int(dna.get("total_observations", 0) or 0)
            planner_influenced = int(dna.get("planner_influenced_observations", 0) or 0)
            independent_observations = total_observations - planner_influenced

            if independent_observations < self.LEARNING_FEEDBACK_MIN_INDEPENDENT_OBSERVATIONS:
                return {
                    "available": False,
                    "independent_observations": independent_observations,
                    "recent_good_run_ratio": None,
                    "total_learning_runs": 0,
                    "reason": (
                        f"독립 관찰 수({independent_observations})가 기준"
                        f"({self.LEARNING_FEEDBACK_MIN_INDEPENDENT_OBSERVATIONS}) 미달이라 참고하지 않음."
                    ),
                }

            learning_statistics = self.learning_interface.get_statistics()
            total_runs = int(learning_statistics.get("total_runs", 0) or 0)
            total_good_runs = int(learning_statistics.get("total_good_runs", 0) or 0)
            good_run_ratio = round(total_good_runs / total_runs, 4) if total_runs else None

            return {
                "available": True,
                "independent_observations": independent_observations,
                "recent_good_run_ratio": good_run_ratio,
                "total_learning_runs": total_runs,
            }
        except Exception as error:
            print(f"Brand DNA Learning Feedback Reference Failed: {error}")
            return {
                "available": False,
                "independent_observations": 0,
                "recent_good_run_ratio": None,
                "total_learning_runs": 0,
                "reason": str(error),
            }

    def _merge_brand_dna_change_into_dashboard(
        self, brand_dna_change: Dict[str, Any], brand_dna_delta: Dict[str, Any]
    ) -> None:
        """
        Phase: Instagram Intelligence. storage/dashboard/daily_learning_report.json은
        Competitor Learning Engine이 이미 소유한 파일이다(hook_top10/cta_top10/
        pattern_top10/layout_top10/new_learning_count 등). 이 메서드는 그 파일을
        불러와 "brand_dna_change"/"brand_dna_delta" 키만 추가/갱신하고 나머지
        키는 그대로 둔다(기존 JSON 구조 유지). Competitor Learning Engine이
        아직 한 번도 실행되지 않아 파일이 없으면, 이 두 키만 담은 최소 파일을
        새로 만든다 - 두 경우 모두 예외를 던지지 않는다.
        """
        try:
            report = self.dashboard_storage.load_dashboard()
            if not isinstance(report, dict):
                report = {}

            report["brand_dna_change"] = brand_dna_change
            report["brand_dna_delta"] = brand_dna_delta
            self.dashboard_storage.save_dashboard(report)
        except Exception as error:
            print(f"Brand DNA Dashboard Merge Failed: {error}")

    def _fallback_result(self, reason: str) -> Dict[str, Any]:
        try:
            brand_profile = self.profile_loader.load()
        except Exception:
            brand_profile = {}

        return {
            "status": "brand_dna_updated",
            "brand_profile": brand_profile,
            "observation": {},
            "dominant_hook_type": "",
            "dominant_cta_type": "",
            "dominant_layout_type": "",
            "dominant_color": "",
            "total_observations": 0,
            "competitor_learning_reference": {
                "available": False,
                "account_profiles": {},
                "account_count": 0,
                "knowledge_database_change": {"new_count": 0, "total_count": 0},
            },
            "brand_dna_change": {"changes": {}, "any_changed": False, "total_observations": 0},
            "brand_dna_delta": {"changed_fields_count": 0, "changed_fields": [], "any_changed": False},
            "learning_feedback_reference": {
                "available": False,
                "independent_observations": 0,
                "recent_good_run_ratio": None,
                "total_learning_runs": 0,
            },
            "fallback_used": True,
            "reason": reason,
            "created_at": datetime.now().isoformat(),
        }
