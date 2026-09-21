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
