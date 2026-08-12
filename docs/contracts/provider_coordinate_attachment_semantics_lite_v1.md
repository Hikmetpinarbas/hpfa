# Provider Coordinate Attachment Semantics Lite V1

Status: `SPEC + EXECUTABLE CANDIDATE GATE / NOT_PRODUCTION`

## Amaç

SportsBase goalkeeper CSV yüzeyindeki `pos_x/pos_y` alanlarının, özellikle `Successful/Unsuccessful cross and pass interception attempts` satırlarında, claim-safe biçimde **event-action location candidate** olarak kullanılıp kullanılamayacağını çözmek.

Bu contract tracking truth, goalkeeper physical-position truth veya validated provider field truth üretmez.

## Kaynak rolleri

Product authority:

- current `provider_alias_field_semantics_lite_v1`;
- current `provider_label_value_semantics_lite_v1`;
- current `row_nucleus_inventory_lite_v1`;
- current `semantic_role_action_bundle_candidates_lite_v1`;
- current `coordinate_frame_precondition_lite_v1`.

Donor/reference support only:

- HP-Motor SportsBase CSV structural readers;
- HP-Engine SportsBase ingest/provider adapters;
- Dropbox `SPORTSBASE_SURFACE_DICTIONARY_v1`;
- Dropbox `SPORTSBASE_CSV_XML_XLSX_READING_PROTOCOL_v1`;
- Google Drive SportsBase/event ontology records;
- public SportsBase material.

Method: `ADAPT_NOT_COPY`.

## Epistemic separation

```text
raw pos_x/pos_y field
!= validated provider coordinate definition

same row actor label
!= goalkeeper physical-position truth

event-action location candidate
!= tracking location

outcome-stratified support pooling
!= event fusion
```

## Field basis

Primary field gate requires exact current product mapping:

```text
csv.pos_x -> event.start_x_candidate
csv.pos_y -> event.start_y_candidate
mapping_status=EXACT_RULE_CANDIDATE
alias_reliability=HIGH
source_role=GOALKEEPER_SURFACE_CANDIDATE
```

This produces only:

`EVENT_START_LOCATION_CANDIDATE_SUPPORTED`

It does not set `validated_semantics=true`.

## Interception admission

Both exact reviewed labels must resolve to the same action subtype:

```text
Successful cross and pass interception attempts
  action_family=INTERCEPTION
  action_subtype=CROSS_OR_PASS_INTERCEPTION
  object_action_family=PASS_OR_CROSS
  outcome=SUCCESS

Unsuccessful cross and pass interception attempts
  action_family=INTERCEPTION
  action_subtype=CROSS_OR_PASS_INTERCEPTION
  object_action_family=PASS_OR_CROSS
  outcome=FAILURE
```

Required per admitted bundle:

- `source_role=GOALKEEPER_SURFACE_CANDIDATE`;
- `bundle_status=PASS`;
- coordinate present;
- CSV/XML required aligned row support;
- unique action-bundle id;
- zero exact PASS/CROSS object-action surface overlap;
- zero overlapping-window + same-coordinate PASS/CROSS object-action overlap.

If all gates pass, output may state:

`EVENT_ACTION_LOCATION_CANDIDATE_SUPPORTED`

and:

`goalkeeper_interception_primary_direction_anchor_candidate_allowed=true`

This is candidacy for a downstream coordinate-frame contract only. It is not attack-direction truth.

## Outcome pooling

SUCCESS and FAILURE rows may be counted together only as unique support rows for the same exact action subtype when both exact label semantics are present.

```text
outcome_stratified_support_pooling_allowed=true
event_fusion_allowed=false
```

No two rows become one event. No canonical event identity is created.

## Negative control

`Shots saved` is retained as a reflection control. Exact SHOT surface overlap demonstrates that goalkeeper-labelled rows can carry object-action reflection locations, so same-row actor association alone is never sufficient.

## Fail-closed rules

- missing field mapping -> attachment unresolved;
- token/fuzzy label semantics -> no promotion;
- review-required action bundle -> excluded from primary admission;
- missing CSV/XML row support -> no promotion;
- exact PASS/CROSS reflection -> no promotion;
- same-coordinate overlapping PASS/CROSS reflection -> no promotion;
- match-surface binding mismatch -> `FAIL_CLOSED`;
- nested phone output -> `nested_phone_output_directory_rejected`;
- sample identity hardcoding forbidden.

Mandatory test:

`test_no_sample_match_identity_leak`

## Claim boundary

```text
coordinate_attachment_is_validated_provider_truth=false
coordinate_is_goalkeeper_physical_position_truth=false
coordinate_frame_is_validated_provider_truth=false
attack_direction_is_validated_truth=false
progression_truth=false
line_break_truth=false
canonical_event_count=UNKNOWN
production_release=false
```

Refs #238, #236, #226, PR #237.
