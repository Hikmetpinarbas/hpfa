# HPFA Gate Report Consumer V1

Purpose:

Read `gate_report.json` produced by Data Quality Gate V1 and convert it into explicit downstream permissions.

This module does not create event truth, does not validate football claims, and does not open the claim layer.

## Policy

- PASS:
  - phase / sequence allowed
  - metric evidence layer allowed
  - claim layer blocked

- DEGRADED:
  - phase / sequence allowed only in degraded mode
  - metric layer conditional
  - claim layer blocked

- FAIL_CLOSED:
  - all downstream analysis blocked

## Required input

`runtime_evidence/data_quality_gate_v1/gate_report.json`

## Boundary

This consumer is a policy reader. It does not run football analysis.
