# Final Report Assembly Gate Lite V1

Module id: `final_report_assembly_gate_lite_v1`

## Product purpose

Final Report Assembly Gate Lite V1 reads Report Output Contract Lite items and decides whether each item is eligible for a draft-report assembly candidate, must be routed to review, or must block assembly.

It is the eighth productive intelligence node in the Composite Football Intelligence line.

It does not create final report text, claim text, production report output or football truth.

## Football value

The analyst can see which report-output contract items can safely move toward draft assembly, which items require review, and which items fail closed before any final report is produced.

## Runtime authority

Only HPFA-generated ACTIVE_MATCH artifacts may become runtime input.

Google Drive, Dropbox, Sider Scholar and donor repos are reference-only and may guide contracts, naming and tests. They do not become runtime truth.

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

## Allowed outputs

```text
final report assembly candidate eligibility
ready assembly item decision
review assembly item decision
blocked assembly item decision
draft report candidate allowed flag
assembly counters
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
```

## Review route

```text
upstream_contract_item_requires_review
```

## Upstream failure rule

If the upstream contract item carries hard blocks, `status=FAIL_CLOSED`, or `inclusion_decision=REJECT_BLOCK`, the assembly gate must block it.

If the upstream contract item carries `inclusion_decision=REVIEW_BLOCK`, the assembly gate must route it to review and must not emit candidate text.

## Test requirements

```text
test_assembly_requires_contract_item_id
test_assembly_requires_report_block_id
test_assembly_requires_upstream_claim_ceiling
test_ready_include_block_becomes_draft_assembly_candidate_only
test_review_block_routes_to_review_without_text
test_reject_block_fails_closed
test_unknown_decision_rejected
test_included_block_requires_output_candidate_text
test_forbidden_upstream_output_attempt_rejected
test_final_or_production_flags_rejected
test_forbidden_language_detected
test_canonical_event_count_claim_rejected
test_build_assembly_gate_counts_ready_review_blocked
test_write_outputs_rejects_nested_phone_output
test_build_report_and_write_outputs
test_no_sample_match_identity_leak
```

## Release status

SMOKE_PASS target only.
Not ACTIVE_MATCH_EVIDENCE_PASS.
Not PRODUCTION_RELEASE.

PASS != RELEASE.
