# Discipline Lens Registry Lite V1

## Runtime role

Registers which diagnostic primitives may enter HPFA from an external discipline and which explicit inputs are required before the primitive can become a candidate.

```text
discipline + diagnostic primitive + supplied inputs
-> INCLUDE_DISCIPLINE_LENS_CANDIDATE / ROUTE_DISCIPLINE_LENS_TO_REVIEW / BLOCK_DISCIPLINE_LENS
```

The registry converts disciplines into input contracts. It does not use scientific terminology as metaphor and does not generate football truth.

## Initial disciplines

```text
statistics
entropy
graph_theory
geometry
bayes
game_theory
```

Each registry entry declares:

```text
allowed_primitives
required_inputs
claim_ceiling
```

## Decision contract

- `INCLUDE_DISCIPLINE_LENS_CANDIDATE`: registered primitive with all required explicit inputs.
- `ROUTE_DISCIPLINE_LENS_TO_REVIEW`: unknown discipline, disallowed primitive, or missing required inputs.
- `BLOCK_DISCIPLINE_LENS`: malformed request, failed upstream state, forbidden output attempt, output-permission escalation, or canonical-event-count claim.

## Fail-closed guards

- Recursive path-aware forbidden-field scan across dictionaries and lists.
- Upstream `FAIL_CLOSED`, `BLOCKED`, blocking decision, or hard-block propagation.
- `canonical_event_count` remains `UNKNOWN`.
- Claim, report-language and safe-sentence output remain disabled.
- Flat output-root policy is delegated to the canonical active-match spine validator.
- No sample match identity is embedded.

## Claim boundary

`discipline_diagnostic_candidate_only`

The module does not assert tactics, dominance, control, intention, off-ball behaviour, pitch control, causality, quality, sequence membership, or organism truth. A registered lens is eligible for diagnostic computation only; it is not evidence that the resulting football interpretation is true.

## Release boundary

`SMOKE_PASS` is the maximum local state. This contract does not provide `ACTIVE_MATCH_EVIDENCE_PASS` or `PRODUCTION_RELEASE`.
