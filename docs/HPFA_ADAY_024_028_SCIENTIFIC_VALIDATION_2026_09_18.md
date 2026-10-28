# HPFA ADAY 024–028 Scientific Validation — 2026-09-18

STATUS: RESEARCH VALIDATION ONLY  
PRODUCT AUTHORITY SNAPSHOT: PR #359 live head `d6bd4f9208f609691c990515481849421c659725` at write time  
RELEASE: OPEN / DRAFT / UNMERGED; production_release=false

## Research question

Do the newly added ADAY 024–028 candidates contribute genuinely new, defensible football intelligence to the current Single-Match Postmatch evidence spine, and what scientific limits must govern implementation?

## Source use

Academic connectors used in this validation:
- SciSpace
- Scholar Gateway
- Scite
- Sider Scholar
- Undermind
- alphaXiv
- Consensus requested but unavailable because the connected account's monthly search quota was exhausted; no Consensus result is used as evidence.
- Context7 used for current scikit-learn `mutual_info_regression` implementation semantics.
- Fresh GitHub frontier audited before product conclusions.

No connector output is product truth. Product truth remains fresh HPFA repository + claim-appropriate test/runtime evidence.

---

## ADAY 024 — PARTIAL IDENTIFICATION / CENSORING RATE BOUNDS

### Scientific verdict

**SUPPORTED, AND ALREADY IMPLEMENTED ON CURRENT OWNER. DO NOT RE-IMPLEMENT.**

Fresh frontier contains:
- `docs/HPFA_PARTIAL_IDENTIFICATION_CENSORING_RATE_BOUND_ADAPTATION_V1.md`
- implementation in `safe_finding_occurrence_consequence_burden_adapter.py`
- dedicated tests

Current implementation follows the scientifically defensible distinction between:
- point identification,
- partial/set identification,
- unresolved denominator membership,
- censoring/missing-outcome uncertainty.

### Scientific basis

Partial-identification literature supports reporting identified sets/bounds when missing outcomes cannot be point-imputed without stronger assumptions.

Useful primary/peer-reviewed examples:
- Manski, partial identification framework: https://doi.org/10.1057/9780230280816_21
- Adegboye et al. (2024), partial identification under non-response: https://doi.org/10.1002/sim.10108
- Sakaguchi, partial identification with endogenous censoring: https://doi.org/10.1002/jae.3024
- Daly-Grafstein & Gustafson, partial identification for discrete data with nonignorable missing outcomes: alphaXiv/arXiv 2308.07319
- Rubinstein et al. (2024), bounds under mixed informative/non-informative censoring: https://doi.org/10.48550/arxiv.2411.16902

### HPFA-safe interpretation

For known eligible denominator membership and unresolved binary outcome:
[
N=s+f+u,quad L=s/N,quad U=(s+u)/N
]

This is an **identification interval**, not a confidence interval.

The implementation must not claim:
- population success probability,
- statistical confidence coverage,
- causal effect,
- latent outcome truth.

### Frontier consequence

ADAY 024 should now move from **NEXT** to:

**IMPLEMENTED_ON_EXISTING_OWNER_PENDING_EXACT_HEAD_CI_AND_PHYSICAL_ACCEPTANCE**

No parallel statistics engine is warranted.

---

## ADAY 025 — OBSERVED PLAYER–PROCESS OUTCOME PROFILE

### Scientific verdict

**SUPPORTED WITH A CRITICAL SCOPE NARROWING.**

Football event-sequence literature supports evaluating player actions/participation in possession or event sequences, but more ambitious player-value methods often introduce predictive, regression, counterfactual, or tracking assumptions that HPFA should not import into the current single-match descriptive product.

Relevant literature:
- Bransen & Van Haaren, *Measuring Football Players' On-the-ball Contributions from Passes during Games* (2018), event-based on-ball contribution.
- Dick, Tavakol & Brefeld, *Rating Player Actions in Soccer* (2021), action valuation from event data.
- Bajons, *Evaluating Player Performances in Football: A Debiased Machine Learning Approach* (2023), possession-sequence player contribution: https://doi.org/10.1145/3613347.3613368
- Bajons & Hornik, possession-sequence adjusted plus-minus (2024): https://doi.org/10.48550/arxiv.2407.17832
- Goes et al., *Not Every Pass Can Be an Assist* (2019), contextual pass effectiveness.
- Off-ball valuation studies returned by SciSpace rely on tracking/low-level spatiotemporal data and therefore are not transferable as event-only truth.

### Product-safe unit

The safe production unit is not “all player opportunities”.

It is:

**player × explicitly admitted process participation instance**

The profile can report:
- admitted participation count,
- visible success/failure variant association,
- unresolved/censored outcome count,
- episode spread,
- partner/dyad concentration,
- first-supported-divergence participation,
- counterevidence locators.

### Critical rejection

Event absence cannot establish:
- player was playable,
- player was an available passing option,
- player created space,
- player should have received the ball.

Therefore:

`OBSERVED_PARTICIPATION != ALL_AVAILABLE_OPPORTUNITY`

### Product conclusion

ADAY 025 remains a genuine product gap, but it should reuse:
- process participation,
- actor concentration,
- process variant,
- divergence,
- consequence burden,
- ADAY 024 bounds.

No new player identity or player-rating engine.

---

## ADAY 026 — RECEIVED PROGRESSION RETENTION

### Scientific verdict

**FOOTBALL-VALUABLE, BUT IMPLEMENTATION MUST WAIT FOR TYPED RECEIVER RELATION CLOSURE.**

The football literature consistently distinguishes action execution from downstream possession outcome, and pass-value literature shows the importance of contextual reception/continuation. However, receiver-side attribution cannot be product-safe unless HPFA can bind the receiver relation explicitly enough.

### Required product chain

[
	ext{delivered progression}
ightarrow
	ext{admitted receiver}
ightarrow
	ext{next admitted step}
ightarrow
{	ext{retained, lost, censored, unresolved}}
]

### Double-credit warning

The same physical progression cannot become independent full credit for:
- passer,
- receiver,
- process.

These are role-specific projections over shared lineage.

### Current decision

**READY_SPEC_BLOCKED_BY_TYPED_RECEIVER_RELATION**

Do not implement from timestamp proximity or “next player” heuristics.

---

## ADAY 027 — PROCESS PARETO / TRADE-OFF RELATION

### Scientific verdict

**SUPPORTED, WITH STRONG DIMENSIONALITY AND INTERPRETATION LIMITS.**

Pareto dominance is well suited to HPFA only as a **relation preserving visible trade-offs**, not as an optimization/winner engine.

Direct sport precedent:
- Newans, Bellinger & Minahan (2022), *The balancing act: Identifying multivariate sports performance using Pareto frontiers*: https://doi.org/10.3389/fspor.2022.918946

General methodological support:
- Deb & Ehrgott (2023), generalized dominance structures: https://doi.org/10.3390/mca28050100
- Russell & Allman (2022), many-objective dimensionality reduction: https://doi.org/10.1002/aic.17962
- Efatmaneshnik et al. (2023), many-objective Pareto limitations: https://doi.org/10.1002/sys.21690
- He, Friedman & Bailey-Kellogg (2011), trade-off interpretation without arbitrary a-priori weights: https://doi.org/10.1002/prot.23237

### Key scientific warning

As objective count increases, non-dominated-set size can expand dramatically. In small-N/high-d settings, almost every observation may become non-dominated, making the frontier descriptively useless.

Therefore HPFA should:
- default to 2–3 semantically distinct dimensions,
- declare direction per dimension,
- preserve tolerance provenance,
- expose frontier saturation,
- never emit a scalar winner from Pareto membership.

### Safe relation vocabulary

- `DOMINATES_WITHIN_DECLARED_DIMENSIONS`
- `NON_DOMINATING_TRADEOFF`
- `EQUIVALENT_WITHIN_TOLERANCE`
- `PARTIALLY_COMPARABLE`
- `NOT_COMPARABLE`

### Forbidden inference

- NON_DOMINATED != BEST
- DOMINATED != BAD FOOTBALL
- PARETO_EFFICIENT != TACTICALLY OPTIMAL
- SHORTER != BETTER
- FEWER ACTIONS != BETTER

### Context7 implementation note

Current scikit-learn `mutual_info_regression` is a KNN-based univariate dependence estimator. `n_neighbors` changes variance/bias trade-off and wrong discrete/continuous typing can invalidate estimates. It is therefore suitable only as an optional redundancy research diagnostic, not as a required Pareto core dependency.

Core Pareto comparison should remain deterministic pure Python.

---

## ADAY 028 — UI-READY MECHANISM CARD / MATCH STORY PROJECTION

### Scientific verdict

**SUPPORTED AS A PRESENTATION/DECISION-SUPPORT PROJECTION, NOT AS A NEW REASONING ENGINE.**

Fresh repo already contains:
- `mechanism_story_review_selector.py`
- `analyst_mechanism_review.py`
- first-supported-divergence projection
- comparable counterevidence
- source-bound Safe Finding / Analyst Output contracts

Therefore a new “mechanism reasoning engine” is a false gap.

### HCI / decision-support basis

Evidence supports several useful design principles:

- Cook & Smallman (2008), *Human Factors of the Confirmation Bias in Intelligence Analysis*: graphical evidence landscapes can promote more balanced evidence selection; confirmation bias is a real decision-support concern. DOI: https://doi.org/10.1518/001872008X354183
- Varga & Varga (2016), *Visual Analytics: Data, Analytical and Reasoning Provenance*: provenance supports analyst reconstruction of what data was used, how analysis occurred, and why reasoning paths were taken. DOI: https://doi.org/10.1007/978-3-319-40226-0_9
- Laker et al. (2017), information overload and emphasis framing: highlighting selected information can improve decision quality but creates a speed/accuracy trade-off. DOI: https://doi.org/10.1111/poms.12777
- Wesslen et al. (2019), visual anchors can influence user activity, confidence, speed and sometimes accuracy, so salience/color/priority must not silently become truth. DOI: https://doi.org/10.1111/cgf.13679

### HPFA design consequences

1. Counterevidence should be structurally visible, not buried.
2. Review locator/provenance should remain one-step accessible.
3. Claim ceiling and unresolved/censoring burden must not disappear in summary cards.
4. A “top 3–5” shortlist is an attention mechanism, not evidence ranking.
5. Color/status must not encode unsupported confidence.
6. Safe meaning must be source-bound; UI copy cannot invent tactical explanation.
7. Zero mechanism cards is valid when admission does not support a mechanism.

### Critical correction to HFI-11

Examples such as:
- support >= 3
- counterexample >= 1
- variants >= 2

must not become universal truth gates.

They can be UX examples or candidate heuristics, but product admission remains governed by current denominator/spread/dependency/censoring contracts.

### Product conclusion

ADAY 028 remains:

**NEXT_AFTER_RELATION_DEFEAT_STORY_CLOSURE / OUTPUT-PROJECTION ONLY**

---

## Cross-candidate sequence after fresh frontier audit

Current fresh frontier materially changed during this research pass.

At the start of this pass, ADAY 024 was a candidate.
At live head `d6bd4f9208f609691c990515481849421c659725`, ADAY 024 is already implemented on the existing owner and awaiting exact-head CI/physical acceptance.

Therefore the queue should be dynamically interpreted as:

1. Close current WIP / exact-head physical acceptance requirements.
2. Physically accept ADAY 024 implementation; do not duplicate it.
3. ADAY 025 — observed player-process outcome profile.
4. ADAY 026 — only after typed receiver relation closure.
5. ADAY 027 — after closed typed relation contract can carry dominance/trade-off semantics.
6. ADAY 028 — after relation/defeat/story closure, as a UI/report projection only.

## Connector limitations recorded

- Consensus: monthly search quota exhausted; no result used.
- Sider Scholar: broad searches produced low-precision results for some questions; only directly relevant returned works should be used.
- Scholar Gateway summaries were used as discovery/support and should be verified against source papers for implementation-critical claims.
- No academic connector result overrides HPFA product/runtime authority.

## Final research decision

The strongest new product knowledge is not another model.

It is a sequence of **bounded representational upgrades**:

[
	ext{censoring bounds}
ightarrow
	ext{observed player-process profile}
ightarrow
	ext{receiver-retention relation}
ightarrow
	ext{non-scalar process trade-off relation}
ightarrow
	ext{auditable analyst mechanism card}
]

Each step creates new football information while preserving the existing evidence spine and WIP=1 discipline.
