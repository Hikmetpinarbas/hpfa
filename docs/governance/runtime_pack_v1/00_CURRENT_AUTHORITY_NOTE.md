# HPFA Runtime Pack V1 — Current Authority Note

Date: 2026-09-15
Status: `CURRENT_AUTHORITY_OVERLAY`
Reference product: single-match Postmatch
Canonical ontology: `EVENT ⊂ ZFGV`; `ZFGV != EVENT`

## Purpose

This directory contains a mixture of durable governance inputs and dated planning/evidence snapshots created during earlier HPFA development stages. File presence inside `runtime_pack_v1` does not make every file current product authority.

This note is the authority overlay for interpreting the directory. It does not rewrite historical evidence.

## Current executable-consumed governance inputs

The current `capability_closure_guard_lite` reads:

- `module_governance_matrix.tsv`
- `source_role_registry.json`
- `release_status_normalizer.json`

Their roles are bounded:

### `module_governance_matrix.tsv`

Role: discovery/lineage seed only.

A matrix row cannot create a current capability merely because its `current_status` says `ACTIVE_MATCH_EVIDENCE_PASS`, `NEXT_PRODUCT_NODE`, `SPEC_ONLY` or another historical state.

Current closure requires repository evidence such as current contract and/or implementation, and stronger decisions require current consumer, test, runtime binding and admitted ACTIVE_MATCH evidence as applicable.

`governance_status_hint` is not product truth. Historical `SUPERSEDED_BY_*` metadata may be used only when a current successor implementation independently corroborates it.

Therefore the June-era status column must not be read as the current project roadmap or current release state.

### `source_role_registry.json`

Role: source-authority vocabulary and source-role governance.

Preserve the authority distinction that ACTIVE_MATCH runtime evidence is different from repository, donor, reference and academic support. Any old Event-Only-era wording is subordinate to current ZFGV governance.

### `release_status_normalizer.json`

Role: release/status vocabulary required by current guard validation.

Status vocabulary does not prove that a particular historical module currently has that status. Current status still requires current repository/test/runtime evidence appropriate to the claim.

## Historical snapshot / planning family

Unless independently re-admitted by current product authority, the following are historical planning or evidence snapshots and MUST NOT determine the current WIP, current reference architecture or current next node:

- `next_node_decision.md`
- `development_gap_register.md`
- `surface_ontology_v1.md`
- `metric_family_ontology_v1.md`
- `permission_spine_closure_donor_depth_sprint_v1.md`
- `r1_active_match_permission_spine_closure_plan_v1.md`
- `r1_module_dependency_graph_v1.json`
- `r1_claim_permission_matrix_v1.tsv`
- `r1_analyst_evidence_contract_v1.json`
- `r1_donor_hardening_scan_v1.md`
- `donor_mining_map_v1.md`
- `metric_fusion_donor_adaptation_note.md`
- `multiversion_donor_rebuild_plan.md`
- `revolutionary_donor_transfer_pack_v1.md`
- dated self-containment / branch / phone-output audits in this directory when they describe an earlier repository state

Historical content remains valuable for lineage, prior evidence, donor provenance and regression context. It is not deleted or silently rewritten into present-tense truth.

## Current authority order

For present product direction, use fresh repository state plus current governance/frontier, including:

1. fresh `Hikmetpinarbas/hpfa` current main and current development frontier;
2. `docs/governance/HPFA_MASTER_PROJECT_DIRECTIVE_SHORT_CURRENT.md`;
3. `docs/governance/HPFA_OPERATOR_HANDOFF_CURRENT.md`;
4. `docs/governance/HPFA_ZFGV_EVENT_ONLY_RESIDUAL_AUTHORITY_LEDGER_V1.md` while the migration WIP remains open;
5. claim-specific repository / test / runtime evidence.

Open PR != main.
CI PASS != physical ACTIVE_MATCH.
Historical physical evidence does not transfer automatically to a newer head.

## ZFGV interpretation rule

Event-specific modules, contracts and historical evidence remain legitimate where their construct is genuinely ACTION/EVENT-specific.

They MUST NOT be generalized into a product-wide rule that:

- every observation is an event;
- every construct needs event identity;
- every metric/model needs an event-family prerequisite;
- every observation family must pass an event-shaped gate;
- non-event evidence is invalid merely because it lacks event fields.

Construct admission is observation-capability-specific.

Tracking/video and other physical-state claims remain separately gated. ZFGV expansion does not weaken evidence ceilings.

## Claim locks

- `canonical_event_count=UNKNOWN`
- `true_action_count=UNKNOWN`
- `production_release=false`
- `ROW != EVENT TRUTH`
- `EVENT != WHOLE OBSERVATION UNIVERSE`
- `AGGREGATE != ACTION IDENTITY`
- `MULTIFORMAT != INDEPENDENT EVIDENCE`
- `SAME TIMESTAMP != TOTAL ORDER`
- `COORDINATE != TRACKING`
- `PROCESS LABEL != COACH INTENTION`
- `RECURRENCE != CAUSALITY`
- `MODEL OUTPUT != FACT`
- `ABSENCE != COUNTEREVIDENCE`

## Release

This authority overlay is governance only.

It does not merge, release or production-bind any capability.
