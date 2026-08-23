# HPFA C0B — Intelligence Final-State File Lineage — 2026-08-23

Status: `C0B_INTELLIGENCE_FILE_LINEAGE_CLOSED / CURRENT_FRONTIER_SELECTED / E2E_CONTRACT_FIXTURE_PASS / NOT_MERGED / NOT_PRODUCTION`

## Purpose

Freeze the current Football Intelligence correctness/integration lineage for controlled `FINAL_CAPABILITY_SNAPSHOT` extraction after the Reconstruction boundary.

This is not a new intelligence feature plan and not a historical PR merge train.

## Current coherent frontier

```text
PR=#278
branch=test/intelligence-e2e-contract-fixture-v1
head=33ebcc161576e0e11012cc8f3c221512013c77f2
base=#277 / 834f0080cb628c9af4dbbb82e7f649fbcbfdda73
open=true
draft=true
mergeable=true
merged=false
review_threads_unresolved=0
production_release=false
```

Exact-head workflow evidence:

```text
workflow=Intelligence E2E Contract Fixture V1
run_id=32646584640
run_number=3
conclusion=success
head=33ebcc161576e0e11012cc8f3c221512013c77f2
```

## Ancestry decision

Direct compare:

```text
base=#267/a8b5d84ff40982b4ed20ddd673a93b0c87ffd55f
head=#278/33ebcc161576e0e11012cc8f3c221512013c77f2
status=ahead
ahead_by=43
behind_by=0
merge_base=#267 exact head
```

The #267→#278 file compare contains Intelligence correctness/integration changes and no Reconstruction producer changes. Therefore #278 is a coherent superset of the final Reconstruction boundary and is the preferred C3 combined extraction head.

## Canonical Intelligence path at #278

```text
Composite Evidence Packet
→ Multi-Signal Fusion
→ Composite Argument
→ Defeasible Argument Route
→ Evidence Graph
→ Safe Argument Router TR
→ Analyst Report Block
→ Report Output Contract
→ Final Report Assembly Gate
```

Evidence Lens Matrix consumes the Evidence Graph as an explicit sidecar review surface. It is not silently treated as a second canonical path or as absence truth.

## I01 — Packet → Fusion failure propagation — #270

Current file family hardened across the #270→#278 ancestry includes:

```text
hpfa/modules/core/composite_evidence_packet_builder_lite/src/composite_evidence_packet_builder.py
hpfa/modules/core/composite_evidence_packet_builder_lite/tests/test_composite_evidence_packet_builder.py
hpfa/modules/core/multi_signal_evidence_fusion_lite/src/multi_signal_evidence_fusion.py
hpfa/modules/core/multi_signal_evidence_fusion_lite/tests/test_multi_signal_evidence_fusion.py
.github/workflows/intelligence-fusion-upstream-failure-propagation-v1.yml
docs/audits/intelligence_fusion_upstream_failure_propagation_v1.md
```

Required retained behaviour:
- upstream Packet FAIL_CLOSED/BLOCK/hard-block state cannot be bypassed by Fusion;
- upstream status/decision/hard-block provenance survives;
- no claim/report/tactical truth opens from successful module execution.

## I02 — Recursive/path-aware forbidden-field guards — #271, #272, #276

Final hardening spans:

```text
hpfa/modules/core/composite_evidence_packet_builder_lite/src/composite_evidence_packet_builder.py
hpfa/modules/core/multi_signal_evidence_fusion_lite/src/multi_signal_evidence_fusion.py
hpfa/modules/core/composite_argument_builder_lite/src/composite_argument_builder.py
hpfa/modules/core/defeasible_argument_router_lite/src/defeasible_argument_router.py
hpfa/modules/core/final_report_assembly_gate_lite/src/final_report_assembly_gate.py
```

Focused regression surfaces include:

```text
hpfa/modules/core/defeasible_argument_router_lite/tests/test_defeasible_recursive_forbidden_guard_v1.py
hpfa/modules/core/final_report_assembly_gate_lite/tests/test_final_assembly_recursive_forbidden_guard_v1.py
.github/workflows/intelligence-recursive-forbidden-field-guard-v1.yml
.github/workflows/intelligence-argument-recursive-forbidden-guard-v1.yml
.github/workflows/intelligence-remaining-recursive-guards-v1.yml
```

Required retained behaviour:
- forbidden claim/truth fields are scanned recursively through nested dict/list payloads;
- non-empty forbidden values preserve exact path-aware evidence;
- nested claim/truth attempts fail closed;
- no layer normalizes an upstream forbidden-field failure into PASS.

## I03 — Canonical Argument → Defeasible Route → Evidence Graph — #273

Final files include:

```text
hpfa/modules/core/defeasible_argument_router_lite/src/defeasible_argument_router.py
hpfa/modules/core/defeasible_argument_router_lite/tests/test_defeasible_argument_router.py
hpfa/modules/core/evidence_graph_engine_lite/src/evidence_graph_engine.py
hpfa/modules/core/evidence_graph_engine_lite/tests/test_evidence_graph_engine.py
docs/contracts/defeasible_argument_router_lite_v1.md
docs/contracts/evidence_graph_engine_lite_v1.md
.github/workflows/intelligence-canonical-defeasible-graph-route-v1.yml
```

Canonical rule:

```text
raw_argument
→ defeasible_route
→ evidence_graph
```

Evidence Graph must not bypass Defeasible Router and read raw Argument as its canonical downstream input.

Review-state mapping retained:

```text
SUPPORTED → candidate graph
WEAKENED → REVIEW_REQUIRED
WITHDRAWN → REVIEW_REQUIRED
BLOCKED → FAIL_CLOSED
```

Support, qualifier, counter-evidence, context, counter-scenario, declared withdrawal and matched withdrawal structures remain evidence candidates, not tactical/causal truth.

## I04 — Safe Router review continuity — #274

Final files include:

```text
hpfa/modules/core/safe_argument_router_tr_lite/src/safe_argument_router_tr.py
hpfa/modules/core/safe_argument_router_tr_lite/tests/test_safe_argument_router_tr.py
docs/contracts/safe_argument_router_tr_lite_v1.md
.github/workflows/intelligence-safe-router-review-continuity-v1.yml
```

Required retained behaviour:
- upstream REVIEW_REQUIRED is not normalized to ordinary SMOKE_PASS language;
- WEAKENED remains explicit in safe sentence candidates;
- WITHDRAWN remains explicit and carries matched withdrawal condition when present;
- report rollup remains REVIEW_REQUIRED if any safe sentence is review-bounded;
- safe language remains candidate/report-support language only.

## I05 — Review continuity through analyst/report output — #275

Final files include:

```text
hpfa/modules/core/analyst_report_block_composer_lite/src/analyst_report_block_composer.py
hpfa/modules/core/analyst_report_block_composer_lite/tests/test_analyst_report_block_composer.py
hpfa/modules/core/report_output_contract_lite/src/report_output_contract.py
hpfa/modules/core/report_output_contract_lite/tests/test_report_output_contract.py
docs/contracts/analyst_report_block_composer_lite_v1.md
docs/contracts/report_output_contract_lite_v1.md
.github/workflows/intelligence-report-review-continuity-v1.yml
```

Required retained behaviour:

```text
Safe Router REVIEW_REQUIRED
→ Analyst Report Block REVIEW_REQUIRED
→ Report Output REVIEW_BLOCK
→ Final Assembly ROUTE_ASSEMBLY_ITEM_TO_REVIEW
```

Review debt cannot disappear merely because downstream formatting succeeds.

## I06 — Explicit counter-evidence metadata lineage — #277

Final files include:

```text
hpfa/modules/core/composite_evidence_packet_builder_lite/src/composite_evidence_packet_builder.py
hpfa/modules/core/multi_signal_evidence_fusion_lite/src/multi_signal_evidence_fusion.py
hpfa/modules/core/multi_signal_evidence_fusion_lite/tests/test_packet_signal_metadata_lineage_v1.py
.github/workflows/intelligence-signal-metadata-lineage-v1.yml
```

Required retained behaviour:
- Packet preserves structured supporting/contradicting signal metadata and provenance;
- Fusion consumes structured records when present and only falls back to legacy refs when required;
- explicit contradiction requires explicit contradiction evidence;
- non-explicit tension remains qualification rather than being promoted to contradiction;
- counter-evidence candidate is not contradiction truth.

## I07 — Canonical end-to-end contract fixture — #278

Final integration files:

```text
.github/workflows/intelligence-e2e-contract-fixture-v1.yml
hpfa/tests/integration/test_intelligence_chain_contract_v1.py
docs/audits/INTELLIGENCE_INTEGRATION_DEBT_CLOSURE_2026_08_23.md
```

The real producer-output → next-consumer fixture verifies:
- standard field/ID continuity;
- explicit counter-evidence → WEAKENED → REVIEW_REQUIRED continuity;
- upstream FAIL_CLOSED propagation through the chain;
- nested forbidden-field fail-closed propagation;
- `canonical_event_count=UNKNOWN` across stages;
- no sample-match identity leak;
- Evidence Lens missing coverage remains explicit.

This fixture is integration evidence. It is not ACTIVE_MATCH football-behaviour evidence and not production release evidence.

## I08 — Evidence Lens Matrix sidecar

Current #278 contains:

```text
hpfa/modules/core/evidence_lens_matrix_lite/src/evidence_lens_matrix.py
```

Current claim ceilings include:

```text
UPSTREAM_CLAIM_CEILING=evidence_graph_candidate_only
LENS_CLAIM_CEILING=evidence_lens_coverage_candidate_only
```

Required lenses include time, space, actor, team, action, outcome, sequence, context, opponent and contradiction.

Decision:
- retain Evidence Lens Matrix in C3 as an explicit review sidecar;
- do not treat missing lens evidence as evidence of absence;
- do not silently bypass its REVIEW_REQUIRED state in production-bound orchestration;
- final orchestration/gating combination remains a post-consolidation closure item before production-bound report assembly.

## Files changed between #267 and #278

The current final Intelligence correction surface comprises 37 changed files, including:
- 9 focused workflows;
- 2 audit records;
- 4 updated contract documents;
- current source/tests for Packet, Fusion, Argument, Defeasible Router, Evidence Graph, Safe Router, Analyst Report Block, Report Output and Final Assembly;
- 1 end-to-end integration fixture.

The extraction rule is final-state content at #278, not replaying #270→#278 commit-by-commit.

## #269 authority clarification

`#269` is the open issue:

```text
Post-consolidation Football Intelligence roadmap V1
```

It explicitly states that it is not implementation authority and that new independent intelligence nodes remain blocked by consolidation. It is roadmap/governance context only and is not part of the executable extraction lineage.

## ACTIVE_MATCH / runtime boundary

#270→#278 are Intelligence correctness/integration hardening slices. They do not create new ACTIVE_MATCH football-behaviour truth.

For C3 acceptance:
- Reconstruction runtime evidence remains bound to the exact executable Reconstruction head/runtime run;
- Intelligence engineering evidence remains bound to #278 exact-head CI;
- after C1+C2+C3 are assembled on one main-based integration head, C4 must run integrated exact-head CI and applicable fresh ACTIVE_MATCH revalidation before any promotion decision.

## Final extraction decision

```text
INTELLIGENCE_FINAL_STATE_SOURCE=#278/33ebcc161576e0e11012cc8f3c221512013c77f2
RECONSTRUCTION_FINAL_BEHAVIOURAL_BOUNDARY=#267/a8b5d84ff40982b4ed20ddd673a93b0c87ffd55f
C3_COMBINED_EXTRACTION_HEAD=#278/33ebcc161576e0e11012cc8f3c221512013c77f2
HISTORICAL_COMMIT_REPLAY=false
GIANT_MERGE=false
BLIND_REBASE=false
```

## Global locks

```text
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
claim_output_allowed=false
final_report_allowed=false
production_release=false
MERGE=NOT_AUTHORIZED
```

## Status

`C0B_INTELLIGENCE_FILE_LINEAGE_CLOSED / CURRENT_FRONTIER_278 / E2E_CONTRACT_FIXTURE_PASS / EVIDENCE_LENS_REVIEW_SIDECAR_PRESERVED / C3_EXTRACTION_SOURCE_SELECTED / NOT_PRODUCTION / NOT_MERGED`
