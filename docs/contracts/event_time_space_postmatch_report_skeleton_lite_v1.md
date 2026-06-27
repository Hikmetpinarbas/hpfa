# P2H Event-Time-Space Postmatch Report Skeleton Lite V1

Status: SPEC_ONLY / REVIEW_REQUIRED

Linked issue: #89

## Purpose

This contract defines the main skeleton of an HPFA Event-Time-Space postmatch intelligence report.

It is a reporting contract, not an execution module and not a production release.

The report must not jump from metric totals to judgement. It must route every judgement through source role, time, space, action, context, sequence, value, player-role, opponent correspondence and claim-safety layers.

## Core Sentence

```text
This report uses metrics not to produce judgement directly, but to audit claims inside event-time-space context.
```

Turkish analyst wording:

```text
Bu rapor metrikleri hüküm üretmek için değil, event-time-space bağlamında iddia denetlemek için kullanır.
```

## Required Report Sections

| No | Section | Main output | Purpose |
|---:|---|---|---|
| 1 | Source Role Map | source_role_map | CSV, XML, XLSX, PDF, missing video/tracking, methodology donor roles |
| 2 | Ingestion Audit | ingestion_audit | surface rows, event matching, missing coordinates, duplicate labels, source conflict |
| 3 | Match Thesis | executive_match_thesis | one-sentence match reading plus claim level |
| 4 | Score and Game-State Timeline | game_state_timeline | goals, turning points, score state, minute, momentum candidate |
| 5 | Event-Time-Space Fusion Table | event_time_space_fusion_table | event id, team, player, time, duration, x-y, zone, action family |
| 6 | Goal Chain Reconstruction | goal_chain_reconstruction | last 5-8 visible events before each goal |
| 7 | Phase Analysis Matrix | phase_analysis_matrix | build-up, progression, final third, transition, set-piece, defensive transition candidates |
| 8 | Zone Occupation / Action Map | zone_action_map | action concentration by zone and lane |
| 9 | Sequence Pattern Table | sequence_pattern_table | regain-to-stabilization, progression-to-turnover, turnover-to-shot, restart-to-shot candidates |
| 10 | Threat / Value Proxy Table | threat_value_proxy_table | xT candidate, VAEP-style consequence proxy, xD/threat removed proxy |
| 11 | Player Role Impact Table | player_role_impact_table | player, role, position, action value, risk, claim level |
| 12 | Opponent Correspondence Map | opponent_correspondence_map | opponent response to visible pattern candidate |
| 13 | Risk Map | risk_map | non-sustainable advantages and repeated fragility candidates |
| 14 | Claim Safety Table | claim_safety_table | evidence, inference, proxy, blocked claim, video/tracking requirement |
| 15 | Final Judgement | final_professional_judgement | safe professional conclusion after gates |

## Layer Contract

| Layer | Question | Data fields | Output | Claim level |
|---|---|---|---|---|
| Source | Which data was used for what? | file, type, role, authority | source role map | direct evidence |
| Time | When did the event happen? | start, end, duration, minute | tempo / sequence candidate | direct evidence |
| Space | Where did the event happen? | x, y, zone, lane | zone map | direct evidence |
| Action | What happened? | action_type, family, result | event family | direct evidence |
| Context | Under what state did it happen? | score_state, phase candidate, possession candidate | contextual meaning | diagnostic |
| Sequence | What came before and after? | previous_event, next_event, chain_id | pattern trace | diagnostic/proxy |
| Value | What was the consequence value? | xG, xA, xT proxy, VAEP proxy | threat/consequence | proxy |
| Player | Who affected the surface? | role, action, outcome | role impact | diagnostic |
| Opponent | What was the opponent correspondence? | opponent event chain | correspondence | diagnostic |
| Claim | How safe is the interpretation? | evidence, limitation | safe judgement | gated |

## Required Source Role Rules

CSV:
- event/action spatial candidate surface
- never canonical event count truth

XML:
- temporal/action conformance surface
- event time spine when fields exist

XLSX/PDF:
- aggregate validation/support surface
- must not replace event-chain evidence

Dropbox / Drive / donor repos / academic sources:
- methodology or report grammar support only
- never runtime truth

## Required Claim States

Allowed section-level claim states:

- direct evidence
- strong event-only diagnostic
- medium event-only proxy
- weak proxy
- context warning
- withdrawn claim
- tracking/video required
- gated

## Blocked Report Moves

The report renderer must not allow:

- metric total directly becoming final judgement
- surface row count becoming canonical event count
- duplicate label cluster becoming deduplicated event truth
- phase candidate becoming phase truth
- sequence candidate becoming sequence truth
- opponent correspondence becoming intent claim
- player role surface becoming player quality truth
- value proxy becoming causal truth
- report thesis using dominance/control/plan language without later explicit gates

## Required Renderer Checks

A future renderer must check:

1. Every section has source role fields.
2. Every judgement has a claim level.
3. Every proxy is labelled as proxy or candidate.
4. Every final judgement cites at least one upstream evidence object.
5. Any tracking/video-required statement is blocked or downgraded.
6. canonical_event_count remains UNKNOWN unless a later explicit event-count validation contract opens it.
7. event_count_claim_allowed remains false by default.
8. Output passes Football Output Audit before analyst-facing release.

## Section Dependencies

| Section | Minimum upstream evidence |
|---|---|
| Source Role Map | source_mapping_contract_lite_v1 |
| Ingestion Audit | source_mapping_contract_lite_v1; source_conflict_registry_lite_v1 |
| Event-Time-Space Fusion Table | xml_csv_temporal_spatial_binder_lite_v1 |
| Game-State Timeline | football_time_foundation_lite_v1; aggregate validation support when present |
| Goal Chain Reconstruction | event_window_builder_lite_v1; consequence attachment candidate |
| Phase Analysis Matrix | phase candidate gate |
| Sequence Pattern Table | sequence candidate gate |
| Threat / Value Proxy Table | metric_readiness_report_lite_v1; proxy_metric_guard_lite_v1 |
| Player Role Impact Table | role-based player surface interpreter gate |
| Claim Safety Table | claim_eligibility_gate_lite_v1 |
| Final Judgement | football_output_audit_lite_v1 |

## Release Status

SPEC_ONLY / REVIEW_REQUIRED.

This contract does not implement full postmatch intelligence and does not claim production release.
