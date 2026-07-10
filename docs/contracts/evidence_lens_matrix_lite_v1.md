# HPFA 360 Evidence Lens Matrix Lite V1 Contract

## Purpose

Convert an `evidence_graph_candidate` into a deterministic coverage matrix for:

```text
time / space / actor / team / action / outcome / sequence / context / opponent / contradiction
```

The matrix exposes which lenses have explicit evidence references and which lenses remain
missing. Missing evidence is a review signal; it is not evidence that an event or behaviour did
not occur.

## Input

One Evidence Graph Engine Lite V1 graph with:

- `graph_id`
- `nodes`
- `edges`
- `claim_ceiling=evidence_graph_candidate_only`

Lens coverage is accepted only from explicit `lens` or `lenses` tags on graph nodes or node
payloads. The existing `context_ref` and `contradiction_ref` node types are also explicit lens
evidence. Names, IDs and free text are never interpreted as lens proof.

## Output

```text
evidence_lens_matrix_lite_v1.json
evidence_lens_matrix_lite_v1.txt
```

Each lens receives `COVERED` or `MISSING`, plus its explicit graph node references.
`coverage_score` is the number of covered lenses divided by 10. It is inventory completeness
only, not evidence strength, match quality, tactical quality or claim confidence.

## Decisions

```text
READY_FOR_LENS_AWARE_REVIEW_CANDIDATE
ROUTE_INCOMPLETE_LENS_COVERAGE_TO_REVIEW
BLOCK_LENS_MATRIX
```

An incomplete matrix routes to review but does not fail closed. Malformed or failed upstream
graphs, unknown lens tags, duplicate node IDs and forbidden upstream outputs fail closed.

## Claim boundary

- Coverage candidate only.
- No claim text or report language.
- No inference from missing evidence.
- No tactical, dominance, control, coach-intention, off-ball, pitch-control, causal, quality,
  sequence or organism truth.
- `canonical_event_count=UNKNOWN` until Canonical Event Lite validates it.
- `SMOKE_PASS` is not `ACTIVE_MATCH_EVIDENCE_PASS` or `PRODUCTION_RELEASE`.
- Phone outputs remain flat at `/sdcard/Download/HPFA` or
  `/storage/emulated/0/Download/HPFA`.

