# HPFA Core Canonical Ingest Donor Discovery V1

Project: HPFA Productization Program
Node: hpfa_core_canonical_ingest_donor_discovery_v1
Status: DISCOVERY_PASS_PLAN_ONLY
Primary product context: POSTMATCH_RELEASE_0.1 / PROGRESSION_ENGINE

## ZFGV Migration Authority Note — 2026-09-15

Authority status: `HISTORICAL_ONLY`
Migration classification: `GLOBAL_ERROR` for the historical product-wide ingest assumption preserved below.

This discovery record is retained for donor lineage only. It is **not** current or future-current product-wide admission authority. The historical wording that all football analysis must first pass through one canonical event table is superseded by `EVENT ⊂ ZFGV` and construct-specific observation admission.

Any future ingest implementation must be derived from the current ZFGV observation contract. ACTION/EVENT schemas may be required for ACTION/EVENT constructs that actually need them; valid ENTITY/ACTOR, TEMPORAL, SPATIAL, OUTCOME/QUALIFIER, RELATIONAL, PROCESS/PARTICIPATION, AGGREGATE/TABULAR, EXTERNAL CONTEXT, TRACKING/VIDEO or HPFA-DERIVED INTELLIGENCE must not be rejected merely because `event_id` / `event_type` or a canonical event row is absent.

Current authority lives in the current governance and observation-contract surfaces, not in this PLAN_ONLY donor record.

## Product Owner Translation

Canonical ingest is the translator that turns different match data files into one HPFA language before any football analysis is allowed.

Without this layer, PROGRESSION_ENGINE risks reading a table as if it were clean match truth when it may only be a vendor-specific or archive-specific surface.

## Authority Rule

This node is discovery only.

No donor code is promoted to product code.
No Dropbox or Google Drive source is treated as runtime proof.
No PDF is treated as event truth.
No registry write or production binding is allowed.

## Confirmed Donor Sources

### Dropbox Research Donor

A03 Ontology for Common Data Format on Football Data Analytics was found in HPFA research archive.

Use role: academic and ontology support for canonical ingest design.
Do not use role: runtime evidence or event truth.

### Google Drive Governance Donor

Product Engineering, release readiness, and Sprint 1 progression governance documents exist in Drive.

Use role: lifecycle, policy, and product decision support.
Do not use role: runtime proof.

### GitHub Code Donors

HP-Motor contains phase, sequence, registry and metric encyclopedia donors.
HP-Engine contains progression metric, sequence, semantic gate and registry donors.

Use role: inspect and adapt after gate review.
Do not use role: validated product code until ACTIVE_MATCH validation passes.

## Donor Mapping

- FCDF / CDF ontology paper: supports canonical event schema and interoperability.
- HP-Motor phase_tagger.py: supports later phase engine.
- HP-Motor phases.yaml: supports phase taxonomy.
- HP-Motor sequences.py: supports later sequence engine.
- HP-Motor metric registry material: supports registry audit.
- HP-Engine progression.py: supports metric primitive discovery.
- HP-Engine sequence engines: supports sequence behavior discovery.
- HP-Engine semantic gate material: supports claim gate discovery.

## Canonical Ingest Requirements

Minimum future skeleton:

hpfa/modules/core/canonical_ingest_engine/

Required files:

- contracts/canonical_event_input_contract_v1.json
- contracts/canonical_event_output_contract_v1.json
- src/canonicalize.py
- src/schema_loader.py
- src/authority_validator.py
- tests/test_active_match_canonical_ingest.py
- tests/test_no_drop_extras.py
- tests/test_required_gate_fail_closed.py

## Football Product Meaning

Before HPFA says anything about progression, phase, sequence or value, it must first know that the match event table is in a trusted common shape.

This is the equivalent of checking the match sheet, field, referee, ball, player IDs and clock before starting analysis.

## PASS Criteria

- canonical/schema/ontology donor candidates identified
- source authority role written
- direct copy versus adaptation separated
- runtime proof not claimed
- PROGRESSION_ENGINE not directly bound

## Decision

DISCOVERY_PASS_PLAN_ONLY

## Next Node

hpfa_core_canonical_ingest_donor_adaptation_plan_v1
