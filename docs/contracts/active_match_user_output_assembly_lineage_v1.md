# ACTIVE_MATCH User Output Assembly Lineage V1

## Owner

Existing producer: `hpfa/modules/core/active_match_spine_runner/src/user_output_bundle.py`.

This contract rehabilitates the current user-output producer. It does not add a parallel report, narration, evidence, sequence or export engine.

## Purpose

`HPFA_ANALYST_REPORT.txt` is a user-facing projection. Human readability must not bypass the final report assembly gate, weaken evidence lineage, or resurrect a stronger claim vocabulary than the final assembly admitted.

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
5. When present upstream, audited null/context evidence is part of that same lineage package and must be preserved to user output:
   - `null_contrast_summary`
   - `context_variations`.
6. Exact trace cohort cardinality must equal `observed_support`, and the anchor family ref must remain inside the supporting trace cohort.
7. Claim-ceiling vocabulary and hop order are revalidated at the user-output boundary rather than trusted by presence alone:
   - `sequence_safe_finding_analyst_reading_candidate` requires `upstream_claim_ceiling=DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY` and no `origin_claim_ceiling`;
   - `sequence_narrative_analyst_reading_candidate` requires `upstream_claim_ceiling=DEFEASIBLE_MATCH_LOCAL_SEQUENCE_NARRATIVE_ONLY` and `origin_claim_ceiling=DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY`;
   - every sequence-derived assembly item requires `claim_ceiling=final_report_assembly_candidate_only`.
8. Null contrast is revalidated at the publication boundary. If `null_contrast_summary` is present:
   - it must be an object;
   - `claim_strengthened=false` is mandatory;
   - when `state != NOT_EVALUATED`, both `significance_claim_allowed=false` and `tactical_pattern_truth_allowed=false` are mandatory.
9. Context variation is revalidated at the publication boundary. If `context_variations` is present:
   - it must be a list of objects;
   - `chronology_direction_claimed=false`;
   - `causality_claimed=false`;
   - `tactical_adaptation_claimed=false`;
   - `coach_intention_claimed=false`;
   - every baseline/comparison trace ref must remain inside the exact supporting trace cohort.
10. Unknown, tactical, causal, production, wrong-hop, null-significance, null-tactical, context-causality, context-adaptation or otherwise escalated sequence claims are suppressed and cannot become user-facing prose.
11. Missing or inconsistent sequence lineage is not converted into readable prose; the candidate is suppressed at this presentation boundary.
12. Presentation may preserve or lower evidence strength. It may never increase it.

## Claim boundary

- recurrence is not tactical-pattern truth;
- null-tail probability is not multiple-testing-corrected significance unless a separate admitted statistical contract establishes that fact;
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
- admitted narrative sequence assembly text must preserve exact trace/dependency/robustness/uncertainty/withdrawal lineage and the exact finding→narrative→assembly claim hop in the analyst report;
- admitted safe-finding sequence text must carry only the finding ceiling and no origin hop;
- support/cohort mismatch must suppress the sequence candidate;
- missing withdrawal condition must suppress the sequence candidate;
- tactical/causal/unknown upstream claim escalation must suppress the sequence candidate;
- wrong narrative origin hop must suppress the sequence candidate;
- unexpected origin claim on a safe-finding block must suppress the sequence candidate;
- wrong final assembly claim ceiling must suppress the sequence candidate;
- audited null/context lineage must be serialized into the analyst report when present;
- null claim-strengthening or significance/tactical-truth escalation must suppress the sequence candidate;
- context causality/adaptation/intention/chronology escalation must suppress the sequence candidate;
- context trace refs outside the exact support cohort must suppress the sequence candidate;
- claim locks must remain present in the user-facing report and bundle manifest;
- no sample match/team/player identity may be introduced into production code.
