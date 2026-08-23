# Safe Argument Router TR Lite V1

Module id: `safe_argument_router_tr_lite_v1`

## Product purpose

Safe Argument Router TR Lite V1 reads candidate-only evidence graph records and creates Turkish safe sentence candidates.

It does not create claim text or final report language.

## Required upstream

```text
evidence_graph_engine_lite_v1
```

Canonical reasoning order:

```text
composite argument
→ defeasible route
→ evidence graph
→ safe argument router TR
```

The router must not bypass the defeasible state already preserved by Evidence Graph.

## Football / analyst value

The analyst can receive a Turkish sentence candidate that preserves support, qualifier, context, counter-scenario, contradiction and withdrawal information while keeping uncertainty explicit.

A weakened or withdrawn argument is not rewritten as an ordinary positive sentence candidate.

## Runtime authority

Only HPFA-generated ACTIVE_MATCH artifacts may become runtime input.

Google Drive, Dropbox, academic sources and donor repos are reference/donor support only. They do not become runtime truth.

## Allowed outputs

```text
safe sentence candidate TR
sentence language
defeasible state
review-required state
review reasons
claim ceiling
blocked language scan result
report composer readiness candidate
```

## Blocked outputs

```text
claim text
final report language
tactical truth
dominance truth
control truth
coach intention truth
off-ball truth
pitch-control truth
causal truth
quality truth
sequence truth
organism truth
canonical event count claim
```

## Decision states

```text
READY_FOR_REPORT_COMPOSER_CANDIDATE
ROUTE_REVIEW_SAFE_SENTENCE_CANDIDATE
BLOCK_SAFE_SENTENCE
```

## Status propagation invariant

```text
upstream FAIL_CLOSED/BLOCKED -> FAIL_CLOSED
upstream REVIEW_REQUIRED     -> REVIEW_REQUIRED
WEAKENED                     -> REVIEW_REQUIRED
WITHDRAWN                    -> REVIEW_REQUIRED
SUPPORTED without review     -> SMOKE_PASS
```

`REVIEW_REQUIRED` must survive both record-level routing and report-level rollup.

If upstream review state is present without an explicit reason, the router emits:

```text
upstream_graph_review_required
```

rather than silently normalizing the record to `SMOKE_PASS`.

## Defeasible language boundary

`WEAKENED` sentence candidates must explicitly state that the argument candidate is weakened.

`WITHDRAWN` sentence candidates must explicitly state that the argument candidate is withdrawn and, when available, expose the matched withdrawal condition.

These are analyst-safe candidate statements, not final report claims.

## Recursive forbidden-field guard

Forbidden fields are scanned recursively through nested dict/list payloads. A nested truth/claim attempt must fail closed with a path-aware hit, for example:

```text
nodes[0].payload.metadata.nested.quality_truth
```

## Hard blocks

```text
graph_required_fields_missing
upstream_graph_failed_closed
upstream_graph_forbidden_output_attempted
upstream_graph_claim_output_allowed
upstream_graph_report_language_allowed
safe_sentence_forbidden_language_detected
```

## Upstream failure rule

If the upstream graph record carries hard blocks, `decision=BLOCK_GRAPH`, or `status=FAIL_CLOSED/BLOCKED`, the safe argument router must fail closed. A failed graph must never become a sentence candidate.

## Language safety rule

The router must reject unsafe certainty, tactical truth, dominance, control, coach intention, causal truth, off-ball truth, pitch-control truth, sequence truth and organism truth language.

## Mandatory regression coverage

At minimum tests must cover:

```text
required graph identity/schema/claim ceiling
upstream fail-closed propagation
recursive nested forbidden-field detection
SUPPORTED normal sentence candidate
upstream REVIEW_REQUIRED continuity
fallback review reason
WEAKENED review-safe language
WITHDRAWN review-safe language + matched withdrawal condition
report-level REVIEW_REQUIRED rollup
truth-language blocking
flat phone-output policy
no sample match identity leak
```

## Claim / release boundary

```text
claim_output_allowed=false
report_language_allowed=false
claim_ceiling=safe_sentence_candidate_only
canonical_event_count=UNKNOWN
production_release=false
```

`SMOKE_PASS` and `REVIEW_REQUIRED` are both non-production states.
PASS != RELEASE.
