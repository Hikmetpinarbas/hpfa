# Multi-Signal Evidence Fusion Lite V1

Module id: `multi_signal_evidence_fusion_lite_v1`

## Product purpose

Multi-Signal Evidence Fusion Lite V1 reads candidate-only composite evidence packets and converts packet contents into explicit evidence relation records.

It is the second productive intelligence node in the Composite Football Intelligence line.

It does not build a football claim, safe sentence or analyst report. It only marks how evidence refs relate to the packet and preserves admitted dependency / independence state for downstream reasoning.

## Football value

The analyst can see whether evidence inside a packet supports, qualifies, explicitly contradicts, complements or contextualizes a later argument.

The fusion layer must also preserve the distinction between nominal evidence volume and admitted independent support. Two signals with different names do not become two independent confirmations when they share a provenance root, dependency group or independence group.

Important distinction:

```text
low shot volume after high access does not automatically contradict the access argument.
It qualifies the reading and opens alternative scenarios such as shot timing, shot angle, shot selection or opponent setup at shot moment.
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

## Dependency / independence admission rule

Fusion does not trust upstream aggregate support counts. When dependency metadata is declared it normalizes the ledger and recomputes admitted support.

Independent-support cardinality is computed from connected components. Records collapse into one support unit when they share any of:

```text
provenance_root
dependency_group
independence_group
```

The dependency ledger must also be structurally bound to packet evidence. Ledger rows cannot introduce ref IDs or group memberships that are absent from the packet evidence surface. Where the packet preserves lineage on the evidence record, ledger lineage must agree with that preserved lineage.

Fusion preserves:

```text
independence_state
independent_support_count
correlated_or_unknown_support_count
dependency_group_count
provenance_root_count
independence_group_count
```

Signal relation records preserve `provenance_root`, `dependency_group`, `independence_group` and an admitted `independent_support_vote` when those fields exist upstream.

The fusion layer must fail closed if:

```text
independent support aggregates disagree with recomputed ledger values
positive independent support has no dependency ledger
ledger refs/group membership do not bind to packet evidence
preserved evidence lineage conflicts with ledger lineage
nominal ref count is promoted to independent support
packet evidence strength is promoted to probability
```

Fusion does not infer football independence from filenames, raw ref counts or metric counts.

## Allowed outputs

```text
fusion relation record
support relation count
qualifier relation count
contradiction relation count
contextualization relation count
dependency / independence state preservation
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
nominal evidence volume as independent corroboration
evidence strength as probability
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
upstream_packet_failed_closed
upstream_packet_claim_ceiling_not_candidate_only
upstream_packet_forbidden_output_attempted
upstream_packet_claim_output_allowed
upstream_packet_report_language_allowed
upstream_independent_support_count_invalid
upstream_dependency_ledger_missing
upstream_dependency_ledger_evidence_ref_binding_mismatch
upstream_dependency_ledger_lineage_binding_mismatch:*
upstream_nominal_ref_promoted_to_independent_support
upstream_evidence_strength_probability_claim_rejected
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
test_nominal_volume_does_not_become_independent_support_downstream
test_same_provenance_root_collapses_before_fusion
test_same_dependency_group_collapses_distinct_roots
test_same_independence_group_collapses_distinct_roots_and_dependencies
test_incomplete_independence_claim_fails_closed_before_argument_chain
test_fusion_rejects_nominal_ref_promotion_even_if_packet_is_forged
test_fusion_rejects_invented_ledger_refs_not_present_in_packet_evidence
test_fusion_rejects_ledger_lineage_mismatch_for_preserved_signal_record
test_report_scope_deduplicates_same_independence_group_across_packets
test_no_tactical_truth
test_write_outputs_rejects_nested_phone_output
test_no_sample_match_identity_leak
```

## Release status

SMOKE_PASS target only.
Not ACTIVE_MATCH_EVIDENCE_PASS.
Not PRODUCTION_RELEASE.

PASS != RELEASE.
