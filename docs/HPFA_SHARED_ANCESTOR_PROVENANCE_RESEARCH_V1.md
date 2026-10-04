# HPFA Shared-Ancestor Provenance Research V1

NODE: hpfa_shared_ancestor_provenance_research_v1
STATUS: RESEARCH_COMPLETE_IMPLEMENTATION_NOT_REQUIRED

## Question

For the current Single-Match Postmatch WIP, what can provenance/lineage establish about shared ancestry and what must it **not** be allowed to establish about evidence independence?

## Product translation

HPFA needs to know whether two downstream football findings are genuinely separate support or merely different descriptions/projections of the same upstream observed occurrence. The lineage layer must collapse shared ancestry, but it must never promote different-looking roots into statistical or evidential independence without an additional admitted dependency/independence contract.

## Primary-source findings

### 1. Derivation records provenance, not statistical independence

W3C PROV defines `prov:wasDerivedFrom` as a derivation relationship between entities: one entity is transformed, updated, or constructed from a pre-existing entity. Qualified derivation can additionally record the activity, usage and generation that produced the derived entity.

Source: W3C PROV-O, `prov:wasDerivedFrom` and qualified derivation.
https://www.w3.org/TR/prov-o/

HPFA consequence: a lineage edge can justify **derived from / shares ancestor / does not share tracked ancestor**, but it cannot by itself justify **independent support**.

### 2. Different representations can still refer to the same underlying thing

W3C PROV uses `prov:alternateOf` for entities that present aspects of the same thing, including different serializations or copies, and `prov:specializationOf` for more specific aspects of a more general entity.

Source: W3C PROV-O expanded terms.
https://www.w3.org/TR/prov-o/

HPFA consequence: CSV/XML reflections or family projections can remain separate objects while still belonging to the same support lineage. This directly supports the existing locks `MULTIFORMAT != INDEPENDENT EVIDENCE` and family-view `!=` independent vote.

### 3. Provenance validity does not imply evidence independence

W3C PROV-CONSTRAINTS validates provenance through uniqueness constraints, event-ordering constraints and impossibility constraints. The validation model is about whether a provenance description is internally valid; it does not define a rule by which distinct provenance roots become statistically independent observations.

Source: W3C PROV-CONSTRAINTS.
https://www.w3.org/TR/prov-constraints/

HPFA consequence: even a valid, distinct lineage graph must keep `bounded_ancestry_distinctness_is_independence_proof=false` unless a separate HPFA dependency/independence admission rule is satisfied.

### 4. Parent and root are distinct concepts and both should remain queryable

OpenLineage ParentRunFacet separates the immediate parent from the root operation that initiated the full chain. The root therefore represents an initial chain ancestor rather than merely the nearest producer.

Source: OpenLineage Parent Run Facet.
https://openlineage.io/docs/spec/facets/run-facets/parent_run/

HPFA consequence: preserving `parent_ref` and bounded root refs separately is the correct shape. A Safe Finding can have an immediate divergence parent while still carrying occurrence ancestry further upstream.

### 5. Forwarded lineage metadata is not automatically authoritative

OpenLineage explicitly warns that forwarded parent/root facets are convenience metadata and are not a replacement for resolving the parent run's own event when full authoritative information is required.

Source: OpenLineage Parent Run Facet.
https://openlineage.io/docs/spec/facets/run-facets/parent_run/

HPFA consequence: a copied/forwarded root ref must not be treated as stronger than the underlying admitted occurrence/evidence object. If a downstream projection and upstream authoritative record disagree, the upstream admitted record wins or the lineage remains REVIEW_REQUIRED.

### 6. Lineage can be carried at multiple dependency granularities

OpenLineage's Lineage Dataset Facet distinguishes entity-level inputs from field-level inputs and can identify exact upstream datasets/jobs/fields from which a target derives.

Source: OpenLineage Lineage Dataset Facet.
https://openlineage.io/docs/spec/facets/dataset-facets/lineage/

HPFA consequence: a future evidence-root refinement may legitimately descend from occurrence ancestry to explicit evidence-atom/supporting-surface ancestry where those refs already exist. That is a refinement of the current owner, not justification for a new lineage engine.

## Current HPFA code fit

Current owner:
`hpfa/modules/core/visible_action_sequence_candidates_lite/src/derived_lineage_runtime_binding.py`

Current implementation already matches the primary-source direction:

- immediate parent and root ancestry are distinct;
- bounded admitted occurrence refs are used as upstream roots where available;
- shared occurrence ancestry is surfaced deterministically;
- shared ancestry cannot add independent support;
- distinct bounded ancestry is explicitly not independence proof;
- unresolved ancestry remains REVIEW_REQUIRED;
- lineage cannot create evidence, authorize EMIT, strengthen claim ceilings, establish recurrence truth or causality.

## Decision

**NO NEW IMPLEMENTATION REQUIRED FROM THIS RESEARCH.**

The current WIP should stay on its existing owner and proceed to physical ACTIVE_MATCH acceptance.

Research-backed acceptance invariants:

1. Shared bounded occurrence ancestor => collapse for support accounting.
2. Different bounded occurrence ancestors => `PROVENANCE_DISTINCT_WITHIN_TRACKED_SCOPE`, **not** independence proof.
3. Missing/unresolvable ancestor => REVIEW_REQUIRED and no claim promotion.
4. Parent/root metadata must remain traceable to the upstream admitted object, not copied narrative text.
5. Any later descent to evidence-atom roots must reuse existing provenance refs and dependency typing; no fabricated inverse aggregate-to-action identity.

## Later candidate

LATER, only after current physical closure: consider a bounded `qualified_derivation`/dependency descriptor on existing lineage objects when the product needs to distinguish transformation types such as serialization reflection, semantic projection, role transformation and aggregate derivation at the same ancestor level. This should adapt existing HPFA dependency taxonomy, not import W3C/OpenLineage as runtime authority.

## Source role / authority

W3C PROV and OpenLineage are design/research references only. They are not HPFA product truth. Product authority remains fresh `Hikmetpinarbas/hpfa` current frontier plus claim-appropriate test/runtime evidence.

canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
