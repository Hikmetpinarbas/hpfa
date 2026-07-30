# HPFA MASTER PROJECT DIRECTIVE — SHORT CURRENT

Version: 2026.07.18-SHORT  
Status: CURRENT GOVERNANCE AUTHORITY  
Repository: Hikmetpinarbas/hpfa  
Runtime authority: `runtime/active_single_match/current`

## Product identity

HPFA is an event-only, claim-safe, modular and portable Football Intelligence Platform.
The `hpfa` repository is the only product repository. HP-Motor, HP-Engine,
HP-PROJELERI, Google Drive, Dropbox, archives and academic work are
`DONOR_SUPPORT` or `REFERENCE_ONLY`.

Donor rule: `ADAPT_NOT_COPY`.

## Evidence rule

Every real runtime result must separate:

1. engineering evidence: module execution, tests, output and status;
2. analyst evidence: what was visible, where it was visible, supporting evidence and safe meaning.

CSV, XML and XLSX row totals are surface rows, not canonical event counts.
`canonical_event_count=UNKNOWN` until Canonical Event Lite is validated.

## Event-derived phase correction

Validated time, order, team, action-family, restart and coordinate/zone evidence can
produce event-derived phase state. Phase derivation must not be confused with tactical
intent, off-ball structure, pressure, fatigue, pitch control or tracking truth.

Candidate upstream evidence may produce phase segments while `phase_truth=false`
remains closed until event identity and the relevant claim gate permit elevation.

## Product spine

RAW DATA → SOURCE AUTHORITY → ACTIVE MATCH → CANONICAL INGEST → DATA QUALITY GATE
→ GATE CONSUMER → PHASE → POSSESSION → SEQUENCE → METRIC CONTRACT
→ METRIC PRIMITIVES → PROGRESSION → CONTEXT → CLAIM GATE
→ FOOTBALL OUTPUT AUDIT → MATCH STORY → RUNTIME EVIDENCE

Implementation may use a two-pass refinement:

1. visible time/team/action continuity;
2. event-derived phase segmentation;
3. phase-aware sequence refinement.

## Runtime and phone policy

The only ACTIVE_MATCH truth is `runtime/active_single_match/current`.
User-visible Termux output must be flat under `/sdcard/Download/HPFA` or
`/storage/emulated/0/Download/HPFA`. Nested phone output is rejected.

## Release policy

`PASS` is not release. CI success, merge and ACTIVE_MATCH execution are distinct.
Production requires explicit release authority. Current PR-chain work remains
`NOT_PRODUCTION` unless separately elevated.

## Current integration state

- PR #164: file inventory node; ACTIVE_MATCH evidence exists; not merged.
- PR #205: visible sequence candidates; CI success; ACTIVE_MATCH execution remains review-bounded; not merged.
- PR #206: event-derived phase implementation; CI and ACTIVE_MATCH state must be read from its current head; not merged.

The former `2026.06.22-SHORT` directive is `SUPERSEDED_REFERENCE`.
