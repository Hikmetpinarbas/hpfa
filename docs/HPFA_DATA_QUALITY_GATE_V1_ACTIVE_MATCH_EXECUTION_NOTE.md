# HPFA Data Quality Gate V1 ACTIVE_MATCH Execution Note

STATUS: EXECUTION_NOTE_NOT_RUNTIME_PROOF

## Purpose

Document the command pattern for running the data quality gate on ACTIVE_MATCH.

This document is not proof. Proof exists only after Termux ACTIVE_MATCH execution writes evidence files.

## Command Pattern

```bash
python tools/hpfa_data_quality_gate_v1.py \
  runtime/active_single_match/current/<events_file>.csv \
  --out runtime_evidence/data_quality_gate_v1/gate_report.json \
  --summary-out runtime_evidence/data_quality_gate_v1/gate_summary.txt
```

For JSONL:

```bash
python tools/hpfa_data_quality_gate_v1.py \
  runtime/active_single_match/current/<events_file>.jsonl \
  --out runtime_evidence/data_quality_gate_v1/gate_report.json \
  --summary-out runtime_evidence/data_quality_gate_v1/gate_summary.txt
```

## Expected Outputs

- gate_report.json
- gate_summary.txt

## Status Meaning

PASS:
Phase sequence and metric layers may run. Claim layer remains blocked.

DEGRADED:
Phase sequence may run in degraded mode. Metric layer is conditional. Claim layer remains blocked.

FAIL_CLOSED:
No downstream analysis is allowed.

## Guardrails

- No registry write.
- No production binding.
- No football conclusion.
- No PDF truth.
- No archive or sample authority.
- No Sprint 2.
