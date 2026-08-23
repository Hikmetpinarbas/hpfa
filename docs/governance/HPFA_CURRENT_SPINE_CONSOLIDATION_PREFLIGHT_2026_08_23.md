# HPFA Current Spine Consolidation Preflight — 2026-08-23

Status: `POLICY_CORRECTION_PASS / CURRENT_STATE_REFETCHED / CONSOLIDATION_PREFLIGHT_READY / NOT_PRODUCTION / NOT_MERGED`

## Purpose

This record refreshes the controlled-mainline consolidation problem against the exact GitHub state observed on 2026-08-23. It is governance/integration evidence only. It creates no Football Intelligence capability and carries no ACTIVE_MATCH authority.

## Current authority split

```text
PRODUCT_MAIN=main
main_head=105539970ffd0ca8b5d592a68e800da6057e3274
main_head_date=2026-08-19

CURRENT_DEVELOPMENT_FRONTIER_PR=267
current_development_frontier_branch=work/reconstruct-visible-sequence-partial-order-v1
current_development_frontier_head=a8b5d84ff40982b4ed20ddd673a93b0c87ffd55f
pr_267_state=open_draft
pr_267_mergeable=true
pr_267_review_threads_unresolved=0
pr_267_current_head_ci=SUCCESS

ACTIVE_MATCH_AUTHORITY=runtime/active_single_match/current
ACTIVE_MATCH_CURRENT_REVALIDATION=REQUIRED_BEFORE_INTEGRATION_PROMOTION

canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

`main` and the development frontier are different maturity surfaces. Neither may silently impersonate the other.

## Confirmed current product-development spine

The current dependency spine that must be preserved during consolidation is:

```text
#254 Row Nucleus
→ #259 Evidence Atom
→ #260 Match-Local Identity
→ #261 Semantic Role / Action Bundle
→ #262 Multi-Family Taxonomy
→ #263 Cross-Role Relation
→ #264 Trackable Action Trace
→ #265 Trackable Action Consequence
→ #266 Visible Action Sequence
→ #267 Partial-Order Hardening
```

The partial-order contract at the frontier preserves:

```text
BEFORE_CONFIRMED
AFTER_CONFIRMED
SAME_TIME_UNORDERED
ORDER_INDETERMINATE
PROVENANCE_ORDER_ONLY
```

and explicitly keeps source-row ordering from becoming football temporal truth.

## Integration debt

The repository still contains multiple open historical/current paths for the same broad capability families, including:

- Foundation and source semantics/reconciliation;
- legacy Evidence Atom / identity / semantic-action paths;
- current #254→#267 reconstruction path;
- historical selected-action / sequence / phase paths;
- spatial/progression branches;
- stale controlled-integration branches.

Therefore consolidation must not be a chronological PR merge train.

## Current decision

Landing unit remains:

```text
FINAL_CAPABILITY_SNAPSHOT
```

Forbidden shortcuts:

```text
giant merge
blind full-stack rebase
historical PR merge train
parallel replacement engine when current producer can be safely extended
stale runtime evidence promoted to current exact-head evidence
```

## Required consolidation order

### C0 — Authority and inventory normalization

- refresh machine-readable `PRODUCT_MAIN / DEVELOPMENT_CHECKPOINT / ACTIVE_MATCH_RUNTIME` separation;
- classify open PRs/capabilities as CURRENT, SUPERSEDED_REFERENCE, DONOR_SUPPORT, DIAGNOSTIC_ONLY or BACKLOG;
- preserve current main history and avoid destructive branch rewrites;
- keep merge/release/production decisions separate.

### C1 — Final Foundation snapshot

```text
inventory
→ CSV reader
→ XLSX reader
→ XML reader
→ content/source-role resolution
→ provider field semantics
→ provider label/value semantics
→ cross-format reconciliation
→ metric-definition policy
→ aggregate-definition alignment
→ provider metric dictionary where required
→ Row Nucleus / G01–G18 final behaviour
```

Later corrections must be folded into the layer they actually repair rather than landing an older historical snapshot.

### C2 — Current Evidence Spine snapshot

```text
Row Nucleus
→ Evidence Atom
→ Match-Local Identity
→ Semantic Role / Action Bundle
→ Multi-Family Taxonomy
→ Cross-Role Relation
```

### C3 — Current Football Reconstruction snapshot

```text
Trackable Action Trace
→ Trackable Action Consequence
→ Visible Action Sequence
→ Partial-Order Hardening
```

### C4 — Integrated exact-head revalidation

After a coherent integration head exists:

```text
CI
→ contract/invariant audit
→ no-sample-match-identity-leak guard
→ flat phone-output guard where applicable
→ exact-head ACTIVE_MATCH execution
→ Engineering Evidence
→ Analyst Evidence
→ claim-boundary audit
```

No downstream feature frontier is promoted before C0–C4 are complete.

## Post-consolidation first feature frontier

After consolidation, the first new Football Intelligence slice is:

```text
Review / Uncertainty Propagation
→ Context Evidence Re-binding
→ Analyst Episode Locator
```

Historical Match Context Slicer and Termux apparatus remain `DONOR_SUPPORT / CAPABILITY_RECOVERY_RESERVE` and must be adapted to the current #254→#267 spine under `ADAPT_NOT_COPY`.

## Claim boundary

```text
research_evidence != implementation_evidence
implementation_evidence != ACTIVE_MATCH_evidence
surface_rows != canonical_events
sequence_candidate != sequence_truth
partial_order != directly_follows_truth
context_candidate != tactical_truth
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

No merge, auto-merge, release or production binding is authorized by this document.
