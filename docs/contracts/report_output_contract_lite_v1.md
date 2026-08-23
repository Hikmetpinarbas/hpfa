# Report Output Contract Lite V1

Module id: `report_output_contract_lite_v1`

## Purpose

Reads analyst report-block candidates and decides whether each block can continue as an output candidate, requires review, or must be rejected. It does not create final report text or claim truth.

## Upstream

`analyst_report_block_composer_lite_v1`

Required field: `report_block_candidate_tr`.

## Review continuity

Review status must not depend only on `block_family`.

A block routes to review when any of these are present:

```text
review_required=true
review_reasons non-empty
status=REVIEW_REQUIRED
block_family=review_required_candidate
```

The output must then be:

```text
status=REVIEW_REQUIRED
inclusion_decision=REVIEW_BLOCK
output_text_candidate_tr=""
```

Preserve upstream review reasons. If review is explicit without a reason, add `upstream_report_block_review_required`.

This prevents a weakened/withdrawn/review-bounded analyst sentence from becoming an include-ready output candidate downstream.

## Recursive guard

Forbidden claim/truth fields are scanned recursively through nested dict/list payloads and fail closed with path-aware evidence.

## Decisions

```text
INCLUDE_BLOCK_CANDIDATE
REVIEW_BLOCK
REJECT_BLOCK
```

## Review hits

```text
block_family_requires_review
upstream_report_block_requires_review
```

## Downstream

`REVIEW_BLOCK` is intended to become `ROUTE_ASSEMBLY_ITEM_TO_REVIEW` in `final_report_assembly_gate_lite_v1`.

## Boundaries

```text
claim_output_allowed=false
final_report_allowed=false
production_report_allowed=false
canonical_event_count=UNKNOWN
production_release=false
```

Drive, Dropbox, academic sources and donor repositories are support only. Current hpfa product path and runtime authority remain authoritative.
