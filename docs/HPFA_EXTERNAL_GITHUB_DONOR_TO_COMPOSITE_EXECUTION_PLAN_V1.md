# HPFA External GitHub Donor To Composite Execution Plan V1

NODE: hpfa_external_github_donor_to_composite_execution_plan_v1
STATUS: PLAN_ONLY_NO_IMPLEMENTATION

## Purpose

Move the HPFA work from donor discovery toward donor to composite execution planning.

This node does not copy donor code, does not create production code, does not registry write, and does not production bind.

## Product Owner Translation

The scouting network has identified players. This node decides which player can train in which role, under which contract, before a match test.

## Correct Direction

The donor material must not be attached directly to PROGRESSION_ENGINE.

The correct spine is:

1. canonical ingest
2. data quality gate
3. phase and sequence
4. metric primitives
5. claim gate
6. registry audit
7. PROGRESSION_ENGINE contract binding
8. ACTIVE_MATCH regression
9. portable runtime test

## Donor Groups

HP-Motor donors:

- hp_motor/ingestion/normalizers.py
- hp_motor/ontology/phases.yaml
- hp_motor/segmentation/phase_tagger.py
- hp_motor/segmentation/sequences.py
- hp_motor/library/registry/metric_registry.json
- tests/test_segmentation_smoke.py

HP-Engine donors:

- engine/metrics_impl/progression.py
- HP_ENGINE/sequence/live/hp_sequence_engine.py
- HP_ENGINE/semantic_gate/live/hp_semantic_gate.py
- HP_ENGINE/semantic_gate/live/claim_runtime_v1.py
- registry/metrics_core_v1.yaml

hpfa donors:

- configs/hpfa_canon/HPFA_Canonical_Event_Schema_v0.1.yaml
- docs productization records
- runtime_evidence records

## Composite Targets

- canonical_ingest_composite_v1
- data_quality_gate_composite_v1
- phase_sequence_composite_v1
- metric_primitive_composite_v1
- claim_abstain_gate_composite_v1
- registry_audit_composite_v1
- progression_contract_binding_composite_v1

## Execution Gate

A donor can become a composite candidate only after:

1. source role is documented
2. input contract is stated
3. output contract is stated
4. claim boundary is stated
5. ACTIVE_MATCH command is defined
6. expected evidence output is defined
7. dirty authority risks are blocked

## Current Decision

PLAN_ONLY_PASS

## Next Node

hpfa_canonical_ingest_composite_candidate_spec_v1
