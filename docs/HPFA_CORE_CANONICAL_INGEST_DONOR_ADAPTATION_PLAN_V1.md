# HPFA Core Canonical Ingest Donor Adaptation Plan V1

Project: HPFA Productization Program
Node: hpfa_core_canonical_ingest_donor_adaptation_plan_v1
Status: PLAN_ONLY_NO_IMPLEMENTATION

Purpose: plan how donor sources will support a future HPFA canonical ingest layer.

Football product meaning: this layer is the match-data registration desk. It checks identity, clock, team, player and event structure before analyst modules use the data.

Future target module:

hpfa/modules/core/canonical_ingest_engine/

Future planned parts:

- input contract
- output contract
- source schema loader
- authority validator
- required-field gate
- row lineage
- unmapped-column preservation
- ACTIVE_MATCH-only tests

Current rules:

- donor material remains donor material
- research material remains reference support
- runtime proof must come from ACTIVE_MATCH
- PROGRESSION_ENGINE is not bound in this node
- registry write remains blocked
- production binding remains blocked

Future PASS criteria:

- ACTIVE_MATCH source converts into canonical output
- required fields are enforced
- unmapped columns are preserved
- row lineage exists
- output hash exists
- no reference material is used as event truth

Current decision:

PLAN_ONLY_PASS

Next node:

hpfa_core_data_quality_gate_template_discovery_v1
