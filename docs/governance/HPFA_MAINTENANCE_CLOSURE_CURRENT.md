# HPFA Maintenance Closure — CURRENT

Status: `CURRENT_MAINTENANCE_GOVERNANCE / NOT_PRODUCTION`

## Purpose

Reduce maintenance cost without changing football semantics or opening new claim authority.

## Current rules

1. Correctness debt precedes capability growth.
2. Historical PR/issue state is not current product truth.
3. A historical branch is closed only after reconciliation with current `main`.
4. Existing canonical producers are rehabilitated before any parallel implementation is opened.
5. New capability work must reuse shared CI/operator/runtime infrastructure where possible.
6. ACTIVE_MATCH remains manual/runtime authority and is not replaced by GitHub CI.
7. Repository maintenance must not change claim locks unless a separate product contract and runtime gate explicitly justify it.

## Historical reconciliation decisions

Use only these decisions:

```text
CURRENT
STILL_NEEDED
SUPERSEDED
HISTORICAL_LINEAGE
ARCHIVE_REFERENCE_ONLY
```

Closing a PR does not delete its lineage. It removes the false signal that the branch remains a merge candidate.

## Capability closure chain

Each capability is audited across:

```text
spec
→ contract
→ implementation
→ canonical producer
→ consumer
→ tests
→ runtime binding
→ analyst evidence
→ release state
```

Missing links remain visible. A partial chain must not be reported as a completed product capability.

## Shared-infrastructure target

Maintenance direction:

```text
capability registry
→ shared CI orchestration
→ shared ACTIVE_MATCH operator
→ first-failure disclosure
→ runtime-surface allowlist
→ duplicate/parallel implementation guard
```

This direction must extend existing `active_match_spine_runner`, current workflows and current producers rather than opening a parallel runtime platform.

## Repository front-door requirement

`README.md` is the product entry point. It must state product authority, runtime authority, claim locks, repository map, engineering method and current development direction.

## Claim locks

```text
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

Maintenance work alone does not promote sequence, phase, possession, rhythm, tactical, causal or model truth.
