> Status: `SUPERSEDED_REFERENCE`  
> Superseded by: `docs/governance/HPFA_MASTER_PROJECT_DIRECTIVE_SHORT_CURRENT.md`  
> This file is retained for lineage and must not be used as current authority.

# HPFA MASTER PROJECT DIRECTIVE — SHORT CURRENT

Version: 2026.06.22-SHORT
Project: HPFA — Hikmet Pınarbaş Football Analytics
Repository: Hikmetpinarbas/hpfa
Status: ACTIVE SHORT DIRECTIVE
Runtime authority: runtime/active_single_match/current

## Project

HPFA is an event-only, claim-safe, modular and portable Football Intelligence Platform.

HPFA does not only write reports. It produces football behaviour evidence, pattern evidence, sequence evidence, match identity, rhythm evidence and analyst-facing output.

The user is a football analyst. Every runtime result must produce two evidence layers:

1. engineering evidence: did the module run, did tests pass, was output written?
2. analyst evidence: what did the match surface show, which reading is safe, which output helps the analyst?

## Runtime Authority

Only runtime match truth:

runtime/active_single_match/current

Termux example:

/data/data/com.termux/files/home/hpfa_claim_integrity/hpfa/runtime/active_single_match/current

Not runtime truth:

Google Drive, Dropbox, Sider Scholar, PDFs, old archives, samples, reports, donor repositories and academic papers.

These are REFERENCE_ONLY or DONOR_SUPPORT.

## Repository Roles

hpfa = product repository. Executable product modules live here.

HP-Motor = donor for canonical ingest, phase, possession, sequence, metric primitives, brief and narrative discipline.

HP-Engine = donor for pattern discovery, sequence intelligence, behaviour graph, semantic gate, metric graph and explanation support.

HP-PROJELERI = donor for governance, policy, authority, release and registry rules.

## Donor Rule

ADAPT_NOT_COPY.

Required sequence:

current hpfa producer → donor capability → source role → boundary → HPFA contract → HPFA module → ACTIVE_MATCH execution → output evidence → football audit → release.

## Product Mode

HPFA is now in Product Engineering mode.

Every new idea must pass:

source role, target module, contract, test, ACTIVE_MATCH need, output, claim boundary, phone output, release status.

Code is the last step.

## Core Spine

RAW DATA → SOURCE AUTHORITY → ACTIVE MATCH → CANONICAL INGEST → DATA QUALITY GATE → GATE CONSUMER → PHASE → POSSESSION → SEQUENCE → METRIC CONTRACT → METRIC PRIMITIVES → PROGRESSION → CONTEXT → CLAIM GATE → FOOTBALL OUTPUT AUDIT → MATCH STORY → RUNTIME EVIDENCE

A downstream layer must not bypass an upstream gate.

## Claim Safety

HPFA must not directly produce:

pitch control truth, body orientation truth, coach intention, dominance truth, fatigue truth, off-ball truth, tactical truth, clean phase truth without claim gate.

Safe language:

- row-level evidence shows...
- visible surface evidence indicates...
- action-family volume suggests...
- coordinate evidence is concentrated in...
- rhythm-state candidate detected...
- requires later validation...

Forbidden language:

- takım bilinçli olarak...
- hoca planladı...
- domine etti...
- saha kontrolünü aldı...
- off-ball yapı...
- kesin tactical truth...

## Analyst Language

HPFA must not become a silent system.

Main analyst text should say:

what was visible, where it was visible, which evidence supports it, and what it means for the analyst.

Do not repeatedly explain what it is not. Limits belong in a separate technical block.

## Row-Count Correction

CSV, XML and XLSX row totals are not canonical events.

Correct terms:

surface rows, visible rows, event-like rows, row-level evidence, event-row evidence, action-family volume.

Do not use before Canonical Event Lite:

canonical event count, true event stream, validated event truth, complete event truth, thousands of events.

canonical_event_count = UNKNOWN.

## Phone Output Policy

All user-visible Termux outputs must be written flat under:

/sdcard/Download/HPFA

or:

/storage/emulated/0/Download/HPFA

Nested output is forbidden.

Invalid example:

/sdcard/Download/HPFA/spine-run/output.txt

Nested path must be rejected with:

nested_phone_output_directory_rejected

## Match-Agnostic Rule

Development ACTIVE_MATCH may contain a real match.

Product code must not hardcode match name, team name, date, competition, sample id or sample row count.

Generic metadata read from input is allowed.

Mandatory test:

test_no_sample_match_identity_leak

## Current Main State

P0 technical blocker is closed.

PR #27 merged:

Reject nested phone output directories
merge_commit_sha=4ea077c88f4a12d0234b352fde60b4fadcc1672f

PR #28 merged:

Add 2026-06-22 HPFA handoff directives
merge_commit_sha=6b012c1aee2720f6b1cbc0820c254dd5d503c117

Main executable core:

- canonical_ingest_surface_manifest
- boundary_analysis_scorer
- active_match_spine_runner

Root CLI:

- boundary_analysis_scorer.py
- active_match_spine_runner.py

## Source Roles

- GITHUB_PRODUCT_REPO
- GITHUB_DONOR_REPO
- DRIVE_GOVERNANCE
- DRIVE_DONOR_LIBRARY
- DROPBOX_ARCHIVE
- DROPBOX_DONOR_LIBRARY
- SIDER_ACADEMIC_BACKING
- TERMUX_RUNTIME_EVIDENCE
- ACTIVE_MATCH_RUNTIME_AUTHORITY

## Release Status

PASS has no single meaning.

Status vocabulary:

- DISCOVERY_PASS_PLAN_ONLY
- POLICY_CORRECTION_PASS
- SPEC_ONLY
- SPEC_CORRECTION_ACCEPTED
- SMOKE_PASS
- REVIEW_REQUIRED
- FAIL_CLOSED
- WAITING_OPERATOR_SELECTION
- RELEASE_CANDIDATE_NOT_PRODUCTION_BOUND
- ACTIVE_MATCH_EVIDENCE_PASS
- PRODUCTION_RELEASE

Rules:

PASS ≠ RELEASE.
SMOKE_PASS ≠ ACTIVE_MATCH evidence.
PLAN_ONLY ≠ executable module.
RELEASE_CANDIDATE ≠ production release.

## Current Product Order

P0A Product Governance Runtime Pack V1
P1 ACTIVE_MATCH Analyst Report Lite V1
P2 Canonical Event Lite V1
P3 Team Binding Lite V1
P4 Time / Phase Lite V1
P5 Possession Boundary Apparatus Lite V1
P6 Event Consequence Surface Lite V1
P7 Metric Primitive Lite V1
P8 Event-Only Rhythm Evidence Stack V12
P9 Claim Eligibility Gate Lite V1
P10 Claim-Safe Report Grammar Gate V1
P11 Football Output Audit Lite V1

## P0A Governance Pack

Required files:

1. source_role_registry.json
2. release_status_normalizer.json
3. module_governance_matrix.tsv
4. runtime_self_containment_audit.md
5. github_branch_truth_audit.md
6. phone_output_policy_audit.md
7. next_node_decision.md

## P1 Analyst Report Lite

Output:

/sdcard/Download/HPFA/active_match_analyst_report_lite_v1.json
/sdcard/Download/HPFA/active_match_analyst_report_lite_v1.txt

Content:

match snapshot, surface inventory, action-family volume, zone/channel distribution, team row-volume, goalkeeper/restart signal, pass/shot/duel/carry/loss/recovery block, analyst reading, missing-column report, technical limits.

## Event-Only Rhythm V12

APP-EVENT-ONLY-RHYTHM-EVIDENCE-001

Status: SPEC_CORRECTION_ACCEPTED.

STFT is not the core classifier. It is an optional spectral diagnostic channel.

Primary methods:

entropy, Markov transition matrix, zone transition matrix, point-process intensity, change-point detection, sequence motif/network support, rhythm state engine, claim router adapter.

Rhythm states:

S0 DEAD_LOW_SIGNAL
S1 LOW_ENTROPY_CIRCULATION
S2 STRUCTURED_BUILDUP
S3 ORGANIZED_PROGRESSION
S4 TRANSITION_SURGE
S5 HIGH_VOLATILITY_SCRAMBLE
S6 RECOVERY_STABILIZATION
S7 TERMINAL_PRESSURE
S8 DIRECT_PLAY_ISOLATION

Rule:

No rhythm state can be assigned from one signal alone.

Rhythm V12 implementation waits until canonical event lite, sequence candidate and signal density gate exist.

## Fitness Signal

APP-FITNESS-SIGNAL-SUPPORT-001

Fitness, load, GPS, HRV, wellness and RPE data may be support signals.

They are not runtime event truth.

They do not produce tactical truth.

They cannot override ACTIVE_MATCH evidence.

## Search Order Before Coding

1. hpfa current main
2. HP-Motor
3. HP-Engine
4. HP-PROJELERI
5. Google Drive governance / donor library
6. Dropbox archive / donor library
7. Sider Scholar academic support
8. Termux discovery reports

Code is last step.
