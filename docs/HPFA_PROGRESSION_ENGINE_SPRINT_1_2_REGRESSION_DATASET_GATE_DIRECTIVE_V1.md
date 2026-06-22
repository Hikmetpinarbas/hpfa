# HPFA PROGRESSION_ENGINE Sprint 1.2 Regression Dataset Gate Directive V1

Project: HPFA Productization Program
Phase: Product Engineering
Release: POSTMATCH_RELEASE_0.1
Product Module: PROGRESSION_ENGINE
Node: hpfa_progression_engine_sprint_1_2_regression_dataset_gate_v1

## Purpose

Before ACTIVE_MATCH regression, the system must verify that a second valid match dataset exists.

## Current Basis

Sprint 1.1 Composite Review status is PASS_WITH_MONITORED_RISK.

The next validation is regression on another ACTIVE_MATCH dataset.

## Rule

The current ACTIVE_MATCH path is the only runtime authority unless a new valid ACTIVE_MATCH is explicitly prepared.

Old match tests, match001 folders, archived folders, quarantine folders, sample folders and reference reports are not regression truth.

## Gate Decision

If a second valid ACTIVE_MATCH dataset exists, proceed to regression.

If not, stop and request ACTIVE_MATCH switch or new dataset preparation.

## Guardrails

- Do not run regression on the same current match.
- Do not treat match_tests as authority.
- Do not use PDF/reference reports as event truth.
- Do not start Sprint 2.
- Do not write registry.
- Do not bind production.
