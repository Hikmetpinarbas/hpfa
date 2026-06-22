# HPFA Core Data Quality Gate V1 ACTIVE_MATCH Execution Directive V1

NODE: hpfa_core_data_quality_gate_v1_active_match_execution_directive_v1
STATUS: READY_FOR_OPERATOR_EXECUTION

## Purpose

Move PR #8 from smoke-pass to ACTIVE_MATCH execution.

Smoke validation has passed. The next proof must come from Termux against the current ACTIVE_MATCH folder.

## Runtime Authority

ACTIVE_MATCH folder:

```text
runtime/active_single_match/current
```

Only this runtime surface can produce the next execution evidence.

## Required Operator Action

1. Work from a clean PR branch clone.
2. Locate event-like CSV or JSONL files under `runtime/active_single_match/current`.
3. Select one non-archive, non-reference, non-sample event surface.
4. Run `tools/hpfa_data_quality_gate_v1.py`.
5. Write both JSON report and TXT summary.
6. Record file size and SHA256 evidence.

## Required Outputs

```text
runtime_evidence/data_quality_gate_v1/gate_report.json
runtime_evidence/data_quality_gate_v1/gate_summary.txt
```

## Guardrails

- No registry write.
- No production binding.
- No football claim output.
- No PDF truth.
- No archive/sample/match_tests authority.
- No Sprint 2.

## Decision Meaning

PASS:
Phase/sequence and metric layers may proceed. Claim layer remains blocked.

DEGRADED:
Phase/sequence may proceed only in degraded mode. Metric layer is conditional. Claim layer remains blocked.

FAIL_CLOSED:
No downstream analysis proceeds.

## Next Node After Operator Output

hpfa_core_data_quality_gate_v1_active_match_execution_audit_v1
