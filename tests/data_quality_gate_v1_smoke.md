# Data Quality Gate V1 Smoke Checklist

This checklist is intentionally non-runtime. Real execution proof must come from Termux ACTIVE_MATCH.

## Command

```bash
python tools/hpfa_data_quality_gate_v1.py runtime/active_single_match/current/<events_file>.csv --out runtime_evidence/data_quality_gate_v1/gate_report.json
```

## Expected report fields

- tool
- status
- input
- input_format
- row_count
- claim_safety
- authority_note
- findings

## Expected status values

- PASS
- DEGRADED
- FAIL_CLOSED

## Minimum acceptance for next node

- The command returns zero.
- The output JSON is created.
- The status is not missing.
- G09_REFERENCE_EXCLUSION is PASS for ACTIVE_MATCH path.
- The report says NO_FOOTBALL_CLAIMS_EMITTED.

## FAIL_CLOSED triggers to verify later in Termux

- Input path contains archive.
- Input path contains sample.
- Input path contains reference.
- Required semantic fields are missing.
- Duplicate event id rate exceeds threshold.
- Temporal backward jump rate exceeds threshold.
- Coordinate bad rate exceeds threshold.

## Downstream rule

Phase, sequence, metric, claim and report layers must not run if status is FAIL_CLOSED.
