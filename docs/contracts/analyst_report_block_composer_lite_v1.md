# Analyst Report Block Composer Lite V1

Module id: `analyst_report_block_composer_lite_v1`

## Purpose

Reads Turkish safe sentence candidates and creates analyst report-block candidates. It does not create final report text or claim truth.

## Upstream

`safe_argument_router_tr_lite_v1`

Required standard field: `safe_sentence_candidate_tr`.

## Review continuity

Upstream review state must survive this layer:

```text
FAIL_CLOSED -> FAIL_CLOSED
REVIEW_REQUIRED -> REVIEW_REQUIRED
SMOKE_PASS -> SMOKE_PASS candidate
```

For review-required input:

```text
status=REVIEW_REQUIRED
decision=ROUTE_REPORT_BLOCK_TO_REVIEW
block_family=review_required_candidate
```

Preserve `review_reasons`. If review is explicit and no reason exists, add `upstream_safe_sentence_review_required`.

`WEAKENED` and `WITHDRAWN` defeasible states therefore cannot become an ordinary include-ready block merely by passing through the composer.

## Recursive guard

Forbidden claim/truth fields are scanned recursively through nested dict/list payloads and fail closed with path-aware evidence.

## Decisions

```text
READY_FOR_REPORT_OUTPUT_CONTRACT_CANDIDATE
ROUTE_REPORT_BLOCK_TO_REVIEW
BLOCK_REPORT_BLOCK
```

## Rollup

```text
any hard block -> FAIL_CLOSED
else any review block -> REVIEW_REQUIRED
else -> SMOKE_PASS
```

The report exposes `review_report_block_count` separately from blocked count.

## Boundaries

```text
claim_output_allowed=false
final_report_allowed=false
production_report_allowed=false
canonical_event_count=UNKNOWN
production_release=false
```

Drive, Dropbox, academic sources and donor repositories are support only. Current hpfa product path and runtime authority remain authoritative.
