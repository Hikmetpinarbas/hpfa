# HPFA C1 — Foundation Final Capability Snapshot V1

Status: `C1_FOUNDATION_SNAPSHOT_ASSEMBLED / CI_PENDING / ACTIVE_MATCH_REVALIDATION_REQUIRED / NOT_PRODUCTION / NOT_MERGED`

Date: 2026-08-23

## Authority

```text
product_base=main
product_base_head=105539970ffd0ca8b5d592a68e800da6057e3274
final_state_source_pr=254
final_state_source_head=a8ae2334473fb792e01c53fb0e6867e8087715c4
landing_unit=FINAL_CAPABILITY_SNAPSHOT
```

This snapshot is assembled from selected **final-state file content** at the audited #254 head. Historical PR commits are not replayed, merged chronologically or treated as product authority.

## Included Foundation capabilities

```text
01 Multiformat File Inventory
02 CSV Surface Reader
03 XLSX Surface Reader
04 XML Surface Reader
05 Provider Alias / Field Semantics
06 Provider Label / Value Semantics
07 Content Source Role Resolver
08 Cross-Format Reconciliation
09 Metric Definition Policy
10 Aggregate Definition Alignment
11 Provider Metric Dictionary
12 Triangulated Event Reflection Resolver
13 Row Nucleus Inventory
```

`metric_family_registry_lite` and `configs/metrics` are included only as current dependencies of the selected Foundation metric-definition surface.

## Explicit exclusions

This landing intentionally excludes:

```text
Evidence Atom and downstream Evidence Spine
Match-Local Identity
Semantic Role / Action Bundle
Multi-Family Taxonomy
Cross-Role Relation
Trackable Action Trace / Consequence
Visible Action Sequence / Partial Order
XLSX Entity Metric Row Projection
Aggregate Derivation Evidence Reconciliation
postmatch analyst-report surfaces
event physical-cost support
unrelated orchestrators
historical governance rewrites
#228 legacy G07 administrative coordinate exemption
#232/#234 deferred runtime side capabilities
```

The current #254 Row Nucleus behaviour is retained: no administrative coordinate exemption is inferred at that layer without an explicit reviewed semantic-role producer.

## Source-role rule

Current content-based source-role resolution is included as part of this final-state snapshot. Filename role tokens cannot admit source role or nucleus grouping.

## Claim boundary

```text
row_count_is_canonical_event_count=false
xlsx_row_is_event_identity=false
csv_xml_reflections_are_independent_votes=false
physical_action_identity_truth=false
validated_team_identity=false
validated_player_identity=false
validated_event_identity=false
sequence_truth=false
possession_truth=false
phase_truth=false
tactical_truth=false
comparison_allowed=false
claim_allowed=false
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

## Validation policy

The snapshot must pass its own exact-head CI before any further consolidation decision.

Historical ACTIVE_MATCH evidence remains evidence for historical exact heads only. This new integrated C1 head requires fresh applicable execution against:

```text
runtime/active_single_match/current
```

before ACTIVE_MATCH promotion can be claimed.

## Release status

```text
C1_FOUNDATION_SNAPSHOT_ASSEMBLED
CI=PENDING
ACTIVE_MATCH=REVALIDATION_REQUIRED
MERGE=NOT_AUTHORIZED
PRODUCTION_RELEASE=false
```
