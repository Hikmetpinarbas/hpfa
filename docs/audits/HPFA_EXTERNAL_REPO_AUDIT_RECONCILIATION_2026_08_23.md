# HPFA External Repository Audit Reconciliation — 2026-08-23

Status: `REFERENCE_ONLY_EXTERNAL_AUDIT_RECONCILED / FALSE_POSITIVES_SEPARATED / CONSOLIDATION_RECOMMENDATION_RETAINED / NOT_PRODUCTION / NOT_MERGED`

## Purpose

This record reconciles an externally generated repository debt audit supplied on 2026-08-23 against the current HPFA GitHub development evidence.

The external document is `REFERENCE_ONLY`. It is not product authority, runtime evidence, ACTIVE_MATCH evidence, or a replacement for current repository code/contracts/tests.

## Source-role correction

The external audit contains acronym contamination: it mixes Hikmet Pınarbaş Football Analytics with an unrelated external work using the acronym HPFA. It also imports unrelated web/research framing into repository findings.

Therefore only findings independently reproduced against current HPFA repository evidence may enter the debt register.

`PASS != RELEASE` is a release-governance rule. It does not mean that football action family `PASS` must be separated from a hypothetical mechanical `RELEASE` ontology.

## Current authority

```text
PRODUCT_MAIN=main
CURRENT_DEVELOPMENT_FRONTIER_PR=278
CURRENT_DEVELOPMENT_FRONTIER_HEAD=33ebcc161576e0e11012cc8f3c221512013c77f2
ACTIVE_MATCH_AUTHORITY=runtime/active_single_match/current
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

Main remains product main. It is behind the development frontier; it is not declared superseded product authority.

## Reconciled external claims

### FALSE POSITIVE — source row order used as temporal truth

Current #267 partial-order contract explicitly defines:

```text
source_row_index_relation=PROVENANCE_ORDER_ONLY
source_row_order_is_temporal_truth=false
same_timestamp_default=SAME_TIME_UNORDERED
missing_or_ambiguous_order_default=ORDER_INDETERMINATE
directly_follows_truth=false
```

Same-timestamp input permutation regression is present. Do not reopen this as current P0 without new contrary exact-head evidence.

### FALSE POSITIVE — Visible Sequence creates possession/control truth

Current Visible Action Sequence producer explicitly preserves:

```text
visible_sequence_candidate_is_sequence_truth=false
visible_sequence_candidate_is_possession_truth=false
single_team_continuity_is_control_truth=false
sequence_truth=false
possession_truth=false
tactical_truth=false
```

### FALSE POSITIVE — Fusion creates canonical event count from list length

Current Intelligence E2E fixture verifies `canonical_event_count=UNKNOWN` at every tested stage. Packet→Fusion signal lineage regression separately verifies Packet and Fusion remain UNKNOWN.

### FALSE POSITIVE — WEAKENED/WITHDRAWN review state is flattened into positive report output

Current #274/#275/#278 path preserves review debt:

```text
Graph REVIEW_REQUIRED
→ Safe Router REVIEW_REQUIRED
→ Report Block REVIEW_REQUIRED
→ Output Contract REVIEW_BLOCK
→ Assembly ROUTE_ASSEMBLY_ITEM_TO_REVIEW
```

The #278 explicit-counterevidence fixture additionally verifies draft report assembly is not allowed on this review path.

### FALSE POSITIVE — downstream FAIL_CLOSED propagation is untested

#278 contains end-to-end upstream failure propagation through Packet, Fusion, Argument, Defeasible Route, Graph, Safe Router, Report Block, Output Contract and Assembly.

### FALSE POSITIVE — nested forbidden-field scanning is absent in report layers

Current #275/#276 hardening provides recursive/path-aware nested scanning in Report Block, Output Contract, Defeasible Router and Final Assembly. #278 verifies nested forbidden input fails closed through the integrated chain.

### FALSE POSITIVE — current Cross-Role Relation produces coach-intention truth

Current product candidate is `cross_role_relation_candidate_resolver_lite_v1`. It resolves exact match-local primary/reflection relation candidates and explicitly keeps tactical/sequence/possession/phase truth false. No independently verified current coach-intention producer was found in this path.

### FALSE POSITIVE — current critical CI relies on merge-ref rather than exact PR head

Current #267 and #278 workflows explicitly checkout the exact pull-request head SHA. CI remains engineering evidence only and is not ACTIVE_MATCH evidence.

### UNSUPPORTED — current Defeasible/Graph path treats missing evidence as evidence of absence

No current exact evidence supporting the external audit's alleged behavior was reproduced. Current Defeasible Router declares `absence_of_counter_evidence_proves_support=false`; Evidence Lens declares `absence_inference_allowed=false`; #278 verifies missing lens coverage remains REVIEW_REQUIRED.

Do not add an UNKNOWN_STATE graph feature solely from the external audit without a reproduced current product gap.

### UNSUPPORTED — coordinate evidence is aliased to tracking truth

No current exact product evidence reproducing the claimed alias was established during reconciliation. Current candidate surfaces use coordinate-evidence terminology and keep tactical truth disabled. Reopen only with exact current path/function evidence.

## Useful external findings retained

The external audit independently converged on several strategic conclusions that are consistent with current HPFA governance:

- new Football Intelligence feature expansion should remain frozen until mainline consolidation;
- do not use a blind historical PR merge train;
- consolidate by final capability state rather than PR chronology;
- temporal/claim/review boundaries are high future-sprung-risk areas and must remain invariant during consolidation;
- future Context, Episode, Rhythm, Video and Cross-Match work must build on the corrected current contracts rather than reintroducing historical assumptions.

These are recommendations, not additional implementation evidence.

## Current real remaining debt

The external audit does not supersede the current confirmed debt register.

Current P0 remains:

```text
C0 authority/inventory normalization
→ C1 Foundation final-capability snapshot
→ C2 Evidence Spine final-capability snapshot
→ C3 Football Reconstruction + Intelligence hardening final-capability snapshot
→ C4 integrated exact-head CI + applicable ACTIVE_MATCH revalidation
```

After one coherent integration head exists, close the Evidence Lens sidecar/orchestration gate so its REVIEW_REQUIRED state cannot diverge from production-bound reasoning/output assembly.

Then perform open-PR authority cleanup.

Only after those steps may the feature freeze end.

## Post-freeze feature order

```text
Context Evidence Re-binding
→ Analyst Episode Locator
→ Rhythm / Change Detection
→ Recurrence / Variation / Deviation
```

## Claim / release locks

```text
external_audit != product_authority
external_audit != runtime_evidence
research_evidence != implementation_evidence
CI_SUCCESS != ACTIVE_MATCH_EVIDENCE
surface_rows != canonical_events
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

No merge, release, production binding, or ACTIVE_MATCH claim is created by this reconciliation.
