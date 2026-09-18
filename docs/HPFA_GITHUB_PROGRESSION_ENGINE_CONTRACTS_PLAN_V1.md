# HPFA GitHub PROGRESSION_ENGINE Contracts Plan V1

Node: hpfa_github_progression_engine_contracts_plan_v1
Status: ZFGV_PLAN_ONLY

## Canonical doctrine

```text
EVENT ⊂ ZFGV
ZFGV != EVENT
```

Progression is a football construct, not an Event-Only construct. Its admission depends on the observation capabilities required by the specific progression definition.

## Input Contract Plan

Target:

hpfa/modules/postmatch/progression_engine/contracts/progression_input_contract_v1.json

Possible input categories, construct-specific:

- admitted ACTION/EVENT observations when the definition requires an action occurrence
- admitted SPATIAL observations with validated coordinate semantics / pitch frame / direction prerequisites as required
- admitted TEMPORAL observations when sequence/window meaning is required
- admitted ENTITY/ACTOR or team identity when entity attribution is required
- OUTCOME/QUALIFIER observations when success/outcome meaning is required
- AGGREGATE/TABULAR progression support when definition alignment is admitted
- EXTERNAL CONTEXT where explicitly admitted
- TRACKING/VIDEO only when physical/off-ball geometry truth is required

No observation family is globally mandatory merely because older progression work was event-shaped.

## Output Contract Plan

Minimum output categories:

- progression evidence candidate
- source/observation-family lineage
- required/admitted capability state
- progression support context
- claim ceiling / safety state
- audit notes

## Claim Boundary

Progression output may support evidence-only observations after its required semantics are admitted.

Without the required authority it must not directly produce:

- tactical truth
- dominance truth
- coach intention
- true off-ball geometry
- pitch-control truth
- causal responsibility

Coordinates alone are not tracking. Aggregate support does not create action identity. Same timestamp does not create total order.

## Current Decision

Any future implementation must begin from construct-specific ZFGV observation requirements and reuse current admission contracts before code is added.

## Next Node

No implementation node is authorized by this PLAN_ONLY record. Fresh current-product gap and consumer evidence are required first.
