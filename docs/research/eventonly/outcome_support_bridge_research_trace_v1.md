# Outcome Support Bridge Research Trace V1

## Product decision

Outcome Support Bridge Lite V1 is a product module in `hpfa`. It reuses current HPFA producers and does not copy a donor implementation.

Method: `ADAPT_NOT_COPY`.

## Source-role map

| Source | Role | Accepted contribution | Explicit exclusion |
|---|---|---|---|
| Current `hpfa` selected-action, selected-event and event-only sequence-consequence producers | `PRODUCT_PRODUCER` | Executable input contracts, exact field vocabulary, output lineage | None of their candidate outputs become canonical event, possession, sequence, tactical or causal truth |
| `runtime/active_single_match/current` | `ACTIVE_MATCH_AUTHORITY` | The only match-local runtime evidence authority | No archive, research file, Drive or Dropbox surface may override it |
| `HPFA_NODE_ROADMAP.md`, `HPFA_NEXT_CONSEQUENCE_NODE_SPEC.md`, `HPFA_CURRENT_STATE.md`, `HPFA_GUARDRAILS.md` | `REFERENCE_ONLY` | Categorical-first consequence framing; consequence is not value or quality; argument building remains downstream | Their historical input names and counts are not current runtime truth |
| `HPFA_DONOR_USAGE_MAP.md` and action/sequence/consequence research packs | `DONOR_SUPPORT` | Sequence compression, consequence surface, structure traceback, guarded progression and turnover concepts | No direct tactical, intention, dominance, pressure, possession or event truth promotion |
| Event-core object contracts, semantic caps and negative-test plans in the uploaded archives | `DONOR_SUPPORT` | Fail-closed behavior, terminal-ownership ambiguity guard, blocked downstream on missing identity/location/schema | Archive contracts are not executable product authority |
| `Archive Governance and Runtime Isolation.pdf` | `REFERENCE_ONLY` | Runtime/archive isolation and authority-drift prevention | Archived or research artifacts cannot enter the runtime execution path |
| `Football Analytics Claim Support Extraction.pdf` and outcome-model research | `REFERENCE_ONLY` | Claim-support/invalidator separation and the distinction between mechanism support and proof | Tracking, video, freeze-frame, off-ball, tactical-template and causal claims are not admitted by this event-only bridge |

## Research-derived guards adopted into product contract

1. **missing lineage must fail closed**: a payload-level binding cannot fill a missing record-level lineage field.
2. **terminal ownership ambiguity must block promotion**: a terminal flag requires a matching `TERMINAL_OUTCOME_ATOM`; a derived flag requires a matching `DERIVED_CONSEQUENCE_ATOM`.
3. Evidence-atom class counts must reconcile with unique evidence-atom IDs.
4. Explicit null actor lineage is allowed only when the source role itself is not actor-bound; missing actor fields are not equivalent to explicit null.
5. Sequence metric anchor support is support-only and intentionally partial; it cannot independently create terminal outcome truth.
6. Phone runtime outputs must remain flat under `/sdcard/Download/HPFA` or `/storage/emulated/0/Download/HPFA`.
7. Invalid output paths are rejected without writing into the rejected path.
8. Generated upstream artifacts are resolved from the flat phone-output surface where their producer runners write them.

## Football-intelligence effect

The bridge improves analytical separation rather than producing a stronger claim by assertion. It distinguishes:

- explicit terminal support;
- explicit derived-consequence support;
- visible downstream consequence support;
- sequence evidence-anchor support;
- compatible multi-source support;
- conflicted support;
- unavailable support.

This prepares later component-first argument construction while preserving the six-phase analysis ambition as a downstream analytical framework. It does not itself assign a tactical phase, coaching intention, dominance, pressing success, off-ball structure, possession control or player quality.

## Fixed boundaries

```text
terminal_outcome_truth=false
sequence_trace_truth=false
progression_truth=false
line_break_truth=false
possession_truth=false
phase_truth=false
tactical_truth=false
causality_truth=false
claim_allowed=false
canonical_event_count=UNKNOWN
production_release=false
```
