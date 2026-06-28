# R1 ACTIVE_MATCH Permission Spine Closure Plan V1

Status: PLAN_ONLY / REVIEW_REQUIRED

Linked issue: #87

## Purpose

R1 closes the ACTIVE_MATCH permission spine before HPFA attempts full Event-Time-Space postmatch intelligence.

This plan exists because several modules are already present in the product repo as contracts, modules or tests, but their ACTIVE_MATCH evidence closure and release-status normalization are uneven.

R1 is a closure plan, not a production release.

## Runtime Authority

Executable truth remains:

```text
runtime/active_single_match/current
```

Donor repositories, Google Drive, Dropbox, academic papers, archive packs and historical reports are support/reference only.

## Product Decision

P2C XML-CSV Temporal-Spatial Binder Lite remains valid as the next Event-Time-Space design node.

However, P2C implementation must not outrun upstream permission gates.

Before full postmatch intelligence, HPFA must close source mapping, source conflict, review resolution, state transition, minimal context and event-window evidence.

## R1 Closure Order

1. Source Mapping Contract Lite ACTIVE_MATCH run
2. Source Conflict Registry Lite ACTIVE_MATCH run
3. Primary Surface Review Resolution Lite ACTIVE_MATCH run
4. GK Taxonomy Source Role Reconciliation evidence check
5. Identity Review Resolution evidence check
6. Event State Transition Verifier Lite ACTIVE_MATCH run
7. Minimum Viable Context Lite ACTIVE_MATCH run
8. Event Window Builder Lite ACTIVE_MATCH run
9. Active Match Identity Guard blocker closure
10. Football Time Foundation Lite implementation
11. Metric Contract Registry ACTIVE_MATCH proof
12. Metric Readiness Report Lite
13. Evidence Bundle Schema Lite
14. Claim Eligibility Gate Lite
15. Support Threshold Router Lite
16. Observation and Mechanism Candidate Registry Lite
17. Analyst Reading Surface Compressor
18. Evidence Card Renderer
19. Football Output Audit Lite
20. Postmatch Analyst Report Lite ACTIVE_MATCH execution

## Evidence Contract

Every closure node must emit two evidence layers.

### Engineering evidence

- module executed
- tests passed
- output written
- flat phone output respected
- nested phone output rejected when applicable
- release status normalized
- upstream gate blockers recorded

### Analyst evidence

- what visible match surface became safer
- what claim became allowed
- what claim was downgraded
- what claim was blocked
- what remains REVIEW_REQUIRED

## Claim Boundary

R1 does not unlock:

- canonical event count truth
- deduplicated event count truth
- possession truth
- phase truth
- sequence truth
- tactical truth
- dominance or control claims
- coach intention
- production release

## Closure Status Vocabulary

Allowed statuses:

- PLAN_ONLY
- SPEC_ONLY
- IMPLEMENTATION_WRITTEN_EXECUTION_PENDING
- SMOKE_PASS
- ACTIVE_MATCH_EVIDENCE_PASS
- REVIEW_REQUIRED
- FAIL_CLOSED
- PRODUCTION_RELEASE

`PASS` alone is not a release status.

## Phone Output Policy

User-visible Termux outputs must be flat under:

```text
/sdcard/Download/HPFA
/storage/emulated/0/Download/HPFA
```

Nested output directories must fail closed with:

```text
nested_phone_output_directory_rejected
```

## R1 Exit Criteria

R1 can close only when the following are true:

1. Each selected upstream node has a normalized status.
2. Each executed node has engineering evidence.
3. Each executed node has analyst evidence.
4. Any REVIEW_REQUIRED blocker is explicit.
5. No node unlocks event-count truth prematurely.
6. No node emits phase, possession or sequence truth without its own later gate.
7. No output violates phone output policy.
8. P2C remains downstream-safe.

## Current Product Judgment

HPFA has moved beyond research/spec repository status.

Current level:

```text
ACTIVE_MATCH evidence producing product-engineering repo
```

Not yet:

```text
full professional postmatch intelligence product
production release
```
