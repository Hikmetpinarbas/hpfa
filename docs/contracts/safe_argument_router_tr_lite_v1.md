# Safe Argument Router TR Lite V1

Module id: `safe_argument_router_tr_lite_v1`

## Product purpose

Safe Argument Router TR Lite V1 reads candidate-only evidence graph records and creates Turkish safe sentence candidates.

It is the fifth productive intelligence node in the Composite Football Intelligence line.

It does not create claim text or final report language.

## Football value

The analyst can receive a Turkish sentence candidate that preserves support, qualifier, context, counter-scenario and withdrawal information.

## Runtime authority

Only HPFA-generated ACTIVE_MATCH artifacts may become runtime input.

Google Drive, Dropbox, Sider Scholar and donor repos are reference-only and may guide contracts, naming and tests. They do not become runtime truth.

## Required upstream

```text
evidence_graph_engine_lite_v1
```

## Allowed outputs

```text
safe sentence candidate TR
sentence language
claim ceiling
blocked language scan result
report composer readiness candidate
```

## Blocked outputs

```text
claim text
final report language
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
READY_FOR_REPORT_COMPOSER_CANDIDATE
BLOCK_SAFE_SENTENCE
```

## Hard blocks

```text
graph_required_fields_missing
upstream_graph_failed_closed
upstream_graph_forbidden_output_attempted
upstream_graph_claim_output_allowed
upstream_graph_report_language_allowed
safe_sentence_forbidden_language_detected
```

## Upstream failure rule

If the upstream graph record carries hard blocks, `decision=BLOCK_GRAPH`, or `status=FAIL_CLOSED`, the safe argument router must fail closed. A failed graph must never become a sentence candidate.

## Language safety rule

The router must reject finalizing unsafe certainty, tactical truth, dominance, control, coach intention, causal truth, off-ball truth, pitch-control truth, sequence truth and organism truth language.

## Test requirements

```text
test_router_requires_graph_id
test_router_requires_nodes_edges_and_claim_ceiling
test_router_creates_safe_turkish_sentence_candidate
test_router_blocks_failed_upstream_graph
test_router_blocks_upstream_truth_output
test_router_does_not_emit_claim_text_or_report_language
test_router_blocks_truth_language_families
test_sentence_avoids_forbidden_claim_fragments
test_write_outputs_rejects_nested_phone_output
test_no_sample_match_identity_leak
```

## Release status

SMOKE_PASS target only.
Not ACTIVE_MATCH_EVIDENCE_PASS.
Not PRODUCTION_RELEASE.

PASS != RELEASE.
