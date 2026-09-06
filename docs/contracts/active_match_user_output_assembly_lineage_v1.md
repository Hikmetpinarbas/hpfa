# ACTIVE_MATCH User Output Assembly Lineage V1

## Owner

Existing producer: `hpfa/modules/core/active_match_spine_runner/src/user_output_bundle.py`.

This contract rehabilitates the current user-output producer. It does not add a parallel report, narration, evidence, sequence or export engine.

## Purpose

`HPFA_ANALYST_REPORT.txt` is a user-facing projection. Human readability must not bypass the final report assembly gate or weaken evidence lineage.

## Admission invariants

1. User-facing C4 analyst text may be sourced only from an `assembly` record with:
   - `status=SMOKE_PASS`
   - `assembly_decision=READY_FOR_DRAFT_REPORT_ASSEMBLY_CANDIDATE`
   - `draft_report_candidate_allowed=true`
   - a non-empty `assembly_item_candidate_tr`.
2. `safe_sentence`, `report_block`, or `output_contract` text is not independent authority for publication in the user bundle. A downstream assembly rejection must suppress earlier text.
3. Sequence-derived block families must retain a complete `sequence_evidence_lineage` package before they can enter `HPFA_ANALYST_REPORT.txt`.
4. Sequence lineage must preserve at minimum:
   - `trace_family_refs`
   - exact `trace_variant_refs`
   - `observed_support`
   - `dependency_summary`
   - `robustness_summary`
   - `uncertainty`
   - `withdrawal_condition`
   - `upstream_claim_ceiling`
   - `origin_claim_ceiling` for narrative sequence blocks.
5. Exact trace cohort cardinality must equal `observed_support`, and the anchor family ref must remain inside the supporting trace cohort.
6. Missing or inconsistent sequence lineage is not converted into readable prose; the candidate is suppressed at this presentation boundary.
7. Presentation may preserve or lower evidence strength. It may never increase it.

## Claim boundary

- recurrence is not tactical-pattern truth;
- context difference is not causality or coaching adaptation;
- dependent projections are not independent support;
- `NO_VISIBLE_FOLLOWUP` is not failure;
- tracking/video-dependent shape, pressure, intent, physical-load or off-ball claims remain unavailable without their evidence class.

## Claim locks

`canonical_event_count=UNKNOWN`

`true_action_count=UNKNOWN`

`production_release=false`

CI success is engineering evidence only and is not physical ACTIVE_MATCH acceptance.

## Regression obligations

- blocked final assembly must suppress an earlier safe sentence;
- admitted sequence assembly text must preserve exact trace/dependency/robustness/uncertainty/withdrawal lineage in the analyst report;
- support/cohort mismatch must suppress the sequence candidate;
- missing withdrawal condition must suppress the sequence candidate;
- claim locks must remain present in the user-facing report and bundle manifest;
- no sample match/team/player identity may be introduced into production code.
