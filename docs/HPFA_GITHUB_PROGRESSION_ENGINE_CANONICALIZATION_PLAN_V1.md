# HPFA GitHub PROGRESSION_ENGINE Canonicalization Plan V1

Project: HPFA Productization Program
Node: hpfa_github_progression_engine_canonicalization_v1
Status: PLAN_ONLY_NO_CODE_MOVE

## Purpose

Create a safe canonicalization plan for PROGRESSION_ENGINE inside the GitHub product repository.

This node does not move existing files, delete files, bind production, or convert evidence into product code.

## Current Product Status

PROGRESSION_ENGINE is a release candidate, not production-bound.

Sprint 1.1 Composite Review: PASS_WITH_MONITORED_RISK.

Sprint 1.2 regression is blocked until a valid second ACTIVE_MATCH dataset exists.

## Canonical Product Path

Target path:

hpfa/modules/postmatch/progression_engine/

Required structure:

- README.md
- contracts/progression_input_contract_v1.json
- contracts/progression_output_contract_v1.json
- composites/progression_consequence_composite_v1.py
- audits/claim_language_risk_policy.md
- tests/test_progression_active_match_contract.py

## Evidence Path

Runtime evidence remains under:

runtime_evidence/postmatch_release_0_1/progression_engine/

Evidence is not product code.

## Release Note Path

docs/release_notes/POSTMATCH_RELEASE_0_1_PROGRESSION_ENGINE_RC.md

## Rules

1. Do not move existing files in this node.
2. Do not delete files in this node.
3. Do not promote runtime evidence as product code.
4. Do not treat release candidate as production release.
5. Do not registry-write.
6. Do not production-bind.
7. Do not start Sprint 2.

## Acceptance Decision

Canonicalization may proceed only as skeleton planning.

Actual code promotion requires separate coordinator approval after regression and portable runtime tests.

## Next Node

hpfa_github_progression_engine_skeleton_spec_v1
