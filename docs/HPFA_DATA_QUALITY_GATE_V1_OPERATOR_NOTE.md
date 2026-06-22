# HPFA Data Quality Gate V1 Operator Note

Node: hpfa_core_data_quality_gate_executable_stub_v1
Status: EXECUTABLE_STUB_NOT_PRODUCTION_BOUND

## What changed

A first executable gate was added at:

`tools/hpfa_data_quality_gate_v1.py`

This is not a product release. It is a safe executable stub that turns previous plan-only Data Quality Gate work into a concrete command-line gate.

## Football product meaning

This gate is the pre-analysis control room. It checks whether an event surface is healthy enough before phase, sequence, metric, claim, or report modules are allowed to use it.

## Current gate families implemented

- G01 schema gate
- G02 duplicate event id gate
- G03 coordinate boundary gate
- G04 temporal order gate
- G05 team identity gate
- G07 period gate
- G09 reference exclusion gate

## Output states

- PASS: downstream modules may use the event surface
- DEGRADED: downstream modules may run only with warning and limited output
- FAIL_CLOSED: downstream product analysis must not run

## Command pattern

```bash
python tools/hpfa_data_quality_gate_v1.py <events.csv_or_jsonl> --out runtime_evidence/data_quality_gate/gate_report.json
```

## Claim safety

The tool emits no football claims. It only emits gate decisions and audit reasons.

## Authority boundary

This tool does not replace ACTIVE_MATCH validation. Runtime proof still requires Termux ACTIVE_MATCH execution.

The tool rejects paths containing reference/archive/sample markers such as:

- pdf
- reference
- archive
- sample
- match_tests
- match001
- quarantine

## What this unlocks

This is the first concrete support spine piece needed before:

1. phase_sequence_composite
2. metric_primitive_library
3. claim_gate_engine
4. registry_audit_engine
5. PROGRESSION_ENGINE production binding

## What remains blocked

- registry write
- production binding
- Sprint 2 start
- progression claim output
- PDF/reference/archive/sample as event truth
