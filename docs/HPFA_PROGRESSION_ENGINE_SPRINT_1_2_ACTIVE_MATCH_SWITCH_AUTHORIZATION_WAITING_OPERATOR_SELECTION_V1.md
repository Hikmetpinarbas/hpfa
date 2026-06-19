# HPFA PROGRESSION_ENGINE Sprint 1.2 ACTIVE_MATCH Switch Authorization WAITING_OPERATOR_SELECTION V1

Project: HPFA Productization Program
Phase: Product Engineering
Release: POSTMATCH_RELEASE_0.1
Product Module: PROGRESSION_ENGINE
Node: hpfa_progression_engine_sprint_1_2_active_match_switch_authorization_v1
Status: WAITING_OPERATOR_SELECTION

## Evidence

- authorization_table: hpfa_progression_engine_sprint_1_2_active_match_switch_authorization_v1.tsv
- line_count: 20
- byte_size: 4715
- sha256: d41e0e3f5f6dd1cefe57b61422f353a7f7891d59fa958bc5e547ac0b007801c1

- authorization_request: hpfa_progression_engine_sprint_1_2_active_match_switch_authorization_request_v1.md
- line_count: 68
- byte_size: 4091
- sha256: 0cf09224c1b4a49c1661affdcf06108810d5fedd5e2e06d631eee764156387c2

## Decision

SECOND_ACTIVE_MATCH_CANDIDATES_REQUIRE_AUTHORIZATION

## Counts

- candidate_count: 19
- authorized_candidate_count: 0

## Current Meaning

Sprint 1.2 cannot run regression yet. Candidate paths were listed, but none is authorized as second ACTIVE_MATCH authority.

## Operator Instruction

Do not approve a candidate directly from this list. Several candidates are current ACTIVE_MATCH subfolders or non-authority runtime folders. Run candidate integrity inspection first.

## Next Node

hpfa_progression_engine_sprint_1_2_active_match_candidate_integrity_inspection_v1

## Guardrails

- Do not switch ACTIVE_MATCH without explicit operator approval.
- Do not run regression yet.
- Do not use match_tests as authority.
- Do not use current ACTIVE_MATCH subfolders as second match.
- Do not write registry.
- Do not bind production.
- Do not start Sprint 2.
