# HPFA ZFGV Retroactive Capability Recovery Map V1

Status: ACTIVE_MIGRATION_GUIDE  
Product model: ZFGV / Enriched Football Observation Data  
Global event-only gate: RETIRED  
Claim discipline: PRESERVED

## Core rule

A construct is not admitted because it is event-only compatible. It is admitted only when its explicit required observation capabilities are present and admitted with valid provenance, dependency, identity, time/space and claim-ceiling semantics.

`required_capabilities ⊆ admitted_capabilities`

Event remains one observation family inside ZFGV. Event-specific modules remain valid when their construct is genuinely event-specific.

## Recovery matrix

| Capability | Old event-only suppression risk | ZFGV surface that can support it | Safe recoverable ceiling | Still forbidden without extra evidence |
|---|---|---|---|---|
| ENTITY / ACTOR | non-event rows treated as secondary | player/team/GK identity and participation surfaces | match-local actor/team participation candidates | global identity truth without identity admission |
| TEMPORAL | row order mistaken for chronology or non-event intervals ignored | semantic time, periods, participation/context intervals | admitted partial order, intervals, WHERE/WHEN | fabricated total order for same timestamp |
| SPATIAL | coordinates closed because tracking absent | admitted coordinate semantics/pitch frame/direction | zone, channel, boundary-entry, spatial-transition candidates | shape, compactness, pitch control, off-ball geometry |
| OUTCOME / QUALIFIER | provider labels either over-promoted or discarded | success/failure/terminal outcome labels with semantics | visible outcome/qualifier candidates | causal mechanism from label alone |
| RELATIONAL | action-centric pipeline loses references | received/opponent/reference atoms and admitted links | relation bundle candidates | physical interaction geometry not observed |
| PROCESS / PARTICIPATION | participation labels discarded as non-events | positional/counter/set-piece/process participation intervals | process membership/participation candidates | possession truth, coach intention, tactical plan |
| AGGREGATE / TABULAR | XLSX treated as validation-only or excluded from action spine | player/team/GK aggregate surfaces | aggregate observation, reconciliation, denominator/context support | action identity, independent evidence vote, metric truth without definition |
| CONTEXT | context treated as external commentary | score/period/competition/role/context surfaces where admitted | context-conditioned comparison candidates | causal attribution to context |
| CONSEQUENCE | only direct event chains considered | terminal outcome candidates, derived consequence atoms, admitted relation/time links | visible consequence candidates | causality if only temporal/relational association exists |
| METRIC / MODEL | event-only compatibility used as eligibility gate | construct-specific multi-surface inputs | metric/model candidate when prerequisites and validation pass | model output as fact; unvalidated xT/xPass/VAEP/EPV truth |
| SAFE FINDING | finding limited to event-pattern language | combined episode/process/context/consequence/counterevidence spine | defeasible match-local finding | dominance, tactical plan, causality, intention unless separately supported |

## Recover now

1. Provider metric dictionary: replace global `event_only_compatible` rejection with explicit ZFGV capability contract while preserving legacy metadata and claim locks.
2. Metric definition policy: add canonical required-observation-capability semantics; `required_event_families` becomes one possible requirement, not the universe definition.
3. Metric fusion eligibility: replace future reliance on `eventonly_metric_allowlist_v1` with construct capability admission; keep the legacy file as historical/compatibility until consumers are proven migrated.
4. Spatial/process/aggregate consumers: audit for gates that reject valid observations solely because they are not action/event rows.
5. Safe Finding: ensure recovered capability evidence keeps source role, dependency, counterevidence, alternative explanation, uncertainty and withdrawal condition.

## Do not recover as truth

The ZFGV migration must not open any direct truth for:

- true team shape
- compactness
- defensive-line height
- pitch control
- off-ball geometry/run/options
- body orientation/scanning
- true player/ball speed or physical load
- true pressure geometry
- coach intention
- tactical plan
- dominance
- causality

These require tracking/video or other specifically admitted evidence depending on the construct.

## Migration invariant

Every rehabilitation must answer:

1. Which old event-only gate suppressed the capability?
2. Which ZFGV surface actually exists?
3. What source/evidence strength does it provide?
4. What is the safe new claim ceiling?
5. What remains forbidden?
6. Which tests prevent both under-use and overclaim?
7. What new defensible football information becomes available to the analyst?

No answer → LATER / REJECT / RESEARCH_ONLY.

## Release locks

`canonical_event_count=UNKNOWN`  
`true_action_count=UNKNOWN`  
`production_release=false`
