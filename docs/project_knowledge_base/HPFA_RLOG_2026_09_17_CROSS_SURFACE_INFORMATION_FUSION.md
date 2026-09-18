# HPFA Research Log — Cross-Surface Information Fusion

Kayıt tipi: AR-GE / research support  
Tarih: 2026-09-17  
Product scope: single-match Postmatch  
Runtime authority: reference-only; this file is not ACTIVE_MATCH truth.  
Canonical ontology: `EVENT ⊂ ZFGV`; event is one observation family, not the whole observation universe.

## 1. Research Question

How can PLAYER/TEAM/GK CSV/XML occurrence-process-spatial observations and PLAYER/GK XLSX aggregate/tabular features be fused mathematically to produce new, auditable football intelligence without treating reflections as independent evidence or aggregate metrics as action identity?

Primary research target:

`Observation Fusion → Mathematical Structure Discovery → Composite Football State → Process/Transition Intelligence → Defensible New Football Knowledge`

## 2. Main Scientific Finding

The strongest immediate route is **not** a single universal latent model. The evidence supports a staged architecture:

1. **Valid compositional families** first: only parts that genuinely form a fixed or semi-fixed whole should enter CoDA.
2. **Deterministic provenance/dependency redundancy** before statistical information decomposition.
3. **MI/CMI discovery** for nonlinear dependence once variable semantics and eligible samples are stable.
4. **PID / synergy** only after sample sufficiency and estimator stability are demonstrated.
5. **Mixed-resolution representation** should reuse feature-level semantic interaction ideas, but not train a single-match neural embedding.

This ordering is productive rather than restrictive: it prevents the statistical layer from rediscovering known serialization/role dependencies as if they were new football information.

## 3. Candidate A — COMPOSITIONAL_ACTION_BALANCE_V1

**Status:** NEXT / HIGH-VALUE RESEARCH CAPITAL

### Football question

Within an admitted action/process family, is the visible action mix relatively concentrated toward one football route versus another?

Examples of candidate compositions, only if the parts close a valid whole:

- pass / carry / duel / shot / recovery / loss;
- short / medium / long distribution;
- progressive / lateral / backward pass family;
- final-third / box / non-box participation family.

### Mathematical basis

For a composition `x=(x1,...,xD)` with constant or closure-normalized total, relevant information is relative. Aitchison geometry and log-ratio coordinates avoid spurious Euclidean correlation created by the constant-sum constraint.

Useful representation:

`clr_i(x) = ln(x_i / g(x))`

For interpretable modelling use ILR balances, where each coordinate is a log-ratio between two football-meaningful groups of parts.

### HPFA implementation interpretation

Do **not** run CoDA over all 131 PLAYER XLSX columns or all 109 GK columns. First define an auditable `composition_family_id` with:

- component metric IDs;
- closure rule;
- total/exposure definition;
- structural-zero policy;
- sampling-zero policy;
- missing/undefined policy;
- role/context scope;
- dependency groups;
- representation version.

A football balance should be expert-defined before data-driven optimization when possible. Example conceptual balance:

`ADVANCE_BALANCE = log( geometric_mean(progressive_pass, carry_entry, final_third_pass) / geometric_mean(lateral_pass, backward_pass) )`

This is a profile coordinate, **not** a quality score or intention claim.

### Why this matters

Raw percentage correlation among parts can be mechanically induced by closure. CoDA changes the question from “which percentages correlate?” to “which relative trade-offs characterize the admitted action mix?”

### Zero handling

Zero is not one thing. Before log-ratio transformation distinguish at minimum:

- true/structural zero;
- sampling/rounded zero;
- missing/unobserved;
- undefined/no denominator.

Automatic pseudocount replacement is not product-safe without a declared sensitivity policy.

### Sources

- Vives-Mestres, Martín-Fernández & Kenett (2016), *Compositional Data Methods in Customer Survey Analysis*, DOI: https://doi.org/10.1002/qre.2029 — simplex, log-ratio coordinates, scale invariance, subcompositional coherence.
- Tang et al. (2021), *Dirichlet composition distribution for compositional data with zero components*, DOI: https://doi.org/10.1002/bimj.202000334 — essential vs rounded zeros and zero-handling burden.
- Fačevicová et al. (2018), *General approach to coordinate representation of compositional tables*, DOI: https://doi.org/10.1111/sjos.12326 — interpretable Aitchison-coordinate decomposition of factor interactions.
- Fiksel, Zeger & Datta (2021), *A transformation-free linear regression for compositional outcomes and predictors*, DOI: https://doi.org/10.1111/biom.13465 — reminder that zero-bearing compositions can require alternatives to log-ratio-only modelling.

## 4. Candidate B — CROSS_SURFACE_INFORMATION_DEPENDENCY_LEDGER_V1

**Status:** NEXT / STRONGLY ALIGNED WITH CURRENT DEPENDENCY CLOSURE

### Football question

When XLSX and CSV/XML both appear to describe progression, creation, loss, distribution or another construct, how much of the apparent agreement is already explained by known reflection/projection/role transformation, and what remains genuinely additional?

### Core principle

Statistical redundancy must not be asked to rediscover known source lineage.

First remove or tag deterministic dependencies already known from the evidence spine:

- `SERIALIZATION_REFLECTION`
- `PARTIAL_SEMANTIC_PROJECTION`
- `ROLE_TRANSFORMATION`
- `AGGREGATE_DERIVATION_UNRESOLVED`
- `UNRESOLVED`

Then calculate information/dependence only on eligible non-duplicated analytical units.

### Proposed ledger fields

- source_variable_a
- source_variable_b
- construct_family
- context_scope
- deterministic_dependency_type
- shared_root_flag
- eligible_n
- resolved_n
- censored_n
- missing_n
- variable_type_a/b
- estimator_id/version
- MI / normalized MI when eligible
- CMI context if eligible
- permutation/null baseline
- bootstrap/stability interval
- claim_ceiling=`STATISTICAL_DEPENDENCY_ONLY`

### Analyst gain

This separates three different situations that raw correlation conflates:

1. same information repeated in another surface;
2. same football construct seen from a different role/resolution;
3. genuinely additional information supplied by the joint surfaces.

## 5. Candidate C — PID_SYNERGY_DISCOVERY_V1

**Status:** LATER / RESEARCH_PROTOTYPE_ONLY / SAMPLE-SUFFICIENCY REQUIRED

### Football question

Can two source families jointly contain information about a target football outcome/process that neither source carries alone?

Example research hypothesis:

`X1 = admitted progression composition/profile`

`X2 = local occurrence/process-spatial state`

`Y = visible final-third access or consequence family`

PID conceptually decomposes:

`I(X1,X2;Y) = Redundant + Unique(X1) + Unique(X2) + Synergistic`

### Important limitation

PID is not one universally settled estimator. Redundancy definitions differ and deterministic dependencies constrain interpretation. Finite-sample bias is especially dangerous for synergy. Therefore single-match PID output must not be a professional finding unless a future validated sample-sufficiency/stability contract exists.

### Product-safe research order

1. deterministic dependency topology;
2. pairwise MI/CMI with permutation baseline;
3. stability resampling;
4. only then PID prototype;
5. multi-match replication before product binding.

### Sources

- Williams & Beer (2010), *Nonnegative Decomposition of Multivariate Information*, arXiv: https://arxiv.org/abs/1004.2515 — foundational redundancy lattice and nonnegative partial information atoms.
- Ince et al./related PID literature should be considered in later estimator selection; do not canonize the original `I_min` redundancy measure without comparison.
- Recent finite-sample research reports that PID components are biased unevenly and synergy can be much more sample-sensitive than unique/redundant terms; estimator validation is therefore a prerequisite for HPFA product use.

## 6. Candidate D — MIXED_RESOLUTION_FEATURE_CONTRACT_V1

**Status:** NEXT_AFTER_DEPENDENCY_CLOSURE / RESEARCH_SUPPORTED

### Football question

How can aggregate XLSX feature families and occurrence/process/spatial observations be represented together without collapsing one resolution into the other?

### Recommended design

Use a transparent feature contract rather than a learned single-match embedding.

Candidate object:

- `composite_state_id`
- `actor_ref/team_ref`
- `family={PROGRESSION,CREATION,THREAT,RETENTION_SECURITY,DUEL_INTERACTION,GK_DISTRIBUTION,SPATIAL_PROCESS}`
- aggregate component refs
- occurrence/process refs
- spatial/context refs
- normalization/exposure state
- dependency groups
- missingness/censoring state
- representation_version
- claim_ceiling=`DESCRIPTIVE_COMPOSITE_STATE_ONLY`

### Why not train the dense model now?

Yang, Memmert & Klemp-Weins (2026), *A Universal Dense Football Event Representation Based on TabTransformer*, arXiv: https://arxiv.org/abs/2606.09327, demonstrates that heterogeneous football-event features can be represented jointly at feature level. But its pretraining uses **6,391,338 events from 1,823 matches**, and the authors explicitly state that empirical evaluation in data-scarce regimes is absent. The model also derives a 911-dimensional event embedding from 28 categorical and 15 continuous features.

Transferable idea for HPFA now:

- preserve feature-level semantic interactions;
- keep continuous and categorical semantics explicit;
- anonymize identity where model training could confound reputation;
- avoid treating an event as an indivisible token when feature interactions matter.

Not transferable now:

- single-match learned dense embedding as production truth;
- latent similarity as football-quality truth;
- neural representation replacing admitted evidence lineage.

## 7. Immediate Science-to-Product Decision

### ADAPT/NEXT

1. `COMPOSITIONAL_ACTION_BALANCE_V1` — after explicit composition-family registry and zero taxonomy.
2. `CROSS_SURFACE_INFORMATION_DEPENDENCY_LEDGER_V1` — build on current dependency topology, not as a parallel engine.
3. `MIXED_RESOLUTION_FEATURE_CONTRACT_V1` — transparent composite state representation after dependency closure.

### LATER

4. `PID_SYNERGY_DISCOVERY_V1` — requires sample sufficiency, estimator comparison, permutation/null baseline, stability and preferably multi-match replication.
5. Learned dense embeddings — multi-match model layer only.

### REJECT NOW

- running Pearson/Spearman on closed compositions as if unconstrained;
- applying ILR/CLR to arbitrary non-compositional XLSX columns;
- automatic pseudocounts without zero taxonomy/sensitivity analysis;
- interpreting MI/PID as causality;
- treating synergy as tactical intelligence or quality;
- using a single-match neural embedding as product truth.

## 8. New Analyst-Facing Football Intelligence Enabled

The scientific gain is not “a more complex score.” It is the ability to say, for example:

- “The player’s admitted progression mix was relatively shifted toward carry/forward-access routes rather than recycling routes.”
- “The XLSX progression family and local final-third occurrence family share information beyond known serialization reflection, but the current evidence only supports statistical dependence.”
- “Two surfaces appear redundant because of provenance, not because two independent observations agreed.”
- “A future multi-match PID study can test whether aggregate progression profile and local process-spatial state jointly add information about visible access that neither source provides alone.”

## 9. Red-Team / Withdrawal Conditions

Withdraw or downgrade the construct if:

- components do not form a coherent composition;
- denominator/closure changes across compared units;
- zero type is unresolved;
- dependency/reflection burden is unresolved;
- MI/CMI estimate is unstable under permutation/bootstrap sensitivity;
- sample size is too small for the selected estimator;
- context conditioning fragments the sample below usable support;
- the output is being interpreted as causality, intention, tactical truth or player quality.

## 10. Product Engineering Transfer

- Transfer now? `YES, BOUNDED / AFTER CURRENT WIP AND DEPENDENCY CLOSURE`
- New parallel engine? `NO`
- Primary reuse target: existing dependency / aggregate-definition / construct-feature / process-context owners.
- Physical ACTIVE_MATCH required before analyst-facing product binding: `YES`
- Merge/release authorization: `NO`

## 11. Research Gap for Next Round

Next high-value research question:

**How should HPFA define and validate football-meaningful ILR balances and cross-surface information targets from the actual 131-player-field and 109-GK-field XLSX schema, instead of choosing components abstractly?**

This requires schema-level mapping of the real XLSX columns into:

- valid compositions;
- formative composites;
- reflective indicators;
- exposure variables;
- outcomes/targets;
- model outputs;
- undefined/no-denominator fields.

That mapping should precede any production CoDA, MI, CMI or PID computation.
