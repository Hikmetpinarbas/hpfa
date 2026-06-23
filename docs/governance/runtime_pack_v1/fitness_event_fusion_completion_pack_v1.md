# HPFA Fitness Event Fusion Completion Pack V1

Date: 2026-06-23
Status: SPEC_BACKLOG

## Purpose

This pack converts user-provided fitness/event fusion research into HPFA product gaps, modules, gates and implementation order.

This is not runtime truth and not a release.

## Source Inputs

```text
HPFA Davranış Füzyon Haritası: Futbol Oyun Dinamiklerini Fiziksel Yük Verileriyle Açıklama
Futbolda Veri Füzyonu Araştırması: Kinematik ve Olay Verilerinin Hibrit Modellemesi
Copilot fitness integration response
HPFA Action Value Cost Fusion research notes
Event-Only Fatigue / Decrement research notes
```

Source role:

```text
REFERENCE_ONLY_RESEARCH_DONOR
```

Transfer rule:

```text
ADAPT_NOT_COPY
```

## Central HPFA Adaptation

Research language may contain strong claims. HPFA must downgrade them into claim-safe layers.

```text
fitness value != event truth
physical cost != tactical truth
fatigue proxy != fatigue truth
off-ball inference != off-ball truth
performance decrement candidate != causal proof
```

## Behaviour Evidence Ladder

The research material defines a four-layer behaviour classification. HPFA adapts this into a report and claim gate ladder.

```text
OBSERVED_BEHAVIOUR
= directly visible from event/surface evidence

SUPPORTED_BEHAVIOUR
= event/surface evidence plus physical-cost support in the same window/direction

ASSUMED_BEHAVIOUR
= physical/report signal without event confirmation; hypothesis only

UNVERIFIED_BEHAVIOUR
= neither event nor fitness evidence can support it; blocked claim
```

Output language examples:

```text
observed: event-row evidence shows high recovery volume in this window.
supported: recovery volume is accompanied by increased acceleration/deceleration cost evidence.
assumed: high physical load without event support may indicate hidden movement demand; requires validation.
unverified: coach intention, tactical plan, off-ball structure and fatigue truth are blocked.
```

Target module:

```text
behaviour_fusion_taxonomy_lite_v1
claim_safe_report_grammar_gate_v1
```

## Fusion Axes Extracted From Research

### 1. Pressure / Duel / Recovery Cost Axis

Event-side signals:

```text
press/challenge candidate
recovery
interception
tackle
duel_pressure
ball_loss_reaction_window
```

Physical-side support signals:

```text
peak acceleration
peak deceleration
metabolic power
player load
repeated high-intensity bursts
```

HPFA safe output:

```text
pressure/recovery activity is physically supported by acceleration/deceleration cost evidence.
```

Blocked:

```text
team pressed by design
coach planned high press
fitness proves defensive structure
```

### 2. Tempo / Rhythm Cost Axis

Event-side signals:

```text
action-family volume per time window
pass/carry/shot density
inter-event interval
rhythm-state candidate
windowed entropy
```

Physical-side support signals:

```text
sprint distance
sprint count
high-intensity distance
heart-rate volatility if available
metabolic power variability
```

HPFA safe output:

```text
rhythm increase candidate is supported by higher physical intensity in the same window.
```

Blocked:

```text
tempo was intentionally manipulated
players were tired as fact
team dominated rhythm
```

### 3. Transition Density Cost Axis

Event-side signals:

```text
recovery -> pass/carry/shot chains
loss -> recovery windows
terminal action after recovery
transition surge candidate
```

Physical-side support signals:

```text
peak sprint distance
acceleration load
metabolic power peaks
repeated sprint metrics
```

HPFA safe output:

```text
transition-surge candidate is physically supported by sprint/acceleration cost evidence.
```

Blocked:

```text
transition strategy truth
successful transition superiority
causal goal claim
```

### 4. Repeated Attack / Terminal Pressure Cost Axis

Event-side signals:

```text
final-third action volume
box-entry candidate
shot volume
terminal-pressure candidate
repeated attack windows
```

Physical-side support signals:

```text
same-window high-intensity load
metabolic power cost
speed reduction candidate
physical cost per terminal action
```

HPFA safe output:

```text
repeated terminal-pressure surface is accompanied by increased physical-cost support.
```

Blocked:

```text
fatigue caused shot decline
technical quality declined because of load
```

### 5. Loss Reaction / Counter-Action Cost Axis

Event-side signals:

```text
ball_loss
recovery within N seconds
challenge after loss
foul/challenge pressure sequence
```

Physical-side support signals:

```text
acceleration burst after loss
peak deceleration
short-window player load
reaction-time proxy if available
```

HPFA safe output:

```text
loss-reaction candidate is supported by acceleration/deceleration evidence after the loss window.
```

Blocked:

```text
counterpressing plan truth
defensive organization truth
player effort truth
```

### 6. Movement Economy / Block Movement Cost Axis

Event-side signals:

```text
zone-to-zone action concentration
carry progression
pass progression
role/position group action distribution
```

Physical-side support signals:

```text
distance per action
player load per distance
metabolic power per distance
high-intensity cost per progressive action
```

HPFA safe output:

```text
movement economy candidate: similar action volume appears with lower physical cost per unit distance/action.
```

Blocked:

```text
off-ball movement truth
formation truth
space occupation truth
```

## Data Fusion Methodology Gates

### Gate 1: Source Authority Gate

Input must declare:

```text
source_file
source_page_or_row
source_surface_type
metric_family
source_role
runtime_truth=false for support documents
```

Required before:

```text
Raw Fitness Value Extract Lite V1
Physical Event Window Join Lite V1
Action Cost Candidate Lite V1
```

### Gate 2: Time Alignment Gate

The research repeatedly identifies temporal synchronization as a critical fusion prerequisite.

HPFA adaptation:

```text
if precise event-fitness timestamps unavailable:
  join_status=WINDOW_LEVEL_ONLY
  exact_action_cost_allowed=false
else:
  join_status=TIMESTAMP_ALIGNED_CANDIDATE
```

Blocked without alignment:

```text
exact event physical cost
frame-level action cost
reaction-time truth
```

### Gate 3: Sensor / Report Reliability Gate

For current HPFA physical surfaces, many values come from reports/PDFs, not raw GPS feeds.

HPFA adaptation:

```text
raw_sensor_value
report_extracted_value
aggregate_report_value
unknown_value
```

Each extracted metric must carry:

```text
source_confidence
unit_confidence
entity_binding_confidence
claim_role
```

### Gate 4: Context Normalization Gate

Research highlights that raw physical values require context.

Normalize by:

```text
minutes played
effective playing time if available
period/window
role/position group
team context
individual speed threshold if available
```

Blocked without context:

```text
cross-player superiority
fitness efficiency truth
injury risk truth
```

### Gate 5: Multicollinearity / Model Risk Gate

Physical metrics are often correlated.

Required before model claims:

```text
correlation matrix
PCA/feature grouping candidate
LASSO/regularized model if regression is used
model_risk=high unless validated
```

HPFA default:

```text
model_output_claim_allowed=false
```

## New Product Nodes Needed

### 1. Raw Fitness Value Extract Lite V1

Purpose:

```text
Extract actual team/player physical values from reference documents or physical-cost surfaces.
```

Outputs:

```text
raw_fitness_team_values_v1.tsv
raw_fitness_player_values_v1.tsv
raw_fitness_value_audit_v1.json
raw_fitness_value_audit_v1.txt
```

Status:

```text
NEXT_FITNESS_NODE
```

### 2. Reference Fitness Provenance Lite V1

Purpose:

```text
Attach source/page/document provenance, unit confidence and entity binding to extracted physical values.
```

Outputs:

```text
reference_fitness_provenance_lite_v1.json
reference_fitness_provenance_lite_v1.txt
```

### 3. Physical Event Window Join Lite V1

Purpose:

```text
Join event-family windows with physical-cost support windows.
```

Join levels:

```text
WINDOW_LEVEL_ONLY
TIMESTAMP_ALIGNED_CANDIDATE
NOT_JOINABLE
```

Outputs:

```text
physical_event_window_join_lite_v1.json
physical_event_window_join_lite_v1.txt
```

### 4. Behaviour Fusion Taxonomy Lite V1

Purpose:

```text
Classify every fused behaviour candidate as observed, supported, assumed or unverified.
```

Outputs:

```text
behaviour_fusion_taxonomy_lite_v1.json
behaviour_fusion_taxonomy_lite_v1.txt
```

### 5. Behavioural Decrement Signal Lite V1

Purpose:

```text
Detect event-only or event+physical performance-decrement candidates without fatigue truth.
```

Allowed methods:

```text
change-point detection
CUSUM
windowed entropy
inter-event interval drift
HMM latent-regime candidate
point-process intensity drift
```

Blocked:

```text
fatigue truth
injury truth
mental decline truth
```

### 6. Action Cost Candidate Lite V1

Purpose:

```text
Estimate candidate physical cost attached to action-family windows.
```

Allowed:

```text
cost per action-family window
cost per role/team window
physical support per event volume
```

Blocked:

```text
exact action cost without timestamp alignment
player superiority truth
technical quality causality
```

### 7. Claim-Safe Report Grammar Gate V1

Purpose:

```text
Convert fusion outputs into allowed analyst language.
```

Required language classes:

```text
observed
supported
assumed
unverified
blocked
```

## Completion Phase Order

```text
1. Source Conflict Registry Lite V1
2. Raw Fitness Value Extract Lite V1
3. Reference Fitness Provenance Lite V1
4. Physical Event Window Join Lite V1
5. Behaviour Fusion Taxonomy Lite V1
6. Behavioural Decrement Signal Lite V1
7. Action Cost Candidate Lite V1
8. Claim-Safe Report Grammar Gate V1
9. Analyst Report Fusion Upgrade
```

## Immediate Gap Closure

The next two executable nodes should be:

```text
A. Source Conflict Registry Lite V1
B. Raw Fitness Value Extract Lite V1
```

Reason:

```text
Source Conflict Registry stabilizes multi-surface reliability.
Raw Fitness Value Extract converts current physical report counts into actual values.
```

## ACTIVE_MATCH Evidence Requirements

Every executable node must produce:

```text
engineering evidence:
- py_compile pass
- pytest pass
- flat phone output
- no nested output

analyst evidence:
- what visible surface changed
- what is observed/supported/assumed/unverified
- what remains blocked
```

## Status

```text
SPEC_BACKLOG
FITNESS_EVENT_FUSION_COMPLETION_PHASE_OPEN
PRODUCTION_RELEASE_NOT_GRANTED
```
