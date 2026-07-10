# Report Output Contract Lite V1

Module id: `report_output_contract_lite_v1`

## Product purpose

Report Output Contract Lite V1 reads analyst report block candidates and decides whether each block may be included as an output candidate, routed to review, or rejected.

It is the seventh productive intelligence node in the Composite Football Intelligence line.

It does not create final report text, production report output or claim truth.

## Football value

The analyst can see which candidate blocks are safe to carry forward, which require review, and which must be rejected before any final report assembly.

## Runtime authority

Only HPFA-generated ACTIVE_MATCH artifacts may become runtime input.

Google Drive, Dropbox, Sider Scholar and donor repos are reference-only and may guide contracts, naming and tests. They do not become runtime truth.

## Required upstream

```text
analyst_report_block_composer_lite_v1
```

## Required upstream field

```text
report_block_candidate_tr
```

## Allowed outputs

```text
report output contract candidate
include block candidate decision
review block decision
reject block decision
output text candidate TR
contract counters
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
```

## Review route

```text
block_family_requires_review
```

## Upstream failure rule

If the upstream report block carries hard blocks, `decision=BLOCK_REPORT_BLOCK`, or `status=FAIL_CLOSED`, the contract must reject it.

## Test requirements

```text
test_contract_requires_report_block_id
test_contract_requires_report_block_candidate_text
test_contract_requires_upstream_claim_ceiling
test_contract_includes_valid_block_candidate
test_review_required_block_family_routes_to_review
test_failed_upstream_block_is_rejected
test_forbidden_upstream_claim_text_rejected
test_final_or_production_output_flags_rejected
test_canonical_event_count_claim_rejected
test_contract_does_not_emit_final_report_or_claim_text
test_contract_blocks_truth_language_families
test_build_contract_counts_include_review_reject
test_write_outputs_rejects_nested_phone_output
test_no_sample_match_identity_leak
```

## Release status

SMOKE_PASS target only.
Not ACTIVE_MATCH_EVIDENCE_PASS.
Not PRODUCTION_RELEASE.

PASS != RELEASE.
