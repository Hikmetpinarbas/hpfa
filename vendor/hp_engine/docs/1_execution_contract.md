# HP-ENGINE EXECUTION CONTRACT v1

## Purpose
HP-Engine produces decision-grade football intelligence by enforcing a single, auditable execution order.
No module (UI, analyzers, narrative) may bypass this contract.

## Immutable Execution Order
1. Ingest
2. Validate (schema, timebase, units, identity integrity)
3. Canonicalize (provider → canonical event model)
4. Compute Features (metric plugins; FULL/DEGRADED decided here)
5. Phase Attribution (F1–F6; proxy/full + confidence)
6. Claim Generation (1 main thesis + 2–3 supports + evidence refs)
7. Confidence & Falsifiability (Popper safety valve)
8. Package Output (single ReportPackage consumed by any channel)

## Hard Rules (Must Never Be Violated)
- No claim without computed features.
- No phase-dependent metric without a phase attribution.
- No published claim without a confidence value and falsifiable_by.
- Every feature MUST include:
  value, unit, mode(FULL|DEGRADED), lineage, confidence, requirements_met
- Every claim MUST include:
  statement, supports[], evidence[], confidence, falsifiable_by[]
- Every run MUST emit:
  run_id, engine_version, data_fingerprint, created_at

## Modes
- FULL: required data available; full-fidelity computation allowed.
- DEGRADED: required data missing; only approved proxies allowed. Must be explicitly labeled.

## Blocked Outputs
If a metric or claim cannot be produced with required minimum confidence or requirements_met=false, it is marked BLOCKED (never silently omitted or faked).