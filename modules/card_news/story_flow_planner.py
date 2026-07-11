from typing import Any, Dict, List, Optional

CANONICAL_ROLE_ORDER = ["hook", "problem", "solution", "cta"]


class StoryFlowPlanner:
    """
    CardNews Intelligence (Phase M7 - 실제 사용 연결) - Story Flow.

    이미 존재하는 4개 슬라이드(hook/problem/solution/cta - Content Output
    Contract, Sprint 14-2가 이미 이 순서를 보장한다)에 실제 서사 role을
    부여한다. 슬라이드 수(4)보다 서사 role 후보 수가 많으면 억지로 채우지
    않고, 실제로 사용 가능한 신호(Evidence/Social Proof/Debate 결과)에 따라
    가장 적합한 role만 실제 슬라이드에 매핑한다.

    새로운 슬라이드를 만들거나 슬라이드 개수/실제 role(hook/problem/solution/
    cta)을 바꾸지 않는다 - 이미 만들어진 4장에 서사적 라벨을 추가로 붙이는
    순수 조회/라벨링 계층이다.
    """

    # 슬라이드 1장(hook)에는 항상 "cover"만 붙는다 - 다른 후보가 없다.
    HOOK_ROLE_CANDIDATES = ["cover"]
    # 슬라이드 2장(problem)에는 항상 "problem"만 붙는다 - context는 problem과
    # 동시에 쓸 슬라이드가 없어 항상 skipped_roles로 남는다(정직하게 기록).
    PROBLEM_ROLE_CANDIDATES = ["problem"]
    # 슬라이드 3장(solution)은 evidence 자산이 실제로 있으면 "evidence",
    # 없으면 "explanation".
    SOLUTION_ROLE_IF_EVIDENCE = "evidence"
    SOLUTION_ROLE_DEFAULT = "explanation"
    # 슬라이드 4장(cta)은 debate 질문이 실제로 적용되면 "debate_cta",
    # social proof가 실제로 있으면 "social_proof", 둘 다 없으면 "conclusion".
    CTA_ROLE_IF_DEBATE = "debate_cta"
    CTA_ROLE_IF_SOCIAL_PROOF = "social_proof"
    CTA_ROLE_DEFAULT = "conclusion"

    ALL_NARRATIVE_ROLES = [
        "cover", "context", "problem", "evidence", "explanation",
        "social_proof", "counterpoint", "conclusion", "debate_cta",
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def plan(
        self,
        slides: Optional[List[Dict[str, Any]]],
        evidence_available: bool = False,
        social_proof_available: bool = False,
        debate_will_apply: bool = False,
    ) -> Dict[str, Any]:
        try:
            return self._plan(
                slides or [],
                bool(evidence_available),
                bool(social_proof_available),
                bool(debate_will_apply),
            )
        except Exception as error:
            return self._fallback_result(reason=f"story_flow_exception: {error}")

    def _plan(
        self,
        slides: List[Dict[str, Any]],
        evidence_available: bool,
        social_proof_available: bool,
        debate_will_apply: bool,
    ) -> Dict[str, Any]:
        actual_role_order = [str(slide.get("role", "")) for slide in slides if isinstance(slide, dict)]
        flow_matched = actual_role_order[: len(CANONICAL_ROLE_ORDER)] == CANONICAL_ROLE_ORDER

        applied_roles: List[Dict[str, Any]] = []
        skipped_roles: List[str] = []

        by_canonical_role = {
            str(slide.get("role", "")): slide
            for slide in slides
            if isinstance(slide, dict)
        }

        # hook -> cover
        if "hook" in by_canonical_role:
            applied_roles.append({"page": by_canonical_role["hook"].get("page"), "role": "hook", "narrative_role": "cover"})
        else:
            skipped_roles.append("cover")

        # problem -> problem (context는 슬라이드가 없어 항상 skip으로 남는다)
        skipped_roles.append("context")
        if "problem" in by_canonical_role:
            applied_roles.append({"page": by_canonical_role["problem"].get("page"), "role": "problem", "narrative_role": "problem"})
        else:
            skipped_roles.append("problem")

        # solution -> evidence(있으면) 또는 explanation
        if "solution" in by_canonical_role:
            solution_narrative = self.SOLUTION_ROLE_IF_EVIDENCE if evidence_available else self.SOLUTION_ROLE_DEFAULT
            applied_roles.append({"page": by_canonical_role["solution"].get("page"), "role": "solution", "narrative_role": solution_narrative})
            skipped_roles.append(self.SOLUTION_ROLE_DEFAULT if evidence_available else self.SOLUTION_ROLE_IF_EVIDENCE)
        else:
            skipped_roles.append("evidence")
            skipped_roles.append("explanation")

        # cta -> debate_cta(적용 예정) > social_proof(가능) > conclusion
        if "cta" in by_canonical_role:
            if debate_will_apply:
                cta_narrative = self.CTA_ROLE_IF_DEBATE
                skipped_roles.append("social_proof")
                skipped_roles.append("conclusion")
            elif social_proof_available:
                cta_narrative = self.CTA_ROLE_IF_SOCIAL_PROOF
                skipped_roles.append("debate_cta")
                skipped_roles.append("conclusion")
            else:
                cta_narrative = self.CTA_ROLE_DEFAULT
                skipped_roles.append("debate_cta")
                skipped_roles.append("social_proof")

            applied_roles.append({"page": by_canonical_role["cta"].get("page"), "role": "cta", "narrative_role": cta_narrative})
        else:
            skipped_roles.extend(["debate_cta", "social_proof", "conclusion"])

        # counterpoint는 실제로 반대 의견 슬라이드를 배치할 여분 슬라이드가
        # 없으므로 이번 4-슬라이드 구조에서는 항상 skip으로 남는다(정직하게 기록).
        skipped_roles.append("counterpoint")

        planned_roles = [item["narrative_role"] for item in applied_roles] + list(dict.fromkeys(skipped_roles))
        continuity_score = round(
            (0.5 if flow_matched else 0.0) + (0.5 * (len(applied_roles) / 4 if slides else 0.0)), 4
        )

        return {
            "expected_role_order": list(CANONICAL_ROLE_ORDER),
            "actual_role_order": actual_role_order,
            "flow_matched": flow_matched,
            "planned_roles": planned_roles,
            "applied_roles": applied_roles,
            "skipped_roles": list(dict.fromkeys(skipped_roles)),
            "continuity_score": continuity_score,
            "continuity_reason": (
                f"실제 슬라이드 {len(applied_roles)}/4장에 서사 role을 적용함. "
                f"role 순서 일치 여부: {flow_matched}."
            ),
        }

    def _fallback_result(self, reason: str) -> Dict[str, Any]:
        return {
            "expected_role_order": list(CANONICAL_ROLE_ORDER),
            "actual_role_order": [],
            "flow_matched": False,
            "planned_roles": [],
            "applied_roles": [],
            "skipped_roles": list(self.ALL_NARRATIVE_ROLES),
            "continuity_score": 0.0,
            "continuity_reason": reason,
        }
