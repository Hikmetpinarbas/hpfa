# Triangulated Event Reflection Resolver Lite V1

Status: RESEARCH_HARDENING_IMPLEMENTED_CI_PENDING
Module id: `triangulated_event_reflection_resolver_lite_v1`
Claim safety: `SERIALIZATION_EQUIVALENCE_EVIDENCE_ONLY`

## Purpose

Audit whether CSV and XML event-like surfaces for the same source role are exact visible-field serializations of one another before downstream row-nucleus and multi-label action-bundle logic is allowed to interpret them.

This module does **not** create physical-action identity, canonical event identity, true event counts, deduplicated event truth, sequence truth or independent-source votes.

## Scope

Event-like serialization surfaces admitted here:

```text
CSV
XML
TSV when present as a delimited diagnostic surface
```

XLSX statistical workbooks are outside this resolver's event-like serialization role. They remain aggregate candidate / reconciliation surfaces and cannot override event-like surface evidence.

## Exact visible-field fingerprint

CSV and XML rows are compared within the same source role using the exact-normalized visible fields:

```text
provider_row_id
start
end
code
team candidate when present
action semantic label
half
pos_x
pos_y
source_role
```

Numeric formatting normalization is allowed, for example `10.0 == 10`. Text whitespace/case normalization is allowed.

The resolver must **not** use time-proximity buckets, minute buckets or coordinate buckets to establish serialization equivalence.

Different semantic labels sharing the same start/end/coordinate anchor remain distinct semantic rows at this layer. Their possible interpretation as one physical on-ball action belongs to a downstream `resolved multi-label on-ball action bundle candidate` layer and requires its own contract/gates.

`start/end` are preserved as visible temporal fields. This module does not promote them to physical action onset, physical duration or total-order truth.

## Source roles

CSV/XML pairing is performed separately for generic source roles derived from input metadata/file identity:

```text
PLAYER
TEAM
GOALKEEPER
```

Missing, ambiguous or multiple CSV/XML members for a role remain review-required rather than being arbitrarily paired.

## Exact duplicate reflections

Same-suffix files with identical SHA-256 content are recorded as exact duplicate reflections. They do not add a second copy of surface-row volume.

Different paths with identical content are not automatically data conflicts.

## Pair states

```text
EXACT_VISIBLE_FIELD_MULTISET_EQUIVALENCE
VISIBLE_FIELD_SERIALIZATION_DISCREPANCY
PAIRING_REVIEW_REQUIRED
```

`EXACT_VISIBLE_FIELD_MULTISET_EQUIVALENCE` means only that the admitted visible-field row multisets match after permitted formatting normalization.

It does **not** prove:

```text
same physical action identity
same upstream-origin truth
canonical event identity
independent provider confirmation
complete event stream
```

Therefore CSV and XML are not promoted to independent votes by this resolver.

## Outputs

Flat phone outputs only:

```text
triangulated_event_reflection_resolver_lite_v1.json
triangulated_event_reflection_resolver_lite_v1.txt
```

Key evidence fields include:

```text
surface_file_count
unique_surface_file_count
duplicate_surface_file_reflection_count
surface_row_count
reflection_group_count
single_surface_group_count
multi_surface_group_count
serialization_role_audit_count
serialization_exact_role_count
serialization_discrepancy_role_count
serialization_pairing_review_role_count
serialization_role_audits
reflection_group_examples
```

Per-role audits expose CSV/XML surface-row totals, exact matched row count, discrepancy count and bounded discrepancy examples.

## Claim boundary

Always fail closed:

```text
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
deduplicated_event_count=UNKNOWN
physical_action_identity_truth=false
same_upstream_origin_truth=false
reflection_group_truth=false
action_count_claim_allowed=false
independent_source_vote_allowed=false
claim_safety=SERIALIZATION_EQUIVALENCE_EVIDENCE_ONLY
```

## Allowed analyst/engineering language

```text
surface rows
exact visible-field CSV/XML serialization equivalence
serialization discrepancy
exact duplicate reflection
semantic row reflection
requires downstream action-bundle validation
```

## Forbidden promotions

```text
validated action count
true event count
canonical event count
complete event stream
CSV and XML independently confirm the action
same upstream origin proven
physical action proven
```

## Required tests

```text
test_groups_same_action_across_surfaces
test_exact_csv_xml_multiset_equivalence
test_nearby_time_or_coordinate_is_not_bucket_merged
test_multi_label_same_anchor_is_not_collapsed_into_one_action
test_duplicate_same_content_file_is_reflection_not_extra_volume
test_xml_group_text_labels_map_to_canonical_fields
test_keeps_surface_rows_separate_from_candidate_groups
test_counts_and_claims_remain_fail_closed
test_flat_outputs
test_no_sample_match_identity_leak
```

Phone-output policy remains delegated to the shared output-root validator; nested user-visible output directories must remain rejected by the upstream output-root contract.
