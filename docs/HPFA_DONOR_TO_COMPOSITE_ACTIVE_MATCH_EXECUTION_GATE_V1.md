# HPFA Donor To Composite ACTIVE_MATCH Execution Gate V1

NODE: hpfa_donor_to_composite_active_match_execution_gate_v1
STATUS: GATE_SPEC_PLAN_ONLY

## Purpose

Define the gate that must be passed before any donor-adapted composite can be used by PROGRESSION_ENGINE.

## Product Owner Translation

This is the final training pitch before the candidate joins the match-plan group.

## Required Evidence For Any Composite Candidate

- source donor path
- adapted target path
- input contract
- output contract
- claim boundary
- ACTIVE_MATCH command
- expected output files
- output hash
- degraded mode behavior
- blocked claim examples

## ACTIVE_MATCH Rule

Only runtime/active_single_match/current or an explicitly approved second ACTIVE_MATCH can provide execution proof.

Old test match folders, archive folders, sample files, reference files and research files cannot provide execution proof.

## PASS Conditions

- command runs on ACTIVE_MATCH authority
- output files are created
- output hashes are recorded
- claim safety status is written
- degraded rows are marked
- no forbidden truth statement is emitted

## FAIL_CLOSED Conditions

- donor code runs only on sample or old match
- output depends on fixed team names
- output treats reference material as event truth
- output emits final tactical or dominance claims
- output lacks evidence files or hashes

## Decision

GATE_SPEC_PLAN_ONLY

## Next Node

hpfa_canonical_ingest_composite_candidate_spec_v1
