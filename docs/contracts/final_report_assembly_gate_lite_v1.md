# Final Report Assembly Gate Lite V1

Module id: `final_report_assembly_gate_lite_v1`

## Product purpose

Final Report Assembly Gate Lite V1 reads Report Output Contract Lite items and decides whether each item is eligible for a draft-report assembly candidate, must be routed to review, or must block assembly.

It does not create final report text, claim text, production report output or football truth.

## Football value

The analyst can move a report-output candidate toward draft assembly only while its evidence limits remain attached. Sequence-derived prose cannot detach from the exact supporting trace cohort, dependency state, robustness, uncertainty or withdrawal condition that made the prose admissible.

## Runtime authority

Only HPFA-generated ACTIVE_MATCH artifacts may become runtime input. External reference sources do not become runtime truth.

## Required upstream

```text
report_output_contract_lite_v1
```

## Required upstream fields

```text
contract_item_id
report_block_id
inclusion_decision
claim_ceiling=report_output_contract_candidate_only
```

## Sequence assembly lineage invariant

For:

```text
sequence_safe_finding_analyst_reading_candidate
sequence_narrative_analyst_reading_candidate
```

the assembly gate requires and preserves the existing `sequence_evidence_lineage` packet. It does not recompute evidence strength.

The packet must retain:

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
origin_claim_ceiling on the narrative path
```

Invariants:

```text
len(trace_variant_refs) == observed_support
anchor trace is a member of trace_variant_refs
missing sequence lineage => FAIL_CLOSED
missing required lineage field => FAIL_CLOSED
lineage survives assembly unchanged
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

Readable prose alone is insufficient for sequence assembly eligibility.

## Allowed outputs

```text
final report assembly candidate eligibility
ready assembly item decision
review assembly item decision
blocked assembly item decision
draft report candidate allowed flag
assembly counters
sequence evidence lineage preservation
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
READY_FOR_DRAFT_REPORT_ASSEMBLY_CANDIDATE
ROUTE_ASSEMBLY_ITEM_TO_REVIEW
BLOCK_ASSEMBLY_ITEM
```

## Hard blocks

```text
assembly_required_fields_missing
upstream_contract_item_failed_closed
unknown_inclusion_decision_rejected
included_block_missing_output_candidate
upstream_contract_forbidden_output_attempted
assembly_candidate_forbidden_language_detected
upstream_contract_claim_output_allowed
upstream_contract_final_report_allowed
upstream_contract_production_output_allowed
canonical_event_count_claim_rejected
true_action_count_claim_rejected
production_release_claim_rejected
sequence_evidence_lineage_missing
assembly_sequence_*
```

## Review route

```text
upstream_contract_item_requires_review
```

## Upstream failure rule

If the upstream contract item carries hard blocks, `status=FAIL_CLOSED`, or `inclusion_decision=REJECT_BLOCK`, the assembly gate must block it.

If the upstream contract item carries `inclusion_decision=REVIEW_BLOCK`, the assembly gate must route it to review and must not emit candidate text.

## Regression requirements

C4 must continue running the full `final_report_assembly_gate_lite/tests` suite. Sequence regressions cover exact lineage preservation, missing-lineage fail-closed behavior, cohort/support and anchor consistency, claim locks and production-code sample-identity leakage.

## Release status

SMOKE_PASS target only.
Not physical ACTIVE_MATCH acceptance.
Not PRODUCTION_RELEASE.

CI SUCCESS != physical device acceptance.
PASS != RELEASE.
