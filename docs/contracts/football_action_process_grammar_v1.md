# HPFA Football Action & Process Grammar V1

Date: 2026-09-21
Status: CANONICAL_SEMANTIC_CONTRACT_CANDIDATE
Authority: HPFA — Hikmet Pınarbaş Football Analytics
Role: Provider-independent football semantics contract. This is not a parallel engine.

## Purpose

This contract defines one shared football language for provider adapters, occurrence reconstruction, relation/process analysis, feature engineering, metrics/models, Safe Findings and analyst output.

Canonical chain:

PROVIDER ALIAS -> CANONICAL GRAMMAR CONCEPT -> OCCURRENCE/RELATION ADMISSION -> PROCESS -> FEATURE -> METRIC/MODEL -> SAFE FINDING

Core locks:

- PROVIDER LABEL != CANONICAL FOOTBALL TRUTH
- CANONICAL CONCEPT != OCCURRENCE TRUTH
- OCCURRENCE != PROCESS
- PROCESS != TACTICAL INTENTION
- METRIC/MODEL != FACT
- SAME TIMESTAMP != TOTAL ORDER
- COORDINATE != TRACKING

## Closed Ontological Classes

ACTION
QUALIFIER
OUTCOME
RELATION
PROCESS
STATE
CONTEXT
META
DERIVED_CONSTRUCT

A concept may not silently migrate between these classes.

Examples:
- PASS = ACTION
- PROGRESSIVE = QUALIFIER
- ASSIST = RELATION
- GOAL = OUTCOME
- TRANSITION_ATTACK = PROCESS
- SCORE_STATE = STATE/CONTEXT
- PERIOD_START = META

## Canonical Composition Grammar

OBSERVATION := ACTION_NUCLEUS + zero-or-more FACET + zero-or-more RELATION + zero-or-more CONTEXT

ACTION_NUCLEUS :=
BALL_TRANSFER | BALL_TRANSPORT | BALL_CONTROL | FINISHING | CONTEST | DEFENSIVE_DISRUPTION | POSSESSION_CHANGE | RESTART | GOALKEEPER_ACTION | INFRACTION

FACET :=
OUTCOME | DIRECTION | DISTANCE | BODY_PART | TECHNIQUE | ZONE_CONTEXT | SET_PIECE_CONTEXT | EXPLICIT_PRESSURE_CONTEXT | PROVIDER_QUALIFIER

PROCESS := START_TRIGGER + one-or-more ACTION_NUCLEUS + optional TERMINAL_OUTCOME

EPISODE := PROCESS + PHASE_CONTEXT + TEAM_PERSPECTIVE + TEMPORAL_BOUNDARY

MATCH_READING :=
EPISODE -> PROCESS_FAMILY -> VARIANT -> CONSEQUENCE -> COUNTEREVIDENCE -> SAFE_FINDING

## Critical Football Distinctions

### Transfer vs annotation
PASS is an action nucleus. Progressive, long, forward, into-final-third and into-box can be facets or derived constructs of that pass. They do not automatically create additional physical actions.

### Carry vs dribble
CARRY is same-actor ball transport and does not require beating an opponent.
DRIBBLE_TAKE_ON is an opponent-facing attempt to beat or create space against an opponent.

### Defensive actions
TACKLE, INTERCEPTION, BLOCK and CLEARANCE are distinct.
None implies possession recovery unless RECOVERY / POSSESSION_HANDOVER is separately admitted.

### Recovery and loss
RECOVERY != INTERCEPTION.
RECOVERY != TACKLE.
LOSS != FORCED_TURNOVER.
LOSS -> opponent RECOVERY may be a visible admitted relation without proving pressure, cause or intention.

### Shot and goal
SHOT is an action.
GOAL is primarily the terminal outcome / score-state transition of a shot sequence.
Do not double-count SHOT + GOAL as two physical on-ball actions unless the source representation explicitly requires atomic decomposition.

### Assist
ASSIST, SECOND_ASSIST, THIRD_ASSIST, KEY_PASS and SHOT_ASSIST are relational constructs. They are not extra physical action counts.

### Phases
SETTLED_ATTACK, TRANSITION_ATTACK and SET_PIECE_ATTACK are processes.
Their reciprocal defensive views are process perspectives, not defensive events.
The HPFA 6-phase / 12-direction model is therefore a process grammar, not an event taxonomy.

### Pressure
PRESSURE may be football truth only when explicit provider observation or tracking/video authority exists.
Sparse event coordinates or temporal proximity must not be renamed pressure geometry.

## Provider Binding

Provider definitions are evidence sources, not semantic authority over HPFA.

A provider mapping must retain provider name, source label, provider definition/rule, rule/version, source role, mapping target and admission/review status.

Provider-specific thresholds remain provider-specific. A provider progressive-pass rule may map to the canonical PROGRESSIVE qualifier while retaining its original threshold definition and version.

## Mathematical Semantics

State:
S_t = (team, actor_set, admitted_time, admitted_spatial_state, action_family, process_family, optional_context)

Unobserved off-ball geometry is not part of S_t.

Transition:
T_t = (S_t, A_t, S_t+1)

T_t can remain a relation candidate / partial order. It is not automatically physical chronology.

Action value:
DeltaV(A_t) = V(S_after) - V(S_before)

Only when a versioned value model and eligible before/after states exist. MODEL OUTPUT != FACT.

Process survival:
S(k) = product_j (1 - d_j / n_j)

The unit of analysis, eligible denominator and censoring rule must be explicit.

Sequence similarity:
distance(trace_i, trace_j)

Edit distance, LCS or DTW may be used only on admitted ordered features.
Similarity != tactical equivalence.

Information structure:
Entropy, HHI, mutual information and information gain describe distributions/dependence. They do not directly mean football quality, superiority or causality.

Spatial comparison:
Grid, KDE, Wasserstein or transition surfaces may compare admitted event-location distributions.
Event spatial footprint != team shape / compactness / pitch control.

Branch divergence:
COMMON_CORE -> FIRST_SUPPORTED_DIVERGENCE -> OUTCOME_CONTEXT

First divergence is an observed grammar difference candidate, not causal breakpoint truth.

## Sciences That Bind to the Grammar

- Formal ontology / knowledge representation: classes, inheritance, aliases, compatibility.
- Formal language theory: legal action/facet/relation/process compositions.
- Process mining: traces, variants, loops, branches and deviations.
- Graph / hypergraph theory: actor-action-zone-process relations.
- Markov / semi-Markov processes: state transitions and sojourn times.
- Survival analysis: time-to-loss, time-to-shot, survival and censoring.
- Information theory: route diversity, motif concentration, information gain.
- Optimal transport: distributional spatial change on admitted event surfaces.
- Compositional data analysis: closed phase/action-share vectors.
- Change-point detection: endogenous match-regime segmentation.
- Bayesian / shrinkage methods: small-sample uncertainty when defensible priors/corpora exist.
- Partial identification / Manski bounds: unresolved/censored outcomes without forced negatives.
- Decision theory: value/risk trade-offs; optimal model output is not fact.
- Defeasible reasoning / argumentation: support, counterevidence, withdrawal.
- Causal inference: only when identification assumptions are actually satisfied.

## Metric Binding Contract

Every metric must declare:

football_question
construct_id
eligible_grammar_objects
numerator
eligible_denominator
unit_of_analysis
spatial_requirement
temporal_requirement
model_requirement
dependency_rule
censoring_rule
uncertainty_method
safe_meaning
forbidden_inference
claim_ceiling

A metric definition without these fields is incomplete for HPFA semantic use.

Examples:

Pass accuracy:
- numerator: PASS with definition-aligned SUCCESS
- denominator: eligible PASS occurrences under the same definition
- forbidden: universal passing-quality truth

Progressive-pass rate:
- numerator: PASS with admitted PROGRESSIVE qualifier
- denominator: eligible PASS occurrences under the same progression definition
- forbidden: cross-provider comparison without definition alignment

Recovery-to-shot conversion:
- numerator: eligible RECOVERY processes reaching SHOT
- denominator: eligible RECOVERY processes
- forbidden: pressing success / causal attribution

## Tracking / Video Boundary

Without admitted tracking/video authority this grammar does not authorize:
- true team shape
- compactness
- true pitch control
- off-ball run geometry
- physical passing-lane denial
- physical pressure geometry
- true speed/load
- body orientation
- coach intention
- causal tactical mechanism

Provider-explicit labels may be preserved as provider observations with provenance, but an HPFA-derived claim may not silently inherit a stronger interpretation.

## Existing Owners Extended, Not Replaced

This grammar extends:
- provider_label_value_semantics_lite
- context_action_semantics_rebind_lite
- action_occurrence_admission_lite
- semantic_role_action_bundle_candidates_lite
- visible_action_sequence_candidates_lite
- reasoning_grammar_spine_lite
- metric_family_ontology_v1

## Research Basis

Internal support / donor corpus reviewed:
- HPFA_CODABLE_MODULE_AND_INTEGRATION_CANDIDATES_LIVING
- HPFA_DRIVE_RESEARCH_CATALOG_AND_NAMING_MAP_LIVING
- HPFA spatial-state / state-value / action-value research
- HPFA football object-centric event modelling
- HPFA football state-transition dynamics
- HPFA process-information-content and actor-participation research
- HPFA Football Encyclopaedia / tactical-intelligence corpus
- HP Motor / HP Engine / Yel Football Lab donor ideas

External reference families:
- Wyscout Data Glossary
- StatsBomb event/glossary semantics
- socceraction SPADL and Atomic-SPADL
- football event-data process-mining literature
- object-centric football event-log research
- semi-Markov possession-state research

Research/support material does not become product truth merely by citation.

## Product Test

For every proposed football term, metric or model:

Does this semantic definition make a different match package more correctly, deeply and defensibly understandable?

If the answer is no, do not add it.
