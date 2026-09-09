# HPFA Metric Fusion Engine V1 — ZFGV Rehabilitation

Lifecycle: COMPOSITE_CANDIDATE  
Status: SCAFFOLD_NOT_PRODUCTION_BOUND  
Historical identifier: `Event-Only Metric Fusion Engine V1` — LEGACY_IDENTIFIER  
Runtime authority: HPFA-generated ACTIVE_MATCH artifacts only  
Claim layer: CLOSED  
Report language: CLOSED

## Purpose

The Metric Fusion Engine aligns admitted metric candidates, source surfaces, context, process/sequence outputs and metric contracts into evidence relations.

It is not a report generator and it is not a tactical truth engine.

## Canonical observation rule

The historical event-only ceiling is retired as a global product gate.

```text
event ⊂ ZFGV
required_capabilities ⊆ admitted_capabilities
```

A metric or relation may depend on ACTION/EVENT, ENTITY/ACTOR, TEMPORAL, SPATIAL, OUTCOME/QUALIFIER, RELATIONAL, PROCESS/PARTICIPATION, AGGREGATE/TABULAR, EXTERNAL CONTEXT, TRACKING/VIDEO when genuinely present, or HPFA-DERIVED INTELLIGENCE. Each construct must declare the capabilities it actually requires.

The legacy policy `policies/eventonly_metric_allowlist_v1.json` is retained for compatibility/history until runtime consumers are proven migrated. It must not become a future global product ceiling. The ZFGV replacement contract is `policies/zfgv_metric_capability_policy_v1.json`.

## Product meaning

This module is the evidence relation desk.

A single metric must not jump directly into a football argument. It must first be checked against supporting, contradicting, complementary and contextual observations/metrics with provenance and dependency preserved.

## Required upstream artifacts

Depending on construct requirements:

- admitted source/surface manifest
- data quality and source-role evidence
- observation semantics
- identity/dependency evidence
- time/space admission when required
- context/process/consequence evidence when required
- metric definition/denominator/model contracts

No upstream surface is automatically required merely because it existed in the historical event-only pipeline.

## V1 relation types

```text
SUPPORTS
CONTRADICTS
COMPLEMENTS
CONTEXTUALIZES
ABSTAINS
```

## Allowed outputs

```text
metric readiness candidate
metric/observation support graph candidate
contradiction/counterevidence candidate
composite metric candidate
argument-ready evidence pack candidate
```

## Blocked outputs

```text
report language
tactical truth
dominance truth
pitch-control truth
off-ball truth
fatigue/physical-load truth
coach intention
tactical plan
causality
production binding
```

Aggregate/tabular observations do not create action identity or independent votes. Coordinates do not create tracking. Process labels do not create possession or intention truth. Model outputs do not become facts.

## Claim locks

```text
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

## Donor rule

GitHub, Google Drive, Dropbox and academic sources may guide contracts, methods and policy. They must not become runtime truth.

All donor material must be adapted into HPFA naming, contracts, tests and admitted product evidence before product use.
