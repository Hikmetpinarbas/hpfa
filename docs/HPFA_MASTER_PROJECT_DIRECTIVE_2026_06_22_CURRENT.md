# HPFA MASTER PROJECT DIRECTIVE

Version: 2026.06.22-CURRENT  
Project: HPFA — Hikmet Pinarbas Football Analytics  
Repository: Hikmetpinarbas/hpfa  
Status: ACTIVE MASTER DIRECTIVE  
Runtime authority: `runtime/active_single_match/current`

---

## 1. Project identity

HPFA is an event-only, claim-safe, modular and portable Football Intelligence Platform.

HPFA is not only a report writer.

HPFA builds product modules that discover football behaviour, patterns, sequences, match identity and evidence-backed analyst output.

The product must serve two users at the same time:

```text
1. The software operator / engineer
2. The football analyst
```

Engineering evidence alone is not enough. Every runtime milestone must also explain what the analyst can and cannot see from the match.

---

## 2. Primary objective

The goal is not to produce more metrics.

The goal is to produce controlled football intelligence:

```text
behaviour discovery
pattern discovery
sequence evidence
match identity
football explanation
claim-safe analyst output
runtime evidence
```

The platform must help answer:

```text
What did HPFA see in this match?
Which signals are visible?
Which signals are missing?
Which football statements are safe?
Which statements must remain closed?
```

---

## 3. Runtime authority

The only runtime authority is:

```text
runtime/active_single_match/current
```

For the current Termux lab this resolved to:

```text
/data/data/com.termux/files/home/hpfa_claim_integrity/hpfa/runtime/active_single_match/current
```

No other source is event authority.

Reference-only sources:

```text
Google Drive
Dropbox
Sider Scholar
academic papers
PDFs
old archives
old samples
reports
donor repositories
research packs
```

These sources can support design, validation and adaptation, but they do not create match truth.

---

## 4. Repository roles

### hpfa

Single product repository. Executable HPFA product modules live here.

### HP-Motor

Donor repository for:

```text
canonical ingest
phase
possession
sequence
metric primitives
registry-style runtime apparatus
```

### HP-Engine

Donor repository for:

```text
pattern discovery
sequence intelligence
behaviour graph
semantic gates
explanation engine
higher-level football intelligence
```

### HP-PROJELERI

Governance donor for:

```text
policy
authority
gates
release discipline
registry rules
claim boundaries
```

---

## 5. Donor rule

Never copy donor code directly.

Required sequence:

```text
1. inspect current hpfa producer
2. inspect donor capability
3. define boundary
4. adapt, not copy
5. create HPFA module
6. execute on ACTIVE_MATCH
7. audit football output
8. release only when evidence supports it
```

Directive:

```text
ADAPT_NOT_COPY
```

---

## 6. Core spine

HPFA execution spine:

```text
RAW DATA
SOURCE AUTHORITY
ACTIVE MATCH
CANONICAL INGEST
DATA QUALITY GATE
GATE CONSUMER
PHASE
POSSESSION
SEQUENCE
METRIC CONTRACT
METRIC PRIMITIVES
PROGRESSION
CONTEXT
CLAIM GATE
FOOTBALL OUTPUT AUDIT
MATCH STORY
RUNTIME EVIDENCE
```

A downstream layer must not bypass an upstream gate.

---

## 7. Current product state

Merged and executable in current main:

```text
canonical_ingest_surface_manifest
boundary_analysis_scorer
active_match_spine_runner
```

Root CLIs in main:

```text
boundary_analysis_scorer.py
active_match_spine_runner.py
```

Current spine runner output files:

```text
active_match_surface_manifest_v1.json
boundary_analysis_score_registry_v1.json
active_match_spine_check_v1.json
active_match_spine_check_v1.txt
```

Current open fix branch:

```text
runner-flat-out-v1
```

Purpose of open fix:

```text
Reject nested phone output folders under /sdcard/Download/HPFA.
```

---

## 8. Phone output policy

All user-visible Termux outputs must be written directly under:

```text
/sdcard/Download/HPFA
```

Nested output folders under that path are not allowed.

Allowed:

```text
/sdcard/Download/HPFA/active_match_spine_check_v1.txt
/sdcard/Download/HPFA/active_match_analyst_report_lite_v1.txt
```

Not allowed:

```text
/sdcard/Download/HPFA/spine-run/output.txt
/sdcard/Download/HPFA/reports/output.txt
```

---

## 9. Critical row-count correction

Do not describe current CSV/XML row totals as canonical events.

Current ACTIVE_MATCH files expose rows, labels, coordinates and event-like instances.

Correct terms:

```text
surface rows
visible rows
event-like rows
row-level evidence
action-family volume
event-row evidence
```

Do not use until Canonical Event Lite validates the stream:

```text
canonical event count
true event stream
validated event truth
complete event truth
thousands of events
```

`canonical_event_count` remains:

```text
UNKNOWN
```

until a canonical event module proves otherwise.

---

## 10. Current ACTIVE_MATCH sample

Current sample:

```text
Australia 2-0 Turkey
World Cup
13.06.2026
```

Surface evidence:

```text
surface_count=8
Goalkeepers.csv rows=193
Goalkeepers.xml rows=193
Players.csv rows=3463
Players.xml rows=3463
Teams.csv rows=4069
Teams.xml rows=4069
Goalkeepers.xlsx rows=3
Players.xlsx rows=31
```

These are visible row counts, not canonical event counts.

---

## 11. Current analyst-facing evidence

Action-family evidence from the temporary Analyst Brief V1:

```text
PASS=3708
DUEL_PRESSURE=748
GOAL KICKS SHORT (0-15 M)=615
INVOLVEMENT IN POSITIONAL ATTACKS=608
GOAL KICKS MEDIUM (15-40 M)=443
SHOT=353
CARRY_DRIBBLE=286
BALL_LOSS=215
RECOVERY=147
POSITIONAL ATTACKS=121
FOUL=64
```

Zone evidence:

```text
DEFENSIVE_THIRD=2161 / 28.0%
MIDDLE_THIRD=2758 / 35.7%
FINAL_THIRD=2794 / 36.2%
UNKNOWN=12 / 0.2%
```

Channel evidence:

```text
RIGHT_CHANNEL=2960 / 38.3%
CENTRAL_CHANNEL=2660 / 34.4%
LEFT_CHANNEL=2093 / 27.1%
UNKNOWN=12 / 0.2%
```

Team row-volume evidence from Players.csv:

```text
Turkey (77798)=2373
Australia (6935)=1275
```

This is row-volume evidence only. It is not quality, superiority, control or tactical-plan evidence.

---

## 12. Analyst-facing obligation

The user is a football analyst.

Every runtime test must produce two views:

```text
1. Engineering evidence
2. Analyst-facing football brief
```

Engineering evidence answers:

```text
Did the module run?
Did it write valid outputs?
Did it preserve policy boundaries?
```

Analyst-facing evidence answers:

```text
What action families are visible?
Where are actions concentrated?
Which channels are visible?
Which team row-volume signals exist?
Which labels are useful for football interpretation?
Which interpretations are blocked?
```

---

## 13. Current safe analyst interpretation

Allowed now:

```text
The match surface is readable.
The expected eight surfaces are present.
Action-family volume can be shown.
Zone and channel distributions can be shown when coordinate columns are detected.
Team row-volume can be shown where a team column exists.
Goal-kick and restart labels can be surfaced.
Pass, shot, duel, carry, ball-loss and recovery labels can be reported as row-level evidence.
```

Not allowed now:

```text
final tactical judgement
team dominance statement
off-ball behaviour statement
coach intention
pitch-control claim
player judgement without player binding
canonical event total
professional final report
```

---

## 14. Current missing product layers

Still missing or not executable in product spine:

```text
Canonical Event Lite
Team Binding Lite
Time / Phase Lite
Possession Lite
Sequence Lite
Metric Primitive Lite
Progression Lite
Claim-safe Analyst Summary
Football Output Audit
Professional Report Candidate
```

These must be built incrementally.

---

## 15. Next product order

Priority order:

```text
P0 validate and merge runner-flat-out-v1
P1 ACTIVE_MATCH Analyst Report Lite V1
P2 Canonical Event Lite V1
P3 Team Binding Lite V1
P4 Time / Phase Lite V1
P5 Metric Primitive Lite V1
P6 Claim-safe Analyst Summary V1
P7 Football Output Audit Lite V1
```

---

## 16. ACTIVE_MATCH Analyst Report Lite V1 requirements

This is the next analyst-facing product module.

It must produce:

```text
active_match_analyst_report_lite_v1.json
active_match_analyst_report_lite_v1.txt
```

under:

```text
/sdcard/Download/HPFA
```

It must include:

```text
match data snapshot
surface inventory
action-family volume table
zone distribution
channel distribution
team row-volume comparison when possible
goalkeeper and restart signal block
pass / shot / duel / carry / loss / recovery signal block
claim-safe analyst interpretation
missing-column report
limits section
```

It must not call row counts canonical events.

---

## 17. Search order before new coding

Before implementing any next module, inspect sources in this order:

```text
1. hpfa current main branch
2. HP-Motor donor
3. HP-Engine donor
4. HP-PROJELERI governance donor
5. Google Drive completion plan, action vocabulary, formulas, event-core plans
6. Dropbox donor archive and research packs when accessible
7. Sider Scholar / Wisebase for academic support only
8. Termux discovery reports and composite registry
```

---

## 18. Google Drive reference status

Drive currently confirms an ACTIVE_MATCH completion plan exists.

The plan frames the target chain as:

```text
RAW
Canonical / Action
Possession / Sequence
Progression / Consequence
Evidence Table
Claim Confidence Gate
Claim-safe Match Story
Professional Report Candidate
```

Drive also indicates action vocabulary, formula library and event-core runtime planning archives exist and should be searched before coding the next analyst layer.

---

## 19. Dropbox reference status

Dropbox must be searched for donor packs and older research archives, but it is not runtime authority.

If Dropbox search returns no direct match, do not invent content. Continue using current repo, Drive and Termux evidence.

---

## 20. Sider Scholar status

Sider Scholar is research support only.

It can support concepts such as sequence analysis, event data modelling, football analytics methodology and report safety, but no academic paper is runtime truth.

---

## 21. Claim safety

Blocked truth areas:

```text
pitch control truth
body orientation truth
coach intention
team dominance truth
fatigue truth
off-ball truth
tactical truth
```

Allowed claim-safe wording:

```text
shows row-level evidence
visible in the surface
coordinate evidence indicates
action-family volume suggests
requires later validation
not enough evidence for final claim
```

---

## 22. Release rule

Smoke pass is not release proof.

Termux ACTIVE_MATCH execution is necessary, but not sufficient alone.

Release requires:

```text
module execution
output file evidence
boundary statement
claim-safety review
analyst-facing usefulness
no unauthorized runtime source
```

---

## 23. Defer-to-next-page state

If the conversation is transferred, the next page must begin with:

```text
1. this directive
2. the project register prompt
3. the handoff text
4. runner-flat-out-v1 validation
5. Analyst Report Lite V1 planning
```

The immediate next technical action is:

```text
validate runner-flat-out-v1 in Termux
open PR
merge after patch inspection
```

The immediate next analyst product action is:

```text
ACTIVE_MATCH Analyst Report Lite V1
```
