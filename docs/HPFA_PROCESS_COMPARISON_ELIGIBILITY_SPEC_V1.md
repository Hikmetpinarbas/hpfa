# HPFA Process Comparison Eligibility Specification V1

Status: TARGET SPEC / WIP=1 DESIGN AUTHORITY
Product scope: single-match Postmatch
Parent architecture: `HPFA_MULTI_DIMENSIONAL_FOOTBALL_INTELLIGENCE_ARCHITECTURE_V1.md`
Execution authority: current product frontier + physical ACTIVE_MATCH only
Production release: false

## 1. Purpose

This specification closes the gap between safe visible sequence candidates and defensible process comparison.

The target question is not:

> Which sequences look vaguely similar?

It is:

> Under a declared football question, which observed processes are sufficiently comparable that their branch, variant and visible-consequence differences may be described without leaking the result into the comparison gate?

This is a prerequisite for:

- Process Branch Map
- First Supported Divergence
- successful / failed / deviant variant comparison
- opportunity-normalized visible yield
- comparable counterevidence
- safe match mechanisms

No new parallel engine is authorized by this specification. The preferred implementation path is rehabilitation of current sequence / process producers and their downstream comparison contracts.

## 2. Current product gap

The current product already has safe objects for:

- admitted occurrences
- time layers
- visible action sequence candidates
- analyst episode navigation candidates
- consequence candidates
- partial-order preservation
- dependency-qualified evidence

The current `visible_action_sequence_candidates_lite_v1` producer uses operational boundaries including:

- period change
- restart
- mixed / unknown team layer
- visible team handover candidate
- terminal outcome support
- time gap greater than the current operational threshold

These boundaries are deliberately not possession, process or tactical truth.

The missing bridge is:

```text
VISIBLE SEQUENCE CANDIDATE
→ PROCESS / PHASE CANDIDATE
→ COMPARISON QUESTION
→ COMPARISON ELIGIBILITY
→ COMPARABLE SET
→ COMMON PREFIX / SHARED STRUCTURE
→ BRANCH MAP
→ FIRST SUPPORTED DIVERGENCE
→ VISIBLE CONSEQUENCE PROFILE
→ COUNTEREVIDENCE
→ SAFE FINDING
```

## 3. Research basis — ADAPT_NOT_COPY

### 3.1 Football event-process mining

Kröckel & Bodendorf (2020), *Process Mining of Football Event Data: A Novel Approach for Tactical Insights Into the Game*, Frontiers in Artificial Intelligence, DOI `10.3389/frai.2020.00047`.

Donor value:

- possession / case / trace thinking
- action order
- player participation order
- typical and unusual trace variants
- process and sequence clustering

HPFA adaptation:

- use trace / variant thinking
- do not inherit tactical-truth language
- preserve observation and dependency ceilings

### 3.2 Phase segmentation and spatiotemporal clustering

Decroos, Van Haaren & Davis (2018), *Automatic Discovery of Tactics in Spatio-Temporal Soccer Match Data*, KDD, DOI `10.1145/3219819.3219832`.

Donor value:

- segment event streams into football-relevant phases
- possession switch / interruption as operational segmentation evidence
- reject fixed equal-duration windows as universally meaningful comparison units
- cluster phases using spatiotemporal information
- mine frequent sequential patterns after segmentation

HPFA adaptation:

- operational time gaps remain segmentation evidence, not natural football truth
- fixed windows must not define process identity by themselves
- phase comparison requires declared semantic and spatial context

### 3.3 Context-rich soccer move similarity

Stein, Janetzko, Schreck & Keim (2019), *Tackling Similarity Search for Soccer Match Analysis: Multimodal Distance Measure and Interactive Query Definition*, IEEE Computer Graphics and Applications, DOI `10.1109/MCG.2019.2922224`.

Donor value:

- similarity should combine more than trajectory shape
- player, event, spatial and higher-level context can alter whether two moves are useful comparisons
- analysts benefit from query-conditioned similarity

HPFA adaptation:

- comparison is question-conditioned, not one universal distance score
- only admitted context may enter the gate
- pressure-related dimensions are unavailable without suitable tracking / freeze-frame / video evidence

### 3.4 Situational context in offensive sequences

Sarmento et al. (2018), *Influence of Tactical and Situational Variables on Offensive Sequences During Elite Football Matches*, Journal of Strength and Conditioning Research, DOI `10.1519/JSC.0000000000002147`.

Casal et al. (2019), *Possession in Football: More Than a Quantitative Aspect — A Mixed Method Study*, Frontiers in Psychology, DOI `10.3389/fpsyg.2019.00501`.

Donor value:

- attack type / start condition
- field zone
- match period
- match status
- intention / interaction context when manually observed
- sequence duration and pass count as contextual descriptors

HPFA adaptation:

- start context, field region, period and score-state may condition comparison when admitted
- manually inferred intention must not be recreated from event-only data

### 3.5 Augmented possession phases

Deb et al. (2024), *Creating an augmented possession framework to evaluate phases of play and application in international football*, Journal of Sports Analytics, DOI `10.1177/22150218241290988`.

Donor value:

- one possession may contain multiple analytically meaningful phases
- phase-level consequence can differ from possession-level outcome
- progression, dangerous possession, shot, critical chance and goal are different consequence levels

HPFA adaptation:

- possession candidate and process / phase candidate are distinct scales
- process comparison should not collapse an entire possession into one label

### 3.6 Transparent matching donor

Iacus, King & Porro (2012), *Causal Inference without Balance Checking: Coarsened Exact Matching*, Political Analysis, DOI `10.1093/pan/mpr013`.

Donor value:

- exact matching may be relaxed through declared coarsening
- matching rules can remain interpretable and auditable

HPFA adaptation:

- use the design principle for transparent eligibility strata
- do NOT import a causal-effect claim
- HPFA comparison remains descriptive / diagnostic unless a separate causal design exists

## 4. Core doctrine

### 4.1 Comparability is question-conditioned

There is no universal definition of two processes being "the same enough".

The comparison question determines which dimensions must match and which dimension is allowed to vary.

Examples:

If the question is:

> Did the same process family behave differently between first and second half?

then `period` is a TEST DIMENSION and must not be forced to match.

If the question is:

> Did actor participation differ between productive and non-productive variants?

then actor identity / role may be a TEST DIMENSION and must not be used to force exact matching.

If the question is:

> Did right-channel and central branches differ after the same visible prefix?

then branch direction / spatial route is a TEST DIMENSION and must not be used to define the comparable set before divergence.

### 4.2 Eligibility must be outcome-blind

The target result must not enter admission.

Forbidden as eligibility features when they occur at or after the target divergence:

- shot / no shot
- goal / no goal
- success / failure label being evaluated
- turnover outcome being evaluated
- terminal consequence being evaluated
- post-divergence actor
- post-divergence zone
- post-divergence route
- any model score derived from the downstream result

Outcome semantics may be attached only after the comparable set is frozen.

### 4.3 Similarity != equivalence

A high similarity score does not establish:

- same possession truth
- same process truth
- same tactical intention
- same causal mechanism
- same opponent response

The product should prefer explicit per-dimension eligibility reasons over one opaque similarity number.

### 4.4 Unknown != different

If a required comparison field is unresolved, do not silently classify the cases as different.

Use:

- REVIEW_REQUIRED
- COMPARISON_CONTEXT_UNRESOLVED
- or INELIGIBLE when the missing capability is mandatory for the declared question

## 5. Comparison Question Contract

Every comparison must begin with an explicit contract.

Required fields:

```text
comparison_question_id
football_question
analysis_scale
candidate_universe
anchor_process_family
comparison_target
required_exact_dimensions
required_coarsened_dimensions
allowed_test_dimensions
optional_similarity_dimensions
forbidden_leakage_dimensions
required_observation_capabilities
optional_observation_capabilities
consequence_horizon
minimum_support_rule
minimum_spread_rule
claim_ceiling
```

### 5.1 Example — half-to-half process evolution

```text
football_question:
  Does the same visible progression process family produce different branches across periods?

required_exact_dimensions:
  team
  open_play_vs_restart
  admitted_process_family
  direction_normalization_state

required_coarsened_dimensions:
  process_entry_zone
  process_entry_action_family

allowed_test_dimensions:
  period

forbidden_leakage_dimensions:
  branch_outcome
  shot
  turnover
  post_divergence_actor
  post_divergence_zone
```

### 5.2 Example — actor participation contrast

```text
football_question:
  Within the same process family and pre-divergence context, does actor participation differ across variants?

required_exact_dimensions:
  team
  process_family
  open_play_vs_restart

required_coarsened_dimensions:
  entry_zone
  prefix_action_structure

allowed_test_dimensions:
  actor_identity
  actor_role_candidate

forbidden_leakage_dimensions:
  downstream_outcome
  terminal_result
```

## 6. Feature role taxonomy

Every field available to comparison must be assigned one role for the current question.

### A. IDENTITY / DEPENDENCY GATE

Examples:

- occurrence identity
- surface dependency cluster
- reflection group
- match binding

Purpose:

Prevent duplicate reflections from becoming repeated comparison cases or independent support.

### B. PRE-ENTRY CONTEXT

Observed before the compared process begins.

Examples when admitted:

- team
- period
- score-state
- restart / open-play
- recovery / regain context
- entry cell / zone
- normalized attack direction

### C. SHARED PREFIX / PROCESS STRUCTURE

Observed before divergence.

Examples:

- ordered action-family layers
- partial-order same-time layer
- actor-role candidate sequence when actor is not the test dimension
- zone-transition candidate sequence when space is not the test dimension

### D. TEST DIMENSION

The dimension the comparison is allowed to vary on.

Examples:

- period
- actor participation
- branch direction
- starting zone
- process variant

A TEST DIMENSION must not also be used as a required matching key.

### E. OUTCOME / CONSEQUENCE

Observed after the comparable set is frozen.

Examples:

- continuation
- progression
- reset
- loss
- final-third access
- box access
- shot
- stoppage
- no visible follow-up
- censored / unresolved

### F. UNAVAILABLE / FORBIDDEN

Examples without required evidence:

- true pressure geometry
- true shape
- compactness
- off-ball option count
- coach intention
- tactical plan

These cannot be imputed into eligibility.

## 7. Eligibility gates

The gates are evaluated in order.

### G0 — Product / provenance eligibility

Required:

- same ACTIVE_MATCH binding
- admitted source / surface role
- dependency identity available enough to prevent reflection inflation
- no hard-blocked upstream record

Failure:

`COMPARISON_INELIGIBLE_PROVENANCE`

### G1 — Observation admission eligibility

Required capabilities depend on the question.

Possible requirements:

- actor admitted
- temporal layer admitted
- spatial frame admitted
- attack direction admitted
- consequence state available
- process binding available

Failure of mandatory capability:

`COMPARISON_INELIGIBLE_REQUIRED_CAPABILITY_MISSING`

Optional capability missing:

`COMPARISON_DEGRADED_OPTIONAL_CAPABILITY_MISSING`

### G2 — Scale eligibility

Do not compare different analytical objects as if they were peers.

Examples:

- occurrence vs occurrence
- process vs process
- possession candidate vs possession candidate
- regime candidate vs regime candidate

A process may be nested inside a possession candidate, but that does not make the two scales interchangeable.

Failure:

`COMPARISON_INELIGIBLE_SCALE_MISMATCH`

### G3 — Structural entry eligibility

Require declared shared entry conditions.

Typical NOW candidates:

- same team
- same process family candidate
- same restart/open-play class
- same direction-normalization state
- same or coarsened entry zone
- compatible first action / first relation structure

Question-specific exceptions are permitted only when the differing field is declared a TEST DIMENSION.

### G4 — Prefix / partial-order eligibility

Two candidates may enter the same comparison set only if they share enough supported pre-divergence structure for the declared question.

Rules:

- same timestamp remains unordered
- source-row order must never create a common prefix
- an unordered layer can align with an unordered layer if their admitted member structure is compatible
- if a unique earliest divergence cannot be established because of partial-order ambiguity, comparison may remain eligible but First Supported Divergence becomes UNRESOLVED

### G5 — Context eligibility

Context is query-dependent.

Possible admitted dimensions:

- period
- score-state
- restart/open-play
- entry zone / channel
- process-start type
- opponent identity
- numerical state only if actually available and admitted

Context can be:

- EXACT_MATCH_REQUIRED
- COARSENED_MATCH_REQUIRED
- TEST_DIMENSION
- OPTIONAL_DIAGNOSTIC
- UNAVAILABLE

### G6 — Outcome leakage gate

No feature at or after the evaluated branch / consequence may determine eligibility.

Hard block examples:

- selecting only shot-ending processes and then asking whether a branch leads to shots
- selecting SUCCESS provider outcomes and comparing them with FAILURE provider outcomes where that same provider outcome determines the downstream consequence under study
- matching on a post-divergence actor and then claiming actor participation differs after divergence

Failure:

`COMPARISON_INELIGIBLE_TARGET_LEAKAGE`

### G7 — Opportunity / support eligibility

The denominator is frozen here, before reading outcome.

Record:

- eligible_case_count
- dependency_unique_case_count
- episode_spread
- actor_spread
- context_spread
- censored_count
- unresolved_count

Small support does not automatically make the comparison false. It lowers claim strength and may force REVIEW / LOCAL_FINDING / WEAK_SIGNAL.

## 8. Comparison grades

Do not collapse comparison eligibility to a single confidence percentage.

### STRICT_ELIGIBLE

All required exact dimensions match and mandatory capabilities are admitted.

### COARSENED_ELIGIBLE

Required exact dimensions match and declared coarsened dimensions fall inside explicit bins / adjacent classes.

Examples:

- same canonical third but different exact coordinate
- same functional corridor class after direction admission
- same action family with different provider subtype aliases

### REVIEW_REQUIRED

Potentially useful comparison but one required context or ordering dimension is unresolved.

No automatic branch-strength elevation.

### INELIGIBLE

One or more hard comparison gates fail.

## 9. Coarsening rules — transparent, football-facing

NOW coarsening should be deterministic and inspectable.

Permitted examples:

### Space

Exact coordinate is not required by default.

Prefer admitted football bins:

- canonical grid cell
- third
- central / half-space candidate / wide channel after semantics

Do not use raw x increase as forward progression without direction admission.

### Time

Do not require equal sequence duration.

Duration may be a descriptor or a coarsened context bin when the question requires it.

The current 12-second sequence gap is not a natural process-comparability threshold.

### Actions

Provider subtype aliases may be coarsened into admitted action families when semantic equivalence is established.

### Actors

Actor identity should match only when actor is not the tested dimension.

Possible coarsening to actor role candidate is allowed only if role semantics are admitted.

## 10. Why no universal similarity score NOW

A single weighted distance creates several risks:

- arbitrary weight selection
- hidden compensation: a large spatial mismatch can be cancelled by action similarity
- outcome leakage through derived features
- loss of football interpretability
- unstable behavior in small single-match samples

Therefore NOW should use:

```text
HARD GATES
+ DECLARED COARSENED GATES
+ EXPLICIT TEST DIMENSIONS
+ OPTIONAL DESCRIPTIVE DISTANCES
```

Learned similarity, path signatures, probabilistic representations or metric learning remain LATER until a stable Gold Corpus and validation target exist.

## 11. Comparable Set object

Minimum contract:

```text
comparable_set_id
comparison_question_id
team
analysis_scale
anchor_process_family
eligibility_grade
member_process_candidate_ids
eligible_case_count
unique_dependency_group_count
required_exact_dimensions
required_coarsened_dimensions
allowed_test_dimensions
resolved_context
unresolved_context
prefix_support_summary
partial_order_state
censoring_burden
dependency_burden
episode_spread
actor_spread
context_spread
claim_ceiling
```

A comparable set is not a finding.

## 12. Branch Map contract

Branch Map is produced only after a comparable set is frozen.

Required fields:

```text
branch_map_id
comparable_set_id
shared_prefix_candidate
shared_prefix_support_n
eligible_denominator_n
branch_partition
branch_support_counts
branch_consequence_profiles
no_visible_followup_count
censored_count
unresolved_count
counterexample_refs
claim_ceiling
```

Example:

```text
eligible comparable cases = 9
shared prefix support = 7/9

first branch after shared structure:
RIGHT   4/7
CENTRAL 2/7
RESET   1/7

RIGHT branch visible consequences:
SHOT                    2/4
LOSS                    1/4
NO_VISIBLE_FOLLOWUP     1/4
```

Do not rewrite this as "50% chance of a shot" unless the statistical model and sampling design justify probability language.

## 13. First Supported Divergence

The current anchor-successor locator is not sufficient for true First Supported Divergence.

Target definition:

> Within an admitted comparable set, find the earliest supported non-alignment after the maximal supported shared prefix / partial-order structure.

Required safeguards:

1. Compare only eligible processes.
2. Use pre-divergence admitted structure.
3. Do not impose order inside SAME_TIME_UNORDERED layers.
4. If several earliest divergences are equally compatible because of partial order, return:
   `FIRST_SUPPORTED_DIVERGENCE_UNRESOLVED`.
5. Attach consequence only after divergence location is fixed.
6. Preserve successful / failed / deviant / censored / unresolved variants separately.
7. Do not convert divergence association into causality.

## 14. Counterevidence

Counterevidence must come from the same declared comparison design where possible.

Useful counterevidence classes:

- same prefix + different branch but same visible consequence
- same branch + different visible consequence
- claimed productive branch with visible failure / loss variant
- claimed failed branch with productive visible consequence
- context-reversal case
- actor-reversal case
- period-reversal case
- high censoring / unresolved burden

Absence is not counterevidence.

NO_VISIBLE_FOLLOWUP is not failure.

## 15. Question-specific eligibility examples

### 15.1 Progression route comparison

Question:

> After the same admitted entry context and shared prefix, do right-side and central continuations show different visible consequences?

Match / coarsen:

- same team
- same process family
- same restart/open-play class
- compatible entry zone
- compatible shared prefix

Test:

- branch route

Outcome after set freeze:

- continuation / progression / access / loss / shot / unresolved

### 15.2 Player participation comparison

Question:

> In otherwise comparable process candidates, where does actor participation differ between branch variants?

Match / coarsen:

- team
- process family
- process entry context
- shared action / zone prefix

Test:

- actor identity or actor-role candidate

Do not match exactly on the actor being evaluated.

### 15.3 Match evolution comparison

Question:

> Does a process family change between first and second half?

Match / coarsen:

- team
- process family
- restart/open-play class
- entry context

Test:

- period

Do not exact-match on period.

## 16. Red Team failure modes

The implementation must test at least the following:

1. OUTCOME LEAKAGE
   - target result accidentally enters eligibility.

2. OVERMATCHING
   - matching on the variable the analyst wants to compare.

3. UNDERMATCHING
   - grouping materially different start contexts into one denominator.

4. REFLECTION INFLATION
   - CSV/XML reflections become multiple cases.

5. SAME-TIME FALSE ORDER
   - row order creates a synthetic prefix or divergence.

6. RESTART MIXING
   - restart and open-play processes enter one set without declared justification.

7. DIRECTION ERROR
   - mirrored halves / teams compared using raw x direction without normalization.

8. PERIOD CONFOUNDING
   - period change interpreted as process effect when it should have been conditioned or declared as test dimension.

9. ACTOR LEAKAGE
   - actor identity used both as matching key and claimed differentiator.

10. SAMPLE COLLAPSE
    - strict matching leaves n=1 or dependency-duplicate cases but language remains strong.

11. CENSORING MISCLASSIFICATION
    - NO_VISIBLE_FOLLOWUP becomes failure.

12. OPERATIONAL THRESHOLD REIFICATION
    - 12-second or 20-second navigation / segmentation heuristics are presented as natural football boundaries.

## 17. NOW / LATER / REJECT

### NOW

Implementable from current evidence spine where capabilities are admitted:

- deterministic question-conditioned eligibility
- exact and declared coarsened context matching
- action-family / process-family compatibility
- canonical spatial bins after admission
- restart/open-play conditioning
- period conditioning or period as test dimension
- score-state only if admitted
- partial-order-aware prefix compatibility
- dependency de-duplication
- explicit eligible denominator
- branch partition
- visible consequence profile
- comparable counterexamples
- First Supported Divergence with UNRESOLVED state when necessary

### LATER

Requires stronger corpus / validation / richer observation:

- learned similarity metric
- path-signature similarity
- probabilistic action embeddings
- propensity / weighting models for population-level estimation
- regime-conditioned matching
- adaptive spatial regions
- cross-match stability
- tracking / freeze-frame pressure context

### REJECT without required evidence

Do not claim from comparison alone:

- causality
- tactical intention
- coach decision
- opponent weakness truth
- true pressure geometry
- true team shape
- true off-ball option structure
- dominance

## 18. Minimal engineering path

No parallel engine.

Preferred order:

```text
1. Preserve current visible_action_sequence_candidates producer and its fail-closed locks.
2. Expose boundary evidence explicitly rather than treating operational gap thresholds as process truth.
3. Rehabilitate process / phase binding on top of admitted occurrence and time-layer structure.
4. Add a comparison-question contract.
5. Add deterministic comparison eligibility reasons / grades.
6. Freeze eligible denominators before consequence attachment.
7. Rehabilitate Branch Map to consume only comparable sets.
8. Rehabilitate First Supported Divergence to use maximal supported shared prefix / partial order.
9. Attach visible consequences after divergence.
10. Add counterevidence and analyst video locators.
11. Test on physical ACTIVE_MATCH.
12. Red Team claim language.
```

## 19. Success criterion

This work is successful only when HPFA can produce a sentence of the following form from admitted real-match evidence:

> Within N comparable process opportunities sharing the declared pre-divergence context and supported prefix, the process separated into these visible branches; the branches showed these realized consequence profiles, with these counterexamples, censoring states and unresolved cases.

A stronger football-facing target is:

> In this match, the same visible mechanism recurred under comparable conditions; successful and failed variants separated at an admitted divergence point, and the observed consequence difference is visible here.

Still forbidden without additional evidence:

> This branch caused the outcome.

> The coach planned this mechanism.

> The opponent could not defend it because of a specific tactical weakness.

## 20. Evidence-spine value

Real gap closed:

> Safe occurrence / sequence candidates currently exist, but the product lacks a question-conditioned, outcome-blind gate that determines when process candidates are truly comparable before branch and consequence analysis.

New defensible football knowledge enabled:

> The analyst can move from "these actions look similar" to "these opportunities were comparable for this declared football question; they shared this supported structure, diverged here, and produced these different visible outcomes."

That is the required bridge from reconstruction to professional Postmatch intelligence.
