# Aggregate Derivation Evidence Reconciliation Lite V1

## Status

`SMOKE_PASS / CURRENT_HEAD_CI_SUCCESS / ACTIVE_MATCH_REVALIDATION_REQUIRED / REVIEW_REQUIRED / NOT_PRODUCTION / NOT_MERGED`

This contract implements the discovery boundary recorded in Issue #230. It does not
produce G16 PASS, provider-definition truth, metric release, comparison permission,
canonical event truth, or production release.

## Purpose

Reconcile one observed XLSX aggregate value with exact row/evidence-level semantic
occurrences inside the same match-local entity/scope without manufacturing provider
definition truth.

The product must preserve three independent evidence dimensions:

```text
observed arithmetic evidence
!= exact derivation lineage evidence
!= reviewed provider-definition evidence
```

The node produces **G16 recheck admission evidence** only.

## Product authority and dependencies

Executable product authority remains the current `hpfa` producer stack. Runtime truth
remains `runtime/active_single_match/current`.

Required upstream product payloads:

```text
xlsx_entity_metric_row_projection_lite_v1
+ evidence_atom_inventory_lite_v1
+ match_local_identity_candidates_lite_v1
+ provider_label_value_semantics_lite_v1
+ aggregate_definition_alignment_lite_v1
→ aggregate_derivation_evidence_reconciliation_lite_v1
→ G16 recheck admission
```

Dependency roles:

- `xlsx_entity_metric_row_projection_lite_v1`: observed aggregate value plus exact
  XLSX file/sheet/source-row provenance;
- `evidence_atom_inventory_lite_v1`: unique row/evidence occurrence candidates and
  source lineage;
- `match_local_identity_candidates_lite_v1`: current non-null match-surface binding
  and evidence-atom-to-entity candidate bindings;
- `provider_label_value_semantics_lite_v1`: exact reviewed label/action/outcome
  vocabulary eligibility; label-profile volumes are never entity occurrence counts;
- `aggregate_definition_alignment_lite_v1`: definition candidate, provider/version,
  aggregate label, semantic contract, independence status, and provider-definition
  evidence state.

Donor repositories and external documents remain `DONOR_SUPPORT` or
`REFERENCE_ONLY` under `ADAPT_NOT_COPY`.

## Input authority gates

The implementation must fail closed or block G16 recheck when any critical authority
condition fails.

Required checks:

1. all payload module IDs are exact expected module IDs;
2. no required upstream payload is `FAIL_CLOSED`;
3. `canonical_event_count=UNKNOWN` and `production_release=false` are preserved;
4. `match_local_identity_candidates_lite_v1.match_surface_binding_id` is non-empty;
5. the evidence-atom and identity payloads carry the same match-surface binding;
6. ACTIVE_MATCH execution requires the resolved runtime path to end with
   `runtime/active_single_match/current`;
7. ACTIVE_MATCH runner must verify exact expected branch and exact 40-hex head SHA;
8. moved/wrong head, wrong runtime authority, or incompatible current-run lineage
   blocks runtime evidence;
9. user-visible phone output is flat under `/sdcard/Download/HPFA` or
   `/storage/emulated/0/Download/HPFA`; nested output is rejected with
   `nested_phone_output_directory_rejected`.

## Candidate-only XLSX to match-local entity alignment

XLSX row identity fields are not validated identity. They may only form an
`entity_scope_candidate` after a deterministic exact candidate gate.

### Comparison-key contract

For XLSX `team_raw_candidate` and `player_raw_candidate`:

1. preserve raw values unchanged in provenance;
2. convert to string only for comparison-key derivation;
3. trim and collapse whitespace;
4. casefold;
5. Unicode NFKD normalize;
6. remove combining marks;
7. replace each non `[a-z0-9]` run with `_`;
8. collapse repeated `_` and trim leading/trailing `_`.

The derived keys are comparison candidates only. They are not global identity keys.

### Entity admission

For an XLSX row to receive an actor-level entity scope candidate:

- source role must be compatible with the aggregate-definition candidate;
- the normalized XLSX team key must match exactly one
  `TEAM_IDENTITY_CANDIDATE_BOUND` team candidate;
- `(team_normalized_key, actor_normalized_key)` must match exactly one
  `ACTOR_IDENTITY_CANDIDATE_BOUND` actor candidate;
- the actor candidate must belong to the admitted team candidate;
- numerator and denominator evidence atoms must independently bind to that exact
  actor/team candidate and the required source role;
- the current non-null match-surface binding must be preserved on every admitted
  support record.

Forbidden joins:

```text
fuzzy name matching
substring name matching
shirt-number-only matching
provider-ID-only identity promotion
cross-team alias fallback
first-match-wins ambiguity resolution
```

Zero entity matches or more than one eligible match produces:

```text
SCOPE_ALIGNMENT_REVIEW_REQUIRED
G16_RECHECK_BLOCKED
```

This gate does not elevate identity:

```text
validated_player_identity=false
validated_team_identity=false
identity_scope=MATCH_LOCAL_CANDIDATE_ONLY
```

## Exact occurrence support

`provider_label_value_semantics_lite_v1.provider_label_records[].surface_row_volume`
is profiling evidence and must never be used as an actor/entity numerator or
denominator.

Occurrence counts come only from unique evidence atoms after exact semantic and
identity gates.

For the current `sportsbase_pass_completion_candidate_v1` registry candidate, the
minimum exact numerator contract is:

```text
source_role=PLAYER_SURFACE_CANDIDATE
normalized_label=passes accurate
action_family_candidates=[PASS]
outcome_candidates=[SUCCESS]
mapping_statuses contains EXACT_REVIEWED_CANDIDATE
identity_binding.decision_state=ACTOR_IDENTITY_CANDIDATE_BOUND
```

The exact failure component is:

```text
source_role=PLAYER_SURFACE_CANDIDATE
normalized_label=inaccurate passes
action_family_candidates=[PASS]
outcome_candidates=[FAILURE]
mapping_statuses contains EXACT_REVIEWED_CANDIDATE
identity_binding.decision_state=ACTOR_IDENTITY_CANDIDATE_BOUND
```

The numerator is the count of unique admitted numerator evidence-atom IDs.
The denominator is:

```text
unique admitted numerator atom IDs
+ unique admitted failure-component atom IDs
```

An evidence-atom ID may contribute at most once to one component for one definition
candidate. Duplicate source reflections already represented by one evidence atom do
not regain independent count weight here.

Reject from derivation support:

- token fallback;
- unknown/conflicted mapping;
- generic PASS family without exact label/outcome contract;
- wrong action subtype or outcome;
- wrong source role;
- wrong entity binding;
- wrong match-surface binding;
- administrative/context/reference atoms;
- missing evidence-atom ID;
- duplicate evidence-atom ID in the same component;
- one evidence atom claimed by mutually incompatible numerator and denominator-only
  components.

## Observation scope

The first implementation is match-file aggregate reconciliation, not per-90, phase,
period, rolling-window, or possession reconciliation.

Required safe scope labels:

```text
entity_scope_candidate = match-local actor identity candidate ID
observation_scope_candidate = MATCH_FILE_AGGREGATE_TO_VISIBLE_OCCURRENCE_SCOPE_CANDIDATE
```

All admitted occurrence support for an entity is collected across the visible match
surface. Player minutes may be preserved as XLSX row evidence but must not be used to
invent per-90 or playing-time denominators in this node.

If a future aggregate definition declares a different scope, it requires an explicit
versioned scope contract before admission.

## Aggregate-value admission

The aggregate value comes only from the row-aligned XLSX metric cell whose
`raw_metric_label` exactly equals the definition candidate aggregate label.

Required cell conditions:

```text
value_admitted=true
formula without cached value=false
raw value preserved
value kind preserved
number format preserved
percent-header candidate preserved
```

Numeric `0` is observed zero. String `-`, `N/A`, blank, and null are not converted to
numeric zero.

## Zero denominator

Zero denominator is explicit and never silently coerced.

Required states include:

```text
ZERO_DENOMINATOR
NONZERO_DENOMINATOR
DENOMINATOR_UNRESOLVED
```

If denominator is zero:

- no arithmetic percentage is computed;
- observed string `-` remains a visible aggregate-surface value;
- observed numeric zero remains observed numeric zero but does not make the
  derivation computable;
- `observed_arithmetic_status=ARITHMETIC_CANDIDATE_NOT_COMPUTABLE`;
- provider-definition evidence remains a separate dimension.

## Arithmetic representation and visible precision

For percentage candidates the implementation must preserve both:

```text
exact_ratio_candidate = numerator / denominator
arithmetic_percentage_candidate = exact_ratio_candidate * 100
```

No arbitrary epsilon or provider rounding tolerance may be invented.

### Observed XLSX number-format evidence

The XLSX row projection preserves the visible cell `number_format`. When a supported
format deterministically exposes display precision, the node may compare:

1. the observed raw XLSX numeric value rendered at the observed format precision;
2. the computed exact ratio rendered at the same observed format precision.

For V1 the only display-format rule admitted for arithmetic comparison is the exact
simple percentage family:

```text
0%
0.0%
0.00%
...
```

The number of zeroes after the decimal point declares visible decimal precision.
Unsupported, compound, locale-dependent, conditional, color-coded, scientific, or
custom formats do not receive guessed display semantics.

The observed-format comparison is XLSX display evidence only. It is **not provider
rounding truth**.

Always report raw delta separately:

```text
provider_rounding_delta_candidate = observed_numeric_ratio - exact_ratio_candidate
```

The field name is retained for compatibility with Issue #230, but its claim ceiling is
`OBSERVED_NUMERIC_DELTA_CANDIDATE_ONLY` until reviewed provider rounding rules exist.

Recommended arithmetic states:

```text
ARITHMETIC_CANDIDATE_REPRODUCED
ARITHMETIC_CANDIDATE_MISMATCH
ARITHMETIC_CANDIDATE_NOT_COMPUTABLE
```

`ARITHMETIC_CANDIDATE_REPRODUCED` may be supported by exact numeric equality or exact
supported observed-display-format equality. The method used must be explicit in an
`arithmetic_comparison_method` field.

## Derivation lineage

`DERIVATION_LINEAGE_CANDIDATE_COMPLETE` requires all of:

- exact definition candidate;
- admitted row-aligned aggregate cell;
- admitted entity scope candidate;
- exact numerator semantic contract;
- exact denominator semantic contract;
- unique numerator support evidence-atom IDs;
- unique denominator support evidence-atom IDs;
- identity binding for every support atom to the same actor/team candidate;
- current non-null match-surface binding on identity/atom support;
- no contradictory support or component collision.

Anything less remains:

```text
DERIVATION_LINEAGE_REVIEW_REQUIRED
```

Arithmetic reproduction alone cannot complete derivation lineage when support IDs or
scope bindings are missing.

## Provider-definition evidence

Provider-definition evidence remains controlled by the aggregate-definition registry
and reviewed provider evidence gate.

Required states:

```text
PROVIDER_DEFINITION_REVIEWED_CANDIDATE
PROVIDER_DEFINITION_REQUIRED
```

Do not upgrade `provider_definition_unverified` from arithmetic agreement, same-label
agreement, same-provider cross-format support, public generic metric formulas, donor
code, or analyst inference.

Same-provider XLSX and CSV/XML evidence remains:

```text
NON_INDEPENDENT_SAME_PROVIDER
```

## G16 recheck admission

V1 separates execution success from G16 recheck admission.

`G16_RECHECK_ADMITTED` requires at minimum:

- scope alignment candidate admitted;
- aggregate value admitted or an explicit zero-denominator/non-numeric surface state
  that is reviewable without coercion;
- exact semantic support contract located;
- derivation lineage complete enough for deterministic G16 re-evaluation;
- no hard block;
- no contradictory entity/component support.

Provider-definition evidence may still be `PROVIDER_DEFINITION_REQUIRED` after recheck
admission. Therefore:

```text
G16_RECHECK_ADMITTED != G16_PASS
```

Otherwise:

```text
G16_RECHECK_BLOCKED
```

## Required record output

Each aggregate-definition/entity reconciliation record must expose at least:

```text
reconciliation_record_id
definition_id
provider_id
provider_version
match_surface_binding_id
source_role
entity_scope_candidate
team_identity_candidate_id
actor_identity_candidate_id
observation_scope_candidate
xlsx_row_projection_id
xlsx_relative_path
xlsx_source_sha256
xlsx_sheet_name
xlsx_source_row_number
aggregate_label
aggregate_value_observed
aggregate_value_kind
aggregate_number_format
numerator_semantic_contract
denominator_semantic_contract
numerator_support_record_ids
denominator_support_record_ids
numerator_observed_candidate
denominator_observed_candidate
zero_denominator_state
exact_ratio_candidate
arithmetic_percentage_candidate
arithmetic_comparison_method
observed_display_value_candidate
computed_display_value_candidate
provider_rounding_delta_candidate
observed_arithmetic_status
scope_alignment_status
derivation_lineage_status
provider_definition_evidence_status
independence_status
g16_recheck_admission
hard_block_hits
review_hits
```

Top-level output must also include counts by status, current binding, runtime evidence
state, hard/review hits, and claim boundary.

## Required tests

Minimum deterministic and negative coverage:

1. exact numerator/denominator semantics admitted;
2. wrong action subtype rejected;
3. wrong outcome rejected;
4. wrong source role rejected;
5. wrong entity rejected;
6. zero entity match blocks scope;
7. ambiguous entity match blocks scope;
8. fuzzy alias is not accepted;
9. provider-ID-only join is not accepted;
10. wrong match binding rejected;
11. missing denominator support;
12. zero denominator with string `-` remains not-computable;
13. zero denominator with numeric zero remains not-computable;
14. numeric zero is distinct from missing;
15. exact numeric arithmetic reproduction;
16. observed `0%` display-precision reproduction without arbitrary epsilon;
17. unsupported number format does not invent rounding semantics;
18. arithmetic mismatch;
19. raw numeric delta preserved;
20. duplicate evidence-atom ID cannot inflate count;
21. contradictory component support blocks recheck;
22. absent provider definition preserves `PROVIDER_DEFINITION_REQUIRED`;
23. same-provider independence promotion rejected;
24. label-profile `surface_row_volume` cannot be used as entity count;
25. runtime head mismatch rejected by runner;
26. nested phone output rejected;
27. `test_no_sample_match_identity_leak`.

## Engineering evidence vs analyst evidence

A real ACTIVE_MATCH run must produce two separate audit surfaces.

Engineering evidence reports:

- exact branch/head;
- runtime authority;
- prerequisite module statuses;
- module execution result;
- test result;
- output paths and package integrity;
- hard/review hits;
- G16 recheck admission counts.

Analyst evidence reports only visible, claim-safe match-surface findings such as:

> Row-level exact pass-success and pass-failure evidence for an admitted match-local
> entity candidate can/cannot reproduce the observed XLSX percentage at the visible
> XLSX precision. Provider definition review remains a separate evidence question.

Do not state player quality, dominance, tactical intention, possession truth,
progression truth, or provider-definition truth.

## Claim boundary

```text
arithmetic_reproduction_is_provider_definition_truth=false
arithmetic_reproduction_is_metric_truth=false
count_parity_is_definition_equivalence=false
same_provider_is_independent_confirmation=false
entity_scope_candidate_is_validated_identity=false
aggregate_equivalence_truth=false
metric_value_release_allowed=false
comparison_allowed=false
claim_allowed=false
canonical_event_count=UNKNOWN
production_release=false
```
