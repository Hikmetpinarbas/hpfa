# HPFA GitHub PROGRESSION_ENGINE Contracts Plan V1

Node: hpfa_github_progression_engine_contracts_plan_v1
Status: PLAN_ONLY

## Input Contract Plan

Target:

hpfa/modules/postmatch/progression_engine/contracts/progression_input_contract_v1.json

Minimum input categories:

- ACTIVE_MATCH raw event surfaces
- event-only coordinates where available
- timestamps or ordering fields where available
- team and player identifiers where available
- no PDF-derived event truth
- no off-ball truth
- no body-orientation truth
- no coach-intention truth

## Output Contract Plan

Target:

hpfa/modules/postmatch/progression_engine/contracts/progression_output_contract_v1.json

Minimum output categories:

- progression evidence signals
- progression support context
- claim safety status
- audit notes
- no dominance claim
- no tactical truth claim
- no coach intention claim

## Claim Boundary

Progression output may support evidence-only observations.

Progression output must not directly produce tactical truth, dominance truth, or responsibility claim.

## Current Decision

Contracts can be drafted after this plan. Product implementation remains blocked until regression and portability validation.

## Next Node

hpfa_github_progression_engine_contract_stub_authorization_v1
