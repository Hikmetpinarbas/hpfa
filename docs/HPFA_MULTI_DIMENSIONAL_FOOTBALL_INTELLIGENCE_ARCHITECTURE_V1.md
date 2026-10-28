# HPFA Multi-Dimensional Football Intelligence Architecture V1

Status: TARGET ARCHITECTURE / WIP=1 DESIGN AUTHORITY
Product scope: single-match Postmatch
Execution authority: current product frontier + physical ACTIVE_MATCH only
Production release: false

## 1. Purpose

HPFA must not be organized as one monolithic analysis engine or as a collection of disconnected metric modules.

The target product is a multi-dimensional football-intelligence network in which multiple specialist analytical lenses inspect the same admitted football universe from different axes, produce evidence-qualified local findings, and contribute those findings to a cross-mechanism synthesis that reconstructs the match as a whole.

The guiding metaphor is:

> Each specialist carries water in its own bucket. The match is understood only when those contributions are coordinated without double-counting the same evidence.

The objective is not more metrics. The objective is more defensible football meaning.

Canonical product chain:

RAW DATA
→ ZFGV COMMON EVIDENCE SPINE
→ DIMENSIONAL FOOTBALL FEATURE FABRIC
→ SPECIALIST FOOTBALL ANALYZERS
→ MICRO / MESO / MACRO FINDINGS
→ PUZZLE_FINDINGS
→ CROSS-MECHANISM EVIDENCE GRAPH
→ MECHANISM_CANDIDATES
→ MATCH_MECHANISMS
→ MATCH_STORY
→ FINAL_POSTMATCH_REPORT

## 2. Non-negotiable architectural separations

The following are different objects and must never be conflated:

- technical producer
- observation capability
- analytical axis
- specialist football analyzer
- puzzle finding
- mechanism candidate
- match mechanism
- final report statement

Likewise:

- analytical diversity != evidence independence
- puzzle diversity != independent support
- recurrence != causality
- provider outcome != tactical success
- coordinate != tracking
- network structure != tactical intention
- pattern candidate != tactical pattern truth
- model output != fact
- LLM text != evidence

A single admitted occurrence may legitimately feed multiple specialist analyzers. This does not create multiple independent evidence votes.

## 3. Common Evidence Spine — shared factory

The common factory reconstructs trustworthy football objects. It does not interpret the match.

SOURCE
→ SURFACE
→ OBSERVATION
→ SEMANTICS
→ IDENTITY / DEPENDENCY
→ TIME / SPACE ADMISSION
→ RELATION
→ EPISODE / PROCESS
→ FEATURE

Observation families remain:

- ACTION / EVENT
- ENTITY / ACTOR
- TEMPORAL
- SPATIAL
- OUTCOME / QUALIFIER
- RELATIONAL
- PROCESS / PARTICIPATION
- AGGREGATE / TABULAR
- EXTERNAL CONTEXT
- TRACKING / VIDEO only when actually available
- HPFA-DERIVED INTELLIGENCE

The Evidence Spine supplies common identifiers, provenance, dependency state, temporal admission, spatial admission, uncertainty and claim ceilings to every downstream analytical lens.

## 4. Football Analysis Lattice — axes, not a pyramid

Football is not represented by one hierarchy. The same occurrence can be projected simultaneously onto several analytical axes.

### 4.1 ACTION axis

Questions:
- What happened?
- What action family was visible?
- What was the admitted outcome semantic?
- What preceded and followed the action?

Examples:
- pass
- cross
- shot
- carry
- dribble
- duel
- recovery
- interception
- restart

### 4.2 TIME axis

Questions:
- When did it happen?
- Which temporal window / episode / regime contained it?
- How did the same mechanism change over time?

Resolution:
instant
→ local window
→ sequence
→ episode
→ process interval
→ match period
→ game-state regime when admitted
→ whole match

Same timestamp remains unordered unless ordering is admitted.

### 4.3 SPACE axis

Questions:
- Where did it start and end?
- Which cell / zone / channel / corridor was involved?
- Did the action produce direction-safe progression?
- Which areas generated or absorbed consequence?

Coordinate availability alone does not authorize tracking claims.

### 4.4 ACTOR axis

Questions:
- Who participated?
- At which process node?
- Was the actor initiating, progressing, connecting or terminating the process?
- Did participation profiles differ between comparable variants?

Actor association never becomes causal attribution by itself.

### 4.5 RELATION axis

Questions:
- Which actor-to-actor, action-to-action, zone-to-zone and process-to-consequence relations are supported?
- Which relations repeat?
- Which relations are context-dependent?

### 4.6 PROCESS axis

Questions:
- Which local actions form a comparable process?
- Which process families recur?
- Which variants are successful, failed, deviant, censored or unresolved?
- Where is the first supported divergence?

### 4.7 OUTCOME / CONSEQUENCE axis

Questions:
- What became visible after the action or process?
- continuation?
- handover?
- recovery?
- progression?
- final-third access?
- box access?
- shot?
- stoppage?
- censored or unresolved?

No-visible-followup is an observation state, not failure.

### 4.8 CONTEXT axis

Questions:
- Which admitted context conditions the observation?
- team
- period
- score-state when admitted
- restart/open-play
- process family
- spatial context
- opponent context

Unknown context != different context.

## 5. Multi-resolution analysis

Every specialist analyzer must declare the scale at which it operates.

### MICRO

Single occurrence, actor, cell, dyad or immediate consequence.

### MESO

Motif, triad, subgroup, sequence, episode, route or local interaction structure.

### MACRO

Team state, recurring process family, match regime, match mechanism and match story.

Cross-scale lineage must be preserved:

ACTION
→ PAIR / DYAD
→ MOTIF / TRIAD
→ LOCAL SUBGROUP
→ SEQUENCE
→ EPISODE
→ PROCESS
→ TEAM STATE
→ MATCH MECHANISM
→ MATCH STORY

A second scale axis is also required:

INDIVIDUAL
→ PAIR / GROUP
→ ZONE
→ UNIT
→ TEAM

Specialist outputs should identify both scale axes where applicable.

## 6. Specialist Football Analyzers

These are analytically distinct lenses, not automatically evidence-independent engines. They must reuse the common Evidence Spine and may share producers.

Initial specialist families:

### 6.1 Pass Intelligence

Examines:
- pass family
- origin / destination
- admitted direction
- outcome semantic
- zone transition
- actors
- relation edges
- process position
- visible consequence
- success / failure / deviant variants
- opportunity-normalized use

### 6.2 Cross Intelligence

Examines:
- source cell / channel
- target region
- actor relation
- preceding access route
- continuation / turnover / shot consequence
- successful / failed variants

### 6.3 Shot & Finishing Intelligence

Examines:
- shot occurrence
- shot source region
- preceding actions
- creation chain
- terminal consequence
- comparable non-shot / failed-chain variants

Model-derived xG or other valuations remain MODEL OUTPUT, never observation truth.

### 6.4 Carry / Dribble Intelligence

Examines:
- origin / destination
- progression candidate
- zone transition
- continuation
- turnover
- downstream access / shot relation

### 6.5 Duel / Recovery Intelligence

Examines:
- visible contest / recovery occurrence
- local process context
- team continuation
- opponent handover
- subsequent transition

### 6.6 Spatial Cell Intelligence

Examines football behavior inside pitch cells and transitions between them.

Cells are not only heatmap bins. For each admitted cell, the analyzer may track:
- action mix
- actor mix
- entries
- exits
- success / failure
- continuation
- turnover
- next-cell transition
- progression candidate
- final-third / box / shot consequence
- process family
- period / game-state conditioning

### 6.7 Passing Network Intelligence

Must distinguish:

PAIR RELATION
X → Y

MOTIF
X → Y → Z
X → Y → X
X → Y → Z → X

PROCESS ROLE
initiator / connector / progressor / terminal participant candidate

Static full-match network summaries are insufficient. Where temporal support exists, network states must be evaluated in windows / episodes / regimes.

### 6.8 Combination / Motif Intelligence

Examines recurring relational structures among small groups.

A repeated motif is not automatically a tactical pattern.

### 6.9 Sequence / Pattern Intelligence

Examines recurring action grammar, partial-order structures and process families.

Pattern candidate requires more than recurrence.

### 6.10 Progression & Access Intelligence

Examines:
- build-up access
- midfield access
- final-third access
- box access
- route survival
- blocked / working route candidates

Raw x increase != forward progression without direction admission.

### 6.11 Chance Creation Chain Intelligence

Examines the sequence before terminal threat:

terminal action
← preceding action
← combination
← progression route
← starting context

Must compare chains that reached threat with comparable chains that did not.

### 6.12 Retention / Loss Intelligence

Examines where processes survive, reset, terminate or hand over possession visibly.

### 6.13 Recovery / Transition Intelligence

Examines visible consequences after changes of control / recovery / loss.

### 6.14 Attack Typology Intelligence

Groups admitted attack processes into observable process families and variants.

Provider labels may assist but are not tactical-plan truth.

### 6.15 Opponent Disruption / Response Intelligence

Examines visible opponent actions associated with process change:
- interception
- duel
- recovery
- forced reset candidate
- handover

Without tracking/video it must not claim true pressure geometry, compactness or defensive plan.

### 6.16 Actor / Participation Intelligence

Examines where actors participate in successful / failed / deviant processes, at which node and in which context.

### 6.17 Match Evolution Intelligence

Cross-cutting lens over every other specialist:
- first half / second half
- early / middle / late
- admitted score-state
- pre/post turning point where supported
- process-state transitions

Match Evolution is both a specialist output and a conditioning lens.

### 6.18 Restart / Set-Piece Intelligence

NOW only as admitted restart context unless observation capability is sufficient for a dedicated specialty analyzer.

## 7. Spatial representation hierarchy

Three spatial representations may coexist.

### CANONICAL GRID — NOW

Stable, explainable and comparable pitch cells after pitch-frame admission.

### FUNCTIONAL FOOTBALL ZONES — NOW / DEGRADED depending semantics

Examples:
- penalty area
- central corridor
- half-space candidates
- wide channel
- thirds

Only after semantics and frame/direction admission.

### LEARNED / ADAPTIVE REGIONS — LATER

Match-specific regions inferred from admitted path / consequence structure.

These are derived model objects, not physical truth.

Tracking-dependent constructs remain unavailable without tracking/video:
- pitch control
- true passing-lane availability
- true pressure geometry
- compactness
- team shape
- defensive-line height
- off-ball availability
- body orientation / scanning

## 8. Opportunity / denominator layer

Raw counts and raw percentages are insufficient.

Where possible, each diagnostic rate must expose:
- numerator
- eligible denominator
- opportunity definition
- dependency burden
- episode spread
- actor spread
- context spread
- censoring
- unresolved burden

Examples:
- 8/11 eligible opportunities
- not simply 8 occurrences

High coverage != high independence.

## 9. Dynamic-state layer

Whole-match aggregation may hide real changes.

Where temporal support exists, specialist analyzers should be able to compare states across admitted windows / episodes / periods / regimes.

Candidate chain:
STATIC SUMMARY
→ WINDOWED STATE
→ STATE TRANSITION
→ MATCH EVOLUTION

No state transition may be inferred from source-row ordering.

## 10. Variant layer

Every specialist should attempt to expose:
- SUCCESSFUL / PRODUCTIVE VISIBLE VARIANT candidate
- FAILED / NON-PRODUCTIVE VISIBLE VARIANT candidate
- DEVIANT VARIANT
- CENSORED
- UNRESOLVED

Outcome semantics must not enter comparison admission when doing so would leak the target result into eligibility.

## 11. Discovery → Comparison → Falsification

Every specialist must implement or explicitly declare missing coverage for three analytical modes.

### DISCOVERY
What happened? What repeated? What local structure is visible?

### COMPARISON
What changed across eligible opportunities / variants / contexts?

### FALSIFICATION
Where are the counterexamples, contradictory findings and alternative explanations?

Counterevidence is not a report footnote. It is part of the native operation of each specialist.

## 12. Pattern candidate contract

A football pattern must not be defined as “seen three times”.

PATTERN_CANDIDATE requires, when capabilities exist:
- recurrent relational / process structure
- comparison eligibility
- context conditioning
- opportunity support
- episode spread
- actor spread
- variant structure
- sensitivity / robustness assessment
- counterevidence
- dependency qualification

PATTERN_CANDIDATE != TACTICAL_INTENTION
PATTERN_CANDIDATE != CAUSALITY
PATTERN_CANDIDATE != COACH_PLAN

## 13. Common PUZZLE_FINDING contract

Specialist analyzers should speak a common upper contract rather than bespoke report schemas.

Required upper fields:
- finding_id
- puzzle_family / specialist_family
- football_question
- scale_micro_meso_macro
- entity_scale
- WHAT_VISIBLE
- WHERE
- WHEN
- GAME_STATE
- PROCESS_OR_EPISODE
- VARIANT
- SUPPORT
- DEPENDENCY
- COUNTEREVIDENCE
- CONTRADICTORY_EVIDENCE
- CONSEQUENCE
- ALTERNATIVE_EXPLANATION
- SAFE_MEANING
- FORBIDDEN_INFERENCE
- UNCERTAINTY
- CLAIM_CEILING
- WITHDRAWAL_CONDITION
- ACTORS
- RELATED_FINDINGS
- ANALYST_ACTION
- PROVENANCE
- CONTRACT_VERSION

Current Safe Finding is to be rehabilitated into this contract; it is not discarded.

## 14. Cross-Mechanism Evidence Graph

This is the coordination layer. It must not be replaced by free-form LLM summarization.

Candidate relations:
- SUPPORTS
- REFINES
- CONTEXTUALIZES
- CONTRADICTS
- COMPLEMENTS
- SHARES_EVIDENCE_WITH
- SHARES_DEPENDENCY_WITH
- SHARES_CONTEXT_WITH
- SHARES_ACTOR_WITH
- SHARES_PROCESS_FAMILY_WITH
- SAME_EPISODE_CANDIDATE
- SAME_PROCESS_CANDIDATE
- SAME_VARIANT_CANDIDATE
- PRECEDES_CONFIRMED
- HAS_VISIBLE_CONSEQUENCE
- COUNTEREXAMPLE_TO
- ALTERNATIVE_EXPLANATION_FOR

Critical rule:

PUZZLE DIVERSITY != EVIDENCE INDEPENDENCE

If three specialists reuse the same upstream occurrence cluster, the synthesizer must represent three analytical perspectives over one dependency cluster, not three independent supports.

## 15. Mechanism Candidate

A mechanism candidate is created only when multiple compatible findings begin to describe a coherent match-local football proposition.

Canonical fields:
- mechanism_candidate_id
- FOOTBALL_PROPOSITION
- team
- period / game-state
- process_family
- supporting_findings
- supporting_specialist_families
- shared_evidence_groups
- dependency_burden
- recurrence
- episode_spread
- actor_spread
- context_spread
- consequence profile
- counterevidence
- contradictory_findings
- alternative_explanations
- safe_meaning
- forbidden_inference
- claim_ceiling
- withdrawal_condition

MECHANISM_CANDIDATE != MATCH_MECHANISM_TRUTH

## 16. Match mechanism ontology

Final synthesis may classify outputs as:

PRIMARY_MECHANISM
- central to match story
- supported by multiple appropriate analytical perspectives
- dependency-qualified
- survives counterevidence review

SUPPORTING_MECHANISM
- explains, limits or extends a primary mechanism

LOCAL_FINDING
- defensible but not elevated to whole-match mechanism

WEAK_SIGNAL
- interesting but limited by sample / dependency / context / censoring

CONTRADICTORY_EVIDENCE
- real evidence that challenges the leading explanation

UNRESOLVED_PIECE
- important football question that current observation capability cannot resolve

No majority vote across specialists is allowed.

## 17. Mechanism strength profile

Do not collapse all dimensions into one confidence percentage by default.

Track separately:
- evidence sufficiency
- dependency burden
- specialist diversity
- recurrence
- episode spread
- actor spread
- context spread
- consequence consistency
- counterevidence burden
- contradictory evidence
- unresolved burden
- censoring burden
- sensitivity stability
- claim ceiling

## 18. Final Postmatch assembly

The final report is not a list of all technical findings.

Target structure:

1. 3–5 PRIMARY / SUPPORTING MATCH MECHANISMS
2. Relevant LOCAL_FINDINGS
3. CONTRADICTORY_EVIDENCE / important caveats
4. UNRESOLVED_PIECES
5. Match Story

The final language layer may summarize only objects already admitted by the evidence / mechanism graph. LLM text remains non-evidence.

## 19. Capability admission — NOW / LATER / REJECT

### NOW

Event / occurrence supported:
- action-family analysis
- pass / cross / shot / carry / duel / recovery families
- admitted actor participation
- partial-order temporal sequence
- process variants
- visible consequence
- comparison eligibility
- counterevidence
- canonical grid after spatial admission
- functional zone candidates after frame/direction semantics
- relation / network candidates
- motif / pattern candidates with explicit ceiling
- micro / meso / macro lineage where supported
- period-conditioned evolution
- score-state only if admitted from evidence

### LATER

Requires additional stable capability / modeling:
- learned adaptive spatial regions
- state clustering / regime learning
- VAEP/xT/EPV-style value models
- cross-match stability
- shrinkage / Bayesian priors
- population-level pattern reliability
- advanced specialty restart intelligence

These remain MODEL OUTPUT / DERIVED INTELLIGENCE, never observation truth.

### REJECT without required evidence

Without tracking / video / suitable external evidence do not claim:
- true team shape
- compactness
- defensive-line height
- pitch control
- true pressure geometry
- true off-ball options / runs
- body orientation / scanning
- true player / ball speed or load
- coach intention
- tactical plan
- dominance
- causality

## 20. Development discipline

WIP=1.

Do not create one parallel engine per football noun.

Preferred sequence:

problem
→ current producer
→ evidence capability
→ analytical axis
→ specialist consumer
→ discovery / comparison / falsification gap
→ output contract
→ fusion role
→ analyst value
→ tests
→ ACTIVE_MATCH need
→ minimal code
→ real-match evidence
→ Red Team

REHABILITATE_BEFORE_PARALLEL_ENGINE
ADAPT_NOT_COPY
CODE_LAST

## 21. Coverage audit matrix

All current producers must eventually be mapped to:

CURRENT_PRODUCER
→ EVIDENCE_CAPABILITY
→ ANALYTICAL_AXIS
→ SPECIALIST_CONSUMER
→ SCALE
→ DISCOVERY
→ COMPARISON
→ FALSIFICATION
→ PUZZLE_OUTPUT
→ CROSS_MECHANISM_ROLE
→ ANALYST_VALUE
→ NOW / LATER / REJECT

This matrix, rather than technical module count, determines product gaps.

## 22. Current development priority

The present product already contains useful Process Variant, Retention/Loss, Actor/Participation and temporal/evolution primitives. The immediate priority is therefore not to create many new specialist engines.

Priority order:

1. normalize existing Safe Finding outputs into common PUZZLE_FINDING contracts
2. rehabilitate existing evidence fusion into football-semantic cross-mechanism fusion
3. materialize MECHANISM_CANDIDATES without inflating evidence independence
4. connect mechanism candidates to Final Postmatch assembly
5. then fill real specialist coverage gaps identified by the audit

Known likely high-value coverage gaps:
- Progression & Access comparison / falsification
- Opponent Disruption & Response
- Chance Creation Chain comparison / falsification
- richer Match Evolution / admitted score-state
- spatial hierarchy beyond coarse cells

## 23. Product success criterion

A successful architecture slice is not “more checks passed”.

It must add a new defensible football statement or strengthen the connection among existing observations so the analyst can explain the match better.

The target single-match product must answer:

- What happened?
- Where and when did it happen?
- Which actors and relations were involved?
- Which process did it belong to?
- Which comparable variants existed?
- What visible consequence followed?
- How did the process vary over time / context?
- What counterevidence challenges the interpretation?
- Which local findings combine into the 3–5 main match mechanisms?
- What is the safest complete match story?

That is the target HPFA Postmatch intelligence architecture.
