# Reconstruction → Intelligence Packet Adapter Lite V1

## Role

This adapter is the narrow product bridge between the current C3 Reconstruction surface and the existing C4 Composite Evidence Packet Builder.

```text
Visible Action Sequence Candidates
+ current time-layer references
+ current consequence summary evidence
+ review / uncertainty state
→ reconstruction-bound packet input candidates
→ Composite Evidence Packet Builder
```

It does not replace either producer and does not create a new reasoning engine.

## Source authority

Accepted upstream module:

`visible_action_sequence_candidates_lite_v1`

The adapter consumes only the current hpfa producer contract. Historical #208/#213, HP-Motor, HP-Engine, Drive, Dropbox and Termux material are donor/reference support under `ADAPT_NOT_COPY`.

## Donor behaviours adapted

Only these behaviours are retained:

- fail closed on upstream hard failure;
- preserve one match-surface binding;
- preserve missing/ambiguous/review state instead of guessing;
- do not invent cross-period or same-time order;
- dependent/reflection-derived evidence is not an independent vote;
- review evidence qualifies an argument candidate rather than becoming contradiction truth;
- no silent evidence loss.

Possession/phase truth, canonical-event assumptions and historical schemas are not imported.

## Packet mapping

Each admitted Visible Action Sequence candidate produces exactly one packet-input candidate.

```text
packet_family=sequence
claim_ceiling=composite_candidate_only
input_sequences=current visible sequence candidate id
input_windows=current visible time-layer candidate ids
supporting_signals=one reconstruction-derived visible-structure support record
contradicting_signals=zero or one QUALIFIES review record
input_features=[]
input_metrics=[]
```

`contradicting_signals` is used only because the existing Fusion contract interprets non-explicit records there as `QUALIFIES`. The adapter never sets `CONTRADICTS`, `explicit_contradiction=true`, or a contradiction basis for ordinary review debt.

## Evidence independence rule

All refs produced by this adapter remain within the same current Reconstruction lineage.

```text
packet_input_ref_count_is_independent_source_count=false
derived_reconstruction_refs_are_independent_sources=false
independent_support_vote_allowed=false
```

The adapter creates only one `SUPPORTS` signal per sequence candidate. Time-layer references enter Fusion as contextual evidence, not additional support votes.

## Review propagation

A sequence candidate becomes review-qualified when either:

- `sequence_record_status=REVIEW_REQUIRED_CONTEXT`; or
- `consequence_review_trace_count > 0`.

The packet input retains explicit `review_required` and `review_reasons`. Fusion must therefore produce a qualifier relation, not contradiction truth.

Top-level upstream `REVIEW_REQUIRED` and `review_hits` are also retained in the adapter report.

## Fail-closed conditions

The bridge fails closed when any of the following is observed:

- wrong upstream module;
- upstream hard block or FAIL_CLOSED;
- missing match-surface binding;
- candidate/time-layer count mismatch;
- missing or duplicate candidate ids;
- missing sequence time-layer references;
- cross-binding reference;
- non-current source claim ceiling;
- any sequence/possession/control truth promotion;
- same-timestamp internal ordering promotion;
- source-row order promoted to temporal truth;
- canonical event count claimed;
- production release claimed.

No partial packet inventory is emitted after a hard block.

## Claim boundary

```text
visible_sequence_candidate_is_sequence_truth=false
visible_sequence_candidate_is_possession_truth=false
single_team_continuity_is_control_truth=false
same_timestamp_internal_ordering_allowed=false
source_row_order_is_temporal_truth=false
sequence_truth=false
possession_truth=false
causal_truth=false
tactical_truth=false
claim_output_allowed=false
report_language_allowed=false
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

## Runtime evidence policy

GitHub CI proves engineering compatibility only.

After exact-head CI, the bridge requires fresh physical execution against:

`runtime/active_single_match/current`

Historical #267 ACTIVE_MATCH evidence and #278 engineering evidence do not transfer to this new head.

## Initial release state

`THIN_ADAPTER_CANDIDATE / ACTIVE_MATCH_REVALIDATION_REQUIRED / NOT_PRODUCTION`
