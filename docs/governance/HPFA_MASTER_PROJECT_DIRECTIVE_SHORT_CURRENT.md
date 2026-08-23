# HPFA MASTER PROJECT DIRECTIVE — SHORT CURRENT

Version: 2026.08.23-BRIDGE-LANDED
Status: ACTIVE_GOVERNANCE_RECORD

## PROJECT
HPFA = Hikmet Pınarbaş Football Analytics.
Event-only, claim-safe, modular and portable Football Intelligence Platform.

HPFA produces football-behaviour evidence, pattern/sequence evidence, match-local identity evidence, rhythm/metric evidence and analyst-facing outputs without promoting unsupported tactical, causal, physical-action, possession or event truth.

## USER ROLE AND RUNTIME EVIDENCE
The user is a football analyst.
Every real runtime result must provide two separate evidence layers:
1. Engineering evidence: execution, tests, status, output paths, hard-block/review state.
2. Analyst evidence: what is visible on the match surface, where it appears, which evidence supports it and its safe analyst meaning.

## RUNTIME AUTHORITY
The sole ACTIVE_MATCH truth is:
`runtime/active_single_match/current`

Termux reference:
`/data/data/com.termux/files/home/hpfa_claim_integrity/hpfa/runtime/active_single_match/current`

Google Drive, Dropbox, PDFs, archives, reports, donor repos, academic literature and historical Termux apparatus are REFERENCE_ONLY / DONOR_SUPPORT. They never override ACTIVE_MATCH.

Termux/local historical material may be used as capability-recovery reserve under `ADAPT_NOT_COPY`; it becomes product capability only after adaptation into current hpfa, tests and applicable current-head runtime validation.

## REPOSITORY ROLES
- `hpfa`: only product repository.
- `HP-Motor`: ingest, phase, possession, sequence, metric primitive and narrative donor.
- `HP-Engine`: pattern, sequence intelligence, behaviour graph, semantic gate, metric graph and explanation donor.
- `HP-PROJELERI`: governance, policy, authority, release and registry donor.

## DONOR RULE
`ADAPT_NOT_COPY`

Required path:
current hpfa producer → donor capability → source role → boundary → HPFA contract → HPFA module → tests → ACTIVE_MATCH when applicable → engineering evidence → analyst evidence → football audit → release decision.

## SOURCE SEARCH ORDER BEFORE CODING
1. current hpfa main / current producer
2. HP-Motor
3. HP-Engine
4. HP-PROJELERI
5. Google Drive
6. Dropbox
7. academic support
8. Termux capability-recovery corpus

Code is the final step.

## CURRENT MAIN AUTHORITY
Authoritative product ref:
`refs/heads/main`

Controlled mainline landings:

```text
C1 Foundation
  merge=f3dc7b44d6bb899033a605a690f6cc51fb0199a4
  source_pr=#254

C2 Evidence Spine
  merge=871cd3c4948dd72b80aaa2983268811d7a22b39b
  source_pr=#263

C3 Reconstruction / Partial-Order
  merge=adb9c1d60cf98c79fd1de1c7a6df7b822c11496a
  source_pr=#267

C4 Intelligence Correctness / Integration
  merge=d23f868a5287811b4dc6e2912085aa85fd547a64
  source_pr=#278

Reconstruction → Intelligence Packet Bridge
  merge=ab8c9a7a3152108eeede5b3a2204d2d1fcb14726
  source_pr=#284
  exact_pr_head_active_match=9b3db1afb88b2d4c592a6c7eabae718c6ab993e8
```

Historical stacked commits were not replayed as a chronological merge train. Final reviewed capability states were landed as controlled units.

Main membership does not automatically establish ACTIVE_MATCH or production release.

## CURRENT PRODUCT SPINE

```text
Multiformat File Inventory
→ CSV / XLSX / XML Surface Readers
→ Provider Alias / Field / Label / Value Semantics
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
→ Partial-Order Hardening
→ Reconstruction → Intelligence Packet Adapter
→ Composite Evidence Packet
→ Multi-Signal Fusion
→ Composite Argument
→ Defeasible Argument Route
→ Evidence Graph
→ Safe Argument Router TR
→ Analyst Report Block
→ Report Output Contract
→ Final Report Assembly Gate
```

Evidence Lens Matrix consumes Evidence Graph as an explicit review sidecar. Missing lens coverage cannot be treated as evidence of absence.

## RECONSTRUCTION → INTELLIGENCE BRIDGE STATUS
The thin product bridge is now landed on main through PR #284.

Exact PR head runtime evidence:

```text
head=9b3db1afb88b2d4c592a6c7eabae718c6ab993e8
runtime_authority=runtime/active_single_match/current
run_rc=0
runtime_evidence_status=ACTIVE_MATCH_EVIDENCE_PASS
module_status=REVIEW_REQUIRED
source_visible_action_sequence_candidate_count=295
packet_input_candidate_count=295
composite_packet_count=295
blocked_composite_packet_count=0
review_required_packet_input_candidate_count=56
packet_input_assignment_complete=true
packet_contract_pass=true
partial_order_boundary_pass=true
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

Bundle SHA-256:
`33c363534fe932a07b22a9e462e2c3765ca8a4cf2f11cae5d4f9c8f58ca0a205`

This runtime evidence is bound to the exact PR head above. Because #284 was squash-merged, the merged main head still requires fresh ACTIVE_MATCH revalidation before merged-main runtime promotion.

## PARTIAL-ORDER AUTHORITY
Allowed states:

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
- missing or ambiguous order remains indeterminate;
- relation records cannot create action volume, sequence truth or possession truth;
- directly-later time does not establish causal/directly-follows football truth.

## SURFACE / COUNT RULES
CSV, TSV, XML, XLS/XLSX, JSON and JSONL are evidence surfaces.
Surface rows are not canonical events.

Use:
`surface rows`, `visible rows`, `event-like rows`, `row-level evidence`, `event-row evidence`, `action-family volume`, `candidate count`.

Do not infer:
- missing value = zero;
- missing column = absent behaviour;
- same timestamp = duplicate event;
- provider label = canonical event key;
- CSV/XML mirror = independent actions;
- XLSX aggregate row = timeline event.

Until explicit later admission:
`canonical_event_count=UNKNOWN`
`true_action_count=UNKNOWN`

## DUPLICATE / REFLECTION RULE
Same SHA-256 at different paths is an exact duplicate reflection/lineage observation, not automatically a conflict.
Duplicate/reflection lineage must not be counted twice as row/event/action/evidence volume or independent evidence votes.

## IDENTITY RULE
Provider fields, codes, aliases, team/player tokens and action labels begin as candidates.
Identity is match-local unless a later explicit registry proves otherwise.
Identity binding is not event truth.
No raw surface row directly becomes an event instance.

## CLAIM SAFETY
HPFA does not directly produce:
pitch-control truth, body-orientation truth, coach intention, dominance truth, fatigue truth, off-ball truth, tactical truth, clean phase truth, complete event-stream truth, sequence truth, possession truth, causal truth or physical-action truth without the relevant later gate.

Safe analyst language includes:
- row-level evidence shows...
- visible surface evidence indicates...
- action-family volume suggests...
- coordinate evidence is concentrated in...
- match-local identity candidate...
- sequence/rhythm candidate detected...
- requires later validation...

Blocked without later explicit admission:
- the team intentionally...
- the coach planned...
- dominated...
- controlled the pitch...
- off-ball structure proves...
- definitive tactical truth...

## ANALYST LANGUAGE
HPFA must not become a silent compliance system.
Main analyst text should state what was observed, where it was observed, which evidence supports it and why it matters.
Technical limitations and claim ceilings belong in a separate technical block.

## PHONE OUTPUT POLICY
All user-visible Termux outputs must be written directly under:
- `/sdcard/Download/HPFA`
- `/storage/emulated/0/Download/HPFA`

Nested output is rejected with:
`nested_phone_output_directory_rejected`

## MATCH-AGNOSTIC RULE
Product code must not hardcode match names, teams, dates, tournaments, sample IDs or sample row counts.
Generic input metadata is allowed.
Required regression:
`test_no_sample_match_identity_leak`

## RELEASE STATUS
PASS is not release.
CI SUCCESS is not ACTIVE_MATCH evidence.
ACTIVE_MATCH_EVIDENCE_PASS is not PRODUCTION_RELEASE.
MERGED is not PRODUCTION_RELEASE.
A moved exact head invalidates its prior exact-head readiness/runtime evidence unless regenerated.
Historical failed CI superseded by a newer green head is not a current blocker.

## CURRENT RELEASE STATE

```text
main_authority_ref=refs/heads/main
foundation_integrated=true
evidence_spine_integrated=true
reconstruction_integrated=true
intelligence_correctness_integrated=true
reconstruction_to_intelligence_runtime_bridge=true
bridge_pr_head_active_match_evidence=ACTIVE_MATCH_EVIDENCE_PASS
bridge_pr_head_status=REVIEW_REQUIRED
merged_main_head_active_match_revalidated=false
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

Status:
`BRIDGE_LANDED / PR_HEAD_ACTIVE_MATCH_EVIDENCE_PASS / REVIEW_REQUIRED_PRESERVED / MERGED_MAIN_ACTIVE_MATCH_REVALIDATION_REQUIRED / NOT_PRODUCTION`

## NEXT PRODUCT ORDER
1. Fresh ACTIVE_MATCH execution on the final current merged main head.
2. Context Evidence Re-binding on the current Reconstruction/Intelligence spine.
3. Analyst Episode Locator.
4. Rhythm / Change Detection.
5. Recurrence / Variation / Deviation.
6. Counterevidence / falsifier reasoning enrichment and analyst-safe language.
7. Metric Intelligence strengthening.
8. Spatial / Progression Evidence integration.
9. Relation Graph enrichment.
10. Video / Visual Evidence bridge.
11. Cross-match / player-team profiling after match-local foundations are stable.

Pattern/recurrence intelligence must not precede context/episode grounding when doing so would manufacture meaning from unbound sequences.
