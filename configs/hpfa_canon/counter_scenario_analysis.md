# HPFA Canonical Event Schema v0.1 - Counter-Scenario Analysis

**Classification:** Critical System Risk Assessment  
**Date:** 2026-02-27  
**Severity:** HIGH

---

## Primary Counter-Scenario: Coordinate Normalization Failure Chain

### Scenario Description

HPFA schema assumes all coordinates are normalized to "attacking direction = left-to-right" based on possession. This creates a critical dependency on possession attribution accuracy.

### Failure Chain

```
┌─────────────────────────────────────────────────────────────────┐
│                    FAILURE CHAIN DIAGRAM                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Provider Data                                                 │
│       │                                                         │
│       ▼                                                         │
│   ┌───────────────────┐                                        │
│   │ Possession        │ ◄── FAILURE POINT 1                    │
│   │ Attribution Error │     Provider assigns possession        │
│   └─────────┬─────────┘     to wrong team                      │
│             │                                                   │
│             ▼                                                   │
│   ┌───────────────────┐                                        │
│   │ Coordinate Flip   │ ◄── FAILURE POINT 2                    │
│   │ Applied Wrongly   │     Flip applied when shouldn't be     │
│   └─────────┬─────────┘     or not applied when should be      │
│             │                                                   │
│             ▼                                                   │
│   ┌───────────────────┐                                        │
│   │ Spatial Metrics   │ ◄── FAILURE POINT 3                    │
│   │ Inverted          │     All x-coordinates mirrored         │
│   └─────────┬─────────┘                                         │
│             │                                                   │
│             ▼                                                   │
│   ┌───────────────────┐                                        │
│   │ xG/xT Models      │ ◄── FAILURE POINT 4                    │
│   │ Produce Nonsense  │     Shot from x=10 becomes x=90        │
│   └─────────┬─────────┘                                         │
│             │                                                   │
│             ▼                                                   │
│   ┌───────────────────┐                                        │
│   │ Causal Graph      │ ◄── TERMINAL FAILURE                   │
│   │ Corrupted         │     SCM edges point wrong direction    │
│   └───────────────────┘                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Breaking Condition (Formal)

```python
# Breaking condition for coordinate normalization
def breaking_condition_CN001(event_batch):
    """
    Returns TRUE if coordinate normalization failure is likely.
    
    Parameters:
    - event_batch: list of events with possession attribution
    
    Breaking condition triggered when:
    1. Possession changes > expected rate, AND
    2. Spatial distribution anomaly detected, AND
    3. Provider confidence below threshold
    """
    
    # Constants
    POSSESSION_CHANGE_RATE_MAX = 0.15  # max 15% of events are possession changes
    SPATIAL_SYMMETRY_THRESHOLD = 0.7   # normalized spatial distribution
    PROVIDER_CONFIDENCE_MIN = 0.85
    
    # Calculate metrics
    possession_change_rate = count_possession_changes(event_batch) / len(event_batch)
    spatial_symmetry = calculate_spatial_symmetry(event_batch)
    avg_confidence = mean([e.confidence_score for e in event_batch])
    
    # Breaking condition
    if (possession_change_rate > POSSESSION_CHANGE_RATE_MAX 
        AND spatial_symmetry < SPATIAL_SYMMETRY_THRESHOLD
        AND avg_confidence < PROVIDER_CONFIDENCE_MIN):
        return {
            "triggered": True,
            "error_code": "CN-001",
            "severity": "CRITICAL",
            "action": "HALT_INGESTION",
            "reason": "Coordinate normalization failure chain likely"
        }
    
    return {"triggered": False}
```

### Quantified Impact

| Metric | Normal Value | Under Failure | Detection Difficulty |
|--------|-------------|---------------|---------------------|
| xG accuracy | ±0.02 | ±0.45 | HARD (requires ground truth) |
| Pass direction accuracy | 98% | 2% | EASY (visually obvious) |
| Causal edge validity | 99.5% | <50% | MODERATE (requires validation set) |
| Zone-based metrics | Valid | Inverted | EASY (left/right swap) |

### Why This Scenario Is Critical

1. **Silent corruption:** Unlike missing data, inverted coordinates pass all basic validation gates (G01-G07). Values are within bounds, timestamps are valid.

2. **Downstream amplification:** Error propagates through entire analytics pipeline. Every metric that uses spatial data becomes unreliable.

3. **Detection requires context:** You need external reference (video, broadcast) to detect this error. Pure data validation cannot catch it.

4. **Provider dependency:** HPFA cannot independently verify possession. It must trust provider attribution.

### Mitigation Strategy

```yaml
mitigation:
  level_1_prevention:
    name: "Possession Continuity Check"
    description: >
      Verify possession doesn't flip-flop unreasonably.
      Maximum 5 possession changes per minute under normal play.
    implementation_gate: "G10 (PENDING)"
    
  level_2_detection:
    name: "Spatial Distribution Sanity Check"
    description: >
      Team A's events should cluster on different x-range than Team B's.
      If both teams' events uniformly distributed, flip error likely.
    implementation_gate: "G13 (PENDING)"
    
  level_3_recovery:
    name: "Dual-Provider Reconciliation"
    description: >
      If multiple providers available, compare possession attribution.
      Disagreement > 5% triggers quarantine.
    implementation_gate: "G12 (PENDING)"
    
  level_4_fallback:
    name: "Manual Video Cross-Reference"
    description: >
      For high-stakes matches, sample 10 random events and verify
      against broadcast video.
    implementation: "HUMAN_IN_LOOP"
```

### Schema Design Implications

**Current schema vulnerability:** Schema assumes possession is correct. No field exists to flag "possession_attribution_confidence" separately from overall event confidence.

**Proposed schema addition for v0.2:**

```yaml
# New field for v0.2
- name: "possession_confidence"
  type: "FLOAT"
  required: true
  min: 0.0
  max: 1.0
  description: "Confidence in possession attribution (affects coordinate flip)"
  default: 1.0  # Assume provider is correct unless flagged
  
- name: "coordinate_flip_applied"
  type: "BOOLEAN"
  required: true
  description: "Whether coordinate normalization was applied to this event"
  audit_importance: "HIGH"
```

---

## Secondary Counter-Scenario: Event Hash Collision

### Scenario Description

Event_id is generated from content hash. Two genuinely different events could theoretically produce same hash.

### Breaking Condition

```
P(collision) = 1 - e^(-n²/2H)

Where:
- n = number of events
- H = hash space (SHA-256 = 2^256)

For n = 10^9 events (lifetime HPFA):
P(collision) ≈ 10^-58

VERDICT: Theoretically possible, practically impossible.
```

### Why This Is NOT a Critical Risk

1. **Mathematical improbability:** SHA-256 collision probability for realistic event volumes is negligible.

2. **Even if collision occurs:** Primary key is composite (match_id + period_id + game_clock_ms + event_sequence_id). Hash is tie-breaker only.

3. **Detection is immediate:** Duplicate event_id would be caught at insertion time.

**Conclusion:** This scenario is documented for completeness but does not require mitigation.

---

## Tertiary Counter-Scenario: Temporal Monotonicity Break

### Scenario Description

Provider sends events out of order, or timestamps regress within a period.

### Breaking Condition

```python
def breaking_condition_TM001(event_stream):
    """
    Detects temporal monotonicity violation.
    """
    
    for i in range(1, len(event_stream)):
        current = event_stream[i]
        previous = event_stream[i-1]
        
        if current.period_id == previous.period_id:
            if current.game_clock_ms < previous.game_clock_ms:
                return {
                    "triggered": True,
                    "error_code": "TM-001",
                    "severity": "HIGH",
                    "action": "QUARANTINE_EVENT",
                    "details": {
                        "expected_min": previous.game_clock_ms,
                        "actual": current.game_clock_ms,
                        "delta": previous.game_clock_ms - current.game_clock_ms
                    }
                }
    
    return {"triggered": False}
```

### Impact Assessment

| Scenario | Frequency | Severity | Current Handling |
|----------|-----------|----------|------------------|
| Provider sends batch out-of-order | Common | LOW | Sort before processing |
| Provider timestamp error | Rare | MEDIUM | G02 gate rejects |
| Clock drift between providers | Occasional | HIGH | 50ms tolerance absorbs |
| VAR-induced timeline split | Rare | CRITICAL | NOT HANDLED |

### VAR Timeline Split Problem

**This is an unresolved schema limitation:**

When VAR overturns a goal, the "official" timeline diverges from the "played" timeline. Current schema has no mechanism to represent:

1. Events that occurred but were retroactively invalidated
2. The moment of VAR decision vs. moment of original event
3. Alternative timeline branches

**Proposed v0.2 addition:**

```yaml
- name: "var_status"
  type: "ENUM"
  required: false
  enum: ["CONFIRMED", "OVERTURNED", "UNDER_REVIEW", "NOT_APPLICABLE"]
  default: "NOT_APPLICABLE"
  
- name: "original_event_id"
  type: "UUID"
  required: false
  description: "For overturned events, reference to the VAR decision event"
```

---

## Risk Priority Matrix

| Counter-Scenario | Probability | Impact | Detection | Priority |
|-----------------|-------------|--------|-----------|----------|
| Coordinate Normalization Failure | Medium | Critical | Hard | **P1** |
| VAR Timeline Split | Low | High | N/A | **P2** |
| Temporal Monotonicity Break | Medium | Medium | Easy | **P3** |
| Event Hash Collision | Negligible | Low | Easy | P5 |
| Schema Drift | Medium | High | Medium | **P2** |
| Sparse Data Collapse | High | Medium | Medium | **P3** |

---

## Conclusion

The primary counter-scenario (Coordinate Normalization Failure) represents the most critical systemic risk in the v0.1 schema. It is:

1. **Not currently detectable** by implemented gates (G01-G07)
2. **Silently corrupting** to all downstream analytics
3. **Dependent on pending gates** (G10, G12, G13) for mitigation

**Recommendation:** Do not deploy v0.1 schema to production until G10 (Possession Coherence) is formalized and implemented.

---

**Document Classification:** HPFA Internal - Technical Risk Assessment  
**Review Required:** System Architecture Lead, Data Quality Lead
