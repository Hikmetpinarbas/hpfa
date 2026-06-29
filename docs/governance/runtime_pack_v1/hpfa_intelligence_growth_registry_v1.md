# HPFA Intelligence Growth Registry V1

Status: SPEC_ONLY
Release status: REVIEW_REQUIRED
Product authority: hpfa
Runtime authority: runtime/active_single_match/current
Source roles: DRIVE_DONOR_LIBRARY, DROPBOX_DONOR_LIBRARY, GITHUB_DONOR_REPO
Rule: ADAPT_NOT_COPY

This registry defines how Google Drive, Dropbox and donor GitHub material can grow HPFA analysis intelligence without becoming runtime truth.

Drive and Dropbox feed knowledge. hpfa builds product modules. ACTIVE_MATCH proves runtime behaviour.

## Registry schema

Each growth record must use this shape:

```json
{
  "growth_family": "string",
  "source_role": "DRIVE_DONOR_LIBRARY|DROPBOX_DONOR_LIBRARY|GITHUB_DONOR_REPO",
  "donor_file_or_path": "string",
  "intelligence_axis": "string",
  "hpfa_target_module": "string",
  "usable_now": false,
  "required_precondition": ["string"],
  "blocked_claim": ["string"],
  "adaptation_type": "CONTRACT|REGISTRY|TEST|LANGUAGE_BANK|METRIC_CANDIDATE|SIGNAL_CANDIDATE|REPORT_GRAMMAR|RETRIEVAL_INDEX",
  "engineering_conversion": "string",
  "analyst_value": "string",
  "test_needed": ["string"],
  "release_status": "REVIEW_REQUIRED"
}
```

## Nine growth families

### 1. Event Ontology Growth

Purpose:

Grow action-family and concept vocabulary for event-only analysis.

Candidate donors:

- Drive event-only metric primitive documents
- Drive event-only analysis design documents
- Dropbox canonical action family maps
- HP-Motor-main ontology registries

Target modules:

- Football Ontology Registry Lite V1
- Action Family Taxonomy Registry Lite V1
- Canonical Event Lite V1

Analyst value:

More consistent language for pass, carry, shot, recovery, turnover, restart, sequence and context candidates.

Blocked claims:

- taxonomy label equals tactical truth
- ontology label equals coach intention

### 2. Canonical Ingest Growth

Purpose:

Improve source-to-HPFA field conversion and action-family normalization.

Candidate donors:

- Drive canonical ingest donor discovery
- Dropbox event canonicalization contract files
- HP-Motor normalizers and mapping registries

Target modules:

- Canonical Event Lite V1
- Source Mapping Contract Lite
- Source Conflict Registry Lite
- Data Quality Gate Lite V1

Analyst value:

Cleaner row-level evidence before interpretation.

Blocked claims:

- canonical event count
- complete event truth

### 3. Context Intelligence Growth

Purpose:

Make event meaning depend on score, half, time, restart, card, window and context candidates.

Candidate donors:

- Drive context layer documents
- Dropbox game-state context engine contract
- Dropbox game-state adjustment rules
- HPFA Match Context Slicer Lite V1

Target modules:

- Match Context Slicer Lite V1
- Context Reasoning Engine
- Event Consequence Surface Lite V1

Analyst value:

The same action can be read differently by match state and window context.

Blocked claims:

- context candidate equals truth
- phase truth
- possession truth

### 4. Metric Primitive Growth

Purpose:

Convert mathematical families into HPFA candidate metric primitives with required fields and blocked claims.

Candidate donors:

- Drive metric ecosystem documents
- Drive event-only metric primitive research
- Dropbox metric fusion formula cards
- HP-Motor metric registry

Target modules:

- Metric Primitive Lite V1
- Metric Dependency Graph Lite V1
- Metric Misuse Registry Lite V1

Analyst value:

Metrics become readable as volume, progression, risk, rhythm support, territory proxy or diagnostic support rather than tactical truth.

Blocked claims:

- metric equals decision
- entropy equals quality
- field tilt equals dominance truth

### 5. Sequence and Rhythm Growth

Purpose:

Grow sequence, motif, process, rhythm and temporal-state candidates.

Candidate donors:

- HP-Engine sequence engine
- HP-Engine temporal signal factory
- HP-Engine temporal metric engine
- Drive rhythm and sequence documents
- Dropbox sequence window and consequence files

Target modules:

- Sequence Candidate Engine Lite V1
- Event Intensity Engine
- Rhythm Support Metric Lite V1
- Temporal State Candidate Lite V1

Analyst value:

The analyst can inspect attack construction, transition, restart, recycle, burst, cooldown and instability candidates.

Blocked claims:

- sequence equals intent
- rhythm signal equals rhythm state truth
- phase transition proxy equals phase truth

### 6. Graph and Network Growth

Purpose:

Model relationships among players, actions, zones, behaviours, sequences, metrics and evidence.

Candidate donors:

- Drive graph intelligence documents
- Dropbox graph type usage guide
- HP-Engine pattern graph input patterns

Target modules:

- Behaviour Graph Lite V1
- Sequence Graph Lite V1
- Metric Graph Lite V1
- Evidence Graph Engine
- Knowledge Graph Engine

Analyst value:

HPFA can later show relation structure, concentration and dependency rather than isolated totals.

Blocked claims:

- centrality equals influence truth
- graph edge equals off-ball structure truth
- dependency equals causality

### 7. Claim Science Growth

Purpose:

Make HPFA reason about what can and cannot be said from event-only evidence.

Candidate donors:

- Drive claim architecture documents
- Dropbox uncertainty/falsifier/claim guard files
- Dropbox falsifier requirement files
- HP-Engine claim runtime donor patterns

Target modules:

- Claim Eligibility Gate Lite V1
- Bayesian Confidence Engine
- Uncertainty Quantification Engine
- Causal Evidence Layer
- Football Output Audit Lite V1

Analyst value:

Every strong reading can include uncertainty, counter-scenario and withdrawal condition.

Blocked claims:

- diagnostic candidate equals truth
- causal language without causal evidence

### 8. Analyst Language Growth

Purpose:

Turn evidence into useful report language without making forbidden claims.

Candidate donors:

- Drive language safety layer documents
- Dropbox tactical intelligence normalization rollup
- Dropbox safe sentence constructor and report style guides
- HP-Engine narrative and claim report patterns

Target modules:

- Claim-Safe Report Grammar Gate V1
- Analyst Explanation Engine
- Analyst Report Lite V1

Analyst value:

Reports can say what was visible, where it appeared, which evidence supports it and what it means for an analyst.

Blocked claims:

- coach intention
- dominance truth
- pitch control truth
- fatigue truth

### 9. Product Engineering and Release Governance Growth

Purpose:

Keep the intelligence layer modular, testable and runtime-bound.

Candidate donors:

- Drive productization documents
- HPFA governance runtime pack
- HP-PROJELERI after tree audit

Target modules:

- Module Dependency Graph Lite V1
- Runtime Evidence Chain Closure
- Release Status Normalizer
- Product Governance Runtime Pack

Analyst value:

The system remains reliable enough to produce repeatable analyst-facing outputs.

Blocked claims:

- PASS equals release
- plan-only equals executable module

## Proposed P-series expansion

- P12 Context Reasoning Engine
- P13 Evidence Graph Engine
- P14 Behaviour Pattern Library
- P15 Event Intensity Engine
- P16 Bayesian Confidence Engine
- P17 Analyst Explanation Engine
- P18 Knowledge Graph Engine
- P19 Uncertainty Quantification Engine
- P20 Causal Evidence Layer
- P21 Analyst Memory and Pattern Retrieval Engine

These modules do not replace the current spine. They sit above canonical event, sequence candidate, context candidate, claim gate and report grammar.

## First implementation path

1. Finish open PR blockers and governance PR cleanup.
2. Build Intelligence Growth Registry as documentation-only main artifact.
3. Build Metric Dependency Graph Lite V1 contract.
4. Build Pattern Candidate Engine Lite V1 contract.
5. Build Sequence Candidate Engine Lite V1 contract.
6. Build Event Intensity Engine contract.
7. Build Analyst Explanation Engine contract.

## Runtime rule

No Drive or Dropbox source is runtime truth. Any growth family becomes HPFA product only after contract, schema, tests, ACTIVE_MATCH execution and claim-safe analyst output audit.
