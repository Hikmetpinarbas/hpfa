# HPFA Metric Fusion Donor Adaptation Note

Date: 2026-06-23

Status: DONOR_ADAPTATION_NOTE

## Finding

The existing main branch contains Event-Only Metric Fusion Engine V1 from PR #19.

Useful product pieces:

```text
MetricNode
MetricEdge
metric support graph
contradiction detector
relation types: SUPPORTS, CONTRADICTS, COMPLEMENTS, CONTEXTUALIZES, ABSTAINS
```

## Boundary

The existing engine is event-only. It does not compute VAEP/xT and does not emit football truth.

It should be adapted as the graph relation layer for future action-value-cost work.

## New Adaptation Path

```text
Metric Family Registry Lite V1
-> Metric Fusion Readiness Gate Lite V1
-> Action Value Cost Fusion Lite V1
```

## Why Metric Family Registry Comes First

Metric production must be family-gated before calculation.

Progression family, physical-cost family and efficiency family must be registered separately so that:

```text
progression evidence is not treated as tactical truth
physical-cost evidence is not treated as event truth
efficiency candidate is not treated as causality
```

## Current Product State

Primary surface is still unresolved. Therefore candidate calculations must wait.

Metric Family Registry can run safely because it classifies and gates metric families without producing values.

## Release Boundary

```text
Metric Family Registry Lite V1 can reach ACTIVE_MATCH_EVIDENCE_PASS as registry-only.
Action Value Cost Fusion Lite V1 remains SPEC_WAIT until readiness is explicit.
PRODUCTION_RELEASE_NOT_GRANTED
```
