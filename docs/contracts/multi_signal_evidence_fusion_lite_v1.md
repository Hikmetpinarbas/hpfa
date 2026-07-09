# Multi-Signal Evidence Fusion Lite V1

Module id: `multi_signal_evidence_fusion_lite_v1`

## Product purpose

Multi-Signal Evidence Fusion Lite V1 reads candidate-only composite evidence packets and converts packet contents into explicit evidence relation records.

It is the second productive intelligence node in the Composite Football Intelligence line.

It does not build a football claim, safe sentence or analyst report. It only marks how evidence refs relate to the packet.

## Football value

The analyst can see whether evidence inside a packet supports, qualifies, explicitly contradicts, complements or contextualizes a later argument.

Important distinction:

```text
low shot volume after high access does not automatically contradict the access argument.
It qualifies the reading and opens alternative scenarios such as shot timing, shot angle, shot selection or opponent setup at shot moment.
```

Example product reading:

```text
right_channel_access → SUPPORTS
low_shot_volume → QUALIFIES
same_construct_opposite_direction with contradiction_basis → CONTRADICTS
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
QUALIFIES
CONTRADICTS
COMPLEMENTS
CONTEXTUALIZES
ABSTAINS
```

## Contradiction rule

`CONTRADICTS` is reserved for explicit same-construct or same-window conflict with a declared contradiction basis.

Generic terminal limitation signals such as low shot volume, low box entry, weak terminal action volume or high loss cost should not become contradiction by default. They are `QUALIFIES` unless the upstream packet explicitly declares contradiction basis.

## Upstream identity rule

Every upstream composite packet must carry a stable `packet_id`.

The fusion layer must not synthesize order-dependent packet identities for missing upstream packet IDs. Missing `packet_id` fails closed with `composite_packet_required_fields_missing`.

## Allowed outputs

```text
fusion relation record
support relation count
qualifier relation count
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
READY_FOR_ARGUMENT_WITH_QUALIFIER
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
test_missing_packet_id_blocks_fusion_identity
test_fusion_records_signal_sources
test_fusion_detects_support_relation
test_low_shot_volume_qualifies_not_contradicts_by_default
test_explicit_contradiction_requires_basis
test_fusion_does_not_emit_claim_text
test_fusion_preserves_candidate_only_claim_ceiling
test_causal_truth_upstream_output_blocks_fusion
test_no_tactical_truth
test_write_outputs_rejects_nested_phone_output
test_no_sample_match_identity_leak
```

## Release status

SMOKE_PASS target only.
Not ACTIVE_MATCH_EVIDENCE_PASS.
Not PRODUCTION_RELEASE.

PASS != RELEASE.
