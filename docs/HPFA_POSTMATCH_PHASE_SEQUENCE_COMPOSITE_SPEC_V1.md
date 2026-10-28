# HPFA Postmatch Phase / Sequence / Numerical Replay Composite Spec V1

NODE: hpfa_postmatch_phase_sequence_composite_spec_v1
STATUS: CURRENT_REHABILITATION_SPEC
UPDATED: 2026-10-02

## Product north star

**Maçın gerçeği sahada oynanır. HPFA maçın rakamlarını yeniden oynatır.**

The product does not treat rows or provider labels as the football action itself. It reconstructs admitted on-ball observations into occurrence, temporal layer, sequence, process, variant and analyst-facing football intelligence.

This composite is not a new parallel engine. It is a rehabilitation contract for the existing HPFA owners.

## Existing owners

Current capability must remain inside existing owners, especially:

- action_occurrence_admission_lite
- occurrence_state_transition_projection
- spatial_transition_candidate_lite
- visible_action_sequence_candidates_lite
- active_match_spine_runner / process_sequence_information
- active_match_spine_runner / rich_multiformat_analysis_lane
- occurrence_consequence_projection
- reconstruction_intelligence_packet_adapter_lite

REHABILITATE_BEFORE_PARALLEL_ENGINE applies.

## Mathematical role

Mathematics works in two directions.

### COMPOSE

FACET → ACTION → TEMPORAL LAYER → SEQUENCE → PROCESS → PATTERN → VARIANT → TEAM / PLAYER / GOALKEEPER INTELLIGENCE → FOOTBALL ARGUMENT

### DECOMPOSE

ARGUMENT / TEAM RESULT → PATTERN → PROCESS → SEQUENCE → ACTION → FACET / ACTOR

Mathematics does not create football truth. It makes the numerical replay measurable, comparable and decomposable.

## Core numerical replay dimensions

Every admitted process may expose, where observable:

- team / actor
- period
- start / end time
- duration
- temporal layer count
- actor spread
- action-family composition
- pass / carry mix
- start / end zone
- visible zone transitions
- event-anchor route length
- net event-anchor displacement
- event-anchor directness
- provider attack-axis change when admitted
- visible loss / recovery
- visible consequence
- terminal / shot-ending state
- opponent visible response
- successful / unsuccessful / deviant variant context
- recurrence and first supported divergence

None of these fields alone is tactical truth.

## Multi-dimensional action semantics

A physical occurrence can carry multiple semantic facets without becoming multiple physical actions.

Example pass facet bundle:

PASS
- direction: FORWARD
- context / length: LONG
- progression: PROGRESSIVE
- destination / zone: PENALTY_AREA
- outcome: SUCCESS
- consequence: visible continuation / shot-chain candidate
- provenance: provider semantic rule ids

Required current behavior:

- preserve semantic facets per admitted temporal layer;
- preserve provider semantic rule provenance;
- count facet presence per temporal layer, not as extra physical actions;
- do not promote same-timestamp labels to total order;
- do not convert provider label into physical/tactical truth.

Current implementation surface:
C03_PROCESS_DEVELOPMENT_SIGNATURE.semantic_facet_profile

## Time

XML and CSV may both contain temporal fields. No source is treated as a universal clock by filename alone.

Admitted temporal semantics can support:

- process duration
- inter-layer time
- recovery-to-next-action time
- recovery-to-final-third time
- recovery-to-box time
- recovery-to-shot time
- loss-to-opponent-visible-consequence time
- value produced per admitted time

These are event-temporal measures, not physical sprint or movement speed.

## Space

Coordinate-derived analysis can support:

- event-anchor location
- zone
- start / end zone
- zone-to-zone transitions
- event-anchor route length
- event-anchor directness
- match-local cell usage
- visible progression / access candidates

Coordinate != tracking.

Event-anchor route != physical ball trajectory.

## Cell / spatial value direction

The pitch may be discretized into fixed cells plus football-semantic overlays.

Potential value vector:

V(c) = [goal proximity, shot threat, assist / shot-assist threat, box-access value, central-danger proximity, turnover risk, opponent visible transition exposure]

Action change:

ΔV = V(c_end) - V(c_start)

For single-match postmatch, observed cell usage and observed conversion are allowed before any generalized probability model is calibrated.

Single-match observed rate != population probability.

Threat / risk probability surfaces require compatible multi-match calibration, denominators and validation.

## Risk / reward direction

Candidate form:

EV(a) = P(success | compatible context) × Reward - P(fail | compatible context) × Cost

This is a MODEL OUTPUT when probabilities are estimated.

Before calibration, HPFA can still report observed:

- high-value destination attempts
- failure / success counts
- turnover location
- downstream visible consequence
- risk / reward profile candidates

No blind composite HPFA score.

## Team cell usage / opponent response

For each team, HPFA should be able to describe:

CELL USE → ACTION TYPE → SUCCESS / FAILURE → OPPONENT VISIBLE RESPONSE → NEXT ACTION → CONSEQUENCE → RECURRENCE / VARIANT

Potential maps:

- usage density
- entry frequency
- progression start/end
- success / failure
- loss / recovery
- opponent disruption / resistance
- value gain
- risk / reward
- box-access yield
- shot-chain yield
- goalkeeper distribution
- second-ball
- A-vs-B comparative spatial use

Repeated on-ball use supports observed spatial-use statements.

Recurrence != coach intention.

## Second ball

Candidate chain:

LONG BALL → FIRST VISIBLE CONTACT / DUEL → SECOND-BALL RECOVERY → NEXT ACTION → CONTINUATION / LOSS

If the admitted chronology cannot resolve who obtained the second ball, return UNRESOLVED.

## Goalkeeper

Goalkeeper distribution is evaluated as process participation, not only completion rate.

Possible reconstruction:

GK distribution → first visible receiver / contest → second action → second ball if present → progression / retention / loss → downstream zone / terminal state

## Acceptance

A change is valuable only if a different match package lets HPFA read the football more correctly, deeply and defensibly.

Tests must preserve:

- ROW != EVENT TRUTH
- SAME TIMESTAMP != TOTAL ORDER
- COORDINATE != TRACKING
- MULTIFORMAT != INDEPENDENT EVIDENCE
- RECURRENCE != CAUSALITY
- PROCESS LABEL != COACH INTENTION
- MODEL OUTPUT != FACT
- NO_VISIBLE_FOLLOWUP != FAILURE

## Current first implemented slice — 2026-10-02

C03 process development now preserves multi-dimensional semantic facets per admitted temporal layer:

- progression
- direction
- context / length semantics
- zone / destination semantics
- outcome
- provider semantic rule ids

It also produces a process-level semantic facet profile using temporal-layer presence as the denominator basis.

This does not create additional actions, event truth, possession truth or tactical truth.

## Next slices

After current slice passes broader and physical regression:

1. match-local cell-use frequency / yield profile
2. explicit sequence time-to-consequence measures
3. second-ball reconstruction
4. observed transition funnel decomposition
5. successful / failed variant first-divergence enrichment
6. goalkeeper distribution chain enrichment
7. calibrated spatial value / risk-reward model only after compatible multi-match data and validation
