# HPFA Source & Capability Registry V1

| Capability | Product authority | Donor support | Decision | Target |
|---|---|---|---|---|
| Multiformat inventory | `hpfa` PR #164 | Drive/Dropbox ingest notes | ADAPT_NOW; existing PR | merge chain |
| CSV/XLSX/XML readers | `hpfa` open PR chain | HP-Motor schemas, local format archives | ADAPT_NOW; existing PRs | ingest spine |
| Cross-format reconciliation | `hpfa` open PR chain | Drive data-fusion research | ADAPT_NOW; existing PR | reconciliation |
| Visible sequence candidates | `hpfa` PR #205 | HP-Motor/HP-Engine sequence methods; Dropbox B05 | PRODUCT_EXISTS | sequence spine |
| Event-derived phase state | this change | Drive Football Phase Engine; local event-semantics archive | ADAPT_NOW; recreated | phase spine |
| Phase-aware sequence refinement | none yet | sequence/phase donor methods | ADAPT_LATER | after ACTIVE_MATCH phase audit |
| Repetition and outcome distribution | none yet | Dropbox pattern/consequence families | ADAPT_LATER | pattern spine |
| Uncertainty/falsifier guard | partial current claim gates | Dropbox claim guards | ADAPT_LATER | claim gate |
| Metric provenance/formula cards | partial contracts | local formula library, Drive metric research | ADAPT_LATER | metric registry |

## Authority rule

`runtime/active_single_match/current` remains the only ACTIVE_MATCH truth. Drive,
Dropbox, local archives and donor repositories are `REFERENCE_ONLY` or
`DONOR_SUPPORT`; they cannot override product output or runtime evidence.

## Superseded records

`HPFA_CURRENT_STATE.md`, `HPFA_NODE_ROADMAP.md`,
`HPFA_NEXT_CONSEQUENCE_NODE_SPEC.md`, old apparatus registries and older Dropbox
current-scan reports must be retained as `SUPERSEDED_REFERENCE`, not treated as
current authority and not deleted by filename alone.
