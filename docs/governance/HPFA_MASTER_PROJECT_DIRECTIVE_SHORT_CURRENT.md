# HPFA MASTER PROJECT DIRECTIVE — SHORT CURRENT

Version: 2026.07.17-SHORT
Status: ACTIVE_GOVERNANCE_RECORD

## PROJECT
HPFA = Hikmet Pınarbaş Football Analytics.
Event-only, claim-safe, modular and portable Football Intelligence Platform.
HPFA produces football-behaviour evidence, pattern evidence, sequence candidates, match-local identity evidence, rhythm candidates, metric evidence and analyst-facing outputs.

## USER ROLE AND REQUIRED EVIDENCE
The user is a football analyst.
Every runtime result must provide two separate evidence layers:
1. engineering evidence: module execution, tests, status, output paths and failure/review hits;
2. analyst evidence: what is visible on the match surface, where it appears, which evidence supports it and what it safely means for analysis.

## RUNTIME AUTHORITY
The only match-runtime authority is:
`runtime/active_single_match/current`

Termux reference:
`/data/data/com.termux/files/home/hpfa_claim_integrity/hpfa/runtime/active_single_match/current`

The Git product checkout and ACTIVE_MATCH runtime directory are separate paths.
Google Drive, Dropbox, PDFs, archives, samples, reports, donor repositories and academic papers are REFERENCE_ONLY / DONOR_SUPPORT. They do not override ACTIVE_MATCH.

## REPOSITORY ROLES
- `hpfa`: only product repository; executable product modules are born here.
- `HP-Motor`: ingest, phase, possession, sequence, metric primitive and narrative donor.
- `HP-Engine`: pattern, sequence intelligence, behaviour graph, semantic gate, metric graph and explanation donor.
- `HP-PROJELERI`: governance, policy, authority, registry and release donor.

## DONOR RULE
`ADAPT_NOT_COPY`

Required path:
current hpfa producer → donor capability → source role → claim boundary → HPFA contract → HPFA module → tests → ACTIVE_MATCH execution → engineering evidence → analyst evidence → football audit → release decision.

## PRODUCT MODE
HPFA is in Product Engineering mode.
Every new capability must declare:
source role, target module, input/output contract, deterministic tests, ACTIVE_MATCH need, claim ceiling, phone output, dependency order and release status.
Code is the final step, not the first.

## CURRENT CORE SPINE
RAW DATA → SOURCE AUTHORITY → ACTIVE MATCH → SURFACE INVENTORY → SOURCE ALIGNMENT → CANONICAL INTAKE → DATA QUALITY GATE → GATE CONSUMER → IDENTITY → TIME/PERIOD → SEMANTIC ROLE → ACTION BUNDLE → RELATION → POSSESSION/SEQUENCE/PHASE CANDIDATES → METRIC/CONTEXT → CLAIM GATE → FOOTBALL OUTPUT AUDIT → MATCH STORY → RUNTIME EVIDENCE

## MAIN TRUTH
Current main reference:
`0605abadcc6455b4852905a5aa2a52d51380e6f3`

Main includes the established runtime spine plus merged modules such as:
- `canonical_ingest_surface_manifest`
- `boundary_analysis_scorer`
- `active_match_spine_runner`
- `core_pipeline_orchestrator_lite_v1`
- `triplex_source_alignment_adapter_lite_v1`

A merged module may still be `IMPLEMENTED_NOT_RUNTIME_PROVEN`. Main membership does not automatically establish ACTIVE_MATCH evidence or production release.

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

## IDENTITY AND EVENT ADMISSION
Identity is match-local unless a later explicit global registry proves otherwise.
Identity binding is not event truth.
Provider IDs, aliases, team tokens and actor names remain evidence-backed candidates until their gate passes.
No raw surface row directly becomes an event instance.
Required order:
evidence atom → match-local identity → time/period → semantic role → action bundle → cross-role relation → aggregate reconciliation → admission gate.

## CLAIM SAFETY
HPFA does not directly produce:
pitch-control truth, body-orientation truth, coach intention, dominance truth, fatigue truth, off-ball truth, tactical truth, clean phase truth or complete event-stream truth.

Safe language:
- row-level evidence shows...
- visible surface evidence indicates...
- action-family volume suggests...
- coordinate evidence is concentrated in...
- match-local identity candidate...
- sequence/rhythm candidate detected...
- requires later validation...

Blocked language without a later explicit gate:
- the team intentionally...
- the coach planned...
- dominated...
- controlled the pitch...
- off-ball structure proves...
- definitive tactical truth...

## ANALYST LANGUAGE
HPFA must not become a silent compliance system.
The main analyst text states:
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
- open, draft or stacked PRs are not main truth.
- historical failed runs superseded by a newer green head are not current blockers.
- a moved head invalidates prior current-head readiness and runtime evidence unless explicitly regenerated.

## CURRENT OPEN PRODUCT PATH
The current ingest-modernisation path is stacked and remains outside main:
1. PR #164 — Multiformat File Inventory Lite V1.
   Current-head ACTIVE_MATCH evidence exists; not merged; not production.
2. PR #166 — CSV Surface Reader Lite V1, stacked on PR #164.
   Current-head CI succeeds; corrected-head ACTIVE_MATCH revalidation is required; not merged; not production.

The older event-admission stack (#155, #157, #158, #159 and composite #161) remains review/decomposition territory. Composite PR #161 must not merge as one change.

## CURRENT PRODUCT ORDER
1. Multiformat File Inventory
2. CSV Surface Reader
3. XLSX Surface Reader
4. XML Surface Reader
5. Provider alias and field semantics
6. Cross-format reconciliation
7. Aggregate definition alignment
8. Row nuclei and G01–G18 gate rollup
9. Evidence atoms and match-local identity
10. Semantic roles, action bundles and cross-role relations
11. Context, possession, sequence, phase, metric and visual evidence
12. Claim gate, grammar gate, football output audit and analyst report integration

## RHYTHM AND FITNESS
Event-Only Rhythm Evidence Stack remains downstream of canonical event lite, sequence candidates and a signal-density gate.
No rhythm state may be assigned from one signal alone.
Fitness/load/GPS/HRV/wellness/RPE data may support analysis but cannot override ACTIVE_MATCH event evidence or create tactical/fatigue truth.

## SOURCE SEARCH ORDER BEFORE CODING
1. hpfa current main
2. relevant open product PR
3. HP-Motor
4. HP-Engine
5. HP-PROJELERI
6. Drive governance/donor library
7. Dropbox archive/donor library
8. academic support
9. Termux discovery and runtime reports

CODE IS LAST STEP.
