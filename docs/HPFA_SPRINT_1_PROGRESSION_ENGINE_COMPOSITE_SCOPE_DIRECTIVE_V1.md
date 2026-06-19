# HPFA Sprint 1 Progression Engine Composite Scope Directive V1

PROJECT: HPFA Productization Program
RELEASE: POSTMATCH_RELEASE_0.1
SPRINT: Sprint 1
PRODUCT MODULE: PROGRESSION_ENGINE
CURRENT CAPABILITY: progression_consequence
CURRENT NODE: hpfa_sprint_1_progression_engine_composite_scope_v1

## Mission

Create a concrete candidate list and composite contract for PROGRESSION_ENGINE.

This node does not write implementation code, repair, bridge, registry write, or production binding.

## Strict Execution Sequence

1. hpfa_sprint_1_progression_engine_composite_scope_v1
2. hpfa_sprint_1_progression_engine_candidate_pool_v1
3. hpfa_sprint_1_progression_engine_composite_selection_v1
4. hpfa_sprint_1_progression_engine_active_match_execution_v1
5. hpfa_sprint_1_progression_engine_football_output_audit_v1

## Composite Scope Questions

1. What is progression?
2. Which event/action surfaces provide progression evidence?
3. How are progressive pass, carry, territory, xT, line-break and packing separated?
4. How is progression attached to consequence?
5. Progression does not directly become a claim.
6. Progression is not dominance.
7. Progression is not tactical truth.
8. Progression produces semantic/evidence surfaces only.
9. Claim Engine may use it only after evidence + context + gate.

## Output 1

hpfa_sprint_1_progression_engine_composite_scope_v1.tsv

## Output 2

hpfa_sprint_1_progression_engine_composite_contract_v1.md

## Acceptance

PASS requires:

- at least one producer candidate
- at least one consequence attachment candidate
- at least one policy/contract source
- dirty/quarantine/reference candidates separated
- ACTIVE_MATCH execution inputs specified
- no new implementation code

## Guardrails

- Progression is not dominance.
- Packing is not dominance.
- Line-break is not tactical truth.
- PDF is reference only, not event truth.
- ACTIVE_MATCH is the only runtime authority.
