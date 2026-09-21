# Analyst Presentation View Model Lite V1

Module id: `analyst_presentation_view_model_lite_v1`

## Purpose

Expose current HPFA runtime artifacts as a thin-client presentation contract.
It does not create football evidence, new semantics, tactical truth, chronology truth or production output.

## Product role

This is a P7/P8 bridge toward future web/mobile clients.
It does not authorize P10 mobile-client release.

Core invariant:

```text
VISUAL_STRENGTH <= EVIDENCE_STRENGTH
```

## Input authority

Only current HPFA output artifacts under the selected output root are read.
No Drive, donor, archive or external research source becomes runtime truth.

## Surface states

Each analyst-facing surface must explicitly resolve to one of:

```text
AVAILABLE
DEGRADED
MISSING
NOT_EVALUATED
FAIL_CLOSED
```

The V1 contract exposes:
- Analyst Report
- Match Story
- Six-Phase Match View
- Mechanism Cards
- Player Process Cards
- Counterevidence Cards
- Observed Replay
- Traceback / Evidence Drawer
- Broadcast Summary
- Unknown / Unobservable Register

Missing capability must stay visible. The client may not interpolate it.

## Safety rules

- RECORDED_ACTIONS_ONLY.
- Event-anchor connection is not ball trajectory.
- Episode candidate is not tactical episode truth.
- Process participant is not off-ball tactical role.
- Same timestamp does not create total order.
- Phase candidate is not six-phase truth.
- Interaction provenance cannot strengthen football evidence.
- Client code cannot create new football semantics.
- canonical_event_count remains UNKNOWN unless separately admitted.
- true_action_count remains UNKNOWN unless separately admitted.
- production_release remains false.

## Traceability

V1 provides artifact-level provenance with size and SHA-256.
Observation-level deep links are explicitly a later contract.

## Bundle integration

The standard ACTIVE_MATCH bundle must include:

```text
analyst_presentation_view_model_lite_v1.json
```

The view model is a standard deliverable, not a replacement for:
- full-spine runtime evidence
- analyst report
- bundle manifest
- report-output governance
- final-report assembly gate

## Acceptance

Minimum:
1. deterministic same-input output;
2. FAIL_CLOSED when full-spine artifact is absent;
3. missing/degraded surfaces remain explicit;
4. no claim-ceiling promotion;
5. view model included in standard user bundle;
6. production_release=false.

PASS != RELEASE.
Mobile application release is not granted by this contract.

## Match Story / Mechanism compression extension

The presentation layer may group current intelligence chains only by an already-admitted upstream tuple:

```text
argument_family + relation_scope + analysis_route
```

This grouping is presentation compression, not discovery of a new football mechanism.

The Match Story target is 3–5 distinct mechanism families only when the admitted runtime actually contains that many distinct families.
A forced minimum is forbidden.

If only one distinct family is admitted, the correct product output is one mechanism card.

Mechanism-card nominal chain counts are navigation/coverage counts only.
They are not independent recurrence, probability, confidence, evidence strength or causal weight.

Each mechanism card must preserve:
- upstream process/argument family
- relation scope
- analysis route
- nominal chain count
- distinct packet/context/support reference counts
- defeasible state distribution
- independence states
- counter-scenarios
- withdrawal conditions
- safe-sentence examples
- explicit cannot-say register

Selection basis:

```text
COVERAGE_COMPRESSION_NOT_EVIDENCE_STRENGTH
```

Forbidden:
- inventing extra mechanism families to reach 3–5
- treating nominal chain count as independent support
- ranking mechanism truth strength from UI coverage
- causal, tactical-intention, off-ball, pressure-geometry or dominance promotion

## Player Process Card extension

Player Process Cards consume only current-invocation:
- match-local identity candidates
- trackable action trace candidates
- trackable action consequence candidates

They represent recorded-action participation, not off-ball tactical role.

Required visible guards:
- identity_scope=MATCH_LOCAL_CANDIDATE_ONLY unless separately admitted
- validated_player_identity flag
- trace_candidate_count_is_physical_action_count=false
- process_participation_is_off_ball_tactical_role=false

Allowed card content:
- match-local actor display candidate
- team identity candidate
- trace-candidate count
- action-family candidate distribution
- source-role distribution
- period distribution
- consequence-candidate record distribution
- count of trace records with visible follow-up support
- representative trace candidate IDs

Blocked interpretation:
- player quality from trace volume alone
- physical action count
- off-ball tactical role
- positioning truth
- pressure geometry
- workload, speed or distance truth
- coach intention

The surface remains DEGRADED while identity is match-local candidate only and higher-level admitted process participation is unavailable.
