# HPFA PROGRESSION_ENGINE Sprint 1.2 Regression Dataset Gate REVIEW_REQUIRED V1

Project: HPFA Productization Program
Phase: Product Engineering
Release: POSTMATCH_RELEASE_0.1
Product Module: PROGRESSION_ENGINE
Node: hpfa_progression_engine_sprint_1_2_regression_dataset_gate_v1
Status: REVIEW_REQUIRED

## Evidence

- gate_table: hpfa_progression_engine_sprint_1_2_regression_dataset_gate_v1.tsv
- line_count: 397
- byte_size: 79609
- sha256: 0994615e945cdc73d0a15b74032cb57a4efa8de574b93159792c749ba2f491ed

- summary: hpfa_progression_engine_sprint_1_2_regression_dataset_gate_v1_summary.txt
- line_count: 17
- byte_size: 815
- sha256: 89a081065e33e858cedbe982e63af3790566d15f9ad1b4f9804a7ce972aaa393

## Decision

POTENTIAL_DATASET_FOUND_BUT_NOT_ACTIVE_MATCH_AUTHORITY

## Counts

- eligible_now_count: 0
- review_needed_count: 19
- total_scanned_count: 396

## Rule

Only a prepared ACTIVE_MATCH can be regression authority.

match_tests, match001, archive, quarantine, sample and reference surfaces are not regression truth.

## Current Meaning

PROGRESSION_ENGINE cannot proceed to real regression yet. Potential datasets exist, but none is currently authorized as second ACTIVE_MATCH authority.

## Next Node

hpfa_progression_engine_sprint_1_2_active_match_switch_authorization_v1

## Guardrails

- Do not run regression on the same current match.
- Do not use match_tests as authority.
- Do not use PDFs or reference reports as event truth.
- Do not start Sprint 2.
- Do not write registry.
- Do not bind production.
