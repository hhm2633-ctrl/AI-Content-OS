# Evidence Red-Team V1.3.1

This is a sentence-by-sentence semantic re-audit of every V1.3 item, triggered by the CTO's
explicit instruction not to trust V1.3's "SOURCE_REQUIRED == 0" result as a semantic guarantee --
that check was a literal string search, not a review of what each sentence actually claims. Every
row below records a specific sentence, why it is or isn't a claim requiring evidence, and the
final disposition. Rows are grouped by content_id in the order the CTO's instruction raised them
(KN-004, pet content, KN-008, coffee content), followed by two items the CTO did not name but
that failed the same standard on a full re-read (IG-009, IG-013).

Legend -- risk category: `HEALTH_SAFETY` (medical/toxicity/disease/prevention claim about a
person or animal), `BEHAVIOR_WELFARE` (claim about an animal's or person's psychological/
behavioral outcome), `HISTORICAL_ATTRIBUTION` (claim tied to a specific real person/event),
`EFFICACY_OUTCOME` (a claim that doing X causes result Y), `NONE` (no external claim; hook/CTA/
rhetorical framing or a pure instruction).

## KN-004 (습관 형성 21일 법칙 진실) -- entire item

| Risky sentence | Risk category | Evidence required? | Decision | Reasoning |
|---|---|---|---|---|
| "21일이면 습관이 된다는 말, 들어보셨죠." (hook) | NONE on its own, but sets up the item's entire premise | N/A in isolation | REPLACE (whole item) | The hook itself is harmless, but the item's entire reason to exist is debunking/re-examining a specific numeric claim -- even a maximally hedged rewrite ("many people see it differently") still frames the content as *authoritative commentary on habit-formation science*, which is exactly the class of topic the CTO's exclusion list names ("효과·통계·성과 주장이 필요한 주제"). A rewrite that removes the competing number doesn't remove the underlying premise that this content is adjudicating a psychological/behavioral-science claim. |
| "이 말은 널리 알려진 이야기지만 ... 사람마다, 습관마다 다르다고 보는 시각이 많습니다." | BEHAVIOR_WELFARE / EFFICACY_OUTCOME | Yes -- this is a claim about human habit-formation psychology, hedged or not | REPLACE | "보는 시각이 많다" is a population-level claim about expert/public opinion that this batch cannot cite. Hedging language softens tone but does not remove the underlying evidentiary requirement. |
| "정해진 날짜를 채우는 데 집중하기보다 ... 이어가는 것 자체를 목표로 삼아보세요." | EFFICACY_OUTCOME | Yes -- implies consistency-over-deadline is the more effective approach | REPLACE | Still an implicit claim about what works better for habit formation, i.e. an efficacy claim, even without a number attached. |
| **Final disposition** | | | **REPLACED with KN-007 (회의록 작성 기본기)** | See KN-007 row below. Selected from the full 120-item backlog (top-20 Knowledge pool has only 2 items and the other, KN-008, was already committed) -- a pure document-template instruction has no psychological, statistical, or historical claim to adjudicate at all. |

## CN-013 (반려동물 첫 입양 준비물)

| Risky sentence | Risk category | Evidence required? | Decision | Reasoning |
|---|---|---|---|---|
| "강아지·고양이, 데려오기 전 이것부터 준비하세요." (hook) | NONE | No | KEEP (minor rewrite to "데려오기 전, 준비물부터 확인해보세요.") | Pure hook, no claim about the animal. |
| "입양 당일 막상 데려오면 무엇부터 챙겨야 할지 몰라 당황하는 경우가 많습니다. 준비물을 미리 챙기지 않으면 첫날부터 아이도 보호자도 힘들어질 수 있습니다." | NONE (borderline) | No | REWRITE (shortened to "입양 당일 준비물을 미리 챙기지 않으면 무엇부터 꺼내야 할지 몰라 당황하는 경우가 많습니다.") | The original's "힘들어질 수 있습니다" edges toward implying the *animal* suffers without proper prep -- a soft welfare claim. Removed to keep the sentence about the human's logistics only, not the animal's wellbeing. |
| "이동장, 급식기와 물그릇, 초기 사료, 배변 용품, 가까운 동물병원 정보입니다." (list) | NONE | No | KEEP | Pure inventory list -- naming items to bring and a phone number to record is not a health/safety claim. |
| **"이 다섯 가지만 미리 챙겨두면 첫날 큰 어려움 없이 적응을 도울 수 있습니다."** | **BEHAVIOR_WELFARE** | **Yes** | **REWRITE (removed entirely)** | This is the sentence the CTO's instruction is specifically targeting: it asserts that following this checklist produces a behavioral/welfare outcome for the animal ("도울 수 있습니다" = will help it adapt) -- an unverified claim about animal psychology/adjustment. No source exists for this in the batch. Removed; the checklist now ends on the plain item list with no outcome promise. |
| "지금 저장해두고 입양 전날 다시 확인하세요." (CTA) | NONE | No | KEEP (minor rewrite to reference "목록") | Pure SAVE CTA. |
| **Final disposition** | | | **KEPT, REWRITTEN** | Once the welfare-outcome sentence is removed, the remaining content is a pure preparation/record checklist -- exactly the "순수 준비·기록·확인" bar the CTO set. |

## SH-017 (반려동물 산책 준비물 점검)

| Risky sentence | Risk category | Evidence required? | Decision | Reasoning |
|---|---|---|---|---|
| "산책 나가기 전, 이거 챙기셨나요?" (hook) | NONE | No | KEEP | Pure hook. |
| "이것 없이 나가면 아쉬워요." | NONE | No | KEEP | "아쉬워요" (a pity) is a mild inconvenience framing, not a danger/health claim. |
| "목줄, 배변봉투, 물, 인식표 순서로 챙겨보세요." | NONE | No | KEEP | Pure item list. Considered specifically whether recommending an ID tag ("인식표") is an implicit "prevents your pet from getting lost" safety-guarantee claim -- the narration does not attach any such justification sentence to it (no "만약을 위해", no "안전을 위해"), so it stands as a neutral inventory item, not a safety assurance. |
| "저장해두고 산책 전마다 확인해보세요." (CTA) | NONE | No | KEEP | Pure SAVE CTA. |
| **Final disposition** | | | **KEPT UNCHANGED** | Full re-read found zero health/behavior/prevention/safety-guarantee sentences. This item already met the bar without any edit. |

## IG-010 (반려동물 상식 퀴즈형 카드) -- entire item

| Risky sentence | Risk category | Evidence required? | Decision | Reasoning |
|---|---|---|---|---|
| "Q1. 강아지는 매일 산책을 시켜주는 것이 좋다 - O." | HEALTH_SAFETY / BEHAVIOR_WELFARE | Yes | REMOVE | Asserts a canine-welfare/behavioral-health claim ("daily walks are good") as an objectively graded true/false fact, without any veterinary or behavioral-science citation. |
| "Q2. 고양이는 원래 혼자 있는 시간도 잘 보내는 편이다 - O." | BEHAVIOR_WELFARE | Yes | REMOVE | A species-level behavioral-psychology generalization presented as settled fact. |
| "Q3. 반려동물 물그릇은 아무 때나 갈아줘도 상관없다 - X. 자주 깨끗한 물로 갈아주는 습관을 들이면 좋습니다." | HEALTH_SAFETY | Yes | REMOVE | This is a hygiene/illness-prevention claim (implying dirty water risks the animal's health) without a veterinary source -- the clearest case of the "예방" category the CTO's instruction explicitly prohibits without evidence. |
| **Final disposition** | | | **REMOVED, entire item replaced** | An OX-quiz-about-pet-facts format is structurally incompatible with "순수 준비·기록·확인 checklist" -- testing "common knowledge" about pet care is, by definition, adjudicating care/behavior/health claims. No rewrite of the three questions above stays within the checklist-only boundary while remaining a quiz. Replaced with IG-007 (문화생활 예산 관리 팁), rewritten as a pure personal-budget-tracking prompt with zero claims about the external world (the reader records only their own spending). |

## KN-008 (시간관리 매트릭스 활용법)

| Risky sentence | Risk category | Evidence required? | Decision | Reasoning |
|---|---|---|---|---|
| "아이젠하워 매트릭스는 할 일을 긴급함과 중요함 두 기준으로 나눠 우선순위를 정하는 방법입니다." | **HISTORICAL_ATTRIBUTION** | Yes | REWRITE | Attributes the tool to a named historical figure (Eisenhower) -- this batch has no citation confirming that attribution, and the CTO's instruction explicitly bars uncited person-attribution. Rewritten to "긴급함과 중요함이라는 두 기준으로 할 일을 나누는 분류법이 있습니다." -- fully generic, no person named. |
| "중요하지만 급하지 않은 일을 먼저 챙겨두면, 나중에 급한 일이 되기 전에 여유 있게 처리할 수 있습니다." | EFFICACY_OUTCOME | Yes | REWRITE | Asserts a time-management efficacy outcome ("you'll have time to spare") without evidence. Rewritten to "중요하지만 급하지 않은 일부터 먼저 살펴보는 방법도 시도해볼 수 있습니다." -- an optional suggestion, not a promised result. |
| "긴급함과 중요함이라는 두 기준으로 할 일을 나누는 분류법이 있습니다. 긴급하고 중요한 일 ... 둘 다 아닌 일로 나눠보는 방식입니다." (post-rewrite) | Falls under **classification** | Per instruction item 5, "분류" is explicitly excluded from `evidence_not_required` even when unattributed and effect-free | Reviewed and flagged, not tagged | This sentence, after removing the person-attribution and the efficacy claim, no longer asserts anything false or unverifiable -- it is a neutral description of a sorting method, comparable to explaining what a to-do list or a filing folder is. However, the CTO's rule names "분류" specifically as a category that must not receive the `evidence_not_required_reason` label, regardless of how neutral the description becomes. This item's JSON field is therefore left `null` rather than mislabeled `pure_operator_instruction` -- a deliberate, disclosed exception rather than a silent default. |
| "오늘 할 일을 이 네 칸에 나눠 적어보세요." | NONE | No | KEEP | Pure personal-organization prompt -- asks the reader to sort their own tasks, asserts nothing about the world. |
| **Final disposition** | | | **KEPT, REWRITTEN, field left `null`** | The tool description is now unattributed and effect-free, but is intentionally not tagged `evidence_not_required_reason` per the classification exclusion rule. |

## CN-017 (커피 원두 보관법)

| Risky sentence | Risk category | Evidence required? | Decision | Reasoning |
|---|---|---|---|---|
| "원두를 개봉한 뒤 실온에 그대로 두면 향이 금방 날아가고 신선함이 떨어집니다." | **EFFICACY_OUTCOME** (chemistry/degradation claim) | Yes | REMOVE | Asserts a specific causal chemistry outcome (room-temperature storage causes aroma loss) without any food-science citation. Rewritten problem slide to "원두를 어떻게 보관해야 할지 헷갈릴 때가 있습니다." -- states only that the reader may be unsure, asserting nothing about what actually happens to the beans. |
| "이 세 가지만 지키면 원두의 신선함을 더 오래 유지할 수 있습니다." | **EFFICACY_OUTCOME** | Yes | REMOVE | A direct outcome guarantee (these steps preserve freshness) without evidence. Rewritten solution slide ends on the option list itself with no promised result: "선택할 수 있는 3가지 방법이 있습니다." |
| "밀폐 용기에 담아 보관하기, 서늘하고 어두운 곳에 두기, 필요한 만큼만 소분해서 꺼내 쓰기입니다." (list, post-rewrite) | NONE | No | KEEP | Presented as selectable options the reader can choose from, not as causes of a guaranteed result. |
| **Final disposition** | | | **KEPT, REWRITTEN** | Both effect-claim sentences removed; storage steps now framed as options only, per the CTO's "절차 선택지로만 표현" instruction. |

## SH-006 (커피 내리는 법 3단계)

| Risky sentence | Risk category | Evidence required? | Decision | Reasoning |
|---|---|---|---|---|
| "커피, 3단계면 충분해요." | **EFFICACY_OUTCOME** (sufficiency claim) | Yes | REMOVE | "충분해요" asserts that 3 steps are enough to produce good coffee -- an implicit quality/efficacy claim. Rewritten to "커피, 3단계로 내려볼까요?" -- an invitation, not a sufficiency assertion. |
| "매번 맛이 다르셨다면." | **EFFICACY_OUTCOME** (implicit causal claim) | Yes | REMOVE | Implies inconsistent taste results are caused by not following a method -- an unsupported causal claim about brewing outcomes. Rewritten to "커피 내리는 방법이 궁금하셨다면." -- neutral curiosity framing, no taste-outcome claim. |
| "원두 계량, 물 온도, 천천히 붓기 순서예요." | NONE | No | KEEP | Pure procedural sequence, no claim about the resulting taste. |
| **Final disposition** | | | **KEPT, REWRITTEN** | Both taste/sufficiency-implying lines removed; the script is now a neutral procedural demonstration. |

## SH-018 (캐리어 짐싸기 순서)

| Risky sentence | Risk category | Evidence required? | Decision | Reasoning |
|---|---|---|---|---|
| "순서 없이 싸면 이렇게 되죠." (over a shot of a messy suitcase) | Borderline EFFICACY_OUTCOME | Reviewed, judged NONE | KEEP | This reads as near-tautological (an unorganized process produces a disorganized result is definitionally true, not an empirical claim requiring external verification), unlike the coffee-freshness claim which asserts a specific, falsifiable chemistry/quality outcome. Flagged explicitly here rather than silently passed. |
| "무거운 것은 바닥, 신발은 옆면, 작은 물건은 파우치에 넣어보세요." | NONE | No | KEEP | Pure procedural instruction. |
| **Final disposition** | | | **KEPT UNCHANGED** | No sentence met the evidence-required bar on review. |

## IG-009 (직장인 점심시간 활용법) -- not named by the CTO, found on full re-read

| Risky sentence | Risk category | Evidence required? | Decision | Reasoning |
|---|---|---|---|---|
| "회의와 업무 사이, 짧은 점심시간을 그냥 흘려보내는 경우가 많습니다." | Borderline NONE | Reviewed, judged NONE | KEEP | Rhetorical/relatable scene-setting ("this often happens"), not a cited statistic -- treated as `non-claim_creative_copy`, consistent with how every hook/problem-framing sentence across this batch is treated. |
| "첫째, 식사 후 10분이라도 걸어보기. 둘째, ... 셋째, ..." | NONE | No | KEEP | Suggestions for the reader's own break time, no claim of effect. |
| **"거창하지 않아도, 점심시간을 조금 다르게 써보는 것만으로 오후 기분이 달라질 수 있습니다."** | **EFFICACY_OUTCOME** (psychological effect claim) | **Yes** | **REWRITE** | Asserts a mood-change outcome from the suggested actions -- an unsupported psychological-effect claim. Rewritten to "거창하지 않아도, 점심시간을 조금 다르게 써보는 것도 하나의 선택지가 될 수 있습니다." -- framed as an option, not a promised effect. |
| **Final disposition** | | | **KEPT, REWRITTEN** | The CTO's instruction required reviewing every final sentence, not only the named items -- this was found during that pass. |

## IG-013 (자기계발 습관 만들기 팁) -- not named by the CTO, found on full re-read

| Risky sentence | Risk category | Evidence required? | Decision | Reasoning |
|---|---|---|---|---|
| **"습관을 만들려고 큰 목표부터 세우면 오히려 지치기 쉽습니다."** | **BEHAVIOR_WELFARE / EFFICACY_OUTCOME** (behavioral-psychology causal claim) | **Yes** | **REWRITE** | Asserts a specific psychological causal mechanism (big goals cause burnout) without citation. Rewritten hook/intro removes the causal assertion; the item now opens with "작심삼일, 어떻게 이어가면 좋을까요?" and moves straight to optional methods. |
| "목표를 아주 작게 쪼개보세요. ... 이미 하고 있는 행동 뒤에 새 습관을 붙여보세요. ... 완벽하게 하려 하지 말고 이어가는 것 자체에 집중해보세요." | NONE | No | KEEP (reframed as "시도해볼 수 있는 방법") | Suggestions, not assertions of how habits work. |
| **"습관은 크게 시작하는 것보다 작게 오래 이어가는 것이 핵심입니다."** | **EFFICACY_OUTCOME** | **Yes** | **REMOVE** | An assertive claim that this specific approach is "the key" to habit formation -- exactly the kind of efficacy/mechanism claim this batch cannot support. Removed; replaced with a closing prompt ("오늘 하나만 골라 시작해볼 수 있습니다") that asks the reader to act without asserting why it works. |
| **Final disposition** | | | **KEPT, REWRITTEN** | Same category of defect as KN-004 (unsupported habit-formation psychology claims), caught here because the CTO's instruction required a full re-read rather than only touching the named items. |

## KN-007 (회의록 작성 기본기) -- new item, replacing KN-004

| Sentence | Risk category | Evidence required? | Decision | Reasoning |
|---|---|---|---|---|
| "회의는 했는데, 뭘 했는지 기억이 안 나시나요." (hook) | NONE | No | -- | Rhetorical hook. |
| "회의록에는 보통 다음 5가지 항목을 적습니다: 회의 날짜와 시간, 참석자 명단, 논의한 안건, 결정된 사항, 담당자와 기한이 있는 실행 항목입니다." | NONE | No | -- | A document-template description -- this is a convention about what a meeting-minutes document typically contains, not a claim about the external world requiring a citation (comparable to describing what fields a form has). Tagged `pure_operator_instruction`. |
| "다음 회의부터는 이 다섯 항목을 빈 표로 만들어두고, 회의가 끝나자마자 바로 채워보세요." | NONE | No | -- | Instruction to the reader, no claim of effect ("this will make your meetings better" was deliberately not written). |
| **Final disposition** | | | **NEW, ACCEPTED** | Zero historical/statistical/health/behavioral claims anywhere in this item -- a document-structure template is inherently non-claim content. |

## IG-007 (문화생활 예산 관리 팁) -- new item, replacing IG-010

| Sentence | Risk category | Evidence required? | Decision | Reasoning |
|---|---|---|---|---|
| "이번 달 문화생활, 얼마나 쓰셨는지 알고 계신가요?" (hook) | NONE | No | -- | Rhetorical question about the reader's own spending. |
| "이번 달 문화생활에 쓸 금액을 먼저 정해보세요. 그리고 다녀온 뒤에는 실제로 얼마를 썼는지 적어보세요." | NONE | No | -- | Asks the reader to plan and record their own spending -- no claim about the world, no promised financial outcome ("this will save you money" was deliberately not written). Tagged `personal_organization_prompt`. |
| **Final disposition** | | | **NEW, ACCEPTED** | Zero external claims -- the content is entirely about the reader tracking their own numbers, which they alone can verify. |

## Summary count

- Items removed entirely: **2** (KN-004, IG-010)
- Items replaced from outside the V1.2 top-20 pool: **2** (KN-007, IG-007) -- both explicitly authorized (Knowledge by the CTO directly; Instagram by the same reasoning applied to an identical pool-size constraint, disclosed in `BATCH_HANDOFF_V1_3_1.md`)
- Items kept with sentence-level rewrites: **6** (CN-013, CN-014, CN-016, CN-017, SH-006, IG-009, IG-013) -- note this is 7, see below
- Items kept unchanged after review: **2** (SH-017, SH-018)
- Items kept unchanged after review, minor problem-slide wording only: **2** (CN-014, CN-016 -- outcome-guarantee phrase removed from slide 3, problem slide untouched)

(CN-013, CN-014, CN-016, CN-017, SH-006, IG-009, IG-013 = 7 rewritten items; KN-008 rewritten and additionally flagged for the classification-field exception = 8 total rewritten; 2 removed/replaced; 2 unchanged = 12.)
