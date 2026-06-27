# P2I Academic Support V1

Status: REFERENCE_ONLY / REVIEW_REQUIRED

Linked PR: #92

## Purpose

Record academic support for P2I Ontology Chain Lite V1.

This note does not change runtime authority and does not implement style detection.

## Authority

ACTIVE_MATCH runtime remains the only executable truth.

Academic search results remain support only.

## Scholar Gateway support

Search topic:

football event data, playing style, possession sequence, clustering, ontology and limitations.

Relevant support:

1. Tactical behaviour analysis requires feature construction, spatial aggregation and temporal aggregation. This supports the HPFA requirement that style candidates must be built from evidence objects, windows and repeated clusters, not from single metrics.

2. Tactical behaviour studies often rely on tracking data for positional and subunit behaviour. This supports the HPFA boundary that off-ball structure, pitch control, compactness and body orientation remain blocked without video or tracking.

3. Clustering can identify style or movement profiles in sport, but style labels must remain model-derived profiles with uncertainty. This supports HPFA style_candidate language and blocks style truth without validation.

4. Video-based studies can identify mechanisms, but even video analysis may remain candidate-level for clinical or causal truth. This supports HPFA's requirement for falsifier, counter-scenario and review gates before recommendations.

## Sider Scholar support

Sider/OpenAlex search was noisy for the broad query. Treat results as low-confidence direction only.

Use decision:

- Do not cite noisy non-football hits as support.
- Keep Sider as secondary recall search, not authority, unless a specific relevant paper is fetched and reviewed.

## Product implications

P2I must keep this route:

row surface -> evidence object -> repeated evidence cluster -> ontology candidate -> style candidate -> recommendation candidate -> claim gate -> football output audit

## Required downstream guards

- feature construction guard
- temporal aggregation guard
- spatial aggregation guard
- multi-signal style support guard
- tracking-video requirement router
- single-match style candidate guard
- recommendation review guard

## Status

REFERENCE_ONLY / REVIEW_REQUIRED.
No production release claim.
