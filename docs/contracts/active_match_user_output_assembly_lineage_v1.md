# ACTIVE_MATCH User Output Assembly Lineage V1

## Owner

Existing producers:
- `hpfa/modules/core/active_match_spine_runner/src/user_output_bundle.py`
- `hpfa/modules/core/active_match_spine_runner/src/process_story_sidecar.py`

This contract rehabilitates current user-output producers. It does not add a parallel report, narration, evidence, sequence or export engine.

## Purpose

`HPFA_ANALYST_REPORT.txt` and `active_match_process_story_sidecar_v1.txt` are user-facing projections. Human readability must not bypass the final report assembly gate, weaken evidence lineage, or resurrect a stronger claim vocabulary than the final assembly admitted.

## Admission invariants

1. User-facing C4 analyst text may be sourced only from an `assembly` record with:
   - `status=SMOKE_PASS`
   - `assembly_decision=READY_FOR_DRAFT_REPORT_ASSEMBLY_CANDIDATE`
   - `draft_report_candidate_allowed=true`
   - a non-empty `assembly_item_candidate_tr`.
2. `safe_sentence`, raw `entity_story`, `report_block`, or `output_contract` text is not independent authority for publication in the user bundle/sidecar. A downstream assembly rejection must suppress earlier text.
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
   - when `state != NOT_EVALUATED`, `claim_ceiling=UNCORRECTED_MATCH_LOCAL_NULL_CONTRAST_CANDIDATE_ONLY` is mandatory;
   - `simulation_count` must be a positive non-boolean integer;
   - `empirical_upper_tail_resolution` must equal exactly `1/(simulation_count+1)` within floating-point tolerance `1e-12`;
   - `finite_simulation_resolution_only=true` is mandatory;
   - `multiple_testing_corrected=false` is mandatory;
   - `significance_claim_allowed=false` is mandatory;
   - `tactical_pattern_truth_allowed=false` is mandatory;
   - `causality_allowed=false` is mandatory;
   - `withdrawal_condition` must be non-empty.
9. Context variation is revalidated at the publication boundary. If `context_variations` is present:
   - it must be a list of objects;
   - `chronology_direction_claimed=false`;
   - `causality_claimed=false`;
   - `tactical_adaptation_claimed=false`;
   - `coach_intention_claimed=false`;
   - every baseline/comparison trace ref must remain inside the exact supporting trace cohort.
10. Match-story TXT publication may use only `match_story_analyst_reading_candidate` assembly items that remain `SMOKE_PASS`, `READY_FOR_DRAFT_REPORT_ASSEMBLY_CANDIDATE`, and `draft_report_candidate_allowed=true`. Raw synthesis `entity_stories` must never be serialized as analyst-facing story text.
11. At the match-story publication boundary, `match_story_evidence_lineage` must revalidate numeric conservation rather than trusting upstream presence:
   - `source_narrative_ids` must be a non-empty unique string cohort;
   - `process_narrative_count` must be a positive non-boolean integer exactly equal to that cohort cardinality;
   - `recurrent_process_count`, `robust_recurrent_process_count`, `counterevidence_bearing_process_count`, `context_sensitive_process_count`, and `null_evaluated_process_count` must be non-boolean integers in `0..process_narrative_count`;
   - `robust_recurrent_process_count <= recurrent_process_count`;
   - `nominal_support_is_independent_evidence_count=false`;
   - `cross_process_support_independence_proven=false`.
12. `active_match_process_story_sidecar_v1.json` is diagnostic lineage, not publication authority. It must declare:
   - `artifact_semantics=DIAGNOSTIC_INTERNAL_EVIDENCE_TRACE`;
   - `user_facing_publication_authority=false`;
   - `publication_authority_artifact=active_match_process_story_sidecar_v1.txt`;
   - `raw_entity_stories_are_publication_authority=false`;
   - `assembly_admission_required_for_user_facing_story=true`.
   The TXT sidecar must declare `artifact_semantics=USER_FACING_ASSEMBLY_ADMITTED_PROJECTION` and `user_facing_publication_authority=true`. Diagnostic JSON may retain raw intermediate evidence for audit, but no downstream consumer may treat those raw fields as analyst-facing authority.
13. Unknown, tactical, causal, production, wrong-hop, null-significance, null-tactical, null-causality, fake multiple-testing correction, wrong null ceiling, invalid simulation count, false tail resolution, finite-resolution lock breach, context-causality, context-adaptation or otherwise escalated sequence claims are suppressed and cannot become user-facing prose.
14. Missing or inconsistent sequence or match-story lineage is not converted into readable prose; the candidate is suppressed at this presentation boundary.
15. Presentation may preserve or lower evidence strength. It may never increase it.

## Claim boundary

- recurrence is not tactical-pattern truth;
- null-tail probability is a finite-simulation diagnostic whose numerical granularity is bounded by `1/(simulation_count+1)`;
- null-tail probability is not multiple-testing-corrected significance unless a separate admitted statistical contract establishes that fact;
- null contrast is not causal evidence;
- context difference is not causality or coaching adaptation;
- dependent projections are not independent support;
- process/subprocess accounting is cohort bookkeeping, not independent physical-action evidence;
- diagnostic artifact retention is not publication admission;
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
- evaluated null evidence must preserve positive `simulation_count`, exact `empirical_upper_tail_resolution=1/(simulation_count+1)`, and `finite_simulation_resolution_only=true`;
- invalid simulation count, tail-resolution mismatch, finite-resolution lock breach, null claim-strengthening, wrong null ceiling, fake multiple-testing correction, significance/tactical-truth/causality escalation, or missing null-specific withdrawal condition must suppress the sequence candidate;
- context causality/adaptation/intention/chronology escalation must suppress the sequence candidate;
- context trace refs outside the exact support cohort must suppress the sequence candidate;
- process-story TXT must publish admitted assembly text and must not publish raw synthesis story text;
- boolean accounting, process/source cohort mismatch, subprocess overflow, or `robust_recurrent > recurrent` must suppress process-story TXT publication;
- process-story JSON must remain diagnostic-only and explicitly identify the TXT artifact as publication authority;
- raw diagnostic `entity_stories` may remain auditable in JSON but must never appear in TXT without final assembly admission;
- claim locks must remain present in the user-facing report and bundle manifest;
- no sample match/team/player identity may be introduced into production code.
