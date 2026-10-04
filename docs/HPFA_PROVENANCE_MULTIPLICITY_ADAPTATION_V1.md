# HPFA Provenance Multiplicity Adaptation V1

NODE: hpfa_provenance_multiplicity_adaptation_v1
STATUS: IMPLEMENTED_ON_CURRENT_WIP_OWNER

## Product question

When one admitted football occurrence is reused by several divergence/finding projections, can HPFA show the analyst that structural multiplicity increased without pretending that independent evidence increased?

## Source synthesis

### Google Drive

The living HPFA coding notebook and HPFA Ana Repo notebook identify the analyst problem: multiple downstream findings can be separate analytical views of one football fact. Blueprint 014/015 already closes shared-ancestor support inflation and exposes bounded occurrence ancestry in physical acceptance.

Adaptation: no second lineage engine. Extend the existing owner with multiplicity telemetry only.

### Dropbox

The Analyst Workaround Lab claim/evidence registry separates SUPPORTS, CONTRADICTS, QUALIFIES and FALSIFIES. Its falsifier registry explicitly defines LINEAGE / duplicate_inflated => FAIL_CLOSED. These records are SPEC_ONLY, not runtime authority.

Adaptation: provenance reuse is a support-quality burden, never a new support vote.

### alphaXiv

GraphEcho (arXiv:2609.17695) separates structural path multiplicity from provenance multiplicity: several graph paths can repeat one evidential origin. The portable idea is the distinction itself, not its benchmark/model machinery.

### Undermind

The literature search surfaced evidence-graph/provenance work in which results retain derivation DAGs and support/challenge relations. This supports traceability and later defeasible reasoning, but does not prove statistical independence.

### Context7

Current pytest documentation supports deterministic table-driven/parametrized regression testing. No new runtime library is required for this adaptation.

## Implementation

Owner:
`hpfa/modules/core/visible_action_sequence_candidates_lite/src/derived_lineage_runtime_binding.py`

New telemetry:
- `resolved_divergence_count`
- `divergence_occurrence_ancestry_edge_count`
- `reused_occurrence_ancestry_edge_count`
- `reused_occurrence_ancestry_edge_denominator`
- `provenance_multiplicity_state`
- per-divergence `bounded_occurrence_ancestor_ref_count`
- per-divergence `shared_ancestor_ref_count`

Physical acceptance exports the same bounded fields.

Truth locks:
- structural multiplicity != provenance multiplicity
- structural multiplicity != independent support
- distinct bounded ancestry != independence proof
- shared ancestry adds zero independent support
- lineage creates no evidence
- lineage cannot authorize EMIT
- lineage cannot strengthen claim ceiling
- canonical_event_count=UNKNOWN
- true_action_count=UNKNOWN
- production_release=false

## Analyst gain

The analyst can now see how many resolved divergence views exist, how many bounded occurrence-ancestry edges they consume, and how many edges reuse an already represented occurrence origin. This exposes evidence-echo burden without creating tactical recurrence, causality, statistical independence, or production truth.

## Authority

Drive, Dropbox, alphaXiv, Undermind and Context7 are SUPPORT / RESEARCH only. Executable authority remains fresh HPFA frontier plus test/runtime evidence.
