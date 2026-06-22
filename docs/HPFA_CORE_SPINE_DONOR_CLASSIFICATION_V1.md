# HPFA Core Spine Donor Classification V1

NODE: hpfa_core_spine_donor_classification_v1
STATUS: DISCOVERY_PASS_PLAN_ONLY

Input scan sizes:

- metric candidates: 2339
- claim candidates: 12687
- phase sequence candidates: 1145
- canonical candidates: 2482
- runtime risk inventory: 10710
- donor rank inventory: 12687
- core donor inventory: 12687

Aggregate:

- unique paths: 12687
- claim gate group: 9270
- canonical ingest group: 2482
- phase sequence group: 935

Review status:

- candidate review: 2009
- risk review: 1849
- runtime risk review: 8829

Product meaning:

The library is large enough to support the HPFA core spine. It should be used as donor material only. It is not ready product code.

Safe build order:

1. canonical ingest
2. data quality gate
3. phase and sequence
4. metric primitives
5. claim gate
6. registry audit
7. PROGRESSION_ENGINE contract link

Decision:

DISCOVERY_PASS_PLAN_ONLY

Next node:

hpfa_core_data_quality_gate_template_discovery_v1
