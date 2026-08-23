# HPFA Defeasible Argument Router Lite V1 Contract

## Purpose

Route an `argument_candidate` when explicit counter-evidence or a declared withdrawal condition becomes available, while preserving enough structural lineage for Evidence Graph to represent the **post-routing** argument.

```text
argument candidate + explicit counter evidence + matched withdrawal condition
-> SUPPORTED / WEAKENED / WITHDRAWN / BLOCKED
```

These are routing states for a candidate argument. They are not football truth, claim text, confidence or publication permission.

## Canonical position

```text
composite_argument_builder_lite_v1
-> defeasible_argument_router_lite_v1
-> evidence_graph_engine_lite_v1
```

Evidence Graph must consume the routed argument rather than bypassing this router.

## Required input

- `argument_id`
- `supporting_refs`
- `contradicting_refs`
- `withdrawal_conditions`
- `claim_ceiling=argument_candidate_only`

Optional runtime observations:

- `counter_evidence_refs`
- `triggered_withdrawal_conditions`

A triggered condition is valid only when it exactly matches a condition declared by the upstream argument. A withdrawal also requires at least one explicit counter-evidence reference.
The module never matches free text or infers intent, causality, tactics or unseen behaviour.

## Structural lineage preservation

When present upstream, the route preserves:

```text
fusion_id
argument_family
relation_scope
analysis_route
whole_to_unit
unit_to_whole
bidirectional
complementary_refs
context_refs
counter_scenarios
upstream_argument_status
upstream_argument_decision
```

This preservation exists only so downstream Evidence Graph can trace the same argument after defeasible routing. It does not create new evidence.

## Decision order

1. Malformed, failed or forbidden upstream input -> `BLOCKED`.
2. Matched withdrawal condition plus counter evidence -> `WITHDRAWN`.
3. Explicit upstream contradiction, runtime counter evidence or qualifier -> `WEAKENED`.
4. At least one support reference and no defeating evidence -> `SUPPORTED`.

`SUPPORTED` means only that the candidate remains undefeated by the supplied evidence surface.
Absence of counter evidence is not proof that no counter evidence exists.

## Output

```text
defeasible_argument_router_lite_v1.json
defeasible_argument_router_lite_v1.txt
```

Output claim ceiling:

```text
defeasible_argument_candidate_only
```

## Claim boundary

- Defeasible argument routing candidate only.
- No claim text, safe sentence or report language.
- No numeric confidence, support weighting or tactical interpretation.
- No intent, dominance, control, off-ball, pitch-control, causal, quality, sequence or organism truth.
- `canonical_event_count=UNKNOWN` until Canonical Event Lite validates it.
- Flat phone output root policy is mandatory.
- `SMOKE_PASS` is not `ACTIVE_MATCH_EVIDENCE_PASS` or `PRODUCTION_RELEASE`.
