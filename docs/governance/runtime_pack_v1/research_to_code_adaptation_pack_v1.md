# HPFA Research-to-Code Adaptation Pack V1

Date: 2026-06-23
Status: SPEC_BACKLOG

## Purpose

This pack maps donor repositories, open-source tools, academic methods, Drive/Dropbox libraries and runtime evidence into HPFA product candidates.

It answers:

```text
which idea can be coded?
which idea is donor only?
which idea is claim-risk high?
which idea needs tracking/360/video and must be blocked?
which idea can enter hpfa product repo after ACTIVE_MATCH proof?
```

## Non-Release Statement

This is not a release decision.

```text
PASS != RELEASE
SPEC_BACKLOG != executable module
DONOR_SUPPORT != ACTIVE_MATCH truth
```

## Runtime Truth

Only ACTIVE_MATCH runtime can provide product evidence:

```text
runtime/active_single_match/current
```

Donor repositories, Drive, Dropbox, academic papers and archives are reference/donor sources only.

## Source Role Registry Alignment

This pack must use only registered source roles from:

```text
docs/governance/runtime_pack_v1/source_role_registry.json
```

Registered roles used here:

```text
GITHUB_PRODUCT_REPO
GITHUB_DONOR_REPO
DRIVE_GOVERNANCE
DRIVE_DONOR_LIBRARY
DROPBOX_ARCHIVE
DROPBOX_DONOR_LIBRARY
SIDER_ACADEMIC_BACKING
ACTIVE_MATCH_RUNTIME_AUTHORITY
TERMUX_RUNTIME_EVIDENCE
```

Unregistered aliases such as `GOVERNANCE_DONOR`, `PRIVATE_DONOR_SUPPORT` and `ACADEMIC_SUPPORT` must not be used as source-role values.

## Repository Role Map

| Source | Registered source role | Product use |
|---|---|---|
| Hikmetpinarbas/hpfa | GITHUB_PRODUCT_REPO | executable product modules |
| Hikmetpinarbas/HP-Motor | GITHUB_DONOR_REPO | ingest, mapping, phase, possession, sequence, metric primitive donor |
| Hikmetpinarbas/HP-Engine | GITHUB_DONOR_REPO | registry, claim, metric fusion, pattern donor |
| Hikmetpinarbas/HP-PROJELERI | GITHUB_DONOR_REPO | governance, schema, gate policy, conflict, verification donor |
| HP-Motor-main | GITHUB_DONOR_REPO | private duplicate/support donor; not product truth |
| Google Drive governance material | DRIVE_GOVERNANCE | governance and source authority support |
| Google Drive donor library | DRIVE_DONOR_LIBRARY | donor/library support |
| Dropbox archive material | DROPBOX_ARCHIVE | historical/archive comparison |
| Dropbox donor library | DROPBOX_DONOR_LIBRARY | method archive and donor quarantine |
| Sider Scholar / Scholar Gateway / Consensus | SIDER_ACADEMIC_BACKING | paper-to-node risk evidence and academic method support |

## Donor Transfer Rule

```text
ADAPT_NOT_COPY
```

Required transfer pipeline:

```text
source role -> target module -> claim risk -> contract -> tests -> ACTIVE_MATCH run -> output evidence -> analyst evidence -> release status
```

## HPFA Product Repo Reality Audit Candidate

Target file:

```text
hpfa_product_reality_audit_v1.json
```

Candidate checks:

```json
{
  "adapter_layer_exists": true,
  "mapping_contract_exists": true,
  "quarantine_exists": true,
  "action_registry_exists": true,
  "possession_logic_exists": true,
  "quality_gate_output_exists": true,
  "match_identity_leak_risk": "review_required",
  "active_match_ready": "requires_runtime_proof"
}
```

## Donor-to-Node Map

| Donor idea | Source | Source role | HPFA target node | Claim risk | Decision |
|---|---|---|---|---|---|
| provider reader abstraction | HP-Motor, kloppy | GITHUB_DONOR_REPO / SIDER_ACADEMIC_BACKING | provider_adapter_registry_lite_v1 | low | adapt concept |
| raw surface table model | HP-Motor, HP-PROJELERI hp_cdl | GITHUB_DONOR_REPO | surface_table_reader_lite_v1 | low | adapt concept |
| source mapping / extras preservation | HP-Motor canonicalize, HP-PROJELERI canonicalize | GITHUB_DONOR_REPO | source_mapping_contract_v1 | low | adapt concept |
| gate policy G01-G14 | HP-PROJELERI | GITHUB_DONOR_REPO | data_quality_gate_lite_v1 / claim_gate_lite_v1 | medium | adapt gate families |
| conflict registry | HP-PROJELERI conflicts | GITHUB_DONOR_REPO | source_conflict_registry_lite_v1 | low-medium | high priority adapt |
| verification report format | HP-PROJELERI | GITHUB_DONOR_REPO | runtime_verification_report_lite_v1 | low | adapt format |
| action language | socceraction / SPADL idea | SIDER_ACADEMIC_BACKING | action_language_lite_v1 | medium | adapt concept only |
| VAEP / xT valuation | socceraction, papers | SIDER_ACADEMIC_BACKING | action_value_cost_fusion_lite_v1 | high | block value truth; reference only until claim gate |
| event state transition model | VERSA-style literature | SIDER_ACADEMIC_BACKING | event_state_transition_verifier_lite_v1 | medium | high priority adapt |
| process mining trace variants | pm4py / football process mining | SIDER_ACADEMIC_BACKING | process_mining_surface_lite_v1 | medium-high | adapt with claim gate |
| event-to-sequence confidence | sequence annotation literature | SIDER_ACADEMIC_BACKING | selected_sequence_annotation_confidence_v1 | medium | adapt |
| context modelling | context literature / HP-Motor context fields | SIDER_ACADEMIC_BACKING / GITHUB_DONOR_REPO | minimum_viable_context_v1 | medium | adapt |
| visual pitch maps | mplsoccer / HPFA graphics pack | SIDER_ACADEMIC_BACKING / GITHUB_PRODUCT_REPO | visual_surface_lite_v1 | medium | output layer only |
| method library risk routing | HP-PROJELERI hpfa_library, academic corpus | GITHUB_DONOR_REPO / SIDER_ACADEMIC_BACKING | academic_literature_risk_router_v1 | medium | adapt |
| claim registries | HP-Engine registry files | GITHUB_DONOR_REPO | observation_registry_lite_v1 / mechanism_registry_lite_v1 / claim_thresholds_lite_v1 | high | registry only; no runtime claim engine yet |
| metric fusion fixtures | HP-Engine metric merge lab | GITHUB_DONOR_REPO | action_value_cost_fusion_lite_v1 | high | candidate-only |

## Open-Source Tool Map

| Tool | Usable idea | Source role | HPFA boundary |
|---|---|---|---|
| socceraction | SPADL/action language discipline | SIDER_ACADEMIC_BACKING | no VAEP truth, no value truth |
| kloppy | provider adapter architecture | SIDER_ACADEMIC_BACKING | no external API runtime truth |
| mplsoccer | pitch/shot/pass/heat visual conventions | SIDER_ACADEMIC_BACKING | visual concentration != dominance |
| statsbombpy | event loader/API separation discipline | SIDER_ACADEMIC_BACKING | reference only; ACTIVE_MATCH local files only |
| pm4py | process mining trace/variant approach | SIDER_ACADEMIC_BACKING | frequent trace != tactical plan |

## Academic Method Map

| Literature family | HPFA target | Source role | Safe use | Blocked claim |
|---|---|---|---|---|
| verified event format / state transitions | event_state_transition_verifier_lite_v1 | SIDER_ACADEMIC_BACKING | sequence validity candidate | complete event truth |
| process mining in football | process_mining_surface_lite_v1 | SIDER_ACADEMIC_BACKING | trace variant candidate | tactical plan / superiority |
| atomic events to sequences | selected_sequence_annotation_confidence_v1 | SIDER_ACADEMIC_BACKING | sequence confidence gate | clean sequence truth without gate |
| context in match analysis | minimum_viable_context_v1 | SIDER_ACADEMIC_BACKING | context enrichment | context = causality |
| physical tracking + event context | raw_fitness_value_extract_lite_v1 / action_value_cost_fusion_lite_v1 | SIDER_ACADEMIC_BACKING | support/fusion candidate | fatigue/performance truth |
| xT / VAEP / EPV | action value research reference | SIDER_ACADEMIC_BACKING | architecture donor | validated value truth |

## Coding Candidate Backlog

### P0B Research-to-Code Adaptation Pack V1

Outputs:

```text
repo_donor_map.tsv
open_source_tool_map.tsv
literature_to_node_map.tsv
coding_candidate_backlog.tsv
claim_risk_router.json
event_only_compatibility_matrix.tsv
implementation_order.md
```

Status:

```text
SPEC_BACKLOG
```

### Source Mapping Contract V1

Purpose:

```text
map source fields to HPFA canonical-lite fields, preserve unmapped columns, fail closed on missing required fields
```

Tests:

```text
test_unmapped_columns_preserved
test_required_columns_fail_closed
test_no_sample_match_identity_leak
```

### Event State Transition Verifier Lite V1

Purpose:

```text
check whether event-family sequence transitions are valid candidates
```

States:

```text
dead_ball
in_play
possession_active
possession_reset
shot_terminal
turnover
restart
unknown
```

Blocked:

```text
complete event truth
clean possession truth
validated sequence truth
```

### Source Conflict Registry Lite V1

Conflict families:

```text
schema_divergence
data_integrity
duplicate_data
event_count_discrepancy
action_taxonomy
time_base
coordinate_boundary
aggregate_conflict
```

### Metric Primitive Lite V1

Primitive families:

```text
zone_entry
third_entry
box_entry
terminal_action
turnover
recovery
restart
carry_progression
pass_progression
shot_surface
gk_surface
```

### Process Mining Surface Lite V1

Trace schema:

```json
{
  "trace_id": "...",
  "team": "...",
  "sequence_id": "...",
  "action_family_chain": ["recovery", "pass", "carry", "pass", "shot"],
  "variant_id": "...",
  "support_count": 0,
  "variant_frequency_band": "rare|common|frequent",
  "unusual_candidate": false,
  "claim_allowed": false
}
```

### Raw Fitness Value Extract Lite V1

Purpose:

```text
extract actual team/player physical values from fitness/report surfaces, not just metric-family extraction counts
```

Candidate outputs:

```text
raw_fitness_team_values_v1.tsv
raw_fitness_player_values_v1.tsv
raw_fitness_value_audit_v1.json
```

Candidate fields:

```text
team
player
period
context
metric
value
unit
speed_band
source_file
source_page
claim_role
```

Blocked:

```text
fatigue truth
fitness caused result
performance superiority truth
```

### Action Value Cost Fusion Lite V1

Requires all upstream readiness inputs below:

```text
primary_event_surface_gate_lite_v1.json
physical_cost_surface_audit_v1.json
event_identity_resolution_gate_lite_v1.json
metric_family_registry_lite_v1.json
raw_fitness_value_extract_lite_v1
team_binding_lite_v1.json
claim router
```

Fail-closed readiness rule:

```text
If primary_event_surface_gate_lite_v1.decision == UNRESOLVED_REVIEW_REQUIRED,
Action Value Cost Fusion must remain WAIT_PRIMARY_SURFACE_REVIEW and cannot be production-bound.
```

Physical-cost readiness rule:

```text
physical_cost_surface_audit_v1.json must show PHYSICAL_COST_SURFACE evidence.
Report-only metric surfaces cannot satisfy physical-cost readiness.
```

Identity readiness rule:

```text
event_identity_resolution_gate_lite_v1.json must be present.
If duplicate risk remains, fusion output must remain candidate-only and metric_count_allowed=false.
```

Candidate metrics:

```text
attack_distance_per_final_third_row
attack_distance_per_shot_row
attack_distance_per_pass_row
high_speed_distance_per_carry_dribble_row
sprint_distance_per_shot_row
defence_distance_per_duel_pressure_row
```

Output remains candidate-only.

Blocked:

```text
efficiency truth
fatigue truth
fitness caused result
tactical causality
metric truth without claim routing
```

## Event-Only Compatibility Matrix

| Method | Event-only compatible? | Decision |
|---|---:|---|
| action family volume | yes | allowed |
| zone/channel distribution | yes if coordinates present | allowed with coordinate gate |
| source mapping | yes | allowed |
| state transition verification | yes | allowed as integrity check |
| process trace variant | yes after sequence candidate | gated |
| raw fitness values | no, support surface | support only |
| fitness-event fusion | mixed | candidate only |
| tracking pitch control | no | blocked/reference only |
| off-ball impact | no without tracking/360 | blocked/reference only |
| formation classification | no without tracking | blocked/reference only |
| VAEP/xT truth | not in current runtime | blocked until claim/value gates |

## Implementation Order

Recommended order:

```text
P0B Research-to-Code Adaptation Pack V1
P1 Source Mapping Contract V1
P2 Event State Transition Verifier Lite V1
P3 Event Definition Confidence Gate V1
P4 Minimum Viable Context V1
P5 Metric Primitive Lite V1
P6 Possession / Sequence Candidate Lite V1
P7 Process Mining Surface Lite V1
P8 Raw Fitness Value Extract Lite V1
P9 Action Value Cost Fusion Lite V1
P10 Claim Eligibility Gate Lite V1
P11 Analyst Report / Visual Surface Lite V1
```

## Guardrails

- use only registered source roles from `source_role_registry.json`
- no donor repo as runtime truth
- no match identity hardcode
- no coach intention
- no dominance language
- no off-ball truth without tracking/360
- no pitch control truth
- no fatigue truth
- no efficiency truth without claim routing
- outputs must remain flat under `/sdcard/Download/HPFA` or `/storage/emulated/0/Download/HPFA`

## Acceptance Criteria

This pack is accepted when:

```text
file exists in hpfa product repo
all source roles match source_role_registry.json
donor roles are explicit
claim risks are explicit
implementation order is explicit
next coding candidates are explicit
Action Value Cost readiness gates preserve existing contract requirements
no runtime truth is assigned to donor material
```

## Current Status

```text
SPEC_BACKLOG
RESEARCH_TO_CODE_MAP_WRITTEN
PRODUCTION_RELEASE_NOT_GRANTED
```
