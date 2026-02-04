# HP-ENGINE OUTPUT CONTRACT v1 (ReportPackage)

## ReportPackage (JSON-serializable)
Required top-level keys:
- meta
- executive_summary
- phase_profile
- claims
- metrics_table
- evidence_index
- uncertainty

### meta
- match_id
- run_id
- engine_version
- data_fingerprint
- mode (FULL|DEGRADED)
- created_at

### executive_summary
- main_thesis (string)
- why_it_matters (string)
- what_to_do_next (list[string])
- confidence (0..1)

### phase_profile
- phases (dict: F1..F6 → {share, confidence, notes})

### claims (list)
Each claim:
- id
- statement
- supports (list of metric refs)
- evidence (list of evidence refs)
- confidence (0..1)
- falsifiable_by (list[string])
- mode (FULL|DEGRADED|MIXED)

### metrics_table (list)
Each metric row:
- canonical_name
- value
- unit
- family
- polarity
- mode (FULL|DEGRADED)
- confidence (0..1)
- lineage (source + derivation)

### evidence_index (list)
Each evidence item:
- id
- type (timestamp|clip|note)
- ref (e.g., "57:48")
- tags

### uncertainty (list)
- what_is_unknown
- why_unknown
- what_data_would_resolve