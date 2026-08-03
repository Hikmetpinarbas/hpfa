# HPFA Event Label and Structural Progression Claim Grammar V1

Status: `SPEC_ONLY / CLAIM_GATE_CLOSED / NOT_PRODUCTION`

## Allowed analyst language

- Visible provider-label evidence supports a progression candidate.
- Coordinate evidence indicates territorial advancement within the eligible team-period frame.
- The action crossed a configured zone or lane boundary.
- Visible downstream evidence retained, reversed or terminated the progression candidate.
- Label, geometry and consequence evidence are aligned.
- The record remains label-only because coordinate or consequence support is unavailable.
- Aggregate and occurrence surfaces differ for a documented candidate reason.
- Requires later validation.

## Required analyst sentence structure

1. What was visible?
2. Where and when was it visible?
3. Which label, geometry, outcome or consequence evidence supports it?
4. What is the safe analyst meaning?
5. Which component is unresolved?

## Blocked language

- true packing
- players/opponents bypassed
- defensive or pressing line broken
- opponent structure collapsed
- pitch control
- the team dominated
- the coach intended
- this proves tactical quality
- this proves a bad decision
- this proves causality
- validated progression truth
- canonical event count

## Component disclosure

Any composite candidate must expose:

```text
provider_label_evidence
geometry_support
outcome_support
consequence_support
aggregate_support
weights_or_rules
downstream_eligibility
claim_ceiling
```

No hidden composite score is allowed. Component-only fallback is mandatory.

## Fixed boundaries

```text
canonical_event_count=UNKNOWN
production_release=false
tracking_truth=false
video_truth=false
line_break_truth=false
packing_truth=false
opponent_displacement_truth=false
possession_truth=false
sequence_truth=false
tactical_truth=false
causality_truth=false
```
