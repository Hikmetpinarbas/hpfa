# HPFA Donor Intelligence Harvest V1

Status: DISCOVERY_PASS_PLAN_ONLY
Release status: REVIEW_REQUIRED
Product authority: hpfa
Runtime authority: runtime/active_single_match/current
Rule: ADAPT_NOT_COPY

This document changes donor research from governance-only scanning to football-intelligence harvesting.

Primary question:

```text
How can this donor capability expand what HPFA sees in football behaviour?
```

This is a discovery map. It creates no executable code, runtime evidence, production release, tactical truth, possession truth, phase truth, sequence truth or dominance truth.

## Step gain record

```json
{
  "step_id": "DONOR_INTELLIGENCE_HARVEST_V1",
  "source_repo": "HP-Engine|HP-Motor|HP-Motor-main|HP-PROJELERI|Dropbox|Google Drive",
  "target_hpfa_module": "football_intelligence_backlog",
  "engineering_gain": [
    "football-intelligence donor scan axis",
    "pattern sequence temporal metric harvest map",
    "analysis-capability backlog",
    "growth-registry direction"
  ],
  "analyst_gain": [
    "future reports can move from surface summary to behaviour reading",
    "sequence rhythm transition and territory-proxy language can be designed as candidate evidence",
    "analyst workflows can later support similarity search and motif retrieval"
  ],
  "new_blockers": [
    "harvest is not executable",
    "each capability requires HPFA-native contract schema tests ACTIVE_MATCH evidence and output audit",
    "multi-match retrieval requires archive authority before runtime use"
  ],
  "claim_boundary_change": "none",
  "runtime_evidence_required": true,
  "release_status": "REVIEW_REQUIRED"
}
```

## Verified GitHub donor intelligence findings

### HP-Engine Pattern Engine

Sources:

- `HP_ENGINE/pattern/live/hp_pattern_engine.py`
- `HP_ENGINE/pattern/live/pattern_registry_v1.json`

Capability:

Pattern detection from sequence and graph surfaces.

Observed football-intelligence candidates:

- direct attack bias
- sustained build-up bias
- transition attack bias
- central progression bias
- switch tendency
- shot pressure pattern
- contested instability
- channel concentration
- degraded pattern handling

Football value:

This can support candidate readings about attack construction, directness, sustained build-up, transition behaviour, channel switching and contest-related instability.

Analyst value:

The analyst can later see candidate match identity rather than only action volume.

HPFA adaptation:

`Pattern Candidate Engine Lite V1` under Analyst Intelligence Layer.

Priority:

P1 after Ontology Registry and Evidence Ladder.

### HP-Engine Sequence Engine

Source:

- `HP_ENGINE/sequence/sprint_v1/sequence_engine_v1.py`

Capability:

Event stream segmentation into sequence candidates using period change, restart, time gap, possession hint and team gain logic.

Observed football-intelligence candidates:

- restart attack candidate
- transition candidate
- open-play candidate
- sequence duration
- event count per sequence
- progression distance
- progression dx and dy
- start and end reasons
- sequence trace

Football value:

This can move HPFA from isolated actions toward construction arcs such as restart, transition, open play, progression, terminal sequence and rebuild candidates.

Analyst value:

The analyst can later see how action clusters begin, continue, split and end.

HPFA adaptation:

`Sequence Candidate Engine Lite V1` under Segmentation Layer.

Priority:

P1/P2 after Match Context Slicer and source governance stabilize.

### HP-Engine Temporal Signal Factory

Source:

- `HP_ENGINE/temporal/_merge_lab/hp_temporal_engine__20260309_162910/src/hp_temporal_signal_factory_v1.py`

Capability:

Build time-series signals from event surfaces.

Observed football-intelligence candidates:

- event density signal
- attack burst signal
- turnover pressure proxy signal
- events dropped for missing time
- signal bin count
- attack and turnover event counts

Football value:

This is the basis for rhythm, tempo, instability, burst and pressure-proxy support.

Analyst value:

The analyst can later inspect where match surface activity changes and where burst or turnover-pressure proxy concentrations rise.

HPFA adaptation:

`Tempo Support Signal Lite V1` and `Event Burst Signal Lite V1`.

Priority:

P2 after temporal and source gates.

### HP-Engine Temporal Metric Engine

Source:

- `HP_ENGINE/temporal/_merge_lab/hp_temporal_engine__20260309_162910/src/hp_temporal_metric_engine_v1.py`

Capability:

Transform temporal signals into rhythm and volatility support metrics.

Observed football-intelligence candidates:

- event rate per minute
- attack rate per minute
- turnover pressure rate per minute
- tempo peak frequency
- tempo peak period
- tempo spectral entropy
- attack cluster index
- rhythm stability index
- phase transition proxy rate
- temporal state entropy

Football value:

This is a strong donor for rhythm and behaviour-volatility support.

Analyst value:

The analyst can later compare low-volatility circulation, bursty transition, high-contest instability and stable rhythm candidates.

HPFA adaptation:

`Rhythm Support Metric Lite V1` and `Temporal State Candidate Lite V1`.

Priority:

P2 after Evidence Ladder and signal-density gate.

### HP-Motor Metric Registry

Source:

- `hp_motor/library/registry/metric_registry.json`

Capability:

Metric definitions with mechanisms, formulas, required fields and status policy.

Observed football-intelligence candidates:

- pass count
- progressive pass count
- shot count
- turnover count
- sequence length
- control, progression and risk mechanisms
- required-column status policy

Football value:

This can support HPFA-native metrics such as progression efficiency, risk concentration, sequence density and field utilization.

Analyst value:

The analyst can later see whether a metric is a volume primitive, progression primitive, risk primitive, temporal primitive or diagnostic support primitive.

HPFA adaptation:

`Metric Dependency Graph Lite V1` and `Football Intelligence Metric Backlog V1`.

Priority:

P1 after Ontology Registry and Evidence Ladder.

## HPFA-native metric backlog candidates

Pressure and escape:

- Escape Difficulty
- Pressure Escape Score
- Escape Route Diversity
- Recovery-to-Escape Speed
- Failed Escape Cascade Rate

Build and progression:

- Build-up Stability
- Progression Efficiency
- Central Progression Bias
- Width Expansion Rate
- Half-space Progression Candidate
- Recycle-to-Progression Ratio

Transition and recovery:

- Recovery Speed
- Transition Elasticity
- Counter-Recovery Rate
- Transition-to-Shot Conversion Candidate
- Failure Cascade Density

Sequence and motif:

- Sequence Density
- Sequence Diversity
- Sequence Persistence
- Attack Construction Depth
- Terminal Pressure Rate
- Sequence Fingerprint Similarity
- Motif Recurrence Index

Rhythm and tempo:

- Rhythm Volatility
- Tempo Elasticity
- Momentum Persistence
- Attack Burst Concentration
- Temporal State Entropy
- Event Compression
- Event Expansion

Territory and field use:

- Territory Proxy
- Territorial Compression
- Field Utilization
- Space Switching Index
- Channel Concentration
- Final-Third Surface Pressure Candidate

Behaviour and complexity:

- Behaviour Entropy
- Decision Complexity
- Risk Concentration
- Instability Load
- Stabilization Response
- Control Loss Surface Candidate

## Intelligence growth families

1. Event Ontology Growth
2. Canonical Ingest Growth
3. Context Intelligence Growth
4. Metric Primitive Growth
5. Sequence and Rhythm Growth
6. Graph and Network Growth
7. Claim Science Growth
8. Analyst Language Growth
9. Product Engineering and Release Governance Growth

## Future analyst workflows

Target workflows:

- match behaviour similarity search
- multi-match motif retrieval
- team signature comparison
- sequence fingerprint search
- anomaly discovery across match history
- change detection across last N matches
- territory-proxy trend retrieval
- context-state query filters

## Implementation priorities

P0 finish open blockers:

- PR #94 Match Context Slicer blocker/test/runtime path
- PR #98 modernization intake cleanup or replacement
- PR #104 capability/ontology/evidence pack review

P1 intelligence primitives:

- Pattern Candidate Engine Lite V1
- Football Behaviour Taxonomy Lite V1
- Metric Dependency Graph Lite V1
- Sequence Candidate Engine Lite V1

P2 temporal and rhythm support:

- Tempo Support Signal Lite V1
- Event Burst Signal Lite V1
- Rhythm Support Metric Lite V1
- Temporal State Candidate Lite V1

P3 retrieval and graph intelligence:

- Sequence Fingerprint Index Lite V1
- Match Similarity Index Lite V1
- Behaviour Graph Lite V1
- Analyst Retrieval Query Lite V1

## Release rule

This harvest is not production capability. It is a football-intelligence backlog and donor research map. Every candidate must later become a HPFA-native contract, schema, test pack, ACTIVE_MATCH runtime evidence and football output audit before any stronger status is allowed.
