# HPFA Aggregate Definition Alignment Lite V1

## Product role

This module sits after current Metric Definition Policy and Cross-Format Reconciliation. It asks a narrow question:

> Can an XLSX aggregate label be linked to a provider-definition candidate and admitted row-level occurrence semantics without claiming event identity, metric truth, or independent confirmation?

It does not compute football quality or tactical truth.

## Source-surface contract

- CSV = action + coordinate candidate surface.
- XML = action-type + source start/end interval candidate surface.
- XLSX = aggregate candidate surface.

These surfaces may support one another only through explicit candidate linkage. They are not automatically the same physical event and are not independent votes when they are reflections from the same provider.

## Admission rules

1. `same_label != same_definition`.
2. `count_parity != definition_equivalence`.
3. Same-provider CSV/XML/XLSX support is not independent confirmation.
4. XLSX rows never become event identity.
5. CSV/XML candidate linkage never becomes physical-event identity without an explicit later linkage gate.
6. Rate-like aggregate alignment consumes R19 denominator closure from Metric Definition Policy. An OPEN/UNKNOWN denominator keeps alignment under review.
7. Per-90 remains subject to R22 ExposureAuthority.
8. R24 conflict authority applies: no static format precedence, no completeness-wins, no dependent majority vote.
9. R36 Measurement Invariance is required before any cross-group/player/team score comparison; this node never grants comparison permission.
10. Current ACTIVE_MATCH validates match-local execution only. It is not generalization evidence for another match.

## Expected current seed behavior

The SportsBase `Passes accurate, %` candidate remains `PROVIDER_DEFINITION_REQUIRED` and its derivation lineage remains unresolved. Current Metric Definition Policy also keeps the pass-completion denominator closure `UNKNOWN`.

Therefore the expected current ACTIVE_MATCH result is:

- execution can pass;
- definition alignment remains `REVIEW_REQUIRED`;
- `definition_alignment_cleared=false`;
- `downstream_gate_open=false`;
- no metric value or comparison output.

This is a useful result: the system has located the visible aggregate and its row-level semantic support, but refuses to pretend that the provider formula is validated.

## Claim boundary

Always false / blocked here:

- aggregate equivalence truth
- independent confirmation
- cross-group comparability
- measurement invariance truth
- metric value output
- quality truth
- tactical truth
- event identity promotion
- canonical event count
- production release

`canonical_event_count=UNKNOWN`
`production_release=false`

## Runtime UX

Phone execution:

- exact branch + exact head gate
- runtime authority `runtime/active_single_match/current`
- single-pass upstream refresh
- no phone pytest
- flat `/sdcard/Download/HPFA`
- exactly one operator ZIP
