# Statistical Spatial Evidence Lite V1

## Purpose

Produce claim-safe spatial distribution evidence from content-role-resolved row nuclei.

```text
content-resolved row nuclei
+ explicit coordinate-frame dimensions
-> raw x-third distribution
-> 12x8 / 16x12 grid occupancy
-> Shannon entropy
-> effective-cell count
-> HHI concentration
-> coordinate centroid / dispersion candidates
```

## Current implemented methods

- `SPATIAL_GRID_SHANNON_ENTROPY`
- `SPATIAL_GRID_CONCENTRATION_HHI`
- `RAW_X_THIRD_DISTRIBUTION`

The statistical unit is an eligible `row_nucleus_candidate`, not a canonical event or physical action.

## Coordinate-frame rule

Pitch length and width must be supplied explicitly with non-empty provenance. This module does not validate provider coordinate-frame truth and does not infer attack direction.

Therefore:

```text
RAW_X_THIRD_1/2/3 != own/middle/final third truth
coordinate centroid != team centroid truth
coordinate dispersion != team width/length truth
grid entropy != tactical unpredictability truth
```

## Deferred statistical families

The executable output must disclose why these remain closed:

- `KDE_2D`: independent point-process unit, bandwidth and edge policy required;
- `RIPLEY_K`: point independence, null process and edge correction required;
- `MANN_WHITNEY_OR_RATE_TESTS`: observation-unit independence and multiplicity policy required;
- `BIVARIATE_POISSON_DIXON_COLES`: multi-match team-strength model and validated inputs required;
- `KAPLAN_MEIER_COX`: admitted sequence unit plus censoring/event definition required;
- `PCA_FACTOR_ANALYSIS`: adequate multi-match sample, scaling and measurement invariance required;
- `BETA_BINOMIAL_BAYESIAN_SHRINKAGE`: validated prior population and eligible denominator/exposure authority required.

## Required claim boundaries

```text
spatial_point_is_canonical_event=false
row_nucleus_is_physical_action=false
team_shape_truth=false
pitch_control_truth=false
dominance_truth=false
tactical_truth=false
comparison_allowed=false
claim_allowed=false
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

## Status vocabulary

CI success is engineering evidence only. ACTIVE_MATCH execution is separately required before any current-match statistical evidence status can be assigned.
