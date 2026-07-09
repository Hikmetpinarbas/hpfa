# Composite Evidence Packet Builder Lite V1

Module id: `composite_evidence_packet_builder_lite_v1`

## Product purpose

Composite Evidence Packet Builder Lite V1 is the first productive intelligence layer for combining multiple HPFA evidence surfaces before argument generation.

It does not create a football claim or report sentence. It creates a machine-readable evidence packet that later fusion, argument, evidence graph and report modules can consume.

## Football value

The analyst can see which feature, window, sequence, metric and signal references belong together before a football argument is built.

Example product reading:

```text
final_third_entry + box_entry + terminal_action_count + low_shot_volume
→ progression-to-consequence packet candidate
```

## Runtime authority

Only HPFA-generated ACTIVE_MATCH artifacts may become runtime input.

Google Drive, Dropbox, Sider Scholar and donor repos are reference-only and may guide contracts, naming and tests. They do not become runtime truth.

## Required output fields

```text
packet_id
packet_family
input_features
input_windows
input_sequences
input_metrics
supporting_signals
contradicting_signals
evidence_strength
minimum_signal_count
claim_ceiling
report_consumers
blocked_language_families
```

## Allowed outputs

```text
composite evidence packet
input reference preservation
supporting signal slot
contradicting signal slot
evidence strength candidate
fusion consumer readiness
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
canonical event count claim
```

## Decision states

```text
READY_FOR_FUSION_CONSUMER
BLOCK_PACKET
```

## Hard blocks

```text
minimum_two_sources_required
single_signal_cannot_create_composite_argument
claim_ceiling_missing
forbidden_output_attempted
```

## Test requirements

```text
test_composite_packet_requires_minimum_two_sources
test_packet_preserves_all_evidence_refs
test_packet_has_support_and_contradiction_slots
test_single_signal_cannot_create_composite_argument
test_packet_claim_ceiling_candidate_only
test_no_tactical_truth
test_no_dominance_control_language
```

## Release status

SMOKE_PASS target only.
Not ACTIVE_MATCH_EVIDENCE_PASS.
Not PRODUCTION_RELEASE.

PASS != RELEASE.
