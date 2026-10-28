# HPFA Enriched Football Observation Data V1

Status: POLICY_CORRECTION_PASS
Runtime authority: no; this is product governance and claim-capacity policy.

## Product definition

HPFA is not globally constrained by an `event-only` product identity. The canonical observation model is **Enriched Football Observation Data** (`Zenginleştirilmiş Futbol Gözlem Verisi`).

The phrase `event-only` may remain in historical filenames, donor lineage, literature categories and compatibility fields, but it must not act as the global ceiling for what HPFA is allowed to observe, reconstruct, compare or project.

## Why this correction exists

Current match surfaces may contain more than isolated event labels. Depending on provider/version and admission, they may expose:

- action labels and action families;
- start/end time candidates and period context;
- spatial coordinates;
- team/player identity candidates;
- multi-player process participation labels;
- team/player/reflection views of the same upstream football occurrence;
- progression, forward, carry, loss, recovery, challenge, interception and terminal-consequence labels;
- aggregate surfaces;
- co-occurrence and opponent-side relational evidence;
- enough admitted structure to reconstruct process, consequence and response candidates.

Therefore capability admission must be based on **what the current surface actually observes**, not on a binary `event-only versus tracking` product label.

## Observation capacity ladder

| Layer | Name | What it may support after explicit admission |
|---|---|---|
| L0 | AGGREGATE_SURFACE | provider aggregate/context surfaces |
| L1 | ACTION_OBSERVATION | action-family occurrence candidates |
| L2 | TEMPORAL_OBSERVATION | bounded temporal windows and admitted partial order |
| L3 | SPATIAL_OBSERVATION | action-location and spatial transition candidates |
| L4 | RELATIONAL_COOCCURRENCE | reconciled same-process/entity/opponent co-occurrence candidates |
| L5 | PROCESS_CONTEXT_OBSERVATION | process participation/context candidates |
| L6 | CONSEQUENCE_RESPONSE_OBSERVATION | visible consequence and opponent-response candidates |
| L7 | RECONSTRUCTED_STATE_TRANSITION | evidence-bearing football state-transition candidates |
| L8 | TRACKING_VIDEO_PHYSICAL_STATE | true physical/off-ball geometry requiring tracking/video or equivalent admitted source |

Lower layers do not imply higher-layer truth.

## Claim-capacity rule

For every metric/model/finding/capability, replace the question:

`Is this event-only compatible?`

with:

`Which observation layers and field semantics does this construct require, and are those layers explicitly admitted for the current source?`

Legacy boolean fields such as `event_only_compatible` are deprecated compatibility metadata. They must not be used as the sole admission gate for new capability work.

Preferred new fields:

- `required_observation_layers`
- `required_surface_semantics`
- `tracking_video_required`
- `observation_layer_admission_state`
- `claim_ceiling`

## Capability expansion opened by this correction

The following families must be re-audited because a global event-only framing may have blocked useful work unnecessarily:

1. **Temporal dynamics** — start/end candidates, bounded windows, duration-like observations, admitted BEFORE/AFTER.
2. **Spatial progression** — action-location progression, directional transition candidates, corridor/zone movement, with coordinate/direction gates.
3. **Relational reconstruction** — opponent-side action pairing, challenge/recovery/loss relations, multi-player same-process participation.
4. **Visible opponent response** — response-latency and response-type candidates after occurrence/process and temporal admission; not true physical reaction speed.
5. **Process-state dynamics** — progression→terminal, recovery→progression, loss→opponent consequence, recurrence/change/deviation.
6. **Analyst attention surfaces** — Match ECG / Focus Candidate / anomaly and change-point radar over admitted observation layers.
7. **Player-process contribution** — participation/support within admitted processes; not causal player impact.
8. **Spatial-temporal state-transition primitives** — construct-level dynamics without claiming tracking truth.

## What remains forbidden without stronger source admission

This correction does **not** weaken claim safety. Without tracking/video or equivalent source admission, HPFA still must not claim:

- true player or ball speed/acceleration;
- physical closing velocity;
- true pressure geometry;
- team shape, compactness, defensive-line height;
- off-ball runs/structure/options;
- body orientation/scanning;
- pitch control;
- fatigue/load;
- tactical plan or coach intention;
- dominance or causality.

Proxy candidates may be created only with explicit labels and withdrawal conditions.

## Engineering migration rule

Do not mass-rename historical files or donor lineage merely for terminology. Instead:

1. Correct global product identity and governing docs.
2. Add observation-layer contracts.
3. Audit every executable gate that uses `event_only_compatible` or equivalent as an operational boolean.
4. Where the boolean is merely metadata, preserve it for backward compatibility and add the richer layer contract.
5. Where the boolean blocks a construct solely because it is not traditional event-only, replace that gate with observation-layer admission.
6. Preserve all existing claim locks and regressions.

## Red Team

The correction must not become a route to overclaim:

- numeric time != chronology;
- coordinate presence != direction integrity;
- co-occurrence != causal interaction;
- same timestamp != total order;
- opponent response candidate != physical reaction speed;
- player participation != impact/causality;
- action-location distribution != team shape;
- recurrence != tactical plan;
- absence != counterevidence.

## Release state

This document changes product framing and migration policy only. It does not by itself promote any new football truth.

canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
