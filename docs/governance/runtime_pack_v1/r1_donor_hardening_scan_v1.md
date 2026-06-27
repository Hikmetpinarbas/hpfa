# R1 Donor Hardening Scan V1

Status: PLAN_ONLY / REVIEW_REQUIRED

Linked issue: #87

## Purpose

This scan re-checks donor repositories after the current HPFA product state improved.

Goal is not to copy donor code. Goal is to identify which donor concepts can harden HPFA R1 permission spine, P2C Event-Time-Space Binder, Metric Readiness, Evidence Bundle and Claim Gate work.

Rule: ADAPT_NOT_COPY.

## Repository Role Reminder

- hpfa: product repo and executable module authority.
- HP-Motor: metric contract, claim schema, provider/canonicalization donor.
- HP-Engine: observation, mechanism, threshold and claim-runtime donor.
- HP-PROJELERI: governance and advanced gate donor.

Only ACTIVE_MATCH runtime outputs may become runtime evidence.

## Donor Finding 1: HP-Motor Metric Spec Schema

Source donor:

```text
Hikmetpinarbas/HP-Motor
hp_motor/contracts/schemas/metric_spec.schema.json
```

Relevant donor elements:

- required fields: metric_id, version, full_name, outputs, data_requirements, impl, scopes
- outputs with type and optional range
- data_requirements.required_fields
- data_requirements.optional_fields
- data_requirements.minimum_sample_size
- derivation.level
- derivation.requires_signals
- derivation.requires_metrics
- derivation.fallbacks
- dimensions.dimension
- dimensions.inference_type = direct / proxy / composite
- dimensions.evidence_strength
- validation.tests with calibration / discrimination / sanity / benchmark
- citations relation: definition / method / benchmark / limitation

HPFA adaptation:

Create or harden:

1. metric_contract_registry_hardening_lite_v1
2. metric_readiness_report_lite_v1
3. proxy_metric_guard_lite_v1
4. minimum_sample_size_gate_lite_v1
5. metric_validation_manifest_lite_v1

Claim boundary:

- Metric Family Registry can stay registry-only.
- Metric Contract Registry must not compute metric truth.
- Metric Readiness may only say READY / DEGRADED / BLOCKED / REVIEW_REQUIRED.
- Proxy metrics must be labeled proxy and carry evidence_strength.

## Donor Finding 2: HP-Motor Analysis Claim Schema

Source donor:

```text
Hikmetpinarbas/HP-Motor
hp_motor/contracts/schemas/analysis_claim.schema.json
```

Useful donor elements:

- claim_id
- scope
- summary
- claims
- provenance
- created_at
- claim.text
- claim.dimension
- claim.evidence
- claim.confidence
- claim.falsification
- claim.status
- evidence_type: primary_raw / primary_derived / secondary_reference / video_support / annotation
- source_type: csv / xml / xlsx / pdf / docx / txt / video / api / manual
- fields_used
- time_window
- value_excerpt
- uncertainty.level
- confidence.score
- confidence.coverage
- falsification tests: unit_check / schema_check / counterfactual / sensitivity / benchmark / drift

Risk elements:

The donor schema includes scopes and dimensions that are unsafe for HPFA event-only truth, including:

- video_analysis
- body_orientation_analysis
- positional_analysis
- intent
- physical
- psychological
- neurological
- somatotype

HPFA adaptation:

Create:

1. evidence_bundle_schema_lite_v1
2. falsification_surface_lite_v1
3. forbidden_scope_router_lite_v1
4. blocked_dimension_router_lite_v1
5. claim_eligibility_gate_lite_v1

Claim boundary:

- evidence bundle is allowed.
- falsification surface is allowed.
- confirmed claim status is blocked until explicit claim gate.
- video/body/intent/psychological dimensions route to BLOCKED or TRACKING_VIDEO_REQUIRED.

## Donor Finding 3: HP-Engine Claim Runtime Shape

Source donor:

```text
Hikmetpinarbas/HP-Engine
HP_ENGINE/claim/live/claim_runtime_v2.py
```

Relevant donor pipeline:

```text
generate_observations
-> generate_mechanisms
-> generate_diagnoses
-> consolidate_claims
```

Runtime inputs include:

- sequences
- patterns
- metrics_base
- metrics_team
- metrics_context
- observation_registry
- mechanism_registry
- diagnosis_registry
- thresholds
- consolidation_rules

HPFA adaptation:

Do not import claim runtime directly.

Use the shape only:

```text
observation candidate
-> mechanism candidate
-> diagnosis candidate
-> claim consolidation candidate
```

But HPFA must insert gates:

```text
source authority gate
minimum context gate
event window gate
metric readiness gate
support threshold gate
claim eligibility gate
football output audit
```

Create:

1. observation_candidate_registry_lite_v1
2. mechanism_candidate_registry_lite_v1
3. support_threshold_router_lite_v1
4. diagnosis_threshold_blocker_lite_v1
5. safe_observation_phrase_rewriter_lite_v1
6. treatment_hint_blocker_lite_v1

Claim boundary:

- Observation candidate can exist.
- Mechanism candidate can exist only after support threshold.
- Diagnosis truth is blocked.
- Treatment hints are blocked until human/claim review.
- Claim consolidation can only produce analyst-safe reading candidates.

## Donor Finding 4: Provider Mapping / Canonicalization Need

The current product scan shows Source Mapping Contract Lite exists in the product repo. Donor direction from HP-Motor/HP-Motor-main remains valuable:

- provider alias registry
- canonical target router
- required field coverage
- unmapped column preservation
- required missing rows audit
- mapping coverage score

HPFA adaptation:

Create or harden:

1. provider_alias_registry_lite_v1
2. provider_column_semantic_target_router_lite_v1
3. mapping_coverage_score_lite_v1
4. required_missing_rows_audit_lite_v1
5. unmapped_column_semantic_report_lite_v1

R1 linkage:

These should attach to Source Mapping Contract Lite before Source Conflict Registry closure.

## Donor Finding 5: Advanced Gate Extensions

HP-PROJELERI remains a governance donor even when code search is unavailable.

Priority gate concepts:

- schema drift
- cross-file reconciliation
- aggregate validation
- sparse data
- golden deviation
- audit hash ledger

HPFA adaptation:

Create:

1. schema_drift_gate_lite_v1
2. cross_file_reconciliation_gate_lite_v1
3. aggregate_validation_gate_lite_v1
4. sparse_data_gate_lite_v1
5. golden_deviation_gate_lite_v1
6. audit_hash_ledger_lite_v1

R1 linkage:

These gates harden Source Conflict Registry, Aggregate Validation Binder, Football Output Audit and Runtime Evidence Chain Closure.

## Updated Priority Decision

The most valuable donor transfer is not more report language.

The highest-value transfer is:

```text
Metric passport + Evidence bundle + Falsification surface + Provider mapping coverage + Support threshold routing
```

## Updated R1/R2 Product Order

### R1A: Source permission closure

1. Source Mapping Contract Lite ACTIVE_MATCH closure
2. provider_alias_registry_lite_v1
3. mapping_coverage_score_lite_v1
4. Source Conflict Registry Lite ACTIVE_MATCH closure
5. schema_drift_gate_lite_v1
6. cross_file_reconciliation_gate_lite_v1
7. aggregate_validation_gate_lite_v1

### R1B: Runtime context closure

8. Primary Surface Review Resolution Lite closure
9. Identity Review Resolution check
10. GK Taxonomy Reconciliation check
11. Event State Transition Verifier closure
12. Minimum Viable Context closure
13. Event Window Builder closure
14. Football Time Foundation implementation

### R2A: Metric and claim readiness

15. metric_contract_registry_hardening_lite_v1
16. metric_readiness_report_lite_v1
17. minimum_sample_size_gate_lite_v1
18. proxy_metric_guard_lite_v1
19. evidence_bundle_schema_lite_v1
20. falsification_surface_lite_v1
21. support_threshold_router_lite_v1
22. claim_eligibility_gate_lite_v1

### R2B: Analyst-facing reasoning

23. observation_candidate_registry_lite_v1
24. mechanism_candidate_registry_lite_v1
25. safe_observation_phrase_rewriter_lite_v1
26. treatment_hint_blocker_lite_v1
27. analyst_reading_surface_compressor_lite_v1
28. evidence_card_renderer_lite_v1
29. football_output_audit_lite_v1
30. postmatch_analyst_report_lite_active_match_execution

## Non-Negotiable Claim Rules

- No event count truth from row totals.
- No deduplicated event count truth from duplicate-risk clusters.
- No possession truth before possession gate.
- No phase truth before phase gate.
- No sequence truth before sequence gate.
- No mechanism truth before claim gate and football output audit.
- No treatment instruction from donor mechanism registry.
- No video/body/intent/psychological claim from event-only runtime.

## Status

PLAN_ONLY / REVIEW_REQUIRED.

This scan does not change production status.
