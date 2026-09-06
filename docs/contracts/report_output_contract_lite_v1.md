# Report Output Contract Lite V1

Module id: `report_output_contract_lite_v1`

## Product purpose

Report Output Contract Lite V1 reads analyst report block candidates and decides whether each block may be included as an output candidate, routed to review, or rejected.

It does not create final report truth, production report output or new football evidence.

## Football value

The analyst can carry a readable sequence finding toward report output without losing which exact traces support it, which counterexamples challenge it, whether support is dependent, how robust it is, what remains uncertain, and which evidence change would require withdrawal.

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
```

The exact supporting trace cohort must remain count-consistent with `observed_support`. A readable report block is not allowed to detach from its evidence lineage.

## Allowed outputs

```text
report output contract candidate
include block candidate decision
review block decision
reject block decision
output text candidate TR
contract counters
sequence evidence lineage
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
sequence_lineage_origin_claim_ceiling_missing
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
