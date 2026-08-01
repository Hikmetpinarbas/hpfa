# HPFA Event-Only Claim Grammar V1

## Status

```text
SPEC_ONLY
CLAIM_GATE=CLOSED_BY_DEFAULT
TRUTH_CLAIM=false
canonical_event_count=UNKNOWN
production_release=false
```

## Purpose

Event and event-label surfaces must produce analyst-facing meaning without being promoted into tracking, video, tactical or causal truth.

Every finding must answer:

1. What was visible?
2. Where and when was it visible?
3. Which row-level, sequence or aggregate evidence supports it?
4. What is the safe analyst meaning?

## Allowed lead language

- Row-level evidence shows...
- Visible action-label evidence indicates...
- The ordered follow-up window contains...
- Coordinate evidence is concentrated in...
- The visible sequence continued for...
- A sequence-continuation candidate was detected...
- An adverse-consequence signal followed...
- A restart-trace candidate repeated...
- Match-local rhythm evidence suggests...
- The distributional diagnostic indicates...
- This requires later validation...

## Allowed metric language

- event-only metric candidate
- descriptive surface count
- normalized visible frequency
- sequence continuation candidate
- progression follow-up support
- adverse consequence signal
- pressure-exposure proxy
- regain stabilization candidate
- restart trace yield candidate
- distributional diagnostic
- diagnostic stability report
- construct/context warning

## Forbidden language

- dominated
- controlled the match
- controlled the pitch
- broke the defensive line
- bypassed N opponents
- escaped the press
- created overload truth
- rest defence was strong or weak
- off-ball structure
- body orientation truth
- scanning truth
- the coach planned
- the team intentionally lured pressure
- the metric proves superiority
- the metric proves player quality
- the sequence proves tactical plan
- the consequence proves causality

## Required finding structure

```text
finding_id=
source_surface=
observation_window=
team_or_actor_identity_state=
visible_evidence=
metric_or_trace_candidate=
location_time_support=
counter_scenario=
falsification_condition=
claim_ceiling=
status=PASS|WARN|FAIL|BLOCKED
analyst_meaning=
```

## Claim ceilings

| Ceiling | Permitted meaning |
|---|---|
| descriptive_only | Visible volume, time, location or label inventory |
| distributional_diagnostic | Diversity, concentration or normalized distribution |
| candidate_sequence_continuation | Visible chain continued after an eligible anchor |
| candidate_consequence_signal | A configured follow-up outcome appeared after an anchor |
| candidate_progression_support | Visible progression was followed by a threshold or action support |
| candidate_stabilization_pattern | A visible recovery was followed by retained sequence evidence |
| candidate_restart_pattern | A restart was followed by a configured visible trace |
| pressure_exposure_proxy | Clearance/loss/action clustering symptom only |
| uncertainty_report | Missingness, conflict or unresolved semantics |
| blocked | Evidence cannot support the requested output |

## Fail-closed conditions

The finding must be `BLOCKED` when any of the following is required but unresolved:

- source role,
- time/order integrity,
- coordinate orientation,
- provider label semantics,
- team/player identity,
- anchor eligibility,
- denominator,
- duplicate reflection lineage,
- period boundary,
- claim ceiling.

## Analyst-output rule

Main text should state what was seen and why it matters. Limits belong in a separate technical note. The output must not become silent, but it must remain inside the evidence ceiling.
