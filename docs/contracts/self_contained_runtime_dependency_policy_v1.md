# HPFA Self-Contained Runtime Dependency Policy V1

Status: `POLICY_SPEC / NOT_PRODUCTION`

## Purpose

HPFA product runtime must remain portable, offline-capable and reproducible. Research, donor repositories, web services and external libraries may inform implementation, but ACTIVE_MATCH execution must not depend on a live external service or remote model.

## Core invariant

```text
ACTIVE_MATCH input
-> hpfa product code
-> local deterministic computation
-> flat HPFA phone output
```

No network hop is required for a valid runtime result.

## Runtime dependency policy

### Allowed by default

- Python standard library;
- HPFA-owned modules inside the product repository;
- deterministic local data files shipped with the repository and covered by contract/test;
- local numerical routines implemented inside HPFA when their mathematical scope is tractable and reviewable.

### Allowed only after explicit dependency gate

A third-party package may be considered only when all of the following are satisfied:

1. capability cannot reasonably be implemented safely inside HPFA;
2. version and license are recorded;
3. offline installation/reproducibility is demonstrated;
4. runtime does not download weights/data/code;
5. dependency failure has a fail-closed path;
6. ACTIVE_MATCH output is invariant to network availability;
7. product owner explicitly admits the dependency.

Until then its method status is `DEFERRED_EXTERNAL_DEPENDENCY_NOT_ADMITTED`.

### Forbidden runtime behavior

- HTTP/API calls during ACTIVE_MATCH analysis;
- cloud inference as a required product step;
- remote model downloads;
- runtime package installation from the internet;
- hidden calls to external tactical/scouting/statistical services;
- donor repository import at runtime;
- Drive/Dropbox/GitHub as runtime truth providers;
- public notebooks/scripts fetched and executed dynamically.

## Mathematical implementation rule

For compact methods, HPFA implements and tests its own deterministic primitives. Examples:

- Shannon entropy;
- HHI;
- Euclidean geometry;
- interval relations;
- empirical quantiles;
- simple matrix/vector routines when numerically safe;
- 1D Wasserstein/sliced-projection primitives;
- graph degree/basic centrality primitives where tractable;
- deterministic changepoint cost functions where tractable.

Large numerical methods remain deferred until a safe internal implementation or an explicitly admitted offline dependency exists. Method sophistication must never be purchased by silently adding runtime dependency risk.

## Donor rule

`ADAPT_NOT_COPY` remains mandatory.

Donor code may provide formulas, test ideas, edge cases or architecture. Product code is re-derived against HPFA contracts, claim boundaries and ACTIVE_MATCH evidence. No donor package becomes a runtime dependency by being useful as research support.

## Reproducibility gates

Every executable scientific module must expose:

- module/version identifier;
- deterministic input contract;
- dependency manifest;
- algorithm/config parameters;
- explicit random seed when stochastic simulation is admitted;
- claim ceiling;
- fail-closed conditions;
- tests for sample-match identity leakage;
- flat phone-output compliance.

## Independence tests

Required for scientific modules as applicable:

```text
NO_NETWORK_RUNTIME
NO_DYNAMIC_CODE_FETCH
NO_REMOTE_MODEL_DEPENDENCY
NO_SAMPLE_MATCH_IDENTITY_LEAK
DETERMINISTIC_REPEATABILITY
REFLECTION_INVARIANCE
```

`REFLECTION_INVARIANCE` means adding/removing a dependent serialization reflection may alter raw surface-row volume but must not alter an admitted downstream numerator, denominator, transition, motif or confidence value after lineage collapse.

## Claim boundary

Self-contained execution does not itself validate a football interpretation. Offline deterministic code can still be epistemically wrong. Claim admission remains governed by upstream evidence contracts.

Always:

```text
canonical_event_count=UNKNOWN
production_release=false
```
