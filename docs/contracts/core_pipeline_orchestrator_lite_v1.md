# HPFA Core Pipeline Orchestrator Lite V1

Status: `IMPLEMENTATION_WRITTEN_EXECUTION_PENDING`

Product authority: `Hikmetpinarbas/hpfa`

Runtime authority: `runtime/active_single_match/current`

## Purpose

Provide one deterministic, fail-closed execution controller for HPFA modules without moving football logic, metric computation, canonicalization or claim decisions into the orchestrator.

The orchestrator is a workflow controller, not an analysis engine.

```text
ordered stage specifications
+ one explicit initial artifact
+ HPFA-native producer functions
-> validated stage execution
-> failure/review propagation
-> deterministic stage ledger
-> final artifact
```

## Architecture role

```text
ENGINE MODULES
-> CORE PIPELINE ORCHESTRATOR
-> REPEATABLE ACTIVE_MATCH RUN
-> STABLE ARTIFACTS
-> FUTURE SERVICE BOUNDARY
```

It sits after module contracts and before any service/API layer.

## Non-goals

The module does not:

- discover stages dynamically;
- calculate football metrics;
- infer phase, possession or sequence truth;
- generate football claims;
- call donor repositories at runtime;
- call AI services;
- use network access;
- retry failed football logic silently;
- repair malformed producer output;
- promote `SMOKE_PASS` to `ACTIVE_MATCH_EVIDENCE_PASS`;
- produce a production release.

## Input contract

### Pipeline input

- `run_id`: explicit non-empty identifier supplied by the caller;
- `initial_artifact`: dictionary produced by an upstream HPFA module or adapter;
- `stages`: ordered `StageSpec` sequence.

### StageSpec

- `stage_id`;
- `input_artifact_type`;
- `output_artifact_type`;
- `runner`;
- `halt_on_review`.

The runner must be a callable receiving one artifact dictionary and returning one artifact dictionary.

## Required stage output contract

Every stage output must include:

```text
artifact_id
artifact_type
status
decision
claim_ceiling
hard_block_hits
review_hits
```

`canonical_event_count`, when present, must remain `UNKNOWN` in this version.

## Output contract

The orchestrator returns:

```text
module_id
run_id
status
decision
claim_ceiling
completed_all_stages
pipeline_halted
halt_reason
stage_count_declared
stage_count_executed
stage_ledger
final_artifact
engineering_evidence
analyst_evidence
claim_boundary
release
```

## Stage ledger

Each executed or rejected stage records:

```text
run_id
stage_index
stage_module_id
input_artifact_type
input_artifact_ids
input_fingerprint
output_artifact_type
output_artifact_ids
output_fingerprint
status
decision
claim_ceiling
hard_block_hits
review_hits
error_code
```

Fingerprints use SHA-256 over canonical JSON with sorted dictionary keys.

No runtime timestamp or duration is inserted into the deterministic result. Environment-specific timing belongs in a separate runtime evidence envelope.

## State transition rules

### Block

The pipeline fails closed when:

- upstream `hard_block_hits` is non-empty;
- upstream status is `FAIL`, `FAILED`, `FAIL_CLOSED`, `BLOCKED` or `ERROR`;
- upstream decision starts with `BLOCK`;
- artifact type does not match the declared stage input;
- stage output is not a dictionary;
- stage output misses required contract fields;
- output artifact type does not match the declared stage output;
- stage runner raises an exception;
- a stage attempts to publish a numeric canonical event count.

### Review

A stage may halt the pipeline for review when:

- status is `REVIEW_REQUIRED` or `WAITING_OPERATOR_SELECTION`;
- decision includes `REVIEW`;
- `review_hits` is non-empty;
- `halt_on_review=True`.

### Completion

`SMOKE_PASS` means only that every declared stage completed under the supplied synthetic or local execution surface.

It does not mean:

- ACTIVE_MATCH evidence;
- football truth;
- production release.

## Determinism

For identical:

- `run_id`;
- initial artifact;
- ordered stage specifications;
- deterministic stage runners;

the orchestrator output must be identical.

The orchestrator does not add current time, random identifiers, environment paths or unordered serialization.

## Failure modes

- `run_id_required`
- `initial_artifact_must_be_dict`
- `stage_id_required`
- `input_artifact_type_required`
- `output_artifact_type_required`
- `runner_must_be_callable`
- `input_artifact_type_mismatch`
- `upstream_artifact_failed_closed`
- `stage_output_must_be_dict`
- `stage_output_fields_missing`
- `output_artifact_type_mismatch`
- `canonical_event_count_truth_not_allowed`
- `stage_runner_exception`

Unexpected exceptions are sanitized to `stage_runner_exception`; implementation details are not exposed in the artifact.

## Complexity

For `n` stages and total serialized artifact size `m`:

```text
time: O(n + m)
ledger space: O(n + m)
```

Actual producer complexity remains outside the orchestrator.

## Dependencies

Python standard library only:

- `dataclasses`
- `hashlib`
- `json`
- `typing`

No pandas, NumPy, workflow framework, cloud service or AI runtime dependency.

## Scientific and donor basis

The design adapts, but does not copy:

- HP-Engine's explicit ordered orchestrator concept;
- HP-Motor's deterministic staged segmentation pattern;
- HP-PROJELERI's lineage/no-drop evidence principles;
- scientific workflow literature emphasizing reproducibility, explicit module dependencies, intermediate artifacts, provenance and failure-aware execution;
- HPFA Intelligence Layer Integration Audit V1.

The implementation deliberately avoids a general-purpose workflow framework because HPFA currently needs a small portable domain controller, not distributed scheduling infrastructure.

## Mandatory tests

- deterministic declared-stage order;
- artifact-type mismatch fail-closed;
- upstream failure propagation;
- review halt propagation;
- exception sanitization;
- non-dictionary output rejection;
- required output-field validation;
- canonical event-count truth rejection;
- stable artifact fingerprints;
- identical-input deterministic result;
- run-id requirement;
- `test_no_sample_match_identity_leak`.

## Integration sequence

This module must not be wired directly to all existing modules in one step.

Required sequence:

```text
1. merge/port shared failure propagation corrections
2. define producer adapters for one narrow chain
3. execute match-agnostic end-to-end fixture
4. add flat JSON/TXT artifact writer
5. run on ACTIVE_MATCH
6. inspect engineering evidence
7. inspect analyst evidence
8. only then consider ACTIVE_MATCH_EVIDENCE_PASS
```

Recommended first real chain:

```text
composite evidence packet
-> multi-signal fusion
-> composite argument
-> defeasible argument router
-> evidence graph
```

## Claim boundary

```text
canonical_event_count = UNKNOWN
phase_truth = false
possession_truth = false
sequence_truth = false
rhythm_truth = false
tactical_truth = false
dominance_truth = false
coach_intention_truth = false
```

## Release status

```text
IMPLEMENTATION_WRITTEN_EXECUTION_PENDING
```

Tests are written but are not claimed as passed until direct execution or CI evidence exists.

No ACTIVE_MATCH evidence has been produced by this branch.

No production release is granted.
