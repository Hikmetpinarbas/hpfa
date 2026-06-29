# HPFA Semantic Ontology Harvest V1

Status: DISCOVERY_PASS_PLAN_ONLY
Release status: REVIEW_REQUIRED
Product authority: hpfa
Runtime authority: runtime/active_single_match/current
Rule: ADAPT_NOT_COPY

This document starts a repository-wide semantic and ontology harvest. The objective is to convert raw row and column surfaces into HPFA-native football meaning, argument nuclei and later report nuclei.

This is the first harvest pass. It establishes the catalog method required for deeper file-by-file inspection.

## Objective

HPFA must be able to read raw rows and columns, identify source roles and field meaning, place fields into ontology/taxonomy/context registries, produce safe semantic observations, and form argument nuclei for future analyst reports.

Working question:

```text
What can this row, column, field, tag, taxonomy or semantic rule add to HPFA football intelligence?
```

## Search language

English and Turkish surfaces:

- semantic / semantik
- canonical / kanonik
- ontology / ontoloji
- taxonomy / taksonomi
- validation / validasyon
- tagger / etiketleyici
- grammar / gramer
- reasoning / muhakeme
- report nucleus / rapor nuvesi
- argument / arguman
- capability / kabiliyet

## Initial verified findings

### hpfa semantic and canonical surface

Sources include canonical event lite, canonical ingest donor discovery, core canonical donor map, data quality gate and quality gate scripts.

Capability:

Product-side canonical and quality-gate surfaces for raw data interpretation.

HPFA adaptation:

Semantic Row Column Mapper Lite V1.

### HP-Engine semantic gate

Source:

- `HP_ENGINE/semantic_gate/live/hp_semantic_gate.py`

Capability:

Term normalization, valid-layer checking and state routing.

Observed concepts include half-space, momentum, tempo score, shot-sequence rate, phase rupture index, central progression, transition attack, sustained possession and switch attack. Valid layers include events, sequences, structures, patterns, metrics, temporal metrics, moments, chain impact and reports.

HPFA adaptation:

Semantic Term Registry Lite V1.

### HP-Engine taxonomy

Source:

- `engine/hp_engine_taxonomy.py`

Capability:

High-level football vocabulary and role tags.

Use:

Language donor only. High-level system labels must become candidate/report-language concepts, not classification truth.

HPFA adaptation:

Football Behaviour Taxonomy Lite V1 and Role Surface Vocabulary Lite V1.

### HP-Motor ontology loader

Source:

- `hp_motor/ontology/loader.py`

Capability:

Small ontology and platform mapping loader pattern.

HPFA adaptation:

Ontology Registry Loader Lite V1.

### HP-Motor-main capability matrix

Source:

- `src/hp_motor/syntax/capability_matrix.py`

Capability:

Maps available file kinds to analysis products and explains blocked products.

HPFA adaptation:

Input Capability Reasoner Lite V1.

### HP-Motor-main canonical ontology surfaces

Sources include canon index, football ontology, metric ontology, platform mappings, canonical event schema, schema specification and conflicts registry.

Capability:

Reusable vocabulary, schema and conflict donors for row/column meaning.

HPFA adaptation:

Row Column Ontology Placement Registry V1.

## Proposed product nodes

### P22 Semantic Row Column Mapper Lite V1

Reads raw headers, mapped columns, unmapped extras and sample rows. Places every visible field into ontology categories.

Core outputs:

- field_semantic_records
- unmapped_field_candidates
- row_semantic_nuclei
- blocked_field_claims
- argument_nuclei

### P23 Row Column Ontology Placement Registry V1

Maintains placement rules for source fields into event, actor, time, space, action, outcome, context, metric, support or unknown families.

### P24 Argument Nucleus Builder Lite V1

Converts row, column, context and metric evidence into small report nuclei before full report generation.

### P25 Input Capability Reasoner Lite V1

Given available file types and field mappings, determines which analysis families are allowed, degraded or blocked.

### P26 Semantic Term Registry Lite V1

Normalizes football terms, English/Turkish labels, aliases, report phrases and donor terminology into HPFA vocabulary.

## Row and column meaning pipeline

```text
RAW ROWS / COLUMNS
-> Source Mapping Contract
-> Source Conflict Registry
-> Semantic Row Column Mapper
-> Row Column Ontology Placement Registry
-> Minimum Viable Context
-> Match Context Slicer
-> Evidence Ladder
-> Argument Nucleus Builder
-> Report Grammar Gate
-> Analyst Report
```

## Required tests

- test_every_visible_column_gets_semantic_status
- test_unmapped_column_preserved_as_unknown_candidate
- test_row_semantic_nucleus_contains_evidence_refs
- test_argument_nucleus_blocks_forbidden_claims
- test_input_capability_reasoner_blocks_unavailable_input_claims
- test_semantic_term_registry_normalizes_aliases
- test_turkish_english_concept_aliases_resolve_to_same_registry_entry
- test_no_sample_match_identity_leak
- test_no_canonical_event_count_claim

## Release rule

This harvest is a discovery and planning artifact. It does not create executable modules or runtime truth. Each proposed node requires contract, schema, tests, ACTIVE_MATCH dry-run and football output audit.
