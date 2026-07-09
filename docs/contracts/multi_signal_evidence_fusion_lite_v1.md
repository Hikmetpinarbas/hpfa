# Multi-Signal Evidence Fusion Lite V1

Module id: `multi_signal_evidence_fusion_lite_v1`

## Product purpose

Multi-Signal Evidence Fusion Lite V1 reads candidate-only composite evidence packets and converts packet contents into explicit evidence relation records.

It is the second productive intelligence node in the Composite Football Intelligence line.

It does not build a football claim, safe sentence or analyst report. It only marks how evidence refs relate to the packet.

## Football value

The analyst can see whether evidence inside a packet supports, contradicts, complements or contextualizes a later argument.

Example product reading:

```text
right_channel_access → SUPPORTS
low_shot_volume → CONTRADICTS
final_third_entry → COMPLEMENTS
window_001 → CONTEXTUALIZES
```

## Runtime authority

Only HPFA-generated ACTIVE_MATCH artifacts may become runtime input.

Google Drive, Dropbox, Sider Scholar and donor repos are reference-only and may guide contracts, naming and tests. They do not become runtime truth.

## Required upstream

```text
composite_evidence_packet_builder_lite_v1
```

## Relation types

```text
SUPPORTS
CONTRADICTS
COMPLEMENTS
CONTEXTUALIZES
ABSTAINS
```

## Allowed outputs

```text
fusion relation record
support relation count
contradiction relation count
contextualization relation count
fusion status candidate
argument consumer readiness
```

## Blocked outputs

```text
claim text
safe sentence
tactical truth
dominance truth
control truth
coach intention
off-ball truth
pitch-control truth
causal truth
canonical event count claim
```

## Decision states

```text
READY_FOR_ARGUMENT_SUPPORT
READY_FOR_ARGUMENT_WITH_CONTRADICTION
REVIEW_REQUIRED
INSUFFICIENT_FOR_ARGUMENT
BLOCK_FUSION
```

## Hard blocks

```text
composite_packet_required_fields_missing
upstream_packet_claim_ceiling_not_candidate_only
upstream_packet_forbidden_output_attempted
upstream_packet_claim_output_allowed
upstream_packet_report_language_allowed
```

## Test requirements

```text
test_fusion_requires_composite_packet
test_fusion_records_signal_sources
test_fusion_detects_support_relation
test_fusion_detects_contradiction_relation
test_fusion_does_not_emit_claim_text
test_fusion_preserves_candidate_only_claim_ceiling
test_no_tactical_truth
test_write_outputs_rejects_nested_phone_output
test_no_sample_match_identity_leak
```

## Release status

SMOKE_PASS target only.
Not ACTIVE_MATCH_EVIDENCE_PASS.
Not PRODUCTION_RELEASE.

PASS != RELEASE.
