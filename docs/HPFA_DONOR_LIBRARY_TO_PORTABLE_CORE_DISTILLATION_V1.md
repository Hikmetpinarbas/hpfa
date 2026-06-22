# HPFA Donor Library To Portable Core Distillation V1

NODE: hpfa_donor_library_to_portable_core_distillation_v1
STATUS: DISTILLATION_PLAN_PASS

## Purpose

Convert Google Drive and Dropbox donor-library usage into a self-contained HPFA product rule.

The product may learn from the libraries, but it must not depend on them while running.

## Product Owner Translation

The club studies the library during the week. On match day, the team plays with its own prepared match bag.

## Input Donor Libraries

Google Drive:

- product engineering decision records
- canonical layout records
- release readiness records
- system architecture and audit documents
- football analytics design and claim support documents

Dropbox:

- research archive
- source papers
- ontology and event-only references

## Distillation Rule

Drive and Dropbox knowledge can be distilled into:

- offline summaries
- contracts
- policies
- test specs
- schema notes
- claim-boundary notes
- module README material

Drive and Dropbox knowledge must not become:

- runtime dependency
- execution proof
- live connector requirement
- event truth
- production binding evidence

## Portable Core Targets

- hpfa/modules/core/canonical_ingest_engine/
- hpfa/modules/core/data_quality_gate_engine/
- hpfa/modules/postmatch/phase_engine/
- hpfa/modules/postmatch/sequence_engine/
- hpfa/modules/core/metric_primitive_library/
- hpfa/modules/core/claim_gate_engine/
- hpfa/modules/core/registry_audit_engine/

## Required Packaging Rule

A portable package must contain all required code, contracts, policies, templates and tests in the GitHub canonical tree.

Runtime must not call Google Drive or Dropbox.

## Current Discovery Result

Google Drive search confirms existing portability and productization records.
Dropbox search did not produce a direct portable runtime donor in this pass.

## Decision

DISTILLATION_PLAN_PASS

## Next Node

hpfa_canonical_ingest_composite_candidate_spec_v1
