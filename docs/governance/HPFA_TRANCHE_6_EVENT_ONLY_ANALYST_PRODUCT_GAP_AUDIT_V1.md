# HPFA TRANCHE 6 — EVENT-ONLY ANALYST PRODUCT GAP AUDIT V1

Date: 2026-08-13
Record type: CONSOLIDATION / PRODUCT-GAP AUDIT
Status: AUDIT_COMPLETE / IMPLEMENTATION_DEFERRED_BY_FEATURE_FREEZE
Product code change: none
Reference development checkpoint: `fdb8e109daebd7a9875d6f257011cb93e0372677`

## Audit question

What is the smallest existing-path change required to turn HPFA's current event-only Behaviour / Sequence / Context evidence into professional analyst-facing football interpretation without tracking or video?

## Verified gap

At the development checkpoint, `reasoning_grammar_spine_lite_v1` is still `primitive_only`.

Current stage gates remain:

```text
sequence_candidate_allowed=false
behaviour_candidate_allowed=false
pattern_candidate_allowed=false
identity_candidate_allowed=false
match_story_allowed=false
```

Its source is still primarily:

```text
postmatch_analyst_report_lite_v1
-> action_family_comparison
-> PASS / CARRY_DRIBBLE / RECOVERY / BALL_LOSS / SHOT
-> primitive candidates
```

The module therefore does not consume the richer development evidence already produced downstream of the Evidence Spine.

`postmatch_analyst_report_lite_v1` is also still primarily a numeric/surface comparison report. It compares visible row volume, action-family volume, zones and channels and generates safe translations from those comparisons. It does not consume current consequence, sequence, phase or context evidence as its primary reasoning basis.

## Existing development intelligence that is not yet promoted into Reasoning/Analyst output

Current development lineage already contains substantially richer candidate surfaces, including:

```text
selected action consequence
selected event consequence
visible time layers
visible sequence candidates
event-derived phase candidates
phase-aware refinement
match context candidates
outcome-support candidates
structural progression evidence
coordinate/progression preconditions
```

Recorded ACTIVE_MATCH development evidence includes, at various exact historical heads:

```text
selected_action_node_count=2511
visible_action_sequence_candidate_count=322
phase_segments=645
```

These counts are development evidence from their respective exact heads and are not revalidated integration-head truth for a future consolidated branch. They demonstrate capability existence, not current release admission.

## Root cause

The problem is not lack of upstream football-intelligence machinery.

The product gap is:

```text
RICH DEVELOPMENT EVIDENCE
!=
CURRENT REASONING INPUT
```

The current Reasoning Grammar still reasons from primitive aggregate comparisons instead of admitted action/consequence/sequence/context evidence objects.

## Product decision

Do not open a parallel "AI analyst" or new independent pattern engine.

After controlled consolidation, evolve the existing reporting/reasoning path so that it consumes admitted outputs from the consolidated Behaviour / Sequence / Context spine.

Preferred path:

```text
Evidence Spine
-> Selected Action / Consequence
-> Visible Sequence
-> Event-Derived Phase / Context
-> Outcome Support
-> Analyst-Usable Evidence Promotion
-> existing Reasoning Grammar evolution
-> existing Analyst Report evolution
```

The exact implementation filename/version should be decided only on the consolidated integration head. The audit does not authorize a new standalone node during feature freeze.

## Minimum analyst-usable evidence object

Every promoted football-reading object should carry at least:

```text
evidence_id
match_surface_binding_id
team_candidate
actor_candidate when applicable
period/time scope
action/sequence/context lineage
observation_class
support_count
eligible_window_count
supporting_evidence_ids
contradicting_evidence_ids
contextualizing_evidence_ids
confidence / evidence ladder
falsifier
blocked_claims
claim_eligibility
```

Optional only when valid and explicitly bound:

```text
zone/channel
score state
opponent/context exposure denominator
value estimate
uncertainty interval
```

## Promotion grammar

### Stage A — direct observable relation

Examples:

```text
recovery -> same-team continuation
recovery -> opponent handover
progressive/zone-gain evidence -> retention
progressive/zone-gain evidence -> later handover
turnover -> opponent shot/box-access candidate
restart -> visible continuation chain
sequence -> terminal shot candidate
```

No tactical interpretation yet.

### Stage B — repeated pattern evidence

A relation may become a pattern candidate only when its eligible-window denominator and repetition count are explicit.

Minimum schema:

```text
pattern_support = repeated_supported_occurrences / eligible_occurrences
```

No universal threshold is hardcoded in governance. Thresholds require validation by metric/pattern family and competition/provider context.

### Stage C — contextualized pattern evidence

Where context is available and valid, compare like with like:

```text
observed_pattern_rate
vs
expected_pattern_rate given context
```

Potential context dimensions:

```text
match minute
score state when validated
team/opponent possession-exposure proxy when admitted
restart/open-play context
field zone/channel when coordinate frame is eligible
opponent strength when external context is explicitly sourced
```

No hidden normalization.

### Stage D — analyst interpretation

Sentence generation is allowed only from an admitted evidence object.

Required sentence anatomy:

```text
OBSERVATION
+ CONTEXT
+ MECHANISM SUPPORTED BY EVENT CHAIN
+ CONSEQUENCE
+ CONFIDENCE / LIMIT WHEN MATERIAL
```

Example safe pattern:

> Visible recovery sequences were repeatedly followed by same-team forward continuation and later final-third/box-access evidence in the admitted windows; this supports an event-only reading that the team converted recoveries into attacking continuation efficiently within this match surface. It does not establish pressing shape or off-ball transition structure.

The exact phrase "efficiently" is only allowed if the denominator/value contract for that family is admitted. Otherwise use "frequently" or direct count/rate language.

## Metric-to-story prohibition

The following is invalid:

```text
high progressive passes
-> team progressed well
```

Required evidence path should seek, where available:

```text
progression evidence
+ outcome support
+ visible retention
+ later zone/box/shot consequence
+ turnover consequence
+ context
+ repetition
-> analyst interpretation
```

## Contradiction requirement

Analyst output must not only accumulate confirming evidence.

For every material pattern candidate, the reasoning layer should seek:

```text
SUPPORTS
CONTRADICTS
COMPLEMENTS
CONTEXTUALIZES
ABSTAINS
```

Example:

A high progression count can be contradicted or qualified by:

- high false-progression candidate share;
- frequent opponent handover after gain;
- low terminal/box consequence support;
- game-state inflation;
- unresolved coordinate-frame eligibility.

## Event-only professional analysis scope

### High-priority direct-analysis families

```text
sequence construction
sequence consequence
progression persistence
turnover consequence
recovery consequence
transition event chains
restart/set-piece event chains
final-third / box access
shot chains
player involvement in admitted sequences
game-state/context-adjusted production
repeated-pattern evidence
opportunity/exposure normalization
calibrated action/sequence value after admission
```

### Explicitly blocked as direct truth without external validation

```text
pressing shape
team compactness
physical block height
inter-player distance
pitch control
body orientation
field of view
sprint / acceleration / fatigue
true off-ball run/location
coach intention
player intention
tactical superiority
dominance
line-breaking truth without opponent structure
```

These may only appear as `EVENT-ONLY PROXY / HYPOTHESIS` when a defined proxy exists and the report states the external validation requirement.

## Post-consolidation implementation priority

### P0

Consolidate and exact-head revalidate the existing Behaviour / Sequence / Context evidence producers.

### P1

Add an analyst-usable evidence promotion adapter/extension to the existing path; prefer extension over a new standalone product node.

### P2

Evolve `reasoning_grammar_spine_lite` so sequence/context/pattern stages can open only when corresponding consolidated gates pass.

### P3

Evolve `postmatch_analyst_report_lite` to consume admitted reasoning objects rather than relying mainly on row-volume/action-family comparisons.

### P4

Add Evidence Notebook drill-down and contradiction/falsifier presentation.

### P5

Only after the above: calibrated value models, contextual expectation models and player/team contribution models.

## Required tests for the first implementation

At minimum:

```text
test_no_raw_metric_to_story_jump
test_every_sentence_has_evidence_lineage
test_contradiction_evidence_is_not_silently_dropped
test_pattern_claim_requires_eligible_denominator
test_context_normalization_is_explicit
test_proxy_claim_is_labeled
test_tracking_truth_remains_blocked
test_sequence_claim_requires_sequence_gate
test_phase_claim_requires_phase_gate
test_progression_claim_requires_progression_gate
test_no_sample_match_identity_leak
test_exact_match_binding_is_preserved
test_canonical_event_count_unknown_is_preserved
test_engineering_audit_separated_from_analyst_report
```

## ACTIVE_MATCH validation target

The first consolidated analyst-product validation should prove an end-to-end chain on an exact integration head:

```text
raw visible surface
-> admitted evidence
-> consequence/sequence/context object
-> analyst-usable evidence
-> analyst sentence
-> evidence notebook trace
```

Acceptance is not "report rendered".

Acceptance is:

```text
traceable
claim-safe
football-useful
context-aware
contradiction-aware
falsifiable
```

## Current decision

The highest-value post-consolidation development target is not another metric family.

It is the missing bridge:

```text
CURRENT DEVELOPMENT FOOTBALL INTELLIGENCE
-> ANALYST_USABLE_EVIDENCE
-> PROFESSIONAL EVENT-ONLY FOOTBALL READING
```

Status:

`GAP_CONFIRMED / EXISTING_PATH_EXTENSION_PREFERRED / FEATURE_FREEZE_PRESERVED / IMPLEMENT_AFTER_CONSOLIDATED_PREREQUISITES / NOT_PRODUCTION / NOT_MERGED`
