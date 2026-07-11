# Triplex XLSX Formula / Derived-Surface Equivalence Check V1

## Scope

This audit records one bounded current-main capability-equivalence search for the Triplex Source Alignment Guard dependency:

```text
XLSX formula / derived-surface detection
```

Current-main baseline:

```text
6cc540399d56e52c021a3a02e3f72b416d393184
```

Truth boundary:

```text
canonical_event_count=UNKNOWN
ACTIVE_MATCH_PROVEN=false
production_release=false
```

## Current-main executable evidence

`tools/hpfa_ingest_v1.py` contains an executable XLSX reader:

```python
wb = openpyxl.load_workbook(path, data_only=True)
```

The reader then iterates `values_only=True` and emits visible cell values into JSONL records.

This establishes only that current main can ingest workbook cached/display values. It does not preserve or adjudicate formula origin.

## Capability result

```text
workbook formula presence inspection        = NOT_FOUND
formula text capture                        = NOT_FOUND
cached-value presence inspection            = PARTIAL_IMPLICIT
formula/manual/unknown classification       = NOT_FOUND
derived-from-source metadata                = NOT_FOUND
independence-group decision                  = NOT_FOUND
fail-closed derived-surface handling         = NOT_FOUND
```

`data_only=True` is not formula detection. It suppresses formula expressions and returns cached values when present. Therefore a formula-derived workbook cell can be indistinguishable from a manually entered value in the emitted surface.

## Product classification

```text
capability_group = XLSX_FORMULA_DERIVED_SURFACE_DETECTION
primary_status = PARTIAL
runtime_status = NOT_RUNTIME_PROVEN
ACTIVE_MATCH_PROVEN = NO
```

`PARTIAL` is used only because an executable XLSX value reader exists. No executable current-main equivalent was resolved for formula-origin detection or derived-surface admission control.

## Claim boundary

The current reader must not be treated as evidence that:

- XLSX values are independent of CSV/XML sources;
- formulas are absent;
- cached values are current;
- workbook cells are manually authored;
- unit, denominator or observation window are compatible;
- an XLSX surface is safe for independent corroboration.

## Minimum future adapter boundary

A later HPFA-native adapter should inspect workbooks in both formula and cached-value modes and emit at least:

```text
cell_origin = FORMULA | MANUAL | EMPTY | UNKNOWN
formula_present
cached_value_present
formula_reference_surface
surface_dependency_state
admission_decision
```

Required fail-closed decisions should include:

```text
BLOCK_INDEPENDENCE_CLAIM
DOWNGRADE_DERIVED_SURFACE
REVIEW_UNKNOWN_FORMULA_ORIGIN
```

This is a contract boundary only. No donor code or pseudocode is copied, and no implementation authorization is granted by this audit.

## Tests

```text
tests_executed = false
tests_passed = NOT_CLAIMED
```

Future deterministic tests must include:

- formula cell with cached value;
- formula cell without cached value;
- manual numeric cell;
- mixed formula/manual column;
- external workbook reference;
- formula-origin metadata missing;
- no sample match identity leakage.

## Release status

```text
DISCOVERY_PASS_PLAN_ONLY
```
