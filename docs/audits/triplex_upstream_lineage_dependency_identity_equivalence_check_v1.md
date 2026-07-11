# Triplex Source Alignment Guard V1 — Upstream Lineage / Dependency Identity Equivalence Check

Status: `DISCOVERY_PASS_PLAN_ONLY`

Repository authority: `Hikmetpinarbas/hpfa`

Main SHA audited: `6cc540399d56e52c021a3a02e3f72b416d393184`

Runtime authority: `runtime/active_single_match/current`

Canonical event count: `UNKNOWN`

Policy: `ADAPT_NOT_COPY`

## Scope

This is the first of four narrow current-main equivalence searches required by the Triplex donor-to-current-main field delta audit. It checks only whether current main contains an executable producer that can identify a surface's upstream origin, compare lineage across surfaces, or adjudicate whether CSV/XML/XLSX surfaces are independent, derived, duplicated or dependent.

Search terms included:

- `upstream`
- `origin`
- `lineage`
- `dependency`
- `source_provenance`
- `fingerprint`
- `duplicate surface`
- `derived surface`

`NOT_FOUND` below means no required executable equivalence was resolved in this bounded search. It is not proof of absolute repository-wide absence.

## Resolved adjacent current-main behavior

### HPFA Data Quality Gate V1

`tools/hpfa_data_quality_gate_v1.py` is executable and records row-local lineage as source line numbers:

```text
__row_lineage__ = {line_no: ...}
```

It also audits duplicate event identifiers inside one loaded CSV or JSONL surface.

This is reusable for row traceability and single-surface duplicate-event validation, but it does not:

- identify the upstream producer or export origin of a file;
- compare lineage between CSV, XML and XLSX surfaces;
- determine whether two surfaces are independent;
- detect that one surface was derived from another;
- assign an independence group;
- emit a cross-surface dependency or duplicate-surface decision.

Classification for Triplex upstream-lineage equivalence: `PARTIAL` prerequisite only.

### Source Mapping Contract Lite V1

The contract and executable module preserve visible source metadata such as source file, format, role, field name and row/source mapping context. The contract explicitly states that it does not deduplicate events or select a primary event surface.

The contract's wording that “source lineage is available for later gates” describes visible mapping/row traceability, not an implemented upstream-origin or dependency adjudicator.

Classification for Triplex upstream-lineage equivalence: `PARTIAL` prerequisite only.

### Canonical Ingest Surface Manifest

The manifest provides visible file identity, relative path, format, role and surface-family inventory. It is a suitable input surface for a future dependency gate, but no executable upstream-origin identifier, lineage graph, independence group, or cross-surface duplicate/dependency decision was resolved.

Classification for Triplex upstream-lineage equivalence: `PARTIAL` prerequisite only.

## Required capability versus current-main evidence

| Required Triplex behavior | Current-main evidence | Result |
|---|---|---|
| Stable upstream-origin identifier | visible file/path metadata only | `GAP` |
| Cross-surface lineage comparison | no executable comparator resolved | `GAP` |
| Derived-surface detection | no executable producer resolved | `GAP` |
| Duplicate/dependent-surface adjudication | single-surface duplicate event-id gate only | `PARTIAL` |
| Independence-group assignment | no executable producer resolved | `GAP` |
| Typed downgrade/block decision for dependent surfaces | no executable producer resolved | `GAP` |
| Row-level source traceability | line-number lineage and mapping context exist | `PRESENT_ADJACENT` |

## Classification

```text
CAPABILITY GROUP = upstream lineage / dependency identity
CURRENT-MAIN EXECUTABLE EQUIVALENT = NOT_FOUND
CURRENT-MAIN ADJACENT PREREQUISITES = PARTIAL
RUNTIME STATUS = NOT_RUNTIME_PROVEN
ACTIVE_MATCH_PROVEN = NO
DONOR CODE COPIED = NO
PRODUCT IMPLEMENTATION CHANGED = NO
```

This does not change the parent Triplex capability classification:

```text
Triplex Source Alignment Guard V1
primary_status = NOT_FOUND
runtime_status = NOT_RUNTIME_PROVEN
adjacent_prerequisites = PARTIAL
```

## Engineering evidence

- current-main SHA pinned: yes
- executable data-quality gate inspected: yes
- source-mapping contract boundary inspected: yes
- capability-equivalence classification recorded: yes
- donor implementation copied: no
- product runtime modified: no
- tests executed: no
- merge authorized: no

## Analyst evidence

No match was analyzed and no football-performance claim was generated.

Potential product value only: an upstream-lineage gate would prevent multiple exports from the same source chain from being counted as independent corroborating evidence.

## Claim boundary

```text
canonical_event_count = UNKNOWN
source independence truth = false
upstream lineage truth = false
cross-surface duplicate truth = false
fusion admissibility truth = false
production release = false
```

## Smallest next verification

Proceed to the second unresolved capability group only:

```text
XLSX formula or derived-surface detection
```

Search current main for executable workbook/formula inspection, cached-value detection, manual-versus-derived classification and fail-closed independence handling. Do not implement an adapter until all four equivalence searches are complete.