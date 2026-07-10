# HPFA 2035 Five-Domain Architecture Review V1

Status: `POLICY_CORRECTION_PASS`

## Executive verdict

The proposal is directionally strong but architecturally over-converged.

Do not lock HPFA into five large modules.

Lock HPFA into five capability domains with small composable modules behind stable contracts.

Why:

```text
five monoliths = high coupling, slow testing, hard migration, hidden state
five domains = stable architecture, replaceable internals, reusable contracts
```

## Current limitation

The current hpfa product already contains relevant building blocks:

```text
event window builder
phase/sequence composite
sequence feature extraction
feature primitive registry
metric governance
composite evidence packet
multi-signal fusion
argument builder
defeasible argument router
evidence graph
360 evidence lens
safe argument router
report block composer
output contract
assembly gate
```

Therefore, creating five new top-level engines from scratch would duplicate existing capability and fragment product truth.

## Hidden limitation

The hidden risk is not donor contamination alone.

It is architecture relabeling:

```text
existing small modules
-> ignored
-> replaced by new large engines
-> duplicate contracts
-> conflicting identities
-> unclear canonical path
```

This would produce technical debt under a futuristic name.

## Accepted architecture decision

Create five domains:

```text
D1 Reference Isolation and Ingest Governance
D2 Spatial and Relational State Diagnostics
D3 Sequence and Stochastic Evidence
D4 Faultline and Defeasible Reasoning
D5 Output and Consumer Orchestration
```

Each domain may contain multiple small HPFA-native modules.

No donor code is copied.

## Domain 1 — Reference Isolation and Ingest Governance

Original proposal: `L1_Donor_Claim_Gateway`

Decision: `ACCEPT_WITH_AUTHORITY_CORRECTION`

Rename recommendation:

```text
reference_intake_isolation_domain
```

Reason:

Donor repositories do not provide match fact. They provide references, capabilities, schemas and candidate data artifacts.

Correct responsibilities:

```text
read-only donor metadata acquisition
immutable reference manifest
content hash
file-type and content eligibility
tracking/video rejection
quarantine
no-imputation gate
connection failure state
reference-to-authority isolation
```

Incorrect responsibility:

```text
turn donor event files into match fact
```

Error families:

```text
ERR-101 REFERENCE_CAPABILITY_MISMATCH
ERR-102 DONOR_INTEGRITY_FAILED
ERR-103 CONNECTION_INCOMPLETE
ERR-104 TRACKING_OR_VIDEO_REJECTED
ERR-105 REQUIRED_FIELD_MISSING_NO_IMPUTATION
```

Product impact: very high.
Runtime dependency: GitHub/network for reference discovery; ACTIVE_MATCH remains separate.
Claim impact: reduces authority contamination.
Release impact: governance/runtime tooling only.

## Domain 2 — Spatial and Relational State Diagnostics

Original proposal: `L2_Topological_State_Space`

Decision: `ADAPT_STRONGLY`

Do not claim team ontology or structural truth from event coordinates.

Correct outputs:

```text
event-action concentration zones
pass-relation graph candidates
coordinate-distance diagnostics
zone transition diagnostics
edge-density candidates
categorical entropy
transition entropy
corridor usage candidates
```

Unsafe outputs:

```text
true space occupation
true player spacing
true pitch control
true off-ball structure
complete team ontology
```

`centroid_distance` is eligible only when:

```text
membership set is explicit
coordinate surface is complete enough
reference frame is declared
missing-coordinate rate is below policy threshold
```

`inner_corridor` requires a canonical zone taxonomy.

Shannon entropy is allowed as a distribution diagnostic:

```text
H = -Σ p_i log(p_i)
```

It must not be interpreted as tactical quality by itself.

Red-card context is a valid qualification, but the proposed fixed rule "30 percent with ten men" must not be hardcoded without research and calibration. Use a generic numerical-state context gate.

Potential HPFA-native modules:

```text
spatial_zone_registry_lite
coordinate_distance_primitive_lite
pass_relation_graph_lite
entropy_diagnostic_lite
numerical_state_context_gate_lite
```

## Domain 3 — Sequence and Stochastic Evidence

Original proposal: `L2_Stochastic_Sequence_Engine`

Decision: `ACCEPT_AS_EVOLUTION, NOT REPLACEMENT`

Current hpfa already extracts sequence features including duration, progression, terminal event type, score state, red-card state, numerical state, start/end zone and sequence type.

Therefore, the correct path is:

```text
existing phase_sequence_composite
-> canonical sequence contract
-> sequence consequence primitives
-> stochastic diagnostic adapters
```

Do not rebuild sequence segmentation from scratch unless the current contract fails.

Sequence Terminal Value must first be defined as a contract, not a single score.

Recommended decomposition:

```text
terminal_event_class
terminal_zone
terminal_action_presence
terminal_value_model_id
value_source
uncertainty
counterfactual baseline
sequence_context
```

Markov and Bayesian methods are eligible only after:

```text
canonical event ordering
team binding
time integrity
sequence identity
state definition
sample sufficiency
calibration evidence
```

Unsafe question:

```text
How much did this pass increase goal expectation?
```

unless a validated value model and counterfactual baseline exist.

Safe question:

```text
How did the observed sequence state distribution change after this event candidate?
```

Potential HPFA-native modules:

```text
sequence_state_registry_lite
sequence_terminal_consequence_lite
markov_transition_diagnostic_lite
bayesian_evidence_update_lite
sequence_value_model_contract_lite
```

## Domain 4 — Faultline and Defeasible Reasoning

Original proposal: `L3_Faultline_Detection_Matrix`

Decision: `ACCEPT_WITH_MAJOR CLAIM CORRECTION`

This domain should not generate definitive tactical percentages such as:

```text
if opponent presses high, centre-back connection quality falls 40 percent
```

unless the percentage comes from validated comparable evidence.

Correct role:

```text
frame candidate
finding candidate
faultline candidate
counter-scenario
falsification condition
withdrawal condition
missing-lens inventory
review state
```

HPFA already contains:

```text
composite argument builder
defeasible argument router
evidence graph
360 evidence lens matrix
```

Therefore, build adapters and contracts around these modules instead of creating a parallel monolith.

The 16 dimensions and 6 phases must be explicit registries, not hardcoded branching logic.

Recommended registries:

```text
analysis_dimension_registry_v1
analysis_phase_registry_v1
faultline_family_registry_v1
counter_scenario_registry_v1
```

OODA may inspire state progression, but it should not be copied as a military decision truth model.

Potential HPFA-native additions:

```text
faultline_candidate_engine_lite
analysis_dimension_coverage_gate_lite
phase_transition_contract_lite
intervention_option_router_lite
```

## Domain 5 — Output and Consumer Orchestration

Original proposal: `L3_Deterministic_Output_Orchestrator`

Decision: `ADAPT_STRONGLY`

The word `deterministic` is valid for execution order, not for football certainty.

The orchestrator may deterministically:

```text
call stages
preserve identities
stop on block
hold on review
write ledgers
route approved candidates to consumers
```

It may not deterministically declare:

```text
working strategy
failed strategy
correct fix
causal explanation
```

Academic and sociological references must remain separate reference layers.

`Fix` must become:

```text
intervention_option_candidate
```

Caravaggio-inspired contrast is allowed as style, but black/white epistemic certainty is rejected.

Required visual contract:

```text
high contrast
no-data mask
uncertainty annotation
sample-density annotation
candidate-only title
```

Consumers:

```text
coach brief candidate
broadcast script candidate
scout report candidate
analyst report candidate
```

These are output consumers, not authority layers.

## Architectural debt detected

### 1. Five-module lock-in

Minimal fix:

```text
rename modules as domains
```

Ideal fix:

```text
capability domains + small modules + stable contracts
```

Priority: P0
Impact: very high
Migration cost: low now, high later

### 2. Donor data called Fact

Minimal fix:

```text
rename to immutable reference artifact
```

Ideal fix:

```text
strict reference plane separated from ACTIVE_MATCH runtime plane
```

Priority: P0
Impact: critical claim/authority safety
Migration cost: low

### 3. Binary Fusion terminology

Minimal fix:

```text
rename to capability comparison
```

Ideal fix:

```text
multi-source reference comparison with mismatch classes
```

Priority: P0
Impact: high
Migration cost: low

### 4. Hardcoded 30 percent red-card rule

Minimal fix:

```text
remove fixed threshold
```

Ideal fix:

```text
numerical-state context policy with evidence-backed thresholds
```

Priority: P1
Impact: medium/high
Migration cost: low

### 5. Sequence Terminal Value as one score

Minimal fix:

```text
define score provenance and uncertainty
```

Ideal fix:

```text
value-model contract with multiple interchangeable models
```

Priority: P1
Impact: high
Migration cost: medium

### 6. Faultline directly produces Fix

Minimal fix:

```text
replace Fix with option candidate
```

Ideal fix:

```text
option router with trade-offs, validation needs and withdrawal conditions
```

Priority: P1
Impact: critical claim safety
Migration cost: medium

### 7. Black/white visual certainty

Minimal fix:

```text
add uncertainty/no-data layer
```

Ideal fix:

```text
visual epistemology contract
```

Priority: P2
Impact: medium/high
Migration cost: low

## Better architecture

```text
REFERENCE PLANE
  read-only donor manifests
  immutable snapshots
  quarantine
  no-imputation

RUNTIME AUTHORITY PLANE
  runtime/active_single_match/current
  canonical ingest
  data quality
  team/time/axis integrity

EVIDENCE PLANE
  event windows
  feature primitives
  spatial diagnostics
  sequence diagnostics
  graph/entropy diagnostics

REASONING PLANE
  composite evidence
  fusion relations
  argument candidates
  counter-evidence
  faultlines
  defeasible routing

CONSUMER PLANE
  analyst report
  scout report
  pre-match packet
  coach brief candidate
  broadcast script candidate
  visual outputs
```

## Migration plan

### P0 — Architecture correction

```text
1. adopt five domains, reject five monoliths
2. preserve existing sequence/intelligence/report modules
3. define canonical domain interfaces
4. separate reference and runtime authority planes
```

### P1 — Domain 1 contracts

```text
read-only connector permissions
reference manifest schema
quarantine path policy
no-imputation policy
connection failure protocol
tracking/video content rejection
```

### P2 — Domain 2 and 3 primitive contracts

```text
zone taxonomy
coordinate primitive contracts
pass relation graph contract
entropy diagnostic contract
sequence terminal consequence contract
Markov/Bayes eligibility gates
```

### P3 — Domain 4 integration

```text
16-dimension registry
6-phase registry
faultline candidate contract
counter-scenario and falsification contract
canonical defeasible route
```

### P4 — Domain 5 thin orchestration

```text
stage ledger
consumer routing
visual uncertainty contract
broadcast/scout/coach candidate contracts
```

### P5 — ACTIVE_MATCH evidence

```text
engineering evidence
analyst evidence
runtime cost evidence
claim audit
release decision
```

## Tests required

```text
test_reference_artifact_never_becomes_runtime_authority
test_tracking_payload_rejected
test_no_imputation_on_required_fields
test_connection_failure_blocks_analysis_promotion
test_zone_taxonomy_required_for_inner_corridor
test_centroid_requires_explicit_membership
test_entropy_does_not_emit_tactical_truth
test_numerical_state_routes_to_context_review
test_sequence_terminal_value_requires_model_provenance
test_markov_requires_canonical_state_definition
test_bayesian_update_requires_declared_prior_and_likelihood
test_faultline_requires_counter_scenario
test_faultline_requires_falsification_condition
test_intervention_output_is_candidate_only
test_orchestrator_stops_on_block
test_orchestrator_preserves_review_state
test_visual_output_has_no_data_mask
test_no_sample_match_identity_leak
```

## Accepted ideas

```text
fault isolation
fail-closed reference intake
no-imputation
content-aware tracking rejection
network/entropy diagnostics
sequence-level reasoning
Markov/Bayesian research path
counter-scenarios
falsification conditions
multi-layer reporting
thin deterministic execution orchestration
```

## Rejected ideas

```text
donor event data as Fact
five monolithic engines
true team ontology from event coordinates
player-space truth without tracking
hardcoded red-card percentage rule
single opaque Sequence Terminal Value score
fixed 40 percent tactical consequence claims
faultline to definitive Fix
black/white football certainty
OSINT merged into canonical match truth
```

## Release readiness

```text
architecture direction: ACCEPTED_WITH_CORRECTIONS
five-domain model: POLICY_CORRECTION_PASS
five executable modules: REJECTED
Domain 1 contracts: SPEC_REQUIRED
Domain 2-5 implementations: NOT_READY
ACTIVE_MATCH evidence: NONE
production release: NOT_READY
```

## Final founder decision

The proposal should become the HPFA 2035 domain architecture, not a five-engine rewrite.

The first executable product node remains:

```text
Read-only Reference Intake and Isolation Governance Pack V1
```

The second is not a new sequence engine.

It is:

```text
Canonical Domain Interface Registry V1
```

This registry will define how existing HPFA modules belong to the five domains and how data may cross domain boundaries.
