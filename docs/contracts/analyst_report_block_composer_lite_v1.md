# Analyst Report Block Composer Lite V1

Module id: `analyst_report_block_composer_lite_v1`

## Product purpose

Analyst Report Block Composer Lite V1 reads Turkish safe sentence candidates and creates analyst report block candidates.

It is the sixth productive intelligence node in the Composite Football Intelligence line.

It does not create final report text, production report output or claim truth.

## Football value

The analyst can receive a report-block candidate that keeps the safe sentence intact and adds a report-block wrapper.

## Runtime authority

Only HPFA-generated ACTIVE_MATCH artifacts may become runtime input.

Google Drive, Dropbox, Sider Scholar and donor repos are reference-only and may guide contracts, naming and tests. They do not become runtime truth.

## Required upstream

```text
safe_argument_router_tr_lite_v1
```

## Required upstream field

```text
safe_sentence_candidate_tr
```

Legacy alias-only input is not enough for this composer. The standard HPFA key is required.

## Allowed outputs

```text
analyst report block candidate TR
block family
block language
claim ceiling
report output contract readiness candidate
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
READY_FOR_REPORT_OUTPUT_CONTRACT_CANDIDATE
BLOCK_REPORT_BLOCK
```

## Hard blocks

```text
safe_sentence_required_fields_missing
upstream_safe_sentence_failed_closed
upstream_safe_sentence_forbidden_output_attempted
upstream_safe_sentence_claim_output_allowed
upstream_safe_sentence_report_language_allowed
upstream_safe_sentence_not_allowed
safe_sentence_candidate_required
report_block_forbidden_language_detected
```

## Upstream failure rule

If the upstream safe sentence record carries hard blocks, `decision=BLOCK_SAFE_SENTENCE`, or `status=FAIL_CLOSED`, the composer must fail closed. A failed safe sentence must never become a report block candidate.

## Test requirements

```text
test_report_block_requires_safe_sentence_id
test_report_block_requires_standard_safe_sentence_key
test_report_block_requires_upstream_claim_ceiling
test_report_block_composes_candidate_tr
test_failed_upstream_safe_sentence_blocks_report_block
test_forbidden_upstream_output_blocks_report_block
test_report_block_does_not_emit_final_report_or_claim_text
test_report_block_blocks_truth_language_families
test_report_block_avoids_forbidden_fragments
test_write_outputs_rejects_nested_phone_output
test_no_sample_match_identity_leak
```

## Release status

SMOKE_PASS target only.
Not ACTIVE_MATCH_EVIDENCE_PASS.
Not PRODUCTION_RELEASE.

PASS != RELEASE.
