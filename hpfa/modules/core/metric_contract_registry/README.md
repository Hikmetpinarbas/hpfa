# HPFA Metric Contract Registry Candidate Module

Lifecycle: COMPOSITE_CANDIDATE
Status: CANDIDATE_STUB_NOT_PRODUCTION_BOUND

## Purpose

The Metric Contract Registry defines what each HPFA metric measures, what input columns it requires, which status it can return, and whether it can support evidence only or a higher-level claim after later gates.

## Football Product Translation

This module is the metric passport office.

Before a metric can appear in a match report, this module checks whether the metric has a valid identity, required data columns, calculation rule, degraded-state policy and confidence record.

## Runtime Rule

This module must not read Google Drive or Dropbox at runtime.

Drive, Dropbox and Scholar material can support offline notes, contracts and policy design, but released code must run from the package itself.

## Current Scope

Candidate-only files:

- contracts/metric_contract_schema_v1.json
- src/metric_registry_loader.py
- src/metric_required_column_gate.py
- src/metric_status_policy_evaluator.py
- src/metric_definition_confidence_audit.py
- tests/test_metric_contract_registry_active_match.py

## Claim Boundary

Metric contract output is not a football conclusion.

A metric may provide evidence readiness, degraded state or abstain state. Final football language still requires Claim Gate and Football Output Audit.

## Production Status

Registry write: NO
Production binding: NO
Sprint 2: NO
ACTIVE_MATCH proof: PENDING
Portable runtime test: PENDING
