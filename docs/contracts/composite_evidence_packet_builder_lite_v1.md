# Composite Evidence Packet Builder Lite V1

Module id: `composite_evidence_packet_builder_lite_v1`

## Product purpose

Composite Evidence Packet Builder Lite V1 is the first productive intelligence layer for combining multiple HPFA evidence surfaces before argument generation.

It does not create a football claim or report sentence. It creates a machine-readable evidence packet that later fusion, argument, evidence graph and report modules can consume.

## Football value

The analyst can see which feature, window, sequence, metric and signal references belong together before a football argument is built.

The packet also separates nominal evidence volume from admitted independent support. Different files, metrics, windows or derived signals must not be treated as independent corroboration merely because their reference IDs differ.

Example product reading:

```text
final_third_entry + box_entry + terminal_action_count + low_shot_volume
→ progression-to-consequence packet candidate

6 nominal refs
→ 0 admitted independent support units
→ evidence strength remains independence-capped
```

## Runtime authority

Only HPFA-generated ACTIVE_MATCH artifacts may become runtime input.

Google Drive, Dropbox, Sider Scholar and donor repos are reference-only and may guide contracts, naming and tests. They do not become runtime truth.

## Evidence dependency / independence rule

Every evidence item may carry:

```text
provenance_root
dependency_group
independence_group
independent_support_vote
```

`independent_support_vote=true` is admissible only when all three lineage identifiers are present.

Independent-support cardinality is computed from connected components. Two admitted support records belong to the same support unit when they share any of:

```text
provenance_root
dependency_group
independence_group
```

Therefore multiple derived metrics, windows, reflections or differently named signals cannot multiply independent-support count when they remain in one shared provenance/dependency/independence lineage.

Missing lineage metadata does not mean independence. It means independence is not admitted.

`nominal_ref_count != independent_support_count` by default.

This layer does not estimate probability and does not convert support count into football truth.

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
dependency_ledger
nominal_ref_count
independent_support_count
correlated_or_unknown_support_count
provenance_root_count
dependency_group_count
independence_group_count
independence_state
evidence_strength
evidence_strength_independence_capped
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
dependency / provenance ledger candidate
independent-support inventory candidate
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
independence inferred from ref count
independence inferred from file count
probability inferred from evidence strength
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
independent_support_claim_not_proven
```

## Invariants

```text
same provenance root cannot create multiple independent votes
same dependency group cannot create multiple independent votes
same independence group cannot create multiple independent votes
duplicate/reflection references cannot multiply support by representation alone
derived evidence may share dependency groups without becoming independent evidence
missing independence metadata is not independent evidence
independent_support_count cannot promote tactical/causal/sequence truth
evidence_strength is not probability
canonical_event_count=UNKNOWN
```

## Test requirements

```text
test_composite_packet_requires_minimum_two_sources
test_packet_preserves_all_evidence_refs
test_packet_has_support_and_contradiction_slots
test_single_signal_cannot_create_composite_argument
test_packet_claim_ceiling_candidate_only
test_nominal_refs_do_not_become_independent_support_by_default
test_same_provenance_root_does_not_multiply_independent_support
test_same_dependency_group_collapses_distinct_roots
test_same_independence_group_collapses_distinct_roots_and_dependencies
test_independent_support_claim_requires_complete_lineage_metadata
test_distinct_provenance_roots_can_be_counted_without_becoming_truth_probability
test_report_scope_deduplicates_same_independence_group_across_packets
test_no_tactical_truth
test_no_dominance_control_language
test_no_sample_match_identity_leak
```

## Release status

SMOKE_PASS target only.
Not ACTIVE_MATCH_EVIDENCE_PASS.
Not PRODUCTION_RELEASE.

PASS != RELEASE.
