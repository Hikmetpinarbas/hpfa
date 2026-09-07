# Report Output Contract Lite V1

Module id: `report_output_contract_lite_v1`

## Product purpose

Report Output Contract Lite V1 reads analyst report block candidates and decides whether each block may be included as an output candidate, routed to review, or rejected.

It does not create final report truth, production report output or new football evidence.

## Football value

The analyst can carry a readable sequence finding toward report output without losing which exact traces support it, which counterexamples challenge it, whether support is dependent, how robust it is, what remains uncertain, which audited null/context checks qualify the interpretation, and which evidence change would require withdrawal.

For match-story blocks, process accounting must also remain bounded by the exact admitted narrative cohort. Process counters are descriptive bookkeeping only; they are not independent evidence counts.

## Runtime authority

Only HPFA-generated ACTIVE_MATCH artifacts may become runtime input.

Google Drive, Dropbox, academic sources and donor repos are reference-only. They do not become runtime truth.

## Required upstream

```text
analyst_report_block_composer_lite_v1
```

## Required upstream field

```text
report_block_candidate_tr
```

## Sequence report lineage

For block families:

```text
sequence_safe_finding_analyst_reading_candidate
sequence_narrative_analyst_reading_candidate
```

the output contract must preserve and validate:

```text
trace_family_refs
trace_variant_refs
counterevidence_refs
dependency_summary
robustness_summary
uncertainty
withdrawal_condition
observed_support
upstream_claim_ceiling
origin_claim_ceiling  # required on narrative path
null_contrast_summary # preserve and revalidate when present
context_variations    # preserve and revalidate when present
```

The exact supporting trace cohort must remain count-consistent with `observed_support`. A readable report block is not allowed to detach from its evidence lineage.

When `null_contrast_summary` is present, the contract must preserve it exactly as audited evidence and require `claim_strengthened=false`. Any evaluated null contrast must also preserve all of the following exact locks and finite-simulation provenance:

```text
claim_ceiling=UNCORRECTED_MATCH_LOCAL_NULL_CONTRAST_CANDIDATE_ONLY
multiple_testing_corrected=false
significance_claim_allowed=false
tactical_pattern_truth_allowed=false
causality_allowed=false
simulation_count=<positive integer>
empirical_upper_tail_resolution=1/(simulation_count+1)
finite_simulation_resolution_only=true
withdrawal_condition=<non-empty audited null withdrawal condition>
```

An uncorrected upper-tail probability is not a significance claim, does not establish tactical-pattern truth, and does not establish causality. Its finite Monte Carlo resolution must remain explicit and mathematically consistent with the exact simulation count; the contract does not invent a minimum simulation threshold or upgrade resolution into evidence quality. A version-skewed or stronger null claim ceiling fails closed rather than being normalized upward.

When `context_variations` are present, each baseline/comparison trace reference must remain inside the exact supporting trace cohort. `chronology_direction_claimed`, `causality_claimed`, `tactical_adaptation_claimed`, and `coach_intention_claimed` must remain false. Observed cohort variation does not establish causal or tactical adaptation truth.

Claim-ceiling lineage is vocabulary-bound, not merely non-empty:

```text
sequence_safe_finding_analyst_reading_candidate:
  upstream_claim_ceiling=DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY
  origin_claim_ceiling=<absent>

sequence_narrative_analyst_reading_candidate:
  upstream_claim_ceiling=DEFEASIBLE_MATCH_LOCAL_SEQUENCE_NARRATIVE_ONLY
  origin_claim_ceiling=DEFEASIBLE_MATCH_LOCAL_SEQUENCE_FINDING_ONLY
```

Any stronger, unknown, version-skewed, or unexpected claim-ceiling value fails closed. In particular an exact trace cohort may not legitimize a tactical-pattern, causal, coach-intention, sequence-truth, or production-truth escalation.

## Match-story accounting lineage

For `match_story_analyst_reading_candidate`, the output contract must preserve and revalidate:

```text
source_narrative_ids
process_narrative_count
recurrent_process_count
robust_recurrent_process_count
counterevidence_bearing_process_count
context_sensitive_process_count
null_evaluated_process_count
unique_trace_refs
unique_trace_ref_count
shared_trace_refs_across_processes
nominal_support_sum
nominal_support_is_independent_evidence_count=false
cross_process_support_independence_proven=false
withdrawal_condition
upstream_claim_ceiling=DEFEASIBLE_MATCH_LOCAL_PROCESS_STORY_ONLY
```

Accounting invariants:

```text
all process counters are non-negative integers and booleans are forbidden as integer evidence
process_narrative_count == len(unique(source_narrative_ids))
each subprocess counter <= process_narrative_count
robust_recurrent_process_count <= recurrent_process_count
unique_trace_ref_count == len(unique(unique_trace_refs))
nominal_support_sum >= unique_trace_ref_count
shared_trace_refs_across_processes subset-of unique_trace_refs
```

These counters describe admitted process-story bookkeeping only. They do not establish independent physical actions, tactical truth, chronology, causality, or production truth.

## Allowed outputs

```text
report output contract candidate
include block candidate decision
review block decision
reject block decision
output text candidate TR
contract counters
sequence evidence lineage
match story evidence lineage
```

## Blocked outputs

```text
claim text
final report text
production report output
tactical truth
dominance truth
control truth
coach intention truth
off-ball truth
pitch-control truth
causal truth
quality truth
sequence truth
organism truth
canonical event count claim
true action count claim
production release claim
null-derived significance claim
null-derived tactical-pattern truth
null-derived causality claim
null multiple-testing-correction promotion
null claim-ceiling escalation
null finite-simulation resolution loss or inflation
context-derived causality claim
context-derived tactical adaptation claim
match-story process accounting inflation
boolean-as-integer match-story accounting
```

## Decision states

```text
INCLUDE_BLOCK_CANDIDATE
REVIEW_BLOCK
REJECT_BLOCK
```

## Hard blocks

```text
report_block_required_fields_missing
upstream_report_block_failed_closed
upstream_report_block_forbidden_output_attempted
upstream_report_block_claim_output_allowed
upstream_report_block_production_output_allowed
upstream_report_block_final_output_allowed
report_block_forbidden_language_detected
canonical_event_count_claim_rejected
true_action_count_claim_rejected
production_release_claim_rejected
sequence_lineage_trace_family_refs_missing
sequence_lineage_trace_variant_refs_missing
sequence_lineage_observed_support_invalid
sequence_lineage_trace_cohort_support_mismatch
sequence_lineage_anchor_not_in_trace_cohort
sequence_lineage_dependency_summary_missing
sequence_lineage_robustness_summary_missing
sequence_lineage_uncertainty_missing
sequence_lineage_withdrawal_condition_missing
sequence_lineage_upstream_claim_ceiling_missing
sequence_lineage_upstream_claim_ceiling_mismatch
sequence_lineage_origin_claim_ceiling_missing
sequence_lineage_origin_claim_ceiling_mismatch
sequence_lineage_unexpected_origin_claim_ceiling
sequence_lineage_null_contrast_summary_invalid
sequence_lineage_null_contrast_claim_strengthened
sequence_lineage_null_contrast_claim_ceiling_mismatch
sequence_lineage_null_contrast_multiple_testing_lock_breach
sequence_lineage_null_contrast_significance_lock_breach
sequence_lineage_null_contrast_tactical_truth_lock_breach
sequence_lineage_null_contrast_causality_lock_breach
sequence_lineage_null_contrast_simulation_count_invalid
sequence_lineage_null_contrast_tail_resolution_mismatch
sequence_lineage_null_contrast_finite_resolution_lock_breach
sequence_lineage_null_contrast_withdrawal_condition_missing
sequence_lineage_context_variations_invalid
sequence_lineage_context_variation_invalid
sequence_lineage_context_variation_claim_lock_breach:<flag>
sequence_lineage_context_variation_trace_lineage_mismatch
match_story_lineage_source_narrative_ids_missing
match_story_lineage_unique_trace_refs_missing
match_story_lineage_<process_counter>_invalid
match_story_lineage_process_narrative_count_mismatch
match_story_lineage_<subprocess_counter>_exceeds_process_count
match_story_lineage_robust_recurrent_process_count_exceeds_recurrent
match_story_lineage_unique_trace_ref_count_invalid
match_story_lineage_unique_trace_ref_count_mismatch
match_story_lineage_nominal_support_invalid
match_story_lineage_shared_trace_refs_not_subset
match_story_lineage_nominal_support_independence_lock_breach
match_story_lineage_cross_process_independence_lock_breach
match_story_lineage_withdrawal_condition_missing
match_story_lineage_upstream_claim_ceiling_mismatch
```

## Review route

```text
block_family_requires_review
upstream_report_block_requires_review
```

Upstream `REVIEW_REQUIRED` may not silently become PASS.

## Upstream failure rule

If the upstream report block carries hard blocks, `decision=BLOCK_REPORT_BLOCK`, or `status=FAIL_CLOSED`, the contract must reject it.

## Claim locks

```text
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

## Release status

SMOKE_PASS target only.
Not physical ACTIVE_MATCH acceptance.
Not PRODUCTION_RELEASE.

CI SUCCESS != physical device acceptance.
PASS != RELEASE.
