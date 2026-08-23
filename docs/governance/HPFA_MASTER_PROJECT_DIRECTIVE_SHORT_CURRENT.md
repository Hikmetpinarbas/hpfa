# HPFA MASTER PROJECT DIRECTIVE — SHORT CURRENT

Version: 2026.08.23-C4-CONSOLIDATED
Status: ACTIVE_GOVERNANCE_RECORD

## PROJECT
HPFA = Hikmet Pınarbaş Football Analytics.
Event-only, claim-safe, modular and portable Football Intelligence Platform.
HPFA produces football-behaviour evidence, pattern evidence, sequence evidence/candidates, match-local identity evidence, rhythm evidence/candidates, metric evidence and analyst-facing outputs.

## USER ROLE AND REQUIRED EVIDENCE
The user is a football analyst.
Every real runtime result must provide two separate evidence layers:
1. engineering evidence: module execution, tests, status, output paths and failure/review hits;
2. analyst evidence: what is visible on the match surface, where it appears, which evidence supports it and what it safely means for analysis.

## RUNTIME AUTHORITY
The only match-runtime authority is:
`runtime/active_single_match/current`

Termux reference:
`/data/data/com.termux/files/home/hpfa_claim_integrity/hpfa/runtime/active_single_match/current`

The Git product checkout and ACTIVE_MATCH runtime directory are separate paths.
Google Drive, Dropbox, PDFs, archives, samples, reports, donor repositories and academic papers are REFERENCE_ONLY / DONOR_SUPPORT. They do not override ACTIVE_MATCH.

Termux/local historical apparatus is also a capability-recovery reserve: when current hpfa lacks a capability, viable local apparatus may be adapted into hpfa under `ADAPT_NOT_COPY`. It does not become product or ACTIVE_MATCH truth until adapted, tested and validated on the current product head.

## REPOSITORY ROLES
- `hpfa`: only product repository; executable product modules are born here.
- `HP-Motor`: ingest, phase, possession, sequence, metric primitive and narrative donor.
- `HP-Engine`: pattern, sequence intelligence, behaviour graph, semantic gate, metric graph and explanation donor.
- `HP-PROJELERI`: governance, policy, authority, registry and release donor.

## DONOR RULE
`ADAPT_NOT_COPY`

Required path:
current hpfa producer → donor capability → source role → boundary → HPFA contract → HPFA module → tests → ACTIVE_MATCH execution when applicable → engineering evidence → analyst evidence → football audit → release decision.

## PRODUCT ENGINEERING MODE
Every new capability must declare:
source role, target module, input/output contract, deterministic tests, ACTIVE_MATCH need, claim ceiling, phone output, dependency order and release status.

Code is the final step, not the first.

## SOURCE SEARCH ORDER BEFORE CODING
1. hpfa current main / current producer
2. HP-Motor
3. HP-Engine
4. HP-PROJELERI
5. Google Drive governance/donor library
6. Dropbox archive/donor library
7. academic support
8. Termux discovery/capability-recovery corpus

## CURRENT MAIN AUTHORITY
Authoritative product ref:
`refs/heads/main`

C4 integrated product-capability baseline before the governance-only authority refresh:
`d23f868a5287811b4dc6e2912085aa85fd547a64`

The live `main` ref is authoritative after governance-only commits as well; the capability baseline SHA is recorded for lineage and must not be misread as a permanently fixed branch head.

Controlled consolidation completed on 2026-08-23 as four final-capability snapshots:

```text
C1 Foundation
  merge=f3dc7b44d6bb899033a605a690f6cc51fb0199a4
  final_state_source_pr=#254

C2 Evidence Spine
  merge=871cd3c4948dd72b80aaa2983268811d7a22b39b
  final_state_source_pr=#263

C3 Reconstruction / Partial-Order
  merge=adb9c1d60cf98c79fd1de1c7a6df7b822c11496a
  final_state_source_pr=#267

C4 Intelligence Correctness / Integration
  merge=d23f868a5287811b4dc6e2912085aa85fd547a64
  final_state_source_pr=#278
```

Historical stacked PR commits were not replayed chronologically. Final reviewed capability state was extracted/adapted as controlled landing units.

Main membership does not establish ACTIVE_MATCH evidence or production release for the integrated head.

## CURRENT INTEGRATED PRODUCT SPINE

```text
Multiformat File Inventory
→ CSV / XLSX / XML surface readers
→ Provider alias/field + label/value semantics
→ Content Source Role Resolver
→ Cross-Format Reconciliation
→ Metric Definition / Aggregate Alignment
→ Provider Metric Dictionary
→ Triangulated Reflection Resolution
→ Row Nucleus
→ Evidence Atom
→ Match-Local Identity Candidates
→ Semantic Role / Action Bundle Candidates
→ Multi-Family Review Taxonomy
→ Cross-Role Relation Candidates
→ Trackable Action Trace Candidates
→ Trackable Action Consequence Candidates
→ Visible Action Sequence Candidates
→ Partial-Order hardening
```

Current Intelligence engineering chain:

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

Evidence Lens Matrix consumes Evidence Graph as an explicit review sidecar. Missing lens coverage cannot be converted into evidence of absence.

## CURRENT INTEGRATION GAP
C1–C4 are engineering-integrated on main, but current main does not yet contain an admitted product adapter that converts C3 Reconstruction output directly into C4 Composite Evidence Packet input.

Therefore:
- integrated-main Intelligence ACTIVE_MATCH truth is not claimed;
- historical #267 runtime evidence remains historical exact-head evidence only;
- historical #278 engineering evidence remains historical exact-head evidence only;
- a safe Reconstruction → Intelligence bridge/orchestration contract must be discovered/adapted before end-to-end integrated ACTIVE_MATCH promotion.

The preferred bridge is a thin adapter if current/donor behaviour supports it. It must preserve sequence candidate lineage, review/uncertainty state, provenance and partial-order ambiguity without promoting sequence, possession, causal or tactical truth.

## PARTIAL-ORDER AUTHORITY
Allowed audit states:

```text
BEFORE_CONFIRMED
AFTER_CONFIRMED
SAME_TIME_UNORDERED
ORDER_INDETERMINATE
PROVENANCE_ORDER_ONLY
```

Rules:
- visible timestamp is the ordering evidence scope;
- same timestamp does not admit internal order;
- source row index is provenance order only;
- missing/ambiguous order remains indeterminate;
- relation records cannot manufacture action volume, sequence truth or possession truth.

## SURFACE AND COUNT RULES
CSV, TSV, XML, XLS/XLSX, JSON and JSONL are evidence surfaces.
Surface rows are not canonical events.
Correct terms include:
`surface rows`, `visible rows`, `event-like rows`, `row-level evidence`, `event-row evidence`, `action-family volume`, `candidate count`.

Do not infer:
- missing value = zero;
- missing column = absent football behaviour;
- same timestamp = duplicate event;
- provider label = canonical event key;
- CSV/XML mirror = two independent actions;
- XLSX aggregate row = timeline event.

Until a later explicit admission contract passes:
`canonical_event_count=UNKNOWN`
`true_action_count=UNKNOWN`

## DUPLICATE / REFLECTION RULE
The same SHA-256 content observed at different paths is an exact duplicate reflection/lineage observation, not automatically a data conflict.
Duplicate reflections must not be counted twice as row/event/action volume.

## IDENTITY AND EVENT ADMISSION
Identity is match-local unless a later explicit global registry proves otherwise.
Provider fields, codes, team/player tokens, action labels and aliases begin as candidates.
Identity binding is not event truth.
No raw surface row directly becomes an event instance.

## CLAIM SAFETY
HPFA does not directly produce:
pitch-control truth, body-orientation truth, coach intention, dominance truth, fatigue truth, off-ball truth, tactical truth, clean phase truth, complete event-stream truth, sequence truth or possession truth without the relevant later gate.

Safe language includes:
- row-level evidence shows...
- visible surface evidence indicates...
- action-family volume suggests...
- coordinate evidence is concentrated in...
- match-local identity candidate...
- sequence/rhythm candidate detected...
- requires later validation...

Blocked without a later explicit gate:
- the team intentionally...
- the coach planned...
- dominated...
- controlled the pitch...
- off-ball structure proves...
- definitive tactical truth...

## ANALYST LANGUAGE
HPFA must not become a silent compliance system.
The main analyst text should state:
what was observed, where it was observed, which evidence supports it and why it matters.
Technical limits, missing evidence and claim ceilings stay in a separate technical block.

## PHONE OUTPUT POLICY
All user-visible Termux outputs must be written directly under:
- `/sdcard/Download/HPFA`
- `/storage/emulated/0/Download/HPFA`

Nested user-visible output directories are rejected with:
`nested_phone_output_directory_rejected`

## MATCH-AGNOSTIC RULE
Product code must not hardcode match name, teams, date, tournament, sample ID or sample row counts.
Generic metadata read from input is allowed.
Mandatory regression:
`test_no_sample_match_identity_leak`

## RELEASE STATUS
PASS is not release.
Use explicit states including:
`DISCOVERY_PASS_PLAN_ONLY`
`POLICY_CORRECTION_PASS`
`SPEC_ONLY`
`SPEC_CORRECTION_ACCEPTED`
`SMOKE_PASS`
`REVIEW_REQUIRED`
`FAIL_CLOSED`
`WAITING_OPERATOR_SELECTION`
`RELEASE_CANDIDATE_NOT_PRODUCTION_BOUND`
`ACTIVE_MATCH_EVIDENCE_PASS`
`PRODUCTION_RELEASE`

Rules:
- CI success proves deterministic engineering checks only.
- SMOKE_PASS is not ACTIVE_MATCH evidence.
- ACTIVE_MATCH_EVIDENCE_PASS is not PRODUCTION_RELEASE.
- MERGED is not PRODUCTION_RELEASE.
- historical failed runs superseded by a newer green head are not current blockers.
- a moved head invalidates prior current-head readiness/runtime evidence unless regenerated.

## CURRENT RELEASE STATE

```text
main_authority_ref=refs/heads/main
integrated_product_capability_baseline=d23f868a5287811b4dc6e2912085aa85fd547a64
foundation_integrated=true
evidence_spine_integrated=true
reconstruction_integrated=true
intelligence_correctness_integrated=true
reconstruction_to_intelligence_runtime_bridge=false
integrated_head_active_match_revalidated=false
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

Status:
`MAINLINE_CONSOLIDATION_C1_C4_COMPLETE / ENGINEERING_INTEGRATED / RECONSTRUCTION_TO_INTELLIGENCE_BRIDGE_REQUIRED / ACTIVE_MATCH_REVALIDATION_REQUIRED / NOT_PRODUCTION`

## NEXT PRODUCT ORDER
1. Reconstruction → Intelligence bridge/orchestration discovery and safe adaptation.
2. Fresh integrated-head ACTIVE_MATCH execution when the bridge contract is admitted.
3. Context Evidence Re-binding / Match Context Slicer on the current spine.
4. Analyst Episode Locator.
5. Rhythm / Change Detection.
6. Process Trace / Recurrence / Variation / Deviation.
7. Evidence/counterevidence reasoning expansion and analyst-safe output integration.
8. Spatial/progression, metric intelligence, visual/video evidence and cross-match profiling only through their own evidence/claim gates.

Pattern/recurrence intelligence must not precede context/episode grounding when doing so would manufacture meaning from unbound sequences.
