# Triplex Source Alignment Guard V1 — Donor-to-Current-Main Field Delta Audit

Status: `DISCOVERY_PASS_PLAN_ONLY`

Repository authority: `Hikmetpinarbas/hpfa`

Main SHA audited: `6cc540399d56e52c021a3a02e3f72b416d393184`

Runtime authority: `runtime/active_single_match/current`

Canonical event count: `UNKNOWN`

Policy: `ADAPT_NOT_COPY`

## Scope

This audit compares the Dropbox donor field contract for `hpfa_triplex_source_alignment_guard_v1` against three current-main prerequisite surfaces only:

- `hpfa/modules/core/canonical_ingest_surface_manifest/src/surface_manifest.py`
- `hpfa/modules/core/source_mapping_contract_lite/src/source_mapping_contract.py`
- `docs/governance/runtime_pack_v1/source_role_registry.json`

The donor pack is `SPEC_CONTRACT` evidence with a closed claim gate. It is not product code, current-main contract evidence, runtime evidence or release evidence.

## Coverage vocabulary

- `PRESENT`: the required field-level behavior is explicitly implemented in an inspected current-main executable producer.
- `PARTIAL`: an adjacent field or prerequisite exists, but the donor-required adjudication is not implemented.
- `GAP`: no equivalent field-level behavior was resolved in the inspected current-main surfaces.
- `GOVERNANCE_ONLY`: policy exists, but no inspected executable producer consumes it for the required decision.

## Field-by-field delta

| Donor field | Donor requirement / fail action | Current-main evidence | Coverage | Delta |
|---|---|---|---|---|
| `match_id` | Conditional all-surface match binding; block conflicting files | No explicit match identity field or cross-file conflict adjudication in the inspected producers | `GAP` | Add explicit match-binding input and fail-closed conflict decision; do not infer identity from filenames alone |
| `period` | Required for CSV/XML event order and context; block sequence fusion | `source_mapping_contract_lite_v1` canonical fields do not include `period` | `GAP` | Add period alias resolution and missing-period fusion block for event-like surfaces |
| `timestamp` | Conditional CSV/XML time-window alignment; downgrade when missing | `timestamp` is a canonical mapping candidate, but no cross-surface agreement or ambiguity decision exists | `PARTIAL` | Reuse canonical mapping; add tolerance/window policy, disagreement state and downgrade route |
| `event_order` | Conditional CSV/XML sequence alignment; downgrade when missing | No explicit canonical field or cross-surface order comparison resolved | `GAP` | Add event-order alias/input contract and mismatch/absence handling without claiming canonical sequence truth |
| `team_or_side` | Required CSV/XML side/team alignment; block when missing | Canonical `team` mapping exists; required event fields currently include only `event_type`, `x`, `y` | `PARTIAL` | Reuse `team`; elevate to Triplex-required alignment input and compare normalized side/team across surfaces |
| `player_id` | Optional identity surface; warn on conflict | Canonical `player` mapping exists, but identity semantics and cross-surface conflict detection are absent | `PARTIAL` | Reuse mapped player candidate; keep optional and emit typed conflict warning rather than identity truth |
| `event_type` | Required canonical action mapping; block unmapped | `event_type` is canonical and required for event-like surfaces; per-source missing-field fail-closed mode exists | `PARTIAL` | Reuse mapping decision; add cross-surface event-family agreement and unmapped fusion block |
| `qualifier` | Optional XML/CSV semantic detail; downgrade unmapped | Unmapped columns are preserved in `extras`; no qualifier contract or semantic comparison exists | `PARTIAL` | Preserve extras behavior; add optional qualifier alias family and downgrade-only disagreement output |
| `possession_id` | Optional sequence grouping; derive or warn | No equivalent field or derivation contract resolved | `GAP` | Add optional input only; derivation must remain separately flagged and cannot create possession truth |
| `sequence_id` | Optional sequence grouping; derive or warn | No equivalent field or derivation contract resolved | `GAP` | Add optional input only; derived values require provenance and cannot establish sequence truth |
| `xlsx_formula_flag` | Required XLSX derived/manual separation; block independent claim if derived | XLSX is classified as `aggregate_support`, but formula/manual origin is not inspected | `GAP` | Add XLSX formula-origin detector or explicit unknown state; block independence claims when derived or unresolved |
| `source_provenance` | Required all-surface dependency detection; downgrade when missing | Source file, format, role and relative path are recorded; upstream origin/lineage is not | `PARTIAL` | Reuse visible source metadata; add upstream-origin identifier, lineage state and dependency comparison |
| `unit` | Required metric fusion precheck; block on missing/conflict | No metric unit contract resolved in inspected producers | `GAP` | Add typed unit input and exact/convertible/conflicting/unknown decision before metric fusion |
| `denominator` | Required rate validity; block metric fusion | No denominator contract resolved | `GAP` | Add denominator identity and compatibility decision; unknown must fail closed for rate fusion |
| `observation_window` | Required comparison validity; block metric fusion | No observation-window alignment contract resolved | `GAP` | Add explicit window/scope input and equality/containment/conflict decision before comparison |

## Cross-cutting prerequisite assessment

### Canonical ingest surface manifest

Reusable:

- source file, relative path, role, format and surface-family inventory;
- event-surface versus aggregate-surface candidate distinction;
- reference-path fail-closed behavior;
- `canonical_event_count=UNKNOWN` preservation.

Not provided:

- source lineage or upstream-origin identity;
- duplicate/dependent-surface adjudication;
- formula/manual XLSX origin;
- cross-surface field agreement;
- fusion claim-capacity decision.

### Source mapping contract lite

Reusable:

- canonical alias mapping for `event_type`, `team`, `player`, `timestamp` and coordinates;
- per-source missing-required-field decisions;
- unmapped-field preservation in `extras`;
- fail-closed mode for missing event-like required fields;
- blocked event, possession, phase, sequence and tactical truth claims.

Not provided:

- donor-required `period`, `event_order`, provenance, unit, denominator or observation-window contracts;
- cross-source comparison and conflict adjudication;
- independence groups;
- derived-source blocking;
- metric-fusion admissibility.

### Source role registry

Reusable as governance:

- source authority families;
- ACTIVE_MATCH runtime authority boundary;
- donor/reference non-authority rules;
- `canonical_event_count=UNKNOWN` rule.

Coverage: `GOVERNANCE_ONLY` for Triplex admission. No inspected executable producer was resolved that consumes the registry to decide source independence, fusion admissibility or claim capacity.

## Minimum HPFA-native adapter boundary

The smallest non-duplicative future adapter should consume existing manifest and mapping outputs rather than recreate them. Its contract should be limited to:

1. `surface_identity_inputs`: source file, format, role, surface family and upstream-origin identifier;
2. `event_alignment_inputs`: match binding, period, timestamp, event order, team/side, player candidate, event type and optional qualifier;
3. `derivation_inputs`: XLSX formula/manual/unknown state and lineage/dependency markers;
4. `metric_alignment_inputs`: unit, denominator and observation window;
5. typed decisions: `ALLOW_ALIGNMENT_REVIEW`, `DOWNGRADE_DEPENDENT`, `BLOCK_EVENT_FUSION`, `BLOCK_METRIC_FUSION`, `BLOCK_INDEPENDENCE_CLAIM`;
6. immutable claim boundaries: canonical event count, possession truth, sequence truth, tactical truth and production release remain blocked.

This audit does not authorize implementation. Before implementation, the adapter contract must define deterministic conflict precedence, missing-value behavior, empty-string handling, legacy aliases and negative tests.

## Classification after delta audit

```text
DIRECTIVE CAPABILITY = Triplex Source Alignment Guard V1
CURRENT-MAIN PRIMARY STATUS = NOT_FOUND
CURRENT-MAIN RUNTIME STATUS = NOT_RUNTIME_PROVEN
ADJACENT PREREQUISITES = PARTIAL
DONOR EQUIVALENCE = SPEC_CONTRACT
FIELD DELTA AUDIT = COMPLETE
ACTIVE_MATCH_PROVEN = NO
PRODUCTION_RELEASE = FALSE
```

## Engineering evidence

- donor field contract inspected: yes
- current-main manifest producer inspected: yes
- current-main source-mapping producer inspected: yes
- current-main source-role governance inspected: yes
- field-by-field delta recorded: yes
- donor code copied: no
- product implementation changed: no
- tests executed: no
- ACTIVE_MATCH execution: no
- merge authorized: no

## Analyst evidence

No match was analyzed and no football-performance claim was generated.

Potential product value only: the delta identifies the exact gates needed to prevent dependent CSV/XML/XLSX exports, incompatible rate denominators or mismatched observation windows from being treated as independent corroborating evidence.

## Claim boundary

```text
canonical_event_count = UNKNOWN
source independence truth = false
canonical event identity truth = false
fusion admissibility truth = false
analytical claim capacity = not established
production release = false
```

## Smallest next verification

Search current main for differently named reusable producers covering these four unresolved groups before selecting an adapter contract:

1. upstream lineage / dependency identity;
2. XLSX formula or derived-surface detection;
3. unit and denominator compatibility;
4. observation-window or scope alignment.

If no executable equivalents are resolved, record exact `NOT_FOUND` evidence and define only the minimal fail-closed adapter contract plus deterministic negative tests in a separate implementation PR.
