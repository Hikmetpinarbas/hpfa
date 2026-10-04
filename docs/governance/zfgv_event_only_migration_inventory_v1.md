# HPFA ZFGV Event-Only Migration Inventory V1

Status: DISCOVERY_PASS_PLAN_ONLY
Authority: current `Hikmetpinarbas/hpfa` main + PR #355 branch only
Purpose: classify every material `event-only` constraint before further migration. This document does not itself promote runtime truth or release state.

## Decision rule

Each occurrence is classified as one of:

- `PRESERVE_AS_GUARD`
- `GENERALIZE`
- `RENAME`
- `SUPERSEDE`
- `DELETE`
- `REVIEW_REQUIRED`

The test is not whether the phrase `event-only` appears. The test is whether the occurrence protects a valid evidence boundary, acts as a legacy identifier, or unnecessarily suppresses an admitted observation capability.

## Current high-value inventory

| Surface | Current role | Classification | Reason / migration action |
|---|---|---|---|
| `README.md` global product identity | Defines HPFA as event-only | `SUPERSEDE` | Global identity incorrectly capped product observation. PR #355 replaces it with ZFGV and construct-specific observation admission. |
| `docs/governance/HPFA_MASTER_PROJECT_DIRECTIVE_SHORT_CURRENT.md` | Active governance startup authority | `SUPERSEDE` | Must not instruct operators to apply a binary event-only ceiling. Updated on PR #355. |
| `configs/metrics/metric_registry_v1.json:event_only_compatible` | Legacy metric metadata / historical compatibility | `GENERALIZE` | Preserve for backward compatibility, but add observation requirements and never use it as sole capability gate. |
| `metric_definition_policy_lite` required field / fingerprint | Definition governance | `GENERALIZE` | Keep legacy field during migration; authoritative admission becomes construct-specific observation contract. Maintain historical fingerprint stability separately from observation-semantic fingerprint. |
| `provider_metric_dictionary_lite` operational `event_only_compatible` gate | Executable admission blocker | `GENERALIZE` | This was a real product ceiling. Use enriched observation compatibility shim and explicit observation contract; valid L1-L7 constructs must not fail solely because legacy flag is false. |
| Provider dictionary regressions expecting `event_only_compatibility_required` | Tests protecting old binary gate | `GENERALIZE` | Replace/augment with tests for required observation capabilities, missing semantics, L8 tracking/video gate, and unknown capability fail-safe behavior. |
| `provider_alias_field_semantics_lite` phrase `SUPERSEDE_FOR_EVENT_ONLY_SEQUENCE_ADMISSION` | Temporal safety vocabulary | `RENAME` | The safety rule is valid, but name should express partial-order/observation admission rather than global event-only identity. Do not weaken same-time/row-order guards. |
| `docs/research_support/academic_backing_matrix_v1.tsv:event_only_usable` | Research taxonomy | `REVIEW_REQUIRED` | Research-support only. Rename/add ZFGV observation-capability columns only when a consumer needs them; do not rewrite historical literature classification merely for branding. |
| Historical module identifiers such as `event_only_rhythm_evidence_stack_v12` | Module/lineage identifier | `PRESERVE_AS_GUARD` | Identifier may be referenced by contracts/runtime lineage. Do not rename mechanically; supersede semantically in new consumers while preserving lineage. |
| `metric_fusion_engine` title `Event-Only Metric Fusion Engine V1` | Scaffold/module label | `REVIEW_REQUIRED` | SCAFFOLD_NOT_PRODUCTION_BOUND. Inspect consumers before rename; do not create a parallel engine. If retained, narrow name only after compatibility map. |
| `reasoning_grammar_spine` prohibitions on pitch-control/off-ball truth from event-only runtime | Claim-safety rule | `PRESERVE_AS_GUARD` | Under ZFGV the wording should eventually become `non-tracking observation`, but the prohibition remains valid. |
| `composite_integration_office` risk flags `tracking_required` / `video_required` | Physical evidence boundary | `PRESERVE_AS_GUARD` | ZFGV != tracking/video. These guards become more important after the global event-only ceiling is removed. |
| Brand/prompt files that define HPFA globally as event-only | Operator/product language | `RENAME` / `SUPERSEDE` | Update only active prompts/brand language that can steer current work; historical research notes may retain old terminology with lineage markers. |
| Donor/research documents titled event-only | Historical/research support | `PRESERVE_AS_GUARD` | Do not rewrite historical donor context as current product truth. Add supersession note only where it could mislead operators. |
| Progression/spatial planning docs that say `event-only coordinates` | Source-scope shorthand | `RENAME` | Replace with admitted spatial observation / source-calibrated coordinate semantics when actively maintained. Preserve guards that coordinates != tracking geometry. |

## Guard set that must survive migration

The following are not event-only limitations; they are evidence-integrity invariants and must remain:

- row count != canonical event count
- row nucleus != action occurrence
- label != action truth
- same timestamp != total order
- source row/list/event index != football chronology
- coordinate presence != admitted coordinate frame/direction
- event-space displacement != physical player/ball speed or travelled distance
- co-occurrence != interaction/marking/pressure truth
- provider pressure flag != true pressure geometry
- pass network != team shape/formation
- recurrence != coach intention/tactical plan
- context difference != causality/adaptation
- same upstream CSV/XML/XLSX reflections != independent evidence
- N metrics != N independent evidence
- absence of evidence != counterevidence
- L8 physical/off-ball constructs require tracking/video authority

## Migration target

Binary question to retire as product authority:

`Is this metric/event construct event-only compatible?`

Authoritative question:

`Which admitted observation capabilities and source semantics are required for this construct, what is forbidden without additional evidence, and what is the claim ceiling?`

Target manifest fields:

- `required_observation_capabilities`
- `optional_observation_capabilities`
- `forbidden_without`
- `claim_ceiling`

The current PR #355 `required_observation_layers`, `required_surface_semantics`, and `tracking_video_required` fields are the first compatibility bridge. The next slice should extend—not replace—the current producer with capability-family semantics.

## Priority capability families for re-audit

1. temporal dynamics
2. spatial progression
3. relational / passer-receiver / player-process binding
4. visible opponent-response candidates
5. consequence chains
6. state-transition candidates
7. episode/process reconstruction
8. change / recurrence / variation / deviation
9. Match ECG attention radar
10. graph projections over admitted state-transition evidence

## Release boundary

This inventory is discovery/governance evidence only. It is not ACTIVE_MATCH evidence and does not authorize production claims.

canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
