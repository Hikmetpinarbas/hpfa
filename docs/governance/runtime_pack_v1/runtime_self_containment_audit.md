# HPFA Runtime Self-Containment Audit V1

Date: 2026-06-22

Status: P0A_GOVERNANCE_FILE

## Purpose

This audit locks HPFA runtime authority boundaries before P1 ACTIVE_MATCH Analyst Report Lite V1.

HPFA must remain event-only, claim-safe, modular and portable.

## Runtime Authority Rule

Only this path can create runtime match truth:

```text
runtime/active_single_match/current
```

Termux example:

```text
/data/data/com.termux/files/home/hpfa_claim_integrity/hpfa/runtime/active_single_match/current
```

All other sources are REFERENCE_ONLY, DONOR_SUPPORT, GOVERNANCE_SUPPORT, ARCHIVE_SUPPORT or ACADEMIC_SUPPORT.

## Runtime Truth Boundary

Allowed as runtime evidence:

- files read directly from `runtime/active_single_match/current`
- command output from an ACTIVE_MATCH execution
- flat user-visible outputs written under `/sdcard/Download/HPFA` or `/storage/emulated/0/Download/HPFA`
- visible row-level evidence from the active match surface

Not allowed as runtime evidence:

- Google Drive planning files
- Dropbox archives
- Sider Scholar papers
- donor repositories
- old local samples
- old generated reports
- Termux discovery/spec artifacts outside ACTIVE_MATCH
- APP card TSV rows by themselves

## Row-Count Boundary

CSV/XML/XLSX row totals are not canonical events.

Allowed terms:

- surface rows
- visible rows
- event-like rows
- row-level evidence
- event-row evidence
- action-family volume

Blocked terms before Canonical Event Lite:

- canonical event count
- true event stream
- validated event truth
- complete event truth
- thousands of events

Runtime value:

```text
canonical_event_count = UNKNOWN
```

## Claim Boundary

HPFA runtime may emit:

- row-level evidence
- visible surface evidence
- action-family volume
- coordinate concentration
- candidate rhythm / sequence / phase language only when upstream gates exist

HPFA runtime must not emit:

- dominance truth
- coach intention
- tactical plan truth
- off-ball structure truth
- pitch control truth
- body orientation truth
- fatigue truth
- clean phase truth before claim gate

## Current Executable Core

Current executable product core:

- `canonical_ingest_surface_manifest`
- `boundary_analysis_scorer`
- `active_match_spine_runner`

Current root CLI:

- `boundary_analysis_scorer.py`
- `active_match_spine_runner.py`

## P1 Runtime Requirement

P1 ACTIVE_MATCH Analyst Report Lite V1 must read ACTIVE_MATCH surfaces and write flat outputs only:

```text
/sdcard/Download/HPFA/active_match_analyst_report_lite_v1.json
/sdcard/Download/HPFA/active_match_analyst_report_lite_v1.txt
```

It must not create nested phone output directories.

## Audit Result

Runtime self-containment status:

```text
RUNTIME_SELF_CONTAINMENT_RULE_LOCKED
```

This file is governance evidence only. It is not ACTIVE_MATCH execution evidence and not product release proof.
