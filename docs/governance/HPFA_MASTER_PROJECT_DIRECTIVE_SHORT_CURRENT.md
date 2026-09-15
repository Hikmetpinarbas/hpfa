# HPFA MASTER PROJECT DIRECTIVE — SHORT CURRENT

Version: 2026.09.08-ENRICHED-OBSERVATION
Status: ACTIVE_GOVERNANCE_RECORD

## PROJECT
HPFA = Hikmet Pınarbaş Football Analytics.
Claim-safe, modular and portable Football Intelligence Platform operating on **Enriched Football Observation Data / Zenginleştirilmiş Futbol Gözlem Verisi**.

`event-only` is a legacy/source-class description where useful. It is **not** the product-wide observation ceiling and must not be used as a binary reason to suppress an otherwise admitted temporal, spatial, relational, process, consequence or reconstructed-state capability.

HPFA turns visible and admitted football observation into defensible analyst intelligence without promoting rows, labels, timestamps, coordinates, metrics, model outputs or reconstructed relations beyond the evidence that supports them.

## OBSERVATION MODEL
Construct admission is based on the observation layers and semantics actually required:

```text
L0_AGGREGATE_SURFACE
L1_ACTION_OBSERVATION
L2_TEMPORAL_OBSERVATION
L3_SPATIAL_OBSERVATION
L4_RELATIONAL_COOCCURRENCE_OBSERVATION
L5_PROCESS_CONTEXT_OBSERVATION
L6_CONSEQUENCE_OPPONENT_RESPONSE_OBSERVATION
L7_RECONSTRUCTED_STATE_TRANSITION_CANDIDATE
L8_TRACKING_VIDEO_PHYSICAL_OFF_BALL_STATE
```

Rules:
- L1-L7 are not automatically tracking-only.
- Rich observation at L2-L7 requires explicit source/surface semantic admission.
- L8 requires tracking/video authority.
- Coordinates do not automatically prove pitch control, team shape or off-ball structure.
- Temporal fields do not automatically prove football chronology.
- Co-occurrence does not automatically prove interaction, marking, pressure or causality.
- Reconstructed state transitions remain candidates until their upstream gates are admitted.
- Global `event_only_compatible=true/false` must not be the sole executable capability gate for new or migrated constructs.

The canonical executable observation contract is the current hpfa implementation of `observation_contract_lite` when landed on main. Until landing, the exact PR head is engineering evidence only.

## USER ROLE AND RUNTIME EVIDENCE
The user is a football analyst / football data analyst.
Every real runtime result must provide two separate evidence layers:
1. Engineering evidence: head, input, execution, tests, status, outputs and failures.
2. Analyst evidence: WHAT_VISIBLE, WHERE_WHEN, SUPPORT, COUNTEREVIDENCE, SAFE_MEANING, FORBIDDEN_INFERENCE, ANALYST_ACTION, ALTERNATIVE_EXPLANATION, UNCERTAINTY and WITHDRAWAL_CONDITION.

## RUNTIME AUTHORITY
The sole ACTIVE_MATCH truth is:
`runtime/active_single_match/current`

Absolute Termux paths are discovered at execution time and are not product authority.
Google Drive, Dropbox, PDFs, archives, reports, donor repos, academic literature and historical runtime material are REFERENCE_ONLY / DONOR_SUPPORT / RESEARCH_SUPPORT / HISTORICAL_LINEAGE. They never override ACTIVE_MATCH.

## REPOSITORY ROLES
- `hpfa`: only product repository.
- `HP-Motor`: ingest, validation, phase/possession/sequence/metric primitive donor.
- `HP-Engine`: pattern, sequence intelligence, semantic/claim gate, graph, contradiction/explanation donor.
- `HP-PROJELERI`: governance, policy, authority, release and registry donor.

## DONOR RULE
`ADAPT_NOT_COPY`
`REHABILITATE_BEFORE_PARALLEL_ENGINE`
`CODE_LAST`

Required path:
current hpfa producer → gap → donor/support role → HPFA contract → admission → invariants/tests → ACTIVE_MATCH need → minimal code → engineering evidence → analyst evidence → Red Team → release decision.

## SOURCE SEARCH ORDER BEFORE CODING
1. current hpfa
2. HP-Motor
3. HP-Engine
4. HP-PROJELERI
5. Google Drive
6. Dropbox
7. academic/web support
8. targeted Termux discovery
9. code

## CURRENT PRODUCT MODEL

```text
RAW / SURFACE
→ source authority
→ ACTIVE MATCH
→ readers / provider semantics
→ reflection control
→ Row Nucleus
→ Evidence Atom
→ match-local identity candidates
→ action / semantic-role candidates
→ temporal observation admission
→ spatial observation admission
→ relational / co-occurrence admission
→ partial order
→ consequence / opponent-response observation
→ context
→ Analyst Episode
→ Episode Features
→ Change
→ Recurrence / Variation / Deviation
→ Counterevidence / Falsifier
→ Metric / Model candidates
→ Defeasible Finding
→ Analyst Report Block
```

This is a conceptual DAG. A node that is not implemented and admitted must not be presented as current product truth.

## SURFACE / COUNT RULES
CSV, TSV, XML, XLS/XLSX, JSON and JSONL are observation surfaces.
Surface rows are not canonical events.

Use:
`surface rows`, `visible rows`, `event-like rows`, `row-level evidence`, `action-family volume`, `observation candidate`, `process candidate`, `state-transition candidate`.

Do not infer:
- missing value = zero;
- missing column = absent behaviour;
- same timestamp = duplicate event;
- provider label = canonical event key;
- CSV/XML mirror = independent actions;
- XLSX aggregate row = timeline event.

Until explicit later admission:
`canonical_event_count=UNKNOWN`
`true_action_count=UNKNOWN`

## DUPLICATE / REFLECTION RULE
Same SHA-256 at different paths is an exact duplicate reflection/lineage observation, not automatically a conflict.
CSV/XML/XLSX reflections of the same upstream fact are not independent evidence votes and must not multiply football volume.

## IDENTITY / RELATION RULE
Provider fields, codes, aliases, team/player tokens, action labels and relation labels begin as candidates.
Identity is match-local unless an explicit registry proves otherwise.
ROW_NUCLEUS != ACTION_OCCURRENCE.
ACTION_BUNDLE != CANONICAL_EVENT.
LABEL != ACTION TRUTH.
Co-occurrence / shared timestamp / shared coordinate does not by itself establish interaction truth.

## TIME RULE
Numeric time parseability is not football chronology.
Admission requires semantic role + unit + clock basis + period/context + provenance.
Source row order/event_index/list order is provenance only.
Same timestamp does not create internal order.

Allowed relation states:
```text
BEFORE_CONFIRMED
AFTER_CONFIRMED
SAME_TIME_UNORDERED
ORDER_INDETERMINATE
PROVENANCE_ORDER_ONLY
```

## CLAIM SAFETY
Observation richness raises the **available evidence ceiling**, not the right to overclaim.

Without the relevant explicit gate, HPFA must not assert:
- pitch control;
- team shape / formation truth from action locations;
- defensive-line height;
- compactness;
- off-ball structure/run;
- passing-option geometry;
- body orientation / scanning;
- physical load/fatigue/speed;
- true pressure or closing geometry;
- coach intention / tactical plan;
- dominance;
- causality.

A capability requiring true physical trajectories or off-ball state belongs to L8 / REQUIRES_TRACKING or REQUIRES_VIDEO.
A capability supported by admitted temporal/spatial/relational/process/consequence observation at L2-L7 must not be rejected merely because it is richer than a bare event stream.

## ANALYST INTELLIGENCE
The system should produce more than counts or narrative:
observation → evidence grouping → context → episode → recurrence/change → alternative explanation → counterevidence → safe argument → report.

Minimum product bridge:
Evidence → Episode → Safe Finding → Analyst Report Block.

Attention apparatus such as Match ECG may surface `ATTENTION_SIGNAL` / `FOCUS_CANDIDATE`, but such signals are not findings. They must drill down into admitted evidence and counterevidence before analyst promotion.

## METRIC / MODEL
Formula alone is not product capability.
Every metric/model must define construct, observation surface, required observation layers, required surface semantics, inputs/units, eligibility, prerequisites, denominator/exposure, leakage, validation, uncertainty, provenance/dependency, interpretation, claim ceiling and release state.

`event_only_compatible` may remain as legacy metadata during migration; construct-specific observation admission is authoritative for capability scope.

## PHONE OUTPUT POLICY
All user-visible Termux outputs must be written directly under:
- `/sdcard/Download/HPFA`
- `/storage/emulated/0/Download/HPFA`

Nested output is rejected with:
`nested_phone_output_directory_rejected`

Phone paths must be discovered before use. `/sdcard` and `/storage/emulated/0` reflections must not be ingested twice.

## MATCH-AGNOSTIC RULE
Product code must not hardcode match names, teams, dates, tournaments, sample IDs or sample row counts.
Required regression:
`test_no_sample_match_identity_leak`

## RED TEAM
Every important capability must check:
correlation→causation
row order→chronology
same timestamp→total order
numeric field→semantic truth
format/metric count→independent evidence
pass network→team shape
PPDA→pressing truth
average position→formation truth
probability→fact
recurrence→coach intention
absence→counterevidence
donor PASS→product PASS
rich observation→tracking truth

## RELEASE STATUS
PASS is not release.
CI SUCCESS is not ACTIVE_MATCH evidence.
ACTIVE_MATCH_EVIDENCE_PASS is not PRODUCTION_RELEASE.
MERGED is not PRODUCTION_RELEASE.
Runtime evidence is not production release.

Release vocabulary:
```text
DISCOVERY_PASS_PLAN_ONLY
POLICY_CORRECTION_PASS
SPEC_ONLY
SPEC_CORRECTION_ACCEPTED
SMOKE_PASS
REVIEW_REQUIRED
FAIL_CLOSED
WAITING_OPERATOR_SELECTION
RELEASE_CANDIDATE_NOT_PRODUCTION_BOUND
ACTIVE_MATCH_EVIDENCE_PASS
PRODUCTION_RELEASE
```

## CURRENT DEVELOPMENT DIRECTION
First migrate genuine executable `event-only` ceilings into construct-specific observation-layer admission. Do not waste effort renaming historical filenames or weakening valid tracking/video claim guards.

Priority re-audit after the observation-model migration:
1. temporal dynamics;
2. spatial progression;
3. relational reconstruction;
4. visible opponent-response candidates;
5. player-process participation;
6. process-state dynamics;
7. State Transition Dynamics;
8. Match ECG / Attention Radar;
9. recurrence/change/counterevidence integration;
10. safe analyst finding projection.

Every new work item must answer:
“Mevcut evidence spine'ın hangi gerçek boşluğunu kapatıyor ve analiste hangi yeni savunulabilir bilgiyi kazandırıyor?”

If there is no clear answer: `IDEA_POOL_ONLY / LATER / REJECT`.

## DEFAULT LOCKS
```text
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```
