# HPFA Revolutionary Donor Transfer Pack V1

Date: 2026-06-23
Status: SPEC_BACKLOG

## Purpose

This pack selects the highest-leverage donor pieces from HP-Motor, HP-Engine, HP-PROJELERI, open-source football/data tooling, academic backing and HPFA research documents.

It is not a code release. It is a ranked transfer plan for what should enter `hpfa` next.

## Core Rule

```text
ADAPT_NOT_COPY
```

No donor repository, paper, PDF, Drive/Dropbox note or open-source project is runtime truth.

## Product Boundary

```text
hpfa = product repo
HP-Motor = ingest / phase / possession / sequence / metric primitive donor
HP-Engine = registry / claim / pattern / metric fusion donor
HP-PROJELERI = governance / schema / gate / conflict / verification donor
Academic sources = SIDER_ACADEMIC_BACKING
Drive/Dropbox = REFERENCE_ONLY / DONOR_LIBRARY
ACTIVE_MATCH runtime = only runtime evidence
```

## Transfer Scoring

Each candidate is scored on five axes:

```text
A. Product leverage
B. ACTIVE_MATCH feasibility
C. Claim-safety compatibility
D. Donor readiness
E. Analyst value
```

Priority bands:

```text
R1 = immediate spine hardener
R2 = analyst-intelligence amplifier
R3 = future support / claim-gated
BLOCK = not event-only or not safe yet
```

## R1 Immediate Spine Hardeners

### 1. Source Mapping Contract V1

Donors:

```text
HP-Motor canonicalize / provider registry
HP-PROJELERI hp_cdl canonicalize/readers
hpfa adapter/mapping/quarantine traces
kloppy provider-adapter concept
```

Why revolutionary:

```text
This turns arbitrary CSV/XML/XLSX surfaces into explicit mapped/unmapped contracts before any football interpretation.
```

Target:

```text
hpfa/modules/core/source_mapping_contract_lite/
```

Outputs:

```text
source_mapping_contract_v1.json
source_mapping_audit_v1.json
source_mapping_audit_v1.txt
```

Acceptance tests:

```text
test_unmapped_columns_preserved
test_required_columns_fail_closed
test_row_lineage_preserved
test_no_sample_match_identity_leak
test_nested_phone_output_directory_rejected
```

Claim boundary:

```text
mapping candidate only
canonical_event_count remains UNKNOWN
```

Priority:

```text
R1
```

### 2. Source Conflict Registry Lite V1

Donors:

```text
HP-PROJELERI conflicts.json
HPFA surface-count correction doctrine
ACTIVE_MATCH multi-surface evidence
```

Why revolutionary:

```text
It lets HPFA reason about source contradictions instead of hiding them in reports.
```

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

Outputs:

```text
source_conflict_registry_lite_v1.json
source_conflict_registry_lite_v1.txt
```

Claim boundary:

```text
conflict evidence only
surface rows != event count
conflict != tactical conclusion
```

Priority:

```text
R1
```

### 3. Event State Transition Verifier Lite V1

Donors:

```text
VERSA-style verified event format literature
HP-Motor sequence/possession concepts
HP-PROJELERI gate policy
HPFA Event-Only Signal Engine packet
```

Why revolutionary:

```text
HPFA stops treating event order as automatically valid and starts verifying whether event-family transitions are plausible candidates.
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

Outputs:

```text
event_state_transition_verifier_lite_v1.json
event_state_transition_verifier_lite_v1.txt
```

Blocked:

```text
complete event truth
clean possession truth
validated sequence truth
player error truth
referee error truth
```

Priority:

```text
R1
```

### 4. Raw Fitness Value Extract Lite V1

Donors:

```text
physical_cost_surface_doctrine_v1
HPFA Deep Research Blueprint
existing physical_cost_surface_audit_v1
reference_document_pages_v1.jsonl
```

Why revolutionary:

```text
It upgrades fitness from metric-family extraction counts to actual team/player physical values with source provenance.
```

Outputs:

```text
raw_fitness_team_values_v1.tsv
raw_fitness_player_values_v1.tsv
raw_fitness_value_audit_v1.json
raw_fitness_value_audit_v1.txt
```

Fields:

```text
entity_type
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
physical value as event count
```

Priority:

```text
R1
```

### 5. Minimum Viable Context V1

Donors:

```text
context-in-match-analysis literature
HP-Motor context fields
HPFA postmatch architecture docs
```

Why revolutionary:

```text
It blocks analyst sentences when period/team/zone/score-state/source confidence are unavailable.
```

Output shape:

```json
{
  "row_ref": "...",
  "period": "...",
  "minute": "...",
  "team": "...",
  "score_state": "unknown|level|leading|trailing",
  "zone": "...",
  "previous_action_family": "...",
  "next_action_window": "...",
  "source_confidence": "high|medium|low",
  "claim_allowed": false
}
```

Priority:

```text
R1
```

## R2 Analyst-Intelligence Amplifiers

### 6. Event-Only Signal Engine Lite V1

Donors:

```text
HPFA_EVENTONLY_SIGNAL_ENGINE_KODLANABILIR_TASARIM_PAKETI
HPFA-DISC-MAP-001
HPFA Signal-Processing Layer
```

Modules:

```text
event_window_builder
event_time_series_features
temporal_pair_candidate_engine
passing_motif_engine
event_network_builder
network_metrics
autocorrelation_profile
classifier_candidate
validation_harness
```

Allowed features:

```text
action_family_count
action_family_share
windowed entropy
tempo coefficient of variation
sequence density candidate
temporal pair candidate count
passing motif count
event network degree/density/reciprocity
lag autocorrelation
```

Forbidden inputs:

```text
tracking
video
gps
speed
acceleration
distance_covered
physical_load
fatigue
pitch_control
body_orientation
off_ball_shape
```

Allowed labels:

```text
sterile_circulation_candidate
chaos_noise_candidate
transition_threat_candidate
controlled_progression_candidate
build_up_fragility_candidate
low_value_possession_candidate
```

Language status:

```text
NOT_REPORT_READY_WITHOUT_CLAIM_GATE
```

Priority:

```text
R2
```

### 7. Process Mining Surface Lite V1

Donors:

```text
pm4py concept
football process mining literature
HP-Motor sequences
HP-Engine sequence fixtures
```

Why revolutionary:

```text
Possession chains become trace variants, not loose narrative examples.
```

Required upstream readiness:

```text
possession_boundary_lite_v1 OR sequence_candidate_lite_v1 must exist before production-bound process variants.
If those gates do not exist, process_mining_surface_lite_v1 must emit sequence_id="UNKNOWN", sequence_source_status="WAIT_SEQUENCE_CANDIDATE", and production_bound=false.
```

Output shape before sequence readiness:

```json
{
  "trace_id": "...",
  "team": "...",
  "sequence_id": "UNKNOWN",
  "sequence_source_status": "WAIT_SEQUENCE_CANDIDATE",
  "action_family_chain_candidate": ["recovery", "pass", "carry", "pass", "shot"],
  "variant_id": "candidate_only",
  "support_count": 0,
  "variant_frequency_band": "unknown|rare|common|frequent",
  "unusual_candidate": false,
  "production_bound": false,
  "claim_allowed": false
}
```

Output shape after sequence readiness:

```json
{
  "trace_id": "...",
  "team": "...",
  "sequence_id": "...",
  "sequence_source_status": "SEQUENCE_CANDIDATE_AVAILABLE",
  "action_family_chain": ["recovery", "pass", "carry", "pass", "shot"],
  "variant_id": "...",
  "support_count": 0,
  "variant_frequency_band": "rare|common|frequent",
  "unusual_candidate": false,
  "production_bound": false,
  "claim_allowed": false
}
```

Blocked:

```text
rare trace = bad decision
frequent trace = tactical plan
variant = superiority
sequence_id without upstream sequence evidence
```

Priority:

```text
R2_AFTER_SEQUENCE_READINESS
```

### 8. Metric Primitive Lite V1

Donors:

```text
Drive Event-Only Metric Primitive
HP-Motor metric registry
socceraction action-language discipline
```

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

Boundary:

```text
primitive evidence only
no score/value truth
```

Priority:

```text
R2
```

### 9. Event Geometry Proxy Lite V1

Donors:

```text
HPFA Mathematics / Physics / Geometry formula pack
HPFA-DISC-MAP-001
socceraction/SPADL geometry discipline
```

Allowed:

```text
Euclidean distance
pass/carry vector
angle
progression delta
zone entry
channel movement
```

Blocked:

```text
pitch control
free-man truth
off-ball shape
formation truth
space control truth
```

Priority:

```text
R2
```

### 10. Visual Surface Lite V1

Donors:

```text
mplsoccer concept
HPFA graphics pack
postmatch report architecture
```

Outputs:

```text
active_match_zone_surface.png
active_match_action_family_surface.png
active_match_shot_surface.png
active_match_turnover_surface.png
active_match_recovery_surface.png
```

Guardrails:

```text
heatmap != dominance
shot map != finishing quality truth
average position != formation truth
```

Priority:

```text
R2
```

## R3 Future / Claim-Gated

### 11. Observation / Mechanism / Claim Registry Lite

Donors:

```text
HP-Engine claim registry
HP-Engine mechanism registry
HP-Engine observation registry
```

Allowed now:

```text
registry format only
claim_allowed=false
requires_claim_gate=true
```

Blocked now:

```text
live claim runtime
diagnosis engine
tactical intention
causal mechanism truth
```

Priority:

```text
R3
```

### 12. Tracking Method Risk Router V1

Donors:

```text
tracking systematic reviews
SkillCorner / Opta Vision / tracking-provider methods
HPFA discipline map
```

Purpose:

```text
route tracking-heavy concepts into reference-only or future-support status
```

Blocked until explicit tracking data:

```text
pitch control
off-ball run truth
pressure intensity truth
formation classification
body orientation
space control
```

Priority:

```text
R3
```

## BLOCK List

Do not implement as product truth from current ACTIVE_MATCH event-only runtime:

```text
pitch_control_truth
body_orientation_truth
off_ball_shape_truth
coach_intention
fatigue_truth
performance_superiority_truth
VAEP_truth
xT_truth
formation_truth
space_control_truth
```

## Recommended Execution Order

```text
1. Source Mapping Contract V1
2. Source Conflict Registry Lite V1
3. Event State Transition Verifier Lite V1
4. Raw Fitness Value Extract Lite V1
5. Minimum Viable Context V1
6. Metric Primitive Lite V1
7. Event Geometry Proxy Lite V1
8. Event-Only Signal Engine Lite V1
9. Possession / Sequence Candidate Lite V1
10. Process Mining Surface Lite V1 after sequence readiness
11. Visual Surface Lite V1
12. Observation / Mechanism / Claim Registry Lite
13. Action Value Cost Fusion Lite V1 after readiness gates
```

## Why Process Mining Is Not Before Sequence Readiness

Process Mining Surface Lite V1 must wait for at least a sequence or possession candidate producer.

If no upstream sequence candidate exists, process mining remains:

```text
WAIT_SEQUENCE_CANDIDATE
```

Allowed interim output:

```text
action_family_chain_candidate only
sequence_id=UNKNOWN
production_bound=false
claim_allowed=false
```

## Why Action Value Cost Fusion Is Not First

Action Value Cost Fusion must wait for:

```text
primary_event_surface_gate_lite_v1.json
event_identity_resolution_gate_lite_v1.json
physical_cost_surface_audit_v1.json
raw_fitness_value_extract_lite_v1
metric_family_registry_lite_v1.json
team_binding_lite_v1.json
claim router
```

If primary surface remains unresolved, fusion remains:

```text
WAIT_PRIMARY_SURFACE_REVIEW
```

## Allowed Flat Phone Output Roots

Executable transfer evidence may write only directly under one of these flat roots:

```text
/sdcard/Download/HPFA
/storage/emulated/0/Download/HPFA
```

Nested output directories remain invalid and must be rejected with:

```text
nested_phone_output_directory_rejected
```

## ACTIVE_MATCH Proof Requirement

Every executable transfer must produce two proof layers:

```text
engineering evidence:
- module ran
- tests passed
- outputs written flat to one allowed phone root: /sdcard/Download/HPFA or /storage/emulated/0/Download/HPFA

analyst evidence:
- what visible surface changed
- what interpretation is safe
- what remains blocked
```

## Status

```text
SPEC_BACKLOG
REVOLUTIONARY_DONOR_TRANSFER_MAP_WRITTEN
PRODUCTION_RELEASE_NOT_GRANTED
```
