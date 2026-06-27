# HPFA Permission Spine Closure & Donor Depth Sprint V1

Status: PLAN_ONLY / REVIEW_REQUIRED

## Purpose

This sprint converts the latest GitHub-focused deepening scan into a product execution plan.

The scan shows HPFA has moved beyond an "missing modules" phase. Several deepening modules now exist in the product repo as contracts, modules and tests. The main problem is no longer discovery. The problem is binding these nodes to ACTIVE_MATCH evidence, release ledger, claim gate and football output audit.

## Core Product Judgment

HPFA should not sprint toward a full report engine yet.

The correct sprint is:

```text
implementation pending
-> ACTIVE_MATCH evidence
-> status ledger
-> downstream permission
-> claim/report opening
```

## Current Product Level

HPFA is now:

```text
ACTIVE_MATCH evidence-producing product-engineering repo
```

Not yet:

```text
one-command professional postmatch intelligence release
production release
```

## ACTIVE_MATCH Evidence Anchors

Modules already reported as ACTIVE_MATCH_EVIDENCE_PASS in the governance matrix include:

- ACTIVE_MATCH Analyst Report Lite V1
- Canonical Event Lite V1
- Reference Document Ingest Lite V1
- Surface Inventory Interpretation Gate Lite V1
- Team Binding Lite V1
- Event Identity Resolution Gate Lite V1
- Event Physical Cost Surface Lite V1
- Primary Event Surface Gate Lite V1
- Metric Family Registry Lite V1
- Fitness Signal PDF Support Lite

Claim boundary remains:

- canonical_event_count = UNKNOWN
- deduplicated_event_count = UNKNOWN
- event_count_claim_allowed = false

## Implementation-Pending High-Value Nodes

The following nodes are high-value because they are already present as contract/module/test candidates and now need ACTIVE_MATCH closure:

1. Source Mapping Contract Lite V1
2. Source Conflict Registry Lite V1
3. Primary Surface Review Resolution Lite V1
4. Event State Transition Verifier Lite V1
5. Minimum Viable Context Lite V1
6. Event Window Builder Lite V1
7. Active Match Identity Guard Lite V1 evidence ledger closure
8. Football Time Foundation Lite V1

## Why These Nodes Matter

### Event State Transition Verifier Lite V1

Moves HPFA from row/action volume toward visible event-order plausibility.

Allowed:

- transition-plausibility candidate
- visible event-family order issue

Blocked:

- complete event truth
- possession truth
- phase truth
- sequence truth
- player/referee error truth
- tactical truth

### Minimum Viable Context Lite V1

Enforces the rule:

```text
No context, no analyst sentence.
```

Required context surfaces:

- minute or time bucket
- team label
- action family
- zone/channel candidate
- previous/next visible action family when order is available
- source confidence

### Event Window Builder Lite V1

Moves HPFA from match-wide volume toward episode/window intelligence.

Questions it can support:

- Which visible action families appear together inside a bounded window?
- Where is the window concentrated?
- Does the window contain terminal action surface?
- Does the window contain loss/recovery/restart surface?
- Is the window dense enough for later signal or sequence analysis?

## R1 Execution Order

1. Source Mapping Contract Lite ACTIVE_MATCH run
2. Source Conflict Registry Lite ACTIVE_MATCH run
3. Primary Surface Review Resolution Lite ACTIVE_MATCH run
4. Event State Transition Verifier Lite ACTIVE_MATCH run
5. Minimum Viable Context Lite ACTIVE_MATCH run
6. Event Window Builder Lite ACTIVE_MATCH run
7. Active Match Identity Guard evidence ledger closure
8. Football Time Foundation Lite implementation

## R2 Permission Spine Hardening

9. downstream_permission_manifest_v1
10. identity_review_resolution_lite_v1
11. gk_taxonomy_source_role_reconciliation evidence closure
12. transition_blocker_router_v1
13. context_sentence_permission_gate_v1
14. event_window_density_gate_v1

## R3 Metric / Evidence / Claim Depth

15. metric_contract_registry_hardening_v1
16. metric_readiness_report_v1
17. proxy_metric_guard_v1
18. evidence_bundle_schema_lite_v1
19. falsification_surface_lite_v1
20. claim_eligibility_gate_lite_v1
21. forbidden_scope_router_v1

## R4 Pattern / Observation Depth

22. observation_registry_lite_v1
23. observation_requirement_router_v1
24. support_threshold_router_lite_v1
25. mechanism_candidate_registry_lite_v1
26. treatment_hint_blocker_v1
27. safe_observation_phrase_rewriter_v1

## R5 Output / Release Depth

28. evidence_card_renderer_v1
29. analyst_reading_surface_compressor_lite_v1
30. football_output_audit_lite_v1
31. release_decision_writer_v1
32. runtime_audit_hash_ledger_v1
33. professional_postmatch_report_renderer_lite_v1

## Donor Adaptation Decisions

### HP-Motor metric schema

Adapt into:

- metric_contract_registry_hardening_v1
- metric_readiness_report_v1
- proxy_metric_guard_v1
- minimum_sample_size_gate_v1
- metric_validation_manifest_v1
- metric_citation_relation_router_v1

Rule:

Metric passport does not produce football conclusion.

### HP-Motor claim schema

Adapt into:

- evidence_bundle_schema_lite_v1
- falsification_surface_lite_v1
- forbidden_scope_router_v1
- claim_dimension_risk_router_v1
- claim_eligibility_gate_lite_v1
- evidence_card_renderer_v1

Rule:

Claim runtime remains closed until eligibility and output audit exist.

### HP-Engine observation / mechanism / threshold assets

Adapt into:

- observation_registry_lite_v1
- observation_requirement_router_v1
- support_threshold_router_lite_v1
- mechanism_candidate_registry_lite_v1
- treatment_hint_blocker_v1
- safe_observation_phrase_rewriter_v1

Rule:

Observation and mechanism outputs are candidates. Treatment hints are blocked until human/claim review.

### HP-PROJELERI gate policy

Adapt into:

- schema_drift_gate_lite_v1
- cross_file_reconciliation_gate_lite_v1
- aggregate_validation_gate_lite_v1
- sparse_data_gate_lite_v1
- golden_deviation_gate_lite_v1
- runtime_audit_hash_ledger_v1

Rule:

Advanced gates harden data quality, source conflict, aggregate validation and release audit. They do not unlock football truth.

## Non-Negotiable Claim Rules

- No canonical event count from raw rows.
- No deduplicated event truth from duplicate clusters.
- No possession truth before possession gate.
- No phase truth before phase gate.
- No sequence truth before sequence gate.
- No metric truth from metric readiness.
- No mechanism truth from observation registry.
- No treatment instruction without human/claim review.
- No production release from PASS.

## Analyst-Facing Target

The analyst-facing system must show:

- which surface supports the reading
- what event-order confidence exists
- which context is sufficient
- which window or sequence is only candidate
- which metric is only readiness or proxy
- which sentence can enter the report
- which claim is blocked

## Sprint Exit Criteria

This sprint can close only when:

1. R1 implementation-pending nodes produce ACTIVE_MATCH execution output.
2. Each node writes engineering evidence.
3. Each node writes analyst evidence.
4. Each node has normalized status.
5. Downstream permission is explicit.
6. Claim boundaries remain closed unless explicitly opened by a later gate.
7. Football Output Audit is not bypassed.

## Status

PLAN_ONLY / REVIEW_REQUIRED.

No production release claim.
