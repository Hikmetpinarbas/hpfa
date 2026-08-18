# HPFA Statistical Method Admission Registry V1

Status: `RESEARCH_HARDENED_SPEC_SUPPORT / NOT_PRODUCTION`

This registry separates methods that current event-only evidence can support now from methods that require later upstream contracts or multi-match data. Donor and academic sources are `REFERENCE_ONLY / DONOR_SUPPORT`; they do not override ACTIVE_MATCH authority.

## Implement now

### Spatial grid Shannon entropy

Unit: eligible content-role-resolved row-nucleus coordinate candidate.

Outputs: 12x8 and 16x12 grid occupancy, Shannon entropy, normalized grid entropy, effective-cell count and HHI concentration.

Safe interpretation: coordinate evidence is more concentrated or more distributed across the selected grid.

Not allowed: physical-event count, tactical unpredictability truth, team shape, dominance, pitch control or intent.

Research support:
- Shannon entropy formalism;
- football spatial-entropy literature using event/pass locations;
- HP-Motor entropy donor;
- HP-Engine temporal/spectral entropy donor;
- Dropbox information-theory formula donor.

## Deferred methods

### KDE 2D

Reason: current row nuclei are not admitted independent physical event points. Bandwidth, boundary correction and point-process unit must be contracted first.

### Ripley's K

Reason: significance requires a defined null point process, edge correction and defensible independence/interaction assumptions. Multi-label row nuclei and serialization dependence make a direct implementation unsafe.

### Mann-Whitney / chi-square / rate tests

Reason: repeated actions inside one match are not automatically independent samples. Observation-unit, clustering, dependence and multiple-testing policies must precede p-value claims. A small p-value cannot be translated into tactical causality.

### Bivariate Poisson / Dixon-Coles / Monte Carlo score simulation

Reason: plugging one match's xG totals directly into Poisson means is a descriptive reference simulation, not a fitted Dixon-Coles team-strength model and not a proof of a deserved result. Required: multi-match attack/defence strength estimation, home/away and low-score correction policy, validated xG construct provenance and calibration audit.

### Kaplan-Meier / Cox proportional hazards

Reason: the event of interest, censoring rule and survival unit must be defined on admitted sequence/possession candidates. Current source `start/end` intervals are source-timeline evidence, not physical possession lifetime.

### PCA / factor analysis

Reason: a single match with roughly tens of players and over one hundred aggregate metrics is underdetermined for stable latent-factor claims and heavily role/context confounded. Required: multi-match sample, scaling policy, missingness policy, role stratification and measurement-invariance checks.

### Beta-Binomial Bayesian shrinkage

Reason: requires a defensible prior population, exact success/failure opportunity denominator, exposure authority and construct validity. A single match cannot create a stable player-ability prior by itself.

## Explicit corrections to reject

- `p < 0.05` does not prove that a goalkeeper caused the result.
- `Mann-Whitney significant` does not prove tempo difference is tactical rather than context-dependent.
- `Cox HR > 1` is meaningless before sequence survival and censoring are validly defined.
- PCA component labels such as "penetration" or "defensive resistance" must be learned and validated; they cannot be named from intuition after one match.
- entropy is distributional uncertainty/concentration evidence; it is not synonymous with quality, chaos, creativity or dominance.

## Future admission order

```text
Trackable Action
-> Consequence
-> Sequence/Context
-> Coordinate Frame + Direction
-> Spatial Distribution
-> Multi-match Comparison Authority
-> Survival / Bayesian / PCA / hypothesis tests
-> calibrated score models
-> analyst reasoning + falsifier
```

Always:

```text
canonical_event_count=UNKNOWN
production_release=false
```
