# HPFA GitHub Canonical Layout Plan V1

Project: HPFA Productization Program
Node: hpfa_github_canonical_layout_plan_v1
Status: PASS_PLAN_ONLY

GitHub is the canonical product repository target. Runtime proof remains in Termux ACTIVE_MATCH execution.

This node is plan-only. It does not relocate files, remove files, open branches, or promote code.

## Target Layout

- repo root: README, pyproject, license, changelog
- hpfa: product package, engines, modules, composites, claim safety, io, utils
- configs: canon config, release policies, claim policies
- runtime_templates: portable folder templates only
- tools: release, doctor, run and maintenance scripts
- ops: bootstrap and maintenance operations
- tests: unit, integration, active match tests
- docs: productization, architecture, decisions, release notes, directives
- runtime_evidence: execution proof and audit records
- archive: legacy reference material
- restricted_not_packaged: unsafe or non-canonical material

## Progression Engine Target

Target product path:
hpfa/modules/postmatch/progression_engine/

Expected minimum contents:
- README
- input contract
- output contract
- progression composite implementation
- claim safety boundary
- active match contract test
- release note

Evidence remains under:
runtime_evidence/postmatch_release_0_1/progression_engine/

## Current Finding

The repository contains packaging root material, productization documents, runtime evidence, release wrapper material and older imported structures. This is acceptable for transition, but not final commercial layout.

## Next Node

hpfa_github_progression_engine_canonicalization_v1
