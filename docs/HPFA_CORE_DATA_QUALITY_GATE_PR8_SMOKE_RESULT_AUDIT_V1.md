# HPFA Core Data Quality Gate PR8 Smoke Result Audit V1

NODE: hpfa_core_data_quality_gate_pr8_smoke_result_audit_v1
STATUS: SMOKE_PASS

## Source

Operator executed a clean clone smoke run on Termux.

Repository: Hikmetpinarbas/hpfa
Branch: hpfa-core-data-quality-gate-v1
Working copy: /data/data/com.termux/files/home/hpfa_pr8_work

## Command

```bash
bash tools/hpfa_data_quality_gate_v1_smoke.sh
```

## Observed Output

```text
{"status": "PASS", "out": "/data/data/com.termux/files/usr/tmp/hpfa_dqg_smoke/gate_report.json", "row_count": 3}
{"status": "FAIL_CLOSED", "out": "/data/data/com.termux/files/usr/tmp/hpfa_dqg_smoke/archive_gate_report.json", "row_count": 3}
{"status": "DEGRADED", "out": "/data/data/com.termux/files/usr/tmp/hpfa_dqg_smoke/no_coordinates_gate_report.json", "row_count": 2}
{"status": "FAIL_CLOSED", "out": "/data/data/com.termux/files/usr/tmp/hpfa_dqg_smoke/bad_jsonl_gate_report.json", "row_count": 2}
HPFA_DQG_SMOKE_PASS
WORKDIR=/data/data/com.termux/files/usr/tmp/hpfa_dqg_smoke
```

## Smoke Coverage

- valid minimal CSV returns PASS
- archive/sample path returns FAIL_CLOSED
- missing coordinates returns DEGRADED
- invalid JSONL returns FAIL_CLOSED through parse handling

## Product Meaning

The data quality gate is no longer only a static script. It can run, produce JSON reports, produce summaries and block or allow downstream layers through next_action.

## Limits

This is smoke validation only.

ACTIVE_MATCH proof is still pending.

Registry write: NO
Production binding: NO
Football claims: NO
Sprint 2: NO

## Decision

SMOKE_PASS_ACCEPTED

## Next Node

hpfa_core_data_quality_gate_v1_active_match_execution
