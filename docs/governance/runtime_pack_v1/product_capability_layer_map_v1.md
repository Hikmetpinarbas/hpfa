# HPFA Product Capability Layer Map V1

Status: SPEC_ONLY
Release status: REVIEW_REQUIRED
Product authority: hpfa
Runtime authority: runtime/active_single_match/current
Rule: ADAPT_NOT_COPY

This document groups donor-mined capabilities into ten HPFA product layers. It is a planning artifact, not executable product code.

## Step gain record

```json
{
  "step_id": "PRODUCT_CAPABILITY_LAYER_MAP_V1",
  "source_repo": "HP-Motor-main|HP-Motor|HP-Engine|HP-PROJELERI",
  "source_role": "GITHUB_DONOR_REPO",
  "target_hpfa_module": "product_capability_layer_map",
  "engineering_gain": ["ten-layer product architecture", "capability grouping map", "verified-vs-candidate separation", "module-sprawl reduction rule"],
  "analyst_gain": ["clearer path from surface evidence to analyst reading", "safer separation of taxonomy, segmentation, validation, evidence and report grammar"],
  "new_blockers": ["layer map is SPEC_ONLY", "each downstream capability requires its own contract, tests and ACTIVE_MATCH runtime evidence"],
  "claim_boundary_change": "none",
  "runtime_evidence_required": true,
  "release_status": "REVIEW_REQUIRED"
}
```

## Proven adaptable capability families

These families were observed in hpfa, HP-Motor-main, HP-Motor or HP-Engine surfaces and can be modernized through HPFA-native contracts.

- Active Match Runtime
- Active Match Identity Guard
- Analyst Report Grammar
- Audit Framework
- Axis Integrity Tagger
- Behaviour Candidate Engine
- Boundary Analysis
- Canon Loader
- Canonical Event Lite
- Canonical Surface Governance
- Capability Matrix
- Claim Eligibility Gate
- Claim Router
- Classification / Tasnif
- Conflict Registry
- Context Slicer
- Diagnostic / Teshis
- Differentiation Gate / Tefrik
- Data Quality Gate
- Donor Adaptation Registry
- Evidence Model
- Event Identity Resolution
- Event State Transition Verifier
- Event Window Builder
- Execution Contract
- Engine Validator
- Football Output Audit
- Governance Matrix
- Grammar Gate
- Goalkeeper Taxonomy
- Identity Review Resolution
- Ingest Pipeline
- Lineage Registry
- Match Context
- Metric Primitive
- Metric Registry
- Metric Ontology
- Minimum Viable Context
- No Silent Drop Audit
- Ontology Registry
- Output Validator
- Pattern Candidate Engine
- Permission Spine
- Phase Candidate
- Platform Mapping
- Possession Boundary Apparatus
- Primary Event Surface Gate
- Primary Surface Review
- Registry Builder
- Release Status Normalizer
- Report Grammar
- Runtime Evidence
- Runtime Validator
- Segmentation
- Semantic Gate
- Sequence Candidate Engine
- Source Mapping Contract
- Source Role Registry
- Source Conflict Registry
- Status Normalizer
- Taxonomy Registry
- Team Binding
- Tempo Support Signals
- Test Registry
- Time Scale Router
- Validation Framework
- Window Assignment Integrity

## Research candidates not yet product-bound

These are useful candidate families, but require repository evidence, contract definition and tests before product binding.

- Adaptation Registry
- Analyst Intelligence Layer
- Ambiguity Registry
- Capability Registry
- Claim Boundary Registry
- Context Intelligence
- Diagnostic Ladder
- Differentiation Engine
- Evidence Graph
- Evidence Ladder
- Knowledge Registry
- Metric Dependency Graph
- Module Dependency Graph
- Ontology Builder
- Pattern Library
- Registry Manager
- Runtime Knowledge Base
- Segmentation Engine
- Signal Fusion Layer
- Taxonomy Manager
- Validation Graph

## Ten product layers

### 1. Canonical Layer

Owns canonical surface governance, event identity candidates, team binding candidates, source mapping, primary surface gates and axis integrity.

Boundary: no canonical event count, no complete event truth, no clean tactical truth.

### 2. Runtime Layer

Owns ACTIVE_MATCH execution, identity guard, permission spine, time scale routing, execution contracts and runtime evidence.

Boundary: no runtime truth from donor or archive sources.

### 3. Registry Layer

Owns source roles, release statuses, capabilities, lineage, platform mappings, donor adaptation records and module dependency records.

Boundary: a registry entry is not analytic truth.

### 4. Ontology Layer

Owns football concepts, action families, metric families, goalkeeper taxonomy and report concepts.

Boundary: taxonomy labels do not create tactical correctness or coach intention.

### 5. Segmentation Layer

Owns context slicing, event windows, minimum viable context, segment candidates, phase candidates, sequence candidates and possession boundary candidates.

Boundary: segment/window/sequence candidates do not create possession, phase or tactical truth.

### 6. Classification Layer

Owns tasnif classifier, tefrik differentiation gate, ambiguity registry, false-merge blocker and false-split blocker.

Boundary: classification is not intent; differentiation is not causality.

### 7. Validation Layer

Owns data quality gate, no silent drop audit, duplicate risk gate, temporal consistency gate, coordinate boundary gate, runtime validator, output validator, test registry and validation graph.

Boundary: validator PASS is not production release; valid rows are not canonical event count.

### 8. Evidence Layer

Owns evidence model, evidence graph, evidence ladder, claim boundary registry, claim eligibility gate, semantic gate, claim router and claim consolidation gate.

Boundary: a single signal does not create truth; proxy evidence does not create tactical truth.

### 9. Analyst Intelligence Layer

Owns behaviour candidates, pattern candidates, diagnostic candidates, diagnostic ladder, context intelligence, tempo support signals, signal fusion and runtime knowledge base.

Boundary: diagnostic candidate is not diagnosis truth; behaviour candidate is not intention.

### 10. Report and Grammar Layer

Owns analyst report grammar, grammar gate, report grammar, football output audit, evidence reference index and blocked claim report.

Boundary: no dominance truth, off-ball truth, pitch-control truth, coach-intention truth or fatigue truth.

## Product rule

Do not add every capability as a separate top-level pillar. New work must bind to one of the ten layers first, then define module, contract, schema, tests, runtime evidence and claim boundary.

## Highest-value next capabilities

1. Source Governance Executable Skeleton
2. Football Ontology Registry Lite
3. Evidence Ladder Lite
4. Metric Dependency Graph Lite
5. Module Dependency Graph Lite

## Release rule

This map is SPEC_ONLY. It creates no executable module, runtime evidence, production release, canonical event count, tactical truth, possession truth, phase truth, sequence truth or dominance truth.
