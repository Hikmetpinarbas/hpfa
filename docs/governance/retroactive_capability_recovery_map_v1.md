# HPFA ZFGV Retroactive Capability Recovery Map V1

Status: AUDIT / REHABILITATION MAP
Executable product truth: fresh main
Migration work: open PR stack only until landed

## Governing decision

Do not ask whether a construct is `event-only compatible`.
Ask:
1. What observation capabilities are required?
2. Which are present and admitted?
3. Which evidence prerequisites are unresolved?
4. What is the safe claim ceiling?
5. What remains forbidden?

## Recovery map

| Capability | Current producer | Old event-only limit | Available ZFGV surface | Safe new ceiling | Still forbidden | Needed contract change | Test | ACTIVE_MATCH need | Analyst gain |
|---|---|---|---|---|---|---|---|---|---|
| Metric/provider admission | metric_definition_policy_lite + provider_metric_dictionary_lite | binary event_only_compatible compatibility could act as admission shorthand | ACTION, ACTOR, AGGREGATE, PROVIDER_DERIVED, PROVENANCE plus optional TIME/SPACE/OUTCOME/CONTEXT | construct-specific admission by required capabilities and forbidden_without | provider label as construct truth; unsupported comparison; tracking truth | provider dictionary rows inherit/declare explicit observation manifest; legacy flag shadow only | explicit rich nonphysical construct must not fail only because legacy flag is false; missing required capability must fail closed | verify current provider/aggregate surfaces and denominator/identity/dependency admission | legitimate metrics can use aggregate/process/spatial/context surfaces without weakening claim safety |
| Process participation | analyst_episode_process_participation_projection_v1 | participation labels treated as generic support because not canonical events | PROCESS/PARTICIPATION, ACTOR, TEAM, TEMPORAL, PROVIDER_DERIVED, PROVENANCE | actor/team/process-family participation candidate bound to episode navigation | possession truth, tactical phase truth, off-ball role, team shape, coach intention | preserve provider semantics, actor identity, reflection/dependency, episode binding | provider label vs tactical truth; missing actor fail closed; missing episode downgrade | confirm process annotations bind to real ACTIVE_MATCH identity/evidence atoms | who appeared in which provider-defined process and where it connects to episode evidence |
| Spatial/progression | spatial_transition_candidate_lite + state_transition_dynamics_lite + progression constructs | tracking/no-tracking binary could suppress useful coordinate semantics | SPATIAL + ACTION + ACTOR + TEMPORAL where admitted | zone/channel/action-location progression/spatial transition candidate | shape, compactness, pitch control, pressure geometry, true trajectory when endpoint absent | coordinate frame, attacking direction, source semantic admission | orientation ambiguity; no fabricated destination/vector; coordinate != tracking | verify real coordinate semantics and direction on ACTIVE_MATCH | where visible progression/access occurs without pretending to know off-ball geometry |
| Aggregate/entity reconciliation | aggregate_definition_alignment_lite + player aggregate/process reconciliation | XLSX treated as non-event support rather than first-class observation surface | AGGREGATE/TABULAR + ENTITY + PROCESS + PROVENANCE/DEPENDENCY | player/team aggregate profile reconciled with process/action evidence | aggregate row as action identity; duplicate reflection as vote | explicit aggregate capability and definition alignment | aggregate-not-event; duplicate reflection; entity mismatch | bind real XLSX aggregate rows to match-local entity candidates | richer player/team profiles with denominator/context support |
| Relation/consequence | trace/consequence producers + episode consequence projection | next-event framing could narrow relation universe | RELATIONAL + TEMPORAL + OUTCOME + PROCESS + ACTOR + PROVENANCE | visible follow-up, handover, terminal support, unresolved consequence candidate | causality; possession truth; total order from same timestamp | admitted temporal relation states and dependency groups | SAME_TIME_UNORDERED; AFTER_CONFIRMED required for directional consequence; absence != counterevidence | verify current consequence inventory and ambiguous cases | what visibly followed an action/process and how often, with uncertainty preserved |
| Episode→interaction→consequence | phase_dynamics_intelligence_lane_v1 | event sequence bias | PROCESS + RELATIONAL + EPISODE + TEMPORAL + CONSEQUENCE + ACTOR/TEAM | match-local interaction/dynamics/consequence candidate | tactical adjustment, momentum truth, phase truth, causality | existing bridge; keep candidate semantics | ambiguity and fail-closed regressions | physical ACTIVE_MATCH execution of the lane | connects process participation, episode context and visible consequences into analyst-facing mechanism candidates |
| Context-conditioned intelligence | context/episode/temporal producers | context could be treated as metadata outside event engine | CONTEXT + TEMPORAL + ENTITY + AGGREGATE where admitted | score/period/role/opponent/sample-conditioned descriptive finding | causal explanation from context alone | context dimensions and comparability contract | context mismatch blocks invalid comparison | verify available match-local context; external context only when authoritative | explains when/under what declared context a visible mechanism occurred |
| Video review queue | report/finding layer future projection | video framed as absent capability rather than targeted validation destination | current ZFGV episode/time/support refs; VIDEO absent | generate review questions + episode/timestamp queue for claims that need visual confirmation | video-derived truth before review; body orientation/scanning/off-ball geometry | REVIEW_REQUIRED / VIDEO_REQUIRED route with question and withdrawal condition | no-video truth leakage; queue references must trace to evidence | use ACTIVE_MATCH timestamps/episodes as navigation only | tells analyst exactly what to inspect on video instead of rewatching blindly |
| Research/model admission | research matrix + metric/model governance | event_only_usable yes/no | construct data requirement across ACTION/AGGREGATE/PROCESS/SPATIAL/CONTEXT/EXTERNAL/TRACKING/VIDEO | method-specific eligibility; tracking-dependent components separated from nontracking components | model output as fact; imported tracking construct without tracking; causality | method_adaptation_card + required capabilities + validation/calibration | prerequisite mismatch; leakage; calibration; out-of-sample | only after real input requirements are satisfied | allows mathematically stronger models where data supports them without copying paper assumptions |
| Safe Finding/reporting | professional finding bridge + construct-specific finding adapters + report layer | event/metric evidence could dominate report gate | all admitted nontracking ZFGV surfaces through evidence graph | WHAT_VISIBLE + WHERE_WHEN + SUPPORT + COUNTEREVIDENCE + ALTERNATIVE + SAFE_MEANING + UNCERTAINTY | unsupported why/causality/intention/shape claims | traceable evidence refs, capability coverage, counterevidence state | claim ceiling, withdrawal, missing != counterevidence | human-readable ACTIVE_MATCH finding acceptance | fewer statistic dumps; more defensible professional analyst statements |

## Already recoverable in PR #355/#356

- ZFGV observation contract and capability vocabulary.
- Legacy `event_only_compatible` no longer declared as global product ceiling in metric policy.
- Spatial semantic projection without tracking fabrication.
- State-transition candidate rehabilitation.
- Provider process participation bound to actor/episode evidence.
- Phase/activity/process/episode interaction bridge.
- Visible episode consequence association.
- Progression effectiveness candidate.
- Ball security candidate.
- Recovery yield candidate.
- Penetration/terminal-access candidate without fabricated box-access truth.
- Construct-specific Safe Finding engineering envelopes.
- Full-spine wiring of the phase/dynamics lane.

## Still closed by evidence, not by event-only doctrine

The following remain closed without tracking/video or suitable external evidence:
- true team shape
- compactness
- defensive-line height
- pitch control
- true pressure geometry
- body orientation
- scanning
- true player/ball speed, acceleration or physical load
- complete off-ball option/run geometry
- coach intention or tactical plan
- causality

## Highest-leverage remaining product gap

Provider/metric admission must complete the transition from legacy compatibility shadow to explicit construct capability manifests. Provider dictionary records should either declare an observation contract or inherit a verified compatible contract from an admitted upstream metric policy. A richer nontracking construct must never fail solely because `event_only_compatible` is false; it must fail only when its actual required observation capability or evidence prerequisite is missing.

This rehabilitation must reuse `observation_contract_lite` and the existing provider dictionary producer. No parallel metric engine.
