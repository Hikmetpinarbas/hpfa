# HPFA Multi-Surface Argument Intelligence Research — 2026-09-18

## Purpose

This note records a source-grounded audit of the Gaziantep FK 0-0 Fenerbahce 14.09.2026 sample bundle supplied to the operator and identifies a product gap: HPFA already reads/reconciles event and XLSX surfaces, but it does not yet systematically compose them into match-local football argument candidates.

This is research/support evidence. It is not production truth and does not authorize merge/release.

## Sample surfaces inspected end-to-end

Uploaded sample bundle:
- player action CSV: 3,053 data rows
- player action XML: 3,053 instances
- team action CSV: 3,672 data rows
- team action XML: 3,672 instances
- goalkeeper action CSV: 169 data rows
- goalkeeper action XML: 169 instances
- player XLSX: 30 player rows x 131 columns
- goalkeeper XLSX: 2 goalkeeper rows x 109 columns

CSV/XML pairs are exact row-level serialization reflections after normalizing blank vs `None`; they are not independent evidence.

The semantically distinct surfaces are nevertheless rich:
- player action/participation surface
- team process/action surface
- goalkeeper action surface
- player aggregate/tabular metric surface
- goalkeeper aggregate/tabular metric surface

## High-value empirical structure found in the sample

### 1. Event facet bundles

The 3,053 player-action rows collapse to 2,043 same-player/same-time/same-location bundles; 697 bundles carry more than one action/qualifier label.

Common bundles include:
- `Passes accurate + Passes forward accurate`
- `Passes accurate + Passes forward accurate + Progressive passes accurate`
- `Involvement in positional attacks + Involvement in positional attacks with shots`
- `Inaccurate passes + Incomplete passes forward + Incomplete progressive passes`
- `Challenges unsuccessful + Tackles unsuccessful`

This is evidence for a facet-composition model rather than treating every label row as an independent physical action.

### 2. Cross-team relational pairs

Exact time/location opposition pairs are abundant:
- 146 challenge-won / challenge-unsuccessful pairs
- 35 successful-dribble / unsuccessful-tackle pairs
- 14 unsuccessful-dribble / successful-tackle pairs
- 21 foul / foul-suffered pairs

These can produce explicit actor-to-actor relations without a new tracking engine.

### 3. Process-to-participant binding

Team `Positional attacks` intervals: 113.
Exact participant bindings from player `Involvement in positional attacks`: 109/113.

Team `Positional attacks with shots`: 12 exact process intervals.

By team:
- Fenerbahce: 72 positional attacks, 10 with shots
- Gaziantep FK: 41 positional attacks, 2 with shots
- Fenerbahce: 10 counterattacks, 0 exact counterattack-with-shot participant intervals
- Gaziantep FK: 27 counterattacks, 6 exact counterattack-with-shot participant intervals

This is already sufficient to build process-family outcome profiles directly from existing provider semantics.

### 4. Match-local association-rule candidates

For Fenerbahce positional attacks, baseline shot-ending share is 10/72 = 13.9%.

Examples generated from admitted participant co-occurrence:
- Matteo Guendouzi present: 24 positional attacks, 7 with shots -> 29.2%; absent: 48 attacks, 3 with shots.
- Kerem Akturkoglu present: 20 attacks, 6 with shots -> 30.0%; absent: 52 attacks, 4 with shots.
- Kerem + Guendouzi together: 12 attacks, 5 with shots -> 41.7%; baseline 13.9%; match-local lift ~3.0.
- Kerem + Romelu Lukaku together: 8 attacks, 4 with shots -> 50.0%; match-local lift ~3.6.

These are hypothesis/attention candidates, not causal credit or independent evidence. The useful product behavior is to surface them with numerator/denominator, episode refs, counterexamples and role context.

### 5. XLSX metric algebra is large and structured

The player XLSX has 131 columns. At least 24 percentage columns were verified as exact numerator/denominator identities on every applicable player row, e.g.:
- pass accuracy
- progressive-pass accuracy
- long-pass accuracy
- box-pass accuracy
- duel-win rate
- dribble success
- tackle success
- action success
- final-third-entry route shares
- shot-on-target rates

Additional exact additive identities include:
- Actions = Actions successful + Actions unsuccessful
- Final third entries = through pass + through carry
- Lost balls = lost balls after passes + individual ball losses
- Open passes received = first-third + central-third + final-third receives

This supports a metric dependency/algebra graph rather than treating XLSX columns as unrelated scalars.

### 6. Cross-entity conservation checks

The aggregate surfaces reconcile football accounting identities:
- Fenerbahce player shots = 13; opponent goalkeeper shots faced = 13.
- Gaziantep player shots = 10; opponent goalkeeper shots faced = 10.
- Fenerbahce summed player xG = 2.20; Tobiasz opponent xG = 2.20.
- Gaziantep summed player xG = 0.72; Ederson opponent xG = 0.72.
- Fenerbahce outfield accurate passes 496 + Ederson 45 = team event-surface accurate passes 541.
- Gaziantep outfield accurate passes 207 + Tobiasz 25 = team event-surface accurate passes 232.

These are not independent confirmations, but they are powerful semantic/accounting constraints and can support automatic reconciliation and argument completeness.

### 7. Cross-surface semantics can expose provider label collisions

The team XML contains 436 `Goal kicks short (0-15 m)`, 429 `Goal kicks medium (15-40 m)`, and 63 `Goal kicks long (40+ m)` labels. These counts nearly partition all pass attempts, while the goalkeeper XLSX records only 6 actual goal kicks for each goalkeeper.

Therefore these team-surface labels cannot be naively interpreted as physical goalkeeper restarts. This sample demonstrates why HPFA needs multi-surface semantic calibration before composition.

The repository already has a closed goal-kick/deep-distribution semantic audit; the broader lesson is to generalize this cross-surface calibration method.

## Current repo false-gap check

At exact PR #359 head used for this audit:
- `xlsx_entity_metric_row_projection_lite` already exposes XLSX entity metric vectors but sets `comparison_allowed=false` and `claim_allowed=false`.
- `cross_format_reconciliation_lite` reconciles surfaces and explicitly prevents XLSX from being treated as independent confirmation.
- `aggregate_definition_alignment_lite` currently has only a narrow reviewed candidate registry (for example pass completion) rather than a full metric algebra/interaction graph.
- process participation projections already exist.
- no current core module named/structured as a general correlation, association-rule, feature-interaction, or multi-surface argument composition layer was found.

Therefore the real gap is not another reader or another event engine. It is a composition layer that consumes existing admitted surfaces.

## Recommended product direction

### A. Metric Algebra Graph

Purpose:
- bind numerator/denominator/subset/sum identities
- expose conservation rules across player/team/goalkeeper surfaces
- distinguish primitive observed aggregate from derived aggregate

Outputs:
- metric_dependency_edges
- denominator_basis
- additive_components
- cross_entity_conservation_group
- reconciliation_state

### B. Process-Outcome Association Grid

Unit: admitted process episode, not raw row.

Candidate dimensions:
- process family
- participants / dyads
- start zone/channel
- duration bucket
- progressive-action bundle
- final-third entry
- box entry
- shot/chance terminal
- loss/recovery terminal

Safe statistics:
- support
- confidence (conditional frequency, clearly labeled)
- lift against match-local base rate
- 2x2 contingency / Fisher exact for small binary comparisons
- permutation-based rank association for small continuous samples
- numerator / eligible denominator

Correlation is a discovery signal, not the final claim.

### C. Actor/Pair Process Profile

For player and dyad:
- admitted process involvement
- with-shot involvement
- successful/failed/deviant variant involvement
- episode spread
- role/position context
- aggregate XLSX enrichment such as xG, xA, final-third receives, opponent-box actions

This supports analyst language like:
“Fenerbahce's shot-ending positional attacks were disproportionately represented among attacks involving Kerem + Guendouzi in this match.”

It does not say the pair caused the shots.

### D. Multi-Surface Argument Candidate

A candidate argument should combine:
1. process observation
2. participant/relation structure
3. outcome/consequence
4. aggregate metric context
5. match-local association statistic
6. counterexample
7. uncertainty/dependency burden
8. football-language interpretation

Example:
- Observation: 72 Fenerbahce positional attacks; 10 ended with a shot.
- Combination: Kerem + Guendouzi were together in 12; 5 ended with a shot.
- Context: both also show material final-third/box aggregate involvement in the XLSX surface.
- Counterexample: seven co-occurrences did not end with a shot; five shot-ending positional attacks occurred without the pair.
- Analyst meaning: a high-priority mechanism hypothesis for video/episode review, not causal proof.

## Scientific support

1. Kröckel, P., & Bodendorf, F. (2020). Process Mining of Football Event Data: A Novel Approach for Tactical Insights Into the Game. Frontiers in Artificial Intelligence, 3, 47. DOI: 10.3389/frai.2020.00047
Primary source: https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2020.00047/full
Relevance: football event sequences, player involvement order, process/sequence analysis.

2. Maneiro, R., Amatria, M., Losada, J. L., Jonsson, G. K., Arda, A., & Ivan-Baragano, I. (2025). Application of association rules to ball possessions in professional men's football. Frontiers in Psychology, 16, 1527437. DOI: 10.3389/fpsyg.2025.1527437
Primary source: https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2025.1527437/full
Relevance: Apriori/association rules over football possessions with support, confidence and lift.

3. Chan, V., Ebert, L., Hillmann, P.-J., Rubensson, C., Fahrenkrog-Petersen, S. A., & Mendling, J. (2025/2026 proceedings). Transforming Football Data into Object-Centric Event Logs with Spatial Context Information. DOI: 10.1007/978-3-032-13426-4_34
Preprint: https://arxiv.org/abs/2507.12504
Relevance: multi-object football event/process representation and spatial context.

4. SciPy current documentation, `spearmanr`, `fisher_exact`, `permutation_test`.
Source: https://github.com/scipy/scipy
Relevance: small-sample association testing; SciPy explicitly recommends permutation tests for small-sample Spearman inference.

Scite MCP was invoked for this research turn but the connected account had reached its monthly MCP limit. No new Scite-derived claim is used in this note.

## Decision

REAL_GAP_CONFIRMED.

Proposed next WIP:
**Multi-Surface Football Argument Composition Contract Audit**

Do not build a new general statistics platform.
Rehabilitate the existing:
- XLSX row projection
- aggregate-definition alignment
- cross-format reconciliation
- process participation
- consequence/counterevidence
- analyst-output chain

First executable target should be a deterministic match-local argument candidate for one process family (positional attacks) that combines process participation + shot outcome + XLSX context and emits no causal or independent-evidence claim.

