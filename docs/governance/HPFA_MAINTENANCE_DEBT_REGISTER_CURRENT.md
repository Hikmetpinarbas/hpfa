# HPFA Maintenance Debt Register — CURRENT

Status: `MAINTENANCE_DEBT_VISIBLE / NOT_PRODUCTION`

## Closed now

- #304 correctness review debt: closed after exact-head CI + ACTIVE_MATCH.
- Repository front door: README restored.
- Stray root file `0`: removed.

## Open maintenance debt

### P0 — Main branch enforcement

Current GitHub branch metadata reports `main` protection disabled. Required repository-level policy:

- pull-request-only changes to `main`;
- required engineering checks;
- unresolved review-thread blocking;
- force-push disabled.

ACTIVE_MATCH must remain outside GitHub branch-protection truth.

### P1 — Historical PR / issue archaeology

Open historical branches must be reconciled against current `main` and classified as `CURRENT`, `STILL_NEEDED`, `SUPERSEDED`, `HISTORICAL_LINEAGE`, or `ARCHIVE_REFERENCE_ONLY`.

### P1 — CI consolidation

Capability-specific workflows have accumulated. Consolidation must reuse current workflows and current orchestrator surfaces rather than deleting coverage first.

Target:

```text
shared engineering orchestrator
→ foundation / affected-module / spine / claim-invariant suites
```

### P1 — ACTIVE_MATCH operator consolidation

Current product already has `active_match_spine_runner`. Generic operator work must rehabilitate/extend it instead of creating another runtime engine.

Target capabilities:

- exact repo/head verification;
- runtime authority discovery/verification;
- capability registry;
- prerequisite and invariant checks;
- first-failure disclosure;
- flat output packaging;
- engineering + analyst evidence envelope.

### P1 — Capability closure registry

Machine-readable closure evidence is required for:

```text
spec
contract
implementation
canonical producer
consumer
tests
runtime
analyst evidence
release
```

### P1 — Duplicate / parallel implementation audit

Exact duplicate reflections must be distinguished from competing implementations. Same SHA on multiple paths is lineage, not independent capability.

## Development gate

Capability growth may begin after active P0/P1 items that can corrupt authority, runtime selection, duplicate counting or operator truth are either closed or explicitly fail-closed behind contracts.

Claim locks remain unchanged:

```text
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```
