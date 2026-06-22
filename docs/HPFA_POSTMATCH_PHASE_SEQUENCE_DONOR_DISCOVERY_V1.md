# HPFA Postmatch Phase Sequence Donor Discovery V1

NODE: hpfa_postmatch_phase_sequence_donor_discovery_v1
STATUS: DISCOVERY_PASS_PLAN_ONLY

## Purpose

Identify donor material for future phase and sequence engines.

## Football Product Meaning

Phase engine is the analyst eye that places each action into a match phase.

Sequence engine is the analyst eye that reads action chains instead of isolated events.

Together they prepare the context PROGRESSION_ENGINE needs before it can safely support report language.

## Confirmed GitHub Donors

HP-Motor donors:

- hp_motor/ontology/phases.yaml
- hp_motor/segmentation/phase_tagger.py
- hp_motor/segmentation/sequences.py
- hp_motor/data/6faz_map.json
- tests/test_segmentation_smoke.py

HP-Engine donors previously identified:

- HP_ENGINE/sequence/live/hp_sequence_engine.py
- HP_ENGINE/sequence/_merge_lab/.../canonical/hp_sequence_engine.py

## Local Inventory Support

The uploaded phase sequence candidate inventory contains 1145 candidate paths.

Many candidates include delete-gate, match001, archive, diagnostics, guards, nodes and registry surfaces.

These are useful as donors but not valid runtime authority.

## Future Module Targets

hpfa/modules/postmatch/phase_engine/
hpfa/modules/postmatch/sequence_engine/

Future composite:

hpfa/composites/phase_sequence_composite/

## Required Contracts

Phase output must provide phase_id or degraded_reason.
Sequence output must provide sequence_id, possession_id if available, event range, duration, start/end coordinates and split_reason.

## Claim Boundary

Allowed language:

- event is phase-tagged by event rules
- sequence has progression evidence
- sequence has degraded reason

Blocked language:

- tactical superiority
- dominance
- coach intention
- off-ball structure truth
- line-break truth without claim gate

## PASS Criteria For This Node

- donor sources identified
- phase and sequence targets separated
- old match and delete-gate surfaces are not promoted
- no implementation created
- no registry write
- no production binding

## Decision

DISCOVERY_PASS_PLAN_ONLY

## Next Node

hpfa_postmatch_phase_sequence_composite_spec_v1
