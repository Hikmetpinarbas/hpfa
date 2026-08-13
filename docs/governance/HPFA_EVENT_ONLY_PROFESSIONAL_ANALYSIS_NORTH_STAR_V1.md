# HPFA EVENT-ONLY PROFESSIONAL ANALYSIS NORTH STAR V1

Date: 2026-08-13
Record type: GOVERNANCE / ANALYST-PRODUCT ACCEPTANCE CONTRACT
Status: CURRENT CONSOLIDATION GUIDANCE
Runtime truth: unchanged
Product code change: none

## North Star

HPFA'nın ana ürün hedefi:

> Tracking ve video olmadan, yalnız event-data yüzeyinin gerçekten desteklediği kanıttan profesyonel futbol analizi üretmek.

Event-only analiz, eksik tracking analizi değildir. HPFA tracking/video gerçekliğini taklit etmeye çalışmaz; event verisinin güçlü olduğu action, consequence, sequence, context, repetition, value/risk ve player/team contribution katmanlarında mümkün olan en yüksek analist değerini üretir.

## Core distinction

```text
ENGINEERING EVIDENCE GRAPH
input -> parse -> schema -> semantics -> identity -> reconciliation -> gate -> status

FOOTBALL INTELLIGENCE GRAPH
evidence -> action -> relation -> consequence -> sequence -> context -> repeated pattern -> metric/value -> analyst interpretation
```

Bir node teknik olarak PASS çalışabilir fakat futbol iddiası REVIEW_REQUIRED kalabilir. Bunun tersi kabul edilmez: futbol anlatısı engineering evidence sınırlarını aşamaz.

## Evidence promotion ladder

```text
RAW_SURFACE
-> EVIDENCE_ATOM
-> SUPPORTED_CANDIDATE
-> RECONCILED_CANDIDATE
-> ANALYST_USABLE_EVIDENCE
-> METRIC_ELIGIBLE
-> CLAIM_ELIGIBLE
```

`TACTICAL_TRUTH` zorunlu son basamak değildir. Event-only profesyonel analiz, tactical-truth iddiası olmadan da yüksek analist değerine ulaşabilir.

## Professional analyst questions HPFA should answer from event-only evidence

1. Ne oldu?
2. Nerede oldu?
3. Ne zaman oldu?
4. Hangi oyuncu/takım yaptı?
5. Aksiyonun sonucu neydi?
6. Öncesindeki görünür event zinciri neydi?
7. Sonrasındaki görünür event zinciri neydi?
8. İlerleme oldu mu; olduysa görünür biçimde korundu mu?
9. Aksiyon/sekans box access, shot, turnover, restart veya recovery gibi hangi observable sonuca bağlandı?
10. Aynı sequence/pattern maç içinde tekrarlandı mı?
11. Game-state ve görünür bağlam değiştiğinde üretim nasıl değişti?
12. Oyuncunun takımın görünür action/sequence üretimine katkısı neydi?
13. Hangi bulgu destekleniyor, hangisi çelişiyor, hangisi yalnız proxy/hypothesis seviyesinde?
14. Hangi veri bulguyu yanlışlayabilir?

## First-class event-only analysis families

Aşağıdaki aileler HPFA'nın tracking/video olmadan profesyonel analiz üretme çekirdeğidir:

- action-family volume and outcome;
- sequence construction and sequence consequence;
- progression persistence / false progression candidate;
- recovery-to-continuation / recovery-to-threat evidence;
- turnover consequence and visible response windows;
- final-third and box access evidence;
- shot-chain and chance-chain evidence;
- transition event-chain evidence;
- restart / set-piece event-chain evidence;
- goalkeeper distribution consequence;
- game-state/context conditioned production;
- opportunity/exposure normalization when denominators are explicit;
- player involvement and contribution within visible sequences;
- team/actor action-family profiles;
- repeated pattern evidence;
- calibrated action/sequence value only after value-model admission gates pass;
- support / contradiction / contextualization graph across metrics and patterns.

## Event-only claim ceiling

### Allowed when evidence and relevant gates support it

Examples:

```text
visible event-chain evidence shows...
this action/sequence was followed by...
progression was retained / lost within the visible event window candidate...
box-access evidence increased/decreased in this context...
recovery was followed by same-team continuation / opponent handover / shot candidate...
this pattern repeated across N eligible windows...
player X had the highest/lowest eligible contribution within the defined event-only metric scope...
```

### Must remain proxy / hypothesis unless independently validated

```text
pressing intensity/shape
team compactness
block height as physical team shape
inter-player distances
pitch control
space occupation without observable event support
body orientation
field of view
physical load / sprint / acceleration / fatigue
true off-ball runs and locations
coach intention
player intention
tactical superiority
dominance
line-breaking truth without opponent-structure ground truth
```

Required label:

`EVENT-ONLY PROXY / HYPOTHESIS`

Required validation when promoted:

`tracking / video / reviewed provider ground-truth`

## No metric-to-story jump

A single metric cannot become a football conclusion directly.

Required relation grammar:

```text
SUPPORTS
CONTRADICTS
COMPLEMENTS
CONTEXTUALIZES
ABSTAINS
```

Example:

`progressive-pass volume` alone is not "good progression".

Professional interpretation should seek eligible support from, where available:

- outcome;
- visible continuation;
- retention;
- zone gain;
- box access;
- shot consequence;
- turnover consequence;
- game state;
- opponent/context exposure;
- repeatability;
- uncertainty.

## Analyst product architecture

Final user-visible product should remain three-layered:

### 1. Analyst Report
Football language first. Main findings, mechanisms, contextual interpretation, player/team implications, uncertainty where material.

### 2. Evidence Notebook
Drill-down by sequence, player, time, coordinate, action, consequence, context and supporting/contradicting evidence.

### 3. Engineering Audit
Runtime provenance, schema/semantic status, review hits, hard blocks, source lineage, exact-head evidence, claim ceilings.

Engineering language must not dominate the Analyst Report.

## Required analyst reasoning spine

The target reasoning chain is:

```text
EVENT
-> ACTION
-> CONSEQUENCE
-> SEQUENCE
-> CONTEXT
-> REPEATED PATTERN
-> CONTEXTUAL EXPECTATION
-> DEVIATION FROM EXPECTATION
-> PLAYER / TEAM CONTRIBUTION
-> ANALYST INTERPRETATION
-> UNCERTAINTY / FALSIFIER
```

No layer may silently manufacture a missing predecessor.

## Tranche 6 acceptance criteria

Tranche 6 — Analyst Product cannot be considered analyst-complete merely because a numeric report renders.

Minimum acceptance:

1. At least one end-to-end event-only evidence chain reaches `ANALYST_USABLE_EVIDENCE` on exact integration-head ACTIVE_MATCH evidence.
2. Analyst-facing sentences are generated only from admitted evidence objects, never raw metric rows alone.
3. Every material interpretation can be traced to supporting evidence IDs/sequence IDs/context IDs.
4. Contradicting evidence is surfaced, not silently discarded.
5. Repeated-pattern claims disclose eligible window/support count.
6. Player/team comparisons disclose denominator and eligibility scope.
7. Game-state/context adjustment is explicit when used; no hidden normalization.
8. Proxy/hypothesis claims are visibly separated from direct event evidence.
9. Tracking/video-only truth fields remain blocked without external validation.
10. Report language is football-first; engineering audit remains separate.
11. `canonical_event_count=UNKNOWN` remains preserved until separately admitted.
12. `production_release=false` remains preserved until explicit release authority.

## Consolidation rule

During the current feature-freeze, this record does not authorize a new independent intelligence node.

Implementation priority is:

1. consolidate existing final-state capability snapshots;
2. revalidate exact integration-head ACTIVE_MATCH evidence;
3. identify the highest-value gap between existing Behaviour/Sequence/Context evidence and Analyst Product;
4. extend an existing admitted capability where possible instead of inventing a parallel node;
5. open a new capability only when the existing dependency graph cannot express the required analyst evidence.

## First post-consolidation engineering target

The first target should be the smallest existing-path extension that promotes current action/consequence/sequence/context evidence into `ANALYST_USABLE_EVIDENCE` while preserving:

```text
possession_truth=false unless separately admitted
sequence_truth=false where evidence remains candidate-only
phase_truth=false where evidence remains candidate-only
progression_truth=false until coordinate/semantic/denominator gates pass
tracking_truth=false
coach_intention=false
```

The objective is not to make HPFA talk more. The objective is to make every professional football statement traceable, useful and epistemically calibrated.

## Decision rule for future research

A new academic method or metric is high-priority only if it improves at least one of:

- evidence resolution;
- context normalization;
- sequence/action valuation;
- uncertainty calibration;
- player/team attribution;
- pattern repeatability testing;
- analyst decision quality;
- claim traceability;
- contradiction handling.

If it mainly imitates unavailable tracking/video information, produces an unvalidated tactical label, duplicates an existing node, or cannot improve analyst decision quality, priority is LOW or REJECT.

## Status

`NORTH_STAR_FIXED / GOVERNANCE_ONLY / FEATURE_FREEZE_PRESERVED / EVENT_ONLY_PROFESSIONAL_ANALYSIS_TARGET / NOT_PRODUCTION / NOT_MERGED`
