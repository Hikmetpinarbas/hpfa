# HPFA MASTER PROJECT DIRECTIVE — SHORT CURRENT

Version: 2026.07.18-SHORT
Status: CURRENT GOVERNANCE AUTHORITY
Repository: Hikmetpinarbas/hpfa

## AUTHORITY RESOLUTION
This file, when landed on `main`, is the single unqualified repository governance authority.

The development checkpoint is a frozen product-development snapshot, not a second governance authority. Any `CURRENT` wording embedded inside a non-main development snapshot is historical snapshot content and does not override this main governance record.

Three authorities are separate and must never substitute for one another:

1. `PRODUCT_MAIN` — code actually accepted into `main`.
2. `DEVELOPMENT_CHECKPOINT` — the current integration reference outside main.
3. `ACTIVE_MATCH_RUNTIME` — the only match-runtime truth at `runtime/active_single_match/current`.

Current machine-readable values are recorded in:
`docs/governance/HPFA_DEVELOPMENT_CHECKPOINT_CURRENT.json`

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
During controlled mainline consolidation, new independent intelligence features are temporarily secondary.

Allowed consolidation-period changes are limited to:
1. upstream semantic/data bug corrections found by ACTIVE_MATCH;
2. changes required to integrate the existing product spine;
3. fail-closed blocker corrections discovered during integration/revalidation.

Every capability must still declare:
source role, target module, input/output contract, deterministic tests, ACTIVE_MATCH need, claim ceiling, phone output, dependency order and release status.
Code is the final step, not the first.

## CURRENT CORE SPINE
RAW DATA → SOURCE AUTHORITY → ACTIVE MATCH → SURFACE INVENTORY → SOURCE ALIGNMENT → CANONICAL INTAKE → DATA QUALITY GATE → GATE CONSUMER → IDENTITY → TIME/PERIOD → SEMANTIC ROLE → ACTION BUNDLE → RELATION → POSSESSION/SEQUENCE/PHASE CANDIDATES → METRIC/CONTEXT → CLAIM GATE → FOOTBALL OUTPUT AUDIT → MATCH STORY → RUNTIME EVIDENCE

Event-derived phase candidates may be produced from validated time, order, team, action-family, restart and coordinate/zone evidence, but phase derivation is not tactical intent, off-ball structure, pressure, fatigue, pitch control or tracking truth.

Implementation may use a two-pass refinement:
1. visible time/team/action continuity;
2. event-derived phase segmentation;
3. phase-aware sequence refinement.

## MAIN AND DEVELOPMENT TRUTH
`main` is the product truth for accepted repository code.
Open, draft or stacked PRs are not main truth.

The development checkpoint is an integration reference only. It may contain capabilities with valid CI or ACTIVE_MATCH evidence, but those capabilities become main truth only after controlled landing and revalidation.

The current consolidation policy is tracked in Issue #244 and the integration/governance debt in Issue #233.

No blind stack-wide rebase, giant merge, or chronological historical-PR merge train is allowed.
Landing units are final capability snapshots: later hardening and bug fixes that semantically belong to an earlier capability must be included in that capability's integration snapshot.

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

Evidence may be promoted through explicit, reversible levels such as:
`RAW_SURFACE → EVIDENCE_ATOM → SUPPORTED_CANDIDATE → RECONCILED_CANDIDATE → ANALYST_USABLE_EVIDENCE → METRIC_ELIGIBLE → CLAIM_ELIGIBLE`.

`TACTICAL_TRUTH` is not a mandatory final promotion state.

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
- MERGED is not PRODUCTION_RELEASE.

## CONTROLLED LANDING ORDER
During consolidation, capabilities are landed by final-state dependency, not by historical PR date.

Tranche 0 — Governance / authority normalization.
Tranche 1 — Data foundation: inventory → CSV/XLSX/XML readers → field semantics → label/value semantics → reconciliation → aggregate/metric-definition support → row nuclei → G01–G18.
Tranche 2 — Evidence spine: evidence atoms → match-local identity → semantic roles → action bundles → multi-family taxonomy → cross-role relations.
Tranche 3 — Behaviour / sequence / context: selected action → consequence → selected event consequence → visible sequence → event-derived phase → phase refinement → match context → outcome support.
Tranche 4 — Coordinate / progression preconditions.
Tranche 5 — Modular runtime orchestrator.
Tranche 6 — Analyst product: Analyst Report + Evidence Notebook + Engineering Audit.

Every runtime-relevant tranche requires fresh exact integration-head CI and ACTIVE_MATCH revalidation before merge consideration.

## RHYTHM AND FITNESS
Event-Only Rhythm Evidence Stack remains downstream of canonical event lite, sequence candidates and a signal-density gate.
No rhythm state may be assigned from one signal alone.
Fitness/load/GPS/HRV/wellness/RPE data may support analysis but cannot override ACTIVE_MATCH event evidence or create tactical/fatigue truth.

## SOURCE SEARCH ORDER BEFORE CODING
1. hpfa current main
2. relevant current development checkpoint / product PR
3. HP-Motor
4. HP-Engine
5. HP-PROJELERI
6. Drive governance/donor library
7. Dropbox archive/donor library
8. academic support
9. Termux discovery and runtime reports

CODE IS LAST STEP.

## RELEASE AUTHORITY
No merge, release, production marking or production binding may be performed without explicit user approval.

Until explicitly released:
`production_release=false`
