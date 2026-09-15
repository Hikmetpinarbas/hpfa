# HPFA 360 Evidence Lens Matrix Lite V1 Contract

## Purpose

Convert an `evidence_graph_candidate` into a deterministic, construct-specific ZFGV evidence-coverage matrix.

The product-wide lens catalog is:

```text
time / space / actor / team / action / outcome / sequence / context / opponent / contradiction
relational / process / aggregate / external_context / tracking_video / derived
```

Presence in this catalog does **not** make a lens mandatory for every football construct.

A construct must declare which lenses are required for that football question and which are optional. Missing required evidence is a review signal. Missing optional or undeclared evidence is inventory information only. Missing evidence is never evidence that an event, behaviour or tactical property did not occur.

## Compatibility

Graphs created before construct-specific ZFGV lens requirements existed may omit `required_lenses` and `optional_lenses`.

Those legacy graphs retain the historical fixed review set:

```text
time / space / actor / team / action / outcome / sequence / context / opponent / contradiction
```

This compatibility mode must not be treated as product-wide ontology authority for new ZFGV constructs.

## Input

One Evidence Graph Engine Lite V1 graph with:

- `graph_id`
- `nodes`
- `edges`
- `claim_ceiling=evidence_graph_candidate_only`
- optional `required_lenses`
- optional `optional_lenses`

For explicit ZFGV mode, at least one required lens must be declared. A lens cannot be both required and optional. Unknown lens names fail closed.

Lens coverage is accepted only from explicit `lens` or `lenses` tags on graph nodes or node payloads. The existing `context_ref` and `contradiction_ref` node types are also explicit lens evidence. Names, IDs and free text are never interpreted as lens proof.

The canonical full-spine may bind a packet's explicit lens manifest and preserved evidence-record lens tags onto the graph. It must not invent evidence. A packet without an explicit manifest leaves the legacy graph behaviour unchanged.

## Construct-specific example

A progression-volume-versus-terminal-production construct may legitimately require:

```text
required_lenses = action / aggregate
optional_lenses = outcome / context / contradiction
```

It must not be downgraded merely because actor, space, opponent or sequence evidence is absent when those surfaces are not required by that construct.

This does not make aggregate and action surfaces independent evidence. Dependency and independence admission remain separate questions.

## Output

```text
evidence_lens_matrix_lite_v1.json
evidence_lens_matrix_lite_v1.txt
```

The matrix exposes:

- the active requirement mode,
- required and optional lenses,
- covered lenses,
- missing required lenses,
- missing optional lenses,
- explicit evidence-node references,
- required-lens coverage,
- wider ZFGV catalog visibility.

`coverage_score` remains an inventory-completeness measure only. It is not evidence strength, match quality, tactical quality, claim confidence or independent-support strength.

## Decisions

```text
READY_FOR_LENS_AWARE_REVIEW_CANDIDATE
ROUTE_INCOMPLETE_LENS_COVERAGE_TO_REVIEW
BLOCK_LENS_MATRIX
```

Missing required lenses route to review but do not become absence evidence. Missing optional lenses do not by themselves trigger review. Malformed or failed upstream graphs, unknown lens tags, invalid requirement manifests, duplicate node IDs and forbidden upstream outputs fail closed.

## Claim boundary

- Coverage candidate only.
- No claim text or production report language.
- No inference from missing evidence.
- No independence inference from multiple formats or multiple lenses.
- No tactical, dominance, control, coach-intention, off-ball, pitch-control, causal, quality, sequence or organism truth.
- Aggregate evidence does not create action identity.
- Coordinate evidence does not create tracking truth.
- `canonical_event_count=UNKNOWN` until separately validated.
- `true_action_count=UNKNOWN` until separately validated.
- `production_release=false` unless explicitly released under product authority.
- `SMOKE_PASS` is not `ACTIVE_MATCH_EVIDENCE_PASS` or `PRODUCTION_RELEASE`.
- Phone outputs remain flat at `/sdcard/Download/HPFA` or `/storage/emulated/0/Download/HPFA`.
