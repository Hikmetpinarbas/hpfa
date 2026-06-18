# HPFA ACTIVE_MATCH Completion Plan V1

## Purpose

This document freezes the next recovery direction for HPFA ACTIVE_MATCH execution.

Goal is not to redesign HPFA.
Goal is to complete the missing runtime chain by consolidating existing multiversion apparatus into stronger composite apparatus where possible.

## Current Operating Authority

Runtime authority is folder-based:

```text
runtime/active_single_match/current
```

The active match folder is the only match authority during execution.
Team name, match name, old test match ID, donor folder, legacy folder, or static report cannot become runtime authority.

## Active Surface Rule

Raw event/data surface:

```text
3 CSV + 3 XML + 2 XLSX
```

Reference reports:

```text
PDF = reference only, not event truth
```

## Current Execution Diagnosis

The project is not empty and does not need a rewrite.
The problem is integration.

Observed system condition:

```text
Canonical / Action surface exists
Possession / Sequence binding is incomplete
Progression / Consequence attachment is incomplete
Evidence table is incomplete
Claim confidence gate is incomplete
Report layer waits for upstream claim-safe surfaces
```

## Core Missing Chain

Priority order:

```text
P1  possession_object_v1
P2  progression_consequence_attachment_v1
P3  evidence_table_active_match_v2
P4  claim_confidence_gate_v1
P5  static contracts and policies
```

## Important Classification Rule

Missing producer rows must be split into five classes before repair:

```text
runtime_generated_artifact
static_contract
static_policy
script_false_positive
legacy_or_blueprint_residue
```

Static contracts must not be treated as runtime artefacts.
Script files must not be treated as produced surfaces.
Legacy and blueprint residues must not become blockers for ACTIVE_MATCH execution.

## Composite Apparatus Strategy

A missing capability should not automatically create a new node.
First check whether multiple existing versions can be fused into a single composite apparatus.

Decision order:

```text
1. Is the capability already present in one or more versions?
2. Do multiple versions produce overlapping surfaces?
3. Can their common core be consolidated?
4. Can the strongest version become the canonical composite?
5. Can weaker versions be demoted to donor/reference/archive?
6. Is new code still necessary after consolidation?
```

## Composite Families To Build

### 1. Possession Composite

Target output:

```text
runtime/possession/current/possession_object_v1.json
runtime/possession/current/possession_object_v1.txt
```

Candidate inputs:

```text
selected_canonical_events_v1.jsonl
selected_canonical_events_enriched_v1.jsonl
selected_realized_actions_v1.jsonl
selected_realized_action_bundles_v1.jsonl
```

### 2. Sequence Confidence Composite

Target output:

```text
runtime/contracts/cross_sequence_confidence_contract_v1.json
```

Important: this is a static or semi-static contract surface, not a match-derived event truth surface.

### 3. Progression-Consequence Composite

Target output:

```text
runtime/progression/progression_consequence_attachment_v1.json
reports/progression_consequence_attachment_v1.md
```

Role:
Connect progression surfaces to consequence surfaces without claiming dominance, control, or tactical intent.

### 4. Evidence Table Composite

Target output:

```text
runtime/evidence/evidence_table_active_match_v2.json
```

Role:
Create traceability from claim candidate back to metric, sequence, canonical event, and source surface.

### 5. Claim Confidence Gate Composite

Target output:

```text
runtime/claim_gate/current/claim_confidence_gate_v1.json
runtime/claim_gate/current/claim_confidence_gate_v1.txt
```

Role:
Decide whether claim candidates are EMIT, DOWNGRADE, ABSTAIN, SUPPRESS, or FAIL_CLOSED.

## Non-Negotiable Guardrails

The following claims remain forbidden without appropriate evidence:

```text
No true event count claim
No PDF event truth
No coach intention claim
No off-ball truth claim
No pitch-control claim
No body-orientation claim
No fatigue claim from event-only data
No dominance claim from progression alone
No dominance claim from packing alone
No player quality claim from contribution alone
No impact claim from contribution alone
```

## Execution Method

For each missing chain item:

```text
1. Inventory all versions
2. Compare input/output surfaces
3. Extract common core
4. Select strongest version
5. Build composite wrapper only if existing apparatus can be reused
6. Run on ACTIVE_MATCH
7. Record pass/fail, artefacts, logs, and football value
8. Demote redundant variants only after successful composite execution
```

## Success Condition

HPFA reaches first stable ACTIVE_MATCH execution spine when this chain exists:

```text
RAW
→ Canonical / Action
→ Possession / Sequence
→ Progression / Consequence
→ Evidence Table
→ Claim Confidence Gate
→ Claim-safe Match Story
→ Professional Report Candidate
```

This is an execution-spine completion plan, not a production-readiness declaration.
