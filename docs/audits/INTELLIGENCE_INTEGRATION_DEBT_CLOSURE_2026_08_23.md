# HPFA Intelligence Integration Debt Closure — 2026-08-23

Status: `INTEGRATION_CORRECTIONS_ENGINEERING_PASS / E2E_CONTRACT_FIXTURE_PASS / CONSOLIDATION_REQUIRED / NOT_PRODUCTION / NOT_MERGED`

This record updates the unresolved-blocker state documented in `docs/audits/intelligence_layer_integration_audit_v1.md` for the current stacked development line. The original audit remains historical evidence of what was found; this file records which findings have now been corrected and what remains.

## Current corrected stack

```text
#267 Visible Sequence Partial Order
→ #270 Packet failure propagation
→ #271 Packet/Fusion recursive guard
→ #272 Argument recursive guard
→ #273 Argument → Defeasible Route → Evidence Graph canonical route
→ #274 Safe Router review continuity
→ #275 Report Block / Output Contract review continuity
→ #276 remaining recursive guards (Defeasible Router + Assembly)
→ #277 Packet → Fusion signal metadata / explicit contradiction lineage
→ #278 end-to-end Intelligence contract fixture
```

## Closed integration findings

### 1. Packet → Fusion failure propagation

Closed by #270.

```text
upstream FAIL_CLOSED/BLOCK/hard_block_hits
→ BLOCK_FUSION
```

A failed packet cannot be reinterpreted as a valid fusion candidate.

### 2. Recursive forbidden-field guard divergence

Closed across the canonical tested path by #271, #272, #273, #274, #275 and #276. Evidence Lens Matrix already had recursive/path-aware behavior.

Nested dict/list claim/truth attempts are fail-closed and path-aware.

### 3. Canonical defeasible route

Closed by #273.

```text
Composite Argument
→ Defeasible Argument Router
→ Evidence Graph
```

Evidence Graph preserves SUPPORTED / WEAKENED / WITHDRAWN / BLOCKED state and matched withdrawal evidence.

### 4. Review-debt continuity

Closed through the current output-contract boundary by #274 and #275.

```text
Graph REVIEW_REQUIRED
→ Safe Router REVIEW_REQUIRED
→ Report Block REVIEW_REQUIRED
→ Output Contract REVIEW_BLOCK
→ Assembly ROUTE_ASSEMBLY_ITEM_TO_REVIEW
```

Review state is not silently normalized to `SMOKE_PASS`.

### 5. Explicit counter-evidence metadata lineage

Closed by #277.

Composite Evidence Packet retains backward-compatible signal refs plus structured signal records. Fusion can preserve explicit contradiction metadata/basis rather than degrading it to a generic qualifier.

Non-explicit tension remains `QUALIFIES`.

### 6. End-to-end producer-consumer execution fixture

Closed by #278.

The exact producer outputs are passed directly to the next consumer through:

```text
Packet
→ Fusion
→ Argument
→ Defeasible Route
→ Evidence Graph
→ Safe Router
→ Report Block
→ Output Contract
→ Assembly
```

Evidence Lens Matrix consumes the same Evidence Graph output as a review sidecar.

The fixture verifies:

```text
standard field / ID continuity
explicit counter-evidence review continuity
upstream failure propagation
nested forbidden-field fail-close
canonical_event_count=UNKNOWN at every tested stage
no sample match identity leak
missing lens coverage remains explicit and is not absence inference
```

Exact-head workflow for #278:

```text
workflow=Intelligence E2E Contract Fixture V1
run_id=32646486687
conclusion=success
```

## Important remaining debt

The correctness findings above are engineering-closed on the stacked development line, but **mainline integration debt is not closed**.

Current product main and current development frontier remain separate authority surfaces. The next work must therefore be controlled consolidation, not additional Context/Episode/Rhythm feature expansion.

Required consolidation order remains:

```text
C0 authority/inventory normalization
→ C1 Foundation final-capability snapshot
→ C2 Evidence Spine final-capability snapshot
→ C3 Football Reconstruction + Intelligence hardening snapshot
→ C4 integrated exact-head CI
→ fresh ACTIVE_MATCH revalidation where applicable
→ open-PR authority cleanup
```

No blind historical PR merge train, giant merge or chronological replay is admitted.

## Lens / orchestrator note

Evidence Lens Matrix currently remains a sidecar review surface rather than the direct input of Safe Argument Router. Its `REVIEW_REQUIRED` result is explicit, but a future integration orchestrator must combine sidecar review state with the primary reasoning/output path before any production-bound report assembly can be admitted.

Do not solve this by hiding missing lenses or inferring evidence absence.

## Claim and release locks

```text
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
claim_output_allowed=false
final_report_allowed=false
production_release=false
```

CI success is engineering evidence only. These corrections are not a production release and are not merged to main.
