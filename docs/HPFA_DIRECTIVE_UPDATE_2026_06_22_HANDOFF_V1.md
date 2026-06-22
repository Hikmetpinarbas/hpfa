# HPFA Directive Update — 2026-06-22 Handoff V1

Status: active handoff note  
Runtime authority: `runtime/active_single_match/current`

## Core correction

Do not describe current CSV/XML row totals as canonical event totals.

Use:

```text
surface rows
event-like rows
visible rows
row-level evidence
action-family volume
```

Do not use, until Canonical Event Lite validates it:

```text
canonical event count
true event stream
validated event truth
```

## Current ACTIVE_MATCH analyst evidence

Match surface:

```text
Australia 2-0 Turkey
World Cup
13.06.2026
```

Observed current brief:

```text
surface_count=8
Players.csv rows=3463
Teams.csv rows=4069
Goalkeepers.csv rows=193
```

Top action-family evidence:

```text
PASS=3708
DUEL_PRESSURE=748
GOAL_KICKS_SHORT=615
POSITIONAL_ATTACK_INVOLVEMENT=608
GOAL_KICKS_MEDIUM=443
SHOT=353
CARRY_DRIBBLE=286
BALL_LOSS=215
RECOVERY=147
```

Spatial evidence:

```text
FINAL_THIRD=2794 / 36.2%
MIDDLE_THIRD=2758 / 35.7%
DEFENSIVE_THIRD=2161 / 28.0%
RIGHT_CHANNEL=2960 / 38.3%
CENTRAL_CHANNEL=2660 / 34.4%
LEFT_CHANNEL=2093 / 27.1%
```

Team row-volume evidence from Players.csv:

```text
Turkey=2373
Australia=1275
```

This is row-volume evidence, not quality or superiority evidence.

## Current executable core

```text
canonical_ingest_surface_manifest
boundary_analysis_scorer
active_match_spine_runner
```

## Current open fix

Codex flagged nested phone output paths for the spine runner.

Patch branch:

```text
runner-flat-out-v1
```

Expected validation:

```text
4 passed
```

## Next work order

```text
P0 merge runner-flat-out-v1 after Termux validation
P1 ACTIVE_MATCH Analyst Report Lite V1
P2 Canonical Event Lite V1
P3 Team Binding Lite V1
P4 Time/Phase Lite V1
P5 Metric Primitive Lite V1
P6 Claim-safe Analyst Summary V1
```

## Source search order

```text
1 hpfa main
2 HP-Motor donor
3 HP-Engine donor
4 HP-PROJELERI governance donor
5 Google Drive action vocabulary / formulas / completion plan
6 Dropbox donor archives when accessible
7 Sider Scholar only for research support
8 Termux discovery and composite registry
```
