# HPFA C4 Intelligence Final Capability Snapshot V1

## Purpose

Land the current claim-safe Intelligence capability as one controlled mainline integration unit on top of C1 Foundation, C2 Evidence Spine, and C3 Reconstruction.

## Canonical producer-consumer path

Composite Evidence Packet
→ Multi-Signal Fusion
→ Composite Argument
→ Defeasible Argument Route
→ Evidence Graph
→ Safe Argument Router TR
→ Analyst Report Block
→ Report Output Contract
→ Final Report Assembly Gate

Evidence Lens Matrix consumes the Evidence Graph as an explicit review sidecar. Missing lens coverage cannot be converted into evidence of absence and does not silently disappear from the analyst surface.

## Source authority

Final donor/development source: PR #278 exact head `33ebcc161576e0e11012cc8f3c221512013c77f2`.

Landing base: current main after C3 Reconstruction.

Historical stacked branch history is not migrated. Final capability state is adapted as a controlled snapshot.

## Required correctness behaviour

- explicit counterevidence remains visible and can weaken an argument;
- REVIEW_REQUIRED propagates downstream instead of being erased;
- upstream FAIL_CLOSED blocks downstream Intelligence production;
- nested forbidden claim fields fail closed;
- producer/consumer IDs remain linked across the canonical chain;
- Evidence Lens review state remains explicit sidecar evidence;
- sample match identity must not leak into product code.

## Claim boundary

This snapshot does not create tactical truth, possession truth, sequence truth, coach-intention truth, dominance truth, pitch-control truth, body-orientation truth, fatigue truth, or off-ball truth.

`canonical_event_count=UNKNOWN`

`true_action_count=UNKNOWN`

`final_report_allowed=false`

`production_release=false`

## Runtime boundary

This landing is engineering integration only. Historical runtime evidence from donor/development branches is not promoted to current main. A fresh ACTIVE_MATCH execution on the integrated head is required before ACTIVE_MATCH evidence status can be assigned.

## Status before merge

`RELEASE_CANDIDATE_NOT_PRODUCTION_BOUND / ACTIVE_MATCH_REVALIDATION_REQUIRED / NOT_PRODUCTION / NOT_MERGED`
