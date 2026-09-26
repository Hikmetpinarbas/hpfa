# HPFA Single Repository Consolidation — Current

Status: ACTIVE CONSOLIDATION STANDARD  
Canonical product repository: `Hikmetpinarbas/hpfa`

## Product decision

HPFA is the single canonical football-analysis product repository. Other analysis repositories are capability donors, historical laboratories, product-specific presentation references, or governance support. They do not remain parallel analytical engines.

The consolidation rule is **ADAPT_NOT_COPY**:

1. identify a football capability, not a file;
2. check whether current HPFA already owns the capability;
3. if a real gap exists, assign the capability to the current HPFA owner;
4. rewrite the capability against HPFA contracts and truth boundaries;
5. prove behaviour with tests and ACTIVE_MATCH evidence when runtime behaviour changes;
6. keep donor provenance in the capability registry;
7. never preserve donor folder topology, duplicate engines, donor naming, match-specific constants, agent prompts, merge-lab debris, generated reports, or historical runtime outputs inside the product tree.

Code must look coherent because it **is coherent**: one naming system, one package topology, one test discipline, one contract vocabulary and one runtime authority. No authorship claims are fabricated.

## Source roles

| Repository / surface | Consolidation role | Product decision |
|---|---|---|
| `Hikmetpinarbas/hpfa` | CANONICAL PRODUCT | sole product/code/runtime authority |
| `Hikmetpinarbas/YelFootballLab` | FOOTBALL CAPABILITY DONOR | mine unique football intelligence; adapt into HPFA owners |
| Termux `HPFA_DAILY_LAB` | PHYSICAL YEL/DONOR MIRROR | not independent evidence; same capability family as YEL |
| `Hikmetpinarbas/HIO-Analytics` | FOOTBALL PRODUCT DONOR | absorb reusable analytical capabilities; do not import mobile application shell |
| `Hikmetpinarbas/HP-Engine` | LEGACY ENGINE DONOR | sequence/temporal/claim ideas only; no engine import |
| `Hikmetpinarbas/HP-Motor` | LEGACY METRIC/REGISTRY DONOR | metric/validator/normalizer ideas only |
| `Hikmetpinarbas/HP-Motor-main` | LEGACY CANON/GATE DONOR | schema/gate/registry ideas only |
| `Hikmetpinarbas/HP-PROJELERI` | GOVERNANCE SUPPORT DONOR | no product code without explicit mapped capability |
| Poyraz repositories | OUTSIDE FOOTBALL PRODUCT CONSOLIDATION | no analytical product code transfer |

## Professional target tree

The final repository should converge toward:

```text
hpfa/
├── .github/                 # CI only
├── hpfa/                    # all permanent product Python code
│   ├── modules/
│   │   ├── core/            # observation, semantics, identity, relation, time/space, evidence
│   │   ├── postmatch/       # single-match football intelligence product
│   │   ├── prematch/        # future admitted opposition/prematch product
│   │   ├── scouting/        # future player/role comparison product
│   │   ├── longitudinal/    # future multi-match memory/trend product
│   │   ├── reporting/       # analyst/report composition
│   │   └── support/         # non-authoritative support adapters
│   └── platforms/           # stable platform boundaries / APIs
├── configs/                 # governed configuration only
├── tests/                   # repository-level integration/distribution tests
├── tools/                   # maintained operator/developer utilities only
├── ops/                     # bootstrap/physical acceptance/maintenance
├── docs/
│   ├── architecture/
│   ├── contracts/
│   ├── decisions/
│   ├── research/
│   └── operations/
├── runtime_evidence/        # acceptance evidence, never product authority by itself
├── README.md
├── pyproject.toml
├── LICENSE
├── NOTICE
└── THIRD_PARTY_NOTICES.md
```

Transitional compatibility wrappers may remain temporarily at repository root only when a current package entrypoint, workflow, runtime acceptance script, or product module consumes them. A root file with no current consumer is an orphan candidate and must be removed after proof.

## Root standard

Repository root is a product entrance, not a laboratory desk.

Disallowed final-state root material:

- abandoned report generators;
- generated match outputs;
- `_diag` artefacts;
- patch dumps;
- `*_bak`, `*_old`, `*_fixed`, version-copy forests;
- donor repository snapshots;
- `merge_lab`, `graveyard`, quarantine and archive code islands;
- team/match-specific scripts;
- AI-agent prompt/task dumps;
- model/provider experimentation that is not a current product dependency.

Temporary compatibility wrappers are tracked as migration debt, not architectural owners.

## Current donor decisions

### Already absorbed or substantially absorbed

- HP-Engine sequence candidate reconstruction → current visible action sequence / partial-order / episode/process owners.
- HP-Engine claim consolidation → current Safe Finding / defeasible argument / claim admission chain.
- HP-Engine temporal/context signals → current context-signal and temporal admission surfaces.
- HP-Motor metric registry / required-field concept → current metric registry, definition policy and metric governance.
- HP-Motor provider/vendor aliasing → current provider field/value semantic owners.
- HP-Motor-main canonical schema/gate discipline → current canonical ingest, source mapping, data quality and admission gates.
- YEL process statistics / mechanism discovery → current rich multiformat analysis, Process Variant Board and mechanism review.
- YEL player-process attribution concept → current actor/process participation and player-function profiles, with causal-credit lock.
- YEL set-piece process intelligence → current process family / six-phase / interaction surfaces where admitted.
- HIO repeated chain / shot-ending route / coarse spatial-process concepts → current process variant, consequence and spatial transition owners.

### ADAPT_NOW

1. **Explicit typed passer→receiver relation admission**  
   Donor seed: YEL `passing_network_admission.py`.  
   Current owner: `cross_role_relation_candidate_resolver_lite`.  
   Product rule: no receiver inference from next player, row order or same-team continuation. Network construction remains blocked until typed receiver relation is admitted.

2. **Professional root contraction**  
   Remove verified unowned root tools; migrate maintained entrypoints into stable package/CLI ownership over successive slices.

### ADAPT_LATER

- YEL/HIO visualization admission contracts → professional product/presentation layer after current Postmatch intelligence closure.
- YEL reference populations → scouting/longitudinal product with explicit unit, competition, season and dependency contracts.
- YEL longitudinal intelligence → multi-match evidence memory; opponent/context adjustment required before stronger interpretation.
- YEL player comparability / role reference population → scouting lane.
- YEL prematch↔postmatch hypothesis calibration → prematch product after longitudinal evidence memory.
- YEL opportunity/execution separation → longitudinal/scouting denominators.
- YEL compositional structure → test/contract donor only until observation unit, dependency and football construct compatibility are explicit.
- HIO relation-aware visual products and export ergonomics → reporting/platform layer, not analytical authority.

### REJECT / HISTORICAL

- next-player-as-receiver pass-network proxies;
- team-shape inference from event pass networks;
- raw donor engines copied wholesale;
- `city_gs` / match-name-specific tools as product code;
- confidence-threshold claim promotion;
- donor folder topology, duplicate version families and merge-lab trees;
- generated donor outputs as source code;
- mobile application shells inside the analytical core;
- any donor code whose licence/provenance cannot be safely established.

## Completion definition

Consolidation is complete only when:

- one canonical analysis repository remains: `Hikmetpinarbas/hpfa`;
- every active football capability has one HPFA owner;
- no active runtime imports donor repositories;
- no donor repository is required to execute ACTIVE_MATCH;
- root contains only intentional product/distribution entry surfaces;
- all donor-derived ideas have a capability decision and provenance record;
- all maintained code follows HPFA naming, contracts, tests and claim boundaries;
- different match packages can use the same code without team/provider hardcoding;
- product reports expose football knowledge, not implementation internals.
